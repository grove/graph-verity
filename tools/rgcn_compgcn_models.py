"""Small PyTorch R-GCN and CompGCN encoders for offline research only."""
from __future__ import annotations

import random

try:
    import torch
    from torch import nn
    from torch.nn import functional as F
except ImportError:  # Model-free export and verification do not require PyTorch.
    torch = nn = F = None


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


def sample_negative_tails(positive_triples, known_triples, entity_count: int,
                          count: int = 10, seed: int = 117):
    """Uniform graph-local corruptions; unobserved triples are samples, not known false facts."""
    rng = random.Random(seed)
    known_by_head_relation = {}
    for head, relation, tail in known_triples:
        known_by_head_relation.setdefault((head, relation), set()).add(tail)
    sampled = []
    for head, relation, _ in positive_triples:
        forbidden = known_by_head_relation.get((head, relation), set())
        pool = [tail for tail in range(entity_count) if tail not in forbidden]
        if len(pool) < count:
            raise ValueError("Not enough graph-local unobserved tails for negative sampling")
        sampled.append(rng.sample(pool, count))
    return torch.tensor(sampled, dtype=torch.long) if torch is not None else sampled


if torch is not None:
    class RGCNLayer(nn.Module):
        """Incoming, relation-specific message transforms over original RDF edges."""

        def __init__(self, width: int, relations: int):
            super().__init__()
            self.root = nn.Linear(width, width)
            self.transforms = nn.Parameter(torch.empty(relations, width, width))
            nn.init.xavier_uniform_(self.transforms)

        def forward(self, entities, edge_index, edge_types):
            source, target = edge_index
            aggregate = torch.zeros_like(entities)
            degree = entities.new_zeros((entities.shape[0], 1))
            for relation in range(self.transforms.shape[0]):
                selected = edge_types == relation
                if selected.any():
                    destinations = target[selected]
                    messages = entities[source[selected]] @ self.transforms[relation]
                    aggregate.index_add_(0, destinations, messages)
                    degree.index_add_(0, destinations, entities.new_ones((len(destinations), 1)))
            return F.relu(self.root(entities) + aggregate / degree.clamp_min(1))


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
                return query @ candidates.T / self.hidden ** 0.5
            return (query[:, None, :] * candidates).sum(-1) / self.hidden ** 0.5

        def score_heads(self, entities, relations, tails, relation_ids, candidate_ids):
            tails = entities[tails]
            candidates = entities[candidate_ids]
            relation_vectors = relations[relation_ids]
            if candidate_ids.ndim == 1:
                candidates = candidates[None, :, :] + relation_vectors[:, None, :]
                return (tails[:, None, :] * candidates).sum(-1) / self.hidden ** 0.5
            candidates = candidates + relation_vectors[:, None, :]
            return (tails[:, None, :] * candidates).sum(-1) / self.hidden ** 0.5

        def score_queries(self, entities, query_features, candidate_ids):
            queries = F.normalize(self.query_input(query_features), dim=-1)
            candidates = F.normalize(entities[candidate_ids], dim=-1)
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
        positive = (entities[heads] + relations[relation_ids]) * entities[tails]
        positive = positive.sum(-1) / model.hidden ** 0.5
        negative = model.score_tails(entities, relations, heads, relation_ids, negative_tail_ids)
        loss = F.softplus(-positive).mean() + F.softplus(negative).mean()
        if query_features is not None:
            scores = model.score_queries(entities, query_features,
                                         torch.arange(entities.shape[0], device=entities.device))
            rows = torch.arange(len(query_targets), device=entities.device)
            query_positive = scores[rows, query_targets]
            query_negative = scores[rows[:, None], query_negative_ids]
            loss = loss + F.softplus(-query_positive).mean() + F.softplus(query_negative).mean()
        return loss


    def fit(model_factory, training_args, validation_mrr, *, seed: int, epochs: int = 100,
            patience: int = 10):
        """Full-batch CPU optimizer; validation controls early stop, never gradient updates."""
        seed_everything(seed)
        model = model_factory()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        best, best_state, stale, history = float("-inf"), None, 0, []
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            loss = training_loss(model, **training_args)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            model.eval()
            with torch.no_grad():
                score = validation_mrr(model)
            history.append({"epoch": epoch + 1, "loss": float(loss.detach()), "validation_mrr@10": float(score)})
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
