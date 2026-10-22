"""Regression tests for honest oracle report denominators; no RDF/model required."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import verify_pre_llm as verify
from verify_pre_llm import oracle_summary


class CommandLogsTests(unittest.TestCase):
    def test_timeout_preserves_partial_bytes_and_failed_command(self):
        partial = subprocess.TimeoutExpired(["git", "diff"], 600,
                                            output=b"partial stdout\xff", stderr=b"last test running\n")
        with tempfile.TemporaryDirectory() as directory, patch.object(verify, "OUT", Path(directory)), \
             patch.object(verify.platform, "platform", return_value="test-platform"), \
             patch.object(verify.subprocess, "run", side_effect=[
                 subprocess.CompletedProcess([], 0, "fixture-commit\n", ""), partial]):
            self.assertEqual(verify.main(), 1)
            self.assertEqual((verify.OUT / "initial-clean-tree.stdout.txt").read_bytes(), partial.output)
            self.assertEqual((verify.OUT / "initial-clean-tree.stderr.txt").read_bytes(), partial.stderr)
            state = json.loads((verify.OUT / "verification.json").read_bytes())
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["commands"][-1]["label"], "initial-clean-tree")
            self.assertTrue(state["commands"][-1]["timed_out"])
            self.assertIsNone(state["commands"][-1]["returncode"])

    def test_timeout_without_output_still_writes_empty_logs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(verify, "OUT", Path(directory)), \
             patch.object(verify.platform, "platform", return_value="test-platform"), \
             patch.object(verify.subprocess, "run", side_effect=subprocess.TimeoutExpired(["git"], 600)):
            self.assertEqual(verify.main(), 1)
            self.assertEqual((verify.OUT / "git-revision.stdout.txt").read_bytes(), b"")
            self.assertEqual((verify.OUT / "git-revision.stderr.txt").read_bytes(), b"")


class OracleSummaryTests(unittest.TestCase):
    def setUp(self):
        self.benchmark = {"cases": [
            {"id": "answer", "split": "dev", "expected_status": "executed"},
            {"id": "abstain", "split": "dev", "expected_status": "unsupported"},
            {"id": "held", "split": "review_candidate", "expected_status": "executed"},
        ]}
        self.report = {"mode": "oracle_no_model", "model": None, "split": "dev",
                       "snapshot_id": "test-snapshot", "passed": 2, "total": 2, "cases": [
            {"id": "answer", "stage": "scored", "passed": True,
             "exact_result_set": True, "structural_ir_exact": True, "pipeline_ms": 1.0},
            {"id": "abstain", "stage": "fixture_status_only", "passed": True,
             "exact_result_set": None, "structural_ir_exact": None, "pipeline_ms": None},
        ]}

    def test_abstentions_are_not_executable_accuracy(self):
        result = oracle_summary(self.report, self.benchmark)
        self.assertEqual(result["executable_checks_total"], 1)
        self.assertEqual(result["recorded_abstention_cases_not_model_tested"], 1)
        self.assertIsNone(result["model_accuracy"])
        self.assertIsNone(result["model_abstention_accuracy"])

    def test_failed_execution_cannot_hide_behind_passing_total(self):
        report = copy.deepcopy(self.report)
        report["cases"][0]["exact_result_set"] = False
        with self.assertRaises(ValueError):
            oracle_summary(report, self.benchmark)

    def test_missing_case_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["cases"].pop()
        with self.assertRaises(ValueError):
            oracle_summary(report, self.benchmark)

    def test_bookkeeping_cannot_be_relabelled_as_execution(self):
        report = copy.deepcopy(self.report)
        report["cases"][1]["stage"] = "scored"
        with self.assertRaises(ValueError):
            oracle_summary(report, self.benchmark)

    def test_model_and_non_development_modes_are_rejected(self):
        for key, value in [("mode", "parser_proposals"), ("model", "some-model"),
                           ("split", "review_candidate")]:
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                report[key] = value
                with self.assertRaises(ValueError):
                    oracle_summary(report, self.benchmark)


if __name__ == "__main__":
    unittest.main()
