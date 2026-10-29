"""Integrity checks for the frozen Wikidata relational benchmark."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rgcn_compgcn_v2 as v2


class RelationalBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions, cls.references, cls.splits = v2.make_cases()
        cls.export = v2.EXPORT
        cls.source_lines = set((cls.export / "snapshot.nq").read_text().splitlines())

    def test_data_adequacy_and_bilingual_question_families(self):
        audit = v2.audit_graph(self.export)
        self.assertEqual((audit["entities"], audit["directed_edges"], audit["distinct_predicates"]),
                         (2157, 5756, 84))
        self.assertGreaterEqual(audit["two_hop_paths_excluding_P17_and_P31"], 1000)
        self.assertEqual(audit["operator_P137_edges"], 1)
        self.assertEqual({row["language"] for row in self.questions}, {"en", "no"})
        families = {row["family"] for row in self.questions}
        self.assertTrue({"forward_one_hop", "reverse_one_hop", "predicate_retrieval",
                         "two_hop_path", "ambiguous_alias", "unsupported_no_match"} <= families)

    def test_benchmark_inputs_rebuild_byte_for_byte(self):
        questions, references, splits = v2.make_cases()
        self.assertEqual(questions, self.questions)
        self.assertEqual(references, self.references)
        self.assertEqual(splits, self.splits)

    def test_positive_references_are_source_checked_and_scopes_are_marked(self):
        for ref in self.references:
            for witness in ref["witnesses"]:
                for line in witness["source_quads"]:
                    self.assertIn(line, self.source_lines)
            self.assertTrue(any(item["kind"] == "out-of-scope-graph"
                                for item in ref["hard_negatives"]))
        gemet_lines = set((v2.ROOT / "data/gemet/snapshot.nq").read_text().splitlines())
        for ref in self.references:
            control = next(item for item in ref["hard_negatives"]
                           if item["kind"] == "out-of-scope-graph")
            self.assertTrue(set(control["source_quads"]) <= gemet_lines)

    def test_split_groups_and_heldout_message_edges_are_disjoint(self):
        group_splits = {}
        exact_query_splits = {}
        for question in self.questions:
            group_splits.setdefault(question["query_group"], set()).add(question["split"])
            exact_query_splits.setdefault(question["query"].casefold(), set()).add(question["split"])
        self.assertTrue(all(len(splits) == 1 for splits in group_splits.values()))
        self.assertTrue(all(len(splits) == 1 for splits in exact_query_splits.values()))
        split_ids = self.splits["witness_edge_ids"]
        self.assertFalse(set(split_ids["train"]) & set(split_ids["validation"]))
        self.assertFalse(set(split_ids["train"]) & set(split_ids["test"]))
        held = set(self.splits["held_out_edge_ids_excluded_from_message_passing"])
        message = set(self.splits["message_passing_train_edge_ids"])
        self.assertTrue(held.isdisjoint(message))
        self.assertTrue(set(split_ids["validation"] + split_ids["test"]) <= held)
        test_statuses = {ref["status"] for ref in self.references if ref["split"] == "test"}
        self.assertTrue({"relevant", "ambiguous", "no_match"} <= test_statuses)

    def test_questions_do_not_include_answer_identifiers_in_traversal_hints(self):
        refs = {ref["id"]: ref for ref in self.references}
        for question in self.questions:
            traversal = json.dumps(question["traversal"])
            for target in refs[question["id"]]["relevant"]:
                self.assertNotIn(target["iri"], traversal)

    def test_unseen_entity_split_removes_all_incident_edges_and_supervision(self):
        unseen = set(self.splits["unseen_entity_generalization"]["unseen_entity_iris"])
        self.assertTrue(unseen)
        messages = set(self.splits["unseen_entity_generalization"]["message_passing_edge_ids"])
        excluded = set(self.splits["unseen_entity_generalization"]["excluded_incident_edge_ids"])
        edge_ids = {v2.edge_key(edge): edge for edge in v2.read_jsonl(self.export / "edges.jsonl")}
        self.assertTrue(all(not ({edge["subject_iri"], edge["object_iri"]} & unseen)
                            for key, edge in edge_ids.items() if key in messages))
        self.assertEqual(excluded, {key for key, edge in edge_ids.items()
                                    if edge["subject_iri"] in unseen or edge["object_iri"] in unseen})
        train_ids = set(self.splits["unseen_entity_generalization"]["train_query_ids"])
        test_ids = set(self.splits["unseen_entity_generalization"]["test_query_ids"])
        self.assertTrue(train_ids)
        self.assertTrue(test_ids)
        refs = {row["id"]: row for row in self.references}
        self.assertTrue(all(not any(item["iri"] in unseen for item in refs[case]["relevant"])
                            for case in train_ids))
        self.assertTrue(all(any(item["iri"] in unseen for item in refs[case]["relevant"])
                            for case in test_ids))

    def test_adjacency_capture_is_directional_and_has_exact_source_paths(self):
        outputs = v2.path_candidates(self.export, v2.read_jsonl(self.export / "edges.jsonl"),
                                     self.questions, 2)
        for question in self.questions:
            ref = next(item for item in self.references if item["id"] == question["id"])
            candidates = outputs[question["id"]]
            for candidate in candidates:
                self.assertEqual(candidate["graph"], v2.GRAPH)
                self.assertTrue(set(candidate["source_quads"]) <= self.source_lines)
            if question["family"] == "two_hop_path" and question["split"] == "test":
                self.assertEqual({candidate["iri"] for candidate in candidates},
                                 {item["iri"] for item in ref["relevant"]})

    def test_exact_path_metric_requires_the_complete_directional_source_path(self):
        graph = v2.GRAPH
        first = f"<urn:start> <urn:forward> <urn:middle> <{graph}> ."
        second = f"<urn:middle> <urn:next> <urn:target> <{graph}> ."
        reference = {"relevant": [{"graph": graph, "iri": "urn:target"}],
                     "witnesses": [{"source_quads": [first, second]}]}
        ranked = [(graph, "urn:target")]
        wrong = [{"graph": graph, "iri": "urn:target", "source_quads":
                  [first, second.replace("urn:next", "urn:reverse")]}]
        right = [{"graph": graph, "iri": "urn:target", "source_quads": [second, first]}]
        self.assertEqual(v2.exact_path_metrics(ranked, reference, wrong)["recall@10"], 0.0)
        self.assertEqual(v2.exact_path_metrics(ranked, reference, right)["recall@10"], 1.0)


if __name__ == "__main__":
    unittest.main()
