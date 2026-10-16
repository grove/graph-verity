"""Review gates use synthetic decisions, never fabricated approvals of retained gold."""
import copy
from datetime import date, timedelta
import json
from pathlib import Path
import unittest

from benchmark_review import case_sha256, review_summary


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id": "one", "question": "Hvilket land?", "interpretation": "Pinned graph only",
                     "family": "direct_relation", "split": "dev", "review_status": "machine_authored",
                     "provenance": "synthetic test", "scope": ["urn:dev"], "expected_status": "executed",
                     "gold": {"snapshot_id": "snapshot", "scope": ["urn:dev"]},
                     "reference_sparql": "SELECT ?country WHERE {}", "expected_bindings": []}
        self.benchmark = {"version": 1, "snapshot_id": "snapshot", "cases": [self.case]}
        self.manifest = {"version": 1, "splits": {"dev": ["one"]},
                         "groups": {"template": ["one"]}, "exposed_groups": []}
        self.reviews = {"version": 1, "records": []}

    def record(self, case=None, decision="approved"):
        case = case or self.case
        return {"case_id": case["id"], "case_sha256": case_sha256(case, self.benchmark["snapshot_id"]),
                "reviewer": "synthetic test reviewer", "reviewed_at": "2026-01-01",
                "decision": decision, "rationale": "Synthetic test decision"}

    def summary(self):
        return review_summary(self.benchmark, self.manifest, self.reviews)

    def test_machine_authorship_never_counts_as_human_review(self):
        root = Path(__file__).resolve().parents[1] / "benchmarks"
        benchmark = json.loads((root / "wikidata.json").read_text())
        manifest = json.loads((root / "split-manifest.json").read_text())
        summary = review_summary(benchmark, manifest, {"version": 1, "records": []})
        self.assertEqual(summary["decisions"], {"pending": len(benchmark["cases"])})
        self.assertFalse(summary["initial_ready"])
        self.assertFalse(summary["final_ready"])

    def test_manifest_requires_exact_nonduplicated_membership(self):
        for section in ("splits", "groups"):
            for members in ([], "one", [""], [None], ["one", "one"], ["one", "extra"], ["extra"]):
                with self.subTest(section=section, members=members):
                    manifest = copy.deepcopy(self.manifest)
                    manifest[section] = {"dev": members}
                    with self.assertRaises(ValueError):
                        review_summary(self.benchmark, manifest, self.reviews)
            manifest = copy.deepcopy(self.manifest)
            manifest[section]["other"] = ["one"]
            with self.assertRaises(ValueError):
                review_summary(self.benchmark, manifest, self.reviews)

    def test_unknown_version_split_duplicate_case_and_mismatched_split(self):
        for obj in (self.benchmark, self.manifest, self.reviews):
            obj["version"] = 2
            with self.assertRaises(ValueError):
                self.summary()
            obj["version"] = 1
        self.manifest["splits"] = {"unknown": ["one"]}
        with self.assertRaises(ValueError):
            self.summary()
        self.manifest["splits"] = {"review_candidate": ["one"]}
        with self.assertRaises(ValueError):
            self.summary()
        self.manifest["splits"] = {"dev": ["one"]}
        self.benchmark["cases"].append(copy.deepcopy(self.case))
        with self.assertRaises(ValueError):
            self.summary()

    def test_related_templates_cannot_cross_test_boundaries(self):
        other = dict(self.case, id="two", split="review_candidate")
        self.benchmark["cases"].append(other)
        self.manifest["splits"]["review_candidate"] = ["two"]
        self.manifest["groups"]["template"].append("two")
        self.summary()  # Exposed candidate siblings are allowed beside development.
        for split in ("locked_holdout", "transfer_test"):
            other["split"] = split
            self.manifest["splits"] = {"dev": ["one"], split: ["two"]}
            with self.assertRaisesRegex(ValueError, "cross a locked test boundary"):
                self.summary()

    def test_status_gold_snapshot_scope_and_metadata_must_agree(self):
        for field, value in (("gold", None), ("reference_sparql", None), ("expected_bindings", None),
                             ("expected_status", "unknown"), ("expected_status", "unsupported"),
                             ("scope", []), ("scope", ["urn:other"]), ("interpretation", "")):
            with self.subTest(field=field):
                case = dict(self.case, **{field: value})
                with self.assertRaises(ValueError):
                    review_summary(dict(self.benchmark, cases=[case]), self.manifest, self.reviews)
        self.case["gold"]["snapshot_id"] = "other"
        with self.assertRaises(ValueError):
            self.summary()

    def test_exposed_groups_cannot_be_promoted_even_as_a_whole(self):
        self.manifest["exposed_groups"] = ["template"]
        self.summary()
        self.case["split"] = "locked_holdout"
        self.manifest["splits"] = {"locked_holdout": ["one"]}
        with self.assertRaisesRegex(ValueError, "Previously exposed"):
            self.summary()
        for exposed in (["unknown"], ["template", "template"]):
            self.manifest["exposed_groups"] = exposed
            with self.assertRaises(ValueError):
                self.summary()

    def test_review_binds_every_case_field_and_snapshot(self):
        self.reviews["records"] = [self.record()]
        self.assertEqual(self.summary()["decisions"], {"approved": 1})
        for field, value in (("question", "Changed question"), ("interpretation", "Changed meaning"),
                             ("reference_sparql", "Changed query"), ("expected_bindings", [{}]),
                             ("provenance", "Changed author"), ("review_status", "Changed state")):
            with self.subTest(field=field):
                old = self.case[field]
                self.case[field] = value
                self.assertEqual(self.summary()["decisions"], {"stale": 1})
                self.case[field] = old
        self.case.update(expected_status="unsupported", gold=None, reference_sparql=None, expected_bindings=None)
        self.reviews["records"] = [self.record()]
        self.benchmark["snapshot_id"] = "changed"
        self.assertEqual(self.summary()["decisions"], {"stale": 1})

    def test_history_and_adjudication_keep_old_records(self):
        self.reviews["records"] = [self.record(decision="disputed")]
        self.assertEqual(self.summary()["decisions"], {"disputed": 1})
        self.case["question"] = "Corrected question"
        self.assertEqual(self.summary()["decisions"], {"stale": 1})
        self.reviews["records"].append(self.record())
        self.assertEqual(self.summary()["decisions"], {"approved": 1})
        self.reviews["records"].append(self.record(decision="excluded"))
        self.assertEqual(self.summary()["decisions"], {"excluded": 1})
        self.assertEqual(self.summary()["approved_by_split"], {})
        self.assertEqual(len(self.reviews["records"]), 3)

    def test_review_records_reject_invalid_fields_identity_dates_and_decisions(self):
        for field, value in (("reviewer", " "), ("case_id", "unknown"), ("case_sha256", "bad"),
                             ("decision", "maybe"), ("rationale", ""), ("extra", "unknown"),
                             ("reviewed_at", "2026-1-1"),
                             ("reviewed_at", (date.today() + timedelta(days=1)).isoformat())):
            with self.subTest(field=field, value=value):
                record = dict(self.record(), **{field: value})
                with self.assertRaises(ValueError):
                    review_summary(self.benchmark, self.manifest, {"version": 1, "records": [record]})
        self.reviews["records"] = [self.record(), dict(self.record(), reviewed_at="2025-12-31")]
        with self.assertRaises(ValueError):
            self.summary()

    def test_initial_gate_needs_thirty_approved_development_cases(self):
        self.benchmark["cases"] = []
        self.manifest.update(splits={"dev": []}, groups={})
        for i in range(30):
            case = dict(self.case, id=str(i))
            self.benchmark["cases"].append(case)
            self.manifest["splits"]["dev"].append(case["id"])
            self.manifest["groups"][case["id"]] = [case["id"]]
            if i < 29:
                self.reviews["records"].append(self.record(case))
        self.assertFalse(self.summary()["initial_ready"])
        self.reviews["records"].append(self.record(case))
        self.assertTrue(self.summary()["initial_ready"])
        case["split"] = "review_candidate"
        self.manifest["splits"]["dev"].pop()
        self.manifest["splits"]["review_candidate"] = [case["id"]]
        self.reviews["records"].append(self.record(case))
        self.assertFalse(self.summary()["initial_ready"])

    def test_final_gate_needs_approved_dev_independent_holdout_and_transfer(self):
        self.benchmark["cases"] = []
        self.manifest.update(splits={}, groups={})
        for split, count in (("dev", 30), ("locked_holdout", 60), ("transfer_test", 10)):
            self.manifest["splits"][split] = []
            for i in range(count):
                case = dict(self.case, id=f"{split}-{i}", split=split)
                self.benchmark["cases"].append(case)
                self.manifest["splits"][split].append(case["id"])
                self.manifest["groups"][case["id"]] = [case["id"]]
                self.reviews["records"].append(self.record(case))
        self.assertTrue(self.summary()["initial_ready"])
        self.assertTrue(self.summary()["final_ready"])
        record = self.reviews["records"].pop()
        self.assertFalse(self.summary()["final_ready"])
        self.reviews["records"].append(dict(record, decision="excluded"))
        self.assertFalse(self.summary()["final_ready"])
        for case in self.benchmark["cases"]:
            if case["split"] == "locked_holdout":
                case["split"] = "review_candidate"
        self.manifest["splits"]["review_candidate"] = self.manifest["splits"].pop("locked_holdout")
        self.reviews["records"] = [self.record(c) for c in self.benchmark["cases"]]
        self.assertFalse(self.summary()["final_ready"])


if __name__ == "__main__":
    unittest.main()
