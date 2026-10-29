"""Model-free integrity checks for the R-GCN / CompGCN research inputs."""
import unittest
import json
from pathlib import Path
import tempfile

from rdflib import SKOS

import rgcn_compgcn as g


class GraphExportTests(unittest.TestCase):
    def test_audit_counts_directed_predicates_and_original_languages(self):
        raw = b'''<urn:a> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2004/02/skos/core#Concept> <urn:g> .
<urn:b> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2004/02/skos/core#Concept> <urn:g> .
<urn:a> <http://www.w3.org/2004/02/skos/core#broader> <urn:b> <urn:g> .
<urn:a> <http://www.w3.org/2004/02/skos/core#prefLabel> "alpha"@en <urn:g> .
<urn:b> <http://www.w3.org/2004/02/skos/core#prefLabel> "beta"@no <urn:g> .
'''
        result = g.audit(raw)
        self.assertEqual(result["skos_concepts"], 2)
        self.assertEqual(result["model_edges"], 1)
        self.assertEqual(result["model_relation_counts"], {str(SKOS.broader): 1})
        self.assertEqual(result["literal_languages"], {"en": 1, "no": 1})
        self.assertEqual(result["weak_components"], 1)
        self.assertEqual(result["isolated_concepts"], 0)

    def test_split_keeps_translations_and_paraphrases_together(self):
        rows = [
            {"id": "en", "intent_group": "same-edge", "question_signature": "same-text", "language": "en"},
            {"id": "no", "intent_group": "same-edge", "question_signature": "translated-text", "language": "no"},
            {"id": "duplicate", "intent_group": "different-intent", "question_signature": "same-text", "language": "en"},
            {"id": "other", "intent_group": "other-edge", "question_signature": "other-text", "language": "en"},
        ]
        first = g.split_groups(rows, "intent_group", seed=117)
        second = g.split_groups(rows, "intent_group", seed=117)
        self.assertEqual(first, second)
        split = {row["id"]: name for name, values in first.items() for row in values}
        self.assertEqual(split["en"], split["no"])
        self.assertEqual(split["en"], split["duplicate"])
        self.assertEqual(sorted(sum((values for values in first.values()), []), key=lambda x: x["id"]),
                         sorted(rows, key=lambda x: x["id"]))

    def test_held_out_source_edges_cannot_enter_message_graph(self):
        row = {"graph": "urn:g", "subject_iri": "urn:a", "predicate": str(SKOS.broader), "object_iri": "urn:b"}
        with self.assertRaisesRegex(ValueError, "leaked into message passing"):
            g.assert_no_message_edge_leakage([row], [row])
        g.assert_no_message_edge_leakage([], [row])

    def test_rank_metrics_preserve_graph_identity_and_open_world_no_match(self):
        relevant = {("urn:g", "urn:a"), ("urn:g", "urn:b")}
        rows = g.rank_metrics(relevant, [("urn:other", "urn:a"), ("urn:g", "urn:b")])
        self.assertEqual(rows["recall@1"], 0.0)
        self.assertEqual(rows["recall@5"], 0.5)
        self.assertEqual(rows["mrr@10"], 0.5)
        self.assertEqual(g.rank_metrics(set(), [("urn:g", "urn:a")])["recall@10"], None)

    def test_summary_reports_paired_incremental_value_on_evaluation_only(self):
        bm25 = {"recall@1": 0.0, "recall@5": 1.0, "recall@10": 1.0, "mrr@10": 0.5, "ndcg@10": 0.63}
        graph = {"recall@1": 1.0, "recall@5": 1.0, "recall@10": 1.0, "mrr@10": 1.0, "ndcg@10": 1.0}
        rows = []
        for method, metrics in [("bm25", bm25), ("neighborhood", graph)]:
            rows.append({"id": "eval-1", "split": "evaluation", "language": "no", "family": "direction",
                         "status": "relevant", "method": method, "ranked": [], "metrics": metrics,
                         "candidate_recall": 1.0})
        summary = g.summarize_capture(rows)
        self.assertEqual(summary["evaluation_paired_delta_neighborhood_minus_bm25"]["recall@1"]["mean"], 1.0)
        self.assertEqual(summary["evaluation_relevant_cases"], 1)

    def test_lexical_view_omits_long_concept_definitions_but_keeps_all_edges(self):
        concept = b"<http://www.eionet.europa.eu/gemet/concept/1>"
        definition = (concept + b" <" + str(SKOS.definition).encode() +
                      b"> \"long source definition\"@en <urn:g> .\n")
        edge = (concept + b" <" + str(SKOS.broader).encode() +
                b"> <http://www.eionet.europa.eu/gemet/concept/2> <urn:g> .\n")
        view, omitted = g.retrieval_view(definition + edge)
        self.assertEqual(omitted, 1)
        self.assertEqual(view, edge)

    def test_public_cases_keep_references_out_of_question_input(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "cases"
            manifest = g.prepare_cases(out)
            questions = json.loads((out / "questions.json").read_text())
            references = json.loads((out / "references.json").read_text())
            self.assertEqual(manifest["counts"]["total"], 122)
            self.assertTrue(all("relevant" not in row and "witnesses" not in row for row in questions))
            self.assertTrue(all(row["review_status"] == "AI_reference_only" for row in references))

    def test_full_export_rebuilds_retained_source_attempt(self):
        raw = g.full_snapshot()
        rows = g.quads(raw)
        stats = g.audit(raw)
        self.assertEqual(stats["snapshot_sha256"], "151be979b5ac8f5db2c55cc724d44988d3aca6d2d7d44e55df108b2c61371b35")
        self.assertEqual(stats["skos_concepts"], 5573)
        self.assertEqual(stats["model_edges"], 14764)
        self.assertEqual(stats["named_graphs"], [g.GRAPH])
        self.assertEqual(sum(1 for s, p, o, _ in rows if p in g.MODEL_PREDICATES), 14764)


if __name__ == "__main__":
    unittest.main()
