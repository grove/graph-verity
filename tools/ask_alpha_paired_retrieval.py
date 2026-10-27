#!/usr/bin/env python3
"""Capture paired BM25-only and source-witnessed candidates; score after capture."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks/ask-alpha-v1"
PROTOCOL = ROOT / "docs/ask-alpha-paired-retrieval.md"
K = (1, 5, 10)
METHODS = ("bm25_only", "neighborhood_v2")
ROLES = {"entity": "entities", "predicate": "predicates"}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def read(path: Path):
    return json.loads(path.read_bytes())


def code_inputs():
    paths = [PROTOCOL, Path(__file__), ROOT / "tools/ask_alpha_benchmark.py",
             ROOT / "tools/ask_alpha_candidate_metrics.py", ROOT / "tools/supervised_ask.py",
             ROOT / "tools/local_nl_ask.py", ROOT / "tools/local_find.py",
             ROOT / "tools/requirements.txt", ROOT / "Cargo.toml", ROOT / "Cargo.lock",
             ROOT / "rust-toolchain.toml"]
    paths += sorted((ROOT / "crates").rglob("*.rs"))
    paths += sorted((ROOT / "crates").rglob("Cargo.toml"))
    return {str(path.relative_to(ROOT)): sha_file(path) for path in paths}


def packet_candidates(packet, scope):
    result = {}
    for role, collection in ROLES.items():
        rows = packet[collection]["candidates"]
        candidates = []
        seen = set()
        for rank, row in enumerate(rows, 1):
            key = (row["graph"], row["iri"])
            if key in seen or row["graph"] not in scope:
                raise ValueError("Duplicate or out-of-scope candidate")
            seen.add(key)
            candidates.append({"rank": rank, "graph": row["graph"], "iri": row["iri"],
                               "exact": row["exact"], "ranking_score": row["ranking_score"]})
        result[role] = candidates
    return result


def candidate_digest(candidates):
    raw = json.dumps(candidates, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode()
    return sha_bytes(raw)


def capture(path: Path):
    import ask_alpha_benchmark as benchmark
    import ask_alpha_candidate_metrics as saved_metrics
    import rdflib

    if path.exists():
        raise ValueError("Refusing to overwrite a retrieval capture")
    saved_metrics.verify()
    questions = read(BENCH / "questions.json")["cases"]
    if len(questions) != 60:
        raise ValueError("Expected the existing exposed 60-question set")

    adapter = benchmark.bundle()
    rows = []
    snapshot_id = adapter.snapshot
    budget = adapter.budget.copy()
    try:
        for question in questions:
            request = {"question": question["question"], "language": question["language"],
                       "snapshot_id": adapter.snapshot,
                       "index_revision": adapter.receipt["index_revision"],
                       "scope": sorted(adapter.scope)}
            bm25 = adapter.json_call("vocabulary", [request, adapter.budget])
            neighborhood = adapter.packet(question["question"], question["language"])
            methods = {"bm25_only": bm25, "neighborhood_v2": neighborhood}
            captured = {}
            for method, packet in methods.items():
                if packet["request"] != request:
                    raise ValueError(f"Request drift in {question['id']} ({method})")
                candidates = packet_candidates(packet, set(request["scope"]))
                captured[method] = {"status": packet["status"], "clipped": packet["clipped"],
                                    "candidates": candidates,
                                    "candidate_sha256": candidate_digest(candidates)}
            rows.append({"id": question["id"], "language": question["language"],
                         "question_sha256": sha_bytes(question["question"].encode()),
                         "snapshot_id": request["snapshot_id"],
                         "index_revision": request["index_revision"],
                         "scope": request["scope"], "methods": captured})
    finally:
        adapter.close()

    inputs = code_inputs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": "ask-alpha-paired-retrieval-capture-v1",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "protocol_sha256": sha_file(PROTOCOL), "input_sha256": inputs,
        "benchmark_manifest_sha256": sha_file(BENCH / "manifest.json"),
        "binary_sha256": sha_file(ROOT / "target/debug/verity"),
        "runtime": {"python": sys.version, "platform": platform.platform(),
                    "rdflib": rdflib.__version__},
        "snapshot_id": snapshot_id,
        "budget": budget, "case_count": len(rows), "cases": rows,
        "capture_boundary": {"references_parsed": False, "inference_performed": False,
                              "answer_query_execution_performed": False,
                              "candidate_retrieval_performed": True}},
        ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def rank(candidates, graph, iri):
    return next((row["rank"] for row in candidates if row["graph"] == graph and row["iri"] == iri), None)


def coverage(rows, method, role, k):
    field = f"{method}_{role}_rank"
    return {"hits": sum(row[field] is not None and row[field] <= k for row in rows),
            "total": len(rows)}


def score(capture_path: Path):
    import ask_alpha_candidate_metrics as saved_metrics

    saved_metrics.verify()
    capture_data = read(capture_path)
    if (capture_data["version"] != "ask-alpha-paired-retrieval-capture-v1"
            or capture_data["input_sha256"] != code_inputs()
            or capture_data["protocol_sha256"] != sha_file(PROTOCOL)
            or capture_data["benchmark_manifest_sha256"] != sha_file(BENCH / "manifest.json")
            or capture_data["binary_sha256"] != sha_file(ROOT / "target/debug/verity")
            or len(capture_data["cases"]) != 60
            or capture_data["capture_boundary"] != {"references_parsed": False,
                "inference_performed": False, "answer_query_execution_performed": False,
                "candidate_retrieval_performed": True}):
        raise ValueError("Capture inputs changed or do not match the registered method")

    for captured in capture_data["cases"]:
        for method in METHODS:
            candidates = captured["methods"][method]["candidates"]
            if candidate_digest(candidates) != captured["methods"][method]["candidate_sha256"]:
                raise ValueError(f"Changed captured candidates: {captured['id']} ({method})")

    questions = read(BENCH / "questions.json")["cases"]
    references = read(BENCH / "references.json")["cases"]
    if len(references) != 60 or len(questions) != 60:
        raise ValueError("Question/reference denominator changed")
    rows = []
    for question, reference, captured in zip(questions, references, capture_data["cases"]):
        if (question["id"] != reference["id"] or question["id"] != captured["id"]
                or question["question"] != reference["question"]
                or question["language"] != reference["language"]
                or question["language"] != captured["language"]
                or captured["question_sha256"] != sha_bytes(question["question"].encode())
                or captured["snapshot_id"] != capture_data["snapshot_id"]
                or reference["intent_mapping_origin"] != "coding_agent_authored_not_independent_human_gold"):
            raise ValueError(f"Question/reference/capture identity mismatch: {question['id']}")
        plan = reference["expected_plan"]
        if ((reference["expected_status"] == "candidate") != (plan is not None)
                or (plan and plan["graph"] not in captured["scope"])):
            raise ValueError(f"Reference status or graph scope mismatch: {question['id']}")
        row = {"id": question["id"], "language": question["language"],
               "expected_status": reference["expected_status"],
               "direction": plan["direction"] if plan else None,
               "clipped": {m: captured["methods"][m]["clipped"] for m in METHODS}}
        for method in METHODS:
            for role, field in (("entity", "start"), ("predicate", "predicate")):
                row[f"{method}_{role}_rank"] = (rank(captured["methods"][method]["candidates"][role],
                                                      plan["graph"], plan[field]) if plan else None)
        rows.append(row)

    supported = [row for row in rows if row["expected_status"] == "candidate"]
    if len(supported) != 29:
        raise ValueError("Expected the existing 29 agent-authored candidate references")

    def summarize(subset):
        result = {}
        for method in METHODS:
            result[method] = {role: {str(k): coverage(subset, method, role, k) for k in K}
                              for role in ROLES}
            result[method]["both"] = {str(k): {"hits": sum(
                row[f"{method}_entity_rank"] is not None and row[f"{method}_entity_rank"] <= k
                and row[f"{method}_predicate_rank"] is not None and row[f"{method}_predicate_rank"] <= k
                for row in subset), "total": len(subset)} for k in K}
        result["paired_target_differences"] = {role: {str(k): {
            "v2_gained": sum(row[f"neighborhood_v2_{role}_rank"] is not None
                             and row[f"neighborhood_v2_{role}_rank"] <= k
                             and (row[f"bm25_only_{role}_rank"] is None or row[f"bm25_only_{role}_rank"] > k)
                             for row in subset),
            "v2_lost": sum(row[f"bm25_only_{role}_rank"] is not None
                           and row[f"bm25_only_{role}_rank"] <= k
                           and (row[f"neighborhood_v2_{role}_rank"] is None or row[f"neighborhood_v2_{role}_rank"] > k)
                           for row in subset), "total": len(subset)} for k in K} for role in ROLES}
        return result

    strata = {field: {value: summarize([row for row in supported if row[field] == value])
                      for value in sorted({row[field] for row in supported})}
              for field in ("language", "direction")}
    noncandidate = [row for row in rows if row["expected_status"] != "candidate"]
    suggestion_returns = {}
    capture_by_id = {row["id"]: row for row in capture_data["cases"]}
    for status in ("needs_clarification", "unsupported"):
        subset = [row for row in noncandidate if row["expected_status"] == status]
        suggestion_returns[status] = {method: sum(
            bool(capture_by_id[row["id"]]["methods"][method]["candidates"]["entity"])
            and bool(capture_by_id[row["id"]]["methods"][method]["candidates"]["predicate"])
            for row in subset) for method in METHODS}

    return {"version": "ask-alpha-paired-retrieval-report-v1",
            "capture_sha256": sha_file(capture_path),
            "summary": {"questions": 60, "languages": {lang: sum(q["language"] == lang for q in questions)
                                                            for lang in ("en", "nb")},
                        "agent_authored_candidate_references": len(supported),
                        "human_relevance_observations": 0,
                        "target_candidate_coverage": summarize(supported),
                        "clipped_candidate_reference_packets": {m: sum(row["clipped"][m] for row in supported)
                                                                 for m in METHODS},
                        "noncandidate_cases_with_both_role_lists": suggestion_returns},
            "strata": strata, "cases": rows,
            "methods": {"bm25_only": "question-vocabulary-packet-v1; whole-question BM25 candidates. Scores are not probabilities.",
                        "neighborhood_v2": "question-vocabulary-packet-v2-neighborhood; BM25 seeds plus source-witnessed neighbors, combined order. Added neighbors use score zero."},
            "limitations": ["Exposed development questions and coding-agent-authored references; no human gold.",
                            "Exact graph+IRI candidate presence is not relevance, answer accuracy, or user usefulness.",
                            "Neighborhood v2 ranks combine lexical and source-witnessed candidates.",
                            "Clipped packets make absent candidates unknown.",
                            "No dense, graph-neural, or generative method was evaluated."],
            "inference_performed": False, "answer_query_execution_performed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--out", type=Path, required=True)
    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--capture", type=Path, required=True)
    score_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.out)
    else:
        if args.out.exists():
            raise ValueError("Refusing to overwrite a scored report")
        report = score(args.capture)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
