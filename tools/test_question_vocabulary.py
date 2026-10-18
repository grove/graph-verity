"""Model-free coverage accounting and gold-free freeze boundary regressions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import question_vocabulary as vocab


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.start = {"role": "entity", "graph": "urn:g", "iri": "urn:start"}
        self.predicate = {"role": "predicate", "graph": "urn:g", "iri": "urn:p", "direction": "incoming"}
        self.statement = {key: {"kind": "iri", "value": value} for key, value in
                          [("subject", "urn:answer"), ("predicate", "urn:p"),
                           ("object", "urn:start"), ("source_graph", "urn:g")]}
        self.entity = {"graph": "urn:g", "iri": "urn:start", "usage": []}
        self.pred = {"graph": "urn:g", "iri": "urn:p",
                     "usage": [{"direction": "predicate", "evidence": [self.statement]}]}
        self.packet = {"entities": {"candidates": [self.entity]},
                       "predicates": {"candidates": [self.pred]}, "classes": {"candidates": []},
                       "clipped": False, "status": "candidates_only"}
        self.reference = {"required": [self.start, self.predicate]}
        self.catalog = {(r["role"], r["graph"], r["iri"]) for r in self.reference["required"]}

    def test_inverse_requires_original_object_and_correct_graph_and_role(self):
        result = vocab.score_case(self.packet, self.reference, self.catalog)
        self.assertTrue(result["direction_covered_at"]["1"])
        self.assertEqual(result["missing_at"]["1"], [])
        self.assertFalse(vocab.directed(self.packet, self.start, self.predicate, "outgoing", 20))
        self.packet["predicates"]["candidates"][0]["graph"] = "urn:other"
        result = vocab.score_case(self.packet, self.reference, self.catalog)
        self.assertFalse(result["direction_covered_at"]["20"])
        self.assertEqual(len(result["missing_at"]["20"]), 1)
        self.assertTrue(result["required"][1]["iri_present_any_graph"])

    def test_top_k_is_applied_before_direction_scoring_and_misses_are_retained(self):
        self.packet["entities"]["candidates"].insert(0, {"graph": "urn:g", "iri": "urn:distractor", "usage": []})
        result = vocab.score_case(self.packet, self.reference, self.catalog)
        self.assertFalse(result["direction_covered_at"]["1"])
        self.assertTrue(result["direction_covered_at"]["5"])
        self.assertEqual(result["missing_at"]["1"][0]["iri"], "urn:start")
        self.assertEqual(result["required"][0]["rank"], 2)

    def test_negative_returns_and_duplicates_do_not_become_semantic_success(self):
        self.packet["entities"]["candidates"].append(copy.deepcopy(self.entity))
        result = vocab.score_case(self.packet, {"required": [], "expected_no_match": True}, set())
        self.assertEqual(result["negative_candidate_returns"], 3)
        self.assertEqual(result["duplicates"], 1)
        self.assertIsNone(result["direction_covered_at"]["20"])
        self.assertEqual(len(result["negative_returned_candidates"]), 3)
        self.assertEqual(result, json.loads(json.dumps(result)))

    def test_source_audit_accepts_rdf11_strings_and_rejects_invented_witnesses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "snapshot.nq").write_text('<urn:answer> <urn:p> "plain" <urn:g> .\n')
            (root / "policy.json").write_text('{"graphs":["urn:g"]}')
            packet = copy.deepcopy(self.packet)
            packet["request"] = {"scope": ["urn:g"]}
            packet["entities"]["candidates"] = []
            packet["predicates"]["candidates"][0]["texts"] = []
            statement = packet["predicates"]["candidates"][0]["usage"][0]["evidence"][0]
            statement["object"] = {"kind": "literal", "value": "plain", "language": None,
                                   "datatype": "http://www.w3.org/2001/XMLSchema#string"}
            with patch.object(vocab, "ROOT", root):
                _, witnesses = vocab.source_audit(packet, {"rdf": "snapshot.nq", "policy": "policy.json"}, {"required": []})
                self.assertEqual(witnesses, ['<urn:answer> <urn:p> "plain" <urn:g> .'])
                statement["object"]["value"] = "invented"
                with self.assertRaises(ValueError):
                    vocab.source_audit(packet, {"rdf": "snapshot.nq", "policy": "policy.json"}, {"required": []})

    def test_freeze_does_not_parse_or_send_reference_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "questions.json").write_text(json.dumps({"questions": [
                {"id": "case", "corpus": "test", "question": "Original whole question?", "language": "en"}]}))
            # Intentionally not valid JSON: retrieval must only hash this file.
            (root / "references.json").write_text("SECRET_REFERENCE_ID invalid-json")
            (root / "scope.json").write_text('["urn:g"]')
            cfg = {"version": "question-vocabulary-study-v1", "retrieval": "whole-original-question-per-role-BM25-only",
                   "questions": "questions.json", "references": "references.json",
                   "budget": {"per_role_top_k": 20, "max_packet_bytes": 10000},
                   "corpora": {"test": {"rdf": "rdf", "scope": "scope.json", "policy": "policy", "config": "config"}}}
            (root / "protocol.json").write_text(json.dumps(cfg))
            requests = []
            def cli(_binary, command, *args):
                self.assertNotIn("SECRET_REFERENCE_ID", str(args))
                self.assertTrue((root / "out/freeze.json").exists())
                if command == "index-build":
                    return b'{"manifest":{"snapshot_id":"snapshot","index_revision":"index"}}'
                request = vocab.read(args[-2])
                requests.append(request)
                self.assertEqual(request["question"], "Original whole question?")
                self.assertEqual(set(request), {"question", "language", "scope", "snapshot_id", "index_revision"})
                return b'{}\n'
            with patch.object(vocab, "ROOT", root), patch.object(vocab, "inputs", return_value={}), patch.object(vocab, "cli", side_effect=cli), patch.object(vocab.subprocess, "check_output", return_value="commit\n"):
                vocab.freeze(root / "protocol.json", root / "out", Path("binary"))
                self.assertEqual(len(requests), 1)
                with self.assertRaises(ValueError):
                    vocab.freeze(root / "protocol.json", root / "out", Path("binary"))
            self.assertEqual(vocab.read(root / "out/checksums.json"), vocab.inventory(root / "out"))


if __name__ == "__main__":
    unittest.main()
