#!/usr/bin/env python3
"""Model-free #82: register, capture gold-free packets, then source-audit exposed regressions."""
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import question_vocabulary as v

ROOT = v.ROOT
PROTOCOL = ROOT / "benchmarks/question-vocabulary-v2-neighborhood/protocol.json"
REPORT = ROOT / "reports/issue-82-neighborhood"
BINARY = ROOT / "target/debug/verity"
SESSION = ROOT / "target/debug/examples/neighborhood_session"
HISTORICAL = ROOT / "reports/issue-74-one-hop-trial/freeze"


def registered_inputs():
    cfg = v.read(PROTOCOL)
    paths = [PROTOCOL, ROOT / cfg["questions"], ROOT / cfg["references"],
             ROOT / "Cargo.lock", ROOT / "rust-toolchain.toml",
             ROOT / "schemas/question-vocabulary-packet-v2-neighborhood.json"]
    paths += sorted((ROOT / "crates/verity_core/src").glob("*.rs"))
    paths += [ROOT / "crates/verity_cli/src/main.rs", ROOT / "crates/verity_cli/examples/neighborhood_session.rs"]
    paths += [ROOT / p for c in cfg["corpora"].values() for p in c.values()]
    return {str(p.relative_to(ROOT)): v.sha(p) for p in paths}


def register():
    path = PROTOCOL.parent / "registration.json"
    v.require(not path.exists(), "Never overwrite preregistration; use a new variant")
    v.dump(path, {"version": "neighborhood-registration-v2", "utc": datetime.now(timezone.utc).isoformat(),
                  "input_sha256": registered_inputs(), "scored_new_ranks_examined": False,
                  "evaluation_is_exposed_regression": True})


def check_registration():
    v.require(v.read(PROTOCOL.parent / "registration.json")["input_sha256"] == registered_inputs(),
              "Registered retrieval/source/protocol changed; never silently refresh")


def request(q, manifest, corpus):
    return {"question": q["question"], "language": q["language"],
            "snapshot_id": manifest["snapshot_id"], "index_revision": manifest["index_revision"],
            "scope": v.read(ROOT / corpus["scope"])}


