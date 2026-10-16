#!/usr/bin/env python3
"""Isolated operator-only locked adapter. Never invoke with private inputs in CI/agents.

Admission and hardware checks happen BEFORE any private bundle or review is read.
All model requests, responses, evidence, diagnostics and logs stay in a new private
output directory outside this repository. Only metadata may be published by a human.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import traceback
import os
import platform
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from local_parser import ASSETS, Memory, config, evaluate, grammar_probes, verify_source
from phase0 import (GATES, PROTOCOL, ROOT, assess, authorize_locked, read, require, seal, sha,
                    summarize, unseal, write_new)
from verify_sealed_holdout import check_external_reviews


def private_path(path):
    path = path.resolve()
    require(not path.is_relative_to(ROOT), "Private inputs/outputs must be outside the public repository")
    return path


def check_hardware(approved):
    if platform.system() == "Darwin":
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        ram = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True))
    else:
        cpu = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name"))
        ram = next(int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:"))
    actual = {"cpu_model": cpu, "os": platform.platform(), "architecture": platform.machine(),
              "logical_cores": os.cpu_count(), "system_ram_bytes": ram, "accelerator": "none"}
    require(all(approved.get(k) == v for k, v in actual.items()), "Current hardware differs from frozen target")
    return actual


def run(args):
    require(not os.environ.get("CI") and not os.environ.get("GITHUB_ACTIONS"), "Locked evaluation is forbidden in CI")
    out = private_path(args.out)
    private_path(args.admission)
    # No private payload, review or integrity evidence is read before this admission.
    authorize_locked(args.freeze, read(args.operator_record), args.admission)
    frozen = unseal(read(args.freeze))
    approval = frozen["approval"]
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True), "Locked evaluation requires a clean frozen checkout")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == frozen["source_revision"], "Checkout differs from frozen source revision")
    require(sha(ROOT / "target/debug/verity") == approval["experiment_identity"]["compiler_binary_sha256"], "Compiler binary changed")
    hardware = check_hardware(approval["target_hardware"])
    cfg = config()
    require(sha(ASSETS / cfg["model_file"]) == cfg["model_sha256"], "Model asset changed")
    require(sha(ASSETS / "build/bin/llama-server") == approval["experiment_identity"]["runtime_binary_sha256"], "Runtime binary changed")
    verify_source(cfg)
    bundle, reviews, integrity_path = map(private_path, [args.bundle, args.reviews, args.split_integrity])
    identity = approval["experiment_identity"]
    require(sha(reviews) == identity["independent_review_evidence_sha256"]
            and sha(integrity_path) == identity["split_integrity_evidence_sha256"], "External evidence differs from freeze")
    integrity = read(integrity_path)
    commitment = read(ROOT / "configs/locked-holdout-commitment.json")
    require(integrity.get("benchmark_sha256") == commitment["benchmark_sha256"]
            and all(integrity.get(k) is True for k in ["public_cases_disjoint", "public_lineage_disjoint", "exposed_groups_excluded"])
            and integrity.get("reviewer") and integrity.get("provenance"), "External split-integrity review incomplete")
    require(check_external_reviews(bundle, reviews)["all_claimed_approved"], "Independent external case reviews incomplete")
    # The existing verifier checks ZIP bounds, all frozen byte identities, case IDs,
    # snapshot, split and denominators without printing questions or reference answers.
    with ZipFile(bundle) as archive:
        benchmark = json.loads(archive.read("holdout.json"))
    public_ids = {c["id"] for name in ["wikidata", "worldcities-transfer"] for c in read(ROOT / f"benchmarks/{name}.json")["cases"]}
    require(not public_ids & {c["id"] for c in benchmark["cases"]}, "Private/public case overlap")
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    memory = Memory()
    state = {"status": "running", "hardware": hardware, "freeze_sha256": read(args.freeze)["sha256"],
             "benchmark_sha256": commitment["benchmark_sha256"], "model": cfg,
             "original_split": commitment["split"], "transport_split": "transfer_dev",
             "transport_policy": "Private cases remapped only inside isolated adapter to reuse public Rust stdio evaluator; never public cases relabeled as holdout",
             "interpretation": "AI-authored reference agreement with externally asserted independent review; software cannot authenticate expertise"}
    # All subprocess logs produced by the existing runner go under this private root.
    with (out / "operator.log").open("x") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            grammar_probes(cfg, out / "grammar-probes")
            transport = copy.deepcopy(benchmark)
            for case in transport["cases"]:
                case["split"] = "transfer_dev"
            write_new(out / "transport.json", transport)
            memory.worker.start()
            state["timing_summary"] = evaluate(cfg, out / "evaluation", "worldcities-transfer", "transfer_dev", memory,
                                                benchmark_path=out / "transport.json")
            report = read(out / "evaluation/report.json")
            report["transport_benchmark_digest"] = report.pop("benchmark_digest")
            report["original_benchmark_sha256"] = commitment["benchmark_sha256"]
            report["split"] = commitment["split"]
            for case in report["cases"]:
                case["split"] = commitment["split"]
            write_new(out / "private-report.json", report)
            dataset_summary = summarize(report, benchmark, commitment["split"])
            write_new(out / "private-summary.json", dataset_summary)
            require(memory.samples and memory.error is None, "Incomplete RSS measurement")
            state["status"] = "completed_private_measurement_not_automatic_GO"
        except BaseException:
            traceback.print_exc()
            state["status"] = "failed_private_diagnostics_only"
            raise
        finally:
            memory.done.set()
            if memory.worker.is_alive():
                memory.worker.join(timeout=6)
            state.update(sampled_peak_rss_kib=memory.peak_kib, rss_samples=memory.samples,
                         rss_error=memory.error, cache="process_cold_OS_page_cache_not_evicted; cache_prompt=True")
            if state["status"] == "completed_private_measurement_not_automatic_GO":
                timing = state["timing_summary"]
                decision_input = {
                    "datasets": {"locked_holdout": dataset_summary},
                    "development_transfer_gap_absolute": None,
                    "user_facing_measurement": {"status": "not_measured", "unflagged_wrong_plan_answers": None},
                    "safety": {"unauthorized_execution_or_disclosure_count": None, "prohibited_execution_count": 0},
                    "target_cpu_measurements": {"status": "measured_frozen_target",
                        "warm_end_to_end_p95_seconds_max": timing["warm_end_to_end_ms"]["p95"] / 1000,
                        "cold_first_answer_seconds_max": timing["cold_first_answer_ms_page_cache_not_evicted"] / 1000,
                        "whole_process_peak_rss_gib_max": memory.peak_kib / 1024**2},
                    "prerequisites": {k: True for k in read(GATES)["prerequisites"]},
                    "preregistration_sha256": state["freeze_sha256"],
                    "gates_at_run_sha256": approval["gates_sha256"], "protocol_at_run_sha256": approval["protocol_sha256"],
                    "approved_before_first_holdout": True}
                # Oracle checks were not performed by this operator run. Never infer them.
                decision_input["prerequisites"]["oracle_regression_pass_fraction"] = None
                decision_input["gate_assessment"] = assess(decision_input, frozen["gates"], approval)
                write_new(out / "private-gate-assessment.json", decision_input)
            write_new(out / "private-run.json", state)
            log.flush()
            write_new(out / "private-manifest.json", seal({"version": 1, "kind": "private_locked_run",
                      "freeze_sha256": read(args.freeze)["sha256"], "state": state,
                      "files": {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["freeze", "operator-record", "admission", "bundle", "reviews", "split-integrity", "out"]:
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    try:
        run(args)
    except BaseException:
        # Exceptions from private parsing/execution may contain private case text.
        # Suppress tracebacks and payloads from the terminal; inspect private logs locally.
        print("Locked evaluation refused or failed; inspect the private output locally. No private diagnostics printed.", file=sys.stderr)
        return 1
    print("Private evaluation completed. No automatic gate decision or public publication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
