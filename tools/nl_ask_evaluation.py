#!/usr/bin/env python3
"""Recalculate #76's blocked evaluation from public frozen evidence, without inference or execution."""
import argparse
from collections import Counter
import json
from pathlib import Path

import one_hop_trial as t

ROOT = t.ROOT
REPORT = ROOT / "reports/issue-76-nl-ask-evaluation"
PROTOCOL = ROOT / "configs/nl-ask-evaluation-v1.json"


def receipts():
    # Explicit public inputs only; never walk private participant or sealed data.
    paths = [PROTOCOL, ROOT / "tools/nl_ask_evaluation.py", ROOT / "tools/test_nl_ask_evaluation.py",
             t.CONFIG, ROOT / "configs/grounded-models-v1.json", ROOT / "Cargo.lock",
             ROOT / "Cargo.toml", ROOT / "rust-toolchain.toml", ROOT / ".github/workflows/ci.yml"]
    for folder in ["studies/nl-ask-v1", "reports/issue-74-one-hop-trial", "reports/issue-75-nl-ask",
                   "examples/nl-ask-v1", "tools/local_nl_ask_ui_v1", "crates", "schemas"]:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())
    paths.extend(p for p in (ROOT / "tools").iterdir() if p.suffix in {".py", ".mjs", ".txt"})
    return {str(p.relative_to(ROOT)): t.sha(p) for p in sorted(set(paths))}


