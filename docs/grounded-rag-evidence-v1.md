# #118 — Grounded RAG evidence and source-only Ask v1

**Status:** First implementation slice, model-free. This is **not** a completed locally generated answer system. No model was downloaded, registered, loaded or invoked. Keep **INCONCLUSIVE_REVISE**.

## What works

A Norwegian or English question is searched against the real, operator-approved Markdown/text documents indexed by merged #119. A small versioned evidence packet carries original source spans and can be displayed without generating an answer. Citation IDs resolve to original bytes through #119's canonical, source-hash-verified index. The default is **source-only**, not a natural language answer and not a statement of semantic entailment.

The new tools/grounded_rag.py provides:

- retrieve / build_packet: permitted source documents, question, language, scope, source hashes, license, UTF-8 offsets, retriever identity and clipping/no-match status.
- available_citations / check_extractive: bounded citation-ID resolution with an exact source-quote / original RDF-object-only saved-candidate contract. No arbitrary paraphrases are accepted as proved.
- fallback: explicit original passage display with no-evidence and clipping states. No generic invented answer.
- with_confirmed_graph: a narrow *trusted in-process adapter* for receipts returned directly by the existing Assisted Ask Rust/approval bridge. Checks approved single-use operation identity, original witnessed triples, named graph, source metadata, snapshot and independent row/evidence clipping. It is **not a JSON-receipt import route**; it does not initiate or approve graph queries.

The packet version is kg-rag-evidence-v1. Document evidence has type document_span; actual approved RDF evidence has type original_rdf_triple with a separate g: citation. Missing graph execution is graph_status: not_invoked. SHACL guidance and GNN predictions never become source facts.

## Run with real authorized documents

First build a #119 index following [document-rag-v1.md](document-rag-v1.md). Keep original documents, manifest and index in OS-protected private directories.

    python3 tools/grounded_rag.py \
      --manifest /path/to/collection/sources.json \
      --index /path/to/private/document-index.json \
      --scope public --question "Hva er søknadsfristen?" --language nb --limit 3

The response includes a packet with original document spans, and a view with status source_only, answer null, source excerpts and citation IDs. This is not a generated RAG answer.

For a manually prepared saved extraction, pass --saved-candidate /path/to/candidate.json. Example (replace citation ID and quote with actual returned values):

    {
      "version": "kg-rag-extractive-v1",
      "language": "nb",
      "claims": [{
        "kind": "verbatim_document_quote",
        "text": "Søknadsfristen er 1. mai.",
        "citation_id": "d:<actual-verified-citation>"
      }]
    }

Saved replay never invokes a model, cannot prove semantic entailment and falls back to sources if invalid. Only verbatim_document_quote and verbatim_rdf_object are allowed; the latter needs actual independently approved source RDF witnesses.

## Safety and tests

- Document scope and original bytes are checked via document_rag.load_index() on every request. The source manifest is a trusted operator authorization input, not filesystem authentication.
- Unselected documents are not read. Keep private sources and the index outside the repo.
- Source text can contain prompt injection: this model-free flow treats it as inert data.
- Bounds: up to five document passages, eight approved RDF witnesses, five saved extraction claims, with citation/claim byte limits.
- Only an in-process trusted caller holding a fresh actual approved Rust bridge result should invoke with_confirmed_graph(). Tests use a simulated receipt solely to check this contract; they are **not live graph execution evidence**.
- Unsupported or unapproved graph plans yield no graph evidence; doc clipping, graph row clipping and triple clipping are separate. Semantic conflict and entailment remain unassessed.
- No inference, embeddings, GNN training, SHACL-derived facts, external services, historical code resealing or authorization reuse.

Model-free regression:

    python3 -m unittest discover -s tools -p test_grounded_rag.py -v

Existing CI auto-discovers tools/test_grounded_rag.py. Tests cover NO/EN document retrieval, exact UTF-8 citations, private scope isolation, stale index, no match, hostile source text, unsupported claims and fake citations, and simulated authorized RDF receipts with independent completeness indicators.

## Before #118 can be closed

1. Wire the trusted approved-graph receipt adapter into the existing Rust-backed path, preserving one exact user approval and exposing citations in a single local Ask UI.
2. Register and freeze a small local generator and source prompt/tokenizer/runtime/host controls. Live inference requires **separate explicit owner authorization**.
3. Demonstrate actual local NO/EN generated answers with citation and factual support checks, plus deterministic fallback. Independently evaluated human quality remains open.

**Do not close #118 on this model-free PR.** The full issue requires actual local generation. Keep INCONCLUSIVE_REVISE.
