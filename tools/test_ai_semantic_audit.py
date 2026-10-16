"""Regression checks for the independent AI-only semantic audit of issue #5.

This must never contribute human approval to benchmarks/reviews.json.
"""
import hashlib
import json
from pathlib import Path
import unittest

from benchmark_review import case_sha256

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "benchmarks" / "ai-semantic-audit.json"
BENCHMARK = ROOT / "benchmarks" / "wikidata.json"
SNAPSHOT = ROOT / "data" / "wikidata" / "snapshot.nq"


def _id(iri):
    if iri == "http://wikiba.se/ontology#Item":
        return "wikibase:Item"
    return "wd:" + iri.rsplit("/", 1)[-1]


def _node(node):
    if node["kind"] == "variable":
        return "?" + node["name"]
    if node["kind"] == "iri":
        return _id(node["iri"])
    if node["kind"] == "literal":
        return '"' + node["value"]["lexical"] + '"'
    raise ValueError("Unsupported node kind")


def _predicate(iri):
    if iri.endswith("#label"):
        return "rdfs:label"
    if iri.endswith("#type"):
        return "rdf:type"
    if "/P" in iri and iri.rsplit("/", 1)[-1].startswith("P"):
        return iri.rsplit("/", 1)[-1]
    return iri


def normalized(plan):
    return {
        "patterns": [{
            "from": _node(p["from"]),
            "predicate": _predicate(p["predicate"]),
            "to": _node(p["to"]),
            "direction": p["direction"],
        } for p in plan["patterns"]],
        "filters": [{
            "variable": "?" + f["variable"],
            "op": f["op"],
            "lexical": f["value"]["lexical"],
            "datatype": f["value"]["datatype"].rsplit("#", 1)[-1],
        } for f in plan["filters"]],
        "projection": [
            "?" + p["name"] if p["kind"] == "variable"
            else f'COUNT(DISTINCT ?{p["variable"]}) AS ?{p["alias"]}'
            for p in plan["projection"]
        ],
        "group_by": ["?" + v for v in plan["group_by"]],
        "having": [{
            "alias": h["alias"], "op": h["op"], "value": h["value"]
        } for h in plan["having"]],
        "scope": [
            "development" if g.endswith("development") else "transfer"
            for g in plan["scope"]
        ],
    }


class AIAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.benchmark = json.loads(BENCHMARK.read_text())
        cls.audit = json.loads(AUDIT.read_text())
        cls.cases = {c["id"]: c for c in cls.benchmark["cases"]}
        cls.records = {c["id"]: c for c in cls.audit["cases"]}

    def test_all_130_cases_bound_to_frozen_question_gold_and_snapshot(self):
        self.assertEqual(self.audit["version"], 1)
        self.assertEqual(self.audit["snapshot_id"], self.benchmark["snapshot_id"])
        self.assertEqual(len(self.cases), 130)
        self.assertEqual(len(self.audit["cases"]), 130)
        self.assertEqual(set(self.records), set(self.cases))
        for cid, case in self.cases.items():
            record = self.records[cid]
            with self.subTest(case=cid):
                self.assertEqual(record["case_sha256"], case_sha256(case, self.benchmark["snapshot_id"]))
                self.assertEqual(record["reviewed_question"], case["question"])
                self.assertEqual(record["split"], case["split"])
                self.assertEqual(record["expected_status"], case["expected_status"])
                self.assertIsInstance(record["independently_stated_intent"], str)
                self.assertTrue(record["independently_stated_intent"].strip())
                if case["expected_status"] == "executed":
                    self.assertEqual(record["expected_plan_signature"], normalized(case["gold"]))
                else:
                    self.assertIsNone(case["gold"])
                    self.assertIsNone(record["expected_plan_signature"])
                self.assertTrue(record["observed_plan_matches_intent_signature"])

    def test_ai_assessment_is_never_human_approval(self):
        self.assertEqual(self.audit["artifact_kind"], "independent_ai_semantic_audit_not_human_review")
        self.assertEqual(self.audit["reviewer"]["type"], "AI_assistant")
        self.assertIs(self.audit["reviewer"]["is_human"], False)
        self.assertIs(self.audit["reviewer"]["source_human_review_ledger_modified"], False)
        self.assertEqual({r["assessment"] for r in self.audit["cases"]}, {
            "provisionally_consistent_ai_only",
            "expected_abstention_is_plausible_ai_only",
        })
        self.assertEqual(sum(r["assessment"] == "needs_question_or_plan_adjudication"
                             for r in self.audit["cases"]), 0)
        self.assertEqual(sum(r["assessment"] == "expected_abstention_is_plausible_ai_only"
                             for r in self.audit["cases"]), 8)

    def test_template_candidates_cannot_masquerade_as_independent_gold(self):
        rows = [r for r in self.audit["cases"] if r["split"] == "review_candidate"]
        self.assertEqual(len(rows), 76)
        for row in rows:
            with self.subTest(case=row["id"]):
                self.assertIn("template_reuses_development_gold_not_independent", row["flags"])
                original = self.cases[row["source_template_id"]]
                number = int(row["id"].rsplit("-", 1)[1])
                prefix = ("Bruk bare opplysningene i dette grafutvalget: "
                          if number % 2 else "Med den lagrede grafversjonen som grunnlag: ")
                current = self.cases[row["id"]]
                self.assertEqual(current["question"], prefix + original["question"])
                for field in ("gold", "reference_sparql", "expected_bindings"):
                    self.assertEqual(current[field], original[field])


    def test_human_review_is_still_pending_and_intents_are_not_circular(self):
        from benchmark_review import review_summary
        reviews = json.loads((ROOT / "benchmarks/reviews.json").read_text())
        manifest = json.loads((ROOT / "benchmarks/split-manifest.json").read_text())
        summary = review_summary(self.benchmark, manifest, reviews)
        self.assertFalse(summary["initial_ready"])
        self.assertFalse(summary["final_ready"])
        self.assertEqual(summary["decisions"], {"pending": 130})
        for case in self.cases.values():
            if case["expected_status"] == "executed":
                self.assertNotIn("Execute exactly the supplied directed plan", case["interpretation"])
                self.assertIn("Graph semantics:", case["interpretation"])
        self.assertEqual(self.audit["correction_history"]["status"],
                         "AI_adjudicated_wording_and_intent_only_not_human_approved")

    def test_material_semantic_findings_grounded_in_exact_snapshot(self):
        snapshot = SNAPSHOT.read_text()
        expected_statements = (
            ("stavanger_q25416_p31_municipality_q755707",
             "<http://www.wikidata.org/entity/Q25416> <http://www.wikidata.org/prop/direct/P31> "
             "<http://www.wikidata.org/entity/Q755707>"),
            ("norway_q20_p17_self_reference",
             "<http://www.wikidata.org/entity/Q20> <http://www.wikidata.org/prop/direct/P17> "
             "<http://www.wikidata.org/entity/Q20>"),
            ("sweden_q34_p36_stockholm_q1754",
             "<http://www.wikidata.org/entity/Q34> <http://www.wikidata.org/prop/direct/P36> "
             "<http://www.wikidata.org/entity/Q1754>"),
        )
        for flag, statement in expected_statements:
            self.assertTrue(self.audit["source_assertions"][flag])
            self.assertIn(statement, snapshot)
        ambiguous = [r for r in self.audit["cases"]
                     if "municipality_entity_q25416_now_explicit_in_question" in r["flags"]]
        self.assertEqual(len(ambiguous), 15)
        self.assertTrue(all("Stavanger kommune" in self.cases[r["id"]]["question"] for r in ambiguous))
        self.assertIn("scope_only_wording_now_explicit_no_exclusivity_claim",
                      self.records["wd-transfer_candidate-006"]["flags"])
        self.assertIn("subject_type_not_required_by_corrected_question",
                      self.records["wd-transfer_candidate-008"]["flags"])
        for r in self.audit["cases"]:
            if r["split"] == "transfer_candidate":
                self.assertIn("same_wikidata_ontology_not_cross_ontology", r["flags"])


if __name__ == "__main__":
    unittest.main()
