"""Exercise private adapter admission with nonexistent synthetic paths only."""
import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from locked_phase0 import private_path, run
from phase0 import APPROVAL, GATES, PROTOCOL, ROOT, read, seal, write_new


class LockedAdapterTests(unittest.TestCase):
    def args(self, path):
        return argparse.Namespace(**{name: path / name for name in ["freeze", "operator_record", "admission", "bundle", "reviews", "split_integrity", "out"]})

    def test_ci_refusal_precedes_all_private_file_access(self):
        with patch.dict(os.environ, {"CI": "true"}), patch("locked_phase0.authorize_locked") as admit:
            with self.assertRaisesRegex(ValueError, "forbidden in CI"):
                run(self.args(Path("/nonexistent")))
            admit.assert_not_called()

    def test_public_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            private_path(ROOT / "artifacts/never-private")

    def test_unapproved_run_never_opens_bundle_or_reviews(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory)
            args = self.args(path)
            write_new(args.operator_record, {})
            write_new(args.freeze, seal({"kind": "preregistration", "approval": read(APPROVAL),
                                        "gates": read(GATES), "protocol": read(PROTOCOL)}))
            with patch("locked_phase0.check_external_reviews") as reviews, patch("locked_phase0.ZipFile") as zipfile:
                with self.assertRaises(ValueError):
                    run(args)
                reviews.assert_not_called()
                zipfile.assert_not_called()
            self.assertFalse(args.out.exists())
            self.assertFalse(args.admission.exists())

