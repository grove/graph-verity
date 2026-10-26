#!/usr/bin/env python3
"""Model-free #118 evidence -> inspectable sources and bounded extractive replay.

The default path never invokes inference or a graph operation. Only the original
#119 index verifier may admit document spans. A graph adapter is callable solely
with a receipt returned in-process by the independently approved Rust bridge;
there is intentionally no import-a-JSON-graph-receipt CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import document_rag as documents

VERSION = "kg-rag-evidence-v1"
CANDIDATE_VERSION = "kg-rag-extractive-v1"
MAX_EVIDENCE = 5
MAX_GRAPH = 8
MAX_CONTEXT = 16 * 1024
MAX_CANDIDATE = 8 * 1024
MAX_CLAIMS = 5
MAX_QUOTE = 384
LANGUAGES = {"en", "no", "nb", "nn"}
CITATION = re.compile(r"[dg]:[0-9a-f]{64}\Z")
GROUNDING_STOP_WORDS = {
    "what", "which", "where", "when", "who", "does", "did", "is", "are",
    "has", "have", "the", "a", "an", "to", "of", "for", "in", "and",
    "hva", "hvilken", "hvilket", "hvor", "når", "er", "har", "alle",
    "every", "all",
}
IDENTIFIER_VALUE = re.compile(r"\b[A-Z][A-Z0-9]*(?:[-._][A-Z0-9]+)+\b")
INSTRUCTION_ATTACK = re.compile(
    r"\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions?\b"
    r"[^.\n]{0,100}\bfabricat\w*\s+(?:a\s+)?citation\b", re.IGNORECASE)
LATENCY_VALUE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:ms|milliseconds?|s|seconds?|sekunder?)\b",
    re.IGNORECASE)


def require(test, description):
    if not test:
        raise ValueError(description)


def sha_json(data):
    return "sha256:" + hashlib.sha256(documents.serialized(data)).hexdigest()


def build_packet(index: dict, question: str, language: str, limit: int = 3) -> dict:
    """Construct from the canonical source-verified #119 index, not loose hit JSON."""
    require(language in LANGUAGES, "Unsupported question language")
    require(type(limit) is int and 1 <= limit <= MAX_EVIDENCE, "Invalid evidence limit")
    result = documents.search_index(index, question, limit)
    require(result["index_sha256"] == index["index_sha256"] and
            result["scope"] == index["payload"]["scope"], "Index mismatch")
    evidence, bytes_used = [], 0
    for hit in result["hits"]:
        cited = documents.cite(index, hit["citation_id"])["evidence"]
        require(all(hit.get(k) == v for k, v in cited.items()),
                "Search passage differs from verified citation")
        entry = {"type": "document_span", **cited}
        size = len(documents.serialized(entry))
        if bytes_used + size > MAX_CONTEXT:
            break
        evidence.append(entry)
        bytes_used += size
    return {
        "version": VERSION, "question": question, "language": language,
        "document_scope": index["payload"]["scope"],
        "retrieval": {
            "kind": result["retriever"],
            "index_sha256": result["index_sha256"],
            "manifest_sha256": index["payload"]["manifest_sha256"],
            "matched_chunks": result["matches"],
        },
        "document_evidence": evidence, "graph_evidence": [],
        "completeness": {
            "documents_status": "matches" if evidence else "no_match",
            "documents_clipped": bool(result["truncated"] or
                                       len(evidence) < len(result["hits"])),
            "graph_status": "not_invoked",
            "graph_rows_clipped": None,
            "graph_evidence_clipped": None,
            "conflicts": "not_assessed",
        },
        "generation": {"status": "not_authorized", "model_invoked": False},
        "limits": {
            "source_truth": "not_established",
            "intent_correctness": "not_assessed",
            "retrieval_is_exhaustive": False,
            "claim_entailment": "not_proven_by_citation",
        },
    }


