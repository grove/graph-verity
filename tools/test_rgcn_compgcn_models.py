"""Tiny synthetic checks only; no research graph or training schedule is run."""
import tempfile
import unittest
from pathlib import Path

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

    def test_negative_tail_sampling_respects_inductive_entity_pool(self):
        values = models.sample_negative_tails([(0, 0, 1)], [(0, 0, 1)],
                                              entity_count=5, count=2, seed=9,
                                              entity_ids=[0, 1, 2])
        if models.torch is not None:
            values = values.tolist()
        self.assertEqual(len(values[0]), 2)
        self.assertTrue(set(values[0]).isdisjoint({1, 3, 4}))

    def test_edge_split_guard_rejects_overlap_and_held_out_message_edges(self):
        models.check_edge_splits([0, 1], [2], [3], [0, 1])
        with self.assertRaisesRegex(ValueError, "assigned to more than one split"):
            models.check_edge_splits([0, 1], [1], [3], [0])
        with self.assertRaisesRegex(ValueError, "held-out RDF edge"):
            models.check_edge_splits([0, 1], [2], [3], [0, 3])

    @unittest.skipIf(models.torch is None, "pinned PyTorch runtime is not installed in this model-free environment")
    def test_encoders_forward_backward_checkpoint_and_seed_on_synthetic_fixture(self):
        torch = models.torch
        node_features = torch.tensor([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        relation_features = torch.tensor([[1., 1., 0.], [0., 1., 1.]])
        edges = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)  # subject -> object
        edge_types = torch.tensor([0, 1], dtype=torch.long)
        positive = torch.tensor([[0, 0, 1], [1, 1, 2]], dtype=torch.long)
        negative = torch.tensor([[2, 0], [0, 1]], dtype=torch.long)
        query_features = torch.tensor([[.2, .3, .5], [.8, .1, .1]])
        query_targets = torch.tensor([1, 3])  # entity 1; relation 0 after three entities
        query_negatives = torch.tensor([[0, 4], [0, 2]], dtype=torch.long)
        for encoder in (models.RGCN, models.CompGCN):
            models.seed_everything(117)
            model = encoder(3, 3, 4, 2, layers=2)
            entities, relations = model(node_features, relation_features, edges, edge_types)
            reverse_entities, _ = model(node_features, relation_features, edges.flip(0), edge_types)
            self.assertFalse(bool(torch.allclose(entities, reverse_entities)))
            scores = model.score_tails(entities, relations, torch.tensor([0]), torch.tensor([0]),
                                       torch.tensor([[1, 2]]))
            reverse_scores = model.score_heads(entities, relations, torch.tensor([1]), torch.tensor([0]),
                                               torch.tensor([[0, 2]]))
            self.assertEqual(tuple(entities.shape), (3, 4))
            self.assertEqual(tuple(relations.shape), (2, 4))
            self.assertEqual(tuple(scores.shape), (1, 2))
            self.assertEqual(tuple(reverse_scores.shape), (1, 2))
            query_scores = model.score_queries(entities, relations, query_features)
            self.assertEqual(tuple(query_scores.shape), (2, 5))
            forward_edge_score = model.score_tails(entities, relations, torch.tensor([0]),
                                                   torch.tensor([0]), torch.tensor([1]))
            reverse_edge_score = model.score_heads(entities, relations, torch.tensor([1]),
                                                   torch.tensor([0]), torch.tensor([0]))
            self.assertTrue(bool(torch.allclose(forward_edge_score, reverse_edge_score)))
            reversed_triple_score = model.score_tails(entities, relations, torch.tensor([1]),
                                                      torch.tensor([0]), torch.tensor([0]))
            self.assertFalse(bool(torch.allclose(forward_edge_score, reversed_triple_score)))
            self.assertTrue(bool(torch.isfinite(scores).all()))

            before = {name: value.detach().clone() for name, value in model.state_dict().items()}
            loss = models.training_loss(
                model, node_features, relation_features, edges, edge_types, positive, negative,
                query_features, query_targets, query_negatives,
            )
            self.assertTrue(bool(torch.isfinite(loss)))
            loss.backward()
            gradients = [parameter.grad for parameter in model.parameters() if parameter.requires_grad]
            self.assertTrue(gradients and all(grad is not None and torch.isfinite(grad).all()
                                              for grad in gradients))
            optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.0001)
            optimizer.step()  # One test-only update on the synthetic fixture.
            self.assertTrue(any(not torch.equal(before[name], value)
                                for name, value in model.state_dict().items()))

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "model.pt"
                torch.save(model.state_dict(), path)
                restored = encoder(3, 3, 4, 2, layers=2)
                restored.load_state_dict(torch.load(path, weights_only=True))
                restored_entities, restored_relations = restored(node_features, relation_features,
                                                                   edges, edge_types)
                self.assertTrue(bool(torch.allclose(model(node_features, relation_features,
                                                          edges, edge_types)[0], restored_entities)))
                self.assertTrue(bool(torch.allclose(model(node_features, relation_features,
                                                          edges, edge_types)[1], restored_relations)))

            models.seed_everything(117)
            repeat = encoder(3, 3, 4, 2, layers=2)
            models.seed_everything(117)
            repeat_again = encoder(3, 3, 4, 2, layers=2)
            self.assertTrue(all(torch.equal(left, right) for left, right in
                                zip(repeat.parameters(), repeat_again.parameters())))


if __name__ == "__main__":
    unittest.main()
