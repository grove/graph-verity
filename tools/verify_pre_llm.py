#!/usr/bin/env python3
"""Read-only pre-LLM verification. Requires the pinned Rust and Python dependencies.

Only dependency acquisition may use the network. No capture, gold creation, model,
held-out candidate evaluation, source modification, or Git write is performed.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "pre-llm"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def oracle_summary(report: dict, benchmark: dict) -> dict:
    """Keep executable checks distinct from fixture abstention bookkeeping."""
    require(report["mode"] == "oracle_no_model", "Expected model-free oracle mode")
    require(report["model"] is None, "A model must not be recorded in an oracle run")
    require(report["split"] == "dev", "This command only evaluates development cases")
    expected = {c["id"]: c for c in benchmark["cases"] if c["split"] == "dev"}
    scored = {c["id"]: c for c in report["cases"]}
    require(len(scored) == len(report["cases"]), "Duplicate scored case")
    require(set(expected) == set(scored), "Report is missing or adding development cases")
    executable = [scored[k] for k, c in expected.items() if c["expected_status"] == "executed"]
    abstention = [scored[k] for k, c in expected.items() if c["expected_status"] != "executed"]
    require(bool(executable), "No executable development cases")
    require(all(c["stage"] == "scored" and c["passed"] and c["exact_result_set"] is True
                and c["structural_ir_exact"] is True for c in executable),
            "An executable oracle check failed")
    require(all(c["stage"] == "fixture_status_only" and c["passed"]
                and c["exact_result_set"] is None and c["pipeline_ms"] is None for c in abstention),
            "Abstention bookkeeping was incorrectly scored as execution")
    require(report["passed"] == report["total"] == len(expected), "Inconsistent report totals")
    return {
        "snapshot_id": report["snapshot_id"],
        "executable_checks_passed": len(executable),
        "executable_checks_total": len(executable),
        "recorded_abstention_cases_not_model_tested": len(abstention),
        "model_accuracy": None,
        "model_abstention_accuracy": None,
        "interpretation": "compiler_oracle_against_machine_authored_human_review_pending_gold",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "status": "running",
        "platform": platform.platform(),
        "logical_cpus_visible": os.cpu_count(),
        "python": sys.version,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "commands": [],
        "model_invoked": False,
        "holdout_evaluated": False,
    }
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        state["cpu_model"] = next((line.split(":", 1)[1].strip()
                                   for line in cpuinfo.read_text().splitlines()
                                   if line.startswith("model name")), None)

    def save() -> None:
        (OUT / "verification.json").write_text(json.dumps(state, indent=2) + "\n")

    def run(label: str, args: list[str], *, should_succeed: bool = True) -> str:
        print(f"[{label}] {' '.join(args)}", flush=True)
        started = time.monotonic()
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=600)
        (OUT / f"{label}.stdout.txt").write_text(result.stdout)
        (OUT / f"{label}.stderr.txt").write_text(result.stderr)
        state["commands"].append({"label": label, "args": args,
                                  "returncode": result.returncode,
                                  "expected_success": should_succeed,
                                  "elapsed_seconds": time.monotonic() - started})
        save()
        require((result.returncode == 0) == should_succeed,
                f"{label}: unexpected exit {result.returncode}; see captured logs")
        return result.stdout

    def cli(label: str, *args: str, should_succeed: bool = True) -> str:
        return run(label, ["cargo", "run", "--locked", "--offline", "--quiet",
                           "-p", "verity_cli", "--", *args], should_succeed=should_succeed)

    try:
        state["git_commit"] = run("git-revision", ["git", "rev-parse", "HEAD"]).strip()
        run("initial-clean-tree", ["git", "diff", "--exit-code", "HEAD"])
        state["rustc"] = run("rust-version", ["rustc", "-Vv"]).strip()
        run("reporting-tests", [sys.executable, "-m", "unittest", "discover",
                                "-s", "tools", "-p", "test_verify_pre_llm.py", "-v"])
        run("dependency-fetch", ["cargo", "fetch", "--locked"])
        run("format", ["cargo", "fmt", "--all", "--check"])
        run("clippy", ["cargo", "clippy", "--workspace", "--all-targets", "--locked",
                       "--offline", "--", "-D", "warnings"])
        run("rust-tests", ["cargo", "test", "--workspace", "--locked", "--offline"])
        cli("smoke", "smoke", "tests/fixtures/smoke.trig", "trig")
        run("dataset-verify", [sys.executable, "tools/dataset.py", "verify"])
        rebuilt = OUT / "rebuilt.nq"
        run("dataset-rebuild", [sys.executable, "tools/dataset.py", "rebuild", str(rebuilt)])
        require(rebuilt.read_bytes() == (ROOT / "data/wikidata/snapshot.nq").read_bytes(),
                "Derived snapshot is not byte-reproducible")
        run("gold-verify", [sys.executable, "tools/benchmark.py", "verify"])
        schema = json.loads(cli("schema", "schema"))
        require(schema == json.loads((ROOT / "schemas/contracts-v1.json").read_text()),
                "Committed JSON contracts differ from Rust types")
        rdf, fmt = "data/wikidata/snapshot.nq", "nquads"
        policy, scope = "data/wikidata/policy.json", "data/wikidata/scope.json"
        cli("inspect", "inspect", rdf, fmt)
        catalog = cli("catalog-first", "catalog", rdf, fmt, policy, scope)
        require(json.loads(catalog) == json.loads(cli("catalog-second", "catalog", rdf, fmt, policy, scope)),
                "Catalog differs between independent imports")
        cli("oracle", "evaluate", rdf, fmt, policy, "benchmarks/wikidata.json", "dev", str(OUT / "oracle"))
        report = json.loads((OUT / "oracle/report.json").read_text())
        benchmark = json.loads((ROOT / "benchmarks/wikidata.json").read_text())
        summary = oracle_summary(report, benchmark)
        manual = json.loads(cli("manual", "run", rdf, fmt, policy, "examples/manual-plan.json"))
        replay = json.loads(cli("replay", "replay", rdf, fmt, policy, scope,
                                "examples/question.txt", "examples/fixture-response.json"))
        require(manual["status"] == replay["status"] == "executed", "Demo did not execute")
        require(manual["origin"] == "manual" and replay["result"]["origin"] == "fixture",
                "Demo origin is mislabeled")
        require(manual["bindings"] == replay["result"]["bindings"] and bool(manual["evidence"]),
                "Manual/fixture demo mismatch or missing evidence")
        require(manual["interpretation_correctness"] == "not_assessed"
                and manual["real_world_truth"] == "not_established", "Unsafe truth claim")
        cli("invalid-response", "replay", rdf, fmt, policy, scope,
            "examples/question.txt", "examples/invalid-response.json", should_succeed=False)
        abstained = json.loads(cli("unsupported-response", "replay", rdf, fmt, policy, scope,
                                   "examples/question.txt", "examples/unsupported-response.json"))
        require(abstained["status"] == "abstained"
                and abstained["proposal"]["status"] == "unsupported", "Fixture failed to abstain")
        run("final-clean-tree", ["git", "diff", "--exit-code", "HEAD"])
        state["summary"] = summary
        state["status"] = "passed"
        (OUT / "summary.md").write_text(
            "# Pre-LLM verification\n\n"
            f"Commit: `{state['git_commit']}`\n\n"
            f"Executable oracle checks: **{summary['executable_checks_passed']} / "
            f"{summary['executable_checks_total']}**.\n\n"
            f"Recorded abstention cases: **{summary['recorded_abstention_cases_not_model_tested']}**; "
            "not model-tested and excluded from executable accuracy.\n\n"
            "Formatting, Clippy, Rust tests, source hashes, byte-rebuild, independent gold, "
            "schema parity, deterministic catalog, manual/fixture evidence, and rejection demos passed.\n\n"
            "No language model was run. Gold is machine-authored and human-review pending. "
            "No independent locked holdout or target-device parser measurement has been completed. "
            "This is engineering readiness for a local parser experiment, not a Phase 0 go decision.\n")
        print(json.dumps(summary, indent=2), flush=True)
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        state["status"] = "failed"
        state["error"] = str(error)
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1
    finally:
        save()


if __name__ == "__main__":
    raise SystemExit(main())
