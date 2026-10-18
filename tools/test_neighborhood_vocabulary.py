"""#82 regression/source security and gold-free capture boundary tests; no models."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import neighborhood_vocabulary as n
import question_vocabulary as v


class NeighborhoodTests(unittest.TestCase):
    def test_complete_replay_and_all_twelve_previously_missed_predicates(self):
        expected = v.read(n.REPORT / "coverage.json")
        self.assertEqual(n.score(n.REPORT / "capture"), expected)
        old, new = expected["methods"]["v1"], expected["methods"]["v2"]
        self.assertEqual([old["at_k"][str(k)]["role_graph_coverage"]["predicate"]["covered"] for k in v.KS], [4, 5, 6, 6])
        self.assertEqual([new["at_k"][str(k)]["role_graph_coverage"]["predicate"]["covered"] for k in v.KS], [6, 16, 18, 18])
        missed = [c for c in new["cases"] if c["previously_missing_predicate"]]
        self.assertEqual(len(missed), 12)
        for c in missed:
            self.assertFalse(c["missing_at"]["20"])
            self.assertTrue(c["missing_predicate_audit"]["true_seed_adjacency"])
            self.assertEqual(c["missing_predicate_audit"]["lexical_failure"], "no_question_token_match")
        self.assertEqual(len(new["cases"]), 30)
        negatives = [c for c in new["cases"] if not c["required"]]
        self.assertEqual(len(negatives), 12)
        self.assertTrue(any(c["clarification_or_unsupported_candidate_returns"]["predicate"] for c in negatives))
        self.assertTrue(all(c["direction_covered_at"]["20"] is None for c in new["cases"]))
        self.assertEqual(new["at_k"]["20"]["new_source_audit_direction"], {"covered": 16, "total": 16})
        self.assertEqual(new["at_k"]["20"]["original_direction_reference_denominator"], 0)

    def test_forged_graph_predicate_language_mapping_and_statement_fail_source_audit(self):
        cfg = v.read(n.PROTOCOL)
        packet = v.read(n.REPORT / "capture/eva-01/v2.json")
        corpus = cfg["corpora"]["evaluation"]
        for field, value in [("graph", "urn:private:CANARY"), ("iri", "urn:unobserved")]:
            forged = copy.deepcopy(packet)
            forged["predicates"]["candidates"][0][field] = value
            with self.assertRaises(ValueError):
                v.source_audit(forged, corpus, {"required": []})
        entity = next(c for c in packet["entities"]["candidates"] if c["texts"])
        for field, value in [("language", "xx"), ("datatype", "urn:false"), ("text", "invented")]:
            forged = copy.deepcopy(packet)
            changed = next(c for c in forged["entities"]["candidates"] if c["iri"] == entity["iri"])
            changed["texts"][0]["value"][field] = value
            with self.assertRaises(ValueError):
                v.source_audit(forged, corpus, {"required": []})
        forged = copy.deepcopy(packet)
        forged["entities"]["candidates"][0]["usage"][0]["evidence"][0]["predicate"]["value"] = "urn:invented"
        with self.assertRaises(ValueError):
            v.source_audit(forged, corpus, {"required": []})
        forged = copy.deepcopy(packet)
        changed = next(c for c in forged["entities"]["candidates"] if c["texts"])
        changed["texts"][0]["via"] = {"source_iri": "urn:forged-property", "predicate": "http://wikiba.se/ontology#directClaim"}
        with self.assertRaises(ValueError):
            v.source_audit(forged, corpus, {"required": []})

    def test_registration_rejects_code_or_protocol_drift(self):
        with patch.object(n, "registered_inputs", return_value={"changed": "hash"}):
            with self.assertRaisesRegex(ValueError, "Registered retrieval"):
                n.check_registration()

    def test_capture_never_parses_references_and_checksums_before_scoring(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            questions = [{"id": f"eva-{i:02}", "question": f"Original question {i}?", "language": "en", "corpus": "evaluation"} for i in range(1, 31)]
            v.dump(root / "questions.json", {"questions": questions})
            (root / "references.json").write_text("not JSON: retrieval must only hash this file")
            v.dump(root / "scope.json", ["urn:g"])
            (root / "binary").write_text("test executable identity")
            (root / "registration.json").write_text("registered")
            corpus = {"rdf": "source.nq", "policy": "policy.json", "scope": "scope.json", "config": "config.json"}
            for name in ["source.nq", "policy.json", "config.json"]:
                (root / name).write_text("fixture")
            cfg = {"questions": "questions.json", "references": "references.json", "budget": {"max_packet_bytes": 1048576}, "corpora": {"evaluation": corpus}}
            v.dump(root / "protocol.json", cfg)
            manifest = {"snapshot_id": "snapshot", "index_revision": "revision"}
            packet = {"test_packet": True}
            raw = json.dumps(packet).encode()
            ready = {"ready": True, "manifest": manifest, "index_bytes": 1, "build_ms": 1}
            def process():
                p = MagicMock()
                p.pid = 123
                p.stdin = io.StringIO()
                p.stdout = io.StringIO(json.dumps(ready) + "\n" + (json.dumps({"packet": packet, "retrieval_ms": 1}) + "\n") * 30)
                p.stderr = io.StringIO()
                p.wait.return_value = 0
                p.poll.return_value = 0
                return p
            for q in questions:
                folder = root / f"retrieval/{q['id']}"
                folder.mkdir(parents=True)
                (folder / "packet.json").write_bytes(raw)
            original_read = v.read
            def guarded_read(path):
                self.assertNotEqual(Path(path).name, "references.json")
                return original_read(path)
            with patch.multiple(n, ROOT=root, PROTOCOL=root / "protocol.json", BINARY=root / "binary", SESSION=root / "binary", HISTORICAL=root), \
                 patch.object(n.platform, "platform", return_value="test-platform"), patch.object(n, "check_registration"), patch.object(n, "registered_inputs", return_value={"references.json": v.sha(root / "references.json")}), \
                 patch.object(v, "read", side_effect=guarded_read), \
                 patch.object(n.subprocess, "Popen", side_effect=[process(), process()]), \
                 patch.object(n.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, raw + b"\n", b"1 maximum resident set size\n")), \
                 patch.object(n.subprocess, "check_output", return_value="1234\n"):
                n.capture(root / "capture")
            freeze = v.read(root / "capture/freeze.json")
            self.assertFalse(freeze["references_parsed_during_capture"])
            self.assertEqual(v.read(root / "capture/checksums.json"), v.inventory(root / "capture"))
            self.assertEqual(v.read(root / "capture/eva-01/request.json")["question"], "Original question 1?")

    def test_percentiles_are_fixed_nearest_rank(self):
        self.assertEqual(n.percentile(list(range(1, 31)), .95), 29)
        self.assertEqual(n.percentile(list(range(1, 31)), .5), 15)


if __name__ == "__main__":
    unittest.main()