def retrieve(manifest: Path, index_file: Path, scope: str, question: str,
             language: str, limit: int = 3) -> dict:
    # Rebuild canonical snippets against actual permitted source bytes each request.
    index = documents.load_index(manifest, index_file, scope)
    packet = build_packet(index, question, language, limit)
    # Detect an edit to the original operator bundle during retrieval.
    fresh = documents.load_index(manifest, index_file, scope)
    require(fresh == index, "Operator source or index changed during retrieval")
    return packet


def _rdf_term(term: dict):
    require(type(term) is dict and term.get("kind") in
            {"iri", "blank_node", "literal"}, "Invalid original RDF term")
    if term["kind"] in ("iri", "blank_node"):
        require(set(term) == {"kind", "value"}, "Invalid RDF resource structure")
    else:
        require(set(term) == {"kind", "value", "datatype", "language"} and
                isinstance(term["datatype"], str) and
                isinstance(term["language"], (str, type(None))),
                "Invalid typed RDF literal")
    require(isinstance(term["value"], str) and
            0 < len(term["value"].encode("utf-8")) <= 2048,
            "Unbounded RDF term")


def _graph_fact(statement: dict, result: dict, config: dict, approval_id: str):
    require(type(statement) is dict and set(statement) ==
            {"subject", "predicate", "object", "source_graph"},
            "Unexpected graph evidence structure")
    for key in ("subject", "predicate", "object", "source_graph"):
        _rdf_term(statement[key])
    graph_term = statement["source_graph"]
    require(graph_term["kind"] == "iri", "Missing original named graph")
    graph = graph_term["value"]
    require(graph in result["scope"] and graph in config, "Unapproved graph")
    require(statement["predicate"]["kind"] == "iri", "Invalid original predicate")
    metadata = config[graph]
    require(isinstance(metadata.get("license"), str) and
            metadata["license"] and
            isinstance(metadata.get("source_revision"), str) and
            metadata["source_revision"], "Missing graph source provenance")
    stable = {
        "graph": graph, "snapshot": result["snapshot_id"],
        "subject": statement["subject"], "predicate": statement["predicate"],
        "object": statement["object"], "source_revision": metadata["source_revision"],
    }
    citation = "g:" + hashlib.sha256(documents.serialized(stable)).hexdigest()
    return {
        "type": "original_rdf_triple", "citation_id": citation,
        "graph": graph, "snapshot": result["snapshot_id"],
        "subject": statement["subject"], "predicate": statement["predicate"],
        "object": statement["object"], "source_revision": metadata["source_revision"],
        "license": metadata["license"],
        "approved_operation": approval_id,
    }


