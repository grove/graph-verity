#!/usr/bin/env python3
"""Describe saved Ask alpha v2 candidate positions; never rerun retrieval or models."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks/ask-alpha-v1"
TOP_K = (1, 5, 10)


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    manifest = read(BENCH / "manifest.json")
    for name, digest in manifest["input_sha256"].items():
        path = ROOT / name
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f"Changed frozen Ask alpha input: {name}")
    return manifest


def candidate_rank(candidates, graph, iri):
    return next((rank for rank, candidate in enumerate(candidates, 1)
                 if candidate["graph"] == graph and candidate["iri"] == iri), None)


def direction_witness(packet, plan):
    direction = "outgoing" if plan["direction"] == "forward" else "incoming"
    for role, iri in (("entities", plan["start"]), ("predicates", plan["predicate"])):
        for candidate in packet[role]["candidates"]:
            if candidate["graph"] != plan["graph"] or candidate["iri"] != iri:
                continue
            for page in candidate["usage"]:
                for statement in page["evidence"]:
                    if (statement["source_graph"]["value"] == plan["graph"]
                            and statement["predicate"]["value"] == plan["predicate"]
                            and statement["subject"]["value"] == plan["start"]
                            and direction == "outgoing") or (
                            statement["source_graph"]["value"] == plan["graph"]
                            and statement["predicate"]["value"] == plan["predicate"]
                            and statement["object"]["value"] == plan["start"]
                            and direction == "incoming"):
                        return True
    return False


def neighboring_entity_witness(packet, graph, iri):
    for rank, seed in enumerate(packet["entities"]["candidates"], 1):
        if seed["graph"] != graph or seed["iri"] == iri:
            continue
        for page in seed["usage"]:
            for statement in page["evidence"]:
                if statement["source_graph"]["value"] != graph:
                    continue
                if page["direction"] == "outgoing" and statement["subject"]["value"] == seed["iri"]:
                    neighbor = statement["object"]
                elif page["direction"] == "incoming" and statement["object"]["value"] == seed["iri"]:
                    neighbor = statement["subject"]
                else:
                    continue
                if neighbor["kind"] == "iri" and neighbor["value"] == iri:
                    return {"seed_rank": rank, "seed_iri": seed["iri"],
                            "direction": page["direction"], "statement": statement}
    return None


def coverage(rows, rank_field, k):
    return {"hits": sum(row[rank_field] is not None and row[rank_field] <= k for row in rows),
            "total": len(rows)}


def summarize():
    manifest = verify()
    questions = read(BENCH / "questions.json")["cases"]
    references = {row["id"]: row for row in read(BENCH / "references.json")["cases"]}
    packets = json.loads(gzip.decompress((BENCH / "packets.json.gz").read_bytes()))
    if len(questions) != 60 or set(packets) != {row["id"] for row in questions} or set(references) != set(packets):
        raise ValueError("Ask alpha candidate baseline must contain the frozen 60 cases")
    languages = {language: sum(question["language"] == language for question in questions)
                 for language in ("en", "nb")}
    if languages != {"en": 30, "nb": 30}:
        raise ValueError("Ask alpha candidate baseline must retain the frozen language split")

    rows = []
    for question in questions:
        case_id = question["id"]
        packet = packets[case_id]["packet"]
        reference = references[case_id]
        if (packet["version"] != "question-vocabulary-packet-v2-neighborhood"
                or packet["request"]["language"] != question["language"]
                or packet["request"]["question"] != question["question"]
                or reference["question"] != question["question"]
                or reference["language"] != question["language"]
                or reference["intent_mapping_origin"] != "coding_agent_authored_not_independent_human_gold"):
            raise ValueError(f"Question, packet, or reference identity mismatch: {case_id}")
        scope = set(packet["request"]["scope"])
        if any(candidate["graph"] not in scope for role in ("entities", "predicates")
               for candidate in packet[role]["candidates"]):
            raise ValueError(f"Out-of-scope candidate: {case_id}")

        plan = reference["expected_plan"]
        entity_rank = predicate_rank = predicate_score = witnessed = adjacent = None
        source_path_nonempty = bool(reference["source_witnesses"]) if plan else None
        if plan:
            entity_rank = candidate_rank(packet["entities"]["candidates"], plan["graph"], plan["start"])
            predicate_rank = candidate_rank(packet["predicates"]["candidates"], plan["graph"], plan["predicate"])
            predicate = next((candidate for candidate in packet["predicates"]["candidates"]
                              if candidate["graph"] == plan["graph"] and candidate["iri"] == plan["predicate"]), None)
            predicate_score = predicate["ranking_score"] if predicate else None
            witnessed = direction_witness(packet, plan)
            adjacent = neighboring_entity_witness(packet, plan["graph"], plan["start"]) if entity_rank is None else None
        rows.append({"id": case_id, "language": question["language"], "reference_status": reference["expected_status"],
                     "direction": plan["direction"] if plan else None, "entity_rank": entity_rank,
                     "predicate_rank_v2_combined": predicate_rank, "predicate_bm25_score": predicate_score,
                     "source_path_nonempty_in_agent_reference": source_path_nonempty,
                     "source_direction_witness_in_packet": witnessed, "missing_entity_neighbor_witness": adjacent,
                     "packet_clipped": packet["clipped"],
                     "entity_candidates": len(packet["entities"]["candidates"]),
                     "predicate_candidates": len(packet["predicates"]["candidates"])})

    supported = [row for row in rows if row["reference_status"] == "candidate"]
    strata = {}
    for field in ("language", "direction"):
        values = sorted({row[field] for row in supported})
        strata[field] = {}
        for value in values:
            subset = [row for row in supported if row[field] == value]
            strata[field][value] = {str(k): {"entity": coverage(subset, "entity_rank", k),
                                             "predicate_v2_combined": coverage(subset, "predicate_rank_v2_combined", k),
                                             "both": {"hits": sum(row["entity_rank"] is not None and row["entity_rank"] <= k
                                                                   and row["predicate_rank_v2_combined"] is not None
                                                                   and row["predicate_rank_v2_combined"] <= k for row in subset),
                                                      "total": len(subset)}} for k in TOP_K}

    returned = {}
    for status in ("needs_clarification", "unsupported"):
        subset = [row for row in rows if row["reference_status"] == status]
        returned[status] = {"cases": len(subset),
                             "with_entity_and_predicate_candidates": sum(row["entity_candidates"] > 0
                                                                           and row["predicate_candidates"] > 0 for row in subset)}

    return {"version": "ask-alpha-candidate-metrics-v1",
            "source": {name: manifest["input_sha256"][name] for name in (
                "benchmarks/ask-alpha-v1/questions.json", "benchmarks/ask-alpha-v1/references.json",
                "benchmarks/ask-alpha-v1/packets.json.gz", "benchmarks/ask-alpha-v1/source.json")},
            "summary": {"cases": len(rows), "languages": languages,
                        "agent_reference_candidate_cases": len(supported),
                        "candidate_position_coverage": {str(k): {"entity_bm25_seed": coverage(supported, "entity_rank", k),
                                                                 "predicate_v2_combined": coverage(supported, "predicate_rank_v2_combined", k),
                                                                 "both": {"hits": sum(row["entity_rank"] is not None and row["entity_rank"] <= k
                                                                                       and row["predicate_rank_v2_combined"] is not None
                                                                                       and row["predicate_rank_v2_combined"] <= k for row in supported),
                                                                          "total": len(supported)}} for k in TOP_K},
                        "reference_predicates_with_zero_bm25_score": sum(row["predicate_bm25_score"] == 0 for row in supported),
                        "witnesses_for_nonempty_reference_paths": {
                            "hits": sum(row["source_direction_witness_in_packet"] is True for row in supported
                                        if row["source_path_nonempty_in_agent_reference"]),
                            "total": sum(row["source_path_nonempty_in_agent_reference"] for row in supported)},
                        "empty_reference_paths_without_witness": sum(
                            not row["source_path_nonempty_in_agent_reference"]
                            and row["source_direction_witness_in_packet"] is False for row in supported),
                        "missing_entity_targets_with_neighbor_witness": sum(row["missing_entity_neighbor_witness"] is not None for row in supported),
                        "clipped_supported_packets": sum(row["packet_clipped"] for row in supported),
                        "noncandidate_suggestion_returns": returned},
            "strata": strata, "cases": rows,
            "method": {"entity_rank": "Exact graph+IRI position in the unchanged v2 BM25 entity-seed list.",
                       "predicate_rank_v2_combined": "Exact graph+IRI position in the v2 list combining retained lexical candidates and source-witnessed neighboring predicates; not a BM25-only rank.",
                       "predicate_bm25_score": "The saved v2 candidate score: BM25 for lexical hits and zero for added neighbors; zero does not rule out a lexical hit beyond the original retained list.",
                       "source_direction_witness": "Exact original graph+predicate+start endpoint is present in retained candidate usage; compare against agent-reference source_witnesses so intentionally empty paths are not treated as misses.",
                       "reference_status": "Coding-agent-authored development references, not human relevance judgments."},
            "human_observations": 0, "inference_performed": False, "new_graph_queries_performed": False,
            "limitations": ["Development-only exposed packets; no sealed holdout.",
                            "Candidate positions measure reference-ID presence, not relevance, answer accuracy, precision, or user usefulness.",
                            "Saved v2 packets can be clipped; absent candidates or edges are unknown.",
                            "The v2 packet does not preserve a separate full predicate BM25 ranking for this 60-case set."],
            "analysis_code_sha256": sha(Path(__file__)),
            "input_manifest_sha256": sha(BENCH / "manifest.json")}


if __name__ == "__main__":
    print(json.dumps(summarize(), ensure_ascii=False, indent=2))
