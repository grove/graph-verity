#!/usr/bin/env python3
"""Frozen, authorization-gated R-GCN/CompGCN direction and alignment study."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import sys
import tempfile
import time

import numpy as np
try:
    import torch
except ImportError:  # Preprocessing and manifest preparation remain model-free.
    torch = None

import rgcn_compgcn_alignment as aligned
import rgcn_compgcn_directional as directional
import rgcn_compgcn_models as models
import rgcn_compgcn_run_v2 as runner
import rgcn_compgcn_v2 as benchmark


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments/rgcn-compgcn-v2/wikidata-relations-v1"
STUDY = EXP / "aligned-v2"
EXPORT = ROOT / "experiments/rgcn-compgcn-v1/wikidata-norway-org-v1/rdf-to-gnn-v1"
BASE_FEATURES = EXP / "embeddinggemma-features.npz"
BASE_FEATURE_MANIFEST = EXP / "embeddinggemma-features.manifest.json"
BASE_RUN_MANIFEST = EXP / "experiment-manifest-final-v3.json"
BASELINE_DIR = EXP / "baseline-score-v5"
MODEL = "google/embeddinggemma-2"
REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"
SEEDS = (117, 118, 119)
HIDDEN = 128
MAX_EPOCHS = 100
PATIENCE = 10
RELATION_SAMPLE_CAP = 32
MAX_SECONDS = 6 * 60 * 60
MAX_RSS = 18 * 1024**3
RSS_WARNING = 12 * 1024**3
FEATURE_MIN_AVAILABLE = 21_000_000_000
FEATURE_MAX_SECONDS = 30 * 60
FEATURE_MAX_RSS = 6 * 1024**3
FEATURE_BATCH = 8
PREREG_VERSION = "rgcn-compgcn-aligned-v2-preregistration"
FINAL_VERSION = "rgcn-compgcn-aligned-v2-final-freeze"
PREREG_NAME = "experiment-manifest-aligned-v2.json"
FINAL_NAME = "experiment-manifest-final-aligned-v2.json"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def read(path: Path):
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def feature_texts(directional_relations: list[dict]) -> list[dict]:
    rows = []
    for relation in directional_relations:
        texts = relation["description_texts"]
        parts = [f"{language}: {texts[language]}" for language in ("en", "no") if texts.get(language)]
        if not parts:
            raise ValueError(f"No source label is available for predicate {relation['predicate_iri']}")
        rows.append({"relation_id": relation["relation_id"], "predicate_id": relation["predicate_id"],
                     "predicate_iri": relation["predicate_iri"], "direction": relation["direction"],
                     "text": "title: none | text: " + "; ".join(parts),
                     "origin": relation["description_origin"],
                     "review_status": relation["review_status"]})
    if [row["relation_id"] for row in rows] != list(range(len(rows))):
        raise ValueError("Directional relation texts must follow the frozen relation ID order")
    return rows


def prepare(out: Path) -> dict:
    """Build deterministic derived adjacency, vocabulary, prompts, and preregistration."""
    prereg_path = out / PREREG_NAME
    if prereg_path.exists() or (out / "directional-export-v1").exists():
        raise ValueError("Aligned experiment version exists; choose a new version directory")
    out.mkdir(parents=True, exist_ok=True)
    directional_dir = out / "directional-export-v1"
    directional_manifest = directional.build(EXPORT, directional_dir)
    relation_text_rows = feature_texts(read_jsonl(directional_dir / "directional-relations.jsonl"))
    write_jsonl(out / "directional-feature-inputs.jsonl", relation_text_rows)
    implementation = {name: sha_file(ROOT / name) for name in (
        "tools/rgcn_compgcn_directional.py", "tools/rgcn_compgcn_alignment.py",
        "tools/rgcn_compgcn_aligned_run_v1.py", "tools/rgcn_compgcn_models.py",
        "tools/rgcn_compgcn_run_v2.py", "tools/rgcn_compgcn_v2.py",
        "tools/embedding_experiment.py", "benchmarks/embeddinggemma/manifest.json",
        "benchmarks/embeddinggemma/upstream.json",
        "benchmarks/embeddinggemma/parity-inputs.json", "benchmarks/retrieval/manifest.json",
        "tools/embedding-requirements.txt",
        "experiments/rgcn-compgcn-v2/requirements-gnn.lock",
        "experiments/rgcn-compgcn-v2/python-version.txt",
        "tools/test_rgcn_compgcn_alignment.py", "tools/test_rgcn_compgcn_directional.py")}
    input_hashes = {name: sha_file(EXP / name) for name in
                    ("manifest.json", "questions.json", "references.json", "splits.json")}
    input_hashes.update({"dataset_manifest": sha_file(EXPORT / "manifest.json"),
                         "base_feature_archive": sha_file(BASE_FEATURES),
                         "base_feature_manifest": sha_file(BASE_FEATURE_MANIFEST),
                         "baseline_summary": sha_file(BASELINE_DIR / "summary.json"),
                         "baseline_cases": sha_file(BASELINE_DIR / "cases.jsonl"),
                         "v3_run_receipt": sha_file(EXP / "training-run-v3/run-receipt.json"),
                         "v3_posthoc_summary": sha_file(EXP / "training-run-v3/posthoc-summary-v1.json"),
                         "directional_export_manifest": sha_file(directional_dir / "manifest.json"),
                         "directional_feature_inputs": sha_file(out / "directional-feature-inputs.jsonl")})
    operation = {"model": MODEL, "revision": REVISION, "operation": "encode generated direction-aware RDF navigation descriptions",
                 "input_count": len(relation_text_rows), "input_sha256": input_hashes["directional_feature_inputs"],
                 "output": "directional_relation_features float32 [168, 768], indexed by relation_id",
                 "prefix_already_in_input": True, "max_tokens": 256, "batch_size": FEATURE_BATCH,
                 "device": "cpu", "threads": {"intra_op": 4, "inter_op": 1},
                 "maximum_wall_seconds": FEATURE_MAX_SECONDS,
                 "maximum_process_rss_bytes": FEATURE_MAX_RSS,
                 "minimum_available_memory_bytes": FEATURE_MIN_AVAILABLE,
                 "assets_must_be_local_and_verified": True, "network_downloads": False}
    write(out / "feature-operation-v1.json", operation)
    manifest = {"version": PREREG_VERSION,
                "status": "frozen-before-new-feature-inference-or-scored-training",
                "dataset": {"manifest_sha256": input_hashes["dataset_manifest"],
                            "graph": directional_manifest["graph"], "license": directional_manifest["license"],
                            "stats": directional_manifest["stats"]},
                "benchmark": {"manifest_sha256": input_hashes["manifest.json"],
                              "questions_sha256": input_hashes["questions.json"],
                              "references_sha256": input_hashes["references.json"],
                              "splits_sha256": input_hashes["splits.json"],
                              "baseline_summary_sha256": input_hashes["baseline_summary"],
                              "baseline_cases_sha256": input_hashes["baseline_cases"]},
                "historical_v3": {"run_manifest_sha256": sha_file(BASE_RUN_MANIFEST),
                                  "run_receipt_sha256": input_hashes["v3_run_receipt"],
                                  "posthoc_summary_sha256": input_hashes["v3_posthoc_summary"]},
                "model": {"id": MODEL, "revision": REVISION,
                          "license": "Apache-2.0 per the pinned upstream metadata; verify exact source at inference"},
                "features": {"base_archive_sha256": input_hashes["base_feature_archive"],
                             "base_manifest_sha256": input_hashes["base_feature_manifest"],
                             "new_relation_feature_operation_sha256": sha_file(out / "feature-operation-v1.json"),
                             "new_relation_features": "await separately authorized inference"},
                "ablations": [
                    {"id": "A", "name": "historical baseline", "action": "reuse v3 receipt and predictions; no retraining"},
                    {"id": "B", "name": "explicit inverse navigation edges", "action": "distinct forward/reverse relation IDs; duplicate v3 predicate vectors"},
                    {"id": "C", "name": "bilingual relation navigation text", "action": "B plus encoded generated bilingual navigation descriptions"},
                    {"id": "D", "name": "balanced and direction-contrastive training", "action": "C plus per-predicate source-edge cap with both navigation directions retained, and source-backed wrong-direction negatives"},
                    {"id": "E", "name": "explicit question-to-graph alignment", "action": "D plus anchor, predicate/direction, and answer alignment losses"}],
                "fitted_variants": ["B", "C", "D", "E"],
                "architectures": ["rgcn", "compgcn"],
                "partitions": ["transductive", "unseen_entity"],
                "seeds": list(SEEDS), "fit_count": 4 * 2 * 2 * len(SEEDS),
                "fit_execution": {"concurrency": 1, "order": "sequential"},
                "training": {"layers": 2, "hidden_dimensions": HIDDEN, "optimizer": "AdamW",
                             "learning_rate": 0.001, "weight_decay": 0.0001,
                             "epochs": MAX_EPOCHS, "patience": PATIENCE,
                             "link_negatives": 10, "query_negatives": 10,
                             "relation_balanced_source_edges_per_predicate_cap": RELATION_SAMPLE_CAP,
                             "device": "CPU only", "threads": {"intra_op": 4, "inter_op": 1},
                             "maximum_seconds": MAX_SECONDS, "minimum_available_memory_bytes": MAX_RSS,
                             "maximum_process_tree_rss_bytes": MAX_RSS, "early_warning_rss_bytes": RSS_WARNING,
                             "safeguard_scope": "Observational host/process sampling; not OS-level isolation."},
                "negative_sampling": {"query_candidates": "sampled ranking distractors; never RDF false-fact claims",
                    "link_prediction": "10 graph-local unobserved corruptions; filter all source-known triples to avoid false negatives",
                    "known_triple_filter_use": "sampling exclusion only; held-out edges never enter message-passing tensors",
                    "unknown_relation_truth": "open-world; not asserted absent"},
                "metrics": {"primary": ["Recall@10", "MRR@10", "nDCG@10"],
                            "secondary": ["Recall@1", "Recall@5", "direction accuracy",
                                          "anchor accuracy", "source-witness coverage", "no-match suggestions",
                                          "source-witnessed path Recall@1/5/10"],
                            "required_views": ["gold_free_end_to_end", "oracle_assisted_structural", "QV2_shared_pool_reranking",
                                               "English", "Norwegian", "forward", "reverse", "two_hop", "unseen_entity"],
                            "predicted_path_candidates": {"source": "authorized graph adjacency only",
                                "top_anchor_candidates": 5, "top_relation_direction_candidates": 10,
                                "maximum_hops": 2, "rank_score": "anchor + relation-direction per step + endpoint score",
                                "direction_and_source_quad_preserved": True},
                            "promotion_criterion_historical": "+0.10 absolute Recall@10 over the strongest matched text baseline and positive paired Recall@10 change over QV2; uncertainty is descriptive, not an added threshold",
                            "failure_conditions": ["resource safeguard stop", "six-hour limit", "non-finite loss or validation score", "integrity or leakage check failure"],
                            "test_tuning": False, "references": "agent-authored and source-checked; not expert gold"},
                "input_sha256": input_hashes, "implementation_sha256": implementation,
                "protocol_sha256": {name: sha_file(out / name) for name in ("README.md", "DIAGNOSIS.md")},
                "safety": {"inverse_edges_are_rdf_facts": False, "predictions_are_source_evidence": False,
                           "cross_graph_scope": False, "automatic_execution": False},
                "authorization": {"new_embedding_inference": "separate authorization required before weights load",
                                  "scored_training": "separate authorization required after final feature and run hashes"}}
    write(prereg_path, manifest)
    return manifest


def _validate_source_inputs(manifest: dict, manifest_path: Path) -> None:
    if manifest.get("version") not in {PREREG_VERSION, FINAL_VERSION}:
        raise ValueError("Unexpected aligned experiment manifest")
    for name, digest in manifest["input_sha256"].items():
        if name == "dataset_manifest":
            path = EXPORT / "manifest.json"
        elif name == "base_feature_archive":
            path = BASE_FEATURES
        elif name == "base_feature_manifest":
            path = BASE_FEATURE_MANIFEST
        elif name == "baseline_summary":
            path = BASELINE_DIR / "summary.json"
        elif name == "baseline_cases":
            path = BASELINE_DIR / "cases.jsonl"
        elif name == "v3_run_receipt":
            path = EXP / "training-run-v3/run-receipt.json"
        elif name == "v3_posthoc_summary":
            path = EXP / "training-run-v3/posthoc-summary-v1.json"
        elif name == "directional_export_manifest":
            path = manifest_path.parent / "directional-export-v1/manifest.json"
        elif name == "directional_feature_inputs":
            path = manifest_path.parent / "directional-feature-inputs.jsonl"
        else:
            path = EXP / name
        if sha_file(path) != digest:
            raise ValueError(f"Frozen aligned input changed: {name}")
    for name, digest in manifest["implementation_sha256"].items():
        if sha_file(ROOT / name) != digest:
            raise ValueError(f"Aligned implementation changed after preregistration: {name}")
    for name, digest in manifest["protocol_sha256"].items():
        if sha_file(manifest_path.parent / name) != digest:
            raise ValueError(f"Aligned protocol document changed after preregistration: {name}")
    if sha_file(manifest_path.parent / "feature-operation-v1.json") != \
            manifest["features"]["new_relation_feature_operation_sha256"]:
        raise ValueError("Frozen EmbeddingGemma feature operation changed")
    if manifest["version"] == FINAL_VERSION:
        features = manifest["features"]
        if (sha_file(manifest_path.parent / "directional-relation-features.npz") !=
                features["directional_feature_archive_sha256"] or
                sha_file(manifest_path.parent / "directional-relation-features.manifest.json") !=
                features["directional_feature_manifest_sha256"]):
            raise ValueError("Frozen directional EmbeddingGemma features changed")


def make_readonly_preflight(manifest_path: Path, out: Path,
                            asset_verification_path: Path | None = None) -> dict:
    manifest = read(manifest_path)
    _validate_source_inputs(manifest, manifest_path)
    if out.exists():
        raise ValueError("Preflight exists; choose a fresh receipt path")
    with tempfile.TemporaryDirectory(prefix="aligned-preflight-") as temp:
        old_receipt_path = Path(temp) / "host-preflight.json"
        base = runner.make_preflight(old_receipt_path, EXP / "experiment-manifest-final.json",
                                     BASE_FEATURES, BASE_FEATURE_MANIFEST)
        record = read(old_receipt_path)
    record["aligned_experiment_manifest_sha256"] = sha_file(manifest_path)
    record["directional_export_manifest_sha256"] = manifest["input_sha256"]["directional_export_manifest"]
    record["feature_operation_sha256"] = manifest["features"]["new_relation_feature_operation_sha256"]
    if asset_verification_path is not None:
        asset_report = read(asset_verification_path)
        if (asset_report.get("aligned_experiment_manifest_sha256") != sha_file(manifest_path) or
                asset_report.get("identity", {}).get("model") != MODEL or
                asset_report.get("identity", {}).get("revision") != REVISION):
            raise ValueError("Asset verification receipt is not bound to this preregistration")
        record["asset_verification_sha256"] = sha_file(asset_verification_path)
        record["asset_set_sha256"] = asset_report["identity"]["asset_set_sha256"]
        record["embedding_runtime_sha256"] = asset_report["identity"]["runtime_sha256"]
    record["fit_execution"] = manifest["fit_execution"]
    record["aligned_fit_count"] = manifest["fit_count"]
    if manifest["version"] == FINAL_VERSION:
        record["directional_feature_archive_sha256"] = manifest["features"]["directional_feature_archive_sha256"]
        record["directional_feature_manifest_sha256"] = manifest["features"]["directional_feature_manifest_sha256"]
    record["feature_inference_assets_must_be_local"] = True
    record["authorization_scope"] = ("read-only admission for the 48-fit aligned training protocol; no training started"
        if manifest["version"] == FINAL_VERSION else
        "read-only admission for 168 EmbeddingGemma description vectors; no model assets loaded")
    record["base_preflight_status"] = base.get("status")
    write(out, record)
    return record


def require_fresh_preflight(preflight_path: Path, manifest_path: Path, *, training: bool = False,
                            asset_verification_path: Path | None = None) -> dict:
    row = read(preflight_path)
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(
            row["captured_at_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)).total_seconds()
    except Exception:
        age = math.inf
    if age < 0 or age > 30 * 60:
        raise ValueError("Preflight must be no more than 30 minutes old")
    if row.get("aligned_experiment_manifest_sha256") != sha_file(manifest_path):
        raise ValueError("Preflight is not bound to the frozen aligned experiment")
    manifest = read(manifest_path)
    if (row.get("fit_execution") != manifest["fit_execution"] or
            row.get("aligned_fit_count") != manifest["fit_count"]):
        raise ValueError("Preflight does not bind the registered sequential fit plan")
    if asset_verification_path is not None and \
            row.get("asset_verification_sha256") != sha_file(asset_verification_path):
        raise ValueError("Preflight does not bind the verified local model assets and runtime")
    expected_memory = MAX_RSS if training else FEATURE_MIN_AVAILABLE
    available = row.get("available_memory_snapshot_bytes", row.get("available_memory_bytes"))
    if (row.get("status") != "pass" or not row.get("target_hardware_match") or
            not isinstance(available, int) or available < expected_memory or
            not isinstance(row.get("memory_pressure_free_percent"), int) or
            row["memory_pressure_free_percent"] <= runner.CRITICAL_FREE_PERCENT or
            row.get("swap_used_bytes") != 0 or row.get("runtime_identity", {}).get("valid") is not True):
        raise ValueError("Aligned run preflight did not pass hardware, RAM, pressure, swap, or runtime admission")
    if training and row.get("training_resource_preflight_passed") is not True:
        raise ValueError("Training resource preflight did not pass")
    if training:
        expected_limits = {"training_admission_threshold_bytes": MAX_RSS,
                           "process_tree_rss_ceiling_bytes": MAX_RSS,
                           "process_tree_rss_warning_bytes": RSS_WARNING,
                           "minimum_runtime_headroom_bytes": runner.MIN_HEADROOM,
                           "maximum_swapout_growth_bytes": runner.MAX_SWAPOUT_GROWTH,
                           "critical_memory_pressure_free_percent": runner.CRITICAL_FREE_PERCENT,
                           "resource_sample_interval_seconds": runner.RESOURCE_SAMPLE_SECONDS}
        if any(row.get(key) != value for key, value in expected_limits.items()):
            raise ValueError("Training preflight does not carry the registered resource safeguards")
    return row


def embedding_runtime_identity(model_dir: Path) -> dict:
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import embedding_experiment
    spec, upstream = embedding_experiment.verify()
    if (spec["model"] != MODEL or spec["revision"] != REVISION or
            spec["dimensions"] != 768 or upstream.get("cardData", {}).get("license") != "apache-2.0" or
            spec.get("terms", {}).get("license") != "Apache-2.0"):
        raise ValueError("Pinned EmbeddingGemma identity or declared license changed")
    assets = embedding_experiment.assets(model_dir)
    if not assets["valid"]:
        raise ValueError("Pinned EmbeddingGemma assets are missing or do not match upstream hashes")
    torch_runtime, runtime = embedding_experiment.cpu_runtime()
    expected_python = (ROOT / "experiments/rgcn-compgcn-v2/python-version.txt").read_text().strip()
    if runtime["python"].split()[0] != expected_python:
        raise ValueError(f"Embedding runtime Python must be {expected_python}")
    package_versions = {}
    failures = []
    for line in (ROOT / "tools/embedding-requirements.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        package, expected = line.split("==", 1)
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        package_versions[package] = actual
        if actual != expected:
            failures.append(f"{package}: expected {expected}, got {actual}")
    if failures:
        raise ValueError("Embedding runtime does not match its pinned requirements: " + "; ".join(failures))
    if (torch_runtime.get_num_threads(), torch_runtime.get_num_interop_threads()) != (4, 1):
        raise ValueError("Embedding runtime thread settings differ from the registered CPU operation")
    return {"model": spec["model"], "revision": spec["revision"], "license": "Apache-2.0",
            "upstream_license": upstream["cardData"]["license"], "assets": assets,
            "asset_set_sha256": sha_bytes(json.dumps(assets["sha256"], sort_keys=True).encode()),
            "runtime": runtime,
            "runtime_sha256": sha_bytes(json.dumps(runtime, sort_keys=True).encode()),
            "locked_package_versions": package_versions,
            "requirements_sha256": sha_file(ROOT / "tools/embedding-requirements.txt"),
            "upstream_metadata_sha256": sha_file(ROOT / "benchmarks/embeddinggemma/upstream.json"),
            "model_manifest_sha256": sha_file(ROOT / "benchmarks/embeddinggemma/manifest.json"),
            "model_weights_loaded": False, "inference_performed": False, "downloads_disabled": True}


def reusable_feature_runtime(embedding_experiment, identity: dict):
    torch_runtime, runtime = embedding_experiment.cpu_runtime()
    actual_threads = (torch_runtime.get_num_threads(), torch_runtime.get_num_interop_threads())
    if actual_threads != (4, 1):
        raise RuntimeError(f"Aligned feature runtime requires 4/1 CPU threads, got {actual_threads}")
    runtime_sha256 = sha_bytes(json.dumps(runtime, sort_keys=True).encode())
    if runtime_sha256 != identity["runtime_sha256"]:
        raise RuntimeError("Reused feature runtime differs from the verified runtime identity")
    return torch_runtime, runtime


def registered_feature_output(manifest: dict, out: Path) -> str:
    expected = manifest["features"].get("new_relation_feature_output")
    try:
        actual = out.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("Feature output must remain inside the repository workspace") from error
    if actual != expected:
        raise ValueError(f"Feature output differs from the frozen path: expected {expected}, got {actual}")
    return actual


def verify_model_assets(manifest_path: Path, model_dir: Path, out: Path) -> dict:
    manifest = read(manifest_path)
    _validate_source_inputs(manifest, manifest_path)
    if manifest["version"] != PREREG_VERSION:
        raise ValueError("Verify local model assets against the pre-inference preregistration")
    if out.exists():
        raise ValueError("Asset verification receipt exists; choose a new path")
    identity = embedding_runtime_identity(model_dir)
    result = {"version": "rgcn-compgcn-aligned-v2-model-asset-verification",
              "aligned_experiment_manifest_sha256": sha_file(manifest_path),
              "dataset_manifest_sha256": manifest["dataset"]["manifest_sha256"],
              "benchmark_manifest_sha256": manifest["benchmark"]["manifest_sha256"],
              "feature_operation_sha256": manifest["features"]["new_relation_feature_operation_sha256"],
              "model_dir": str(model_dir.resolve()), "identity": identity,
              "status": "verified-without-loading-weights-or-running-inference"}
    write(out, result)
    return result


def generate_relation_features(manifest_path: Path, preflight_path: Path,
                               asset_verification_path: Path, authorization_path: Path,
                               model_dir: Path, out: Path) -> dict:
    manifest = read(manifest_path)
    _validate_source_inputs(manifest, manifest_path)
    require_fresh_preflight(preflight_path, manifest_path,
                            asset_verification_path=asset_verification_path)
    operation_path = manifest_path.parent / "feature-operation-v1.json"
    inputs_path = manifest_path.parent / "directional-feature-inputs.jsonl"
    expected = {"model": MODEL, "revision": REVISION,
                "dataset_manifest_sha256": manifest["dataset"]["manifest_sha256"],
                "benchmark_manifest_sha256": manifest["benchmark"]["manifest_sha256"],
                "questions_sha256": manifest["benchmark"]["questions_sha256"],
                "directional_export_manifest_sha256": sha_file(manifest_path.parent / "directional-export-v1/manifest.json"),
                "feature_inputs_sha256": sha_file(inputs_path),
                "feature_operation_sha256": sha_file(operation_path),
                "feature_output_path": registered_feature_output(manifest, out),
                "aligned_experiment_manifest_sha256": sha_file(manifest_path),
                "preflight_sha256": sha_file(preflight_path),
                "asset_verification_sha256": sha_file(asset_verification_path)}
    asset_verification = read(asset_verification_path)
    verified_identity = asset_verification.get("identity", {})
    if (asset_verification.get("status") != "verified-without-loading-weights-or-running-inference" or
            asset_verification.get("aligned_experiment_manifest_sha256") != sha_file(manifest_path) or
            asset_verification.get("model_dir") != str(model_dir.resolve()) or
            verified_identity.get("model") != MODEL or verified_identity.get("revision") != REVISION):
        raise ValueError("Model asset verification is not bound to this run or local asset path")
    expected["asset_set_sha256"] = verified_identity["asset_set_sha256"]
    expected["embedding_runtime_sha256"] = verified_identity["runtime_sha256"]
    runner.approval(authorization_path, "allow_aligned_embeddinggemma_inference", expected)
    if out.exists() or out.with_suffix(".manifest.json").exists():
        raise ValueError("Feature output exists; choose a new versioned path")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import embedding_experiment
    identity = embedding_runtime_identity(model_dir)
    if (identity["asset_set_sha256"] != verified_identity["asset_set_sha256"] or
            identity["runtime_sha256"] != verified_identity["runtime_sha256"]):
        raise ValueError("Local model assets or EmbeddingGemma runtime changed after authorization")
    spec, _ = embedding_experiment.verify()
    assets = identity["assets"]
    torch_runtime, runtime = reusable_feature_runtime(embedding_experiment, identity)
    encoder = embedding_experiment.Encoder(model_dir, torch_runtime, spec)
    text_rows = read_jsonl(inputs_path)
    texts = [row["text"] for row in text_rows]
    started = time.perf_counter()
    vectors = []
    for index in range(0, len(texts), FEATURE_BATCH):
        if time.perf_counter() - started > FEATURE_MAX_SECONDS:
            raise RuntimeError("Aligned relation-feature inference exceeded its 30-minute budget")
        if runner.process_peak_rss_bytes() > FEATURE_MAX_RSS:
            raise RuntimeError("Aligned relation-feature inference exceeded its 6 GiB RSS budget")
        vectors.append(encoder.encode(texts[index:index + FEATURE_BATCH]).cpu().numpy())
    matrix = np.concatenate(vectors).astype(np.float32)
    if matrix.shape != (len(text_rows), 768) or not np.isfinite(matrix).all():
        raise ValueError("EmbeddingGemma returned invalid directional relation features")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("xb") as stream:
        np.savez_compressed(stream, relation_features=matrix,
                            relation_ids=np.asarray([row["relation_id"] for row in text_rows], dtype=np.int64))
    result = {"version": "rgcn-compgcn-directional-features-v2", **expected,
              "operation": read(operation_path), "runtime": runtime,
              "asset_identity": assets, "feature_file": out.name,
              "asset_verification_sha256": sha_file(asset_verification_path),
              "feature_file_sha256": sha_file(out), "count": len(text_rows),
              "shape": list(matrix.shape), "dtype": str(matrix.dtype),
              "normalization": "EmbeddingGemma encoder L2-normalized output",
              "inference_wall_seconds": time.perf_counter() - started,
              "authorization_sha256": sha_file(authorization_path)}
    write(out.with_suffix(".manifest.json"), result)
    return result


def finalize_manifest(prereg_path: Path, feature_file: Path, feature_manifest_path: Path,
                      out: Path) -> dict:
    prereg = read(prereg_path)
    _validate_source_inputs(prereg, prereg_path)
    feature_manifest = read(feature_manifest_path)
    if (feature_manifest.get("feature_file_sha256") != sha_file(feature_file) or
            feature_manifest.get("aligned_experiment_manifest_sha256") != sha_file(prereg_path) or
            feature_manifest.get("feature_operation_sha256") != prereg["features"]["new_relation_feature_operation_sha256"]):
        raise ValueError("Directional feature archive does not match the frozen feature operation")
    if out.exists():
        raise ValueError("Final experiment manifest exists; choose a new versioned path")
    final = dict(prereg)
    final["version"] = FINAL_VERSION
    final["preregistration_manifest_sha256"] = sha_file(prereg_path)
    final["features"] = {**prereg["features"],
                         "directional_feature_archive_sha256": sha_file(feature_file),
                         "directional_feature_manifest_sha256": sha_file(feature_manifest_path),
                         "directional_feature_shape": feature_manifest["shape"]}
    final["status"] = "frozen-before-scored-training"
    write(out, final)
    return final


def directional_id(predicate_iri: str, direction: str, predicate_ids: dict[str, int]) -> int:
    if direction not in {"forward", "reverse"}:
        raise ValueError(f"Unknown RDF navigation direction: {direction}")
    return 2 * predicate_ids[predicate_iri] + (direction == "reverse")


def question_targets(question: dict, reference: dict, node_ids: dict[str, int],
                     predicate_ids: dict[str, int]) -> dict:
    traversal = question["traversal"]
    steps = traversal.get("steps", [])
    if question["role"] == "predicate":
        predicate = reference["relevant"][0]["iri"]
        anchor_iri = traversal["subject_iri"]
        steps = [{"predicate": predicate, "direction": "forward"}]
    else:
        anchor_iri = traversal["start_iri"]
    return {"anchor_id": node_ids[anchor_iri],
            "relation_direction_ids": [directional_id(step["predicate"], step["direction"], predicate_ids)
                                       for step in steps],
            "target_id": (node_ids[reference["relevant"][0]["iri"]]
                          if question["role"] == "entity" else predicate_ids[reference["relevant"][0]["iri"]]),
            "role": question["role"]}


def make_query_examples(qids: list[str], questions: list[dict], references: list[dict],
                        query_features: np.ndarray, node_ids: dict[str, int],
                        predicate_ids: dict[str, int], node_count: int, predicate_count: int,
                        *, seed: int, excluded_node_iris: set[str],
                        hard_negatives: bool) -> list[dict]:
    by_q = {row["id"]: row for row in questions}
    by_ref = {row["id"]: row for row in references}
    feature_rows = {row["id"]: index for index, row in enumerate(questions)}
    rng = random.Random(seed)
    examples = []
    for qid in qids:
        question, ref = by_q[qid], by_ref[qid]
        if ref["status"] != "relevant" or len(ref["relevant"]) != 1:
            continue
        target = question_targets(question, ref, node_ids, predicate_ids)
        is_entity = target["role"] == "entity"
        target_candidate = (target["target_id"] if is_entity else
                            node_count + 2 * target["target_id"])
        retrieval_candidate = (target["target_id"] if is_entity else
                               node_count + target["target_id"])
        if is_entity:
            excluded = {node_ids[iri] for iri in excluded_node_iris if iri in node_ids}
            pool = [index for index in range(node_count)
                    if index != target_candidate and index not in excluded]
        else:
            pool = [node_count + index for index in range(2 * predicate_count)
                    if node_count + index != target_candidate]
        contrastives = []
        hard_candidate = -1
        if hard_negatives:
            hard = aligned.direction_hard_negative(question, ref,
                                                   node_ids, predicate_ids)
            if hard and hard["candidate_id"] != target["target_id"]:
                candidate = (hard["candidate_id"] if is_entity else
                             node_count + 2 * hard["candidate_id"])
                if candidate in pool:
                    contrastives.append(candidate)
                    hard_candidate = candidate
            if not is_entity:
                inverse_id = node_count + 2 * target["target_id"] + 1
                if inverse_id in pool:
                    contrastives.append(inverse_id)
        contrastives = list(dict.fromkeys(contrastives))[:10]
        remaining = [candidate for candidate in pool if candidate not in contrastives]
        need = max(0, 10 - len(contrastives))
        if len(remaining) < need:
            raise ValueError("Frozen role candidate pool is too small for query negatives")
        negatives = contrastives + rng.sample(remaining, need)
        examples.append({"id": qid, "feature_row": feature_rows[qid],
                         "question": question, "reference": ref, **target,
                         "target_candidate_id": target_candidate,
                         "retrieval_candidate_id": retrieval_candidate,
                         "negative_candidate_ids": negatives,
                         "hard_negative_candidate_id": hard_candidate})
    return examples


def base_candidate_scores(model, entities, relations, query_features, node_count: int,
                          predicate_count: int) -> tuple:
    raw = model.score_queries(entities, relations, query_features)
    entity_scores = raw[:, :node_count]
    directional_scores = raw[:, node_count:]
    predicate_scores = aligned.pooled_predicate_scores(directional_scores, predicate_count)
    answer_scores = torch.cat((entity_scores, predicate_scores), dim=-1)
    anchor_scores = torch.nn.functional.normalize(model.query_input(query_features), dim=-1) @ \
                    torch.nn.functional.normalize(entities, dim=-1).T
    return answer_scores, directional_scores, anchor_scores


def alignment_candidate_scores(head, entities, relations, query_features,
                               node_count: int, predicate_count: int) -> tuple:
    outputs = head(query_features, entities, relations)
    predicate_scores = aligned.pooled_predicate_scores(
        outputs["relation_direction_logits"], predicate_count)
    answer_scores = torch.cat((outputs["entity_answer_logits"], predicate_scores), dim=-1)
    return answer_scores, outputs["relation_direction_logits"], outputs["anchor_logits"], outputs


def _triple_loss(model, node_features, relation_features, edge_index, edge_types,
                 triples, negative_tails):
    entities, relations = model(node_features, relation_features, edge_index, edge_types)
    heads, relation_ids, tails = triples.T
    positive = model.score_tails(entities, relations, heads, relation_ids, tails[:, None]).squeeze(1)
    negative = model.score_tails(entities, relations, heads, relation_ids, negative_tails)
    return entities, relations, torch.nn.functional.softplus(-positive).mean() + \
           torch.nn.functional.softplus(negative).mean()


def _validation_mrr(model, aligner, partition_name: str, examples: list[dict],
                    node_features, relation_features, edge_index, edge_types,
                    query_features, node_count: int, predicate_count: int) -> float:
    model.eval()
    if aligner:
        aligner.eval()
    rows = []
    with torch.no_grad():
        entities, relations = model(node_features, relation_features, edge_index, edge_types)
        qfeatures = torch.as_tensor(query_features[[row["feature_row"] for row in examples]], dtype=torch.float32)
        if aligner:
            scores, _, _, _ = alignment_candidate_scores(aligner, entities, relations, qfeatures,
                                                          node_count, predicate_count)
        else:
            scores, _, _ = base_candidate_scores(model, entities, relations, qfeatures,
                                                 node_count, predicate_count)
        for index, example in enumerate(examples):
            candidates = range(node_count) if example["role"] == "entity" else range(node_count, node_count + predicate_count)
            order = sorted(candidates, key=lambda item: (-float(scores[index, item]), item))
            rank = order.index(example["retrieval_candidate_id"]) + 1
            rows.append(1.0 / rank if rank <= 10 else 0.0)
    return sum(rows) / len(rows) if rows else 0.0


def fit_aligned_encoder(encoder_factory, training_args: dict, validation_mrr,
                        *, seed: int, resource_guard=None) -> tuple:
    """Train the graph encoder and explicit alignment head for variant E only."""
    models.seed_everything(seed)
    model = encoder_factory()
    head = aligned.QuestionGraphAlignmentHead(training_args["query_width"], HIDDEN)
    optimizer = torch.optim.AdamW([*model.parameters(), *head.parameters()], lr=0.001, weight_decay=0.0001)
    best, best_states, stale, history = float("-inf"), None, 0, []
    for epoch in range(MAX_EPOCHS):
        started = time.perf_counter()
        model.train(); head.train()
        optimizer.zero_grad(set_to_none=True)
        entities, relations, link_loss = _triple_loss(
            model, training_args["node_features"], training_args["relation_features"],
            training_args["edge_index"], training_args["edge_types"],
            training_args["positive_triples"], training_args["negative_tail_ids"])
        outputs = head(training_args["query_features"], entities, relations)
        loss = link_loss + aligned.alignment_loss(
            outputs, training_args["answer_targets"], training_args["anchor_targets"],
            training_args["relation_direction_targets"], training_args["roles"],
            training_args["predicate_count"], training_args["hard_negative_ids"],
            training_args["query_negative_ids"])
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("Aligned training loss became non-finite")
        loss.backward()
        torch.nn.utils.clip_grad_norm_([*model.parameters(), *head.parameters()], 1.0)
        optimizer.step()
        score = float(validation_mrr(model, head))
        if not math.isfinite(score):
            raise RuntimeError("Aligned validation MRR became non-finite")
        row = {"epoch": epoch + 1, "loss": float(loss.detach()),
               "validation_mrr@10": score, "epoch_ms": (time.perf_counter() - started) * 1000}
        history.append(row)
        if resource_guard:
            resource_guard(epoch + 1, row)
        if score > best:
            best, stale = score, 0
            best_states = ({name: value.detach().clone() for name, value in model.state_dict().items()},
                           {name: value.detach().clone() for name, value in head.state_dict().items()})
        else:
            stale += 1
            if stale >= PATIENCE:
                break
    if best_states:
        model.load_state_dict(best_states[0]); head.load_state_dict(best_states[1])
    return model, head, {"seed": seed, "best_validation_mrr@10": best,
                         "epochs": len(history), "history": history}


def load_scope_support() -> dict[str, set[tuple[str, str]]]:
    support = defaultdict(set)
    capture = EXP / "adjacency-capture-v1"
    for name in ("one-hop.jsonl", "two-hop.jsonl"):
        for row in read_jsonl(capture / name):
            support[row["id"]].update((candidate["graph"], candidate["iri"])
                                       for candidate in row["candidates"])
    return support


def load_twohop_paths() -> dict[str, list[dict]]:
    return {row["id"]: row["candidates"] for row in
            read_jsonl(EXP / "adjacency-capture-v1/two-hop.jsonl")}


def question_direction_labels(question: dict, reference: dict, predicate_ids: dict[str, int]) -> list[int]:
    steps = question["traversal"].get("steps", [])
    if question["role"] == "predicate":
        steps = [{"predicate": reference["relevant"][0]["iri"], "direction": "forward"}]
    return [directional_id(item["predicate"], item["direction"], predicate_ids) for item in steps]


def metric_row(question: dict, reference: dict, ranked: list[tuple[str, str]],
               support: dict[str, set[tuple[str, str]]]) -> dict:
    relevant = {(item["graph"], item["iri"]) for item in reference["relevant"]}
    metrics = benchmark.v1.rank_metrics(relevant, ranked)
    top10 = set(ranked[:10])
    return {"id": question["id"], "split": question["split"], "query_group": question["query_group"],
            "language": question["language"], "family": question["family"], "status": reference["status"],
            "relevant": [list(item) for item in sorted(relevant)], "ranked": ranked[:50],
            "metrics": metrics, "candidate_pool_recall": (len(set(ranked) & relevant) / len(relevant) if relevant else None),
            "candidate_count": len(ranked),
            "top10_source_witness_coverage": len(top10 & support.get(question["id"], set())) / min(10, len(ranked)) if ranked else 0.0,
            "no_match_top10_suggestion": reference["status"] == "no_match" and bool(ranked[:10]),
            "source_path_metrics": None,
            "predictions_are_hypotheses_not_RDF_evidence": True}


def summarize_partition(rows: list[dict]) -> dict:
    relevant = [row for row in rows if row["status"] == "relevant"]
    metrics = ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10")
    def group(values):
        return {"n": len(values), **{key: (sum(row["metrics"][key] for row in values) / len(values)
                                            if values else None) for key in metrics}}
    result = {"overall": group(relevant), "strata": {}, "outcomes": {}}
    for language in ("en", "no"):
        result["strata"][f"language/{language}"] = group([row for row in relevant if row["language"] == language])
    for family in sorted({row["family"] for row in relevant}):
        result["strata"][f"family/{family}"] = group([row for row in relevant if row["family"] == family])
    for status in ("ambiguous", "no_match"):
        subset = [row for row in rows if row["status"] == status]
        result["outcomes"][status] = {"n": len(subset), "candidate_returns": sum(bool(row["ranked"]) for row in subset),
                                       "top10_suggestions": sum(row["no_match_top10_suggestion"] for row in subset)}
    result["source_witness_coverage"] = {"n": len(rows), "mean": sum(row["top10_source_witness_coverage"] for row in rows) / len(rows) if rows else None}
    directions = [row.get("direction_diagnostics") for row in relevant if row.get("direction_diagnostics")]
    result["direction_diagnostics"] = {"n": len(directions),
        "joint_relation_direction_top1_accuracy": (sum(x["joint_relation_direction_top1_correct"] for x in directions) / len(directions) if directions else None),
        "conditional_direction_accuracy": (sum(x["direction_accuracy_conditioned_on_gold_predicate"] for x in directions
            if x["direction_accuracy_conditioned_on_gold_predicate"] is not None) /
            sum(x["direction_accuracy_conditioned_on_gold_predicate"] is not None for x in directions)
            if any(x["direction_accuracy_conditioned_on_gold_predicate"] is not None for x in directions) else None),
        "anchor_top1_accuracy": (sum(x["anchor_top1_correct"] for x in directions if x["anchor_top1_correct"] is not None) /
            sum(x["anchor_top1_correct"] is not None for x in directions)
            if any(x["anchor_top1_correct"] is not None for x in directions) else None)}
    predicted_paths = [row["predicted_path_metrics"] for row in relevant if row.get("predicted_path_metrics")]
    oracle_paths = [row["oracle_source_path_metrics"] for row in relevant if row.get("oracle_source_path_metrics")]
    def path_summary(paths):
        return {"n": len(paths), **{metric: (sum(row[metric] for row in paths) / len(paths) if paths else None)
                                     for metric in metrics}}
    result["gold_free_path_retrieval"] = path_summary(predicted_paths)
    result["oracle_assisted_source_path_diagnostic"] = path_summary(oracle_paths)
    return result


def _base_or_aligned_scores(model, head, node_features, relation_features, edge_index, edge_types,
                            query_features, node_count: int, predicate_count: int):
    entities, relations = model(node_features, relation_features, edge_index, edge_types)
    if head:
        scores, direction_scores, anchor_scores, outputs = alignment_candidate_scores(
            head, entities, relations, query_features, node_count, predicate_count)
    else:
        scores, direction_scores, anchor_scores = base_candidate_scores(
            model, entities, relations, query_features, node_count, predicate_count)
        outputs = None
    return entities, relations, scores, direction_scores, anchor_scores, outputs


def _rank_candidate_scores(question: dict, scores, candidate_ids: dict[int, tuple[str, str]],
                           node_count: int, predicate_count: int) -> list[tuple[str, str]]:
    candidates = range(node_count) if question["role"] == "entity" else range(node_count, node_count + predicate_count)
    ordered = sorted(candidates, key=lambda idx: (-float(scores[idx]), idx))
    return [candidate_ids[index] for index in ordered]


def path_id(source_quads: list[str], directions: list[str]) -> str:
    if len(source_quads) != len(directions):
        raise ValueError("Every source-witnessed path edge needs its navigation direction")
    return sha_bytes("\n".join(f"{quad}\0{direction}" for quad, direction in
                               zip(source_quads, directions)).encode())


def source_adjacency(edges: list[dict]) -> dict[int, list[dict]]:
    adjacency = defaultdict(list)
    for edge in edges:
        if edge["graph"] == benchmark.GRAPH:
            adjacency[edge["subject_id"]].append(edge)
    return {key: sorted(rows, key=lambda edge: (edge["relation_id"], edge["object_id"], edge["source_edge_id"]))
            for key, rows in adjacency.items()}


def rank_source_paths(anchor_scores, relation_scores, entity_scores,
                      adjacency: dict[int, list[dict]], nodes: list[dict], *,
                      anchor_limit: int = 5, relation_limit: int = 10,
                      path_limit: int = 50) -> list[dict]:
    """Rank graph-witnessed paths from model-predicted anchors and relation directions."""
    values = lambda tensor: tensor.detach().cpu().tolist() if hasattr(tensor, "detach") else list(tensor)
    anchor_values, relation_values, entity_values = map(values, (anchor_scores, relation_scores, entity_scores))
    anchors = sorted(range(len(anchor_values)), key=lambda item: (-anchor_values[item], item))[:anchor_limit]
    relation_ids = set(sorted(range(len(relation_values)),
                              key=lambda item: (-relation_values[item], item))[:relation_limit])
    rows = {}

    def add_path(path_edges, start_id, end_id, score):
        quads = [edge["source_quad"] for edge in path_edges]
        directions = [edge["direction"] for edge in path_edges]
        identifier = path_id(quads, directions)
        rows.setdefault(identifier, {"path_id": identifier, "graph": benchmark.GRAPH,
            "start_iri": nodes[start_id]["iri"], "end_iri": nodes[end_id]["iri"],
            "hop_count": len(path_edges), "source_quads": quads, "directions": directions,
            "relation_direction_ids": [edge["relation_id"] for edge in path_edges],
            "source_witnessed": True, "score": float(score)})

    for anchor in anchors:
        first_score = anchor_values[anchor]
        for first in adjacency.get(anchor, []):
            if first["relation_id"] not in relation_ids:
                continue
            first_total = first_score + relation_values[first["relation_id"]]
            endpoint = first["object_id"]
            add_path([first], anchor, endpoint, first_total + entity_values[endpoint])
            for second in adjacency.get(endpoint, []):
                if second["relation_id"] not in relation_ids:
                    continue
                total = first_total + relation_values[second["relation_id"]]
                end_id = second["object_id"]
                add_path([first, second], anchor, end_id, total + entity_values[end_id])
    return sorted(rows.values(), key=lambda row: (-row["score"], row["path_id"]))[:path_limit]


def path_retrieval_metrics(question: dict, reference: dict, ranked_paths: list[dict]) -> dict | None:
    if (question["family"] != "two_hop_path" or reference["status"] != "relevant" or
            len(reference["relevant"]) != 1):
        return None
    directions = [step["direction"] for step in question["traversal"]["steps"]]
    expected = {path_id(witness["source_quads"], directions)
                for witness in reference["witnesses"]
                if len(witness["source_quads"]) == len(directions)}
    ranked = [row["path_id"] for row in ranked_paths if row["hop_count"] == len(directions)]
    return {**benchmark.v1.rank_metrics(expected, ranked), "expected_path_count": len(expected),
            "candidate_path_count": len(ranked)}


def build_alignment_tensors(examples: list[dict], query_features: np.ndarray,
                            predicate_count: int) -> dict:
    feature = torch.as_tensor(query_features[[x["feature_row"] for x in examples]], dtype=torch.float32)
    answer = torch.tensor([x["target_candidate_id"] for x in examples], dtype=torch.long)
    anchors = torch.tensor([x["anchor_id"] for x in examples], dtype=torch.long)
    roles = torch.tensor([0 if x["role"] == "entity" else 1 for x in examples], dtype=torch.long)
    relation_targets = torch.zeros((len(examples), 2 * predicate_count), dtype=torch.float32)
    hard = torch.tensor([x["hard_negative_candidate_id"] for x in examples], dtype=torch.long)
    negatives = torch.tensor([x["negative_candidate_ids"] for x in examples], dtype=torch.long)
    for row, example in enumerate(examples):
        for relation_id in example["relation_direction_ids"]:
            relation_targets[row, relation_id] = 1.0
    return {"query_features": feature, "answer_targets": answer, "anchor_targets": anchors,
            "roles": roles, "relation_direction_targets": relation_targets,
            "hard_negative_ids": hard, "query_negative_ids": negatives,
            "predicate_count": predicate_count,
            "query_width": feature.shape[1]}


def _source_edge_sets(split: dict, partition_name: str) -> tuple[set[str], set[str], set[str]]:
    if partition_name == "transductive":
        message = set(split["message_passing_train_edge_ids"])
        held = set(split["witness_edge_ids"]["validation"]) | set(split["witness_edge_ids"]["test"])
        train = set(split["witness_edge_ids"]["train"])
        return message, held, train
    section = split["unseen_entity_generalization"]
    message = set(section["message_passing_edge_ids"])
    held = (set(section["excluded_incident_edge_ids"]) |
            set(section["excluded_validation_edge_ids"]) |
            set(section["excluded_test_edge_ids"]))
    return message, held, message


def _partition_ids(split: dict, questions: list[dict], partition_name: str) -> dict[str, list[str]]:
    if partition_name == "transductive":
        return {name: [row["id"] for row in questions if row["split"] == name]
                for name in ("train", "validation", "test")}
    section = split["unseen_entity_generalization"]
    return {name: list(section[f"{name}_query_ids"]) for name in ("train", "validation", "test")}


def _message_edges(directional_edges: list[dict], allowed_source_ids: set[str],
                   unseen_iris: set[str]) -> list[dict]:
    return [edge for edge in directional_edges if edge["source_edge_id"] in allowed_source_ids and
            edge["subject_iri"] not in unseen_iris and edge["object_iri"] not in unseen_iris]


def _check_navigation_pairs(edges: list[dict]) -> None:
    by_source = defaultdict(set)
    for edge in edges:
        by_source[edge["source_edge_id"]].add(edge["direction"])
    if any(directions != {"forward", "reverse"} for directions in by_source.values()):
        raise ValueError("A source edge must keep both forward and reverse navigation rows")


def _training_link_arrays(train_edges: list[dict], known_edges: list[dict], node_count: int,
                          unseen_iris: set[str], node_ids: dict[str, int], *, seed: int) -> tuple:
    rows = train_edges
    triples_list = [[row["subject_id"], row["relation_id"], row["object_id"]] for row in rows]
    known_triples = [[row["subject_id"], row["relation_id"], row["object_id"]]
                     for row in known_edges]
    negatives = models.sample_negative_tails(
        triples_list, known_triples, node_count, count=10, seed=seed,
        entity_ids=[node_id for iri, node_id in node_ids.items() if iri not in unseen_iris])
    triples = torch.tensor(triples_list, dtype=torch.long)
    return triples, negatives, len(rows)


def _base_query_args(examples: list[dict], query_features: np.ndarray) -> dict:
    if not examples:
        raise ValueError("Frozen training/validation partition has no single-target relevant questions")
    return {"query_features": torch.as_tensor(query_features[[x["feature_row"] for x in examples]], dtype=torch.float32),
            "query_targets": torch.tensor([x["target_candidate_id"] for x in examples], dtype=torch.long),
            "query_negative_ids": torch.tensor([x["negative_candidate_ids"] for x in examples], dtype=torch.long)}


def _evaluation_questions(qids: list[str], questions: list[dict]) -> list[dict]:
    by_id = {row["id"]: row for row in questions}
    return [by_id[qid] for qid in qids]


def _candidate_uri_ids(nodes: list[dict], predicates: list[dict]) -> dict[int, tuple[str, str]]:
    result = {row["id"]: (benchmark.GRAPH, row["iri"]) for row in nodes}
    offset = len(nodes)
    for row in predicates:
        result[offset + row["id"]] = (benchmark.GRAPH, row["iri"])
    return result


def _expected_relation_direction(question: dict, reference: dict, predicate_ids: dict[str, int]) -> list[int]:
    return question_direction_labels(question, reference, predicate_ids)


def _rank_of(targets: set[tuple[str, str]], ranked: list[tuple[str, str]]) -> int | None:
    for index, candidate in enumerate(ranked, 1):
        if candidate in targets:
            return index
    return None


def _make_oracle_row(question: dict, reference: dict, entities, relations,
                     node_ids: dict[str, int], predicate_ids: dict[str, int],
                     candidate_ids: dict[int, tuple[str, str]], twohop_paths) -> dict | None:
    if reference["status"] != "relevant" or len(reference["relevant"]) != 1:
        return None
    traversal = question["traversal"]
    if question["role"] == "entity":
        anchor = node_ids[traversal["start_iri"]]
        steps = [directional_id(step["predicate"], step["direction"], predicate_ids)
                 for step in traversal["steps"]]
        scores = aligned.oracle_structural_scores(
            entities, relations, anchor, steps, list(range(entities.shape[0])))
        ordered = sorted(range(entities.shape[0]), key=lambda idx: (-float(scores[idx]), idx))
        ranked = [candidate_ids[idx] for idx in ordered]
    else:
        subject = node_ids[traversal["subject_iri"]]
        obj = node_ids[traversal["object_iri"]]
        scored = []
        for predicate_iri, predicate_id in predicate_ids.items():
            rel = relations[2 * predicate_id]
            score = -float((entities[subject] + rel - entities[obj]).square().sum()) / entities.shape[-1] ** 0.5
            scored.append((score, predicate_id))
        ranked = [candidate_ids[len(node_ids) + predicate_id]
                  for _, predicate_id in sorted(scored, key=lambda row: (-row[0], row[1]))]
    row = metric_row(question, reference, ranked, {})
    row["oracle_source_path_metrics"] = (
        benchmark.exact_path_metrics(ranked, reference, twohop_paths.get(question["id"], []))
        if question["family"] == "two_hop_path" else None)
    row["partition"] = "oracle_assisted_structural"
    row["oracle_inputs"] = {"anchor_and_path_relation_direction": True,
                            "endpoints_for_predicate_question": True,
                            "question_embedding_used": False}
    return row


def _baseline_unseen_cases(baseline_cases: list[dict], qids: set[str]) -> list[dict]:
    result = []
    for row in baseline_cases:
        if row["id"] in qids and row["status"] == "relevant":
            clone = dict(row); clone["original_question_split"] = clone["split"]; clone["split"] = "test"
            result.append(clone)
    return result


def baseline_summary_for_cases(cases: list[dict]) -> dict:
    by_method = defaultdict(list)
    for row in cases:
        if row["split"] == "test" and row["status"] == "relevant":
            by_method[row["method"]].append(row["metrics"]["recall@10"])
    return {"methods": {method: {"metrics": {"recall@10": sum(values) / len(values)}}
                        for method, values in by_method.items() if values}}


def _direction_diagnostics(question: dict, reference: dict, directional_scores,
                           anchor_scores, predicate_ids: dict[str, int],
                           node_ids: dict[str, int]) -> dict:
    expected = _expected_relation_direction(question, reference, predicate_ids)
    values = directional_scores.detach().cpu().tolist()
    top_id = max(range(len(values)), key=lambda i: (values[i], -i))
    conditional = []
    for relation_id in expected:
        base = (relation_id // 2) * 2
        conditional.append(max((base, base + 1), key=lambda i: values[i]) == relation_id)
    anchor_id = int(anchor_scores.argmax()) if anchor_scores is not None else None
    expected_anchor = question["traversal"].get("start_iri", question["traversal"].get("subject_iri"))
    expected_anchor_id = node_ids.get(expected_anchor) if expected_anchor else None
    return {"expected_relation_direction_ids": expected,
            "top1_relation_direction_id": top_id,
            "joint_relation_direction_top1_correct": bool(expected and top_id in expected),
            "direction_accuracy_conditioned_on_gold_predicate": (sum(conditional) / len(conditional) if conditional else None),
            "anchor_top1_correct": (anchor_id == expected_anchor_id if expected_anchor_id is not None else None),
            "expected_anchor_iri": expected_anchor}


def run_training(final_path: Path, feature_file: Path,
                 feature_manifest_path: Path, preflight_path: Path,
                 authorization_path: Path, out: Path) -> dict:
    if torch is None:
        raise RuntimeError("Use the pinned PyTorch environment for scored training")
    manifest = read(final_path)
    _validate_source_inputs(manifest, final_path)
    if manifest.get("version") != FINAL_VERSION:
        raise ValueError("Training requires the finalized feature-bound experiment manifest")
    preflight = require_fresh_preflight(preflight_path, final_path, training=True)
    feature_manifest = read(feature_manifest_path)
    if (feature_manifest.get("feature_file_sha256") != sha_file(feature_file) or
            sha_file(feature_file) != manifest["features"]["directional_feature_archive_sha256"] or
            sha_file(feature_manifest_path) != manifest["features"]["directional_feature_manifest_sha256"]):
        raise ValueError("Directional relation features differ from the final freeze")
    expected_auth = {"experiment_manifest_sha256": sha_file(final_path),
                     "feature_manifest_sha256": sha_file(feature_manifest_path),
                     "preflight_sha256": sha_file(preflight_path)}
    runner.approval(authorization_path, "authorize_aligned_training", expected_auth)
    if out.exists():
        raise ValueError("Training output exists; choose a fresh path")
    out.mkdir(parents=True)
    for key, path in (("baseline_summary", BASELINE_DIR / "summary.json"),
                      ("baseline_cases", BASELINE_DIR / "cases.jsonl")):
        if sha_file(path) != manifest["input_sha256"][key]:
            raise ValueError(f"Matched baseline changed after freeze: {key}")

    base_arrays = runner.validate_features(BASE_FEATURES, BASE_FEATURE_MANIFEST, EXP)[1]
    with np.load(feature_file, allow_pickle=False) as archive:
        directional_features = archive["relation_features"].astype(np.float32)
        feature_relation_ids = archive["relation_ids"].tolist()
    directional_rows = read_jsonl(final_path.parent / "directional-export-v1/directional-relations.jsonl")
    if feature_relation_ids != list(range(len(directional_rows))) or directional_features.shape != (len(directional_rows), 768):
        raise ValueError("Directional feature ID order or shape differs from the graph vocabulary")

    nodes = read_jsonl(EXPORT / "nodes.jsonl")
    predicates = read_jsonl(EXPORT / "relations.jsonl")
    directional_edges = read_jsonl(final_path.parent / "directional-export-v1/directional-edges.jsonl")
    questions = read(EXP / "questions.json")
    references = read(EXP / "references.json")
    split = read(EXP / "splits.json")
    by_reference = {row["id"]: row for row in references}
    question_feature_rows = {row["id"]: index for index, row in enumerate(questions)}
    node_ids = {row["iri"]: row["id"] for row in nodes}
    predicate_ids = {row["iri"]: row["id"] for row in predicates}
    candidate_ids = _candidate_uri_ids(nodes, predicates)
    candidate_id_by_uri = {value: key for key, value in candidate_ids.items()}
    support = load_scope_support()
    twohop_paths = load_twohop_paths()
    path_adjacency = source_adjacency(directional_edges)
    baseline_cases = read_jsonl(BASELINE_DIR / "cases.jsonl")
    test_output = out / "fits"
    monitor = runner.ResourceMonitor(out, preflight["vm_stat"])
    total_started = time.perf_counter()
    fit_records = []
    monitor.start()

    def guard(epoch, row):
        monitor.check()
        if time.perf_counter() - total_started > MAX_SECONDS:
            raise RuntimeError("Six-hour total aligned run budget exceeded")

    try:
        original_relation_features = torch.as_tensor(base_arrays["relation_features"], dtype=torch.float32)
        node_features = torch.as_tensor(base_arrays["node_features"], dtype=torch.float32)
        query_features = base_arrays["query_features"]
        for partition_name in ("transductive", "unseen_entity"):
            qids = _partition_ids(split, questions, partition_name)
            train_query_ids, validation_query_ids, test_query_ids = (qids[k] for k in ("train", "validation", "test"))
            group_ids = {row["id"]: row["query_group"] for row in questions}
            message_source_ids, heldout_source_ids, split_train_source_ids = _source_edge_sets(split, partition_name)
            aligned.check_alignment_splits(train_query_ids, validation_query_ids, test_query_ids,
                                           group_ids, split_train_source_ids, heldout_source_ids,
                                           message_source_ids)
            unseen_iris = (set(split["unseen_entity_generalization"]["unseen_entity_iris"])
                           if partition_name == "unseen_entity" else set())
            train_edges = _message_edges(directional_edges, message_source_ids, unseen_iris)
            negative_filter_edges = _message_edges(
                directional_edges, {edge["source_edge_id"] for edge in directional_edges}, unseen_iris)
            message_sources = {edge["source_edge_id"] for edge in train_edges}
            if message_sources & heldout_source_ids:
                raise ValueError("An original edge or its derived inverse entered held-out message passing")
            for variant in ("B", "C", "D", "E"):
                relation_features = (torch.stack([original_relation_features[row["predicate_id"]]
                                                  for row in directional_rows]) if variant == "B" else
                                     torch.as_tensor(directional_features, dtype=torch.float32))
                balanced = variant in {"D", "E"}
                hard = variant in {"D", "E"}
                for model_name, encoder in (("rgcn", models.RGCN), ("compgcn", models.CompGCN)):
                    for seed in SEEDS:
                        monitor.check()
                        run_dir = test_output / variant / partition_name / model_name / f"seed-{seed}"
                        run_dir.mkdir(parents=True)
                        if balanced:
                            selected_source_ids = aligned.relation_balanced_source_ids(
                                [(edge["source_edge_id"], edge["predicate_id"]) for edge in train_edges],
                                per_relation_cap=RELATION_SAMPLE_CAP, seed=seed)
                            fit_edges = [edge for edge in train_edges
                                         if edge["source_edge_id"] in selected_source_ids]
                        else:
                            fit_edges = train_edges
                        _check_navigation_pairs(fit_edges)
                        edge_index = torch.tensor([[edge["subject_id"] for edge in fit_edges],
                                                   [edge["object_id"] for edge in fit_edges]], dtype=torch.long)
                        edge_types = torch.tensor([edge["relation_id"] for edge in fit_edges], dtype=torch.long)
                        triples, link_negatives, link_count = _training_link_arrays(
                            fit_edges, negative_filter_edges, len(nodes), unseen_iris, node_ids, seed=seed)
                        train_examples = make_query_examples(
                            train_query_ids, questions, references, query_features, node_ids, predicate_ids,
                            len(nodes), len(predicates), seed=seed,
                            excluded_node_iris=unseen_iris, hard_negatives=hard)
                        validation_examples = make_query_examples(
                            validation_query_ids, questions, references, query_features, node_ids, predicate_ids,
                            len(nodes), len(predicates), seed=seed + 1,
                            excluded_node_iris=set(), hard_negatives=False)
                        if not train_examples or not validation_examples:
                            raise ValueError("Frozen partition lacks relevant train or validation questions")
                        edge_args = {"node_features": node_features, "relation_features": relation_features,
                                     "edge_index": edge_index, "edge_types": edge_types,
                                     "positive_triples": triples, "negative_tail_ids": link_negatives}
                        query_args = _base_query_args(train_examples, query_features)
                        training_args = {**edge_args, **query_args}
                        def base_validate(model):
                            return _validation_mrr(model, None, partition_name, validation_examples,
                                node_features, relation_features, edge_index, edge_types,
                                query_features, len(nodes), len(predicates))
                        model_factory = lambda enc=encoder: enc(
                            768, 768, HIDDEN, len(directional_rows), layers=2)
                        fit_started = time.perf_counter()
                        if variant == "E":
                            align_tensors = build_alignment_tensors(train_examples, query_features,
                                                                    len(predicates))
                            align_tensors.update({"node_features": node_features,
                                                  "relation_features": relation_features,
                                                  "edge_index": edge_index, "edge_types": edge_types,
                                                  "positive_triples": triples,
                                                  "negative_tail_ids": link_negatives})
                            def validate_e(model, head):
                                return _validation_mrr(model, head, partition_name, validation_examples,
                                    node_features, relation_features, edge_index, edge_types,
                                    query_features, len(nodes), len(predicates))
                            model, head, history = fit_aligned_encoder(
                                model_factory, align_tensors, validate_e, seed=seed, resource_guard=guard)
                        else:
                            model, history = models.fit(model_factory, training_args, base_validate,
                                seed=seed, epochs=MAX_EPOCHS, patience=PATIENCE, resource_guard=guard)
                            head = None
                        monitor.check()
                        if time.perf_counter() - total_started > MAX_SECONDS:
                            raise RuntimeError("Six-hour total aligned run budget exceeded")
                        model.eval()
                        if head:
                            head.eval()
                        query_rows = _evaluation_questions(test_query_ids, questions)
                        query_feature_rows = [question_feature_rows[row["id"]] for row in query_rows]
                        qfeature_tensor = torch.as_tensor(query_features[query_feature_rows], dtype=torch.float32)
                        with torch.no_grad():
                            entities, relations, scores, direction_scores, anchor_scores, _ = _base_or_aligned_scores(
                                model, head, node_features, relation_features, edge_index, edge_types,
                                qfeature_tensor, len(nodes), len(predicates))
                        goldfree_rows, prediction_rows, oracle_rows, shared_rows = [], [], [], []
                        qv2_by_id = {row["id"]: row for row in baseline_cases
                                     if row["method"] == "neighborhood_1hop"}
                        for row_index, question in enumerate(query_rows):
                            qid = question["id"]
                            reference = by_reference[qid]
                            numeric_scores = scores[row_index].detach().cpu()
                            ranked = _rank_candidate_scores(question, numeric_scores, candidate_ids,
                                                            len(nodes), len(predicates))
                            goldfree = metric_row(question, reference, ranked, support)
                            predicted_paths = rank_source_paths(
                                anchor_scores[row_index], direction_scores[row_index],
                                numeric_scores[:len(nodes)], path_adjacency, nodes)
                            goldfree["predicted_path_metrics"] = path_retrieval_metrics(
                                question, reference, predicted_paths)
                            goldfree["partition"] = "gold_free_end_to_end"
                            goldfree["original_question_split"] = question["split"]
                            goldfree["split"] = "test"
                            direction = _direction_diagnostics(
                                question, reference, direction_scores[row_index], anchor_scores[row_index],
                                predicate_ids, node_ids)
                            goldfree["direction_diagnostics"] = direction
                            expected = {(item["graph"], item["iri"]) for item in reference["relevant"]}
                            candidate_scores = {candidate_ids[index]: float(numeric_scores[index])
                                                for index in range(len(numeric_scores))}
                            candidate_id_ranked = [(role, graph, iri, candidate_scores[(graph, iri)])
                                                   for role, graph, iri in
                                                   [("entity" if i < len(nodes) else "predicate", *candidate_ids[i])
                                                    for i in range(len(candidate_ids))]]
                            prediction_rows.append({"id": qid, "split": "test", "partition": partition_name,
                                "language": question["language"], "family": question["family"],
                                "status": reference["status"],
                                "top50": [{"role": role, "graph": graph, "iri": iri, "score": value,
                                           "source_witnessed": (graph, iri) in support.get(qid, set())}
                                          for role, graph, iri, value in candidate_id_ranked[:50]],
                                "target_ranks": [{"graph": graph, "iri": iri,
                                    "rank": ranked.index((graph, iri)) + 1 if (graph, iri) in ranked else None}
                                    for graph, iri in sorted(expected)],
                                "direction_diagnostics": direction,
                                "predicted_source_paths": predicted_paths,
                                "predictions_are_hypotheses_not_RDF_evidence": True})
                            goldfree_rows.append(goldfree)
                            oracle = _make_oracle_row(question, reference, entities, relations,
                                node_ids, predicate_ids, candidate_ids, twohop_paths)
                            if oracle:
                                oracle["original_question_split"] = question["split"]
                                oracle["split"] = "test"
                                oracle_rows.append(oracle)
                            baseline_row = qv2_by_id.get(qid)
                            if baseline_row:
                                qv2_candidates = [tuple(item) for item in baseline_row.get("ranked", [])[:50]]
                                pool_ids = [candidate_id_by_uri[item] for item in qv2_candidates
                                            if item in candidate_id_by_uri]
                                shared_order = aligned.rank_shared_pool(
                                    pool_ids, {candidate_id: candidate_scores[candidate_ids[candidate_id]]
                                               for candidate_id in pool_ids})
                                shared_ranked = [candidate_ids[index] for index in shared_order]
                                shared = metric_row(question, reference, shared_ranked, support)
                                shared["partition"] = "QV2_shared_candidate_pool_reranking"
                                shared["original_question_split"] = question["split"]
                                shared["split"] = "test"
                                shared["candidate_pool_source"] = "QV2 top-50 candidates; GNN cannot add candidates"
                                shared["candidate_pool_recall"] = (len(expected & set(qv2_candidates)) / len(expected)
                                                                    if expected else None)
                                shared_rows.append(shared)
                        write_jsonl(run_dir / "predictions.jsonl", prediction_rows)
                        write_jsonl(run_dir / "raw-ranks.jsonl", goldfree_rows)
                        write_jsonl(run_dir / "oracle-assisted-ranks.jsonl", oracle_rows)
                        write_jsonl(run_dir / "qv2-shared-pool-ranks.jsonl", shared_rows)
                        if variant == "E":
                            torch.save({"encoder": model.state_dict(), "alignment_head": head.state_dict()},
                                       run_dir / "checkpoint.pt")
                        else:
                            torch.save(model.state_dict(), run_dir / "checkpoint.pt")
                        partition_baselines = (baseline_cases if partition_name == "transductive" else
                                               _baseline_unseen_cases(baseline_cases, set(test_query_ids)))
                        comparison = runner.compare_to_baselines(
                            goldfree_rows, partition_baselines,
                            baseline_summary_for_cases(partition_baselines))
                        record = {"variant": variant, "partition": partition_name, "model": model_name,
                            "seed": seed, "history": history, "training_seconds": time.perf_counter() - fit_started,
                            "training_epoch_seconds": sum(x["epoch_ms"] for x in history["history"]) / 1000,
                            "checkpoint_bytes": (run_dir / "checkpoint.pt").stat().st_size,
                            "max_process_tree_rss_bytes": monitor.peak_rss_bytes,
                            "message_passing_source_edge_count": len({edge["source_edge_id"] for edge in fit_edges}),
                            "message_passing_directional_edge_count": len(fit_edges),
                            "negative_filter_source_edge_count": len({edge["source_edge_id"] for edge in negative_filter_edges}),
                            "link_prediction_edge_count": link_count,
                            "test_summary": summarize_partition(goldfree_rows),
                            "oracle_assisted_summary": summarize_partition(oracle_rows),
                            "qv2_shared_pool_summary": summarize_partition(shared_rows),
                            "end_to_end_paired_comparison": comparison,
                            "query_counts": {"train": len(train_query_ids), "validation": len(validation_query_ids),
                                             "test": len(test_query_ids)},
                            "files": {name: sha_file(run_dir / name) for name in
                                      ("checkpoint.pt", "predictions.jsonl", "raw-ranks.jsonl",
                                       "oracle-assisted-ranks.jsonl", "qv2-shared-pool-ranks.jsonl")}}
                        write(run_dir / "training.json", record)
                        fit_records.append(record)
        monitor.close()
        receipt = {"version": "rgcn-compgcn-aligned-v2-run-receipt",
                   "experiment_manifest_sha256": sha_file(final_path),
                   "feature_manifest_sha256": sha_file(feature_manifest_path),
                   "preflight_sha256": sha_file(preflight_path),
                   "training_authorization_sha256": sha_file(authorization_path),
                   "fit_count": len(fit_records), "seeds": list(SEEDS),
                   "training_seconds": time.perf_counter() - total_started,
                   "max_process_tree_rss_bytes": monitor.peak_rss_bytes,
                   "resource_monitor_summary": read(monitor.summary_path),
                   "device": "cpu", "torch_version": torch.__version__,
                   "torch_geometric_version": runner.runtime_identity()["packages"]["torch-geometric"],
                   "torch_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(),
                   "predictions_are_hypotheses_not_RDF_evidence": True,
                   "results": fit_records}
        write(out / "run-receipt.json", receipt)
        return receipt
    except Exception as error:
        try:
            monitor.close()
        finally:
            write(out / "failure.json", {"error_type": type(error).__name__, "error": str(error),
                                         "elapsed_seconds": time.perf_counter() - total_started,
                                         "completed_fits": len(fit_records),
                                         "resource_monitor_summary": read(monitor.summary_path)
                                         if monitor.summary_path.exists() else None})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare", help="build the immutable directional export and preregistration")
    prepare_parser.add_argument("--study-dir", type=Path, default=STUDY)
    preflight_parser = sub.add_parser("preflight", help="capture a fresh read-only host/runtime admission receipt")
    preflight_parser.add_argument("--manifest", type=Path, required=True)
    preflight_parser.add_argument("--asset-verification", type=Path)
    preflight_parser.add_argument("--out", type=Path, required=True)
    features_parser = sub.add_parser("features", help="authorized local-only EmbeddingGemma relation inference")
    features_parser.add_argument("--manifest", type=Path, required=True)
    features_parser.add_argument("--preflight", type=Path, required=True)
    features_parser.add_argument("--asset-verification", type=Path, required=True)
    features_parser.add_argument("--authorization", type=Path, required=True)
    features_parser.add_argument("--model-dir", type=Path, required=True)
    features_parser.add_argument("--out", type=Path, required=True)
    assets_parser = sub.add_parser("verify-assets", help="verify local model/license/runtime identities without inference")
    assets_parser.add_argument("--manifest", type=Path, required=True)
    assets_parser.add_argument("--model-dir", type=Path, required=True)
    assets_parser.add_argument("--out", type=Path, required=True)
    finalize_parser = sub.add_parser("finalize", help="bind generated feature hashes to a final frozen manifest")
    finalize_parser.add_argument("--preregistration", type=Path, required=True)
    finalize_parser.add_argument("--features", type=Path, required=True)
    finalize_parser.add_argument("--feature-manifest", type=Path, required=True)
    finalize_parser.add_argument("--out", type=Path, required=True)
    train_parser = sub.add_parser("train", help="run only with a separately authorized final manifest")
    train_parser.add_argument("--manifest", type=Path, required=True)
    train_parser.add_argument("--features", type=Path, required=True)
    train_parser.add_argument("--feature-manifest", type=Path, required=True)
    train_parser.add_argument("--preflight", type=Path, required=True)
    train_parser.add_argument("--authorization", type=Path, required=True)
    train_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.study_dir)
    elif args.command == "preflight":
        result = make_readonly_preflight(args.manifest, args.out, args.asset_verification)
    elif args.command == "features":
        result = generate_relation_features(args.manifest, args.preflight, args.asset_verification,
                                            args.authorization,
                                            args.model_dir, args.out)
    elif args.command == "verify-assets":
        result = verify_model_assets(args.manifest, args.model_dir, args.out)
    elif args.command == "finalize":
        result = finalize_manifest(args.preregistration, args.features, args.feature_manifest, args.out)
    else:
        result = run_training(args.manifest, args.features, args.feature_manifest,
                              args.preflight, args.authorization, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
