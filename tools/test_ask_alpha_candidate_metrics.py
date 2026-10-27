"""Read-only descriptive summaries of the frozen Ask alpha packets."""
import unittest

import ask_alpha_candidate_metrics as metrics


class CandidateMetrics(unittest.TestCase):
    def test_rank_requires_exact_graph_and_iri(self):
        rows = [{"graph": "g1", "iri": "e1"}, {"graph": "g2", "iri": "e1"}]
        self.assertEqual(metrics.candidate_rank(rows, "g2", "e1"), 2)
        self.assertIsNone(metrics.candidate_rank(rows, "g3", "e1"))

    def test_direction_witness_checks_original_orientation_and_graph(self):
        graph, entity, predicate, value = "g", "e", "p", "v"
        edge = {"source_graph": {"value": graph}, "subject": {"value": entity},
                "predicate": {"value": predicate}, "object": {"value": value}}
        packet = {
            "entities": {"candidates": [{"graph": graph, "iri": entity,
                                           "usage": [{"evidence": [edge]}]}]},
            "predicates": {"candidates": [{"graph": graph, "iri": predicate,
                                             "usage": [{"evidence": [edge]}]}]},
        }
        self.assertTrue(metrics.direction_witness(packet, {"graph": graph, "start": entity,
                                                           "predicate": predicate, "direction": "forward"}))
        self.assertFalse(metrics.direction_witness(packet, {"graph": graph, "start": entity,
                                                            "predicate": predicate, "direction": "reverse"}))

    def test_saved_exposed_packet_summary(self):
        report = metrics.summarize()
        self.assertEqual(report["summary"]["languages"], {"en": 30, "nb": 30})
        self.assertEqual(report["summary"]["candidate_position_coverage"]["10"]["both"],
                         {"hits": 28, "total": 29})
        self.assertEqual(report["summary"]["witnesses_for_nonempty_reference_paths"],
                         {"hits": 27, "total": 27})
        alpha08 = next(row for row in report["cases"] if row["id"] == "alpha-08")
        self.assertIsNone(alpha08["entity_rank"])
        self.assertEqual(alpha08["missing_entity_neighbor_witness"]["statement"]["object"]["value"],
                         "http://www.wikidata.org/entity/Q20")
        self.assertFalse(report["inference_performed"])
        self.assertFalse(report["new_graph_queries_performed"])


if __name__ == "__main__":
    unittest.main()
