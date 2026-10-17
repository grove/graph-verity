"""Deterministic Phase 0 checks: no inference, private files, approvals or gold writes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phase0 import (APPROVAL, GATES, PROTOCOL, ROOT, annotate, assess, authorize_locked,
                    build_report, digest, freeze, rate, read, seal, sha, statistics, summarize,
                    unseal, verify_manifest, write_new)


class Phase0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = read(GATES)
        cls.approval = read(APPROVAL)
        cls.reference = read(ROOT / "benchmarks/wikidata.json")
        cls.report = read(ROOT / "reports/local-parser-development/wikidata-report.json")
        cls.baseline = summarize(cls.report, cls.reference, "dev")

    def case(self, **changes):
        c = copy.deepcopy(self.report["cases"][0])
        c.update(changes)
        return c

    def summary(self):
        return {"datasets": {"test": copy.deepcopy(self.baseline)},
                "development_transfer_gap_absolute": .079,
                "safety": {"unauthorized_execution_or_disclosure_count": None, "prohibited_execution_count": None},
                "target_cpu_measurements": {"status": "not_measured"},
                "prerequisites": {k: False for k in self.gates["prerequisites"]}}

    def ready_summary(self):
        summary = self.summary()
        d = summary["datasets"]["test"]
        for metric in ["exact_answer", "structural_ir", "correct_abstention"]:
            d["metrics"][metric] = rate(200, 200)
        d["metrics"]["false_abstention"] = rate(0, 200)
        d["per_family"] = {"test": {"exact_answer": rate(200, 200)}}
        summary["prerequisites"] = dict(self.gates["prerequisites"])
        summary["safety"] = {"unauthorized_execution_or_disclosure_count": 0, "prohibited_execution_count": 0}
        summary["target_cpu_measurements"].update({k: 1 for k in self.gates["cpu_go_proposal"]})
        summary.update(gates_at_run_sha256=digest(self.gates), protocol_at_run_sha256=digest(read(PROTOCOL)),
                       approved_before_first_holdout=True, preregistration_sha256="synthetic_test_only")
        return summary

    def approved(self):
        # Synthetic test record only, never written as real project approval.
        cfg = read(ROOT / "configs/local-parser.json")
        identity = {k: cfg[k] for k in ["model_sha256", "runtime_revision", "prompt_sha256", "grammar_sha256", "schema_sha256"]}
        identity.update({k: "synthetic_test_only" for k in ["tokenizer_identity", "quantization", "runtime_binary_sha256", "compiler_revision", "split_integrity_evidence_sha256", "independent_review_evidence_sha256"]})
        return {"status": "approved", "gates_sha256": digest(self.gates), "protocol_sha256": digest(read(PROTOCOL)),
                "approved_by": "synthetic_test_only", "approved_at": "2026-01-01T00:00:00+00:00", "provenance": "synthetic_test_only",
                "experiment_identity": {**identity, "compiler_binary_sha256": "synthetic_test_only"},
                "target_hardware": {k: 4 for k in ["cpu_model", "os", "architecture", "logical_cores", "threads", "system_ram_bytes", "accelerator", "measurement_configuration"]}}

    def test_historical_results_and_all_denominators_unchanged(self):
        m = self.baseline["metrics"]
        self.assertEqual(m["json_valid"]["numerator"], 41)
        self.assertEqual(m["json_valid"]["denominator"], 46)
        self.assertEqual(m["exact_answer"]["numerator"], 3)
        self.assertEqual(m["exact_answer"]["denominator"], 38)
        self.assertEqual(m["structural_ir"]["numerator"], 0)
        self.assertEqual(m["correct_abstention"]["denominator"], 8)
        self.assertEqual(m["wrong_plan_executed"]["numerator"], 19)

    def test_failures_false_abstention_and_f1_stay_in_supported_denominator(self):
        cases = [self.case(proposal_status="unsupported", safety_valid=None),
                 self.case(json_valid=False, contract_valid=False, proposal_status=None),
                 self.case(exact_result_set=True, precision=1, recall=1, f1=1)]
        m = statistics(cases)
        self.assertEqual(m["exact_answer"], rate(1, 3))
        self.assertEqual(m["false_abstention"], rate(1, 3))
        self.assertAlmostEqual(m["macro_answer_scores_all_supported"]["f1"], 1/3)

    def test_abstentions_do_not_turn_parser_errors_into_correct_refusals(self):
        c = self.case(expected_status="unsupported", proposal_status="parsing_error", passed=True)
        self.assertEqual(statistics([c])["correct_abstention"]["numerator"], 0)
        c["proposal_status"] = "unsupported"
        self.assertEqual(statistics([c])["correct_abstention"]["numerator"], 1)
        self.assertEqual(statistics([c], model=False)["status"], "not_measured_oracle_is_not_model_accuracy")

    def test_wilson_empty_and_small_zero_error_sets(self):
        self.assertIsNone(rate(0, 0)["value"])
        interval = rate(0, 3)["wilson_95"]
        self.assertGreater(interval[1], .5)
        self.assertGreater(rate(3, 3)["wilson_95"][0], .4)
        self.assertIsNone(statistics([])["macro_answer_scores_all_supported"]["f1"])

    def test_missing_duplicate_extra_cases_and_changed_snapshot_fail_closed(self):
        for mutate in [lambda r: r["cases"].pop(),
                       lambda r: r["cases"].append(r["cases"][0]),
                       lambda r: r.update(snapshot_id="wrong"),
                       lambda r: r["cases"][0].update(family="changed")]:
            r = copy.deepcopy(self.report)
            mutate(r)
            with self.assertRaises(ValueError):
                summarize(r, self.reference, "dev")

    def test_schema_failure_empty_results_unknown_missing_facts_and_retrieval(self):
        ref = self.reference["cases"][0]
        c = self.case(json_valid=False, contract_valid=False)
        a = annotate(c, ref, "test", "dev")
        self.assertEqual(a["failure_stage"], "json_generation")
        self.assertEqual(a["retrieval"]["status"], "not_applicable")
        self.assertEqual(a["missing_facts"]["status"], "not_measured")
        self.assertEqual(a["observed_user_facing_false_confidence"]["status"], "not_measured")
        c.update(json_valid=True, retrieval={"status": "failed", "mode": "external_candidates", "failure": "missing predicate"},
                 result_classification="empty_query_result_not_real_world_false")
        a = annotate(c, ref, "test", "dev")
        self.assertEqual(a["failure_stage"], "response_schema")
        self.assertEqual(a["retrieval"]["status"], "failed")
        self.assertEqual(a["missing_facts"]["status"], "not_measured")

    def test_missing_approvals_measurements_and_samples_prevent_go(self):
        result = assess(self.summary(), self.gates, self.approval)
        self.assertEqual(result["decision"], "NOT READY")
        self.assertIn("fail", {r["status"] for r in result["matrix"]})
        self.assertIn("unavailable", {r["status"] for r in result["matrix"]})
        summary = self.ready_summary()
        self.assertEqual(assess(summary, self.gates, self.approved())["decision"], "NOT READY")  # UI not measured

    def test_deterministic_go_revise_stop_and_unknown_threshold(self):
        # A measured UI is deliberately unavailable in normal reports. Supply that
        # measurement at the threshold mapping for decision-algorithm branch tests.
        s = self.ready_summary()
        s["user_facing_measurement"] = {"unflagged_wrong_plan_answers": 0}
        self.assertEqual(assess(s, self.gates, self.approved())["decision"], "GO")
        s["datasets"]["test"]["metrics"]["exact_answer"] = rate(100, 200)
        self.assertEqual(assess(s, self.gates, self.approved())["decision"], "REVISE")
        s["datasets"]["test"]["metrics"]["exact_answer"] = rate(3, 3)
        self.assertEqual(assess(s, self.gates, self.approved())["decision"], "REVISE")
        s["gates_at_run_sha256"] = "different_thresholds"
        self.assertEqual(assess(s, self.gates, self.approved())["decision"], "NOT READY")
        for key in s["safety"]:
            s["safety"][key] = 1
            self.assertEqual(assess(s, self.gates, self.approval)["decision"], "STOP")
            s["safety"][key] = 0
        bad = copy.deepcopy(self.gates)
        bad["quality_go_proposal"]["invented_min"] = .9
        with self.assertRaises(ValueError):
            assess(s, bad, self.approval)

    def test_fixture_parser_without_model_identity_is_not_model_accuracy(self):
        fixture = copy.deepcopy(self.report)
        fixture["model"] = None
        result = summarize(fixture, self.reference, "dev")
        self.assertFalse(result["model_predictions_scored"])
        self.assertNotIn("exact_answer", result["metrics"])

    def test_new_components_are_unavailable_in_historical_reports(self):
        self.assertEqual(self.baseline["metrics"]["components"]["variables"]["status"], "not_measured")
        self.assertIsNone(self.baseline["metrics"]["components"]["variables"]["numerator"])
        self.assertEqual(self.baseline["metrics"]["components"]["direction"]["status"], "measured")

    def test_manifest_tampering_outputs_inputs_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            write_new(p / "input.json", {"value": 1})
            write_new(p / "summary.json", {"value": 2})
            value = seal({"inputs": [{"path": str(p / "input.json"), "sha256": sha(p / "input.json")}],
                          "outputs": {"summary.json": sha(p / "summary.json")}})
            write_new(p / "manifest.json", value)
            verify_manifest(p / "manifest.json", True)
            with self.assertRaises(FileExistsError):
                write_new(p / "manifest.json", value)
            changed = copy.deepcopy(value)
            changed["payload"]["outputs"]["summary.json"] = "altered"
            with self.assertRaises(ValueError):
                unseal(changed)
            (p / "input.json").write_text("changed")
            verify_manifest(p / "manifest.json")  # original snapshot may live in an older checkout
            with self.assertRaises(ValueError):
                verify_manifest(p / "manifest.json", True)
            (p / "summary.json").write_text("changed")
            with self.assertRaises(ValueError):
                verify_manifest(p / "manifest.json")

    def test_oracle_aggregation_is_never_model_accuracy_and_modes_cannot_mix(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp)
            write_new(evidence / "run.json", read(ROOT / "reports/local-parser-development/run.json"))
            for name in ["wikidata", "worldcities-transfer"]:
                report = read(ROOT / f"reports/local-parser-development/{name}-report.json")
                report["mode"] = "oracle_no_model"
                report["model"] = None
                write_new(evidence / f"{name}-report.json", report)
            out = evidence / "out"
            out.mkdir()
            with patch("phase0.platform.platform", return_value="synthetic_os"), patch("phase0.subprocess.check_output", return_value="synthetic_test_only"):
                result = build_report(evidence, out)
            self.assertEqual(result["aggregate"]["status"], "not_measured_oracle_is_not_model_accuracy")
            self.assertNotIn("exact_answer", result["aggregate"])
            mixed = read(evidence / "wikidata-report.json")
            mixed["mode"] = "parser_proposals"
            mixed["model"] = "synthetic_test_only"
            (evidence / "wikidata-report.json").write_text(json.dumps(mixed))
            with self.assertRaisesRegex(ValueError, "Do not aggregate"):
                build_report(evidence, evidence / "never-written")

    def test_archived_public_reports_and_repeat_evidence_checksums(self):
        for name in ["phase-0-baseline", "phase-0-development-repeat"]:
            payload = verify_manifest(ROOT / f"reports/{name}/manifest.json")
            self.assertFalse(payload["holdout_accessed"])
        folder = ROOT / "reports/phase-0-development-repeat"
        expected = (folder / "evidence.sha256").read_text().split()[0]
        self.assertEqual(sha(folder / "evidence.tar.gz"), expected)

    def test_approved_freeze_is_immutable_versioned_and_requires_change_reason(self):
        approved = {**self.approved(), "revision": 1}
        original_sha = sha
        def test_sha(path):
            return "synthetic_test_only" if str(path).endswith("target/debug/verity") else original_sha(path)
        with tempfile.TemporaryDirectory() as tmp, patch("phase0.sha", side_effect=test_sha), \
             patch("phase0.subprocess.check_output", side_effect=lambda args, **kw: "" if "status" in args else "synthetic_test_only"):
            p = Path(tmp)
            freeze(approved, p / "v1.json")
            old = read(p / "v1.json")
            with self.assertRaises(FileExistsError):
                freeze(approved, p / "v1.json")
            changed = {**approved, "revision": 2}
            with self.assertRaises(ValueError):
                freeze(changed, p / "v2.json", p / "v1.json")
            changed["change_reason"] = "synthetic test revision only"
            freeze(changed, p / "v2.json", p / "v1.json")
            self.assertEqual(unseal(read(p / "v2.json"))["previous_sha256"], old["sha256"])
            self.assertEqual(read(p / "v1.json"), old)

    def test_unapproved_freeze_and_locked_admission_never_read_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            with self.assertRaises(ValueError):
                freeze(self.approval, p / "freeze.json")
            write_new(p / "freeze.json", seal({"kind": "preregistration", "approval": self.approval, "gates": self.gates, "protocol": read(PROTOCOL)}))
            with self.assertRaises(ValueError):
                authorize_locked(p / "freeze.json", {}, p / "admission.json")
            self.assertFalse((p / "admission.json").exists())
            # Admission validates metadata before any private file operation is possible.
            self.assertNotIn("holdout_path", authorize_locked.__code__.co_varnames)

    def test_locked_admission_binds_freeze_commitment_and_explicit_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            from phase0 import artifact_paths
            approved = self.approved()
            frozen = seal({"kind": "preregistration", "approval": approved,
                           "gates": self.gates, "protocol": read(PROTOCOL),
                           "source_revision": approved["experiment_identity"]["compiler_revision"],
                           "inputs": [{"path": str(x.relative_to(ROOT)), "sha256": sha(x)} for x in artifact_paths()],
                           "frozen_at": "2026-01-01T00:00:00+00:00"})
            write_new(p / "freeze.json", frozen)
            commitment = read(ROOT / "configs/locked-holdout-commitment.json")
            operator = {k: commitment[k] for k in ["benchmark_sha256", "bundle_sha256", "split", "cases"]}
            operator.update(action="authorize_one_external_locked_evaluation", operator="synthetic_test_only",
                            authorization_provenance="test_only", freeze_sha256=frozen["sha256"],
                            authorized_at="2026-01-02T00:00:00+00:00", split_integrity_verified=True)
            for key in ["freeze_sha256", "action", "benchmark_sha256", "split", "cases", "split_integrity_verified"]:
                bad = {**operator, key: None}
                with self.assertRaises(ValueError):
                    authorize_locked(p / "freeze.json", bad, p / "bad.json")
            authorize_locked(p / "freeze.json", operator, p / "admission.json")
            self.assertFalse(unseal(read(p / "admission.json"))["payload_opened"])
            with self.assertRaises(FileExistsError):
                authorize_locked(p / "freeze.json", operator, p / "admission.json")


if __name__ == "__main__":
    unittest.main()