def with_confirmed_graph(packet: dict, receipt: dict, bundle) -> dict:
    """Trusted in-process adapter, called *after* the existing exact approval.

    This is NOT a verifier for arbitrary exported JSON. Only the live bridge's
    immediate result may be passed by its trusted caller; no CLI accepts receipts.
    """
    require(packet["version"] == VERSION and
            not packet["graph_evidence"] and
            packet["completeness"]["graph_status"] == "not_invoked",
            "Graph evidence must be added once, after approval")
    bundle.current()
    require(receipt.get("status") == "executed", "Graph was not executed")
    confirmation = receipt["provenance"]["operator_confirmation"]
    require(confirmation["decision"] == "approve" and
            confirmation["single_use"] is True, "No independent exact approval")
    outcome = receipt["outcome"]
    result = outcome["result"]
    approval_id = confirmation["approval_id"]
    require(outcome["status"] == "executed" and
            isinstance(approval_id, str) and len(approval_id) >= 32 and
            outcome["approval_id"] == approval_id and
            result["evidence_verification"] == "verified_against_snapshot",
            "Missing authoritative Rust execution evidence")
    chosen = receipt["provenance"]["selected_operation"]
    steps = chosen["template"]["steps"]
    require(len(steps) == 1 and steps[0]["direction"] == "forward" and
            chosen["template"]["kind"] == "follow_path" and
            result["snapshot_id"] == chosen["snapshot_id"] == bundle.snapshot and
            result["scope"] == chosen["scope"] == [steps[0]["graph"]] and
            result["scope"][0] in bundle.scope, "Graph operation or snapshot mismatch")
    config = json.loads(Path(bundle.common[4]).read_bytes())["graphs"]
    require(receipt["sources"] == {g: config[g] for g in result["scope"]},
            "Graph source metadata differs from the trusted operator bundle")
    require(type(result["complete_within_scope"]) is bool and
            type(result["evidence_complete_for_returned_rows"]) is bool,
            "Unknown execution completeness")
    original = result["evidence"]
    require(type(original) is list, "Missing Rust statement witnesses")
    accepted = []
    for answer in receipt["answers"]:
        value = answer["value"]
        _rdf_term(value)
        expected = {
            "subject": {"kind": "iri", "value": chosen["template"]["start"]},
            "predicate": {"kind": "iri", "value": steps[0]["predicate"]},
            "object": value,
            "source_graph": {"kind": "iri", "value": steps[0]["graph"]},
        }
        witnesses = answer["source_triples"]
        require(type(witnesses) is list and
                all(w == expected and w in original for w in witnesses),
                "Answer witnesses differ from original approved RDF statements")
        # If no original witness was returned, never turn a result binding
        # into a generated RDF factual citation.
        for witness in witnesses:
            item = _graph_fact(witness, result, config, approval_id)
            if item["citation_id"] not in {x["citation_id"] for x in accepted}:
                accepted.append(item)
    require(len(accepted) <= 200, "Unbounded graph receipt")
    bundle.current()
    bounded = accepted[:MAX_GRAPH]
    upgraded = {**packet, "graph_evidence": bounded}
    upgraded["completeness"] = {
        **packet["completeness"],
        "graph_status": ("approved_executed" if bounded else "approved_no_witness"),
        "graph_rows_clipped": not result["complete_within_scope"],
        "graph_evidence_clipped": (not result["evidence_complete_for_returned_rows"] or
                                    len(accepted) > MAX_GRAPH or
                                    any(not a["source_triples"] for a in receipt["answers"])),
    }
    upgraded["limits"] = {**packet["limits"],
                         "intent_correctness": "not_assessed_after_manual_approval"}
    # Only original witnessed RDF statements; SHACL/GNN suggestions never enter.
    return upgraded


def available_citations(packet: dict) -> dict:
    require(packet.get("version") == VERSION and
            isinstance(packet.get("document_evidence"), list) and
            isinstance(packet.get("graph_evidence"), list), "Bad evidence packet")
    items = {}
    for evidence, kind in (("document_evidence", "document_span"),
                           ("graph_evidence", "original_rdf_triple")):
        for item in packet[evidence]:
            cid = item["citation_id"]
            require(item.get("type") == kind and isinstance(cid, str) and
                    CITATION.fullmatch(cid) and cid not in items,
                    "Citation not unique or source typed incorrectly")
            items[cid] = item
    return items


def _question_terms(value: str) -> set[str]:
    terms = set()
    for word in documents.tokens(value):
        if word in GROUNDING_STOP_WORDS:
            continue
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
            word = word[:-1]
        terms.add(word)
    return terms


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(
        r"(?<=[!?])\s+|(?<=\.)\s+(?=[A-ZÆØÅ])|\n", text)
            if part.strip()]


def _matching_passages(packet: dict, text: str | None = None) -> list[dict]:
    terms = _question_terms(packet["question"])
    if not terms:
        return []
    passages = packet["document_evidence"]
    if text is not None:
        passages = [{"text": text}]
    return [item for item in passages if any(
        terms <= _question_terms(sentence) for sentence in _sentences(item["text"]))]


