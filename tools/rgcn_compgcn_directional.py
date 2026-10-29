"""Deterministic navigation-only export for the aligned R-GCN experiment.

Reverse rows are derived adjacency records, never RDF assertions. Their
source_quad always points to the original directed Wikidata statement.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile


GRAPH = "urn:graph-verity:wikidata:norway-org-v1"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
LANGS = ("en", "no", "nb", "nn")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                  for row in rows))


def source_edge_id(edge: dict) -> str:
    raw = "\0".join((edge["graph"], edge["subject_iri"], edge["predicate"], edge["object_iri"]))
    return sha_bytes(raw.encode())


def source_quad(edge: dict) -> str:
    return (f"<{edge['subject_iri']}> <{edge['predicate']}> <{edge['object_iri']}> "
            f"<{edge['graph']}> .")


def navigation_text(label: str | None, language: str, direction: str) -> str | None:
    if label is None:
        return None
    if language == "en":
        if direction == "forward":
            return f"RDF navigation: from the subject, follow predicate ‘{label}’ to the object."
        return f"RDF navigation: from the object, traverse the original edge backwards along predicate ‘{label}’ to the subject."
    if language == "no":
        if direction == "forward":
            return f"RDF-navigasjon: fra subjektet, følg egenskapen «{label}» til objektet."
        return f"RDF-navigasjon: fra objektet, følg den opprinnelige kanten baklengs langs egenskapen «{label}» til subjektet."
    raise ValueError(f"Unsupported navigation language: {language}")


def build(export: Path, out: Path) -> dict:
    if out.exists():
        raise ValueError("Output exists; choose a new versioned path")
    source_manifest = json.loads((export / "manifest.json").read_text())
    if source_manifest.get("source_graph") != GRAPH:
        raise ValueError("Unexpected graph scope")
    snapshot = set((export / "snapshot.nq").read_text().splitlines())
    nodes = read_jsonl(export / "nodes.jsonl")
    relations = read_jsonl(export / "relations.jsonl")
    edges = read_jsonl(export / "edges.jsonl")
    if len({row["id"] for row in nodes}) != len(nodes):
        raise ValueError("Duplicate entity ID")
    if len({row["id"] for row in relations}) != len(relations):
        raise ValueError("Duplicate predicate ID")
    labels_by_property = {}
    for row in relations:
        property_iri = row["property_iri"]
        values = []
        for language, labels in sorted(row.get("labels", {}).items()):
            for label in sorted(set(labels)):
                literal = json.dumps(label, ensure_ascii=False)
                quad = f"<{property_iri}> <{RDFS_LABEL}> {literal}@{language} <{GRAPH}> ."
                if quad not in snapshot:
                    raise ValueError(f"Predicate label has no source quad: {property_iri} {language}")
                values.append({"language": language, "text": label, "source_quad": quad,
                               "origin": "source_rdfs_label"})
        labels_by_property[property_iri] = values

    directional_relations = []
    vocabulary = []
    by_predicate = {}
    for relation in sorted(relations, key=lambda row: row["id"]):
        property_iri = relation["property_iri"]
        labels = labels_by_property[property_iri]
        by_language = {}
        for language in LANGS:
            available = [row for row in labels if row["language"] == language]
            if available:
                by_language[language] = available[0]["text"]
        norwegian_label = next((by_language[lang] for lang in ("nb", "nn", "no")
                                if by_language.get(lang)), None)
        vocabulary.append({
            "predicate_id": relation["id"], "predicate_iri": relation["iri"],
            "property_iri": property_iri, "source_graph": GRAPH,
            "source_labels": labels, "aliases": [],
            "alias_status": "absent_from_frozen_export",
            "source_descriptions": [],
            "description_status": "absent_from_frozen_export",
            "navigation_descriptions": [
                {"direction": direction, "language": language,
                 "text": navigation_text(by_language.get(language) if language == "en" else norwegian_label,
                                          language, direction),
                 "label_language": language if language == "en" else next(
                     (lang for lang in ("nb", "nn", "no") if by_language.get(lang)), None),
                 "origin": "generated_navigation_template",
                 "review_status": "unreviewed"}
                for direction in ("forward", "reverse") for language in ("en", "no")],
            "inverse_ontology_axiom": None,
        })
        for direction, offset in (("forward", 0), ("reverse", 1)):
            directional_id = 2 * relation["id"] + offset
            text_en = navigation_text(by_language.get("en"), "en", direction)
            text_no = navigation_text(norwegian_label, "no", direction)
            directional_relations.append({
                "relation_id": directional_id, "predicate_id": relation["id"],
                "predicate_iri": relation["iri"], "source_graph": GRAPH,
                "direction": direction, "asserted_predicate_iri": relation["iri"],
                "description_texts": {"en": text_en, "no": text_no},
                "description_origin": "generated_navigation_template",
                "review_status": "unreviewed"})
        by_predicate[relation["iri"]] = relation["id"]

    node_ids = {row["iri"]: row["id"] for row in nodes}
    directional_edges = []
    for edge in sorted(edges, key=source_edge_id):
        sid = source_edge_id(edge)
        quad = source_quad(edge)
        if quad not in snapshot:
            raise ValueError(f"Export edge lacks its original RDF source quad: {sid}")
        predicate_id = by_predicate[edge["predicate"]]
        for direction, offset in (("forward", 0), ("reverse", 1)):
            reverse = direction == "reverse"
            subject_id, object_id = ((edge["object_id"], edge["subject_id"]) if reverse else
                                     (edge["subject_id"], edge["object_id"]))
            row = {"edge_id": sha_bytes(f"{sid}\0{direction}".encode()),
                   "source_edge_id": sid, "graph": edge["graph"],
                   "subject_id": subject_id, "subject_iri": (edge["object_iri"] if reverse else edge["subject_iri"]),
                   "object_id": object_id, "object_iri": (edge["subject_iri"] if reverse else edge["object_iri"]),
                   "relation_id": 2 * predicate_id + offset, "predicate_id": predicate_id,
                   "predicate_iri": edge["predicate"], "direction": direction,
                   "asserted_rdf_fact": not reverse, "source_quad": quad,
                   "derived_from_source_quad": quad if reverse else None}
            directional_edges.append(row)

    out.mkdir(parents=True)
    write_jsonl(out / "predicate-vocabulary.jsonl", vocabulary)
    write_jsonl(out / "directional-relations.jsonl", directional_relations)
    write_jsonl(out / "directional-edges.jsonl", directional_edges)
    predicate_counts = Counter(edge["predicate"] for edge in edges)
    stats = {"entities": len(nodes), "original_edges": len(edges),
             "directional_navigation_edges": len(directional_edges),
             "predicates": len(relations), "directional_relation_ids": len(directional_relations),
             "derived_reverse_edges": sum(row["direction"] == "reverse" for row in directional_edges),
             "predicate_edge_counts": {iri: predicate_counts[iri] for iri in sorted(by_predicate)},
             "top_five_predicate_edge_share": (sum(count for _, count in predicate_counts.most_common(5)) /
                                                len(edges) if edges else 0.0),
             "source_label_predicate_coverage": {
                 "en": sum(bool(labels_by_property[row["property_iri"]] and any(
                     label["language"] == "en" for label in labels_by_property[row["property_iri"]]))
                           for row in relations),
                 "norwegian_nb_nn_no": sum(any(label["language"] in {"nb", "nn", "no"}
                     for label in labels_by_property[row["property_iri"]]) for row in relations)},
             "source_alias_predicates": 0, "source_definition_predicates": 0}
    files = {name: sha_file(out / name) for name in
             ("predicate-vocabulary.jsonl", "directional-relations.jsonl", "directional-edges.jsonl")}
    manifest = {"version": "rgcn-compgcn-directional-navigation-v1",
                "graph": GRAPH, "license": source_manifest.get("license"),
                "source_export_manifest_sha256": sha_file(export / "manifest.json"),
                "source_snapshot_sha256": sha_file(export / "snapshot.nq"),
                "source_edges_sha256": sha_file(export / "edges.jsonl"),
                "source_relations_sha256": sha_file(export / "relations.jsonl"),
                "navigation_policy": "Keep each original directed RDF edge and add one reverse-only navigation edge with a distinct relation ID. Reverse edges point to the original source quad and are not RDF assertions or owl:inverseOf axioms.",
                "description_policy": "Source labels and label quads are retained. The frozen source export contains no aliases or definitions; generated bilingual navigation templates are explicitly unreviewed.",
                "stats": stats, "files_sha256": files}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def verify(export: Path, folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    for name, digest in manifest["files_sha256"].items():
        if sha_file(folder / name) != digest:
            raise ValueError(f"Directional export hash mismatch: {name}")
    with tempfile.TemporaryDirectory(prefix="rgcn-directional-verify-") as temp:
        rebuilt = Path(temp) / "export"
        fresh = build(export, rebuilt)
        if fresh != manifest:
            raise ValueError("Directional export manifest does not rebuild deterministically")
        for name in manifest["files_sha256"]:
            if sha_file(rebuilt / name) != sha_file(folder / name):
                raise ValueError(f"Directional export differs from clean rebuild: {name}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    build_parser = subs.add_parser("build")
    build_parser.add_argument("--export", type=Path, required=True)
    build_parser.add_argument("--out", type=Path, required=True)
    verify_parser = subs.add_parser("verify")
    verify_parser.add_argument("--export", type=Path, required=True)
    verify_parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.export, args.out) if args.command == "build" else verify(args.export, args.directory)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
