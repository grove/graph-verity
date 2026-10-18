#!/usr/bin/env python3
"""Model-free #73 freeze, question-only retrieval, independent source audit and replay."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/question-vocabulary-v1/protocol.json"
COLLECTIONS = {"entity": "entities", "predicate": "predicates", "class": "classes"}
KS = (1, 5, 10, 20)


def read(path):
    return json.loads(Path(path).read_bytes())


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob("*"))
            if p.is_file() and p.name != "checksums.json"}


def cli(binary, *args):
    return subprocess.check_output([str(binary), *map(str, args)], cwd=ROOT, timeout=60)


def inputs(protocol_path, cfg):
    paths = [protocol_path, ROOT / cfg["questions"], ROOT / cfg["references"],
             ROOT / "tools/question_vocabulary.py", ROOT / "schemas/question-vocabulary-packet-v1.json",
             ROOT / "Cargo.lock", ROOT / "rust-toolchain.toml"]
    paths += sorted((ROOT / "crates").rglob("*.rs"))
    for corpus in cfg["corpora"].values():
        paths += [ROOT / corpus[k] for k in ["rdf", "policy", "scope", "config"]]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def corpus_args(corpus):
    return [corpus["rdf"], "nquads", corpus["policy"], corpus["scope"], corpus["config"]]


def freeze(protocol_path, out, binary):
    cfg = read(protocol_path)
    questions = read(ROOT / cfg["questions"])["questions"]
    require(cfg["version"] == "question-vocabulary-study-v1", "Unknown protocol")
    require(cfg["retrieval"] == "whole-original-question-per-role-BM25-only", "Wrong retrieval policy")
    require(cfg["budget"]["per_role_top_k"] == 20, "Coverage needs frozen top 20")
    require(questions and len({q["id"] for q in questions}) == len(questions), "Duplicate/empty question table")
    require(all(re.fullmatch(r"[a-z0-9-]+", q["id"]) for q in questions), "Unsafe case ID")
    require(not out.exists(), "Never overwrite a retrieval freeze")
    out.mkdir(parents=True)
    # References are hashed here, never parsed or supplied to the retrieval path.
    dump(out / "freeze.json", {"protocol": cfg, "input_sha256": inputs(protocol_path, cfg),
         "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
         "inference_performed": False, "holdout_accessed": False,
         "ordering": "inputs_and_selection_frozen_before_packets; all_packets_saved_before_reference_scoring"})
    dump(out / "budget.json", cfg["budget"])
    indexes = {}
    for name, corpus in cfg["corpora"].items():
        index = json.loads(cli(binary, "index-build", *corpus_args(corpus)))
        indexes[name] = index["manifest"]
        dump(out / f"{name}-manifest.json", index["manifest"])
    for q in questions:
        folder = out / q["id"]
        folder.mkdir()
        manifest = indexes[q["corpus"]]
        request = {"question": q["question"], "language": q["language"],
                   "snapshot_id": manifest["snapshot_id"], "index_revision": manifest["index_revision"],
                   "scope": read(ROOT / cfg["corpora"][q["corpus"]]["scope"])}
        dump(folder / "request.json", request)
        raw = cli(binary, "vocabulary", *corpus_args(cfg["corpora"][q["corpus"]]),
                  folder / "request.json", out / "budget.json").rstrip(b"\n")
        require(len(raw) <= cfg["budget"]["max_packet_bytes"], "Packet exceeds budget")
        (folder / "packet.json").write_bytes(raw)
    dump(out / "checksums.json", inventory(out))


def rdf_term(term):
    from rdflib import BNode, Literal, URIRef
    if term["kind"] == "iri":
        return URIRef(term["value"])
    if term["kind"] == "blank_node":
        return BNode(term["value"])
    require(term["kind"] == "literal", "Unknown RDF term")
    return Literal(term["value"], lang=term["language"],
                   datatype=None if term["language"] else URIRef(term["datatype"]), normalize=False)


def source_audit(packet, corpus, reference):
    import rdflib
    from rdflib import Dataset, Literal, RDF, URIRef
    rdflib.NORMALIZE_LITERALS = False
    data = Dataset()
    data.parse(ROOT / corpus["rdf"], format="nquads")
    scope = set(packet["request"]["scope"])
    require(scope <= set(read(ROOT / corpus["policy"])["graphs"]), "Unauthorized source audit")
    evidence = set()
    catalog = set()
    for g in scope:
        for s, p, o in data.graph(URIRef(g)):
            catalog.add(("predicate", g, str(p)))
            for node in (s, o):
                if isinstance(node, URIRef):
                    catalog.add(("entity", g, str(node)))
            if p == RDF.type and isinstance(o, URIRef):
                catalog.add(("class", g, str(o)))
    for ref in reference["required"]:
        require((ref["role"], ref["graph"], ref["iri"]) in catalog, "Reference is not an authorized graph-local catalog entry")
    start = next((r for r in reference["required"] if r["role"] == "entity"), None)
    for ref in reference["required"]:
        if "direction" in ref and start:
            require(start["graph"] == ref["graph"], "Cross-graph reference path")
            graph = data.graph(URIRef(ref["graph"]))
            pattern = ((URIRef(start["iri"]), URIRef(ref["iri"]), None) if ref["direction"] == "outgoing"
                       else (None, URIRef(ref["iri"]), URIRef(start["iri"])))
            require(ref["direction"] in ("outgoing", "incoming") and any(graph.triples(pattern)), "Reference direction lacks an original source triple")
    def witness(s, p, o, g):
        graph = data.graph(URIRef(g))
        # RDF 1.1 plain strings and xsd:string denote the same RDF literal.
        if (s, p, o) not in graph and isinstance(o, Literal) and o.datatype == rdflib.XSD.string:
            o = Literal(str(o), normalize=False)
        require(g in scope and (s, p, o) in graph, "Non-source packet witness")
        evidence.add(f"{s.n3()} {p.n3()} {o.n3()} <{g}> .")
    for role, collection in COLLECTIONS.items():
        for candidate in packet[collection]["candidates"]:
            g, iri = candidate["graph"], candidate["iri"]
            require((role, g, iri) in catalog, "Non-catalog or wrong-role candidate")
            for text in candidate["texts"]:
                value = text["value"]
                subject = URIRef(text.get("via", {}).get("source_iri", iri))
                predicate = URIRef(text["predicate"])
                matches = [o for o in data.graph(URIRef(g)).objects(subject, predicate)
                           if isinstance(o, Literal) and o.language == value["language"]
                           and str(rdflib.RDF.langString if o.language else o.datatype or rdflib.XSD.string) == value["datatype"]
                           and (str(o).startswith(value["text"]) if text["truncated"] else str(o) == value["text"])]
                require(bool(matches), "Invented/changed label, alias, language or datatype")
                witness(subject, predicate, matches[0], g)
                if "via" in text:
                    witness(subject, URIRef(text["via"]["predicate"]), URIRef(iri), g)
            for page in candidate["usage"]:
                for statement in page["evidence"]:
                    terms = [rdf_term(statement[k]) for k in ["subject", "predicate", "object", "source_graph"]]
                    witness(*terms[:3], str(terms[3]))
    return catalog, sorted(evidence)


def directed(packet, start, predicate, direction, k):
    entities = [c for c in packet["entities"]["candidates"][:k]
                if c["iri"] == start["iri"] and c["graph"] == start["graph"]]
    predicates = [c for c in packet["predicates"]["candidates"][:k]
                  if c["iri"] == predicate["iri"] and c["graph"] == predicate["graph"]]
    if start["graph"] != predicate["graph"] or direction not in ("incoming", "outgoing"):
        return False
    position = "subject" if direction == "outgoing" else "object"
    return bool(entities and predicates and any(
        s["source_graph"] == {"kind": "iri", "value": start["graph"]}
        and s["predicate"] == {"kind": "iri", "value": predicate["iri"]}
        and s[position] == {"kind": "iri", "value": start["iri"]}
        for c in entities + predicates for page in c["usage"] for s in page["evidence"]))


def score_case(packet, reference, catalog):
    required = reference["required"]
    rows = []
    for ref in required:
        role, graph, iri = ref["role"], ref["graph"], ref["iri"]
        hits = packet[COLLECTIONS[role]]["candidates"]
        rank = next((i for i, c in enumerate(hits, 1) if (c["graph"], c["iri"]) == (graph, iri)), None)
        rows.append({**ref, "rank": rank, "authorized_catalog_match": (role, graph, iri) in catalog,
                     "iri_present_any_graph": any(c["iri"] == iri for c in hits),
                     "graph_covered_at": {str(k): any(c["graph"] == graph for c in hits[:k]) for k in KS},
                     "role_and_graph_covered_at": {str(k): rank is not None and rank <= k for k in KS}})
    start = next((r for r in required if r["role"] == "entity"), None)
    predicate = next((r for r in required if r["role"] == "predicate" and "direction" in r), None)
    keys = [(role, c["graph"], c["iri"]) for role, collection in COLLECTIONS.items()
            for c in packet[collection]["candidates"]]
    return {"required": rows, "missing_at": {str(k): [r for r in rows if r["rank"] is None or r["rank"] > k] for k in KS},
            "direction_covered_at": {str(k): directed(packet, start, predicate, predicate["direction"], k)
                                     if start and predicate else None for k in KS},
            "duplicates": len(keys) - len(set(keys)),
            "cross_role_identity_repeats": len(keys) - len({(g, iri) for _, g, iri in keys}),
            "negative_candidate_returns": len(keys) if reference.get("expected_no_match") else None,
            "negative_returned_candidates": [list(key) for key in keys] if reference.get("expected_no_match") else [],
            "clipped": packet["clipped"], "status": packet["status"]}


def validate_freeze(folder):
    require(read(folder / "checksums.json") == inventory(folder), "Changed frozen packet files")
    freeze_record = read(folder / "freeze.json")
    for name, digest in freeze_record["input_sha256"].items():
        require(sha(ROOT / name) == digest, f"Post-freeze input drift: {name}")
    require(not freeze_record["inference_performed"] and not freeze_record["holdout_accessed"], "Wrong study boundary")
    return freeze_record["protocol"]


def evaluate(folder, binary):
    cfg = validate_freeze(folder)
    # Every packet already exists and is checksummed before reference IDs are parsed.
    questions = read(ROOT / cfg["questions"])["questions"]
    references = read(ROOT / cfg["references"])
    require(set(references["cases"]) == {q["id"] for q in questions}, "Reference denominator mismatch")
    outcomes = []
    source_evidence = {}
    for q in questions:
        case = folder / q["id"]
        corpus = cfg["corpora"][q["corpus"]]
        replay = json.loads(cli(binary, "vocabulary-replay", *corpus_args(corpus),
                            case / "request.json", folder / "budget.json", case / "packet.json"))
        require(replay == read(case / "packet.json"), f"First packet regression: {q['id']}")
        catalog, source_evidence[q["id"]] = source_audit(replay, corpus, references["cases"][q["id"]])
        outcomes.append({"id": q["id"], "question": q["question"], "language": q["language"],
                         "corpus": q["corpus"], **score_case(replay, references["cases"][q["id"]], catalog)})
    aggregates = {}
    for k in map(str, KS):
        by_role = {}
        for role in COLLECTIONS:
            rows = [r for c in outcomes for r in c["required"] if r["role"] == role]
            by_role[role] = {"covered": sum(r["role_and_graph_covered_at"][k] for r in rows), "total": len(rows)}
        directions = [c["direction_covered_at"][k] for c in outcomes if c["direction_covered_at"][k] is not None]
        aggregates[k] = {"role_graph_coverage": by_role,
                         "candidate_direction_coverage": {"covered": sum(directions), "total": len(directions)},
                         "all_required_covered_cases": sum(bool(c["required"]) and not c["missing_at"][k] for c in outcomes)}
    return {"version": "question-vocabulary-coverage-v1", "case_count": len(outcomes), "at_k": aggregates,
            "first_miss_in_frozen_order": {str(k): next(({"id": c["id"], "missing": c["missing_at"][str(k)]}
                                                         for c in outcomes if c["missing_at"][str(k)]), None) for k in KS},
            "cases": outcomes, "source_evidence": source_evidence,
            "reviewer_status": references["reviewer_status"], "issue72_cases": "pending_issue72_freeze",
            "inference_performed": False, "holdout_accessed": False,
            "limitations": "New retrieval regressions on public exposed sources; not independent #72 evaluation or human semantic validation. No baseline tuned after observing ranks. No-match does not prove absence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "score", "verify"])
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--folder", type=Path, default=ROOT / "reports/issue-73-question-vocabulary/freeze")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/issue-73-question-vocabulary/coverage.json")
    parser.add_argument("--binary", type=Path, default=ROOT / "target/debug/verity")
    args = parser.parse_args()
    binary, folder = args.binary.resolve(), args.folder.resolve()
    if args.command == "freeze":
        freeze(args.protocol.resolve(), folder, binary)
    elif args.command == "score":
        require(not args.report.exists(), "Never overwrite a scored report")
        dump(args.report, evaluate(folder, binary))
        dump(args.report.parent / "checksums.json", inventory(args.report.parent))
    else:
        require(read(args.report.parent / "checksums.json") == inventory(args.report.parent), "Changed checksummed report")
        require(read(args.report) == evaluate(folder, binary), "First coverage/source-evidence regression")
    print(f"{args.command}: question-only BM25; no inference or sealed holdout access")


if __name__ == "__main__":
    main()