def capture(out):
    check_registration()
    cfg = v.read(PROTOCOL)
    questions = v.read(ROOT / cfg["questions"])["questions"]
    v.require(not out.exists(), "Never overwrite captured packets")
    v.require(len(questions) == 30 and len({q["id"] for q in questions}) == 30, "Wrong case denominator")
    # Fixed public IDs are checked before creating any paths; no reference file is parsed here.
    v.require([q["id"] for q in questions] == [f"eva-{i:02}" for i in range(1, 31)], "Wrong case order")
    out.mkdir(parents=True)
    v.dump(out / "budget.json", cfg["budget"])
    resources = {"platform": platform.platform(), "python": sys.version, "binary_sha256": v.sha(BINARY),
                 "session_sha256": v.sha(SESSION), "binary_bytes": BINARY.stat().st_size,
                 "session_bytes": SESSION.stat().st_size, "os_file_cache": "uncontrolled",
                 "resident_rss_semantics": "ps RSS KiB sampled after each request; not peak or allocator measurement",
                 "cold_rss_semantics": "fresh CLI process maximum RSS from time; OS caches uncontrolled",
                 "methods": {}}
    corpus = cfg["corpora"]["evaluation"]
    args = [str(ROOT / corpus[k]) for k in ("rdf", "policy", "scope", "config")]
    resources["input_bytes"] = {p: (ROOT / p).stat().st_size for p in corpus.values()}
    resources["load_before"] = list(__import__("os").getloadavg())
    for method, command in [("v1", "vocabulary"), ("v2", "neighborhood")]:
        started = time.perf_counter()
        process = subprocess.Popen([str(SESSION), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, cwd=ROOT)
        try:
            ready = json.loads(process.stdout.readline())
            v.require(ready["ready"], "Session not ready")
            rows = []
            for q in questions:
                case = out / q["id"]
                case.mkdir(exist_ok=True)
                req = request(q, ready["manifest"], corpus)
                v.dump(case / "request.json", req)
                frame = {"method": method, "request": req, "budget": cfg["budget"]}
                start = time.perf_counter()
                process.stdin.write(json.dumps(frame) + "\n")
                process.stdin.flush()
                response = json.loads(process.stdout.readline())
                elapsed = (time.perf_counter() - start) * 1000
                packet = response["packet"]
                # Capture native compact bytes too: Python float formatting cannot authenticate replay.
                time_args = ["/usr/bin/time", "-l" if sys.platform == "darwin" else "-v"]
                cli_args = [str(BINARY), command, *v.corpus_args(corpus), str(case / "request.json"), str(out / "budget.json")]
                cold_start = time.perf_counter()
                cold = subprocess.run([*time_args, *cli_args], cwd=ROOT, capture_output=True, timeout=60, check=True)
                cold_ms = (time.perf_counter() - cold_start) * 1000
                raw = cold.stdout.rstrip(b"\n")
                v.require(json.loads(raw) == packet, "Resident/cold packet mismatch")
                v.require(len(raw) <= cfg["budget"]["max_packet_bytes"], "Packet exceeds shared byte budget")
                (case / f"{method}.json").write_bytes(raw)
                (case / f"{method}-time.txt").write_bytes(cold.stderr)
                rss = int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(process.pid)], text=True).strip())
                if method == "v1":
                    v.require(raw == (HISTORICAL / f"retrieval/{q['id']}/packet.json").read_bytes(), "Historical v1 packet changed")
                rows.append({"id": q["id"], "retrieval_ms": response["retrieval_ms"],
                             "resident_roundtrip_ms": elapsed, "resident_rss_kib": rss,
                             "cold_cli_ms": cold_ms, "packet_bytes": len(raw)})
            process.stdin.close()
            v.require(process.wait(timeout=10) == 0, "Session failed")
            resources["methods"][method] = {"pid": process.pid, "ready": ready, "samples": rows,
                                             "session_wall_ms": (time.perf_counter() - started) * 1000}
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
    resources["load_after"] = list(__import__("os").getloadavg())
    v.dump(out / "resources.json", resources)
    v.dump(out / "freeze.json", {"registration_sha256": v.sha(PROTOCOL.parent / "registration.json"),
                                 "input_sha256": registered_inputs(), "inference_performed": False,
                                 "holdout_accessed": False, "references_parsed_during_capture": False})
    v.dump(out / "checksums.json", v.inventory(out))


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def summarize(cases):
    return {str(k): {"role_graph_coverage": {
        role: {"covered": sum(r["rank"] is not None and r["rank"] <= k for c in cases for r in c["required"] if r["role"] == role),
               "total": sum(r["role"] == role for c in cases for r in c["required"])} for role in v.COLLECTIONS},
        "both_required": sum(bool(c["required"]) and not c["missing_at"][str(k)] for c in cases),
        "original_direction_reference_denominator": 0,
        "new_source_audit_direction": {"covered": sum(c["direction_v2"][str(k)] is True for c in cases),
                                        "total": sum(c["direction_v2"][str(k)] is not None for c in cases)}} for k in v.KS}