def calculate(binary):
    protocol = t.n.read(PROTOCOL)
    t.n.verify()
    folder = t.REPORT / "freeze"
    t.verify(folder, binary)
    decision = t.n.read(t.REPORT / "decision.json")
    t.n.require(decision == t.blocked_decision(folder, t.n.read(t.REPORT / "host.json")),
                "Changed prerequisite decision")
    t.n.require(decision["inference_performed"] is False and decision["executions"] == 0,
                "This blocked evaluator requires a new version for actual inference evidence")
    selected = t.cases()
    coverage = t.n.read(folder / "coverage.json")
    coverage_by_id = {c["id"]: c for c in coverage["cases"]}
    dataset = t.n.parse_rdf(t.n.Dataset(), t.STUDY / "snapshot.nq", format="nquads")
    audits = []
    previews = []
    for case in selected:
        cid = case["id"]
        packet_path = folder / "retrieval" / cid / "packet.json"
        packet = t.n.read(packet_path)
        preview = t.n.rust_preview(case, json.dumps(case["gold_draft"]), binary)
        previews.append(dict(id=cid, origin="AI_reference_fixture_not_model",
                             classification=preview[0], authoritative_preview=preview[1],
                             approval="not_requested", execution=None))
        supported = case["expected_status"] == "candidate"
        if supported:
            rows, evidence = t.n.rows_and_witnesses(case, dataset)
            t.n.require(rows == case["full_bindings"] and evidence == case["full_evidence"],
                        "Independent reference mismatch: " + cid)
            t.n.require(preview[1]["request"] == case["gold_request"], "Reference preview mismatch: " + cid)
        else:
            rows, evidence = None, None
        audits.append(dict(id=cid, question=case["question"], language=case["language"],
            task_family=case["task_family"], intent_lineage=case["intent_lineage"],
            gold_provenance=case["provenance"], expected_status=case["expected_status"],
            reference_request=case["gold_request"], reference_bindings=rows, reference_evidence=evidence,
            reference_answer_status=("no_stored_match" if rows == [] else "nonempty") if supported else "not_applicable",
            retrieval_required=coverage_by_id[cid]["required"],
            retrieval_missing_at_20=coverage_by_id[cid]["missing_at"]["20"],
            direction_coverage="unmeasured_no_direction_reference_in_frozen_retrieval",
            packet_receipt=dict(path=str(packet_path.relative_to(ROOT)), sha256=t.sha(packet_path),
                packet_id=packet["packet_id"], snapshot_id=packet["request"]["snapshot_id"],
                policy_hash=packet["policy_hash"], graph_hashes=packet["graph_hashes"], sources=packet["sources"]),
            model_faithfulness=None, graph_execution=None, strict_answer_exactness=None,
            human_comprehension=None))
    controls = []
    by_id = {c["id"]: c for c in selected}
    for control in t.n.read(t.REPORT / "replay-controls.json"):
        outcome = t.score_saved(by_id[control["record"]["id"]], control["record"], control["stage"], folder, binary)
        for key, expected in control["expected"].items():
            t.n.require(outcome[key] == expected, "Fixture regression: " + control["name"])
        _, preview = t.n.rust_preview(by_id[control["record"]["id"]], control["record"].get("raw_response", ""), binary) if control["record"]["runtime_status"] == "completed" else (None, None)
        controls.append(dict(name=control["name"], stage=control["stage"],
            origin="fixture_not_model_or_human", raw_record=control["record"], outcome=outcome,
            authoritative_preview=preview, approval="not_requested", execution=None))
    inventory = []
    for model, stages in decision["variants"].items():
        for stage, result in stages.items():
            t.n.require(Counter(by_id[c["id"]]["expected_status"] for c in result["cases"])
                        == protocol["denominators_per_variant_stage"], "Lost blocked denominators")
            for case in result["cases"]:
                inventory.append(dict(variant=model, stage=stage, **case,
                    expected_status=by_id[case["id"]]["expected_status"],
                    prompt=None, raw_output=None, native_token_ids=None, model_status=None,
                    chosen_table_refs=None, rust_preview=None, confirmation=None, execution=None,
                    latency_seconds=None, sampled_process_tree_rss_gib=None))
    missing = [c for c in audits if c["retrieval_missing_at_20"]]
    return dict(version=protocol["version"], protocol=protocol, decision="INCONCLUSIVE_REVISE",
        blockers=["#74 host preflight blocked both candidates; no validated new-contract live adapter",
                  "No actual question-to-approved-answer run or cold/resident model measurements",
                  "Zero consenting human participants; comprehension and confidently wrong approvals unmeasured"],
        inference_performed=False, model_draft_executions=0, holdout_accessed=False,
        product_rollout_authorized=False, unattended_ask_authorized=False,
        evidence_status="exploratory_AI_references_only",
        source_sha256=receipts(),
        summary=dict(evaluation_cases=len(selected), unattempted_variant_stage_cases=len(inventory),
            actual_model_outputs=0, actual_user_approved_answers=0,
            retrieval_at_20=coverage["at_k"]["20"],
            missing_predicate_cases=[c["id"] for c in missing],
            retrieval_misses_by_family=dict(Counter(c["task_family"] for c in missing)),
            model_faithful_plans=dict(numerator=None, denominator=18, unmeasured=18),
            strict_answer_sets=dict(numerator=None, denominator=18, unmeasured=18),
            model_clarifications=dict(numerator=None, denominator=6, unmeasured=6),
            model_unsupported=dict(numerator=None, denominator=6, unmeasured=6),
            wrong_but_executable=dict(numerator=None, denominator=30, unmeasured=30),
            safety=dict(model_executions_observed=0, live_safety_gate="unmeasured_no_inference")),
        human=dict(consenting_participants=0, attempts=0, comprehension=None, correct_approvals=None,
            incorrect_approvals=None, confidently_wrong_accepted_plans=None, cancellations=None,
            assistance=None, completion=None, confidence=None, gate="unmeasured_blocked"),
        resources=dict(host_evidence="reports/issue-74-one-hop-trial/host.json",
            host_captured_at=t.n.read(t.REPORT / "host.json")["captured_at"],
            host_blockers=decision["blockers"], cold_startup_seconds=None,
            cold_end_to_end_seconds=None, resident_end_to_end_seconds=None,
            cold_process_tree_rss_gib=None, resident_process_tree_rss_gib=None,
            interpreter=None, persistent_worker_lifecycle=None,
            measurement="Historical host screen only; no model process existed. Recalculation costs are not inference costs."),
        cases=audits, run_inventory=inventory, reference_previews=previews, fixture_controls=controls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["report", "verify"])
    parser.add_argument("--out", type=Path, default=REPORT / "evaluation.json")
    parser.add_argument("--binary", type=Path, default=t.BINARY)
    args = parser.parse_args()
    report = calculate(args.binary.resolve())
    if args.command == "verify":
        t.n.require(t.n.read(args.out) == report, "Evaluation differs from frozen receipts or recalculation")
        if args.out == REPORT / "evaluation.json":
            t.n.require(t.n.read(REPORT / "checksums.json") == t.v.inventory(REPORT), "Changed evaluation bundle")
    else:
        if args.out == REPORT / "evaluation.json":
            t.n.require(not (REPORT / "checksums.json").exists(), "Never overwrite an evaluation bundle")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x") as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        if args.out == REPORT / "evaluation.json":
            with (REPORT / "checksums.json").open("x") as stream:
                stream.write(json.dumps(t.v.inventory(REPORT), indent=2) + "\n")
    print("INCONCLUSIVE_REVISE: 120 unattempted outcomes; zero model executions; zero humans")


if __name__ == "__main__":
    main()
