#!/usr/bin/env python3
"""Version-2 Wikidata benchmark and source-witnessed adjacency baseline."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import rgcn_compgcn as v1

ROOT = v1.ROOT
GRAPH = "urn:graph-verity:wikidata:norway-org-v1"
EXPORT = ROOT / "experiments/rgcn-compgcn-v1/wikidata-norway-org-v1/rdf-to-gnn-v1"
OUT = ROOT / "experiments/rgcn-compgcn-v2/wikidata-relations-v1"
LANGS = ("en", "no")
NO_RELATIONS = {
    "P17": "land", "P31": "type", "P452": "bransje", "P1454": "juridisk form",
    "P47": "grenser til", "P159": "hovedkontor", "P131": "administrativ enhet",
    "P749": "moderorganisasjon", "P190": "vennskapsorgan", "P37": "offisielt språk",
    "P2936": "språk brukt", "P6": "regjeringssjef", "P36": "hovedstad",
    "P527": "har som del", "P127": "eid av", "P463": "medlem av",
}
SELECTED = tuple(NO_RELATIONS)
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
GEMET_LABEL = "http://www.w3.org/2004/02/skos/core#prefLabel"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def edge_key(edge: dict) -> str:
    raw = "\0".join((edge["graph"], edge["subject_iri"], edge["predicate"], edge["object_iri"]))
    return sha_bytes(raw.encode())


def split_for(group: str) -> str:
    value = int(sha_bytes(("117\0" + group).encode())[:8], 16) % 100
    return "train" if value < 70 else "validation" if value < 85 else "test"


def label(node: dict, language: str) -> str | None:
    labels = node["labels"]
    if language == "en":
        return next(iter(labels.get("en", [])), None)
    for lang in ("nb", "nn", "no"):
        value = next(iter(labels.get(lang, [])), None)
        if value:
            return value
    return None


def prop_code(iri: str) -> str:
    return iri.rsplit("/", 1)[-1]


def prop_label(relation: dict, language: str) -> str:
    code = prop_code(relation["iri"])
    if language == "no":
        return NO_RELATIONS[code]
    return next(iter(relation["labels"].get("en", [])), code)


def nquad(edge: dict) -> str:
    return f"<{edge['subject_iri']}> <{edge['predicate']}> <{edge['object_iri']}> <{edge['graph']}> ."


def audit_graph(export: Path = EXPORT) -> dict:
    manifest = json.loads((export / "manifest.json").read_text())
    nodes, edges, relations = (read_jsonl(export / name) for name in
                               ("nodes.jsonl", "edges.jsonl", "relations.jsonl"))
    counts = Counter(edge["predicate"] for edge in edges)
    node_by_id = {node["id"]: node for node in nodes}
    outgoing = defaultdict(list)
    for edge in edges:
        outgoing[edge["subject_id"]].append(edge)
    paths = [(first, second) for first in edges if prop_code(first["predicate"]) not in {"P17", "P31"}
             for second in outgoing[first["object_id"]]
             if prop_code(second["predicate"]) not in {"P17", "P31"}
             and first["subject_id"] != second["object_id"]]
    top5 = sum(count for _, count in counts.most_common(5)) / len(edges)
    root = ROOT / "experiments/rgcn-compgcn-v1/wikidata-norway-org-v1"
    return {
        "version": "wikidata-relational-audit-v1",
        "decision": "Use the existing CC0 Wikidata slice and broaden relation families; do not claim service-operator adequacy.",
        "source": "Wikidata Query Service retained responses; direct claims from first 1,000 IRI-ordered items with P17=Norway and P31=Organization.",
        "license": "CC0 for Wikidata structured data",
        "graph_scope": [GRAPH],
        "source_response_sha256": {name: sha(root / name) for name in
            ("entity-selection-response.json", "direct-claim-edge-response.json", "node-and-predicate-label-response.json")},
        "source_export_manifest_sha256": sha(export / "manifest.json"),
        "snapshot_sha256": manifest["export_sha256"]["snapshot.nq"],
        "source_edge_policy": "Only original direct claims; direction and identifiers preserved; no reverse or inferred triples.",
        "entities": len(nodes), "directed_edges": len(edges), "distinct_predicates": len(counts),
        "predicate_counts": dict(sorted(counts.items())),
        "predicates_with_at_least_20_edges": sum(value >= 20 for value in counts.values()),
        "top_five_predicate_edge_share": top5,
        "entity_label_coverage": {
            lang: sum(bool(label(node, lang)) for node in nodes) for lang in LANGS},
        "two_hop_paths_excluding_P17_and_P31": len(paths),
        "unique_two_hop_endpoint_pairs_excluding_P17_and_P31": len({
            (first["subject_id"], second["object_id"]) for first, second in paths}),
        "weak_components": manifest["stats"]["weak_components"],
        "largest_weak_component": manifest["stats"]["largest_weak_component"],
        "operator_P137_edges": counts.get("http://www.wikidata.org/prop/direct/P137", 0),
        "limitations": ["IRI-ordered 1,000-root sample is not representative.",
                        "One weak component is largely caused by shared country/type/industry objects.",
                        "The top five predicates dominate; operator P137 has one edge.",
                        "Norwegian questions are author-translated; property labels are mostly English.",
                        "No independent human relevance review is available."],
    }


def choose_examples(nodes: list[dict], edges: list[dict], relations: list[dict]):
    node_by_id = {node["id"]: node for node in nodes}
    relation_by_iri = {relation["iri"]: relation for relation in relations}
    selected_predicates = {"http://www.wikidata.org/prop/direct/" + code for code in SELECTED}
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    pair_edges = defaultdict(list)
    for edge in edges:
        outgoing[(edge["subject_id"], edge["predicate"])].append(edge)
        incoming[(edge["object_id"], edge["predicate"])].append(edge)
        pair_edges[(edge["subject_id"], edge["object_id"])].append(edge)
    eligible = [edge for edge in edges if edge["predicate"] in selected_predicates
                and edge["subject_id"] != edge["object_id"]
                and all(label(node_by_id[node_id], lang) for node_id in
                        (edge["subject_id"], edge["object_id"]) for lang in LANGS)
                and len(outgoing[(edge["subject_id"], edge["predicate"])]) == 1
                and len(incoming[(edge["object_id"], edge["predicate"])]) == 1
                and len(pair_edges[(edge["subject_id"], edge["object_id"])]) == 1]
    reserved: set[str] = set()
    path_examples = []
    by_subject = defaultdict(list)
    for edge in edges:
        by_subject[edge["subject_id"]].append(edge)
    path_candidates = defaultdict(list)
    for first in edges:
        if first["predicate"] not in selected_predicates:
            continue
        for second in by_subject[first["object_id"]]:
            if second["predicate"] not in selected_predicates or first["subject_id"] == second["object_id"]:
                continue
            if any(not label(node_by_id[node_id], lang) for node_id in
                   (first["subject_id"], second["object_id"]) for lang in LANGS):
                continue
            query_key = (first["subject_id"], first["predicate"], second["predicate"])
            matching_targets = {edge2["object_id"] for edge in by_subject[first["subject_id"]]
                                if edge["predicate"] == first["predicate"]
                                for edge2 in by_subject[edge["object_id"]]
                                if edge2["predicate"] == second["predicate"]}
            if len(matching_targets) != 1 or second["object_id"] not in matching_targets:
                continue
            pair = (first, second)
            if pair not in path_candidates[query_key]:
                path_candidates[query_key].append(pair)
    # Keep one path per edge-overlap component so a held-out path cannot share
    # one of its source statements with a query in another split.
    parent = {key: key for key in path_candidates}
    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    edge_owner = {}
    for key, pairs in path_candidates.items():
        for edge in {edge_key(edge): edge for pair in pairs for edge in pair}.values():
            edge_id = edge_key(edge)
            if edge_id in edge_owner:
                parent[find(key)] = find(edge_owner[edge_id])
            else:
                edge_owner[edge_id] = key
    components = defaultdict(list)
    for key, pairs in path_candidates.items():
        components[find(key)].append((key, pairs))
    representatives = []
    for values in components.values():
        representatives.append(min(values, key=lambda value: sha_bytes(repr(value[0]).encode())))
    for _, pairs in sorted(representatives, key=lambda value: sha_bytes(repr(value[0]).encode())):
        keys = {edge_key(edge) for pair in pairs for edge in pair}
        if reserved & keys:
            continue
        reserved |= keys
        path_examples.append(pairs)
        if len(path_examples) == 20:
            break
    direct_examples = []
    used_predicates = Counter()
    for edge in sorted(eligible, key=lambda row: sha_bytes(edge_key(row).encode())):
        if edge_key(edge) in reserved:
            continue
        code = prop_code(edge["predicate"])
        if used_predicates[code] >= 4:
            continue
        direct_examples.append(edge)
        reserved.add(edge_key(edge))
        used_predicates[code] += 1
    if len(direct_examples) < 24 or len(path_examples) < 12:
        raise ValueError(f"Insufficient unique bilingual examples: {len(direct_examples)} direct, {len(path_examples)} paths")
    return node_by_id, relation_by_iri, direct_examples, path_examples


def add_question(questions, references, *, group, language, family, role, query, traversal,
                 positives, witnesses, hard_negatives=(), status="relevant"):
    split = split_for(group)
    case_id = f"{sha_bytes(group.encode())[:16]}-{family}-{language}"
    questions.append({"id": case_id, "split": split, "language": language, "family": family,
                      "role": role, "query": query, "query_group": group, "traversal": traversal})
    references.append({"id": case_id, "split": split, "language": language, "family": family,
                       "role": role, "status": status,
                       "relevant": [{"graph": GRAPH, "iri": iri} for iri in sorted(set(positives))],
                       "witnesses": [{"source_quads": sorted({nquad(edge) for edge in path})}
                                     for path in witnesses],
                       "hard_negatives": list(hard_negatives), "review_status": "AI_reference_only",
                       "judgment_note": "Agent-authored, source-checked development evidence; not expert gold."})


def make_cases(export: Path = EXPORT) -> tuple[list[dict], list[dict], dict]:
    nodes = read_jsonl(export / "nodes.jsonl")
    edges = read_jsonl(export / "edges.jsonl")
    relations = read_jsonl(export / "relations.jsonl")
    node_by_id, relation_by_iri, direct, paths = choose_examples(nodes, edges, relations)
    questions, references = [], []
    all_edges = {edge_key(edge): edge for edge in edges}
    for edge in direct:
        group = "edge-" + edge_key(edge)
        subject, obj = node_by_id[edge["subject_id"]], node_by_id[edge["object_id"]]
        relation = relation_by_iri[edge["predicate"]]
        for language in LANGS:
            source, target, relation_text = label(subject, language), label(obj, language), prop_label(relation, language)
            if language == "en":
                forward = f"Which entity is the value of the property ‘{relation_text}’ for {source}?"
                reverse = f"Which entity has {target} as the value of the property ‘{relation_text}’?"
                predicate = f"Which RDF property connects {source} to {target}?"
            else:
                forward = f"Hvilken enhet er verdien for egenskapen «{relation_text}» for {source}?"
                reverse = f"Hvilken enhet har {target} som verdi for egenskapen «{relation_text}»?"
                predicate = f"Hvilken RDF-egenskap knytter {source} til {target}?"
            wrong = next((other for other in all_edges.values()
                          if other["subject_id"] == edge["subject_id"]
                          and other["predicate"] != edge["predicate"]
                          and other["object_id"] != edge["object_id"]), None)
            hard = [{"graph": GRAPH, "iri": edge["subject_iri"], "kind": "reverse-direction",
                     "source_quads": [nquad(edge)],
                     "note": "Observed endpoint in the wrong answer direction; contrastive, not a false RDF claim."}]
            if wrong:
                hard.append({"graph": GRAPH, "iri": wrong["object_iri"], "kind": "wrong-predicate",
                             "source_quads": [nquad(wrong)],
                             "note": "Observed under another predicate; contrastive, not a known-false triple."})
            add_question(questions, references, group=group, language=language, family="forward_one_hop",
                         role="entity", query=forward,
                         traversal={"kind": "path", "start_iri": edge["subject_iri"],
                                    "steps": [{"predicate": edge["predicate"], "direction": "forward"}]},
                         positives=[edge["object_iri"]], witnesses=[(edge,)], hard_negatives=hard)
            add_question(questions, references, group=group, language=language, family="reverse_one_hop",
                         role="entity", query=reverse,
                         traversal={"kind": "path", "start_iri": edge["object_iri"],
                                    "steps": [{"predicate": edge["predicate"], "direction": "reverse"}]},
                         positives=[edge["subject_iri"]], witnesses=[(edge,)], hard_negatives=hard)
            add_question(questions, references, group=group, language=language, family="predicate_retrieval",
                         role="predicate", query=predicate,
                         traversal={"kind": "endpoints", "subject_iri": edge["subject_iri"],
                                    "object_iri": edge["object_iri"]},
                         positives=[edge["predicate"]], witnesses=[(edge,)], hard_negatives=hard)
    for pairs in paths:
        first, second = pairs[0]
        group = "path-" + sha_bytes((str(first["subject_id"]) + first["predicate"]
                                     + second["predicate"]).encode())
        targets = sorted({pair[1]["object_iri"] for pair in pairs})
        for language in LANGS:
            source = label(node_by_id[first["subject_id"]], language)
            first_label = prop_label(relation_by_iri[first["predicate"]], language)
            second_label = prop_label(relation_by_iri[second["predicate"]], language)
            if language == "en":
                query = f"Which entity is reached from {source} via ‘{first_label}’ and then ‘{second_label}’?"
            else:
                query = f"Hvilken enhet nås fra {source} via «{first_label}» og deretter «{second_label}»?"
            add_question(questions, references, group=group, language=language, family="two_hop_path",
                         role="entity", query=query,
                         traversal={"kind": "path", "start_iri": first["subject_iri"], "steps":[
                             {"predicate": first["predicate"], "direction": "forward"},
                             {"predicate": second["predicate"], "direction": "forward"}]},
                         positives=targets, witnesses=pairs)
    # Ambiguous exact aliases are retained as multi-target cases, never forced into a single answer.
    alias_nodes = defaultdict(list)
    for node in nodes:
        for lang, values in node["labels"].items():
            for value in values:
                if len(value) >= 6:
                    alias_nodes[(lang, value.casefold())].append((node, value))
    ambiguous = [(key, values) for key, values in alias_nodes.items() if len({n["id"] for n, _ in values}) > 1]
    chosen = sorted(ambiguous, key=lambda item: sha_bytes(repr(item[0]).encode()))[:4]
    nq_lines = sorted(set((export / "snapshot.nq").read_text().splitlines()))
    for (source_lang, _), values in chosen:
        label_text = values[0][1]
        target_iris = sorted({node["iri"] for node, _ in values})
        group = "alias-" + sha_bytes(label_text.casefold().encode())
        for language in LANGS:
            query = (f"Which entity has the exact label ‘{label_text}’?" if language == "en"
                     else f"Hvilken enhet har den nøyaktige etiketten «{label_text}»?")
            label_witnesses = []
            for iri in target_iris:
                label_witnesses.extend([[line] for line in nq_lines
                                        if line.startswith(f"<{iri}> <{LABEL}> ") and label_text in line])
            add_question(questions, references, group=group, language=language, family="ambiguous_alias",
                         role="entity", query=query, traversal={"kind": "label", "text": label_text},
                         positives=target_iris, witnesses=[tuple() for _ in ()], status="ambiguous")
            references[-1]["witnesses"] = [{"source_quads": path} for path in label_witnesses]
    # No-match means no P137 operator statement in this bounded graph, not real-world absence.
    operator = "http://www.wikidata.org/prop/direct/P137"
    p137_subjects = {edge["subject_id"] for edge in edges if edge["predicate"] == operator}
    no_match_nodes = [node for node in nodes if node["id"] not in p137_subjects
                      and all(label(node, language) for language in LANGS)]
    for node in sorted(no_match_nodes, key=lambda item: sha_bytes(item["iri"].encode()))[:4]:
        group = "nomatch-" + sha_bytes(node["iri"].encode())
        for language in LANGS:
            name = label(node, language)
            query = (f"Who operates {name}?" if language == "en"
                     else f"Hvem driver {name}?")
            add_question(questions, references, group=group, language=language, family="unsupported_no_match",
                         role="entity", query=query,
                         traversal={"kind": "path", "start_iri": node["iri"],
                                    "steps": [{"predicate": operator, "direction": "forward"}]},
                         positives=[], witnesses=[], status="no_match")
    # Guarantee both ambiguity and unsupported examples in the frozen test set.
    for status, prefix in (("ambiguous", "alias-"), ("no_match", "nomatch-")):
        status_groups = sorted({question["query_group"] for question, reference in zip(questions, references)
                                if reference["status"] == status})
        for index, group in enumerate(status_groups):
            assigned = "train" if index == 0 else "validation" if index == 1 else "test"
            for question, reference in zip(questions, references):
                if question["query_group"] == group:
                    question["split"] = reference["split"] = assigned
    # The cross-graph example is a real GEMET label and remains an excluded scope control.
    gemet_lines = (ROOT / "data/gemet/snapshot.nq").read_text().splitlines()
    scope_line = next(line for line in gemet_lines if "/gemet/concept/" in line and GEMET_LABEL in line)
    scope_iri = scope_line.split(" ", 1)[0][1:-1]
    scope_graph = scope_line.rsplit("<", 1)[-1].split(">", 1)[0]
    for reference in references:
        reference["hard_negatives"].append({"graph": scope_graph, "iri": scope_iri,
            "kind": "out-of-scope-graph", "source_quads": [scope_line],
            "note": "Real source-backed candidate from another retained graph; excluded from this experiment's scope."})
    groups = defaultdict(set)
    for question, reference in zip(questions, references):
        groups[question["query_group"]].add(question["split"])
    if any(len(splits) != 1 for splits in groups.values()):
        raise ValueError("Question-family variants crossed a split")
    if len({question["id"] for question in questions}) != len(questions):
        raise ValueError("Duplicate question ID")
    split_edge_ids = {split: set() for split in ("train", "validation", "test")}
    for question, reference in zip(questions, references):
        for witness in reference["witnesses"]:
            for statement in witness["source_quads"]:
                if statement in {nquad(edge) for edge in edges}:
                    matching = next(edge for edge in edges if nquad(edge) == statement)
                    split_edge_ids[question["split"]].add(edge_key(matching))
    if split_edge_ids["train"] & split_edge_ids["validation"] or \
       split_edge_ids["train"] & split_edge_ids["test"] or \
       split_edge_ids["validation"] & split_edge_ids["test"]:
        raise ValueError("A source edge crosses query splits")
    all_ids = {edge_key(edge) for edge in edges}
    held_out = split_edge_ids["validation"] | split_edge_ids["test"]
    node_iri_to_id = {node["iri"]: node_id for node_id, node in node_by_id.items()}
    unseen_nodes = {item["iri"] for reference in references if reference["status"] == "relevant"
                    and reference["role"] == "entity" for item in reference["relevant"]
                    if int(sha_bytes(("unseen-117\0" + item["iri"]).encode())[:8], 16) % 10 < 2}
    refs_by_id = {reference["id"]: reference for reference in references}
    touched_by_group = defaultdict(set)
    for question in questions:
        traversal = question["traversal"]
        touched = set()
        touched.add(traversal.get("start_iri", ""))
        touched.update((traversal.get("subject_iri", ""), traversal.get("object_iri", "")))
        touched.update(item["iri"] for item in refs_by_id[question["id"]]["relevant"]
                       if item["graph"] == GRAPH and item["iri"] in node_iri_to_id)
        touched_by_group[question["query_group"]].update(touched & unseen_nodes)
    unseen_groups = {group for group, touched in touched_by_group.items() if touched}
    unseen_test_ids = sorted(question["id"] for question in questions
        if question["query_group"] in unseen_groups
        and refs_by_id[question["id"]]["status"] == "relevant"
        and refs_by_id[question["id"]]["role"] == "entity"
        and any(item["iri"] in unseen_nodes for item in refs_by_id[question["id"]]["relevant"]))
    unseen_train_ids = sorted(question["id"] for question in questions
        if question["split"] == "train" and question["query_group"] not in unseen_groups
        and refs_by_id[question["id"]]["status"] == "relevant")
    unseen_validation_ids = sorted(question["id"] for question in questions
        if question["split"] == "validation" and question["query_group"] not in unseen_groups
        and refs_by_id[question["id"]]["status"] == "relevant")
    unseen_validation_edge_ids = {edge_key(edge) for edge in edges if any(
        statement == nquad(edge) for qid in unseen_validation_ids
        for witness in refs_by_id[qid]["witnesses"] for statement in witness["source_quads"])}
    unseen_test_edge_ids = {edge_key(edge) for edge in edges if any(
        statement == nquad(edge) for qid in unseen_test_ids
        for witness in refs_by_id[qid]["witnesses"] for statement in witness["source_quads"])}
    unseen_incident_edge_ids = {edge_key(edge) for edge in edges
                                if edge["subject_iri"] in unseen_nodes or edge["object_iri"] in unseen_nodes}
    unseen_edge_ids = unseen_validation_edge_ids | unseen_test_edge_ids | unseen_incident_edge_ids
    split_manifest = {
        "version": "wikidata-relational-splits-v1", "seed": 117,
        "assignment": "sha256('117\\0'+query_group) modulo 100; train <70, validation <85, else test",
        "query_groups": {split: sorted(group for group, values in groups.items() if split in values)
                         for split in ("train", "validation", "test")},
        "witness_edge_ids": {split: sorted(values) for split, values in split_edge_ids.items()},
        "message_passing_train_edge_ids": sorted(all_ids - held_out),
        "held_out_edge_ids_excluded_from_message_passing": sorted(held_out),
        "transductive": True,
        "unseen_entity_generalization": {
            "unseen_entity_iris": sorted(unseen_nodes),
            "train_query_ids": unseen_train_ids,
            "validation_query_ids": unseen_validation_ids,
            "test_query_ids": unseen_test_ids,
            "message_passing_edge_ids": sorted(all_ids - unseen_edge_ids),
            "excluded_incident_edge_ids": sorted(unseen_incident_edge_ids),
            "excluded_validation_edge_ids": sorted(unseen_validation_edge_ids),
            "excluded_test_edge_ids": sorted(unseen_test_edge_ids),
            "policy": "Node-disjoint target holdout; remove every edge incident to held-out entity IDs from encoder inputs and exclude every touching query group from supervised train/validation.",
        },
    }
    return questions, references, split_manifest


def path_candidates(export: Path, edges: list[dict], questions: list[dict], maximum_hops: int) -> dict[str, list[dict]]:
    outgoing, incoming = defaultdict(list), defaultdict(list)
    nodes = read_jsonl(export / "nodes.jsonl")
    snapshot_lines = (export / "snapshot.nq").read_text().splitlines()
    for edge in edges:
        outgoing[(edge["subject_iri"], edge["predicate"])].append(edge)
        incoming[(edge["object_iri"], edge["predicate"])].append(edge)
    captures = {}
    for question in questions:
        traversal = question["traversal"]
        matches = []
        if traversal["kind"] == "path":
            current = [(traversal["start_iri"], [])]
            for step in traversal["steps"][:maximum_hops]:
                following = []
                index = outgoing if step["direction"] == "forward" else incoming
                for node, witness_path in current:
                    for edge in index[(node, step["predicate"] )]:
                        next_node = edge["object_iri"] if step["direction"] == "forward" else edge["subject_iri"]
                        following.append((next_node, witness_path + [edge]))
                current = following
            matches = [{"graph": GRAPH, "iri": node, "source_quads": [nquad(edge) for edge in witness]}
                       for node, witness in current]
        elif traversal["kind"] == "endpoints":
            for edge in edges:
                if edge["subject_iri"] == traversal["subject_iri"] and edge["object_iri"] == traversal["object_iri"]:
                    matches.append({"graph": GRAPH, "iri": edge["predicate"], "source_quads": [nquad(edge)]})
        elif traversal["kind"] == "label":
            needle = traversal["text"].casefold()
            for node in nodes:
                if any(needle == value.casefold() for values in node["labels"].values() for value in values):
                    label_lines = [line for line in snapshot_lines
                                   if line.startswith(f"<{node['iri']}> <{LABEL}> ") and traversal["text"] in line]
                    matches.append({"graph": GRAPH, "iri": node["iri"], "source_quads": label_lines})
        unique = {}
        for candidate in matches:
            key = (candidate["graph"], candidate["iri"])
            previous = unique.get(key)
            if previous is None or len(candidate["source_quads"]) < len(previous["source_quads"]):
                unique[key] = candidate
        captures[question["id"]] = [unique[key] for key in sorted(unique)]
    return captures


def exact_path_metrics(ranked: list[tuple[str, str]], reference: dict,
                       path_candidates: list[dict]) -> dict:
    """Score ranked answers only when a matching source-witnessed path is attached."""
    relevant_paths = set()
    for witness in reference["witnesses"]:
        graph = reference["relevant"][0]["graph"]
        relevant_paths.add((graph, sha_bytes("\n".join(sorted(witness["source_quads"])).encode())))
    paths_by_entity = defaultdict(list)
    for candidate in path_candidates:
        key = (candidate["graph"], sha_bytes("\n".join(sorted(candidate["source_quads"])).encode()))
        paths_by_entity[(candidate["graph"], candidate["iri"])].append(key)
    ranked_paths, seen = [], set()
    for entity in ranked:
        for path in paths_by_entity.get(entity, []):
            if path not in seen:
                ranked_paths.append(path)
                seen.add(path)
    return v1.rank_metrics(relevant_paths, ranked_paths)


def capture_adjacency(export: Path, questions_path: Path, out: Path) -> dict:
    if out.exists():
        raise ValueError("Capture output exists; choose a fresh path")
    questions = json.loads(questions_path.read_text())
    edges = read_jsonl(export / "edges.jsonl")
    out.mkdir(parents=True)
    files = {}
    for name, hops in (("one-hop.jsonl", 1), ("two-hop.jsonl", 2)):
        rows = path_candidates(export, edges, questions, hops)
        (out / name).write_text("".join(json.dumps({"id": key, "candidates": value}, ensure_ascii=False) + "\n"
                                             for key, value in sorted(rows.items())))
        files[name] = sha(out / name)
    receipt = {"version": "wikidata-relational-adjacency-capture-v1",
               "questions_sha256": sha(questions_path), "export_manifest_sha256": sha(export / "manifest.json"),
               "scope": [GRAPH], "references_opened": False, "model_inference": False,
               "candidate_generation": "Exact source/predicate structure carried as task metadata; outputs remain graph-witnessed. This is an oracle navigation baseline, not a natural-language parser.",
               "files": files}
    (out / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def capture_embedding(export: Path, questions_path: Path, feature_file: Path,
                      feature_manifest_path: Path, out: Path) -> dict:
    if out.exists():
        raise ValueError("Capture output exists; choose a fresh path")
    feature_manifest = json.loads(feature_manifest_path.read_text())
    if feature_manifest["feature_file_sha256"] != sha(feature_file):
        raise ValueError("Embedding features do not match their manifest")
    questions = json.loads(questions_path.read_text())
    with __import__("numpy").load(feature_file, allow_pickle=False) as archive:
        entity_features = archive["node_features"]
        relation_features = archive["relation_features"]
        query_features = archive["query_features"]
        query_ids = archive["query_ids"].tolist()
    if query_ids != [row["id"] for row in questions]:
        raise ValueError("Embedding query vectors are not aligned to frozen questions")
    entities, relations = read_jsonl(export / "nodes.jsonl"), read_jsonl(export / "relations.jsonl")
    out.mkdir(parents=True)
    rows = []
    for i, question in enumerate(questions):
        matrix, candidates = (entity_features, entities) if question["role"] == "entity" else (relation_features, relations)
        scores = matrix @ query_features[i]
        order = sorted(range(len(candidates)), key=lambda j: (-float(scores[j]), candidates[j]["iri"]))[:50]
        rows.append({"id": question["id"], "hits": [
            {"graph": GRAPH, "iri": candidates[j]["iri"], "score": float(scores[j]), "exact": False}
            for j in order]})
    (out / "embedding-ranks.jsonl").write_text("".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    receipt = {"version": "wikidata-relational-embedding-capture-v1",
               "questions_sha256": sha(questions_path), "feature_manifest_sha256": sha(feature_manifest_path),
               "feature_file_sha256": sha(feature_file), "export_manifest_sha256": sha(export / "manifest.json"),
               "references_opened": False, "model_inference": False,
               "model": feature_manifest["model"], "revision": feature_manifest["revision"],
               "candidates": len(entities), "predicates": len(relations),
               "files_sha256": {"embedding-ranks.jsonl": sha(out / "embedding-ranks.jsonl")}}
    (out / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def write_score_receipt(export: Path, questions_path: Path, references_path: Path,
                        native_capture: Path, adjacency_capture: Path,
                        embedding_capture: Path | None, out: Path) -> dict:
    receipt = {"version": "wikidata-relational-score-inputs-v1",
               "inputs_sha256": {"questions": sha(questions_path), "references": sha(references_path),
                                 "splits": sha(questions_path.parent / "splits.json"),
                                 "export_manifest": sha(export / "manifest.json"),
                                 "snapshot": sha(export / "snapshot.nq"),
                                 "native_capture": sha(native_capture / "checksums.json"),
                                 "adjacency_capture": sha(adjacency_capture / "capture.json"),
                                 "embedding_capture": (sha(embedding_capture / "capture.json")
                                                       if embedding_capture else None),
                                 "scorer": sha(Path(__file__))},
               "references_opened_after_retrieval_capture": True,
               "outputs_sha256": {"cases.jsonl": sha(out / "cases.jsonl"),
                                  "summary.json": sha(out / "summary.json")}}
    (out / "score-inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
    checksums = {str(path.relative_to(out)): sha(path) for path in sorted(out.rglob("*"))
                 if path.is_file() and path.name != "checksums.json"}
    (out / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    return receipt


def score_all(export: Path, questions_path: Path, references_path: Path,
              native_capture: Path, adjacency_capture: Path, out: Path,
              embedding_capture: Path | None = None) -> dict:
    if out.exists():
        raise ValueError("Score output exists; choose a fresh path")
    questions = json.loads(questions_path.read_text())
    references = json.loads(references_path.read_text())
    refs = {item["id"]: item for item in references}
    question_ids = {item["id"] for item in questions}
    if set(refs) != question_ids or len(refs) != len(references):
        raise ValueError("Question and reference IDs differ or duplicate")
    if any(item["review_status"] != "AI_reference_only" for item in references):
        raise ValueError("Reference provenance is missing")
    native_checksums = json.loads((native_capture / "checksums.json").read_text())
    if native_checksums != v1.inventory(native_capture):
        raise ValueError("Native baseline capture changed after retrieval")
    native_receipt = json.loads((native_capture / "capture.json").read_text())
    if native_receipt["questions_sha256"] != sha(questions_path) or native_receipt["references_opened"]:
        raise ValueError("Native capture is not bound to the frozen question-only run")
    adjacency_receipt = json.loads((adjacency_capture / "capture.json").read_text())
    if adjacency_receipt["questions_sha256"] != sha(questions_path) or adjacency_receipt["references_opened"]:
        raise ValueError("Adjacency capture is not bound to the frozen question-only run")
    native = {"bm25": {row["id"]: row["hits"] for row in
                        (json.loads(line) for line in (native_capture / "bm25-ranks.jsonl").read_text().splitlines())}}
    packets = {row["id"]: row["packet"] for row in
               (json.loads(line) for line in (native_capture / "neighborhood-packets.jsonl").read_text().splitlines())}
    for row in questions:
        packet = json.loads((native_capture / packets[row["id"]]).read_text())
        native.setdefault("neighborhood_1hop", {})[row["id"]] = packet[
            {"entity": "entities", "predicate": "predicates", "class": "classes"}[row["role"]]]["candidates"]
    adjacency = {}
    for method, filename in (("adjacency_1hop_oracle", "one-hop.jsonl"),
                             ("adjacency_2hop_oracle", "two-hop.jsonl")):
        adjacency[method] = {row["id"]: row["candidates"] for row in
                             (json.loads(line) for line in (adjacency_capture / filename).read_text().splitlines())}
    if embedding_capture:
        embedding_receipt = json.loads((embedding_capture / "capture.json").read_text())
        if embedding_receipt["questions_sha256"] != sha(questions_path) or embedding_receipt["references_opened"]:
            raise ValueError("Embedding capture is not bound to the frozen question-only run")
        if embedding_receipt["files_sha256"]["embedding-ranks.jsonl"] != sha(embedding_capture / "embedding-ranks.jsonl"):
            raise ValueError("Embedding ranks changed after capture")
        native["embeddinggemma"] = {row["id"]: row["hits"] for row in
            (json.loads(line) for line in (embedding_capture / "embedding-ranks.jsonl").read_text().splitlines())}
    native_scope = json.loads((export / "scope.json").read_text())
    source_lines = set((export / "snapshot.nq").read_text().splitlines())
    gemet_lines = set((ROOT / "data/gemet/snapshot.nq").read_text().splitlines())
    for reference in references:
        for negative in reference["hard_negatives"]:
            if negative["kind"] == "out-of-scope-graph" and any(
                    line not in gemet_lines for line in negative["source_quads"]):
                raise ValueError("Out-of-scope hard-negative source changed")
    oracle_onehop = {row["id"]: row["candidates"] for row in
                     (json.loads(line) for line in (adjacency_capture / "one-hop.jsonl").read_text().splitlines())}
    oracle_twohop = {row["id"]: row["candidates"] for row in
                     (json.loads(line) for line in (adjacency_capture / "two-hop.jsonl").read_text().splitlines())}
    corpus = {key: str((export / name).resolve()) for key, name in
              (("rdf", "snapshot.nq"), ("policy", "policy.json"),
               ("scope", "scope.json"), ("config", "discovery.json"))}
    import question_vocabulary as qv
    rows, summaries = [], {}
    for method, result in {**native, **adjacency}.items():
        method_rows = []
        for question in questions:
            ref = refs[question["id"]]
            candidates = result[question["id"]]
            if method == "neighborhood_1hop":
                packet = json.loads((native_capture / packets[question["id"]]).read_text())
                qv.source_audit(packet, corpus, {"required": []})
            ranked = [(candidate["graph"], candidate["iri"]) for candidate in candidates]
            if len(ranked) != len(set(ranked)):
                raise ValueError(f"Duplicate graph-qualified candidate for {question['id']} ({method})")
            if any(graph not in native_scope for graph, _ in ranked):
                raise ValueError(f"Out-of-scope candidate returned for {question['id']} ({method})")
            witness_count = 0
            for candidate in candidates:
                for statement in candidate.get("source_quads", []):
                    if statement not in source_lines:
                        raise ValueError("Adjacency candidate witness is absent from the frozen RDF snapshot")
                    witness_count += 1
                witness_count += sum(len(page.get("evidence", [])) for page in candidate.get("usage", []))
            for witness in ref["witnesses"]:
                if any(statement not in source_lines for statement in witness["source_quads"]
                       if statement.startswith("<http://www.wikidata.org/")):
                    raise ValueError("Positive witness missing from its source graph")
            relevant = {(item["graph"], item["iri"]) for item in ref["relevant"]}
            metrics = v1.rank_metrics(relevant, ranked)
            path_metrics = (exact_path_metrics(ranked, ref, oracle_twohop[question["id"]])
                            if question["family"] == "two_hop_path" and ref["status"] == "relevant"
                            else None)
            oracle_supported = {(candidate["graph"], candidate["iri"])
                                for candidate in oracle_onehop[question["id"]] + oracle_twohop[question["id"]]}
            supported_top10 = len(set(ranked[:10]) & oracle_supported)
            method_rows.append({"id": question["id"], "split": question["split"],
                                "query_group": question["query_group"],
                                "language": question["language"], "family": question["family"],
                                "status": ref["status"], "relevant": sorted([list(x) for x in relevant]),
                                "ranked": [list(x) for x in ranked], "metrics": metrics,
                                "source_path_metrics": path_metrics,
                                "candidate_recall": (len(set(ranked) & relevant) / len(relevant) if relevant else None),
                                "source_witness_count": witness_count,
                                "top10_source_witness_coverage": supported_top10 / min(10, len(ranked))
                                    if ranked else 0.0,
                                "no_match_suggestion": ref["status"] == "no_match" and bool(ranked),
                                "exact_graph_iri_preserved": all(graph == GRAPH and iri for graph, iri in ranked)})
        rows.extend({"method": method, **row} for row in method_rows)
        test_relevant = [row for row in method_rows if row["split"] == "test" and row["status"] == "relevant"]
        summary = {"test_relevant_n": len(test_relevant), "test_no_match_n": sum(
            row["split"] == "test" and row["status"] == "no_match" for row in method_rows),
            "test_ambiguous_n": sum(row["split"] == "test" and row["status"] == "ambiguous" for row in method_rows)}
        metric_names = ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10")
        def metric_summary(group):
            return {"n": len(group), **{metric: (sum(row["metrics"][metric] for row in group) / len(group)
                                                 if group else None) for metric in metric_names}}
        summary["metrics"] = metric_summary(test_relevant)
        summary["strata"] = {}
        for language in LANGS:
            summary["strata"][f"language/{language}"] = metric_summary(
                [row for row in test_relevant if row["language"] == language])
        for family in sorted({row["family"] for row in test_relevant}):
            summary["strata"][f"family/{family}"] = metric_summary(
                [row for row in test_relevant if row["family"] == family])
        summary["test_no_match_suggestions"] = sum(row["no_match_suggestion"] for row in method_rows
                                                    if row["split"] == "test")
        summary["test_top10_source_witness_coverage_mean"] = (
            sum(row["top10_source_witness_coverage"] for row in method_rows
                if row["split"] == "test") / sum(row["split"] == "test" for row in method_rows)
            if any(row["split"] == "test" for row in method_rows) else None)
        path_rows = [row["source_path_metrics"] for row in method_rows
                     if row["split"] == "test" and row["source_path_metrics"] is not None]
        summary["two_hop_source_path_metrics"] = {
            "n": len(path_rows), **{metric: (sum(row[metric] for row in path_rows) / len(path_rows)
                                               if path_rows else None) for metric in metric_names}}
        summary["all_candidates_preserve_authorized_graph_and_iri"] = all(
            row["exact_graph_iri_preserved"] for row in method_rows)
        summaries[method] = summary
    out.mkdir(parents=True)
    (out / "cases.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    summary = {"version": "wikidata-relational-baseline-score-v2", "test_split_only": True,
               "reference_status": "Agent-authored source-checked development evidence; not expert gold.",
               "methods": summaries,
               "scope_note": "Oracle adjacency receives structured anchor/predicate annotations; native BM25 and QV receive only question text. Do not treat oracle lift as a matched NLP comparison.",
               "EmbeddingGemma": ("Matched feature-vector capture completed; see method metrics." if embedding_capture else
                                   "No compatible Wikidata vectors are retained. The existing issue-50 vectors are GEMET-only; no inference or weights were run."),
               "source_witness_note": "Adjacency returns exact statement/path witnesses. BM25/QV candidate outputs are not themselves statement evidence; the metric indicates whether returned candidates carry a traversal witness in the adjacency capture."}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    write_score_receipt(export, questions_path, references_path, native_capture,
                        adjacency_capture, embedding_capture, out)
    return summary


def write_benchmark(out: Path) -> dict:
    questions, references, splits = make_cases()
    if out.exists():
        raise ValueError("Benchmark output exists; choose a fresh path")
    out.mkdir(parents=True)
    (out / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n")
    (out / "references.json").write_text(json.dumps(references, ensure_ascii=False, indent=2) + "\n")
    (out / "splits.json").write_text(json.dumps(splits, ensure_ascii=False, indent=2) + "\n")
    audit = audit_graph()
    audit.update({"benchmark_version": "wikidata-relational-v1",
                  "questions_sha256": sha(out / "questions.json"),
                  "references_sha256": sha(out / "references.json"),
                  "splits_sha256": sha(out / "splits.json"),
                  "query_counts": dict(sorted(Counter(q["family"] for q in questions).items())),
                  "split_counts": dict(sorted(Counter(q["split"] for q in questions).items())),
                  "language_counts": dict(sorted(Counter(q["language"] for q in questions).items())),
                  "source_reference_provenance": "Agent-authored templates, positive IDs and witnesses verified against original Wikidata response export; no independent human review.",
                  "feature_scope": "Wikidata only; no cross-graph labels or triples enter export/features.",
                  "hard_negative_policy": "Source-backed contrastive candidates are labeled as direction/predicate distractors, not known-false RDF claims; no-match is graph-bounded.",
                  "split_policy": "Question-language/template variants are grouped by source edge/path/alias before hashing; validation/test witness edges are excluded from message-passing edge IDs."})
    (out / "dataset-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    inventory = {name: sha(out / name) for name in ("questions.json", "references.json", "splits.json", "dataset-audit.json")}
    manifest = {"version": "rgcn-compgcn-v2-data-freeze", "dataset": str(EXPORT.relative_to(ROOT)),
                "dataset_manifest_sha256": sha(EXPORT / "manifest.json"),
                "snapshot_sha256": sha(EXPORT / "snapshot.nq"), "files_sha256": inventory,
                "counts": {"questions": len(questions), "groups": len(splits["query_groups"]["train"])
                    + len(splits["query_groups"]["validation"]) + len(splits["query_groups"]["test"]),
                    "splits": dict(sorted(Counter(q["split"] for q in questions).items()))},
                "frozen_before_baseline_capture": True}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Write the v2 bilingual source-checked benchmark and splits")
    build.add_argument("--out", type=Path, default=OUT)
    capture = sub.add_parser("capture-native", help="Capture existing BM25 and Graph Verity QV2 methods")
    capture.add_argument("--questions", type=Path, required=True)
    capture.add_argument("--out", type=Path, required=True)
    capture.add_argument("--bm25-session", type=Path, required=True)
    capture.add_argument("--neighborhood-session", type=Path, required=True)
    capture.add_argument("--export", type=Path, default=EXPORT)
    adjacency = sub.add_parser("capture-adjacency", help="Capture typed adjacency with source witnesses")
    adjacency.add_argument("--questions", type=Path, required=True)
    adjacency.add_argument("--out", type=Path, required=True)
    adjacency.add_argument("--export", type=Path, default=EXPORT)
    embedding = sub.add_parser("capture-embedding", help="Rank frozen feature vectors without references")
    embedding.add_argument("--questions", type=Path, required=True)
    embedding.add_argument("--features", type=Path, required=True)
    embedding.add_argument("--feature-manifest", type=Path, required=True)
    embedding.add_argument("--out", type=Path, required=True)
    embedding.add_argument("--export", type=Path, default=EXPORT)
    score = sub.add_parser("score", help="Score all captured methods after candidate capture")
    score.add_argument("--questions", type=Path, required=True)
    score.add_argument("--references", type=Path, required=True)
    score.add_argument("--native-capture", type=Path, required=True)
    score.add_argument("--adjacency-capture", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True)
    score.add_argument("--export", type=Path, default=EXPORT)
    score.add_argument("--embedding-capture", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = write_benchmark(args.out)
    elif args.command == "capture-native":
        result = v1.capture_baselines(args.export, args.questions, args.out,
                                      args.bm25_session, args.neighborhood_session)
    elif args.command == "capture-adjacency":
        result = capture_adjacency(args.export, args.questions, args.out)
    elif args.command == "capture-embedding":
        result = capture_embedding(args.export, args.questions, args.features,
                                   args.feature_manifest, args.out)
    else:
        result = score_all(args.export, args.questions, args.references,
                           args.native_capture, args.adjacency_capture, args.out, args.embedding_capture)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
