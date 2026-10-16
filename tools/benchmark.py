#!/usr/bin/env python3
"""Draft/freeze candidate gold with RDFLib, independently of the Rust compiler."""
from __future__ import annotations
import argparse
import copy
from decimal import Decimal
import json
from pathlib import Path
import rdflib
from rdflib import Dataset, Literal, URIRef
from dataset import DATA, ROOT, DIRECT, WD, WB, dump, sha, snapshot_id, verify as verify_data

rdflib.NORMALIZE_LITERALS = False
XSD = "http://www.w3.org/2001/XMLSchema#"
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
DEV = "urn:graph-verity:wikidata:development"
TRANSFER = "urn:graph-verity:wikidata:transfer"
PATH = ROOT / "benchmarks" / "wikidata.json"
PREFIX = f"PREFIX wd: <{WD}>\nPREFIX wdt: <{DIRECT}>\nPREFIX wikibase: <{WB}>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX xsd: <{XSD}>\n"
REVIEW = "machine_authored_machine_checked_human_review_pending"


def node(value: str) -> dict:
    return {"kind": "variable", "name": value[1:]} if value.startswith("?") else {"kind": "iri", "iri": value}


def edge(subject: str, predicate: str, obj: str, graph: str, reverse: bool = False) -> dict:
    return {"graph": graph, "from": node(subject), "predicate": predicate, "direction": "reverse" if reverse else "forward", "to": node(obj)}


def projection(name: str) -> dict:
    return {"kind": "variable", "name": name}


def count(variable: str, alias: str = "count") -> dict:
    return {"kind": "count_distinct", "variable": variable, "alias": alias}


def comparison(variable: str, op: str, lexical: str, datatype: str) -> dict:
    return {"variable": variable, "op": op, "value": {"lexical": lexical, "datatype": XSD + datatype, "language": None}}


