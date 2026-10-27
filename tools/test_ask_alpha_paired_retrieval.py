"""Model-free checks for the paired Ask-alpha candidate capture."""
import unittest

import ask_alpha_paired_retrieval as paired


class PairedRetrieval(unittest.TestCase):
    def test_rank_requires_exact_graph_and_iri(self):
        candidates = [{"rank": 1, "graph": "g1", "iri": "e"},
                      {"rank": 2, "graph": "g2", "iri": "e"}]
        self.assertEqual(paired.rank(candidates, "g2", "e"), 2)
        self.assertIsNone(paired.rank(candidates, "g3", "e"))

    def test_capture_candidates_fail_closed_on_scope_and_duplicates(self):
        packet = {"entities": {"candidates": [
            {"graph": "g", "iri": "e", "exact": False, "ranking_score": 1.0}]},
            "predicates": {"candidates": []}}
        self.assertEqual(paired.packet_candidates(packet, {"g"})["entity"][0]["iri"], "e")
        packet["entities"]["candidates"].append(packet["entities"]["candidates"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate or out-of-scope"):
            paired.packet_candidates(packet, {"g"})
        packet["entities"]["candidates"] = [
            {"graph": "outside", "iri": "e", "exact": False, "ranking_score": 1.0}]
        with self.assertRaisesRegex(ValueError, "Duplicate or out-of-scope"):
            paired.packet_candidates(packet, {"g"})

    def test_digest_ignores_object_key_order_but_preserves_list_order(self):
        candidates = {"entity": [], "predicate": [
            {"rank": 1, "graph": "g", "iri": "p", "exact": True, "ranking_score": 4.0}]}
        reordered_keys = {"predicate": [{"ranking_score": 4.0, "exact": True,
                                         "iri": "p", "graph": "g", "rank": 1}], "entity": []}
        self.assertEqual(paired.candidate_digest(candidates), paired.candidate_digest(reordered_keys))
        candidates["predicate"].append({"rank": 2, "graph": "g", "iri": "q",
                                         "exact": False, "ranking_score": 1.0})
        reordered_keys["predicate"].reverse()
        self.assertNotEqual(paired.candidate_digest(candidates), paired.candidate_digest(reordered_keys))


if __name__ == "__main__":
    unittest.main()
