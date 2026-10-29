"""Small deterministic contracts for alignment and retrieval diagnostics."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rgcn_compgcn_alignment as aligned
import rgcn_compgcn_aligned_run_v1 as run


class AlignmentPrimitiveTests(unittest.TestCase):
    def test_relation_balanced_sampler_caps_common_but_keeps_rare(self):
        relation_ids = [0] * 9 + [1] * 2 + [2]
        first = aligned.relation_balanced_edge_indices(relation_ids, per_relation_cap=2, seed=117)
        second = aligned.relation_balanced_edge_indices(relation_ids, per_relation_cap=2, seed=117)
        self.assertEqual(first, second)
        counts = {relation_id: sum(relation_ids[index] == relation_id for index in first)
                  for relation_id in set(relation_ids)}
        self.assertEqual(counts, {0: 2, 1: 2, 2: 1})

    def test_relation_balancing_samples_source_edges_before_direction_expansion(self):
        source_relations = [(f"edge-{i}", 0) for i in range(8)] + [("rare", 1)]
        first = aligned.relation_balanced_source_ids(source_relations,
                                                     per_relation_cap=2, seed=119)
        second = aligned.relation_balanced_source_ids(source_relations,
                                                      per_relation_cap=2, seed=119)
        self.assertEqual(first, second)
        self.assertEqual(sum(source.startswith("edge-") for source in first), 2)
        self.assertIn("rare", first)
        expanded = [{"source_edge_id": source, "direction": direction}
                    for source, relation_id in source_relations if source in first
                    for direction in ("forward", "reverse")]
        run._check_navigation_pairs(expanded)
        with self.assertRaisesRegex(ValueError, "both forward and reverse"):
            run._check_navigation_pairs(expanded[:-1])

    def test_direction_hard_negative_is_source_backed_and_contrastive(self):
        quad = "<urn:s> <urn:p> <urn:o> <urn:g> ."
        entities = {"urn:s": 0, "urn:o": 1}
        forward = {"family": "forward_one_hop"}
        reverse = {"family": "reverse_one_hop"}
        ref = {"relevant": [{"iri": "urn:o"}], "witnesses": [{"source_quads": [quad]}]}
        hard = aligned.direction_hard_negative(forward, ref, entities, {})
        self.assertEqual(hard["candidate_id"], 0)
        self.assertTrue(hard["contrastive_only"])
        ref_reverse = {"relevant": [{"iri": "urn:s"}], "witnesses": [{"source_quads": [quad]}]}
        self.assertEqual(aligned.direction_hard_negative(reverse, ref_reverse, entities, {})["candidate_id"], 1)

    def test_training_and_retrieval_predicate_candidate_spaces_stay_distinct(self):
        nodes = {f"urn:e:{i}": i for i in range(12)}
        predicates = {f"urn:p:{i}": i for i in range(6)}
        graph = "urn:g"
        quad = f"<urn:e:0> <urn:p:1> <urn:e:1> <{graph}> ."
        entity_q = {"id": "entity", "family": "forward_one_hop", "role": "entity",
                    "query": "entity", "language": "en", "traversal": {
                        "start_iri": "urn:e:0", "steps": [{"predicate": "urn:p:1", "direction": "forward"}]}}
        predicate_q = {"id": "predicate", "family": "predicate_retrieval", "role": "predicate",
                       "query": "predicate", "language": "no", "traversal": {
                           "kind": "endpoints", "subject_iri": "urn:e:0", "object_iri": "urn:e:1"}}
        entity_ref = {"id": "entity", "status": "relevant", "relevant": [{"graph": graph, "iri": "urn:e:1"}],
                      "witnesses": [{"source_quads": [quad]}], "hard_negatives": []}
        predicate_ref = {"id": "predicate", "status": "relevant",
                         "relevant": [{"graph": graph, "iri": "urn:p:1"}],
                         "witnesses": [{"source_quads": [quad]}],
                         "hard_negatives": [{"kind": "wrong-predicate", "iri": "urn:p:0",
                                             "source_quads": [quad]}]}
        examples = run.make_query_examples(
            ["entity", "predicate"], [entity_q, predicate_q], [entity_ref, predicate_ref],
            np.zeros((2, 3), dtype=np.float32), nodes, predicates, 12, 6,
            seed=117, excluded_node_iris=set(), hard_negatives=True)
        self.assertEqual(examples[0]["hard_negative_candidate_id"], 0)
        self.assertEqual(examples[1]["target_candidate_id"], 12 + 2)
        self.assertEqual(examples[1]["retrieval_candidate_id"], 12 + 1)
        self.assertEqual(examples[1]["relation_direction_ids"], [2])
        self.assertEqual(examples[1]["hard_negative_candidate_id"], 12)

    def test_shared_pool_reranking_cannot_add_candidates_and_keeps_tie_order(self):
        self.assertEqual(aligned.rank_shared_pool([8, 2, 4], {8: 1.0, 2: 2.0, 4: 2.0}), [2, 4, 8])
        with self.assertRaisesRegex(ValueError, "no GNN score"):
            aligned.rank_shared_pool([1, 2], {1: 0.5})

    def test_edge_lineage_split_guard_catches_inverse_message_leakage(self):
        groups = {"en": "edge-a", "no": "edge-a", "other": "edge-b"}
        aligned.check_alignment_splits(["en", "no"], ["other"], [], groups,
                                       {"edge-a"}, {"edge-b"}, {"edge-a"})
        with self.assertRaisesRegex(ValueError, "message passing"):
            aligned.check_alignment_splits(["en", "no"], [], ["other"], groups,
                                           {"edge-a"}, {"edge-b"}, {"edge-a", "edge-b"})
        with self.assertRaisesRegex(ValueError, "source-lineage"):
            aligned.check_alignment_splits(["en"], [], ["no"], groups,
                                           {"edge-a"}, set(), {"edge-a"})

    @unittest.skipIf(aligned.torch is None, "pinned PyTorch runtime is not installed")
    def test_alignment_head_has_separate_anchor_direction_and_answer_gradients(self):
        torch = aligned.torch
        torch.manual_seed(117)
        head = aligned.QuestionGraphAlignmentHead(question_width=3, hidden=4)
        q = torch.tensor([[0.2, 0.4, 0.7], [0.5, 0.2, 0.1]])
        entities = torch.randn(4, 4)
        relations = torch.randn(4, 4)  # two predicates x forward/reverse
        outputs = head(q, entities, relations)
        self.assertEqual(tuple(outputs["anchor_logits"].shape), (2, 4))
        self.assertEqual(tuple(outputs["relation_direction_logits"].shape), (2, 4))
        self.assertEqual(tuple(outputs["entity_answer_logits"].shape), (2, 4))
        relation_labels = torch.tensor([[1, 0, 0, 0], [0, 0, 0, 1]])
        loss = aligned.alignment_loss(
            outputs, torch.tensor([2, 4]), torch.tensor([0, 3]), relation_labels,
            torch.tensor([0, 1]), predicate_count=2,
            hard_negative_ids=torch.tensor([3, 5]),
            query_negative_ids=torch.tensor([[0, 1], [5, 7]]))
        self.assertTrue(bool(torch.isfinite(loss)))
        loss.backward()
        self.assertIsNotNone(head.query_projection.weight.grad)
        self.assertTrue(bool(torch.isfinite(head.query_projection.weight.grad).all()))

    @unittest.skipIf(aligned.torch is None, "pinned PyTorch runtime is not installed")
    def test_oracle_structural_score_uses_supplied_directional_path(self):
        torch = aligned.torch
        entities = torch.tensor([[0., 0.], [2., 0.], [0., 2.]])
        relations = torch.tensor([[1., 0.], [0., 1.]])
        scores = aligned.oracle_structural_scores(entities, relations, 0, [0], [1, 2])
        self.assertGreater(float(scores[0]), float(scores[1]))

    @unittest.skipIf(aligned.torch is None, "pinned PyTorch runtime is not installed")
    def test_gold_free_path_ranking_keeps_edge_order_direction_and_witness(self):
        graph = "urn:graph-verity:wikidata:norway-org-v1"
        quads = [f"<urn:e:0> <urn:p:0> <urn:e:1> <{graph}> .",
                 f"<urn:e:2> <urn:p:1> <urn:e:1> <{graph}> ."]
        edges = [
            {"graph": graph, "subject_id": 0, "object_id": 1, "relation_id": 0,
             "direction": "forward", "source_quad": quads[0], "source_edge_id": "a"},
            {"graph": graph, "subject_id": 1, "object_id": 2, "relation_id": 3,
             "direction": "reverse", "source_quad": quads[1], "source_edge_id": "b"},
        ]
        nodes = [{"id": i, "iri": f"urn:e:{i}"} for i in range(3)]
        paths = run.rank_source_paths(
            aligned.torch.tensor([1., 0., 0.]), aligned.torch.tensor([.9, -.8, -.7, .8]),
            aligned.torch.tensor([0., 0., 1.]), run.source_adjacency(edges), nodes,
            anchor_limit=1, relation_limit=2)
        expected = run.path_id(quads, ["forward", "reverse"])
        self.assertEqual(paths[0]["path_id"], expected)
        self.assertEqual(paths[0]["source_quads"], quads)
        question = {"family": "two_hop_path", "traversal": {"steps": [
            {"direction": "forward"}, {"direction": "reverse"}]}}
        reference = {"status": "relevant", "relevant": [{"iri": "urn:e:2"}],
                     "witnesses": [{"source_quads": quads}]}
        self.assertEqual(run.path_retrieval_metrics(question, reference, paths)["recall@1"], 1.0)


class LeakageBoundaryTests(unittest.TestCase):
    def test_heldout_source_edge_filter_removes_both_navigation_directions(self):
        rows = [{"source_edge_id": "held", "direction": direction,
                 "subject_iri": "urn:e:a", "object_iri": "urn:e:b"}
                for direction in ("forward", "reverse")]
        rows.extend({"source_edge_id": "train", "direction": direction,
                     "subject_iri": "urn:e:a", "object_iri": "urn:e:c"}
                    for direction in ("forward", "reverse"))
        result = run._message_edges(rows, {"train"}, set())
        self.assertEqual([row["direction"] for row in result], ["forward", "reverse"])
        run._check_navigation_pairs(result)


if __name__ == "__main__":
    unittest.main()
