#!/usr/bin/env python3
"""Phase 0 public development reports, Rust replay, integrity receipts and proposed gates.

No command reads private holdout payloads. authorize-locked checks public metadata only;
actual hidden inference deliberately remains outside the public runner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

from local_parser import DATASETS, ROOT, percentiles, require, sha

SCORING = "phase0-v1-ordered-structural-and-binding-set"
GATES = ROOT / "configs/phase-0-gates.proposed.json"
PROTOCOL = ROOT / "configs/phase-0-protocol.json"
APPROVAL = ROOT / "configs/phase-0-approval.json"
COMPONENTS = ["entity", "predicate", "direction", "variables", "operator", "datatype", "number", "date_operand", "aggregation", "group_by", "having", "projection", "scope", "snapshot", "literal", "limit"]
ABSTENTIONS = {"unsupported", "needs_clarification", "parsing_error"}


def read(path):
    return json.loads(Path(path).read_text())


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_new(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def seal(payload):
    return {"sha256": digest(payload), "payload": payload}


def unseal(value):
    require(set(value) == {"sha256", "payload"} and value["sha256"] == digest(value["payload"]),
            "Invalid or altered manifest checksum")
    return value["payload"]


def rate(k, n, z=1.96):
    if n == 0:
        return {"status": "not_applicable", "numerator": k, "denominator": n,
                "value": None, "wilson_95": None}
    p = k / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return {"status": "measured", "numerator": k, "denominator": n, "value": p,
            "wilson_95": [max(0, center-radius), min(1, center+radius)]}


def statistics(cases, model=True):
    supported = [c for c in cases if c["expected_status"] == "executed"]
    unsupported = [c for c in cases if c["expected_status"] != "executed"]
    if not model:
        return {"status": "not_measured_oracle_is_not_model_accuracy",
                "executable_checks": rate(sum(c["passed"] for c in supported), len(supported)),
                "fixture_bookkeeping": len(unsupported)}
    metrics = {
        "json_valid": rate(sum(c["json_valid"] is True for c in cases), len(cases)),
        "contract_valid": rate(sum(c["contract_valid"] is True for c in cases), len(cases)),
        "structural_ir": rate(sum(c["structural_ir_exact"] is True for c in supported), len(supported)),
        "exact_answer": rate(sum(c["exact_result_set"] is True for c in supported), len(supported)),
        "correct_abstention": rate(sum(c["proposal_status"] == c["expected_status"] for c in unsupported), len(unsupported)),
        "false_abstention": rate(sum(c["proposal_status"] in ABSTENTIONS for c in supported), len(supported)),
        "failure_to_abstain": rate(sum(c["proposal_status"] not in ABSTENTIONS for c in unsupported), len(unsupported)),
        "candidate_on_expected_abstention": rate(sum(c["proposal_status"] == "candidate" for c in unsupported), len(unsupported)),
        "wrong_plan_executed": rate(sum(c["wrong_plan_successful_execution"] for c in cases), len(cases)),
        "wrong_plan_among_executions": rate(sum(c["wrong_plan_successful_execution"] for c in cases),
                                            sum(c["wrong_plan_successful_execution"] or c["exact_result_set"] is not None for c in cases)),
    }
    metrics["macro_answer_scores_all_supported"] = {
        k: sum((c.get(k) or 0) for c in supported)/len(supported) if supported else None
        for k in ["precision", "recall", "f1"]}
    # Descriptive bootstrap over cases; fixed resampling makes reports reproducible.
    # Related templates are correlated: neither this nor Wilson establishes independence.
    import random
    rng = random.Random(7)
    intervals = {}
    for key in ["precision", "recall", "f1"]:
        values = [(c.get(key) or 0) for c in supported]
        samples = sorted(sum(rng.choices(values, k=len(values)))/len(values) for _ in range(1000)) if values else []
        intervals[key] = [samples[24], samples[974]] if samples else None
    metrics["macro_answer_bootstrap_95"] = intervals
    metrics["components"] = {}
    for key in COMPONENTS:
        unavailable = any(c["proposal_status"] == "candidate" and c["contract_valid"] is True
                          and c["components_exact"].get(key) is None for c in supported)
        metrics["components"][key] = ({"status": "not_measured", "value": None, "numerator": None,
                                       "denominator": len(supported), "wilson_95": None}
                                      if unavailable else rate(sum(c["components_exact"].get(key) is True for c in supported), len(supported)))
    return metrics


def annotate(score, reference, benchmark, split):
    require(score["family"] == reference["family"] and score["expected_status"] == reference["expected_status"],
            "Saved case metadata mismatch")
    c = dict(score)
    c["components_exact"] = {key: score["components_exact"].get(key) for key in COMPONENTS}
    raw = c.pop("raw_response", None)
    c["raw_response_sha256"] = hashlib.sha256(raw.encode()).hexdigest() if raw is not None else None
    c["raw_response_evidence"] = "Unmodified input Rust report, case ID; manifest pins its complete bytes"
    retrieval = score.get("retrieval", {"status": "not_applicable", "mode": "oracle_vocabulary", "failure": None})
    require(retrieval["status"] in {"not_applicable", "not_measured", "failed", "measured"}, "Invalid retrieval status")
    c.update(benchmark=benchmark, split=split, provenance=reference["provenance"],
             review_status=reference["review_status"], requested_scope=reference["scope"],
             expected_abstention=reference["expected_status"] != "executed",
             actual_abstention=score["proposal_status"] in ABSTENTIONS,
             retrieval=retrieval,
             missing_facts={"status": "not_measured", "reason": "No independent per-case completeness annotation"},
             observed_user_facing_false_confidence={"status": "not_measured", "reason": "No complete user interface"})
    if not c.get("error_code") and c["detail"]:
        c["error_code"] = c["detail"].split(":", 1)[0]
    if c["contract_valid"] is False:
        c["failure_stage"] = "response_schema" if c["json_valid"] else "json_generation"
    elif c["safety_valid"] is False:
        c["failure_stage"] = "rust_validation_authorization"
    elif c["proposal_status"] in ABSTENTIONS:
        c["failure_stage"] = "expected_abstention" if c["proposal_status"] == c["expected_status"] else "incorrect_abstention"
    elif c["stage"] in {"scored", "reference"} or c["wrong_plan_successful_execution"]:
        c["failure_stage"] = "matching_reference_results" if c["exact_result_set"] else "semantic_or_answer_disagreement"
    else:
        c["failure_stage"] = c["stage"]
    c.setdefault("result_classification", "not_measured_historical_bindings_not_retained")
    return c


def summarize(report, benchmark, split):
    require(report["split"] == split and report["snapshot_id"] == benchmark["snapshot_id"]
            and report["benchmark"] == benchmark["name"], "Benchmark/split/snapshot mismatch")
    refs = {c["id"]: c for c in benchmark["cases"] if c["split"] == split}
    require(len(refs) == len(report["cases"]) and set(refs) == {c["id"] for c in report["cases"]},
            "Missing, extra or duplicate scored cases")
    cases = [annotate(c, refs[c["id"]], benchmark["name"], split) for c in report["cases"]]
    model = report["mode"] != "oracle_no_model"
    return {"benchmark": report["benchmark"], "snapshot_id": report["snapshot_id"], "split": split, "cases": cases,
            "metrics": statistics(cases, model),
            "per_family": {f: statistics([c for c in cases if c["family"] == f], model)
                           for f in sorted({c["family"] for c in cases})},
            "failure_stages": {s: sum(c["failure_stage"] == s for c in cases)
                               for s in sorted({c["failure_stage"] for c in cases})},
            "warm_latency_ms": {"samples": max(0, len(cases)-1), **percentiles([c["end_to_end_ms"] for c in cases[1:]])},
            "stage_latency_ms": {key: {"status": "measured" if any(c.get(key) is not None for c in cases) else "not_measured", "samples": sum(c.get(key) is not None for c in cases),
                                       **percentiles([c[key] for c in cases if c.get(key) is not None])}
                                 for key in ["generation_ms", "catalog_ms", "validation_compile_ms", "pipeline_ms", "vocabulary_selection_ms", "model_roundtrip_ms", "runtime_prompt_ms", "runtime_predicted_ms"]},
            "execution_stage_latency_ms": {key: {"status": "measured" if any(c.get("execution") for c in cases) else "not_measured", "samples": sum(c.get("execution") is not None for c in cases),
                                                 **percentiles([c["execution"][key] for c in cases if c.get("execution")])}
                                           for key in ["validation_ms", "query_ms", "evidence_ms"]},
            "quality_failures": sum(not c["passed"] for c in cases),
            "attempts": len(cases),
            "validation_rejections": sum(c["safety_valid"] is False for c in cases),
            "retrieval_failures": sum(c["retrieval"]["status"] == "failed" for c in cases),
            "generation_failures": sum(c["json_valid"] is None for c in cases),
            "timeouts": {"count": sum(c.get("error_code") == "timeout" or "timed out" in c["detail"].lower() for c in cases),
                         "scope": "recorded case errors; inspect runner failures for interrupted attempts"}}


def replay(evidence, out):
    """Feed saved raw strings to the *same* Rust evaluator, never a Python IR evaluator."""
    for dataset, split in DATASETS:
        source = read(evidence / f"{dataset}-report.json") if (evidence / f"{dataset}-report.json").exists() else read(evidence / dataset / "report.json")
        benchmark = read(ROOT / f"benchmarks/{dataset}.json")
        require(source["split"] == split and source["snapshot_id"] == benchmark["snapshot_id"], "Replay split/snapshot mismatch")
        refs = {c["id"]: c for c in benchmark["cases"] if c["split"] == split}
        require(set(refs) == {c["id"] for c in source["cases"]} and len(refs) == len(source["cases"]), "Replay case mismatch")
        responses = {(refs[c["id"]]["question"], tuple(refs[c["id"]]["scope"])): c for c in source["cases"]}
        command = [str(ROOT / "target/debug/verity"), "evaluate-local", f"data/{dataset}/snapshot.nq", "nquads",
                   f"data/{dataset}/policy.json", f"benchmarks/{dataset}.json", split, "saved_output_replay_no_inference"]
        with (out / f"{dataset}-stderr.log").open("x") as errors:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True)
            try:
                while line := process.stdout.readline():
                    value = json.loads(line)
                    if value.get("startup_ready"):
                        continue
                    if "report" in value:
                        require(value["report"]["benchmark_digest"] == source["benchmark_digest"], "Changed typed benchmark identity")
                        write_new(out / f"{dataset}-report.json", value["report"])
                        break
                    request = value["parser_request"]
                    case = responses[(request["question"], tuple(request["catalog"]["scope"]))]
                    reply = {"response": case["raw_response"]} if case["raw_response"] is not None else {"error": "Recorded generation failure"}
                    process.stdin.write(json.dumps(reply) + "\n")
                    process.stdin.flush()
                process.stdin.close()
                require(process.wait(timeout=30) == 0, "Rust replay failed; partial outputs preserved")
                require((out / f"{dataset}-report.json").exists(), "Missing replay report")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
                if not process.stdin.closed:
                    process.stdin.close()


def artifact_paths():
    return [GATES, PROTOCOL, ROOT / "configs/local-parser.json", ROOT / "configs/local-parser.prompt.txt",
            ROOT / "configs/local-parser.gbnf", ROOT / "schemas/contracts-v1.json", ROOT / "Cargo.lock",
            ROOT / "rust-toolchain.toml", ROOT / "benchmarks/split-manifest.json", ROOT / "configs/locked-holdout-commitment.json",
            ROOT / "tools/phase0.py", ROOT / "tools/local_parser.py", ROOT / "tools/locked_phase0.py",
            *sorted((ROOT / "crates").glob("*/src/*.rs")),
            *[ROOT / f"benchmarks/{name}.json" for name, _ in DATASETS],
            *[ROOT / f"data/{name}/{file}" for name, _ in DATASETS for file in ["snapshot.nq", "policy.json"]]]


def assess(summary, gates, approval):
    require(gates["version"] == 1, "Unsupported gates version")
    matrix = []
    def check(name, actual, limit, minimum=False, reason=""):
        state = "unavailable" if actual is None else "pass" if (actual >= limit if minimum else actual <= limit) else "fail"
        matrix.append({"gate": name, "actual": actual, "threshold": limit, "comparison": ">=" if minimum else "<=", "status": state, "reason": reason})
    datasets = summary["datasets"]
    metrics = [d["metrics"] for d in datasets.values()]
    def values(key):
        return [m.get(key, {}).get("value") for m in metrics]
    def worst(key, minimum=True):
        v = values(key)
        return (min(v) if minimum else max(v)) if v and all(x is not None for x in v) else None
    mapping = {
        "supported_question_exact_answer_set_min": (worst("exact_answer"), True),
        "semantic_plan_accuracy_min": (worst("structural_ir"), True),
        "correct_abstention_on_unsupported_or_ambiguous_min": (worst("correct_abstention"), True),
        "false_abstention_on_supported_questions_max": (worst("false_abstention", False), False),
        "unflagged_wrong_plan_answers_max_count": (summary.get("user_facing_measurement", {}).get("unflagged_wrong_plan_answers"), False),
        "unauthorized_execution_or_scope_disclosure_max_count": (summary["safety"]["unauthorized_execution_or_disclosure_count"], False),
        "raw_sparql_or_write_execution_max_count": (summary["safety"]["prohibited_execution_count"], False),
        "transfer_exact_answer_accuracy_gap_max_absolute": (summary["development_transfer_gap_absolute"], False),
    }
    families = [f["exact_answer"]["value"] for d in datasets.values() for f in d["per_family"].values()
                if f.get("exact_answer", {}).get("denominator", 0)]
    mapping["per_supported_family_exact_answer_set_min"] = (min(families) if families else None, True)
    require(set(mapping) == set(gates["quality_go_proposal"]), "Unknown or missing quality gate")
    for name, limit in gates["quality_go_proposal"].items():
        require(isinstance(limit, (int, float)) and math.isfinite(limit) and limit >= 0, "Invalid numerical threshold")
        actual, minimum = mapping[name]
        check(name, actual, limit, minimum, "Descriptive public AI-reference agreement; structural equality is conservative")
    sample_policy = read(PROTOCOL)["minimum_samples_proposed"]
    for name, dataset in datasets.items():
        m = dataset["metrics"]
        for metric, minimum in [("exact_answer", sample_policy["supported_per_dataset"]),
                                ("correct_abstention", sample_policy["abstentions_per_dataset"])]:
            check(f"{name}_{metric}_samples", m.get(metric, {}).get("denominator"), minimum, True,
                  "Proposed minimum; sample counts alone never establish negligible risk")
        for family, f in dataset["per_family"].items():
            n = f.get("exact_answer", {}).get("denominator", 0)
            if n:
                check(f"{name}_{family}_samples", n, sample_policy["supported_per_family"], True)
    perf = summary["target_cpu_measurements"]
    require(set(gates["cpu_go_proposal"]) == {"warm_end_to_end_p95_seconds_max", "cold_first_answer_seconds_max", "whole_process_peak_rss_gib_max"}, "Unknown CPU gate")
    for name, limit in gates["cpu_go_proposal"].items():
        require(isinstance(limit, (int, float)) and math.isfinite(limit) and limit >= 0, "Invalid CPU threshold")
        check(name, perf.get(name), limit, reason=perf["status"])
    prerequisites = summary["prerequisites"]
    require(set(prerequisites) == set(gates["prerequisites"]), "Unknown or missing prerequisite")
    for name, expected in gates["prerequisites"].items():
        actual = prerequisites[name]
        matrix.append({"gate": name, "actual": actual, "threshold": expected, "status": "pass" if actual == expected else "unavailable", "reason": "Required evidence, not inferred from engineering success"})
    try:
        validate_approval(approval, gates, read(PROTOCOL))
        approved = True
    except (KeyError, TypeError, ValueError):
        approved = False
    bound_run = (summary.get("gates_at_run_sha256") == digest(gates)
                 and summary.get("protocol_at_run_sha256") == digest(read(PROTOCOL))
                 and summary.get("approved_before_first_holdout") is True
                 and bool(summary.get("preregistration_sha256")))
    matrix.append({"gate": "preregistered_run", "status": "pass" if bound_run else "unavailable",
                   "actual": summary.get("preregistration_sha256"), "threshold": "frozen_before_first_holdout",
                   "reason": "Later threshold approvals cannot retroactively pass an earlier run"})
    matrix.append({"gate": "approval", "status": "pass" if approved else "unavailable", "actual": approval.get("status"), "threshold": "approved_bound_thresholds", "reason": "Proposal comparisons cannot authorize GO"})
    stop = any((summary["safety"].get(key) or 0) > 0 for key in ["unauthorized_execution_or_disclosure_count", "prohibited_execution_count"])
    decision = "STOP" if stop else "NOT READY" if any(r["status"] == "unavailable" for r in matrix) else "REVISE" if any(r["status"] == "fail" for r in matrix) else "GO"
    return {"decision": decision, "gates_sha256": digest(gates), "matrix": matrix,
            "recommendation": "Revise the measured configuration; abandon unattended unrestricted Ask for this configuration. Keep exact resolution/manual typed plans. This is not a preregistered decision."}


def build_report(evidence, out, replayed=False):
    historical = read(evidence / "run.json")
    datasets = {}
    for name, split in DATASETS:
        pinned = historical.get("artifact_sha256", {}).get(f"benchmarks/{name}.json")
        require(pinned == sha(ROOT / f"benchmarks/{name}.json"), "Missing or changed benchmark byte identity")
        path = evidence / f"{name}-report.json"
        if not path.exists():
            path = evidence / name / "report.json"
        datasets[name] = summarize(read(path), read(ROOT / f"benchmarks/{name}.json"), split)
    answers = [d["metrics"].get("exact_answer", {}).get("value") for d in datasets.values()]
    gap = abs(answers[0] - answers[1]) if all(v is not None for v in answers) else None
    gap_interval = None
    if gap is not None:
        bounds = [rate(d["metrics"]["exact_answer"]["numerator"], d["metrics"]["exact_answer"]["denominator"], 2.2414)["wilson_95"] for d in datasets.values()]
        lo, hi = bounds[0][0] - bounds[1][1], bounds[0][1] - bounds[1][0]
        gap_interval = [0 if lo <= 0 <= hi else min(abs(lo), abs(hi)), max(abs(lo), abs(hi))]
    violations, audited = 0, 0
    for d in datasets.values():
        for case in d["cases"]:
            execution = case.get("execution")
            if execution:
                audited += 1
                scope = set(case["requested_scope"])
                violations += int(set(execution["scope"]) != scope or execution["snapshot_id"] != d["snapshot_id"]
                                  or any(e["source_graph"].get("value") not in scope for e in execution["evidence"]))
    summary = {"version": 1, "scoring_version": SCORING, "evidence_class": "public_development_AI_reference_agreement_only",
               "datasets": datasets, "aggregate": statistics([c for d in datasets.values() for c in d["cases"]]),
               "development_transfer_gap_absolute": gap, "development_transfer_gap_absolute_interval_95": gap_interval,
               "gap_interval_method": "Conservative difference of marginal 97.5% Wilson intervals (Bonferroni), descriptive under correlated cases",
               "transfer_gap_warning": "Public development comparison, not independent transfer/generalization; not paired observations",
               "historical_performance": {"status": "inherited_from_recorded_run" if not replayed else "not_applicable_replay_is_not_inference",
                                          "environment": {k: v for k, v in historical.items() if k != "results"},
                                          "results": historical.get("results", {}) if not replayed else {}},
               "target_cpu_measurements": {"status": "not_measured_no_separately_designated_target_cpu"},
               "safety": {"unauthorized_execution_or_disclosure_count": violations if violations else None,
                          "observed_execution_scope_violations": violations, "executions_with_scope_and_evidence_audited": audited, "prohibited_execution_count": None,
                          "reason": "No full disclosure/authorization audit receipt; rejections are not boundary violations",
                          "structural_wrong_plan_proxy_count": sum(c["wrong_plan_successful_execution"] for d in datasets.values() for c in d["cases"])},
               "user_facing_measurement": {"status": "not_measured", "unflagged_wrong_plan_answers": None},
               "prerequisites": {"independent_human_gold_review": False, "independent_locked_question_split": False,
                                 "runtime_model_tokenizer_prompt_grammar_hashes": historical.get("grammar_probes_passed", False),
                                 "numerical_gates_approved_before_holdout": False, "actual_target_cpu_recorded": False,
                                 "oracle_regression_pass_fraction": None},
               "uncertainty": "Wilson 95% for rates and fixed-seed 1000-resample percentile bootstrap for macro P/R/F1. Descriptive only: related templates and AI reference correlation invalidate independence claims; zero errors never prove zero risk."}
    approval, gates = read(APPROVAL), read(GATES)
    summary["gate_assessment"] = assess(summary, gates, approval)
    write_new(out / "summary.json", summary)
    markdown(out / "summary.md", summary)
    paths = artifact_paths() + [APPROVAL, evidence / "run.json"]
    for name, _ in DATASETS:
        path = evidence / f"{name}-report.json"
        paths.append(path if path.exists() else evidence / name / "report.json")
    inputs = [{"path": str(p.resolve().relative_to(ROOT)) if p.resolve().is_relative_to(ROOT) else str(p.resolve()), "sha256": sha(p)} for p in paths]
    payload = {"version": 1, "kind": "development_replay" if replayed else "historical_development_reassessment",
               "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
               "scoring_version": SCORING, "command": sys.argv, "environment": {"platform": platform.platform(), "python": sys.version},
               "inputs": inputs, "outputs": {name: sha(out / name) for name in ["summary.json", "summary.md"]},
               "splits": DATASETS, "model_invoked": False, "holdout_accessed": False,
               "inference_mode": "saved_raw_outputs" if replayed else "inherited_recorded_cpu_grammar_constrained",
               "toolchain": subprocess.check_output(["rustc", "-Vv"], text=True),
               "measured_vs_inherited": "Replay stage timings measure replay overhead, never model generation; historical input files remain immutable"}
    write_new(out / "manifest.json", seal(payload))
    return summary


def markdown(path, summary):
    lines = ["# Phase 0 evaluation", "", f"Formal decision: **{summary['gate_assessment']['decision']}**.", "",
             "Public AI-reference agreement; no expert semantic validation or production-readiness claim.", "",
             "| Dataset | Metric | Numerator / denominator | Value | 95% Wilson interval |", "|---|---|---|---|---|"]
    for name, dataset in summary["datasets"].items():
        for key, m in dataset["metrics"].items():
            if isinstance(m, dict) and "denominator" in m:
                lines.append(f"| {name} | {key} | {m['numerator']}/{m['denominator']} | {m['value']} | {m['wilson_95']} |")
    lines += ["", "| Dataset / family | Exact answer | Structural IR | Correct abstention | Macro P / R / F1 (all supported) |",
              "|---|---|---|---|---|"]
    def fraction(m):
        return f"{m['numerator']}/{m['denominator']}" if m else "not_measured"
    for name, dataset in summary["datasets"].items():
        for family, m in dataset["per_family"].items():
            lines.append(f"| {name} / {family} | {fraction(m.get('exact_answer'))} | {fraction(m.get('structural_ir'))} | {fraction(m.get('correct_abstention'))} | {m.get('macro_answer_scores_all_supported')} |")
    perf = summary["historical_performance"]
    lines += ["", "Recorded inference performance: " + perf["status"] + ". Replay stage timings are not model measurements.",
              "", "| Dataset | Warm E2E p50 / p95 / p99 ms | Generation p50 / p95 / p99 ms | Process-cold first answer ms |",
              "|---|---|---|---|"]
    for name, result in perf["results"].items():
        lines.append(f"| {name} | {result.get('warm_end_to_end_ms')} | {result.get('generation_ms')} | {result.get('cold_first_answer_ms_page_cache_not_evicted')} |")
    env = perf["environment"]
    lines += ["", f"Recorded CPU: {env.get('machdep.cpu.brand_string', 'not_measured')}; OS: {env.get('platform', 'not_measured')}; logical cores: {env.get('logical_cpus', 'not_measured')}; threads: {env.get('config', {}).get('cpu_threads', 'not_measured')}; system RAM bytes: {env.get('hw.memsize', 'not_measured')}; accelerators disabled by recorded CPU-only build.",
              f"Sampled aggregate peak RSS KiB: {env.get('sampled_aggregate_peak_rss_kib', 'not_measured')}; samples: {env.get('rss_samples', 'not_measured')}. {env.get('rss_limitations', '')}",
              "Cache: " + env.get('cache_condition', 'not_measured') + ". No disk-cold measurement. Target deployment CPU is not designated.",
              "Historical M1 Pro warm p95 (28.06/26.59 seconds) exceeds the proposed 10-second budget; cold first answers (17.68/18.04 seconds) and sampled RSS (1.43 GiB) are below proposed budgets. These are descriptive historical comparisons, not target-CPU gate passes."]
    lines += ["", "| Gate | Status | Actual | Requirement | Reason |", "|---|---|---|---|---|"]
    for row in summary["gate_assessment"]["matrix"]:
        lines.append(f"| {row['gate']} | {row['status']} | {row['actual']} | {row.get('comparison', '')} {row['threshold']} | {row['reason']} |")
    lines += ["", summary["gate_assessment"]["recommendation"], "", summary["uncertainty"], "",
              "Wrong-plan execution is a conservative structural proxy. Observed user-facing false confidence is not measured.",
              "Empty bindings do not establish real-world falsity; missing facts remain unknown without independent completeness evidence."]
    with path.open("x") as stream:
        stream.write("\n".join(lines) + "\n")


def verify_manifest(path, check_inputs=False):
    payload = unseal(read(path))
    for item in payload.get("inputs", []) if check_inputs else []:
        require(sha(ROOT / item["path"]) == item["sha256"], f"Changed manifest input: {item['path']}")
    outputs = payload.get("outputs", payload.get("files"))
    require(isinstance(outputs, dict), "Missing manifest outputs")
    for name, expected in outputs.items():
        target = (path.parent / name).resolve()
        require(not Path(name).is_absolute() and target.is_relative_to(path.parent.resolve())
                and sha(target) == expected, "Changed or unsafe manifest output")
    return payload


def archive_inference(out, state):
    if state["status"] == "completed_measurement_not_a_feasibility_pass":
        build_report(out, out)
    else:
        write_new(out / "failure-manifest.json", seal({
            "version": 1, "status": "incomplete_inference_run", "scoring_version": SCORING,
            "source_revision": state.get("base_git_commit"), "environment": state,
            "model_invoked": state.get("grammar_probes_passed", False), "holdout_accessed": False,
            "outputs": {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}}))


def timestamp(value):
    require(isinstance(value, str), "Timestamp must be an ISO string with timezone")
    parsed = dt.datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, "Timestamp must include timezone")
    return parsed


def validate_approval(approval, gates, protocol):
    require(approval["status"] == "approved" and approval["gates_sha256"] == digest(gates)
            and approval["protocol_sha256"] == digest(protocol), "Missing approval bound to exact gates and protocol")
    require(all(approval.get(k) for k in ["approved_by", "approved_at", "provenance", "target_hardware", "experiment_identity"]), "Incomplete approval provenance or experiment identity")
    require(timestamp(approval["approved_at"]) <= dt.datetime.now(dt.timezone.utc), "Future approval")
    required = {"cpu_model", "os", "architecture", "logical_cores", "threads", "system_ram_bytes", "accelerator", "measurement_configuration"}
    require(required <= approval["target_hardware"].keys() and all(approval["target_hardware"][k] is not None for k in required), "Incomplete actual target CPU")
    identity = {"model_sha256", "tokenizer_identity", "quantization", "runtime_revision", "runtime_binary_sha256", "compiler_binary_sha256", "prompt_sha256", "grammar_sha256", "compiler_revision", "schema_sha256", "split_integrity_evidence_sha256", "independent_review_evidence_sha256"}
    require(identity <= approval["experiment_identity"].keys() and all(approval["experiment_identity"][k] for k in identity), "Incomplete experiment identities")
    cfg = read(ROOT / "configs/local-parser.json")
    identity = approval["experiment_identity"]
    for key in ["model_sha256", "runtime_revision", "prompt_sha256", "grammar_sha256", "schema_sha256"]:
        require(identity[key] == cfg[key], f"Approved {key} differs from pinned inference config")
    require(approval["target_hardware"]["threads"] == cfg["cpu_threads"], "Approved thread count differs from inference config")


def freeze(approval, out, previous=None):
    gates, protocol = read(GATES), read(PROTOCOL)
    validate_approval(approval, gates, protocol)
    require(approval["experiment_identity"]["compiler_binary_sha256"] == sha(ROOT / "target/debug/verity"), "Compiler binary differs from approval")
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True), "Freeze requires a clean committed checkout")
    prior = unseal(read(previous)) if previous else None
    require((prior is None and approval.get("revision") == 1) or (prior is not None and approval.get("revision") == prior["approval"]["revision"] + 1 and approval.get("change_reason")), "Version changes and explain threshold/protocol revisions")
    payload = {"version": 1, "kind": "preregistration", "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(),
               "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "approval": approval, "gates": gates, "protocol": protocol, "scoring_version": SCORING,
               "previous_sha256": digest(prior) if prior else None,
               "inputs": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in artifact_paths()]}
    require(approval["experiment_identity"]["compiler_revision"] == payload["source_revision"], "Approval must bind current compiler/source revision")
    write_new(out, seal(payload))


def authorize_locked(frozen, operator, out):
    """Metadata admission only, before any external operator may open private payloads."""
    value = read(frozen)
    payload = unseal(value)
    require(payload["kind"] == "preregistration", "No preregistration")
    validate_approval(payload["approval"], payload["gates"], payload["protocol"])
    require(payload["source_revision"] == payload["approval"]["experiment_identity"]["compiler_revision"], "Compiler revision mismatch")
    require(timestamp(payload["approval"]["approved_at"]) <= timestamp(payload["frozen_at"]), "Approval must precede freeze")
    require({i["path"] for i in payload["inputs"]} == {str(p.relative_to(ROOT)) for p in artifact_paths()}, "Incomplete frozen inputs")
    require(payload["gates"] == read(GATES) and payload["protocol"] == read(PROTOCOL), "Frozen protocol changed")
    for item in payload["inputs"]:
        require(sha(ROOT / item["path"]) == item["sha256"], "Frozen input changed")
    require(operator.get("action") == "authorize_one_external_locked_evaluation" and operator.get("operator")
            and operator.get("authorization_provenance") and operator.get("freeze_sha256") == value["sha256"], "Missing explicit operator authorization")
    require(operator.get("authorized_at") and timestamp(operator["authorized_at"]) >= timestamp(payload["frozen_at"])
            and timestamp(operator["authorized_at"]) <= dt.datetime.now(dt.timezone.utc), "Authorization must follow freeze")
    commitment = read(ROOT / "configs/locked-holdout-commitment.json")
    require(operator.get("benchmark_sha256") == commitment["benchmark_sha256"]
            and operator.get("bundle_sha256") == commitment["bundle_sha256"]
            and operator.get("split") == commitment["split"]
            and operator.get("cases") == commitment["cases"]
            and operator.get("split_integrity_verified") is True, "Locked split identity/integrity mismatch")
    # Exclusive receipt prevents reuse at this location. Custody and cross-host single-use
    # enforcement belong to the external operator; this is not a signature service.
    write_new(out, seal({"kind": "external_operator_admission_only", "freeze_sha256": value["sha256"],
                         "operator": operator, "payload_opened": False, "public_runner_enabled": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["report", "replay"]:
        p = sub.add_parser(command)
        p.add_argument("--evidence", type=Path, default=ROOT / "reports/local-parser-development")
        p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("assess")
    p.add_argument("summary", type=Path)
    p.add_argument("--gates", type=Path, default=GATES)
    p.add_argument("--approval", type=Path, default=APPROVAL)
    p = sub.add_parser("verify")
    p.add_argument("manifest", type=Path)
    p.add_argument("--check-inputs", action="store_true")
    p = sub.add_parser("compare")
    p.add_argument("runs", nargs=2, type=Path)
    p = sub.add_parser("freeze")
    p.add_argument("--approval", type=Path, default=APPROVAL)
    p.add_argument("--previous", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("authorize-locked")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--operator-record", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command in {"report", "replay"}:
        args.out.mkdir(parents=True, exist_ok=False)
        try:
            if args.command == "replay":
                replay(args.evidence, args.out)
                write_new(args.out / "run.json", {"results": {}, "mode": "replay_no_inference",
                    "saved_input_sha256": {str(p): sha(p) for p in args.evidence.glob("*-report.json")},
                    "source_run_sha256": sha(args.evidence / "run.json"),
                    "artifact_sha256": read(args.evidence / "run.json").get("artifact_sha256", {})})
            build_report(args.out if args.command == "replay" else args.evidence, args.out, args.command == "replay")
        except BaseException as error:
            write_new(args.out / "failure.json", {"status": "failed", "error": str(error)})
            raise
    elif args.command == "assess":
        manifest = verify_manifest(args.summary.parent / "manifest.json")
        require(args.summary.name in manifest["outputs"], "Summary is not covered by run manifest")
        print(json.dumps(assess(read(args.summary), read(args.gates), read(args.approval)), indent=2))
    elif args.command == "verify":
        verify_manifest(args.manifest, args.check_inputs)
        print("Manifest and outputs verified" + ("; current inputs verified" if args.check_inputs else "; input identities retained, not reread"))
    elif args.command == "compare":
        runs = [verify_manifest(p / "manifest.json") for p in args.runs]
        require(runs[0]["scoring_version"] == runs[1]["scoring_version"], "Different scoring policies; explicitly rescore saved outputs")
        print(json.dumps([{ "manifest_sha256": read(p / "manifest.json")["sha256"],
                            "metrics": {k: v["metrics"] for k, v in read(p / "summary.json")["datasets"].items()}}
                          for p in args.runs], indent=2))
    elif args.command == "freeze":
        freeze(read(args.approval), args.out, args.previous)
    else:
        authorize_locked(args.freeze, read(args.operator_record), args.out)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        sys.exit(f"Phase 0 failed closed: {error}")
