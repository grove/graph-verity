"""Only public saved evidence and tiny scoring cases; never invoke inference."""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from compact_ab import DATASETS, REPORT, case_record, case_table, compare, exact_answers, metrics, verified_archive
from local_parser import ROOT, config, evaluate
from phase0 import read, verify_manifest


class CompactABTests(unittest.TestCase):
    def test_names_terms_completeness_and_empty_projection_width(self):
        gold = read(ROOT / "benchmarks/adversarial.json")["cases"][0]
        execution = {"bindings": [{"v0": next(iter(gold["expected_bindings"][0].values()))}],
                     "plan": {"projection": [{"kind": "variable", "name": "v0"}]},
                     "complete_within_scope": True}
        self.assertEqual(exact_answers(execution, gold), (False, True))
        execution["complete_within_scope"] = False
        self.assertEqual(exact_answers(execution, gold), (False, False))
        execution["complete_within_scope"] = True
        execution["bindings"][0]["v0"] = {"kind": "literal", "value": "wrong", "language": "nb"}
        self.assertEqual(exact_answers(execution, gold), (False, False))
        empty = copy.deepcopy(gold)
        empty["expected_bindings"] = []
        execution["bindings"] = []
        execution["plan"]["projection"].append({"kind": "variable", "name": "v1"})
        self.assertEqual(exact_answers(execution, empty), (True, False))

    def test_preflight_invalid_abstention_and_backend_stay_failures(self):
        gold = read(ROOT / "benchmarks/adversarial.json")["cases"][0]
        request = {"scope": gold["scope"], "snapshot_id": gold["gold"]["snapshot_id"], "references": []}
        c = {"id": gold["id"], "family": gold["family"], "stage": "compact_expansion",
             "error_code": "compact_reason", "preflight_would_block": None, "detail": "invalid reason",
             "raw_response": "{}", "execution": None, "contract_valid": True, "json_valid": True,
             "proposal_status": "unsupported", "safety_valid": False, "structural_ir_exact": None,
             "end_to_end_ms": 1, "generation_ms": 1}
        runtime = {"content": "{}", "input_token_count": 10, "tokens_predicted": 2}
        invalid = case_record(c, gold, runtime, request, "prompt", "{}", True)
        self.assertFalse(invalid["model_abstention"])
        c.update(error_code="complexity", detail="Variable IDs must be in 0..12")
        limited = case_record(c, gold, runtime, request, "prompt", "{}", True)
        self.assertTrue(limited["expander_only_rejection"])
        self.assertFalse(limited["rust_compiler_rejection"])
        c.update(error_code="semantic_negation", preflight_would_block="semantic_negation", proposal_status="candidate")
        blocked = case_record(c, gold, runtime, request, "prompt", "{}", True)
        self.assertTrue(blocked["preflight_block"])
        self.assertFalse(blocked["rust_compiler_rejection"])
        c.update(stage="generation", raw_response=None, json_valid=None, contract_valid=None, safety_valid=None)
        backend = case_record(c, gold, None, request, "prompt", None, True)
        summary = metrics([invalid, blocked, backend])
        self.assertEqual(summary["strict_complete_exact"]["denominator"], 3)
        self.assertEqual(summary["strict_complete_exact"]["numerator"], 0)
        self.assertEqual(summary["model_abstention"]["numerator"], 0)
        self.assertEqual(summary["backend_failure"]["numerator"], 1)
        self.assertEqual(summary["missing_runtime_counts"], 1)

    def test_retained_experiment_recomputes_without_runtime(self):
        verify_manifest(REPORT / "manifest.json", check_inputs=True)
        result = compare()
        self.assertEqual(result, read(REPORT / "comparison.json"))
        self.assertEqual(case_table(result), (REPORT / "case-comparison.md").read_text())
        self.assertEqual(len(result["cases"]), 30)
        for route in ["v1", "v2"]:
            self.assertEqual(result["overall"][route]["strict_complete_exact"]["denominator"], 24)
            self.assertEqual(result["overall"][route]["correct_status_abstention"]["denominator"], 6)

    def test_all_saved_v2_outputs_replay_through_rust_without_model(self):
        subprocess.run(["cargo", "build", "--locked", "--offline", "--quiet", "-p", "verity_cli"],
                       cwd=ROOT, check=True)
        files = verified_archive(REPORT, "compact-manifest.json")
        responses = {}
        for dataset in DATASETS:
            for c in read(ROOT / f"benchmarks/{dataset}.json")["cases"]:
                prefix = f"run-1/{dataset}/{c['id']}/"
                responses[(c["question"], tuple(c["scope"]))] = json.loads(files[prefix + "runtime-response.json"])

        class SavedOutputs:
            def __init__(self, cfg, out):
                self.process, self.startup_seconds = SimpleNamespace(pid=os.getpid()), 0
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                pass
            def generate(self, prompt):
                context = json.loads(prompt.split('<|im_start|>user\n')[1].split('<|im_end|>')[0])
                return copy.deepcopy(responses[(context["question"], tuple(context["scope"]))])

        with tempfile.TemporaryDirectory() as directory, patch("local_parser.Server", SavedOutputs), \
             patch("local_parser.validate_grammar", return_value=False), contextlib.redirect_stdout(io.StringIO()):
            for dataset, split in zip(DATASETS, ["dev", "transfer_dev"]):
                out = Path(directory) / dataset
                evaluate(config("compact-v2"), out, dataset, split, SimpleNamespace(pids=[]))
                original = json.loads(files[f"run-1/{dataset}/report.json"])
                replay = read(out / "report.json")
                for a, b in zip(original["cases"], replay["cases"]):
                    for key in ["id", "stage", "error_code", "json_valid", "contract_valid", "safety_valid",
                                "proposal_status", "preflight_would_block", "expanded_plan", "raw_response",
                                "structural_ir_exact", "exact_result_set"]:
                        self.assertEqual(a.get(key), b.get(key), (dataset, a["id"], key))
                    self.assertEqual(a["execution"] is None, b["execution"] is None)
                    if a["execution"]:
                        for key in ["bindings", "scope", "snapshot_id", "plan", "evidence", "complete_within_scope"]:
                            self.assertEqual(a["execution"][key], b["execution"][key], (dataset, a["id"], key))


if __name__ == "__main__":
    unittest.main()
