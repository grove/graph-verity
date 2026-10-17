"""Synthetic observations only. No recruitment, human evidence, inference or holdout."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pilot_study as study


class PilotStudy(unittest.TestCase):
    def setUp(self):
        self.tasks = study.load(study.KIT / "tasks.json")
        self.protocol = "synthetic-unit-test-protocol"
        self.session = study.form(self.tasks, self.protocol, "en", "beginner", "fluent", "rehearsal")
        self.session["assessor"] = {"id": "R-0000000000000000", "role": "owner"}

    def complete(self, index=0):
        task, row = self.tasks[index], self.session["records"][index]
        row.update(status="completed", seconds=20, assisted=False, confidence=5,
                   checks=dict.fromkeys(task["checks"], True))
        if task["kind"] == "ask":
            row.update(decision=task["decision"], explained_before_approval=True)
        else:
            row["relevance"] = 4
        return row

    def report(self, sessions=None):
        return study.report([self.session] if sessions is None else sessions,
                            self.tasks, self.protocol, "rehearsal")

    def test_frozen_inputs_order_lineage_and_source_witnesses(self):
        protocol, tasks, identity = study.verify()
        self.assertEqual(protocol["order"], [t["id"] for t in tasks])
        self.assertEqual(len(identity), 64)
        self.assertEqual(protocol["actual_participants"], 0)
        for task in tasks:
            self.assertIsNone(task["reviewer"])
            self.assertTrue(task["lineage"] and task["ambiguity"] and task["target"])
            self.assertEqual(set(task["prompt"]), {"en", "nb"})
            if task["kind"] == "ask":
                self.assertIn("approval", task["checks"])
        with patch.object(study, "frozen_files", return_value={}):
            with self.assertRaises(ValueError):
                study.verify()

    def test_missing_abandoned_excluded_and_assistance_keep_denominators(self):
        self.complete(0)
        self.complete(1).update(status="abandoned", assisted=True)
        excluded = self.complete(2)
        excluded["status"] = "excluded"
        excluded["checks"]["entity"] = False
        self.session["records"].pop(3)
        result = self.report()
        tasks = result["tasks"]
        self.assertEqual(tasks["planned"], len(self.tasks))
        self.assertEqual(tasks["attempted"], 3)
        self.assertEqual(tasks["missing_records"], 1)
        self.assertEqual((tasks["abandoned"], tasks["excluded"], tasks["assisted"]), (1, 1, 1))
        self.assertEqual(tasks["success_per_planned"], study.rate(1, len(self.tasks)))
        self.assertEqual(tasks["confident_wrong"], study.rate(1, 3))
        self.assertEqual(result["participants"]["with_observed_failure"], 1)
        self.assertEqual(result["participants"]["completed_all"], 0)
        self.assertFalse(result["release_go"])

    def test_zero_people_rates_are_unmeasured_not_zero(self):
        result = study.report([], self.tasks, self.protocol)
        self.assertEqual(result["human_participants"], 0)
        self.assertEqual(result["human_task_attempts"], 0)
        self.assertEqual(result["status"], "blocked_pending_real_participants")
        for metric in ("incorrect_selection", "misunderstanding", "confident_wrong", "low_relevance"):
            self.assertEqual(result["tasks"][metric], study.rate(0, 0))
        self.assertIsNone(result["hypotheses_descriptive_only"]["comprehension_target_met"])

    def test_null_assessor_null_checks_no_invented_human_review(self):
        row = self.complete()
        self.session["assessor"] = None
        with self.assertRaises(ValueError):
            self.report()
        row["checks"] = dict.fromkeys(self.tasks[0]["checks"])
        result = self.report()
        self.assertEqual(result["tasks"]["unassessed_attempts"], 1)
        self.assertEqual(result["tasks"]["success_per_assessed"], study.rate(0, 0))
        self.assertEqual(result["tasks"]["confidence_unassessed"], 1)
        self.assertEqual(result["independent_assessors"], 0)

    def test_confident_wrong_detected_even_with_partial_assessment(self):
        row = self.complete()
        row["checks"]["entity"] = False
        row["checks"]["scope"] = None
        result = self.report()
        self.assertEqual(result["tasks"]["confident_wrong"], study.rate(1, 1))
        self.assertEqual(result["tasks"]["incorrect_selection"], study.rate(1, 1))
        self.assertTrue(result["hypotheses_descriptive_only"]["stop_for_confident_wrong"])

    def test_explanations_must_precede_approval_and_cancel_can_succeed(self):
        index = next(i for i, t in enumerate(self.tasks) if t["id"] == "A04")
        row = self.complete(index)
        self.assertEqual(self.report()["tasks"]["success_per_assessed"], study.rate(1, 1))
        for timing in (False, None):
            row["explained_before_approval"] = timing
            self.assertEqual(self.report()["tasks"]["success_per_planned"]["numerator"], 0)
        row["explained_before_approval"] = True
        row["decision"] = "approved"
        result = self.report()
        self.assertEqual(result["tasks"]["confident_wrong"], study.rate(1, 1))
        self.assertEqual(result["tasks"]["decisions"]["approved"], 1)
        self.assertEqual(result["tasks"]["failures"]["approval"], study.rate(1, 1))
        row["decision"] = None
        self.assertEqual(self.report()["tasks"]["assessed"], 0)
        row.update(decision="approved", explained_before_approval=None)
        self.assertEqual(self.report()["tasks"]["confident_wrong"], study.rate(1, 1))

    def test_duplicates_reordering_unknowns_mixed_modes_and_protocols_rejected(self):
        bad = []
        for mutation in (
            lambda s: s["records"].append(s["records"][0]),
            lambda s: s["records"].reverse(),
            lambda s: s["records"][0].update(task_id="unknown"),
            lambda s: s.update(kind="human"),
            lambda s: s.update(protocol_id="wrong"),
            lambda s: s.update(consent=False),
            lambda s: s.update(participant="Alice"),
            lambda s: s["records"][0].update(seconds=1),
        ):
            session = copy.deepcopy(self.session)
            mutation(session)
            bad.append(session)
        for session in bad:
            with self.subTest(session=session), self.assertRaises(ValueError):
                self.report([session])
        with self.assertRaises(ValueError):
            self.report([self.session, copy.deepcopy(self.session)])

    def test_private_fields_and_invalid_values_rejected_at_every_level(self):
        for key in ("query", "quote", "email", "credential", "recording", "rdf", "explanation", "url"):
            for level in ("session", "record", "assessor", "checks"):
                session = copy.deepcopy(self.session)
                target = {"session": session, "record": session["records"][0],
                          "assessor": session["assessor"], "checks": session["records"][0]["checks"]}[level]
                target[key] = "SENSITIVE_CANARY"
                with self.subTest(key=key, level=level), self.assertRaises(ValueError):
                    self.report([session])
        row = self.complete()
        for field, value in (("confidence", True), ("confidence", 6), ("relevance", "5"),
                             ("seconds", -1), ("seconds", 1.5), ("assisted", "yes")):
            saved = row[field]
            row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.report()
            row[field] = saved

    def test_participant_task_and_subgroup_denominators_are_separate(self):
        self.complete()
        other = copy.deepcopy(self.session)
        other.update(participant="S-1111111111111111", language="nb", experience="experienced", language_proficiency="basic")
        other["records"][0]["checks"]["entity"] = False
        result = self.report([self.session, other])
        self.assertEqual(result["participants"]["enrolled"], 2)
        self.assertEqual(result["tasks"]["planned"], 2 * len(self.tasks))
        self.assertEqual(result["by_language"]["nb"]["confident_wrong"], study.rate(1, 1))
        self.assertEqual(result["by_experience"]["beginner"]["attempted"], 1)
        self.assertEqual(result["by_task_type"]["bilingual_label"]["planned"], 2)
        self.assertEqual(result["participants"]["confident_wrong"], study.rate(1, 2))
        self.assertEqual(result["participants"]["incorrect_selection"], study.rate(1, 2))
        serialized = json.dumps(result)
        for private in (self.session["participant"], self.session["assessor"]["id"]):
            self.assertNotIn(private, serialized)
        self.assertNotIn('"records":', serialized)
        self.assertEqual(result["human_participants"], 0)

    def test_no_automatic_release_go_even_if_all_hypotheses_pass(self):
        for i in range(len(self.tasks)):
            self.complete(i)
        sessions = []
        for i in range(5):
            session = copy.deepcopy(self.session)
            session.update(participant=f"S-{i:016x}", kind="human")
            sessions.append(session)
        result = study.report(sessions, self.tasks, self.protocol)
        self.assertTrue(result["hypotheses_descriptive_only"]["sample_target_met"])
        self.assertTrue(result["hypotheses_descriptive_only"]["comprehension_target_met"])
        self.assertFalse(result["release_go"])
        self.assertEqual(result["owner_assessors"], 1)
        self.assertEqual(result["independent_assessors"], 0)

    def test_rehearsal_deterministic_and_not_human_evidence(self):
        a = study.rehearsal(self.tasks, self.protocol)
        self.assertEqual(a, study.rehearsal(self.tasks, self.protocol))
        self.assertEqual(a["human_participants"], 0)
        self.assertEqual(a["human_task_attempts"], 0)
        self.assertEqual(a["synthetic_participants"], 1)
        self.assertEqual(a["tasks"]["attempted"], 2)
        self.assertFalse(a["holdout_accessed"])

    def test_json_privacy_size_duplicate_keys_and_exclusive_private_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "form.json"
            for raw in ('{"consent": true, "consent": false}', '{"seconds": NaN}', 'x' * (1024 * 1024 + 1)):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    study.load(path)
            path.unlink()
            study.write_new(path, {"a": 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                study.write_new(path, {"a": 2})
            self.assertEqual(study.load(path), {"a": 1})
            with self.assertRaises(ValueError):
                study.private_path(path)
            self.assertTrue(study.private_path(study.PRIVATE / "form.json").is_relative_to(study.PRIVATE))

    def test_cli_requires_consent_and_does_not_echo_payloads(self):
        command = [sys.executable, str(study.ROOT / "tools/pilot_study.py")]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "SENSITIVE_CANARY.json"
            result = subprocess.run(command + ["init", "--language", "en", "--experience", "beginner",
                                               "--language-proficiency", "fluent", "--out", str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertNotIn("SENSITIVE_CANARY", result.stdout + result.stderr)
            result = subprocess.run(command + ["rehearse", "--out", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(study.load(output)["human_participants"], 0)

    def test_synthetic_bundle_really_has_shared_terms_and_independent_caps(self):
        from local_find import Bundle
        binary = study.ROOT / "target/debug/verity"
        subprocess.run(["cargo", "build", "--locked", "--offline", "-q", "-p", "verity_cli"],
                       cwd=study.ROOT, check=True)
        for policy, limit in (("policy.json", 50), ("clipped-policy.json", 1)):
            bundle = Bundle(binary, study.KIT / "snapshot.nq", "nquads", study.KIT / policy,
                            study.KIT / "scope.json", study.KIT / "discovery.json")
            try:
                request = {"version": 1, "snapshot_id": bundle.snapshot, "scope": bundle.scope,
                           "limit": limit, "template": {"kind": "follow_path", "start": "urn:pilot:start",
                           "steps": [{"graph": "urn:pilot:graph", "predicate": "urn:pilot:" + p, "direction": "forward"}
                                     for p in ("owns", "value")], "filter": None, "output": "values"}}
                preview = bundle.ask(request)
                result = bundle.ask(request, preview["approval_id"])[1]["result"]
                self.assertEqual(len(result["bindings"]), 2 if limit == 50 else 1)
                self.assertEqual(not result["complete_within_scope"], limit == 1)
                self.assertEqual(not result["evidence_complete_for_returned_rows"], limit == 1)
                if limit == 50:
                    request["template"]["output"] = "count_distinct"
                    preview = bundle.ask(request)
                    result = bundle.ask(request, preview["approval_id"])[1]["result"]
                    self.assertEqual(result["bindings"][0]["count"]["value"], "2")
            finally:
                bundle.close()


if __name__ == "__main__":
    unittest.main()
