"""Regression tests for honest oracle report denominators; no RDF/model required."""
import copy
import unittest
from verify_pre_llm import oracle_summary


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
