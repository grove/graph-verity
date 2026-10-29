"""Direction-aware alignment and evaluation primitives for the v4 ablations."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Iterable

try:
    import torch
    from torch import nn
    from torch.nn import functional as F
except ImportError:  # Preprocessing and the deterministic sampler stay model-free.
    torch = nn = F = None


def relation_balanced_edge_indices(relation_ids: Iterable[int], *, per_relation_cap: int,
                                   seed: int) -> list[int]:
    """Cap frequent relations per epoch while retaining every rare relation edge."""
    if per_relation_cap <= 0:
        raise ValueError("per_relation_cap must be positive")
    groups = defaultdict(list)
    for index, relation_id in enumerate(relation_ids):
        groups[int(relation_id)].append(index)
    rng = random.Random(seed)
    selected = []
    for relation_id in sorted(groups):
        indexes = groups[relation_id]
        if len(indexes) > per_relation_cap:
            indexes = rng.sample(indexes, per_relation_cap)
        selected.extend(indexes)
    return sorted(selected)


def relation_balanced_source_ids(source_relations: Iterable[tuple[str, int]], *,
                                per_relation_cap: int, seed: int) -> set[str]:
    """Sample original source edges per predicate; callers retain both navigation directions."""
    rows = {}
    for source_id, relation_id in source_relations:
        previous = rows.setdefault(source_id, int(relation_id))
        if previous != int(relation_id):
            raise ValueError("One RDF source edge cannot have multiple predicate IDs")
    ordered = sorted(rows.items())
    kept = relation_balanced_edge_indices([relation for _, relation in ordered],
                                          per_relation_cap=per_relation_cap, seed=seed)
    return {ordered[index][0] for index in kept}


def direction_hard_negative(question: dict, reference: dict,
                            entity_ids: dict[str, int], predicate_ids: dict[str, int]) -> dict | None:
    """Return an observed wrong-direction endpoint as a contrastive candidate."""
    family = question["family"]
    if family in {"forward_one_hop", "reverse_one_hop"}:
        if not reference["witnesses"] or not reference["witnesses"][0]["source_quads"]:
            return None
        parts = reference["witnesses"][0]["source_quads"][0].split("<")
        if len(parts) < 5:
            return None
        subject, obj = parts[1].split(">", 1)[0], parts[3].split(">", 1)[0]
        iri = subject if family == "forward_one_hop" else obj
        target_iris = {row["iri"] for row in reference["relevant"]}
        if iri in target_iris or iri not in entity_ids:
            return None
        return {"candidate_id": entity_ids[iri], "iri": iri,
                "kind": "observed_opposite_endpoint", "contrastive_only": True,
                "source_quad": reference["witnesses"][0]["source_quads"][0]}
    if family == "predicate_retrieval":
        target_iris = {row["iri"] for row in reference["relevant"]}
        for item in reference.get("hard_negatives", []):
            iri = item.get("iri")
            if item.get("kind") == "wrong-predicate" and iri in predicate_ids and iri not in target_iris:
                return {"candidate_id": predicate_ids[iri], "iri": iri,
                        "kind": "observed_wrong_predicate", "contrastive_only": True,
                        "source_quads": item.get("source_quads", [])}
    return None


def pooled_predicate_scores(directional_scores, predicate_count: int):
    """Collapse forward/reverse scores to one answer candidate per RDF predicate."""
    if directional_scores.shape[-1] != 2 * predicate_count:
        raise ValueError("Expected exactly one forward/reverse score pair per predicate")
    if torch is not None and isinstance(directional_scores, torch.Tensor):
        return directional_scores.reshape(*directional_scores.shape[:-1], predicate_count, 2).amax(dim=-1)
    return [[max(row[2 * i], row[2 * i + 1]) for i in range(predicate_count)]
            for row in directional_scores]


def rank_shared_pool(candidate_ids: list[int], score_by_id: dict[int, float],
                     limit: int = 50) -> list[int]:
    """Rerank only the supplied baseline pool; never add a missing candidate."""
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Shared candidate pool contains duplicate IDs")
    if any(candidate_id not in score_by_id for candidate_id in candidate_ids):
        raise ValueError("A shared-pool candidate has no GNN score")
    original_rank = {candidate_id: index for index, candidate_id in enumerate(candidate_ids)}
    return sorted(candidate_ids, key=lambda item: (-float(score_by_id[item]), original_rank[item]))[:limit]


def oracle_structural_scores(entities, relations, anchor_id: int,
                              directional_relation_ids: list[int], candidate_ids):
    """Score endpoints with gold anchor/path labels; diagnostic only, never end-to-end."""
    if not directional_relation_ids:
        raise ValueError("Oracle path needs at least one relation step")
    if torch is None or not isinstance(entities, torch.Tensor):
        raise RuntimeError("Oracle structural scoring requires the pinned PyTorch runtime")
    query = entities[anchor_id]
    for relation_id in directional_relation_ids:
        query = query + relations[relation_id]
    candidates = entities[torch.as_tensor(candidate_ids, dtype=torch.long, device=entities.device)]
    return -(query[None, :] - candidates).square().sum(dim=-1) / entities.shape[-1] ** 0.5


def check_alignment_splits(train_question_ids: list[str], validation_question_ids: list[str],
                           test_question_ids: list[str], query_groups: dict[str, str],
                           train_source_edge_ids: set[str], heldout_source_edge_ids: set[str],
                           message_passing_source_edge_ids: set[str]) -> None:
    """Keep paraphrase families and both directions of each source edge together."""
    partitions = [set(train_question_ids), set(validation_question_ids), set(test_question_ids)]
    if any(partitions[i] & partitions[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError("Question IDs overlap between alignment splits")
    group_splits = defaultdict(set)
    for split_name, ids in zip(("train", "validation", "test"), partitions):
        for question_id in ids:
            if question_id not in query_groups:
                raise ValueError("Question is missing its frozen source-lineage group")
            group_splits[query_groups[question_id]].add(split_name)
    if any(len(values) > 1 for values in group_splits.values()):
        raise ValueError("A source-lineage group crosses alignment splits")
    if train_source_edge_ids & heldout_source_edge_ids:
        raise ValueError("Source edge is both training and held out")
    if message_passing_source_edge_ids & heldout_source_edge_ids:
        raise ValueError("A held-out source edge or its inverse is in message passing")


if nn is not None:
    class QuestionGraphAlignmentHead(nn.Module):
        """Explicitly predict anchor, predicate/direction, and answer candidates."""

        def __init__(self, question_width: int, hidden: int):
            super().__init__()
            self.query_projection = nn.Linear(question_width, hidden, bias=False)

        def forward(self, question_features, entity_states, directional_relation_states):
            query = F.normalize(self.query_projection(question_features), dim=-1)
            entities = F.normalize(entity_states, dim=-1)
            relations = F.normalize(directional_relation_states, dim=-1)
            anchor_logits = query @ entities.T
            relation_direction_logits = query @ relations.T
            anchor_context = anchor_logits.softmax(-1) @ entities
            relation_context = relation_direction_logits.softmax(-1) @ relations
            target_query = F.normalize(query + anchor_context + relation_context, dim=-1)
            entity_answer_logits = target_query @ entities.T
            return {"anchor_logits": anchor_logits,
                    "relation_direction_logits": relation_direction_logits,
                    "entity_answer_logits": entity_answer_logits,
                    "query_projection": query}


    def alignment_loss(outputs, entity_targets, anchor_targets, relation_direction_targets,
                       roles, predicate_count: int, hard_negative_ids=None,
                       query_negative_ids=None):
        """Add anchor and direction supervision to the frozen sampled retrieval objective."""
        zero = outputs["entity_answer_logits"].sum() * 0
        candidate_scores = torch.cat((outputs["entity_answer_logits"],
                                      outputs["relation_direction_logits"]), dim=-1)
        rows = torch.arange(len(roles), device=roles.device)
        positive_scores = candidate_scores[rows, entity_targets]
        answer_loss = F.softplus(-positive_scores).mean()
        if query_negative_ids is not None:
            negative_scores = candidate_scores[rows[:, None], query_negative_ids]
            answer_loss = answer_loss + F.softplus(negative_scores).mean()
        anchor_mask = anchor_targets >= 0
        anchor_loss = (F.cross_entropy(outputs["anchor_logits"][anchor_mask], anchor_targets[anchor_mask])
                       if bool(anchor_mask.any()) else zero)
        relation_loss = F.binary_cross_entropy_with_logits(
            outputs["relation_direction_logits"], relation_direction_targets.float())
        contrastive_loss = zero
        if hard_negative_ids is not None:
            hard_mask = hard_negative_ids >= 0
            if bool(hard_mask.any()):
                hard_scores = candidate_scores[rows[hard_mask], hard_negative_ids[hard_mask]]
                positive_scores = candidate_scores[rows[hard_mask], entity_targets[hard_mask]]
                contrastive_loss = F.softplus(hard_scores - positive_scores + 0.1).mean()
        return answer_loss + anchor_loss + relation_loss + contrastive_loss
else:
    class QuestionGraphAlignmentHead:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Install the pinned PyTorch runtime before alignment training")

    def alignment_loss(*args, **kwargs):
        raise RuntimeError("Install the pinned PyTorch runtime before alignment training")