def _identifier_records(packet: dict) -> list[tuple[str, str]]:
    records = []
    for item in packet["document_evidence"]:
        for sentence in _sentences(item["text"]):
            english = re.search(
                r"\b(?P<subject>(?:[A-Za-z0-9][A-Za-z0-9_-]*\s+){1,2}trial)\b"
                r"[^.!?]{0,80}\b(?:identifier|id)\b[^.!?]{0,32}"
                r"\b(?P<value>[A-Z][A-Z0-9]*(?:[-._][A-Z0-9]+)+)\b",
                sentence, re.IGNORECASE)
            norwegian = re.search(
                r"\b(?P<subject>[A-Za-z0-9][A-Za-z0-9_-]*-forsøket)\b"
                r"[^.!?]{0,80}\bidentifikator(?:en)?\b[^.!?]{0,32}"
                r"\b(?P<value>[A-Z][A-Z0-9]*(?:[-._][A-Z0-9]+)+)\b",
                sentence, re.IGNORECASE)
            match = english or norwegian
            if match:
                subject = match["subject"].casefold()
                subject = re.sub(r"^(?:the\s+)", "", subject)
                if subject.endswith("-forsøket"):
                    subject = subject[:-len("-forsøket")] + " trial"
                records.append((subject, match["value"].casefold()))
    return records


# shortcut: finite surface rules do not prove entailment, upgrade only with independent relevance evidence.
def assess_grounding_risk(packet: dict) -> dict:
    """Apply narrow source-packet checks; CLEAR is not semantic entailment."""
    question = packet["question"]
    text = "\n".join(item["text"] for item in packet["document_evidence"])
    has_untrusted_instruction = bool(INSTRUCTION_ATTACK.search(text))
    risk = {
        "classification": "UNDETERMINED",
        "reason": "unable_to_establish_relevance",
        "detail": "question_or_evidence_outside_supported_rules",
        "untrusted_instruction_present": has_untrusted_instruction,
    }
    lower = question.casefold()
    if re.search(r"\b(?:count|how many|number of|total number)\b", lower) or re.search(
            r"\b(?:every|all|each)\b[^?]{0,48}"
            r"\b(?:documents?|files?|sources?|records?|trials?|passages?|claims?)\b|"
            r"\b(?:documents?|files?|sources?|records?|trials?|passages?|claims?)\b"
            r"[^?]{0,48}\b(?:every|all|each)\b", lower) or re.search(
            r"\b(?:oppsummer|tell|hvor mange|alle dokumentene?|alle kildene|"
            r"samtlige dokumenter|samlet konklusjon)\b", lower):
        risk.update(classification="UNSUPPORTED_QUESTION",
                    reason="unsupported_answer_type", detail="count_or_multi_document_synthesis")
        return risk
    targeted_instruction = bool(re.search(
        r"\b(?:note|instruct\w*|instruction\w*|citation|assistant|prompt)\b",
        lower))
    terms = _question_terms(question)
    targeted_instruction |= has_untrusted_instruction and any(
        INSTRUCTION_ATTACK.search(sentence) and
        terms <= _question_terms(sentence)
        for item in packet["document_evidence"]
        for sentence in _sentences(item["text"]))
    if has_untrusted_instruction and targeted_instruction:
        risk.update(classification="UNTRUSTED_INSTRUCTION_RISK",
                    reason="untrusted_instructions",
                    detail="question_or_matching_passage_targets_embedded_instruction")
        return risk
    if (re.search(r"\b(?:startup|start-up)\b", lower) and
            re.search(r"\blatency\b", lower)):
        measured = any(
            re.search(r"\b(?:startup|start-up)\b", sentence, re.IGNORECASE) and
            re.search(r"\blatency\b", sentence, re.IGNORECASE) and
            LATENCY_VALUE.search(sentence)
            for item in packet["document_evidence"]
            for sentence in _sentences(item["text"]))
        if not measured:
            risk.update(classification="INSUFFICIENT_EVIDENCE",
                        reason="insufficient_source_support",
                        detail="no_startup_latency_value_in_retrieved_passages")
            return risk
    identifier_question = bool(re.search(
        r"\b(?:what|which)\b[^?]{0,60}\b(?:identifier|id)\b|"
        r"\b(?:identifier|id)\b[^?]{0,60}\b(?:does|has|have)\b|"
        r"\b(?:hva|hvilken)\b[^?]{0,60}\bidentifikator(?:en)?\b",
        lower))
    if identifier_question:
        records = _identifier_records(packet)
        subject_match = re.search(
            r"\b((?:[A-Za-z0-9][A-Za-z0-9_-]*\s+){1,2}trial)\b",
            question, re.IGNORECASE)
        if subject_match is None:
            subject_terms = _question_terms(question) - {
                "identifier", "id", "identifikator", "identifikatoren",
            }
            if not subject_terms and IDENTIFIER_VALUE.search(text):
                risk.update(classification="AMBIGUOUS",
                            reason="ambiguous_question",
                            detail="identifier_question_omits_subject")
                return risk
            if subject_terms:
                risk.update(detail="identifier_subject_outside_supported_rule")
                return risk
            risk.update(classification="INSUFFICIENT_EVIDENCE",
                        reason="insufficient_source_support",
                        detail="no_identifier_value_in_retrieved_passages")
            return risk
        subject = re.sub(r"^(?:the\s+)", "", subject_match[1].casefold())
        values = {value for found_subject, value in records if found_subject == subject}
        if len(values) > 1:
            risk.update(classification="CONFLICTING_EVIDENCE",
                        reason="conflicting_evidence",
                        detail="same_trial_identifier_values_disagree")
            return risk
        if not values:
            risk.update(classification="INSUFFICIENT_EVIDENCE",
                        reason="insufficient_source_support",
                        detail="no_subject_matched_identifier_value_in_retrieved_passages")
            return risk
        if packet["completeness"]["documents_clipped"]:
            risk.update(reason="retrieval_coverage_incomplete",
                        detail="retrieval_coverage_incomplete")
            return risk
        if _matching_passages(packet):
            risk.update(classification="CLEAR_SUPPORTED_CASE",
                        reason="source_quote_candidate",
                        detail="identifier_family_exact_terms_present")
            return risk
        return risk
    if not re.match(r"^(?:what|which|where|when|who|hva|hvor|når|hvilken|hvilket)\b",
                    lower):
        return risk
    if packet["completeness"]["documents_clipped"]:
        risk.update(reason="retrieval_coverage_incomplete",
                    detail="retrieval_coverage_incomplete")
        return risk
    if _matching_passages(packet):
        risk.update(classification="CLEAR_SUPPORTED_CASE",
                    reason="source_quote_candidate",
                    detail="direct_question_terms_share_one_retrieved_sentence")
    return risk


