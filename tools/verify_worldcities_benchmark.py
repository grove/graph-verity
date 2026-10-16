#!/usr/bin/env python3
"""Read-only second-ontology reference oracle. Never accesses a locked holdout."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from rdflib import Dataset, BNode, Literal, URIRef

import worldcities_transfer as transfer

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "worldcities-transfer.json"

def rdf_term(term):
    if isinstance(term, URIRef):
        return {"kind": "iri", "value":str(term)}
    if isinstance(term, BNode):
        return {"kind": "blank_node", "value": str(term)}
    if isinstance(term, Literal):
        return {"kind": "literal", "value": str(term),
                "language": term.language,
                "datatype": str(term.datatype or
                                ("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
                                 if term.language else
                                 "http://www.w3.org/2001/XMLSchema#string"))}
    raise ValueError("Unsupported reference binding")

def rows(store: Dataset, query: str):
    result = store.query(query)
    if result.type != "SELECT":
        raise ValueError("Reference queries must be SELECT")
    values = []
    for record in result:
        values.append({str(v): rdf_term(record[v]) for v in result.vars if record[v] is not None})
    return values

def normalized(answer):
    return sorted(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                  for row in answer)

def verify() -> dict:
    transfer_info = transfer.verify()
    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    cases = benchmark["cases"]
    if (benchmark["version"] != 1 or benchmark["snapshot_id"] != transfer_info["snapshot_id"]
            or len(cases) != 40 or len({c["id"] for c in cases}) != 40
            or any(c["split"] != "transfer_dev" for c in cases)):
        raise ValueError("Invalid model-independent transfer benchmark contract")
    store = Dataset()
    store.parse(data=(transfer.DATA / "snapshot.nq").read_bytes(), format="nquads")
    executed = abstentions = 0
    for case in cases:
        status = case["expected_status"]
        if not case["question"].strip() or not case["interpretation"].strip():
            raise ValueError("Missing intended question semantics")
        if status == "executed":
            executed += 1
            plan = case["gold"]
            if (plan["snapshot_id"] != benchmark["snapshot_id"]
                    or plan["scope"] != case["scope"]
                    or len(plan["patterns"]) < 1
                    or len(plan["patterns"]) > 8
                    or case["reference_sparql"] is None
                    or case["expected_bindings"] is None):
                raise ValueError("Invalid expected query plan "+case["id"])
            found = rows(store, case["reference_sparql"])
            if normalized(found) != normalized(case["expected_bindings"]):
                raise ValueError("Frozen reference mismatch "+case["id"]+": "+
                                 json.dumps(found, ensure_ascii=False))
        elif status in ("needs_clarification", "unsupported"):
            abstentions += 1
            if any(case[field] is not None for field in
                   ("gold", "reference_sparql", "expected_bindings")):
                raise ValueError("Abstention may not carry invented executable gold")
        else:
            raise ValueError("Unknown expected query status")
    if (executed, abstentions) != (35, 5):
        raise ValueError("Unexpected reference and abstention denominators")
    return {"mode": "cross_ontology_oracle_no_model", "passed_executable": executed,
            "recorded_abstentions_not_model_tested": abstentions,
            "benchmark": benchmark["name"],
            "snapshot_id": benchmark["snapshot_id"],
            "interpretation_accuracy": None,
            "human_gold_approval": None,
            "locked_holdout_evaluated": False}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify"])
    args = parser.parse_args()
    print(json.dumps(verify(), indent=2))

if __name__ == "__main__":
    main()