def score(out, replay=True):
    check_registration()
    v.require(v.read(out / "checksums.json") == v.inventory(out), "Capture changed")
    freeze = v.read(out / "freeze.json")
    v.require(freeze["input_sha256"] == registered_inputs() and not freeze["references_parsed_during_capture"], "Invalid capture identity")
    v.require(freeze["registration_sha256"] == v.sha(PROTOCOL.parent / "registration.json"), "Registration drift")
    cfg = v.read(PROTOCOL)
    # All packet bytes and their hashes exist before any reference or #76 plan is loaded.
    questions = v.read(ROOT / cfg["questions"])["questions"]
    references = v.read(ROOT / cfg["references"])
    old = v.read(HISTORICAL / "coverage.json")
    audit76 = v.read(ROOT / "reports/issue-76-nl-ask-evaluation/evaluation.json")
    # Explicit source-only direction supplement, separate from the unchanged original denominator.
    audit_rows = audit76["cases"]
    if isinstance(audit_rows, list):
        audit_rows = {c["id"]: c for c in audit_rows}
    corpus = cfg["corpora"]["evaluation"]
    import rdflib
    from rdflib import Dataset, URIRef
    rdflib.NORMALIZE_LITERALS = False
    data = Dataset()
    data.parse(ROOT / corpus["rdf"], format="nquads")
    source_index = json.loads(v.cli(BINARY, "index-build", *v.corpus_args(corpus)))
    methods = {}
    for method, command in [("v1", "vocabulary-replay"), ("v2", "neighborhood-replay")]:
        outcomes = []
        for q in questions:
            case = out / q["id"]
            packet = v.read(case / f"{method}.json")
            if replay:
                raw = v.cli(BINARY, command, *v.corpus_args(corpus), case / "request.json", out / "budget.json", case / f"{method}.json").rstrip(b"\n")
                v.require(raw == (case / f"{method}.json").read_bytes(), "Packet replay mismatch")
            catalog, evidence = v.source_audit(packet, corpus, references["cases"][q["id"]])
            ref = references["cases"][q["id"]]
            result = v.score_case(packet, ref, catalog)
            result.update(id=q["id"], question=q["question"], source_evidence=evidence,
                          packet_sha256=v.sha(case / f"{method}.json"))
            result["direction_v2"] = {str(k): None for k in v.KS}
            result["direction_source_v2"] = []
            if ref["required"]:
                plan = audit_rows[q["id"]]["reference_request"]
                template = plan["template"]
                step = template["steps"][0]
                direction = "outgoing" if step["direction"] == "forward" else "incoming"
                start = next(r for r in ref["required"] if r["role"] == "entity")
                pred = next(r for r in ref["required"] if r["role"] == "predicate")
                v.require(template["start"] == start["iri"] and step["predicate"] == pred["iri"] and step["graph"] == pred["graph"], "Direction supplement identity mismatch")
                graph = data.graph(URIRef(pred["graph"]))
                pattern = ((URIRef(start["iri"]), URIRef(pred["iri"]), None) if direction == "outgoing" else (None, URIRef(pred["iri"]), URIRef(start["iri"])))
                triples = sorted(f"{s.n3()} {p.n3()} {o.n3()} <{pred['graph']}> ." for s, p, o in graph.triples(pattern))
                result["direction_source_v2"] = triples
                result["direction_reference_v2"] = direction
                # Empty reference paths cannot supply a positive directional source witness.
                if triples:
                    result["direction_v2"] = {str(k): v.directed(packet, start, pred, direction, k) for k in v.KS}
                result["non_required_predicate_candidates"] = [c["iri"] for c in packet["predicates"]["candidates"] if (c["graph"], c["iri"]) != (pred["graph"], pred["iri"])]
            else:
                result["clarification_or_unsupported_candidate_returns"] = {role: len(packet[name]["candidates"]) for role, name in v.COLLECTIONS.items()}
            old_case = next(c for c in old["cases"] if c["id"] == q["id"])
            result["previously_missing_predicate"] = next((r for r in old_case["missing_at"]["20"] if r["role"] == "predicate"), None)
            result["ambiguity"] = {"requires_disambiguation": packet["requires_disambiguation"],
                                   "matches_before_clipping": {role: packet[name]["matches"] for role, name in v.COLLECTIONS.items()}}
            result["exact_first_preserved"] = {}
            baseline = v.read(case / "v1.json")
            for role, name in v.COLLECTIONS.items():
                exact = [c for c in baseline[name]["candidates"] if c["exact"]]
                result["exact_first_preserved"][role] = ([(c["graph"], c["iri"]) for c in packet[name]["candidates"][:len(exact)]] == [(c["graph"], c["iri"]) for c in exact]) if exact else None
            if result["previously_missing_predicate"]:
                pred = result["previously_missing_predicate"]
                iri, g = pred["iri"], pred["graph"]
                seeds = baseline["entities"]["candidates"]
                all_adjacent = []
                for rank, seed in enumerate(seeds, 1):
                    if seed["graph"] != g:
                        continue
                    graph = data.graph(URIRef(g))
                    for direction, pattern in [("outgoing", (URIRef(seed["iri"]), URIRef(iri), None)), ("incoming", (None, URIRef(iri), URIRef(seed["iri"])))]:
                        for s, p, o in graph.triples(pattern):
                            all_adjacent.append({"seed_rank": rank, "seed_iri": seed["iri"], "direction": direction,
                                                 "statement": f"{s.n3()} {p.n3()} {o.n3()} <{g}> ."})
                tokens = set("".join(c if c.isalnum() else " " for c in q["question"].lower()).split())
                postings = source_index["graphs"][g]["postings"]
                matched_tokens = sorted(t for t in tokens if iri in postings.get(t, {}))
                result["missing_predicate_audit"] = {
                    "matched_lexical_tokens": matched_tokens,
                    "lexical_failure": "no_question_token_match" if not matched_tokens else "matched_but_outside_top20",
                    "original_iri": iri, "graph": g, "authorized_predicate": ("predicate", g, iri) in catalog,
                    "true_seed_adjacency": all_adjacent,
                    "v1_text_match_absent_top20": True,
                    "v1_clipped_usage_pages": any(page["clipped"] for c in seeds for page in c["usage"]),
                    "wrong_role_entity": False, "question_language_supported": q["language"] in ("en", "no", "nb", "nn"),
                    "explanation": "Authorized original adjacency exists near retrieved seeds; predicate missed by whole-question lexical top-20. Clipped v1 navigation cannot prove absence." if all_adjacent else "No original adjacency for this predicate among retained entity seeds; open-world unknown, lexical miss remains."}
            outcomes.append(result)
        methods[method] = {"at_k": summarize(outcomes), "cases": outcomes}
    v.require(methods["v1"]["at_k"]["20"]["role_graph_coverage"]["predicate"] == {"covered": 6, "total": 18}, "Lost historical baseline")
    resources = v.read(out / "resources.json")
    resource_summary = {}
    for method, measured in resources["methods"].items():
        samples = measured["samples"]
        metrics = {field: {"p50": percentile([r[field] for r in samples], 0.5), "p95": percentile([r[field] for r in samples], 0.95),
                           "max": max(r[field] for r in samples)}
                   for field in ["retrieval_ms", "resident_roundtrip_ms", "cold_cli_ms", "resident_rss_kib", "packet_bytes"]}
        cold_rss = []
        for sample in samples:
            raw = (out / sample["id"] / f"{method}-time.txt").read_text()
            for line in raw.splitlines():
                if "maximum resident set size" in line.lower():
                    value = int(line.split()[0]) if line.split()[0].isdigit() else int(line.rsplit(":", 1)[1]) * 1024
                    cold_rss.append(value)
        resource_summary[method] = {"metrics": metrics, "cold_maximum_rss_bytes": {"max": max(cold_rss), "samples": cold_rss},
                                    "index_bytes": measured["ready"]["index_bytes"], "index_build_ms": measured["ready"]["build_ms"]}
    return {"version": "neighborhood-regression-coverage-v2", "case_count": 30, "supported": 18,
            "clarification": 6, "unsupported": 6, "methods": methods,
            "direction_reference": "source-audit-v2 supplement to #76 original plans; positive original triple witnesses only, empty paths excluded; #74 denominator remains 0",
            "resource_summary": resource_summary,
            "scorer_sha256": v.sha(Path(__file__)),
            "registration_sha256": v.sha(PROTOCOL.parent / "registration.json"),
            "capture_checksums_sha256": v.sha(out / "checksums.json"),
            "reviewer_status": references["reviewer_status"], "inference_performed": False, "holdout_accessed": False,
            "limitations": "Exposed, correlated AI-authored regression questions; no independent generalization, model accuracy or automatic execution claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["register", "capture", "score", "verify"])
    parser.add_argument("--folder", type=Path, default=REPORT / "capture")
    parser.add_argument("--report", type=Path, default=REPORT / "coverage.json")
    args = parser.parse_args()
    if args.command == "register":
        register()
    elif args.command == "capture":
        capture(args.folder)
    elif args.command == "score":
        v.require(not args.report.exists(), "Never overwrite a scored report")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        v.dump(args.report, score(args.folder))
    else:
        seal = args.report.parent / "checksums.json"
        if seal.exists():
            v.require(v.read(seal) == v.inventory(args.report.parent), "Report/source receipts changed")
        v.require(v.read(args.report) == score(args.folder), "Coverage/source replay changed")
    print(f"{args.command}: model-free exposed regression; no inference, execution or holdout access")


if __name__ == "__main__":
    main()
