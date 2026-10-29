"""Small PyTorch R-GCN and CompGCN encoders for offline research only."""
from __future__ import annotations

import random
import math
import time

try:
    import torch
    from torch import nn
    from torch.nn import functional as F
    from torch_geometric.nn import RGCNConv
except ImportError:  # Model-free export and verification do not require PyTorch.
    torch = nn = F = RGCNConv = None


def compose_subtract(entities, relations):
    """CompGCN's documented subtraction operator: phi(e, r) = e - r."""
    if torch is not None and isinstance(entities, torch.Tensor):
        return entities - relations
    return [[left - right for left, right in zip(entity, relation)]
            for entity, relation in zip(entities, relations)]


def seed_everything(seed: int) -> None:
    if torch is None:
        raise RuntimeError("Install the repository-pinned ML requirements before training")
    random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    if torch.get_num_threads() != 4:
        torch.set_num_threads(4)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)


def check_edge_splits(train_ids, validation_ids, test_ids, message_passing_ids) -> None:
    """Reject query-edge overlap and any validation/test edge in encoder inputs."""
    train, validation, test = map(set, (train_ids, validation_ids, test_ids))
    if train & validation or train & test or validation & test:
        raise ValueError("An RDF edge is assigned to more than one split")
    if (validation | test) & set(message_passing_ids):
        raise ValueError("A held-out RDF edge is present in message passing")


def sample_negative_tails(positive_triples, known_triples, entity_count: int,
                          count: int = 10, seed: int = 117, entity_ids=None):
    """Uniform graph-local corruptions; unobserved triples are samples, not known false facts."""
    rng = random.Random(seed)
    known_by_head_relation = {}
    for head, relation, tail in known_triples:
        known_by_head_relation.setdefault((head, relation), set()).add(tail)
    sampled = []
    candidates = list(range(entity_count)) if entity_ids is None else list(entity_ids)
    for head, relation, _ in positive_triples:
        forbidden = known_by_head_relation.get((head, relation), set())
        pool = [tail for tail in candidates if tail not in forbidden]
        if len(pool) < count:
            raise ValueError("Not enough graph-local unobserved tails for negative sampling")
        sampled.append(rng.sample(pool, count))
    return torch.tensor(sampled, dtype=torch.long) if torch is not None else sampled