def quote_matches_question(packet: dict, text: str) -> bool:
    """Require every meaningful question term in the one quoted answer sentence."""
    return len(_sentences(text)) == 1 and bool(_matching_passages(packet, text))


def generation_passages(packet: dict) -> list[dict]:
    """Use exact relevant sentences from retrieved spans; keep the full packet for fallback."""
    terms = _question_terms(packet["question"])
    selected = []
    for item in packet["document_evidence"]:
        sentences = [sentence for sentence in _sentences(item["text"])
                     if terms and terms <= _question_terms(sentence)]
        if sentences:
            selected.append({**item, "text": " ".join(sentences)})
    return selected


def check_extractive(packet: dict, candidate: dict) -> dict:
    """Strict saved-output replay: source quotes/terms only; never entails prose."""
    try:
        risk = None
        if packet.get("document_evidence") and packet.get("graph_evidence") == []:
            risk = assess_grounding_risk(packet)
            if risk["classification"] != "CLEAR_SUPPORTED_CASE":
                return {**fallback(packet, reason=risk["reason"]),
                        "grounding_risk": risk}
        require(type(candidate) is dict and set(candidate) ==
                {"version", "language", "claims"}, "Unrecognized candidate structure")
        require(candidate["version"] == CANDIDATE_VERSION and
                candidate["language"] == packet["language"], "Candidate protocol mismatch")
        claims = candidate["claims"]
        require(type(claims) is list and 1 <= len(claims) <= MAX_CLAIMS,
                "Unsupported claim count")
        if risk is not None:
            require(len(claims) == 1,
                    "Only one direct document quote is supported")
        if len(documents.serialized(candidate)) > MAX_CANDIDATE:
            raise ValueError("Candidate exceeds byte budget")
        sources = available_citations(packet)
        approved = []
        for claim in claims:
            require(type(claim) is dict and set(claim) == {"kind", "text", "citation_id"},
                    "Unrecognized claim structure")
            cid, text = claim["citation_id"], claim["text"]
            require(isinstance(cid, str) and cid in sources and
                    isinstance(text, str) and text.strip() == text and
                    1 <= len(text) <= MAX_QUOTE, "Unsupported citation or text")
            source = sources[cid]
            if claim["kind"] == "verbatim_document_quote":
                require(source["type"] == "document_span" and text in source["text"],
                        "Claim is not an exact source excerpt")
                if risk is not None:
                    require(quote_matches_question(packet, text),
                            "Quote lacks direct lexical question support")
            elif claim["kind"] == "verbatim_rdf_object":
                require(source["type"] == "original_rdf_triple" and
                        text == source["object"]["value"],
                        "Claim does not match the original typed RDF object")
            else:
                raise ValueError("Only exact source quotations/values are supported")
            approved.append({"text": text, "citation_id": cid,
                             "kind": claim["kind"]})
        return {
            "status": "checked_extractive_replay",
            "model_invoked": False,
            "claims": approved,
            "entailment": "not_proven; only exact quotations and citation IDs checked",
            "limitations": packet["completeness"],
            **({"grounding_risk": risk} if risk is not None else {}),
        }
    except (ValueError, TypeError, KeyError, UnicodeError):
        return fallback(packet, reason="candidate_rejected")


