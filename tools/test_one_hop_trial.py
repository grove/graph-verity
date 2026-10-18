"""Model-free saved-draft and resource-stop regressions for #74."""
import json
import subprocess
import unittest

import one_hop_trial as t


class OneHopTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["cargo", "build", "--quiet", "--locked", "--offline", "-p", "verity_cli"],
                       cwd=t.ROOT, check=True)
        cls.folder = t.REPORT / "freeze"
        cls.saved = t.n.read(t.REPORT / "replay-controls.json")

    def test_saved_raw_drafts_replay_through_rust_without_execution(self):
        cases = {c["id"]: c for c in t.cases()}
        for control in self.saved:
            with self.subTest(control=control["name"]):
                outcome = t.score_saved(cases[control["record"]["id"]], control["record"],
                                        control["stage"], self.folder, t.BINARY)
                for key, expected in control["expected"].items():
                    self.assertEqual(outcome[key], expected, key)
                self.assertEqual(outcome["execution_provenance"], "no_execution")
                self.assertFalse(outcome["model_abstention_correct"])
                self.assertIsNone(outcome["exact_answer_set"])

    def test_model_origin_is_distinct_from_fixture_and_host_block(self):
        case = next(c for c in t.cases() if c["expected_status"] == "needs_clarification")
        record = dict(id=case["id"], runtime_status="completed", origin="model",
                      raw_response=json.dumps(case["gold_draft"]))
        self.assertTrue(t.score_saved(case, record, "oracle", self.folder, t.BINARY)["model_abstention_correct"])
        record["origin"] = "fixture"
        self.assertFalse(t.score_saved(case, record, "oracle", self.folder, t.BINARY)["model_abstention_correct"])
        record.update(runtime_status="error", raw_response=None)
        self.assertEqual(t.score_saved(case, record, "oracle", self.folder, t.BINARY)["category"], "runtime_error")

    def test_wrong_executable_plan_with_coincidentally_equal_answer_is_not_semantic_success(self):
        case = next(c for c in t.cases() if c["task_family"] == "explicit_no_match")
        draft = dict(case["gold_draft"], predicate=1004)
        _, preview = t.n.rust_preview(case, json.dumps(draft), t.BINARY)
        self.assertIsNotNone(preview)
        record = dict(id=case["id"], runtime_status="completed", origin="fixture", raw_response=json.dumps(draft),
            decision="approved", approval_id=preview["preview"]["approval_id"], execution=dict(
                status="executed", plan=preview["preview"]["plan"], snapshot_id=preview["request"]["snapshot_id"],
                scope=preview["request"]["scope"], complete_within_scope=True,
                evidence_complete_for_returned_rows=True, bindings=case["full_bindings"]))
        # Saved operator claims only; this test never executes or approves a query.
        outcome = t.score_saved(case, record, "oracle", self.folder, t.BINARY)
        self.assertTrue(outcome["exact_answer_set"])
        self.assertFalse(outcome["strict_semantic_and_answer_success"])
        self.assertEqual(outcome["category"], "valid_draft_semantically_wrong")
        record["approval_id"] = "stale"
        with self.assertRaisesRegex(ValueError, "Approval mismatch"):
            t.score_saved(case, record, "oracle", self.folder, t.BINARY)

    def test_fail_closed_resource_checks_and_full_blocked_denominators(self):
        host = dict(commands=[], load_per_cpu=0.1, swap_used_mib=0, memory_free_percent=80,
                    disk_free_gib=100, max_process_cpu_percent=10, competing_model_processes=[])
        cfg = t.n.read(t.CONFIG)
        self.assertEqual(t.host_blockers(host, cfg), [])
        with self.assertRaisesRegex(ValueError, "Host did not block"):
            t.blocked_decision(self.folder, host)
        for key in ["load_per_cpu", "swap_used_mib", "memory_free_percent", "disk_free_gib", "max_process_cpu_percent"]:
            unavailable = dict(host, **{key: None})
            self.assertTrue(t.host_blockers(unavailable, cfg))
        host["load_per_cpu"] = 2
        decision = t.blocked_decision(self.folder, host)
        self.assertEqual(decision["decision"], "INCONCLUSIVE_REVISE")
        self.assertIsNone(decision["model_ranking"])
        self.assertFalse(decision["integration_authorized"])
        self.assertEqual(set(decision["variants"]), {"qwen35", "gemma4"})
        self.assertEqual(sum(len(s["cases"]) for m in decision["variants"].values() for s in m.values()), 120)
        for model in decision["variants"].values():
            for stage in model.values():
                self.assertEqual(stage["denominators"], dict(candidate=18, needs_clarification=6, unsupported=6))
                self.assertIsNone(stage["semantic_accuracy"])
                self.assertEqual(stage["attempted"], 0)

    def test_contexts_do_not_contain_reference_fields_and_retrieval_is_gold_independent(self):
        forbidden = {"gold_request", "gold_draft", "full_bindings", "expected_status", "direction", "resolved_start", "blocked"}
        for path in (self.folder / "contexts").glob("*.json"):
            context = t.n.read(path)
            self.assertFalse(forbidden & context.keys())
            # Source packet navigation may describe observed directions; no gold direction is added.
            self.assertNotIn("gold_request", context)
        # Retrieval has its own source-audited missing-ID denominator, independent of any model output.
        coverage = t.n.read(self.folder / "coverage.json")
        self.assertEqual(coverage["case_count"], 30)
        self.assertEqual(coverage["at_k"]["20"]["role_graph_coverage"]["entity"]["total"], 18)
        self.assertEqual(coverage["at_k"]["20"]["role_graph_coverage"]["predicate"]["total"], 18)

    def test_committed_freeze_and_decision_replay_without_models(self):
        t.verify(self.folder, t.BINARY)
        self.assertEqual(t.n.read(t.REPORT / "decision.json"),
                         t.blocked_decision(self.folder, t.n.read(t.REPORT / "host.json")))


if __name__ == "__main__":
    unittest.main()