def bindings(dataset: Dataset, query: str) -> list[dict]:
    rows = []
    for row in dataset.query(query):
        encoded = {}
        for name, term in row.asdict().items():
            if isinstance(term, URIRef):
                encoded[str(name)] = {"kind": "iri", "value": str(term)}
            elif isinstance(term, Literal):
                datatype = str(term.datatype or (URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString") if term.language else URIRef(XSD + "string")))
                encoded[str(name)] = {"kind": "literal", "value": str(term), "datatype": datatype, "language": term.language}
            else:
                raise ValueError("Gold blank-node identity needs an explicit equivalence policy")
        rows.append(encoded)
    unique = {json.dumps(row, sort_keys=True, ensure_ascii=False): row for row in rows}
    return [unique[key] for key in sorted(unique)]


def dataset() -> Dataset:
    return Dataset().parse(data=(DATA / "snapshot.nq").read_bytes(), format="nquads")


def create() -> None:
    verify_data()
    if PATH.exists():
        verify()
        print("Frozen benchmark retained; creation never overwrites gold")
        return
    rdf = dataset()
    snapshot = snapshot_id((DATA / "snapshot.nq").read_bytes())
    cases = []
    counters = {}

    def add(question: str, family: str, patterns: list[dict], selected: list[dict], reference: str,
            graph: str = DEV, filters: list[dict] | None = None, groups: list[str] | None = None,
            having: list[dict] | None = None, split: str = "dev") -> None:
        counters[split] = counters.get(split, 0) + 1
        plan = {"version": 1, "snapshot_id": snapshot, "scope": [graph], "patterns": patterns,
                "filters": filters or [], "projection": selected, "group_by": groups or [], "having": having or [], "limit": 100}
        reference = PREFIX + reference
        cases.append({"id": f"wd-{split}-{counters[split]:03d}", "question": question,
            "interpretation": f"Execute exactly the supplied directed plan in {graph}; direct best-ranked snapshot statements only, existential filters, no implicit latest-value selection or real-world completeness.",
            "family": family, "split": split, "review_status": REVIEW,
            "provenance": "data/wikidata/manifest.json; separately written reference SPARQL evaluated with RDFLib 7.1.4, not the Rust compiler; no independent human approval",
            "scope": [graph], "expected_status": "executed", "gold": plan,
            "reference_sparql": reference, "expected_bindings": bindings(rdf, reference)})

    def city_cases(qid: str, name: str, graph: str = DEV, split: str = "dev") -> None:
        entity = WD + qid
        add(f"Hvilke navn er oppført for {name} i utvalget?", "entity_labels", [edge(entity, LABEL, "?label", graph)], [projection("label")],
            f"SELECT DISTINCT ?label WHERE {{ GRAPH <{graph}> {{ wd:{qid} rdfs:label ?label }} }}", graph, split=split)
        add(f"Hvilket land er {name} knyttet til i grafen?", "direct_relation", [edge(entity, DIRECT + "P17", "?country", graph)], [projection("country")],
            f"SELECT DISTINCT ?country WHERE {{ GRAPH <{graph}> {{ wd:{qid} wdt:P17 ?country }} }}", graph, split=split)
        add(f"Hvilke land i utvalget har {name} som hovedstad?", "inverse_relation", [edge(entity, DIRECT + "P36", "?country", graph, True)], [projection("country")],
            f"SELECT DISTINCT ?country WHERE {{ GRAPH <{graph}> {{ ?country wdt:P36 wd:{qid} }} }}", graph, split=split)
        add(f"Hva er hovedstaden i landet som {name} er knyttet til?", "two_hop", [edge(entity, DIRECT + "P17", "?country", graph), edge("?country", DIRECT + "P36", "?capital", graph)], [projection("capital")],
            f"SELECT DISTINCT ?capital WHERE {{ GRAPH <{graph}> {{ wd:{qid} wdt:P17 ?country . ?country wdt:P36 ?capital }} }}", graph, split=split)
        add(f"Hvilke etableringsdatoer er oppført for {name} i grafutvalget?", "date_lookup", [edge(entity, DIRECT + "P571", "?date", graph)], [projection("date")],
            f"SELECT DISTINCT ?date WHERE {{ GRAPH <{graph}> {{ wd:{qid} wdt:P571 ?date }} }}", graph, split=split)

    for qid, name in [("Q585", "Oslo"), ("Q26793", "Bergen"), ("Q25804", "Trondheim"), ("Q25416", "Stavanger")]:
        city_cases(qid, name)
    observed = sorted(Decimal(str(v)) for v in rdf.graph(URIRef(DEV)).objects(URIRef(WD + "Q585"), URIRef(DIRECT + "P1082")))
    if not observed or observed[0] != observed[0].to_integral_value():
        raise ValueError("Oslo population boundary must be inspected before drafting numeric cases")
    boundary = str(int(observed[0]))
    numeric_cases = [("gt", ">", "100000", "mer enn 100000"), ("ge", ">=", "200000", "minst 200000"),
        ("lt", "<", "1000000", "under 1000000"), ("le", "<=", "500000", "høyst 500000"),
        ("gt", ">", boundary, f"mer enn {boundary}"), ("ge", ">=", boundary, f"minst {boundary}")]
    for op, symbol, number, words in numeric_cases:
        add(f"Hvilke ressurser knyttet til Norge har et oppgitt folketall på {words} i utvalget?", "numeric_comparison",
            [edge("?entity", DIRECT + "P17", WD + "Q20", DEV), edge("?entity", DIRECT + "P1082", "?population", DEV)], [projection("entity")],
            f"SELECT DISTINCT ?entity WHERE {{ GRAPH <{DEV}> {{ ?entity wdt:P17 wd:Q20; wdt:P1082 ?population . FILTER(?population {symbol} {number}) }} }}",
            filters=[comparison("population", op, number, "integer")])
    for op, symbol, year, words in [("lt", "<", "1100", "før 1100"), ("le", "<=", "1200", "senest 1. januar 1200"), ("ge", ">=", "1000", "fra og med 1. januar 1000"), ("gt", ">", "1500", "etter 1. januar 1500")]:
        date = year + "-01-01T00:00:00Z"
        add(f"Hvilke ressurser har en oppgitt etableringsdato {words} i grafutvalget?", "date_comparison",
            [edge("?entity", DIRECT + "P571", "?date", DEV)], [projection("entity")],
            f'SELECT DISTINCT ?entity WHERE {{ GRAPH <{DEV}> {{ ?entity wdt:P571 ?date . FILTER(?date {symbol} "{date}"^^xsd:dateTime) }} }}',
            filters=[comparison("date", op, date, "dateTime")])
    add("Hvor mange ulike Wikidata-elementer finnes i utviklingsutvalget?", "distinct_count",
        [edge("?entity", TYPE, WB + "Item", DEV)], [count("entity")],
        f"SELECT (COUNT(DISTINCT ?entity) AS ?count) WHERE {{ GRAPH <{DEV}> {{ ?entity a wikibase:Item }} }}")
    add("Hvor mange ulike land peker land-relasjonene i utviklingsutvalget til?", "distinct_count",
        [edge("?entity", DIRECT + "P17", "?country", DEV)], [count("country")],
        f"SELECT (COUNT(DISTINCT ?country) AS ?count) WHERE {{ GRAPH <{DEV}> {{ ?entity wdt:P17 ?country }} }}")
    for threshold in [None, 2, 5]:
        having = [] if threshold is None else [{"alias": "count", "op": "ge", "value": threshold}]
        condition = "" if threshold is None else f" HAVING(COUNT(DISTINCT ?entity) >= {threshold})"
        question = "Hvor mange ulike ressurser i utvalget er knyttet til hvert land?" if threshold is None else f"Hvilke land har minst {threshold} ulike tilknyttede ressurser i utvalget, og hvor mange?"
        add(question, "grouping" if threshold is None else "having",
            [edge("?entity", DIRECT + "P17", "?country", DEV)], [projection("country"), count("entity")],
            f"SELECT ?country (COUNT(DISTINCT ?entity) AS ?count) WHERE {{ GRAPH <{DEV}> {{ ?entity wdt:P17 ?country }} }} GROUP BY ?country{condition}", groups=["country"], having=having)
    add("Hvilke elementer i utvalget har minst to ulike oppførte klassifiseringer, og hvor mange?", "conjunction_distinct_count",
        [edge("?entity", TYPE, WB + "Item", DEV), edge("?entity", DIRECT + "P31", "?class", DEV)], [projection("entity"), count("class")],
        f"SELECT ?entity (COUNT(DISTINCT ?class) AS ?count) WHERE {{ GRAPH <{DEV}> {{ ?entity a wikibase:Item; wdt:P31 ?class }} }} GROUP BY ?entity HAVING(COUNT(DISTINCT ?class) >= 2)", groups=["entity"], having=[{"alias": "count", "op": "ge", "value": 2}])
    add("Hvilke Wikidata-elementer finnes innenfor den valgte utviklingsgrafen?", "named_graph_scope",
        [edge("?entity", TYPE, WB + "Item", DEV)], [projection("entity")],
        f"SELECT DISTINCT ?entity WHERE {{ GRAPH <{DEV}> {{ ?entity a wikibase:Item }} }}")
    add("Hvilke ressurser har både oppgitt folketall over 200000 og en etableringsdato før 1100?", "conjunction_numeric_date",
        [edge("?entity", DIRECT + "P1082", "?population", DEV), edge("?entity", DIRECT + "P571", "?date", DEV)], [projection("entity")],
        f'SELECT DISTINCT ?entity WHERE {{ GRAPH <{DEV}> {{ ?entity wdt:P1082 ?population; wdt:P571 ?date . FILTER(?population > 200000 && ?date < "1100-01-01T00:00:00Z"^^xsd:dateTime) }} }}',
        filters=[comparison("population", "gt", "200000", "integer"), comparison("date", "lt", "1100-01-01T00:00:00Z", "dateTime")])
    abstentions = [
        ("Hva er hovedstaden?", "needs_clarification", "Country and intended scope are unspecified"),
        ("Hvilken by er størst?", "needs_clarification", "Largest could mean area, population or another measure"),
        ("Hvor mange innbyggere har Oslo akkurat nå?", "unsupported", "Current-world/time-qualified population is not established by this direct-statement capture"),
        ("Hvilke byer har ikke noen etableringsdato?", "unsupported", "Negation and closed-world absence inference are unsupported"),
        ("Hvilke selskaper eier Oslo kommune?", "unsupported", "Ownership and municipal corporate entities are outside the selected vocabulary/data"),
        ("Hvor mye vokste Bergen fra 2020 til 2025?", "unsupported", "Time-qualified observations and temporal arithmetic are not supported"),
        ("Vis alle kommuner i Norge.", "unsupported", "Selected city entities do not form a complete municipality registry"),
        ("Vis aktive kontrakter for Trondheim.", "unsupported", "No contract/status domain is included"),
    ]
    for question, status, reason in abstentions:
        counters["dev"] += 1
        cases.append({"id": f"wd-dev-{counters['dev']:03d}", "question": question, "interpretation": reason,
            "family": "ambiguous" if status == "needs_clarification" else "unsupported", "split": "dev", "review_status": REVIEW,
            "provenance": "Machine-drafted boundary question; requires human review; no model abstention observed", "scope": [DEV],
            "expected_status": status, "gold": None, "reference_sparql": None, "expected_bindings": None})
    # Prospective review pool, not an independently authored or locked statistical test set.
    for original in [case for case in cases if case["gold"] is not None]:
        for prefix in ["Bruk bare opplysningene i dette grafutvalget: ", "Med den lagrede grafversjonen som grunnlag: "]:
            candidate = copy.deepcopy(original)
            counters["review_candidate"] = counters.get("review_candidate", 0) + 1
            candidate["id"] = f"wd-review-{counters['review_candidate']:03d}"
            candidate["split"] = "review_candidate"
            candidate["question"] = prefix + original["question"]
            candidate["provenance"] += "; templated paraphrase of " + original["id"] + "; not independent holdout"
            cases.append(candidate)
    city_cases("Q1754", "Stockholm", TRANSFER, "transfer_candidate")
    for selected, question, ref in [
        ([projection("entity")], "Hvilke elementer finnes bare i den valgte overføringsgrafen?", "SELECT DISTINCT ?entity"),
        ([count("entity")], "Hvor mange ulike elementer finnes i overføringsutvalget?", "SELECT (COUNT(DISTINCT ?entity) AS ?count)"),
    ]:
        add(question, "transfer_scope", [edge("?entity", TYPE, WB + "Item", TRANSFER)], selected,
            f"{ref} WHERE {{ GRAPH <{TRANSFER}> {{ ?entity a wikibase:Item }} }}", TRANSFER, split="transfer_candidate")
    add("Hvilke land og hovedsteder er uttrykkelig oppført i overføringsgrafen?", "transfer_relation",
        [edge("?country", DIRECT + "P36", "?capital", TRANSFER)], [projection("country"), projection("capital")],
        f"SELECT DISTINCT ?country ?capital WHERE {{ GRAPH <{TRANSFER}> {{ ?country wdt:P36 ?capital }} }}", TRANSFER, split="transfer_candidate")
    benchmark = {"version": 1, "name": "wikidata-nordic-candidate-v1", "snapshot_id": snapshot, "cases": cases}
    dump(PATH, benchmark)
    splits = {split: [case["id"] for case in cases if case["split"] == split] for split in sorted({case["split"] for case in cases})}
    dump(ROOT / "benchmarks" / "split-manifest.json", {"benchmark_sha256": sha(PATH.read_bytes()), "splits": splits,
        "holdout_status": "prospective_candidate_pools_not_independent_or_human_approved; do_not_tune_on_candidates; reviewer_must_author_and_freeze_final_holdout"})
    policy = {"version": 1, "graphs": [DEV, TRANSFER], "max_rows": 1000, "max_evidence": 10000, "timeout_ms": 10000}
    dump(DATA / "policy.json", policy)
    dump(DATA / "scope.json", [DEV])
    sample = next(case for case in cases if case["family"] == "two_hop")
    dump(ROOT / "examples" / "manual-plan.json", sample["gold"])
    dump(ROOT / "examples" / "fixture-response.json", {"version": 1, "proposal": {"status": "candidate", "plan": sample["gold"]}})
    (ROOT / "examples" / "question.txt").write_text(sample["question"] + "\n", encoding="utf-8")
    dump(ROOT / "examples" / "unsupported-response.json", {"version": 1, "proposal": {"status": "unsupported", "reason": "Fixture status only; no interpretation was performed"}})
    (ROOT / "examples" / "invalid-response.json").write_text('{"version":1,"proposal":{"status":"candidate","sparql":"DROP ALL"}}\n', encoding="utf-8")
    verify()
    print(json.dumps({"candidate_questions": len(cases), "splits": {k: len(v) for k, v in splits.items()}}, ensure_ascii=False))


def verify() -> None:
    verify_data()
    benchmark = json.loads(PATH.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "benchmarks" / "split-manifest.json").read_text(encoding="utf-8"))
    if sha(PATH.read_bytes()) != manifest["benchmark_sha256"]:
        raise ValueError("Frozen benchmark checksum changed")
    if benchmark["snapshot_id"] != snapshot_id((DATA / "snapshot.nq").read_bytes()):
        raise ValueError("Benchmark snapshot mismatch")
    rdf = dataset()
    ids = [case["id"] for case in benchmark["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question ID")
    for case in benchmark["cases"]:
        if case["id"] not in manifest["splits"][case["split"]] or case["review_status"] != REVIEW:
            raise ValueError("Split or review state requires approval")
        if case["split"] == "dev" and case["reference_sparql"] is not None:
            actual = bindings(rdf, case["reference_sparql"])
            if actual != case["expected_bindings"]:
                raise ValueError(f"Independent reference mismatch: {case['id']}")
    print("Frozen development reference queries and bindings verified with RDFLib; gold was not rewritten")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["create", "verify"])
    args = parser.parse_args()
    create() if args.command == "create" else verify()
