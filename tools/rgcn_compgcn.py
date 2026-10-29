#!/usr/bin/env python3
"""Offline data export and ranking metrics for the R-GCN / CompGCN study."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time

import rdflib
from rdflib import Dataset, Literal, RDF, RDFS, SKOS, URIRef

import gemet

ROOT = gemet.ROOT
STUDY = ROOT / "experiments/rgcn-compgcn-v1"
FULL_SOURCE = ROOT / "reports/issue-50-real-rdf-hybrid/full-source-attempt.nq.gz"
GRAPH = gemet.GRAPH
MODEL_PREDICATES = {SKOS.broader, SKOS.narrower, SKOS.related}
NODE_TEXT_PREDICATES = {SKOS.prefLabel, SKOS.altLabel}
RELATION_TEXT_PREDICATES = {RDFS.label, RDFS.comment}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def full_snapshot() -> bytes:
    manifest = gemet.verify()
    source_concepts = json.loads((gemet.DATA / "stats.json").read_text())["source_concepts"]
    raw, stats = gemet.extract(source_concepts)
    require(stats["selected_concepts"] == 5573, "Unexpected full-source concept count")
    require(gzip.decompress(FULL_SOURCE.read_bytes()) == raw,
            "Full source differs from retained #50 source attempt")
    return raw


def quads(raw: bytes):
    previous = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        dataset = Dataset()
        dataset.parse(data=raw, format="nquads")
        rows = list(dataset.quads((None, None, None, None)))
    finally:
        rdflib.NORMALIZE_LITERALS = previous
    require(all(isinstance(s, URIRef) and isinstance(p, URIRef) and isinstance(g, URIRef)
                for s, p, o, g in rows), "Blank nodes or non-IRI graph terms are outside this export")
    return rows


def audit(raw: bytes) -> dict:
    rows = quads(raw)
    concepts = {s for s, p, o, _ in rows if p == RDF.type and o == SKOS.Concept}
    edges = [(s, p, o) for s, p, o, _ in rows
             if p in MODEL_PREDICATES and s in concepts and o in concepts]
    relation_counts = Counter(str(p) for _, p, _ in edges)
    languages = Counter((o.language or "untagged") for _, _, o, _ in rows if isinstance(o, Literal))
    labeled_concepts = {
        (s, o.language or "untagged") for s, p, o, _ in rows
        if s in concepts and p in NODE_TEXT_PREDICATES and isinstance(o, Literal)
    }
    parent = {node: node for node in concepts}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    degree = Counter()
    adjacency = {node: set() for node in concepts}
    for subject, predicate, obj in edges:
        left, right = find(subject), find(obj)
        if left != right:
            parent[left] = right
        degree[subject] += 1
        degree[obj] += 1
        adjacency[subject].add(obj)
    component_sizes = Counter(find(node) for node in concepts)
    broader = {(s, o) for s, p, o in edges if p == SKOS.broader}
    narrower = {(o, s) for s, p, o in edges if p == SKOS.narrower}
    resources = {term for row in rows for term in row[:3] if isinstance(term, URIRef)}
    return {
        "snapshot_sha256": sha_bytes(raw),
        "snapshot_id": "sha256:" + sha_bytes(b"graph-verity-snapshot-v1\0nquads\0" + raw),
        "quads": len(rows),
        "named_graphs": sorted({str(g) for _, _, _, g in rows}),
        "graph_qualified_resources": len(resources),
        "skos_concepts": len(concepts),
        "concepts_with_en_or_no_labels": len({s for s, language in labeled_concepts if language in {"en", "no"}}),
        "literal_languages": dict(sorted(languages.items())),
        "model_edges": len(edges),
        "model_relation_counts": dict(sorted(relation_counts.items())),
        "weak_components": len(component_sizes),
        "largest_weak_component": max(component_sizes.values(), default=0),
        "isolated_concepts": sum(1 for node in concepts if not degree[node]),
        "maximum_relation_degree": max(degree.values(), default=0),
        "broader_narrower_reciprocal_pairs": len(broader & narrower),
        "source_model_edges_are_directed": True,
        "synthetic_or_inferred_edges": 0,
    }


def jsonl(rows) -> bytes:
    return b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode()
                    for row in rows)


def retrieval_view(raw: bytes) -> tuple[bytes, int]:
    """Keep every graph edge, but omit long concept definitions from lexical features."""
    concept_prefix = b"<http://www.eionet.europa.eu/gemet/concept/"
    definition = b"<http://www.w3.org/2004/02/skos/core#definition>"
    kept, omitted = [], 0
    for line in raw.splitlines(keepends=True):
        subject, predicate, _ = line.split(b" ", 2)
        if subject.startswith(concept_prefix) and predicate == definition:
            omitted += 1
        else:
            kept.append(line)
    return b"".join(kept), omitted


def export(out: Path) -> dict:
    require(not out.exists(), "Export output already exists; choose a fresh path")
    raw = full_snapshot()
    rows = quads(raw)
    concepts = {s for s, p, o, _ in rows if p == RDF.type and o == SKOS.Concept}
    graph_by_concept = {s: str(g) for s, p, o, g in rows if p == RDF.type and o == SKOS.Concept}
    texts = {}
    for subject, predicate, obj, graph in rows:
        if subject in concepts and predicate in NODE_TEXT_PREDICATES and isinstance(obj, Literal):
            texts.setdefault(subject, []).append({
                "predicate": str(predicate), "language": obj.language or "",
                "datatype": str(obj.datatype or ""), "text": str(obj),
            })
    ordered = sorted(concepts, key=lambda node: (graph_by_concept[node], str(node)))
    ids = {(graph_by_concept[node], str(node)): index for index, node in enumerate(ordered)}
    nodes = [{"id": ids[(graph_by_concept[node], str(node))], "graph": graph_by_concept[node],
              "iri": str(node), "texts": sorted(texts.get(node, []),
                  key=lambda row: (row["language"], row["predicate"], row["text"]))}
             for node in ordered]
    edges = []
    for subject, predicate, obj, graph in rows:
        if predicate in MODEL_PREDICATES and subject in concepts and obj in concepts:
            edges.append({"graph": str(graph), "subject_id": ids[(str(graph), str(subject))],
                          "subject_iri": str(subject), "predicate": str(predicate),
                          "object_id": ids[(str(graph), str(obj))], "object_iri": str(obj),
                          "direction": "subject_to_object"})
    edges.sort(key=lambda row: (row["graph"], row["subject_iri"], row["predicate"], row["object_iri"]))
    relation_text = {}
    for subject, predicate, obj, graph in rows:
        if subject in MODEL_PREDICATES and predicate in RELATION_TEXT_PREDICATES and isinstance(obj, Literal):
            relation_text.setdefault(str(subject), []).append({
                "predicate": str(predicate), "language": obj.language or "",
                "datatype": str(obj.datatype or ""), "text": str(obj),
            })
    relation_rows = [{"graph": GRAPH, "predicate": predicate,
                      "texts": sorted(relation_text.get(str(predicate), []),
                          key=lambda row: (row["language"], row["predicate"], row["text"]))}
                     for predicate in sorted(MODEL_PREDICATES, key=str)]
    text_snapshot, omitted_definitions = retrieval_view(raw)
    text_snapshot_id = "sha256:" + sha_bytes(b"graph-verity-snapshot-v1\0nquads\0" + text_snapshot)
    policy = (gemet.DATA / "policy.json").read_bytes()
    scope = (gemet.DATA / "scope.json").read_bytes()
    discovery = {
        "version": 1, "snapshot_id": text_snapshot_id,
        "graphs": {GRAPH: {
            "source": "EEA GEMET 4.2.3 and W3C SKOS Reference 2009; original graph statements",
            "license": "CC-BY-4.0 AND W3C Software and Document License (2023)",
            "source_revision": "sha256:" + sha(ROOT / "data/gemet/source/gemet-4.2.3.rdf.gz")
                + ";skos-sha256:" + sha(ROOT / "data/gemet/source/skos.rdf"),
            "importer_revision": "rgcn-compgcn-export-v1-sha256:" + sha(Path(__file__)),
        }},
    }
    out.mkdir(parents=True)
    (out / "snapshot.nq").write_bytes(raw)
    (out / "retrieval.nq").write_bytes(text_snapshot)
    (out / "policy.json").write_bytes(policy)
    (out / "scope.json").write_bytes(scope)
    (out / "discovery.json").write_text(json.dumps(discovery, ensure_ascii=False, indent=2) + "\n")
    (out / "nodes.jsonl").write_bytes(jsonl(nodes))
    (out / "relations.jsonl").write_bytes(jsonl(relation_rows))
    (out / "edges.jsonl").write_bytes(jsonl(edges))
    result = audit(raw)
    result.update({"node_rows": len(nodes), "edge_rows": len(edges),
                   "nodes_sha256": sha(out / "nodes.jsonl"), "relations_sha256": sha(out / "relations.jsonl"),
                   "edges_sha256": sha(out / "edges.jsonl"),
                   "lexical_view_sha256": sha_bytes(text_snapshot),
                   "lexical_view_snapshot_id": text_snapshot_id,
                   "concept_definitions_omitted_from_text_features": omitted_definitions})
    (out / "manifest.json").write_text(json.dumps({
        "version": "rgcn-compgcn-export-v1",
        "source": "EEA GEMET 4.2.3 and W3C SKOS Reference 2009; retained source, no refresh",
        "license": ["CC-BY-4.0", "W3C Software and Document License (2023)"],
        "graph_boundary": [GRAPH],
        "identifier_policy": "Original RDF IRIs and named graph preserved; node IDs are export-local, graph-qualified indices",
        "edge_policy": "Only original SKOS broader/narrower/related resource triples; original direction retained; no inverse or inferred edges",
        "text_policy": "Original concept prefLabel/altLabel and original W3C SKOS predicate rdfs:label/comment literals only; source language/datatype preserved",
        "source_sha256": {path: sha(ROOT / path) for path in [
            "data/gemet/source/gemet-4.2.3.rdf.gz", "data/gemet/source/skos.rdf",
            "data/gemet/manifest.json", "tools/gemet.py"]},
        "export_sha256": {name: sha(out / name) for name in ["snapshot.nq", "retrieval.nq", "nodes.jsonl", "relations.jsonl", "edges.jsonl",
            "policy.json", "scope.json", "discovery.json"]},
        "lexical_view_policy": "Same graph and all original relationships/labels; omit original concept skos:definition literals to fit the existing 64 MiB native discovery index budget; do not increase the budget",
        "audit": result,
    }, ensure_ascii=False, indent=2) + "\n")
    return result


def verify_export(folder: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="rgcn-compgcn-verify-") as temp:
        fresh = Path(temp) / "export"
        expected = export(fresh)
        expected_manifest = (fresh / "manifest.json").read_bytes()
        require((folder / "manifest.json").read_bytes() == expected_manifest,
                "Export manifest does not rebuild from retained sources and current code")
        manifest = json.loads(expected_manifest)
        for name in manifest["export_sha256"]:
            require(sha(folder / name) == sha(fresh / name), "Export changed or no longer rebuilds: " + name)
        return expected


def split_groups(rows: list[dict], group_field: str, seed: int = 117) -> dict[str, list[dict]]:
    """Assign related query variants and duplicate wording to one deterministic split."""
    require(all(isinstance(row.get(group_field), str) and row[group_field] for row in rows),
            "Every row needs a non-empty grouping key")
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for row in rows:
        aliases = [row[group_field]]
        if row.get("question_signature"):
            aliases.append(row["question_signature"])
        first = find(aliases[0])
        for alias in aliases[1:]:
            parent[find(alias)] = first
    result = {name: [] for name in ("train", "validation", "test")}
    root_split = {}
    for row in rows:
        group = find(row[group_field])
        bucket = int(hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()[:8], 16) % 100
        split = "train" if bucket < 80 else "validation" if bucket < 90 else "test"
        previous = root_split.setdefault(group, split)
        require(previous == split, "Related query variants crossed a split")
        result[split].append(row)
    return result


def assert_no_message_edge_leakage(training_edges: list[dict], held_out_edges: list[dict]) -> None:
    """Held-out RDF facts cannot be inputs to the GNN's message-passing graph."""
    def key(edge):
        return (edge["graph"], edge["subject_iri"], edge["predicate"], edge["object_iri"])
    train = {key(edge) for edge in training_edges}
    held_out = {key(edge) for edge in held_out_edges}
    require(train.isdisjoint(held_out), "Held-out evaluation edge leaked into message passing")