if torch is not None:
    class RGCNLayer(nn.Module):
        """PyG R-GCN convolution with a four-basis relation decomposition."""

        def __init__(self, width: int, relations: int):
            super().__init__()
            self.conv = RGCNConv(width, width, relations, num_bases=min(4, relations),
                                 aggr="mean", root_weight=True)

        def forward(self, entities, edge_index, edge_types):
            return F.relu(self.conv(entities, edge_index, edge_types))


    class CompGCNLayer(nn.Module):
        """CompGCN layer with subtraction composition and jointly updated relations."""

        def __init__(self, width: int):
            super().__init__()
            self.root = nn.Linear(width, width)
            self.message = nn.Linear(width, width, bias=False)
            self.relation_update = nn.Linear(width, width)

        def forward(self, entities, relations, edge_index, edge_types):
            source, target = edge_index
            aggregate = torch.zeros_like(entities)
            degree = entities.new_zeros((entities.shape[0], 1))
            composed = compose_subtract(entities[source], relations[edge_types])
            aggregate.index_add_(0, target, self.message(composed))
            degree.index_add_(0, target, entities.new_ones((len(target), 1)))
            return (F.relu(self.root(entities) + aggregate / degree.clamp_min(1)),
                    self.relation_update(relations))


    class _Base(nn.Module):
        def __init__(self, node_width: int, relation_width: int, hidden: int, relation_count: int):
            super().__init__()
            self.node_input = nn.Linear(node_width, hidden)
            self.relation_input = nn.Linear(relation_width, hidden)
            self.query_input = nn.Linear(node_width, hidden, bias=False)
            self.hidden = hidden
            self.relation_count = relation_count

        def score_tails(self, entities, relations, heads, relation_ids, candidate_ids):
            query = entities[heads] + relations[relation_ids]
            candidates = entities[candidate_ids]
            if candidate_ids.ndim == 1:
                difference = query[:, None, :] - candidates[None, :, :]
            else:
                difference = query[:, None, :] - candidates
            return -difference.square().sum(-1) / self.hidden ** 0.5

        def score_heads(self, entities, relations, tails, relation_ids, candidate_ids):
            query = entities[tails] - relations[relation_ids]
            candidates = entities[candidate_ids]
            if candidate_ids.ndim == 1:
                difference = query[:, None, :] - candidates[None, :, :]
            else:
                difference = query[:, None, :] - candidates
            return -difference.square().sum(-1) / self.hidden ** 0.5

        def score_queries(self, entities, relations, query_features,
                          entity_candidate_ids=None, relation_candidate_ids=None):
            queries = F.normalize(self.query_input(query_features), dim=-1)
            if entity_candidate_ids is None:
                entity_candidate_ids = torch.arange(entities.shape[0], device=entities.device)
            if relation_candidate_ids is None:
                relation_candidate_ids = torch.arange(relations.shape[0], device=relations.device)
            candidates = torch.cat((entities[entity_candidate_ids],
                                    relations[relation_candidate_ids]), dim=0)
            candidates = F.normalize(candidates, dim=-1)
            return queries @ candidates.T


    class RGCN(_Base):
        """R-GCN encoder; relation types have separate weights, triples stay directed."""

        def __init__(self, node_width: int, relation_width: int, hidden: int,
                     relation_count: int, layers: int = 2):
            super().__init__(node_width, relation_width, hidden, relation_count)
            self.layers = nn.ModuleList(RGCNLayer(hidden, relation_count) for _ in range(layers))

        def forward(self, node_features, relation_features, edge_index, edge_types):
            entities = self.node_input(node_features)
            relations = self.relation_input(relation_features)
            for layer in self.layers:
                entities = layer(entities, edge_index, edge_types)
            return entities, relations


    class CompGCN(_Base):
        """CompGCN encoder; entity and relation states update together each layer."""

        def __init__(self, node_width: int, relation_width: int, hidden: int,
                     relation_count: int, layers: int = 2):
            super().__init__(node_width, relation_width, hidden, relation_count)
            self.layers = nn.ModuleList(CompGCNLayer(hidden) for _ in range(layers))

        def forward(self, node_features, relation_features, edge_index, edge_types):
            entities = self.node_input(node_features)
            relations = self.relation_input(relation_features)
            for layer in self.layers:
                entities, relations = layer(entities, relations, edge_index, edge_types)
            return entities, relations


    def training_loss(model, node_features, relation_features, edge_index, edge_types,
                      positive_triples, negative_tail_ids, query_features=None,
                      query_targets=None, query_negative_ids=None):
        """Equal-weight link and question retrieval losses; negatives are frozen by the caller."""
        entities, relations = model(node_features, relation_features, edge_index, edge_types)
        heads, relation_ids, tails = positive_triples.T
        positive = model.score_tails(entities, relations, heads, relation_ids,
                                     tails[:, None]).squeeze(1)
        negative = model.score_tails(entities, relations, heads, relation_ids, negative_tail_ids)
        loss = F.softplus(-positive).mean() + F.softplus(negative).mean()
        if query_features is not None:
            scores = model.score_queries(entities, relations, query_features)
            rows = torch.arange(len(query_targets), device=entities.device)
            query_positive = scores[rows, query_targets]
            query_negative = scores[rows[:, None], query_negative_ids]
            loss = loss + F.softplus(-query_positive).mean() + F.softplus(query_negative).mean()
        return loss


    def fit(model_factory, training_args, validation_mrr, *, seed: int, epochs: int = 100,
            patience: int = 10, resource_guard=None):
        """Full-batch CPU optimizer; validation controls early stop, never gradient updates."""
        seed_everything(seed)
        model = model_factory()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        best, best_state, stale, history = float("-inf"), None, 0, []
        for epoch in range(epochs):
            started = time.perf_counter()
            model.train()
            optimizer.zero_grad(set_to_none=True)
            loss = training_loss(model, **training_args)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError("Training loss became non-finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            model.eval()
            with torch.no_grad():
                score = validation_mrr(model)
            if not math.isfinite(float(score)):
                raise RuntimeError("Validation MRR became non-finite")
            history.append({"epoch": epoch + 1, "loss": float(loss.detach()),
                            "validation_mrr@10": float(score),
                            "epoch_ms": (time.perf_counter() - started) * 1000.0})
            if resource_guard is not None:
                resource_guard(epoch + 1, history[-1])
            if score > best:
                best, stale = float(score), 0
                best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            else:
                stale += 1
                if stale >= patience:
                    break
        if best_state is not None:
            model.load_state_dict(best_state)
        return model, {"seed": seed, "best_validation_mrr@10": best,
                       "epochs": len(history), "history": history}

else:
    class RGCN:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Install the repository-pinned ML requirements before training")

    class CompGCN(RGCN):
        pass

    def training_loss(*args, **kwargs):
        raise RuntimeError("Install the repository-pinned ML requirements before training")

    def fit(*args, **kwargs):
        raise RuntimeError("Install the repository-pinned ML requirements before training")
