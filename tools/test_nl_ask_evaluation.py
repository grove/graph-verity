"""#76's evidence audit never promotes fixtures, missing runs or synthetic approvals."""
import copy
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import nl_ask_evaluation as e


class NLAskEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["cargo", "build", "--quiet", "--locked", "--offline", "-p", "verity_cli"],
                       cwd=e.ROOT, check=True)
        cls.report = e.calculate(e.t.BINARY)

    def test_committed_report_recalculates_without_weights_or_execution(self):
        self.assertEqual(self.report, e.t.n.read(e.REPORT / "evaluation.json"))
        self.assertEqual(e.t.n.read(e.REPORT / "checksums.json"), e.t.v.inventory(e.REPORT))
        self.assertFalse(self.report["inference_performed"])
        self.assertFalse(self.report["holdout_accessed"])
        self.assertEqual(self.report["decision"], "INCONCLUSIVE_REVISE")
        self.assertEqual(self.report["human"]["consenting_participants"], 0)
        self.assertIsNone(self.report["human"]["confidently_wrong_accepted_plans"])
        for key in ["model_faithful_plans", "strict_answer_sets", "model_clarifications",
                    "model_unsupported", "wrong_but_executable"]:
            self.assertIsNone(self.report["summary"][key]["numerator"])

    def test_all_denominators_and_receipts_are_preserved(self):
        inventory = self.report["run_inventory"]
        self.assertEqual(len(inventory), 120)
        self.assertEqual(len({(c["variant"], c["stage"], c["id"]) for c in inventory}), 120)
        for row in inventory:
            self.assertIsNone(row["raw_output"])
            self.assertIsNone(row["execution"])
        self.assertEqual(len(self.report["cases"]), 30)
        self.assertEqual(len(self.report["summary"]["missing_predicate_cases"]), 12)
        for row in self.report["cases"]:
            receipt = row["packet_receipt"]
            self.assertEqual(receipt["sha256"], self.report["source_sha256"][receipt["path"]])
            self.assertIsNone(row["strict_answer_exactness"])

    def test_reference_and_negative_controls_are_separate_from_model_and_humans(self):
        controls = {c["name"]: c for c in self.report["fixture_controls"]}
        self.assertEqual(controls["valid_but_inverse"]["outcome"]["category"], "valid_draft_semantically_wrong")
        self.assertTrue(controls["dropped_named_constant"]["outcome"]["dropped_or_changed_named_constant"])
        for row in self.report["reference_previews"] + list(controls.values()):
            self.assertEqual(row["approval"], "not_requested")
            self.assertIsNone(row["execution"])
        empty = next(c for c in self.report["cases"] if c["task_family"] == "explicit_no_match")
        self.assertEqual(empty["reference_answer_status"], "no_stored_match")
        self.assertEqual(empty["reference_bindings"], [])
        self.assertIsNone(empty["graph_execution"])

    def test_changed_receipts_and_fabricated_success_fail_verification(self):
        for mutate in [lambda r: r.update(decision="GO"),
                       lambda r: r["human"].update(consenting_participants=1),
                       lambda r: r["source_sha256"].update({"configs/nl-ask-evaluation-v1.json": "0" * 64}),
                       lambda r: r["run_inventory"].pop()]:
            changed = copy.deepcopy(self.report)
            mutate(changed)
            with tempfile.TemporaryDirectory() as temp:
                path = e.Path(temp) / "evaluation.json"
                path.write_text(json.dumps(changed))
                with patch.object(e, "calculate", return_value=self.report), patch("sys.argv", [
                        "nl_ask_evaluation.py", "verify", "--out", str(path)]):
                    with self.assertRaisesRegex(ValueError, "Evaluation differs"):
                        e.main()


if __name__ == "__main__":
    unittest.main()