def rank_metrics(relevant: set[tuple[str, str]], ranked: list[tuple[str, str]]) -> dict:
    require(len(ranked) == len(set(ranked)), "Rank list contains duplicate graph-qualified candidates")
    if not relevant:
        return {"recall@1": None, "recall@5": None, "recall@10": None,
                "mrr@10": None, "ndcg@10": None, "returned_candidates": len(ranked)}
    hit_ranks = [i + 1 for i, item in enumerate(ranked) if item in relevant]
    recall = {f"recall@{k}": sum(rank <= k for rank in hit_ranks) / len(relevant)
              for k in (1, 5, 10)}
    dcg = sum(1 / math.log2(rank + 1) for rank in hit_ranks if rank <= 10)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(relevant), 10) + 1))
    return {**recall, "mrr@10": next((1 / rank for rank in hit_ranks if rank <= 10), 0.0),
            "ndcg@10": dcg / ideal if ideal else 0.0, "returned_candidates": len(ranked)}


def prepare_cases(out: Path) -> dict:
    """Split the existing public #50 query/reference file into separate inputs."""
    source = ROOT / "benchmarks/hybrid/cases.json"
    cases = json.loads(source.read_text())
    require(len(cases) == 122 and len({case["id"] for case in cases}) == 122,
            "Unexpected public #50 case set")
    questions = [{key: case[key] for key in ("id", "split", "language", "family", "role", "query")}
                 for case in cases]
    references = [{key: case[key] for key in ("id", "split", "language", "family", "role", "status",
                                              "relevant", "witnesses", "group_lineage", "judgment_note")}
                  for case in cases]
    for row in references:
        row["author"] = "Codex AI, inherited from public issue #50 benchmark"
        row["review_status"] = "AI_reference_only"
    require(not out.exists(), "Case output already exists; choose a fresh path")
    out.mkdir(parents=True)
    (out / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n")
    (out / "references.json").write_text(json.dumps(references, ensure_ascii=False, indent=2) + "\n")
    manifest = {
        "version": "rgcn-compgcn-public-cases-v1",
        "source": "benchmarks/hybrid/cases.json",
        "source_sha256": sha(source),
        "questions_sha256": sha(out / "questions.json"),
        "references_sha256": sha(out / "references.json"),
        "counts": {"total": len(cases),
                   "split": dict(sorted(Counter(case["split"] for case in cases).items())),
                   "language": dict(sorted(Counter(case["language"] for case in cases).items()))},
        "status": "public_exposed_regression_only; no independent human judgments; not a sealed holdout",
        "capture_boundary": "BM25/neighborhood capture reads questions.json only; score reads references.json after capture",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def inventory(folder: Path) -> dict:
    return {str(path.relative_to(folder)): sha(path) for path in sorted(folder.rglob("*"))
            if path.is_file() and path.name != "checksums.json"}


def start_session(binary: Path, export_dir: Path):
    process = subprocess.Popen(
        [str(binary), str(export_dir / "retrieval.nq"), str(export_dir / "policy.json"),
         str(export_dir / "scope.json"), str(export_dir / "discovery.json")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    line = process.stdout.readline()
    if not line:
        error = process.stderr.read()
        process.wait()
        raise ValueError("Native retrieval session failed to start: " + error)
    ready = json.loads(line)
    require(ready.get("ready") is True, "Native retrieval session did not report ready")
    return process, ready


def ask_session(process, request: dict) -> dict:
    process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    require(bool(line), "Native retrieval session ended during a request")
    return json.loads(line)


def close_session(process) -> None:
    process.stdin.close()
    code = process.wait(timeout=30)
    error = process.stderr.read()
    process.stdout.close()
    process.stderr.close()
    require(code == 0, "Native retrieval session failed: " + error)


def capture_baselines(export_dir: Path, questions_path: Path, out: Path,
                      bm25_binary: Path, neighborhood_binary: Path) -> dict:
    """Capture native BM25 and witnessed v2 packets without opening any references."""
    require(not out.exists(), "Capture output already exists; choose a fresh path")
    questions = json.loads(questions_path.read_text())
    require(0 < len(questions) <= 1000 and len({q["id"] for q in questions}) == len(questions),
            "Question list is empty, duplicated, or exceeds the native batch limit")
    require(all(0 < len(q["query"].encode()) <= 4096 and q["role"] in {"entity", "predicate", "class"}
                for q in questions), "Malformed retrieval question")
    out.mkdir(parents=True)
    scope = json.loads((export_dir / "scope.json").read_text())
    start = time.perf_counter()
    bm25, bm25_ready = start_session(bm25_binary, export_dir)
    bm25_build_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    neighborhood, neighborhood_ready = start_session(neighborhood_binary, export_dir)
    neighborhood_build_ms = (time.perf_counter() - start) * 1000
    budget = {"per_role_top_k": 20, "max_packet_bytes": 1_048_576, "texts_per_candidate": 8,
              "max_text_bytes": 2048, "evidence_per_page": 3, "max_source_bytes": 4096}
    bm25_rows, neighborhood_rows, packets, timings = [], [], [], []
    try:
        for question in questions:
            request = {"query": question["query"], "role": question["role"], "scope": scope, "limit": 50}
            start = time.perf_counter()
            lexical = ask_session(bm25, request)
            bm25_ms = (time.perf_counter() - start) * 1000
            bm25_rows.append({"id": question["id"], "hits": [
                {"graph": hit["graph"], "iri": hit["iri"], "score": hit["score"], "exact": hit["exact"]}
                for hit in lexical["hits"]]})
            vocabulary_request = {
                "question": question["query"], "language": question["language"],
                "snapshot_id": neighborhood_ready["manifest"]["snapshot_id"],
                "index_revision": neighborhood_ready["manifest"]["index_revision"], "scope": scope,
            }
            start = time.perf_counter()
            reply = ask_session(neighborhood, {"method": "v2", "request": vocabulary_request, "budget": budget})
            neighborhood_ms = (time.perf_counter() - start) * 1000
            packet = reply["packet"]
            packet_path = out / "packets" / (question["id"] + ".json")
            packet_path.parent.mkdir(exist_ok=True)
            packet_path.write_text(json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n")
            packets.append({"id": question["id"], "path": str(packet_path.relative_to(out))})
            neighborhood_rows.append({"id": question["id"], "packet": str(packet_path.relative_to(out))})
            timings.append({"id": question["id"], "bm25_ms": bm25_ms, "neighborhood_ms": neighborhood_ms})
    finally:
        close_session(bm25)
        close_session(neighborhood)
    (out / "bm25-ranks.jsonl").write_bytes(jsonl(bm25_rows))
    (out / "neighborhood-packets.jsonl").write_bytes(jsonl(neighborhood_rows))
    (out / "timings.json").write_text(json.dumps({
        "bm25_index_build_ms": bm25_build_ms, "neighborhood_index_build_ms": neighborhood_build_ms,
        "bm25_index_bytes": bm25_ready.get("index_bytes"),
        "neighborhood_index_bytes": neighborhood_ready.get("index_bytes"),
        "samples": timings,
    }, ensure_ascii=False, indent=2) + "\n")
    receipt = {
        "version": "rgcn-compgcn-baseline-capture-v1",
        "questions_sha256": sha(questions_path),
        "export_manifest_sha256": sha(export_dir / "manifest.json"),
        "retrieval_view_sha256": sha(export_dir / "retrieval.nq"),
        "bm25_binary_sha256": sha(bm25_binary),
        "neighborhood_binary_sha256": sha(neighborhood_binary),
        "case_count": len(questions), "references_opened": False, "model_inference": False,
        "methods": ["native BM25", "native source-witnessed question-vocabulary v2"],
        "environment": {"platform": platform.platform(), "machine": platform.machine(),
                        "processor": platform.processor(), "python": sys.version,
                        "max_child_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
                            * (1 if sys.platform == "darwin" else 1024),
                        "rss_semantics": "largest child high-water mark; not a simultaneous process-tree peak"},
    }
    (out / "capture.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    (out / "checksums.json").write_text(json.dumps(inventory(out), indent=2) + "\n")
    return receipt


def score_capture(export_dir: Path, questions_path: Path, references_path: Path,
                  capture_dir: Path, out: Path) -> dict:
    require(not out.exists(), "Score output already exists; choose a fresh path")
    checksums = json.loads((capture_dir / "checksums.json").read_text())
    require(checksums == inventory(capture_dir), "Baseline capture changed after retrieval")
    receipt = json.loads((capture_dir / "capture.json").read_text())
    require(receipt["questions_sha256"] == sha(questions_path), "Questions changed after capture")
    questions = json.loads(questions_path.read_text())
    references = json.loads(references_path.read_text())
    require(all(ref["review_status"] == "AI_reference_only" for ref in references),
            "Public case reference provenance is missing")
    by_ref = {row["id"]: row for row in references}
    bm25 = {row["id"]: row["hits"] for row in
            (json.loads(line) for line in (capture_dir / "bm25-ranks.jsonl").read_text().splitlines())}
    neighborhood_paths = {row["id"]: row["packet"] for row in
                          (json.loads(line) for line in (capture_dir / "neighborhood-packets.jsonl").read_text().splitlines())}
    require(set(by_ref) == set(bm25) == set(neighborhood_paths) == {q["id"] for q in questions},
            "Question/reference/capture denominators differ")
    corpus = {key: str((export_dir / name).resolve()) for key, name in
              [("rdf", "snapshot.nq"), ("policy", "policy.json"), ("scope", "scope.json"),
               ("config", "discovery.json")]}
    source_lines = set((export_dir / "snapshot.nq").read_text().splitlines())
    import question_vocabulary as qv
    case_rows = []
    for question in questions:
        ref = by_ref[question["id"]]
        for witness in ref["witnesses"]:
            for statement in witness["source_quads"]:
                require(statement in source_lines, "Reference witness is absent from the full source graph")
        relevant = {(row["graph"], row["iri"]) for row in ref["relevant"]}
        bm25_ranked = [(hit["graph"], hit["iri"]) for hit in bm25[question["id"]]]
        packet = json.loads((capture_dir / neighborhood_paths[question["id"]]).read_text())
        qv.source_audit(packet, corpus, {"required": []})
        collection = {"entity": "entities", "predicate": "predicates", "class": "classes"}[question["role"]]
        neighborhood_ranked = [(candidate["graph"], candidate["iri"])
                                for candidate in packet[collection]["candidates"]]
        for method, ranked in [("bm25", bm25_ranked), ("neighborhood", neighborhood_ranked)]:
            metrics = rank_metrics(relevant, ranked)
            case_rows.append({"id": question["id"], "split": question["split"],
                              "language": question["language"], "family": question["family"],
                              "role": question["role"], "status": ref["status"], "method": method,
                              "relevant": sorted([list(item) for item in relevant]),
                              "ranked": [list(item) for item in ranked], "metrics": metrics,
                              "candidate_recall": (len(set(ranked) & relevant) / len(relevant)) if relevant else None,
                              "reference_witnesses": sum(len(w["source_quads"]) for w in ref["witnesses"]),
                              "no_source_answer_candidate_return": ref["status"] != "relevant" and bool(ranked)})
    out.mkdir(parents=True)
    (out / "cases.jsonl").write_bytes(jsonl(case_rows))
    summary = summarize_capture(case_rows)
    summary["source_evidence_audited"] = True
    summary["independence"] = "All judgments are inherited AI-authored public #50 references; not independent human relevance or a pristine holdout."
    summary["no_match_semantics"] = "No source-supported relevant target in this bounded benchmark; not a claim of real-world absence."
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (out / "capture_sha256.json").write_text(json.dumps({
        "capture": sha(capture_dir / "checksums.json"), "questions": sha(questions_path),
        "references": sha(references_path), "export": sha(export_dir / "manifest.json"),
    }, indent=2) + "\n")
    (out / "checksums.json").write_text(json.dumps(inventory(out), indent=2) + "\n")
    return summary


def summarize_capture(rows: list[dict]) -> dict:
    methods = {}
    def metrics(group_rows):
        result = {}
        for key in ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10"):
            values = [row["metrics"][key] for row in group_rows if row["metrics"][key] is not None]
            result[key] = {"n": len(values), "mean": sum(values) / len(values) if values else None}
        return result

    for method in ("bm25", "neighborhood"):
        selected = [row for row in rows if row["method"] == method]
        relevant = [row for row in selected if row["status"] == "relevant"]
        groups = {"overall": relevant}
        for split in ("development", "evaluation"):
            groups["split/" + split] = [row for row in relevant if row["split"] == split]
            for language in ("no", "en"):
                groups[f"split/{split}/language/{language}"] = [
                    row for row in groups["split/" + split] if row["language"] == language]
        groups.update({"language/" + language: [row for row in relevant if row["language"] == language]
                       for language in ("no", "en")})
        groups.update({"family/" + family: [row for row in relevant if row["family"] == family]
                       for family in sorted({row["family"] for row in relevant})})
        outcomes = {}
        for status in ("ambiguous", "no_match"):
            group = [row for row in selected if row["status"] == status]
            outcomes[status] = {"n": len(group),
                                "candidate_return_count": sum(bool(row["ranked"]) for row in group),
                                "candidate_return_rate": (sum(bool(row["ranked"]) for row in group) / len(group)
                                                           if group else None)}
        methods[method] = {
            "metrics": {key: metrics(value) for key, value in groups.items()},
            "outcomes": outcomes,
            "candidate_pool_recall": {
                split: (sum(row["candidate_recall"] for row in group if row["candidate_recall"] is not None) /
                        sum(row["candidate_recall"] is not None for row in group)
                        if any(row["candidate_recall"] is not None for row in group) else None)
                for split, group in [("all", relevant),
                                     ("evaluation", groups["split/evaluation"])]
            },
        }
    bm25 = {row["id"]: row for row in rows if row["method"] == "bm25" and row["split"] == "evaluation"
            and row["status"] == "relevant"}
    neighborhood = {row["id"]: row for row in rows if row["method"] == "neighborhood"
                    and row["split"] == "evaluation" and row["status"] == "relevant"}
    deltas = {}
    for key in ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10"):
        values = [neighborhood[case]["metrics"][key] - bm25[case]["metrics"][key]
                  for case in sorted(set(bm25) & set(neighborhood))]
        deltas[key] = {"n": len(values), "mean": sum(values) / len(values) if values else None}
    return {"case_count": len(rows) // 2, "evaluation_relevant_cases": len(bm25),
            "evaluation_paired_delta_neighborhood_minus_bm25": deltas, "methods": methods}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("audit", help="Print source-verified full GEMET adequacy statistics")
    build = commands.add_parser("export", help="Build a fresh graph-qualified RDF and typed adjacency export")
    build.add_argument("--out", type=Path, required=True)
    verify = commands.add_parser("verify", help="Rebuild and verify an existing export")
    verify.add_argument("--export", type=Path, required=True)
    cases = commands.add_parser("prepare-cases", help="Separate public #50 questions from AI-authored references")
    cases.add_argument("--out", type=Path, required=True)
    capture = commands.add_parser("capture", help="Capture native BM25 and witnessed-neighborhood ranks, without references")
    capture.add_argument("--export", type=Path, required=True)
    capture.add_argument("--questions", type=Path, required=True)
    capture.add_argument("--out", type=Path, required=True)
    capture.add_argument("--bm25-session", type=Path, required=True)
    capture.add_argument("--neighborhood-session", type=Path, required=True)
    score = commands.add_parser("score", help="Audit and score a completed model-free baseline capture")
    score.add_argument("--export", type=Path, required=True)
    score.add_argument("--questions", type=Path, required=True)
    score.add_argument("--references", type=Path, required=True)
    score.add_argument("--capture", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "audit":
        result = audit(full_snapshot())
    elif args.command == "export":
        result = export(args.out)
    elif args.command == "verify":
        result = verify_export(args.export)
    elif args.command == "prepare-cases":
        result = prepare_cases(args.out)
    elif args.command == "capture":
        result = capture_baselines(args.export, args.questions, args.out,
                                   args.bm25_session, args.neighborhood_session)
    else:
        result = score_capture(args.export, args.questions, args.references, args.capture, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