def fallback(packet: dict, reason: str = "generation_not_authorized") -> dict:
    """Never manufacture a fluent answer when the generator is absent or invalid."""
    sources = available_citations(packet)
    entries = []
    for item in sources.values():
        excerpt = (item["text"] if item["type"] == "document_span"
                   else item["object"]["value"])
        entries.append({
            "citation_id": item["citation_id"], "kind": item["type"],
            "source": item["source"] if item["type"] == "document_span"
                      else item["graph"],
            "excerpt": excerpt,
        })
    return {
        "status": "source_only" if entries else "no_evidence",
        "reason": reason, "answer": None, "model_invoked": False,
        "evidence": entries,
        "message": (
            "Verifiserte kildeutdrag, ikke et generert svar. Ingen slutning om fravær."
            if packet["language"] != "en" else
            "Verified source excerpts, not a generated answer. No claim of absence."
        ) if entries else (
            "Ingen leksikalske treff i valgt kildeomfang; ikke bevis for fravær."
            if packet["language"] != "en" else
            "No lexical matches in selected sources; this does not prove absence."
        ),
        "completeness": packet["completeness"],
        "entailment": "not_assessed",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--language", choices=sorted(LANGUAGES), default="en")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--saved-candidate", type=Path,
                        help="Explicit model-free fixture replay; NEVER live generation")
    args = parser.parse_args(argv)
    try:
        packet = retrieve(args.manifest, args.index, args.scope,
                          args.question, args.language, args.limit)
        if args.saved_candidate:
            candidate = json.loads(documents.limited_file(args.saved_candidate,
                                                           MAX_CANDIDATE))
            view = check_extractive(packet, candidate)
        else:
            view = fallback(packet)
        print(json.dumps({"packet": packet, "view": view},
                         ensure_ascii=False, sort_keys=True, indent=2))
    except (ValueError, OSError, UnicodeError, TypeError, KeyError,
            json.JSONDecodeError) as err:
        parser.exit(2, "grounded-rag: " + str(err) + "\n")


if __name__ == "__main__":
    main()
