"""Tiny forward-only checks; these tests never optimize or save model weights."""
import unittest

import rgcn_compgcn_models as models


class ModelTests(unittest.TestCase):
    def test_compgcn_subtraction_operator(self):
        self.assertEqual(models.compose_subtract([[4.0, 2.0]], [[1.0, 3.0]]), [[3.0, -1.0]])

    def test_negative_tail_sampling_is_seeded_and_filters_known_positives(self):
        positives = [(0, 0, 1), (0, 1, 2)]
        known = positives + [(0, 0, 3)]
        first = models.sample_negative_tails(positives, known, entity_count=5, count=2, seed=9)
        second = models.sample_negative_tails(positives, known, entity_count=5, count=2, seed=9)
        if models.torch is not None:
            first, second = first.tolist(), second.tolist()
        self.assertEqual(first, second)
        self.assertTrue(set(first[0]).isdisjoint({1, 3}))
        self.assertTrue(set(first[1]).isdisjoint({2}))

    def test_negative_tail_sampling_rejects_exhausted_candidate_set(self):
        with self.assertRaisesRegex(ValueError, "Not enough"):
            models.sample_negative_tails([(0, 0, 1)], [(0, 0, 0), (0, 0, 1)],
                                         entity_count=2, count=1)

    @unittest.skipIf(models.torch is None, "pinned PyTorch runtime is not installed in this model-free environment")
    def test_encoders_preserve_directed_edge_inputs_and_emit_comparable_shapes(self):
        torch = models.torch
        node_features = torch.tensor([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        relation_features = torch.tensor([[1., 1., 0.], [0., 1., 1.]])
        edges = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)  # subject -> object
        edge_types = torch.tensor([0, 1], dtype=torch.long)
        outputs = []
        for encoder in (models.RGCN, models.CompGCN):
            models.seed_everything(117)
            model = encoder(3, 3, 4, 2, layers=2)
            entities, relations = model(node_features, relation_features, edges, edge_types)
            scores = model.score_tails(entities, relations, torch.tensor([0]), torch.tensor([0]),
                                       torch.tensor([[1, 2]]))
            reverse_scores = model.score_heads(entities, relations, torch.tensor([1]), torch.tensor([0]),
                                               torch.tensor([[0, 2]]))
            self.assertEqual(tuple(entities.shape), (3, 4))
            self.assertEqual(tuple(relations.shape), (2, 4))
            self.assertEqual(tuple(scores.shape), (1, 2))
            self.assertEqual(tuple(reverse_scores.shape), (1, 2))
            forward_edge_score = model.score_tails(entities, relations, torch.tensor([0]),
                                                   torch.tensor([0]), torch.tensor([1]))
            reverse_edge_score = model.score_heads(entities, relations, torch.tensor([1]),
                                                   torch.tensor([0]), torch.tensor([0]))
            self.assertTrue(bool(torch.allclose(forward_edge_score, reverse_edge_score)))
            self.assertTrue(bool(torch.isfinite(scores).all()))
            outputs.append((entities.detach(), relations.detach()))
        for expected, actual in zip(outputs[0], outputs[1]):
            self.assertEqual(tuple(expected.shape), tuple(actual.shape))


if __name__ == "__main__":
    unittest.main()
