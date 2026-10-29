#!/usr/bin/env python3
"""Authorized EmbeddingGemma feature export and frozen R-GCN/CompGCN runs."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

import numpy as np

import rgcn_compgcn as baseline
import rgcn_compgcn_v2 as study
import rgcn_compgcn_models as models

ROOT = study.ROOT
EXP = study.OUT
MODEL = "google/embeddinggemma-2"
REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"
DIMENSIONS = 768
HIDDEN = 128
SEEDS = (117, 118, 119)
MAX_EPOCHS = 100
PATIENCE = 10
MAX_SECONDS = 6 * 60 * 60
MAX_RSS = 24 * 1024**3


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def process_peak_rss_bytes() -> int:
    high_water = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(high_water if sys.platform == "darwin" else high_water * 1024)


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def approval(path: Path, field: str, expected: dict) -> dict:
    record = read(path)
    if record.get("status") != "approved" or record.get(field) is not True:
        raise ValueError(f"Owner authorization must set status=approved and {field}=true")
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"Owner authorization does not bind frozen {key}")
    return record


def text_for_node(node: dict) -> str:
    values = [f"{lang}: {value}" for lang, labels in sorted(node["labels"].items())
              for value in labels]
    return "; ".join(values) if values else node["iri"]


def text_for_relation(relation: dict) -> str:
    values = [f"{lang}: {value}" for lang, labels in sorted(relation["labels"].items())
              for value in labels]
    return "; ".join(values) if values else relation["iri"]


def encode_batches(encoder, texts: list[str], batch_size: int = 8) -> np.ndarray:
    chunks = [encoder.encode(texts[i:i + batch_size]).cpu().numpy() for i in range(0, len(texts), batch_size)]
    return np.concatenate(chunks).astype(np.float32, copy=False)


def make_features(experiment_dir: Path, model_dir: Path, authorization_file: Path,
                  out: Path) -> dict:
    questions_path = experiment_dir / "questions.json"
    bench_manifest = read(experiment_dir / "manifest.json")
    expected = {"model": MODEL, "revision": REVISION,
                "dataset_manifest_sha256": bench_manifest["dataset_manifest_sha256"],
                "benchmark_manifest_sha256": sha_file(experiment_dir / "manifest.json"),
                "questions_sha256": sha_file(questions_path)}
    approval(authorization_file, "allow_embeddinggemma_inference", expected)
    manifest_path = out.with_suffix(".manifest.json")
    if out.exists() or manifest_path.exists():
        raise ValueError("Feature output exists; choose a fresh path")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import embedding_experiment
    spec, _ = embedding_experiment.verify()
    if spec["model"] != MODEL or spec["revision"] != REVISION or spec["dimensions"] != DIMENSIONS:
        raise ValueError("EmbeddingGemma pin or dimensions changed")
    assets = embedding_experiment.assets(model_dir)
    if not assets["valid"]:
        raise ValueError("Model assets must already exist locally and match the pinned upstream hashes")
    torch, runtime = embedding_experiment.cpu_runtime()
    encoder = embedding_experiment.Encoder(model_dir, torch, spec)
    nodes = study.read_jsonl(study.EXPORT / "nodes.jsonl")
    relations = study.read_jsonl(study.EXPORT / "relations.jsonl")
    questions = read(questions_path)
    node_texts = ["title: none | text: " + text_for_node(node) for node in nodes]
    relation_texts = ["title: none | text: " + text_for_relation(relation) for relation in relations]
    query_texts = ["task: search result | query: " + row["query"] for row in questions]
    inference_started = time.perf_counter()
    node_features = encode_batches(encoder, node_texts)
    relation_features = encode_batches(encoder, relation_texts)
    query_features = encode_batches(encoder, query_texts)
    inference_ms = (time.perf_counter() - inference_started) * 1000
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("xb") as stream:
        np.savez_compressed(stream, node_features=node_features, relation_features=relation_features,
                            query_features=query_features,
                            query_ids=np.asarray([row["id"] for row in questions], dtype="U96"))
    manifest = {"version": "wikidata-relational-features-v1", **expected,
                "benchmark_manifest_sha256": expected["benchmark_manifest_sha256"],
                "relations_sha256": sha_file(study.EXPORT / "relations.jsonl"),
                "nodes_sha256": sha_file(study.EXPORT / "nodes.jsonl"),
                "feature_file": out.name, "feature_file_sha256": sha_file(out),
                "prefixes": {"node_and_relation": "title: none | text: ",
                             "query": "task: search result | query: "},
                "node_text_policy": "Original graph labels tagged with their language; identifier fallback only if unlabeled.",
                "relation_text_policy": "Original Wikidata property labels tagged with their language; property IRI fallback only if unlabeled.",
                "dtype": "float32", "dimensions": DIMENSIONS,
                "shapes": {"node_features": list(node_features.shape),
                           "relation_features": list(relation_features.shape),
                           "query_features": list(query_features.shape)},
                "queries_sha256": sha_file(questions_path), "assets_sha256": assets["sha256"],
                "runtime": runtime, "model_load_ms": encoder.load_ms,
                "inference_ms": inference_ms, "inference_performed": True}
    write(manifest_path, manifest)
    return manifest


def validate_features(feature_file: Path, feature_manifest_file: Path,
                      experiment_dir: Path) -> tuple[dict, dict[str, np.ndarray]]:
    manifest = read(feature_manifest_file)
    questions = read(experiment_dir / "questions.json")
    nodes = study.read_jsonl(study.EXPORT / "nodes.jsonl")
    relations = study.read_jsonl(study.EXPORT / "relations.jsonl")
    if manifest["model"] != MODEL or manifest["revision"] != REVISION:
        raise ValueError("Feature model revision mismatch")
    if manifest["feature_file_sha256"] != sha_file(feature_file):
        raise ValueError("Feature file hash mismatch")
    if manifest["queries_sha256"] != sha_file(experiment_dir / "questions.json"):
        raise ValueError("Feature queries differ from frozen questions")
    if manifest["benchmark_manifest_sha256"] != sha_file(experiment_dir / "manifest.json"):
        raise ValueError("Feature dataset freeze differs from the benchmark")
    with np.load(feature_file, allow_pickle=False) as archive:
        values = {name: archive[name] for name in archive.files}
    expected_shapes = {"node_features": (len(nodes), DIMENSIONS),
                       "relation_features": (len(relations), DIMENSIONS),
                       "query_features": (len(questions), DIMENSIONS),
                       "query_ids": (len(questions),)}
    for name, shape in expected_shapes.items():
        if name not in values or values[name].shape != shape:
            raise ValueError(f"Invalid {name} feature shape")
        if name != "query_ids" and (values[name].dtype != np.float32 or
                                    not np.isfinite(values[name]).all()):
            raise ValueError(f"Invalid {name} feature values or dtype")
    if values["query_ids"].tolist() != [row["id"] for row in questions]:
        raise ValueError("Query feature row order differs from the frozen benchmark")
    for name in ("node_features", "relation_features", "query_features"):
        norms = np.linalg.norm(values[name], axis=1)
        if not np.allclose(norms, 1.0, atol=1e-4):
            raise ValueError(f"{name} vectors are not L2 normalized")
    return manifest, values


def feature_binding(feature_manifest_file: Path) -> dict:
    manifest = read(feature_manifest_file)
    feature_file = feature_manifest_file.parent / manifest["feature_file"]
    if manifest["feature_file_sha256"] != sha_file(feature_file):
        raise ValueError("Feature file does not match its manifest")
    return {"feature_manifest_sha256": sha_file(feature_manifest_file),
            "feature_file_sha256": sha_file(feature_file)}


def feature_tests_only(path: Path) -> None:
    import tempfile
    rng = np.random.default_rng(117)
    questions = read(EXP / "questions.json")
    nodes = study.read_jsonl(study.EXPORT / "nodes.jsonl")
    relations = study.read_jsonl(study.EXPORT / "relations.jsonl")
    with tempfile.TemporaryDirectory() as directory:
        feature_file = Path(directory) / "features.npz"
        matrices = {}
        for name, rows in (("node_features", len(nodes)), ("relation_features", len(relations)),
                           ("query_features", len(questions))):
            value = rng.normal(size=(rows, DIMENSIONS)).astype(np.float32)
            value /= np.linalg.norm(value, axis=1, keepdims=True)
            matrices[name] = value
        with feature_file.open("wb") as stream:
            np.savez_compressed(stream, **matrices,
                                query_ids=np.asarray([row["id"] for row in questions], dtype="U96"))
        manifest = {"model": MODEL, "revision": REVISION, "feature_file_sha256": sha_file(feature_file),
                    "feature_file": feature_file.name,
                    "queries_sha256": sha_file(EXP / "questions.json"),
                    "benchmark_manifest_sha256": sha_file(EXP / "manifest.json")}
        manifest_file = Path(directory) / "manifest.json"
        write(manifest_file, manifest)
        validate_features(feature_file, manifest_file, EXP)
        binding = feature_binding(manifest_file)
        if binding["feature_file_sha256"] != sha_file(feature_file):
            raise ValueError("Synthetic feature manifest did not bind its vector file")


def make_preflight(out: Path) -> dict:
    if out.exists():
        raise ValueError("Preflight receipt exists; choose a fresh path")
    result = subprocess.run(["system_profiler", "-detailLevel", "mini", "SPHardwareDataType"],
                            capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError("Read-only system_profiler hardware check failed: " + result.stderr)
    import platform
    import psutil
    profile = result.stdout
    expected = all(value in profile for value in ("MacBookPro18,1", "Apple M1 Pro", "Memory: 32 GB"))
    memory = psutil.virtual_memory()
    resource_ok = expected and memory.available >= MAX_RSS
    receipt = {"version": "rgcn-compgcn-readonly-preflight-v2", "hardware_profile": profile,
               "target_hardware_match": expected, "machine": platform.machine(),
               "cpu_count": psutil.cpu_count(logical=True), "ram_total_bytes": memory.total,
               "available_memory_snapshot_bytes": memory.available,
               "memory_snapshot_policy": "Informational only; not used to infer model memory or training RSS.",
               "available_memory_exceeds_registered_rss_ceiling": memory.available >= MAX_RSS,
               "resource_preflight_passed": resource_ok,
               "disk_free_bytes": __import__("shutil").disk_usage(ROOT).free,
               "execution": "No processes terminated, no resource limits changed, no model loaded, no training run.",
               "training_resource_preflight": "Requires at least 24 GiB currently available; this does not estimate model RSS. Actual model RSS and latency remain unmeasured."}
    receipt["status"] = "pass" if resource_ok else "fail-static-resource-gate"
    write(out, receipt)
    return receipt


def candidate_universe(nodes: list[dict], relations: list[dict]):
    return [("entity", node["iri"]) for node in nodes] + [("predicate", row["iri"]) for row in relations]


def role_candidate_ids(role: str, node_count: int, relation_count: int,
                       excluded_entity_ids: set[int] | None = None) -> list[int]:
    if role == "entity":
        excluded = excluded_entity_ids or set()
        return [index for index in range(node_count) if index not in excluded]
    if role == "predicate":
        return list(range(node_count, node_count + relation_count))
    raise ValueError(f"Unsupported retrieval role: {role}")


def query_target(iri: str, role: str, node_ids: dict[str, int], relation_ids: dict[str, int], node_count: int) -> int:
    if role == "entity":
        return node_ids[iri]
    return node_count + relation_ids[iri]


def query_examples(qids: list[str], questions: list[dict], references: list[dict],
                   query_features: np.ndarray, node_ids: dict[str, int], relation_ids: dict[str, int],
                   node_count: int, relation_count: int, *, seed: int, excluded_nodes: set[str]):
    by_question = {row["id"]: row for row in questions}
    by_reference = {row["id"]: row for row in references}
    feature_rows = {row["id"]: i for i, row in enumerate(questions)}
    rng = random.Random(seed)
    values = []
    for qid in qids:
        question, reference = by_question[qid], by_reference[qid]
        if reference["status"] != "relevant" or len(reference["relevant"]) != 1:
            continue
        target = query_target(reference["relevant"][0]["iri"], question["role"],
                              node_ids, relation_ids, node_count)
        excluded_ids = {node_ids[iri] for iri in excluded_nodes if iri in node_ids}
        pool = [candidate for candidate in role_candidate_ids(
            question["role"], node_count, relation_count, excluded_ids) if candidate != target]
        negatives = rng.sample(pool, 10)
        values.append((feature_rows[qid], target, negatives))
    if not values:
        raise ValueError("Frozen split contains no single-target relevant questions")
    return values


def encode_query_tensors(examples, query_features, torch):
    return (torch.as_tensor(query_features[[x[0] for x in examples]], dtype=torch.float32),
            torch.tensor([x[1] for x in examples], dtype=torch.long),
            torch.tensor([x[2] for x in examples], dtype=torch.long))


def evaluate_model(model, node_features, relation_features, edge_index, edge_types,
                   question_ids, questions, references, query_features, candidate_ids,
                   graph: str, support: dict[str, set[tuple[str, str]]],
                   twohop_paths: dict[str, list[dict]], torch):
    started = time.perf_counter()
    model.eval()
    with torch.no_grad():
        entities, relations = model(node_features, relation_features, edge_index, edge_types)
    encode_ms = (time.perf_counter() - started) * 1000
    by_question = {row["id"]: row for row in questions}
    by_reference = {row["id"]: row for row in references}
    feature_rows = {row["id"]: i for i, row in enumerate(questions)}
    predictions, rank_rows = [], []
    score_started = time.perf_counter()
    with torch.no_grad():
        for qid in question_ids:
            q = by_question[qid]
            scores = model.score_queries(entities, relations,
                torch.as_tensor(query_features[feature_rows[qid]:feature_rows[qid] + 1], dtype=torch.float32))[0]
            score_values = scores.cpu().tolist()
            node_count = entities.shape[0]
            role_ids = role_candidate_ids(q["role"], node_count, relations.shape[0])
            order = sorted(role_ids, key=lambda i: (-score_values[i], candidate_ids[i][1]))
            ranked = [(graph, candidate_ids[i][1]) for i in order]
            ref = by_reference[qid]
            relevant = {(item["graph"], item["iri"]) for item in ref["relevant"]}
            metrics = baseline.rank_metrics(relevant, ranked)
            path_metrics = (study.exact_path_metrics(ranked, ref, twohop_paths.get(qid, []))
                            if q["family"] == "two_hop_path" and ref["status"] == "relevant"
                            else None)
            target_ranks = [{"graph": item["graph"], "iri": item["iri"],
                             "rank": ranked.index((item["graph"], item["iri"])) + 1
                                    if (item["graph"], item["iri"]) in ranked else None,
                             "score": score_values[next(i for i, candidate in enumerate(candidate_ids)
                                 if candidate[1] == item["iri"])] if any(candidate[1] == item["iri"]
                                 for candidate in candidate_ids) else None} for item in ref["relevant"]]
            top = [{"role": candidate_ids[i][0], "graph": graph, "iri": candidate_ids[i][1],
                    "score": score_values[i], "source_witnessed": (graph, candidate_ids[i][1])
                    in support.get(qid, set())} for i in order[:50]]
            top10 = [(graph, candidate_ids[i][1]) for i in order[:10]]
            support_set = support.get(qid, set())
            witness_coverage = (len(set(top10) & support_set) / len(top10)) if top10 else 0.0
            source_paths = [{"rank": rank, "graph": candidate["graph"], "entity_iri": candidate["iri"],
                             "source_quads": candidate["source_quads"]}
                            for rank, (candidate_graph, candidate_iri) in enumerate(ranked[:50], 1)
                            for candidate in twohop_paths.get(qid, [])
                            if (candidate["graph"], candidate["iri"]) == (candidate_graph, candidate_iri)]
            predictions.append({"id": qid, "split": q["split"], "language": q["language"],
                                "family": q["family"], "status": ref["status"],
                                "target_ranks": target_ranks, "top50": top,
                                "source_witnessed_paths": source_paths,
                                "path_candidate_source": "structured-query traversal capture; graph quads independently source-checked",
                                "source_path_metrics": path_metrics,
                                "metrics": metrics, "full_candidate_count": len(ranked),
                                "no_match_top10_suggestion": ref["status"] == "no_match" and bool(ranked[:10])})
            rank_rows.append({"id": qid, "split": q["split"], "language": q["language"],
                              "query_group": q["query_group"], "family": q["family"], "status": ref["status"],
                              "relevant": sorted([list(item) for item in relevant]),
                              "metrics": metrics, "candidate_count": len(ranked),
                              "source_path_metrics": path_metrics,
                              "target_ranks": target_ranks,
                              "candidate_pool_recall": (len(relevant & set(ranked)) / len(relevant)
                                                         if relevant else None),
                              "top10_source_witness_coverage": witness_coverage,
                              "candidate_returned": bool(ranked[:10]),
                              "no_match_top10_suggestion": ref["status"] == "no_match" and bool(ranked[:10])})
    score_ms = (time.perf_counter() - score_started) * 1000
    return predictions, rank_rows, {"graph_encode_ms": encode_ms, "query_scoring_ms": score_ms,
                                    "query_scoring_ms_per_case": score_ms / max(1, len(question_ids))}


def summarize(rows: list[dict]) -> dict:
    metrics = ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10")
    def group_summary(group):
        return {"n": len(group), **{key: (sum(row["metrics"][key] for row in group) / len(group)
                                          if group else None) for key in metrics}}
    output = {"overall": {}, "strata": {}, "outcomes": {}}
    for split in ("train", "validation", "test"):
        output["overall"][split] = group_summary([row for row in rows
            if row["split"] == split and row["status"] == "relevant"])
    test = [row for row in rows if row["split"] == "test" and row["status"] == "relevant"]
    for language in ("en", "no"):
        output["strata"][f"language/{language}"] = group_summary([row for row in test
            if row["language"] == language])
    for family in sorted({row["family"] for row in test}):
        output["strata"][f"family/{family}"] = group_summary([row for row in test
            if row["family"] == family])
    for status in ("ambiguous", "no_match"):
        group = [row for row in rows if row["split"] == "test" and row["status"] == status]
        output["outcomes"][status] = {"n": len(group),
            "candidate_returns": sum(bool(row["candidate_returned"]) for row in group),
            "no_match_top10_suggestions": sum(bool(row["no_match_top10_suggestion"]) for row in group)}
    test_rows = [row for row in rows if row["split"] == "test"]
    output["test_top10_source_witness_coverage"] = {
        "n": len(test_rows), "mean": (sum(row["top10_source_witness_coverage"] for row in test_rows)
                                        / len(test_rows) if test_rows else None)}
    path_rows = [row["source_path_metrics"] for row in rows
                 if row["split"] == "test" and row["source_path_metrics"] is not None]
    output["two_hop_source_path_metrics"] = {
        "n": len(path_rows), **{key: (sum(row[key] for row in path_rows) / len(path_rows)
                                      if path_rows else None)
                                for key in ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10")}}
    return output


def paired_group_delta(model_rows: list[dict], baseline_rows: list[dict], metric: str,
                       seed: int = 117, draws: int = 2000) -> dict:
    by_model = {row["id"]: row for row in model_rows
                if row["split"] == "test" and row["status"] == "relevant"}
    by_baseline = {row["id"]: row for row in baseline_rows
                   if row["split"] == "test" and row["status"] == "relevant"}
    groups = defaultdict(list)
    for qid in sorted(set(by_model) & set(by_baseline)):
        groups[by_model[qid]["query_group"]].append(
            by_model[qid]["metrics"][metric] - by_baseline[qid]["metrics"][metric])
    values = [sum(group) / len(group) for group in groups.values()]
    if not values:
        return {"query_n": 0, "group_n": 0, "mean": None, "bootstrap_95": None}
    rng = random.Random(seed)
    samples = [sum(values[rng.randrange(len(values))] for _ in values) / len(values)
               for _ in range(draws)]
    samples.sort()
    return {"query_n": len(set(by_model) & set(by_baseline)), "group_n": len(values),
            "mean": sum(values) / len(values),
            "bootstrap_95": [samples[int(0.025 * draws)], samples[min(draws - 1, int(0.975 * draws))]],
            "resampling_unit": "query_group (source edge/path family)"}


def compare_to_baselines(rank_rows: list[dict], baseline_cases: list[dict], baseline_summary: dict) -> dict:
    method_cases = defaultdict(list)
    for row in baseline_cases:
        method_cases[row["method"]].append(row)
    methods = sorted(method_cases)
    text_methods = [name for name in methods if name in {"bm25", "embeddinggemma"}]
    if "embeddinggemma" not in text_methods:
        raise ValueError("A matched EmbeddingGemma Wikidata baseline must be scored before training approval")
    strongest_text = max(text_methods, key=lambda name:
                         baseline_summary["methods"][name]["metrics"]["recall@10"])
    return {"strongest_text_baseline": strongest_text,
            "paired_group_deltas": {name: {metric: paired_group_delta(rank_rows, method_cases[name], metric)
                                                  for metric in ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10")}
                                    for name in methods}}


def run_training(experiment_dir: Path, run_manifest_path: Path, feature_file: Path,
                 feature_manifest_path: Path, preflight_path: Path,
                 authorization_file: Path, out: Path) -> dict:
    run_manifest = read(run_manifest_path)
    baseline_dir = ROOT / run_manifest["source"]["baseline_score_dir"]
    if sha_file(baseline_dir / "summary.json") != run_manifest["source"]["baseline_summary_sha256"] or \
       sha_file(baseline_dir / "cases.jsonl") != run_manifest["source"]["baseline_cases_sha256"]:
        raise ValueError("Matched baseline results changed after the experiment freeze")
    baseline_summary = read(baseline_dir / "summary.json")
    baseline_cases = [json.loads(line) for line in (baseline_dir / "cases.jsonl").read_text().splitlines()]
    if "embeddinggemma" not in baseline_summary["methods"]:
        raise ValueError("Matched EmbeddingGemma retrieval results are required before GNN training")
    feature_manifest, arrays = validate_features(feature_file, feature_manifest_path, experiment_dir)
    if run_manifest["features"].get("binding") != feature_binding(feature_manifest_path):
        raise ValueError("Final experiment freeze must bind these exact feature and manifest hashes")
    preflight = read(preflight_path)
    if preflight.get("target_hardware_match") is not True or preflight.get("resource_preflight_passed") is not True:
        raise ValueError("Read-only preflight must match the M1 Pro and have at least 24 GiB currently available")
    expected = {"experiment_manifest_sha256": sha_file(run_manifest_path),
                "feature_manifest_sha256": sha_file(feature_manifest_path),
                "preflight_sha256": sha_file(preflight_path)}
    approval(authorization_file, "authorize_full_training", expected)
    for path, digest in run_manifest["implementation_sha256"].items():
        if sha_file(ROOT / path) != digest:
            raise ValueError(f"Implementation changed after preregistration: {path}")
    if out.exists():
        raise ValueError("Training output exists; choose a fresh path")
    os.environ.update(CUBLAS_WORKSPACE_CONFIG=":4096:8", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4")
    import psutil
    import torch
    from torch_geometric import __version__ as pyg_version
    models.seed_everything(SEEDS[0])
    torch.set_num_threads(4)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    process = psutil.Process()
    max_rss = process_peak_rss_bytes()
    total_started = time.perf_counter()
    nodes = study.read_jsonl(study.EXPORT / "nodes.jsonl")
    relations = study.read_jsonl(study.EXPORT / "relations.jsonl")
    edges = study.read_jsonl(study.EXPORT / "edges.jsonl")
    questions = read(experiment_dir / "questions.json")
    references = read(experiment_dir / "references.json")
    split = read(experiment_dir / "splits.json")
    graph = study.GRAPH
    node_ids = {row["iri"]: row["id"] for row in nodes}
    relation_ids = {row["iri"]: row["id"] for row in relations}
    edge_by_id = {study.edge_key(row): row for row in edges}
    statement_edge_id = {study.nquad(edge): study.edge_key(edge) for edge in edges}
    if set(split["message_passing_train_edge_ids"]) - set(edge_by_id):
        raise ValueError("Frozen message-passing split references unknown edge IDs")
    candidate_ids = candidate_universe(nodes, relations)
    references_by_id = {row["id"]: row for row in references}
    adjacency = read(experiment_dir / "adjacency-capture-v1/capture.json")
    support = {}
    twohop_paths = {}
    for row in (json.loads(line) for line in
                (experiment_dir / "adjacency-capture-v1/two-hop.jsonl").read_text().splitlines()):
        twohop_paths[row["id"]] = row["candidates"]
    for name in ("one-hop.jsonl", "two-hop.jsonl"):
        for row in (json.loads(line) for line in
                    (experiment_dir / "adjacency-capture-v1" / name).read_text().splitlines()):
            support.setdefault(row["id"], set()).update((candidate["graph"], candidate["iri"])
                                                         for candidate in row["candidates"])
    partitions = {
        "transductive": {
            "edges": split["message_passing_train_edge_ids"],
            "train": [row["id"] for row in questions if row["split"] == "train"],
            "validation": [row["id"] for row in questions if row["split"] == "validation"],
            "test": [row["id"] for row in questions if row["split"] == "test"],
            "unseen_nodes": set(),
        },
        "unseen_entity": {
            "edges": split["unseen_entity_generalization"]["message_passing_edge_ids"],
            "train": split["unseen_entity_generalization"]["train_query_ids"],
            "validation": split["unseen_entity_generalization"]["validation_query_ids"],
            "test": split["unseen_entity_generalization"]["test_query_ids"],
            "unseen_nodes": set(split["unseen_entity_generalization"]["unseen_entity_iris"]),
        },
    }
    out.mkdir(parents=True)
    results = []
    for partition_name, partition in partitions.items():
        train_edges = [edge_by_id[key] for key in partition["edges"]]
        train_edge_ids = set(partition["edges"])
        validation_ids, test_ids = set(partition["validation"]), set(partition["test"])
        def witness_edge_ids(qids):
            return {statement_edge_id[statement] for ref in references if ref["id"] in qids
                    for witness in ref["witnesses"] for statement in witness["source_quads"]
                    if statement in statement_edge_id}
        validation_edge_ids, test_edge_ids = witness_edge_ids(validation_ids), witness_edge_ids(test_ids)
        models.check_edge_splits(train_edge_ids, validation_edge_ids, test_edge_ids, train_edge_ids)
        edge_index = torch.tensor([[edge["subject_id"] for edge in train_edges],
                                   [edge["object_id"] for edge in train_edges]], dtype=torch.long)
        edge_types = torch.tensor([edge["predicate_id"] for edge in train_edges], dtype=torch.long)
        triples = torch.tensor([[edge["subject_id"], edge["predicate_id"], edge["object_id"]]
                               for edge in train_edges], dtype=torch.long)
        negatives = models.sample_negative_tails(triples.tolist(), triples.tolist(), len(nodes),
                                                  count=10, seed=117,
                                                  entity_ids=[node["id"] for node in nodes
                                                              if node["iri"] not in partition["unseen_nodes"]])
        node_features = torch.as_tensor(arrays["node_features"], dtype=torch.float32)
        relation_features = torch.as_tensor(arrays["relation_features"], dtype=torch.float32)
        train_examples = query_examples(partition["train"], questions, references,
                                        arrays["query_features"], node_ids, relation_ids,
                                        len(nodes), len(relations), seed=117,
                                        excluded_nodes=partition["unseen_nodes"])
        valid_examples = query_examples(partition["validation"], questions, references,
                                        arrays["query_features"], node_ids, relation_ids,
                                        len(nodes), len(relations), seed=118, excluded_nodes=set())
        train_query_features, train_targets, train_query_negatives = encode_query_tensors(
            train_examples, arrays["query_features"], torch)
        training_args = {"node_features": node_features, "relation_features": relation_features,
                         "edge_index": edge_index, "edge_types": edge_types,
                         "positive_triples": triples, "negative_tail_ids": negatives,
                         "query_features": train_query_features, "query_targets": train_targets,
                         "query_negative_ids": train_query_negatives}
        valid_query_features, valid_targets, _ = encode_query_tensors(valid_examples,
                                                                       arrays["query_features"], torch)
        def validation_mrr(model):
            model.eval()
            with torch.no_grad():
                entity_state, relation_state = model(node_features, relation_features, edge_index, edge_types)
                scores = model.score_queries(entity_state, relation_state, valid_query_features)
            reciprocal = []
            for row, target in enumerate(valid_targets.tolist()):
                question = questions[valid_examples[row][0]]
                role_ids = role_candidate_ids(question["role"], len(nodes), len(relations))
                order = sorted(role_ids, key=lambda candidate_id: -float(scores[row, candidate_id]))
                rank = order.index(target) + 1
                reciprocal.append(1 / rank if rank <= 10 else 0.0)
            return sum(reciprocal) / len(reciprocal)
        test_ids = partition["test"]
        for model_name, encoder in (("rgcn", models.RGCN), ("compgcn", models.CompGCN)):
            for seed in SEEDS:
                run_dir = out / partition_name / model_name / f"seed-{seed}"
                run_dir.mkdir(parents=True)
                def guard(epoch, row):
                    nonlocal max_rss
                    max_rss = max(max_rss, process.memory_info().rss, process_peak_rss_bytes())
                    if time.perf_counter() - total_started > MAX_SECONDS:
                        raise RuntimeError("Six-hour total training budget exceeded")
                    if max_rss > MAX_RSS:
                        raise RuntimeError("24 GiB process RSS ceiling exceeded")
                factory = lambda: encoder(DIMENSIONS, DIMENSIONS, HIDDEN, len(relations), layers=2)
                model, history = models.fit(factory, training_args, validation_mrr,
                                            seed=seed, epochs=MAX_EPOCHS, patience=PATIENCE,
                                            resource_guard=guard)
                predictions, rank_rows, timings = evaluate_model(
                    model, node_features, relation_features, edge_index, edge_types, test_ids,
                    questions, references, arrays["query_features"], candidate_ids, graph,
                    support, twohop_paths, torch)
                max_rss = max(max_rss, process.memory_info().rss, process_peak_rss_bytes())
                torch.save(model.state_dict(), run_dir / "checkpoint.pt")
                (run_dir / "predictions.jsonl").write_text("".join(
                    json.dumps(row, ensure_ascii=False) + "\n" for row in predictions))
                (run_dir / "raw-ranks.jsonl").write_text("".join(
                    json.dumps(row, ensure_ascii=False) + "\n" for row in rank_rows))
                record = {"partition": partition_name, "model": model_name, "seed": seed,
                          "history": history, "timings": timings,
                          "checkpoint_bytes": (run_dir / "checkpoint.pt").stat().st_size,
                          "max_process_rss_bytes": max_rss,
                          "training_wall_ms": sum(row["epoch_ms"] for row in history["history"]),
                          "test_summary": summarize(rank_rows),
                          "comparison": compare_to_baselines(rank_rows, baseline_cases, baseline_summary),
                          "message_passing_edge_count": len(train_edges),
                          "query_counts": {split_name: len(ids) for split_name, ids in partition.items()
                                           if split_name in {"train", "validation", "test"}}}
                write(run_dir / "training.json", record)
                results.append(record)
    receipt = {"version": "rgcn-compgcn-v2-run-receipt", "run_manifest_sha256": sha_file(run_manifest_path),
               "feature_manifest_sha256": sha_file(feature_manifest_path),
               "preflight_sha256": sha_file(preflight_path), "training_seconds": time.perf_counter() - total_started,
               "max_process_rss_bytes": max_rss, "torch_version": torch.__version__,
               "torch_geometric_version": pyg_version, "torch_threads": torch.get_num_threads(),
               "torch_interop_threads": torch.get_num_interop_threads(), "device": "cpu",
               "results": results, "authorized_training_executed": True,
               "predictions_are_hypotheses_not_RDF_evidence": True}
    write(out / "run-receipt.json", receipt)
    return receipt


def freeze_manifest(out: Path, baseline_score_dir: Path,
                    feature_manifest_path: Path | None = None) -> dict:
    if out.exists():
        raise ValueError("Freeze exists; choose a fresh path")
    bench = read(EXP / "manifest.json")
    score_dir = baseline_score_dir if baseline_score_dir.is_absolute() else ROOT / baseline_score_dir
    baseline_summary = read(score_dir / "summary.json")
    relative_score_dir = str(score_dir.relative_to(ROOT))
    binding = feature_binding(feature_manifest_path) if feature_manifest_path else None
    inputs = {name: sha_file(EXP / name) for name in
              ("questions.json", "references.json", "splits.json", "dataset-audit.json", "manifest.json")}
    implementation = {name: sha_file(ROOT / name) for name in
        ("tools/rgcn_compgcn_v2.py", "tools/rgcn_compgcn_models.py", "tools/rgcn_compgcn_run_v2.py",
         "tools/rgcn_compgcn.py", "tools/rgcn_compgcn_wikidata.py",
         "tools/embedding_experiment.py", "tools/retrieval.py", "tools/embedding-requirements.txt",
         "benchmarks/embeddinggemma/manifest.json", "benchmarks/embeddinggemma/upstream.json",
         "benchmarks/embeddinggemma/parity-inputs.json", "benchmarks/retrieval/manifest.json",
         "experiments/rgcn-compgcn-v2/requirements-gnn.lock", "experiments/rgcn-compgcn-v2/python-version.txt")}
    config = {
        "version": "rgcn-compgcn-v2-preregistration-v7",
        "status": ("frozen-protocol; matched EmbeddingGemma baseline absent" if "embeddinggemma" not in baseline_summary["methods"]
                   else "frozen-protocol; feature manifest binding absent" if binding is None
                   else "frozen-protocol; scored GNN run requires separate owner authorization"),
        "source": {"benchmark_manifest_sha256": sha_file(EXP / "manifest.json"),
                   "dataset_manifest_sha256": bench["dataset_manifest_sha256"],
                   "snapshot_sha256": bench["snapshot_sha256"], "input_sha256": inputs,
                   "baseline_score_dir": relative_score_dir,
                   "baseline_summary_sha256": sha_file(score_dir / "summary.json"),
                   "baseline_cases_sha256": sha_file(score_dir / "cases.jsonl"),
                   "native_capture_receipt_sha256": sha_file(EXP / "native-capture-v1/capture.json"),
                   "adjacency_capture_receipt_sha256": sha_file(EXP / "adjacency-capture-v1/capture.json")},
        "features": {"model": MODEL, "revision": REVISION, "dimensions": DIMENSIONS,
                     "dtype": "float32", "node_relation_prompt": "title: none | text: ",
                     "query_prompt": "task: search result | query: ", "normalization": "L2",
                     "max_tokens": 256, "authorization_status": "new inference still unauthorized",
                     "binding": binding},
        "architectures": {"shared": {"layers": 2, "hidden": HIDDEN,
                          "link_objective": "directed translation score -||head+relation-tail||^2/sqrt(128)",
                                      "query_objective": "normalized projected query dot product against all entity and predicate vectors"},
                          "rgcn": {"implementation": "PyG RGCNConv", "basis_count": 4,
                                   "direction": "original subject-to-object edges only"},
                          "compgcn": {"composition": "subtraction phi(entity,relation)=entity-relation",
                                      "relation_updates": "learned linear update at each layer",
                                      "direction": "original subject-to-object edges only"}},
        "training": {"seeds": list(SEEDS), "optimizer": "AdamW", "learning_rate": 0.001,
                     "weight_decay": 0.0001, "batching": "full graph and full batch",
                     "epochs": MAX_EPOCHS, "early_stopping": {"metric": "validation MRR@10", "patience": PATIENCE},
                     "link_negatives": 10, "query_negatives": 10,
                     "negative_filter": "training-split positives only; unobserved triples are not known false",
                     "message_passing": "training edges only for transductive; all incident held-out entity edges removed for unseen-entity partition",
                     "partitions": ["transductive", "unseen_entity"], "device": "CPU only",
                     "threads": {"intra_op": 4, "inter_op": 1},
                     "resource_ceiling": {"total_training_seconds": MAX_SECONDS, "process_rss_bytes": MAX_RSS}},
        "comparison": {"primary": "+0.10 absolute Recall@10 over the stronger matched text method (BM25 or EmbeddingGemma)",
                       "structural": "positive paired Recall@10 change over native QV2 source-witnessed retrieval, which receives the same raw question text; structured adjacency is reported as an oracle ceiling, not a pass threshold",
                       "uncertainty": "paired bootstrap 95% interval on test query groups; lower bound must exceed zero",
                       "two_hop_path_reporting": "measure endpoint rank only when the retrieved candidate can be attached to the exact source-quads path; query-structure traversal is an oracle path source, not a learned path score",
                       "regressions": "report per-language, direction, depth, exact-IRI, scope, no-match and source-witness outcomes; no scope/direction/identifier safety regression",
                       "candidate_generation": "record full-pool recall before any shared-pool reranking; entity questions rank all entities and predicate questions rank all 84 predicates, without cross-role competition"},
        "judgments": "Agent-authored, source-checked development references only; no expert gold or independent semantic claim.",
        "limitations": ["EmbeddingGemma Wikidata feature vectors have not been generated.",
                        "The test split has 28 relevant questions, including only four two-hop queries.",
                        "The deterministic adjacency result uses structured query hints and is an oracle, not a natural-language baseline.",
                        "No unseen-entity results exist until the separately frozen node-disjoint run completes."],
        "implementation_sha256": implementation,
        "authorization": {"feature_inference": "requires approval bound to model/dataset/question hashes; local model assets only",
                          "full_training": "requires approval bound to this run-manifest hash, feature-manifest hash, and read-only preflight receipt",
                          "no_training_or_model_download_performed": True},
    }
    write(out, config)
    return {"path": str(out), "sha256": sha_file(out), "status": config["status"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--out", type=Path, default=EXP / "experiment-manifest.json")
    freeze.add_argument("--baseline-score", type=Path, default=EXP / "baseline-score-v2")
    freeze.add_argument("--feature-manifest", type=Path)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--out", type=Path, required=True)
    feature = sub.add_parser("features")
    feature.add_argument("--experiment-dir", type=Path, default=EXP)
    feature.add_argument("--model-dir", type=Path, required=True)
    feature.add_argument("--owner-authorization", type=Path, required=True)
    feature.add_argument("--out", type=Path, required=True)
    train = sub.add_parser("train")
    train.add_argument("--experiment-dir", type=Path, default=EXP)
    train.add_argument("--run-manifest", type=Path, default=EXP / "experiment-manifest.json")
    train.add_argument("--features", type=Path, required=True)
    train.add_argument("--feature-manifest", type=Path, required=True)
    train.add_argument("--preflight", type=Path, required=True)
    train.add_argument("--owner-authorization", type=Path, required=True)
    train.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            result = freeze_manifest(args.out, args.baseline_score, args.feature_manifest)
        elif args.command == "preflight":
            result = make_preflight(args.out)
        elif args.command == "features":
            result = make_features(args.experiment_dir, args.model_dir, args.owner_authorization, args.out)
        else:
            result = run_training(args.experiment_dir, args.run_manifest, args.features,
                                  args.feature_manifest, args.preflight,
                                  args.owner_authorization, args.out)
    except Exception as error:
        if args.command == "train" and args.out.exists():
            write(args.out / "failure.json", {"version": "rgcn-compgcn-v2-run-failure",
                  "error_type": type(error).__name__, "error": str(error),
                  "training_not_reported_as_success": True})
        raise
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
