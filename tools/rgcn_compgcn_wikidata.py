"""Rebuild the retained, bounded Wikidata RDF slice without network access."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import tempfile

from rdflib import Literal, URIRef

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/rgcn-compgcn-v1/wikidata-norway-org-v1"
GRAPH = "urn:graph-verity:wikidata:norway-org-v1"
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
LANGUAGES = {"en", "no", "nb", "nn"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["results"]["bindings"]


def query_files() -> dict[str, str]:
    selection_query = ("PREFIX bd: <http://www.bigdata.com/rdf#>\n"
        "PREFIX wd: <http://www.wikidata.org/entity/>\n"
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n\n"
        "SELECT ?item ?itemLabel WHERE {\n  ?item wdt:P17 wd:Q20 ;\n"
        "        wdt:P31 wd:Q43229 .\n  SERVICE wikibase:label {\n"
        "    bd:serviceParam wikibase:language \"no,en\" .\n  }\n}\n"
        "ORDER BY ?item\nLIMIT 1000\n")
    roots = sorted({row["item"]["value"] for row in rows(SOURCE / "entity-selection-response.json")})
    edges = rows(SOURCE / "direct-claim-edge-response.json")
    resources = {row["subject"]["value"] for row in edges} | {row["object"]["value"] for row in edges}
    properties = {"http://www.wikidata.org/entity/" + row["predicate"]["value"].rsplit("/", 1)[-1]
                  for row in edges}
    values = lambda items: "\n".join(f"    <{iri}>" for iri in sorted(items))
    entity_ids = "\n".join(roots) + "\n"
    edge_query = ("PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n\n"
        "SELECT DISTINCT ?subject ?predicate ?object WHERE {\n  VALUES ?subject {\n" + values(roots) +
        "\n  }\n  ?subject ?predicate ?object .\n"
        "  FILTER(STRSTARTS(STR(?predicate), STR(wdt:)) &&\n"
        "    STRSTARTS(STR(?object), \"http://www.wikidata.org/entity/Q\"))\n}\n")
    label_query = ("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\n"
        "SELECT DISTINCT ?resource ?label WHERE {\n  VALUES ?resource {\n" +
        values(resources | properties) + "\n  }\n  ?resource rdfs:label ?label .\n"
        "  FILTER(LANG(?label) IN (\"en\", \"no\", \"nb\", \"nn\"))\n}\n")
    return {"entity-selection.rq": selection_query, "entity-ids.txt": entity_ids,
            "direct-claim-edges.rq": edge_query,
            "node-and-predicate-labels.rq": label_query}


def verify_query_files() -> None:
    for name, expected in query_files().items():
        path = SOURCE / name
        require(path.read_text() == expected, "Generated query input changed: " + name)


def write_query_files() -> None:
    for name, contents in query_files().items():
        (SOURCE / name).write_text(contents)


def source_data() -> tuple[set[str], list[tuple[str, str, str]], dict[str, set[tuple[str, str]]]]:
    verify_query_files()
    roots = {row["item"]["value"] for row in rows(SOURCE / "entity-selection-response.json")}
    edges = sorted({(row["subject"]["value"], row["predicate"]["value"], row["object"]["value"])
                    for row in rows(SOURCE / "direct-claim-edge-response.json")})
    labels: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in rows(SOURCE / "node-and-predicate-label-response.json"):
        lang = row["label"].get("xml:lang", "")
        if lang in LANGUAGES:
            labels[row["resource"]["value"]].add((lang, row["label"]["value"]))
    return roots, edges, labels


def render_nq(triples: set[tuple[str, str, str]]) -> bytes:
    lines = []
    for subject, predicate, obj in triples:
        if predicate == LABEL:
            lang, value = json.loads(obj)
            object_text = Literal(value, lang=lang).n3()
        else:
            object_text = f"<{obj}>"
        lines.append(f"<{subject}> <{predicate}> {object_text} <{GRAPH}> .")
    return ("\n".join(sorted(lines)) + "\n").encode()


def graph_stats(edges: list[tuple[str, str, str]], roots: set[str],
                labels: dict[str, set[tuple[str, str]]]) -> dict:
    nodes = {item for subject, _, obj in edges for item in (subject, obj)}
    predicates = Counter(predicate for _, predicate, _ in edges)
    adjacency: dict[str, set[str]] = defaultdict(set)
    undirected: dict[str, set[str]] = defaultdict(set)
    for subject, _, obj in edges:
        adjacency[subject].add(obj)
        undirected[subject].add(obj)
        undirected[obj].add(subject)
    unseen, components = set(nodes), []
    while unseen:
        start = min(unseen)
        queue, component = deque([start]), set()
        while queue:
            node = queue.popleft()
            if node in component:
                continue
            component.add(node)
            queue.extend(undirected[node] - component)
        unseen -= component
        components.append(len(component))
    two_hop_paths = sum(len(adjacency.get(mid, set())) for mids in adjacency.values() for mid in mids)
    two_hop_pairs = {
        (source, target)
        for source, mids in adjacency.items()
        for mid in mids
        for target in adjacency.get(mid, set())
    }
    return {
        "selected_organization_roots": len(roots),
        "entity_nodes": len(nodes),
        "nodes_with_english_or_norwegian_labels": sum(bool(labels.get(node)) for node in nodes),
        "quads_including_labels": len(edges) + sum(len(values) for iri, values in labels.items()
                                                   if iri in nodes or iri.startswith("http://www.wikidata.org/entity/P")),
        "direct_source_edges": len(edges),
        "predicate_count": len(predicates),
        "predicate_counts": dict(sorted(predicates.items())),
        "weak_components": len(components),
        "largest_weak_component": max(components, default=0),
        "isolated_entity_nodes": sum(not undirected[node] for node in nodes),
        "directed_two_hop_paths": two_hop_paths,
        "directed_two_hop_reachable_pairs": len(two_hop_pairs),
        "english_and_norwegian_label_literals": dict(sorted(Counter(
            lang for node in nodes for lang, _ in labels.get(node, set())).items())),
        "synthetic_or_inferred_edges": 0,
        "source_edges_preserve_direction": True,
    }


def export(out: Path) -> dict:
    if out.exists():
        raise ValueError("Export output already exists; choose a fresh path")
    roots, edges, labels = source_data()
    nodes = sorted({item for subject, _, obj in edges for item in (subject, obj)})
    predicates = sorted({predicate for _, predicate, _ in edges})
    triples = set(edges)
    for resource, values in labels.items():
        for lang, value in values:
            triples.add((resource, LABEL, json.dumps([lang, value], ensure_ascii=False)))
    raw = render_nq(triples)
    view_hash = hashlib.sha256(raw).hexdigest()
    snapshot_id = "sha256:" + hashlib.sha256(b"graph-verity-snapshot-v1\0nquads\0" + raw).hexdigest()
    node_ids = {iri: index for index, iri in enumerate(nodes)}
    relation_ids = {iri: index for index, iri in enumerate(predicates)}
    out.mkdir(parents=True)
    (out / "snapshot.nq").write_bytes(raw)
    (out / "retrieval.nq").write_bytes(raw)
    (out / "nodes.jsonl").write_text("".join(json.dumps({
        "id": node_ids[iri], "graph": GRAPH, "iri": iri, "is_selected_organization": iri in roots,
        "labels": {lang: sorted(texts) for lang, texts in sorted(
            ((lang, {text for seen_lang, text in labels.get(iri, set()) if seen_lang == lang})
             for lang in LANGUAGES)) if texts},
    }, ensure_ascii=False) + "\n" for iri in nodes))
    property_labels = {
        "http://www.wikidata.org/entity/" + iri.rsplit("/", 1)[-1]: labels.get(
            "http://www.wikidata.org/entity/" + iri.rsplit("/", 1)[-1], set())
        for iri in predicates
    }
    relations = []
    for iri in predicates:
        property_iri = "http://www.wikidata.org/entity/" + iri.rsplit("/", 1)[-1]
        relations.append({"id": relation_ids[iri], "iri": iri, "property_iri": property_iri,
                          "labels": {lang: sorted(text for seen_lang, text in property_labels[property_iri]
                                                   if seen_lang == lang)
                                     for lang in sorted(LANGUAGES)
                                     if any(seen_lang == lang for seen_lang, _ in property_labels[property_iri])}})
    (out / "relations.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in relations))
    (out / "edges.jsonl").write_text("".join(json.dumps({
        "graph": GRAPH, "subject_id": node_ids[s], "subject_iri": s,
        "predicate_id": relation_ids[p], "predicate": p,
        "object_id": node_ids[o], "object_iri": o,
    }, ensure_ascii=False) + "\n" for s, p, o in edges))
    stats = graph_stats(edges, roots, labels)
    (out / "scope.json").write_text(json.dumps([GRAPH], indent=2) + "\n")
    (out / "policy.json").write_text(json.dumps({"version": 1, "graphs": [GRAPH], "max_rows": 1000,
        "max_evidence": 10000, "timeout_ms": 10000}, indent=2) + "\n")
    (out / "discovery.json").write_text(json.dumps({"version": 1, "snapshot_id": snapshot_id,
        "graphs": {GRAPH: {"source": "Wikidata structured data, bounded Norway organization export",
          "license": "CC0", "source_revision": "selection:" + sha(SOURCE / "entity-selection-response.json") +
            ";edges:" + sha(SOURCE / "direct-claim-edge-response.json") +
            ";labels:" + sha(SOURCE / "node-and-predicate-label-response.json"),
          "importer_revision": "tools/rgcn_compgcn_wikidata.py sha256:" + sha(Path(__file__))}}}, indent=2) + "\n")
    manifest = {
        "version": "rgcn-compgcn-wikidata-export-v1",
        "source_url": "https://query.wikidata.org/sparql",
        "source_graph": GRAPH,
        "source_graph_name_assigned_by_importer": True,
        "license": "CC0 for Wikidata structured data",
        "queries": {name: sha(SOURCE / name) for name in ["entity-selection.rq", "direct-claim-edges.rq",
            "node-and-predicate-labels.rq"]},
        "responses": {name: sha(SOURCE / name) for name in ["entity-selection-response.json",
            "direct-claim-edge-response.json", "node-and-predicate-label-response.json"]},
        "input_triples_are_original_direct_claims_or_labels": True,
        "preprocessing": "Select the first 1,000 direct P17=Norway, P31=Organization results ordered by IRI; retain all direct claim statements from selected organizations whose objects are Wikidata Q entities and en/no/nb/nn rdfs:label statements. No inverse or inferred edges.",
        "stats": stats,
        "export_sha256": {name: sha(out / name) for name in ["snapshot.nq", "retrieval.nq", "nodes.jsonl",
            "relations.jsonl", "edges.jsonl", "scope.json", "policy.json", "discovery.json"]},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def verify(folder: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="rgcn-wikidata-verify-") as temp:
        fresh = Path(temp) / "export"
        manifest = export(fresh)
        require((folder / "manifest.json").read_bytes() == (fresh / "manifest.json").read_bytes(),
                "Export manifest does not rebuild from retained Wikidata responses")
        for name in manifest["export_sha256"]:
            require(sha(folder / name) == sha(fresh / name), "Export changed or no longer rebuilds: " + name)
        return manifest


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("queries", help="verify frozen query files against retained source responses")
    sub.choices["queries"].add_argument("--write", action="store_true",
        help="regenerate query and entity ID inputs from retained responses")
    build = sub.add_parser("export")
    build.add_argument("--out", required=True, type=Path)
    check = sub.add_parser("verify")
    check.add_argument("--export", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "queries":
        if args.write:
            write_query_files()
            print("Query files rebuilt from retained responses.")
        else:
            verify_query_files()
            print("Query files match the retained response inputs.")
    else:
        print(json.dumps(export(args.out) if args.command == "export" else verify(args.export),
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
