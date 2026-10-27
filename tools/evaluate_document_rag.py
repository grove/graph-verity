#!/usr/bin/env python3
"""Run source-only document Ask for a reviewed CSV question set; emit JSONL."""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import re

import document_rag as documents
import grounded_rag as evidence
import local_document_ask as ask

MAX_QUESTIONS_BYTES = 1024 * 1024
MAX_CASES = 100
LABELS = {
    "OWNER_REVIEW_REQUIRED", "SUPPORTED_BY_SOURCE",
    "UNSUPPORTED_BY_SELECTED_SOURCES", "AMBIGUOUS", "CONFLICTING", "UNKNOWN",
}
QUESTION_FIELDS = (
    "case_id", "question", "language", "source_expectation",
    "expectation_reviewer", "expected_document_id", "expected_citation_id",
    "human_relevance_judgment", "human_reviewer", "notes",
)
CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


def read_questions(path: Path) -> list[dict]:
    raw = documents.limited_file(path, MAX_QUESTIONS_BYTES)
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
        if tuple(reader.fieldnames or ()) != QUESTION_FIELDS:
            raise ValueError("Question CSV must use the evaluation template header")
        cases, seen = [], set()
        for row in reader:
            if row is None or not any(value for value in row.values() if value):
                continue
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Evaluation row has the wrong number of CSV fields")
            case_id, question, language = (row["case_id"].strip(),
                                           row["question"].strip(),
                                           row["language"].strip())
            expectation = row["source_expectation"].strip() or "OWNER_REVIEW_REQUIRED"
            expectation_reviewer = row["expectation_reviewer"].strip()
            human = row["human_relevance_judgment"].strip()
            document_id = row["expected_document_id"].strip()
            citation_id = row["expected_citation_id"].strip()
            if (None in row or not CASE_ID.fullmatch(case_id) or case_id in seen or
                    not question or language not in {"en", "nb"} or
                    expectation not in LABELS or
                    (human and human not in LABELS - {"OWNER_REVIEW_REQUIRED"}) or
                    (document_id and not documents.IDENT.fullmatch(document_id)) or
                    (citation_id and (not evidence.CITATION.fullmatch(citation_id) or
                                       not citation_id.startswith("d:")))):
                raise ValueError("Invalid or duplicate evaluation case")
            if len(question.encode("utf-8")) > documents.MAX_QUERY:
                raise ValueError("Evaluation question exceeds the Ask query limit")
            if expectation != "OWNER_REVIEW_REQUIRED" and not expectation_reviewer:
                raise ValueError("A reviewed source expectation requires a reviewer name")
            if human and not row["human_reviewer"].strip():
                raise ValueError("A human relevance label requires a reviewer name")
            seen.add(case_id)
            cases.append({
                "case_id": case_id, "question": question, "language": language,
                "source_expectation": expectation,
                "expectation_reviewer": expectation_reviewer or None,
                "expected_document_id": document_id or None,
                "expected_citation_id": citation_id or None,
                "human_relevance_judgment": human or None,
                "human_reviewer": row["human_reviewer"].strip() or None,
                "notes": row["notes"].strip() or None,
            })
            if len(cases) > MAX_CASES:
                raise ValueError("Evaluation question set exceeds 100 cases")
        if not cases:
            raise ValueError("Question CSV contains no evaluation cases")
        return cases
    except (UnicodeError, csv.Error, KeyError, TypeError) as error:
        raise ValueError("Invalid UTF-8 evaluation question CSV") from error


def evaluate_case(bundle: ask.Bundle, manifest: Path, index_path: Path,
                  scope: str, corpus: dict, case: dict) -> dict:
    request = {key: case[key] for key in ("question", "language")}
    result = bundle.api(ask.PREFIX + "ask", request)
    packet, view = result["packet"], result["view"]
    if result["execution"] != "none" or view.get("model_invoked") is not False:
        raise ValueError("Evaluation runner must remain source-only")
    hits, risk = [], None
    if packet is not None:
        if (packet["generation"]["model_invoked"] or
                packet["completeness"]["graph_status"] != "not_invoked"):
            raise ValueError("Evaluation runner must not invoke a model or graph")
        # Re-open the trusted index after Ask returns; suppress rankings if its
        # source bundle changed during this case.
        current = documents.load_index(manifest, index_path, scope)
        if current["index_sha256"] != packet["retrieval"]["index_sha256"]:
            result = bundle.unavailable("source_changed")
            packet, view = result["packet"], result["view"]
        else:
            packet_ids = {item["citation_id"] for item in packet["document_evidence"]}
            search = documents.search_index(current, case["question"], 3)
            for rank, hit in enumerate(search["hits"], 1):
                cited = documents.cite(current, hit["citation_id"])["evidence"]
                verified = all(hit.get(key) == value for key, value in cited.items())
                hits.append({
                    "rank": rank, "document_id": hit["document_id"],
                    "source": hit["source"], "language": hit["language"],
                    "citation_id": hit["citation_id"], "span": hit["span"],
                    "text": hit["text"], "bm25_score": hit["score"],
                    "score_kind": "bm25_not_confidence",
                    "original_source_span_verified": verified,
                    "returned_by_source_only_ask": hit["citation_id"] in packet_ids,
                })
            risk = view.get("grounding_risk")

    expected_doc = case["expected_document_id"]
    expected_citation = case["expected_citation_id"]
    result_hits = [item for item in hits if item["returned_by_source_only_ask"]]
    return {
        **case,
        "corpus_version": corpus,
        "selected_scope": scope,
        "retrieval_status": (packet["completeness"]["documents_status"]
                             if packet else "source_unavailable"),
        "matched_chunks": (packet["retrieval"]["matched_chunks"] if packet else None),
        "retrieved_documents": list(dict.fromkeys(
            item["document_id"] for item in result_hits)),
        "retrieved_passages": hits,
        "expected_document_in_top_three": (
            any(item["document_id"] == expected_doc for item in hits)
            if expected_doc and packet else None),
        "expected_passage_ranked_in_bm25_top_three": (
            any(item["citation_id"] == expected_citation for item in hits)
            if expected_citation and packet else None),
        "expected_passage_returned_by_source_only_ask": (
            any(item["citation_id"] == expected_citation for item in result_hits)
            if expected_citation and packet else None),
        "retrieval_clipped": (packet["completeness"]["documents_clipped"]
                              if packet else None),
        "grounding_risk": risk,
        "citation_resolution": [
            {"citation_id": item["citation_id"],
             "source_span_verified": item["original_source_span_verified"]}
            for item in hits
        ],
        "source_only_status": view["status"],
        "source_only_reason": view["reason"],
        "model_invoked": False,
        "graph_execution": "not_invoked",
        "answer_supported": None,
        "useful_to_answer": None,
        "failure_category": None,
        "native_inference_status": "NOT_RUN",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cases = read_questions(args.questions)
        index = documents.load_index(args.manifest, args.index, args.scope)
        corpus = {
            "manifest_sha256": documents.sha(documents.limited_file(
                args.manifest, documents.MAX_MANIFEST)),
            "index_sha256": index["index_sha256"],
        }
        bundle = ask.Bundle(args.manifest, args.index, args.scope)
        rows = [evaluate_case(bundle, args.manifest, args.index,
                              args.scope, corpus, case) for case in cases]
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")))
    except (ValueError, OSError, TypeError, KeyError, UnicodeError,
            json.JSONDecodeError) as error:
        parser.exit(2, "document-rag-evaluation: " + str(error) + "\n")


if __name__ == "__main__":
    main()