class SyntheticAuthorizedAdapterTests(unittest.TestCase):
    def test_authorized_adapter_restores_locked_identity_and_keeps_private_artifacts(self):
        self.check_authorized_adapter("independent_human_review")

    def test_ai_reference_adapter_verifies_bundle_without_fabricating_human_reviews(self):
        self.check_authorized_adapter("ai_reference_only")

    def test_private_scope_violation_forces_stop_even_with_ai_waiver(self):
        self.check_authorized_adapter("ai_reference_only", violation=True)

    def check_authorized_adapter(self, reference_policy, violation=False):
        import copy
        import io
        import json
        import zipfile
        from types import SimpleNamespace
        from phase0 import digest
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            args = LockedAdapterTests().args(root)
            cfg = read(ROOT / "configs/local-parser.json")
            b = read(ROOT / "benchmarks/worldcities-transfer.json")
            b["cases"] = [copy.deepcopy(b["cases"][0])]
            b["cases"][0].update(id="synthetic-private-unit-test-only", split="locked_holdout")
            report = read(ROOT / "reports/local-parser-development/worldcities-transfer-report.json")
            report["cases"] = [copy.deepcopy(report["cases"][0])]
            report["cases"][0].update(id=b["cases"][0]["id"], family=b["cases"][0]["family"])
            approved = {"target_hardware": {}, "gates_sha256": digest(read(GATES)), "protocol_sha256": digest(read(PROTOCOL)),
                        "reference_policy": reference_policy,
                        "experiment_identity": {k: "synthetic-sha" for k in ["compiler_binary_sha256", "runtime_binary_sha256", "independent_review_evidence_sha256", "split_integrity_evidence_sha256"]}}
            if reference_policy == "ai_reference_only":
                args.reviews = None
                del approved["experiment_identity"]["independent_review_evidence_sha256"]
                approved["experiment_identity"]["owner_ai_gold_waiver_sha256"] = "synthetic-sha"
            if violation:
                report["cases"][0]["execution"] = {"scope": ["urn:unauthorized-synthetic-scope"],
                    "snapshot_id": b["snapshot_id"], "evidence": [], "complete_within_scope": True,
                    "evidence_complete_for_returned_rows": True, "validation_ms": 0, "query_ms": 0, "evidence_ms": 0}
            frozen = {"approval": approved, "source_revision": "synthetic-revision", "gates": read(GATES), "protocol": read(PROTOCOL)}
            write_new(args.freeze, seal(frozen))
            write_new(args.operator_record, {})
            commitment = read(ROOT / "configs/locked-holdout-commitment.json")
            write_new(args.split_integrity, {"benchmark_sha256": commitment["benchmark_sha256"],
                     "public_cases_disjoint": True, "public_lineage_disjoint": True, "exposed_groups_excluded": True,
                     "reviewer": "synthetic-test-only", "provenance": "synthetic-test-only"})
            args.bundle = root / "synthetic.zip"
            with zipfile.ZipFile(args.bundle, "w") as z:
                z.writestr("holdout.json", json.dumps(b))
            memory = SimpleNamespace(worker=MagicMock(), done=MagicMock(), samples=2, error=None, peak_kib=100)
            memory.worker.is_alive.return_value = False
            def evaluate_fake(cfg, out, dataset, split, memory, *, benchmark_path):
                self.assertEqual(split, "transfer_dev")
                transport = read(benchmark_path)
                self.assertEqual(transport["cases"][0]["split"], "transfer_dev")
                out.mkdir()
                write_new(out / "report.json", {**report, "split": split})
                return {"warm_end_to_end_ms": {"p95": 1}, "cold_first_answer_ms_page_cache_not_evicted": 2}
            def fake_sha(path):
                return cfg["model_sha256"] if Path(path).name == cfg["model_file"] else "synthetic-sha"
            with patch("locked_phase0.authorize_locked"), patch("locked_phase0.subprocess.check_output", side_effect=lambda cmd, **kw: "" if "status" in cmd else "synthetic-revision"), \
                 patch("locked_phase0.check_hardware", return_value={}), patch("locked_phase0.sha", side_effect=fake_sha), \
                 patch("locked_phase0.verify_source"), patch("locked_phase0.check_external_reviews", return_value={"all_claimed_approved": True}) as reviews, \
                 patch("locked_phase0.verify") as verify, \
                 patch("locked_phase0.grammar_probes"), patch("locked_phase0.Memory", return_value=memory), \
                 patch("locked_phase0.evaluate", side_effect=evaluate_fake):
                original_reviews = args.reviews
                args.reviews = root / "must-not-be-read" if reference_policy == "ai_reference_only" else None
                with self.assertRaisesRegex(ValueError, "human-review ledger|requires external case reviews"):
                    run(args)
                reviews.assert_not_called()
                verify.assert_not_called()
                args.reviews = original_reviews
                run(args)
                if reference_policy == "ai_reference_only":
                    reviews.assert_not_called()
                    verify.assert_called_once_with(args.bundle.resolve())
                else:
                    reviews.assert_called_once_with(args.bundle.resolve(), args.reviews.resolve())
                    verify.assert_not_called()
            result = read(args.out / "private-report.json")
            self.assertEqual(result["split"], "locked_holdout")
            self.assertEqual(result["cases"][0]["split"], "locked_holdout")
            self.assertIn("transport_benchmark_digest", result)
            self.assertTrue((args.out / "private-manifest.json").exists())
            assessment = read(args.out / "private-gate-assessment.json")
            self.assertEqual(assessment["gate_assessment"]["decision"], "STOP" if violation else "NOT READY")
            self.assertEqual(assessment["prerequisites"]["independent_human_gold_review"], reference_policy == "independent_human_review")
            state = read(args.out / "private-run.json")
            self.assertEqual(state["reference_policy"], reference_policy)
            if reference_policy == "ai_reference_only":
                self.assertIn("not expert-validated", state["interpretation"])
                self.assertIn("not expert-validated", assessment["evidence_class"])
                self.assertIn("not expert-validated", result["evidence_class"])
                self.assertIn("not expert-validated", read(args.out / "private-summary.json")["evidence_class"])
            self.assertEqual(args.out.stat().st_mode & 0o777, 0o700)

    def test_terminal_errors_are_sanitized(self):
        import io
        from locked_phase0 import main
        command = ["locked_phase0.py"]
        for key in ["freeze", "operator-record", "admission", "bundle", "reviews", "split-integrity", "out"]:
            command += ["--" + key, "/nonexistent"]
        errors = io.StringIO()
        with patch("sys.argv", command), patch("locked_phase0.run", side_effect=ValueError("synthetic-secret-question")), patch("sys.stderr", errors):
            self.assertEqual(main(), 1)
        self.assertNotIn("synthetic-secret-question", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
