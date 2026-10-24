# Graph Verity — local, verifiable Knowledge Graph RAG

**Status:** Phase 2 architecture proposal, **not yet built**. **Decision:** `INCONCLUSIVE_REVISE`.  
**Goal:** Ask a question in Norwegian or English and receive a useful, locally **generated** answer, backed by original RDF triples from an authorized knowledge graph.  
**Design principle:** *Use language and graph structure to find the right evidence; use Rust to retrieve it; use a local model to explain only that evidence.*

Tracks: [#71 — Phase 2](https://github.com/grove/graph-verity/issues/71), [#114 — text retrieval](https://github.com/grove/graph-verity/issues/114), [#117 — R-GCN/CompGCN](https://github.com/grove/graph-verity/issues/117), [#115 — SHACL/graph operations](https://github.com/grove/graph-verity/issues/115), [#118 — evidence-grounded generation](https://github.com/grove/graph-verity/issues/118). Reuse the [Phase 2 roadmap](../phase-2-natural-language-ask.md) and [Assisted Ask v1](../assisted-ask-v1.md); do not introduce a second planner or executor.

## 1. Product: what counts as RAG?

**Retrieval-Augmented Generation = RETRIEVE → AUGMENT → GENERATE.** A search result or a formatted RDF table is *not yet RAG*. The product must ultimately use **actual retrieved graph facts as the factual context for a local generative model** and return a natural, cited answer.

Example: “Hva er de offisielle nettsidene til Universitetet i Tromsø?”

1. **Discover:** Match the university and official-website predicate using exact/semantic text plus existing graph relationships. Present a clear interpretation, with alternatives when ambiguous.
2. **Confirm and query:** The user explicitly approves a specific entity, predicate, **direction**, named graph and scope. Rust constructs/revalidates the supported plan and Oxigraph retrieves real stored values and their source triples.
3. **Augment:** Build a small, typed **evidence packet**: returned RDF terms, supporting triples, source IDs, provenance and completeness limits. Do **not** substitute top-k suggested vocabulary, SHACL expectations or GNN-predicted edges for factual results.
4. **Generate:** A pinned local model uses that packet to write a concise Norwegian/English answer with citations to its exact source statements.
5. **Check and show:** Validate citation IDs, quoted identifiers/values and the permitted answer family; display answer + expandable original evidence. If generation is absent, unfaithful or too expensive, show a truthful **deterministic result fallback**, not invented prose.

This should feel like **one simple Ask screen**, not six research tools. The first demo can be the current authorized university/P856-P1448 one-hop scope; it must demonstrate actual model generation before being called a **completed RAG slice**. General natural-language interpretation is still unproven: the user confirms the proposed operation, not the original question's truth.

**Hypothesis, not marketing claim:** Graph paths, typed relationships, SHACL guidance and triple-level citations may help outperform plain document-chunk RAG in correctness, relevance and explainability. Test that against a **simple text-RAG baseline on the same RDF source**, not just against earlier Graph Verity versions.

## 2. One coherent system

~~~mermaid
flowchart TD
    Q["NO/EN question"] --> T["BM25 exact search + optional EmbeddingGemma"]
    Q --> G["Witnessed directed RDF graph neighborhoods"]
    G --> H["Optional R-GCN / CompGCN reranking (research)"]
    T --> C["Authorized entity / predicate / path candidates"]
    G --> C
    H --> C
    S["Trusted SHACL shapes and original predicate metadata"] --> C
    C --> I["User sees interpreted operation + uncertainty"]
    I --> P["Distinct explicit approval of Rust preview"]
    P --> X["Read-only Oxigraph retrieves actual RDF facts"]
    X --> E["EVIDENCE: typed bindings, source triples, graph and snapshot"]
    E --> A["AUGMENT: bounded local-model context"]
    A --> L["GENERATE: short cited answer"]
    L --> V["Check claims / citations / completeness"]
    V --> Y["Answer + original evidence"]
    V --> Z["On failure: deterministic values or clarification"]
~~~

The **two retrieval stages must remain distinct**:

- **Vocabulary/structure discovery:** top-k entities, predicates and paths to *suggest*. BM25/EmbeddingGemma, actual adjacency and optional GNNs may rank them. Neither a high score nor an apparently valid SHACL path proves what the user meant.
- **Authoritative fact retrieval:** only the **exact approved**, Rust-validated bounded read-only Oxigraph query can determine which RDF statements are recorded. The resulting source triples become the generator's factual input. A graph source witness is evidence *within its snapshot*, not proof of real-world truth.

The local LLM may eventually help propose interpretations, but never selects query authority, generates raw executable SPARQL, creates RDF triples, overrides source facts or auto-approves. Start with the existing explicit choices and independently measured supported question families.

## 3. Simple components with clear boundaries

| Component | Job | Keep it honest |
| --- | --- | --- |
| **BM25** | Exact identifiers, labels, lexical matches | Current Find default; preserve first-rank exact IDs and no-match behavior |
| **EmbeddingGemma 2** | Bilingual semantic/paraphrase retrieval of original graph vocabulary | Research variant; retrieval score is not calibrated intent confidence, and earlier hybrid no-match regressions remain |
| **Directed neighborhoods** | Retrieve *witnessed* incoming/outgoing RDF edges and bounded paths | Mandatory simple structural baseline before training a GNN; preserve source/graph/direction |
| **R-GCN / CompGCN** | Learn relational entity and entity+predicate representations, potentially rerank witnessed candidates/paths | **First-class original motivation (#117)**; trained models are optional. Predicted links are hypotheses, never original RDF facts |
| **SHACL + property definitions** | Give trusted type, property-path, node-kind and constraint guidance where real shapes/metadata exist | Shape provenance matters; SHACL cannot certify user intent, source completeness or world truth |
| **Rust + Oxigraph** | Authoritative plan, separate single-use approval, scoped execution and evidence | Reuse existing Confirmed/Assisted Ask; no separate engine, unapproved writes or raw SPARQL |
| **Local generator + checker** | Turn **returned facts** into useful natural prose with resolvable citations | **Required end-state (#118)**, separately authorized inference; deterministic fallback must remain available |

**Design for efficiency:** one local app/loopback entry point, reuse pinned indexes and Rust engine, and **don't load every model for every question**. Route simple exact lookups to cheap retrieval; activate embeddings/GNNs only when a measured benefit justifies them. Generate only after a valid approved fact query; avoid giving a large language model a whole graph dump. Profile total model+process RSS, startup, warm latency and rebuild cost on the M1 Pro / 32 GiB instead of promising speeds.

## 4. Shared source, candidate and answer contracts

**Candidate packet: advisory only.** Reuse the existing graph-qualified vocabulary packet rather than introducing new parallel frameworks. Preserve original question/language, authorized graph/snapshot/policy/index revision, role, original entity/predicate IRI, labels/descriptions with language and source/license, exact direction/path source witnesses, and optional *separately labelled* BM25/dense/adjacency/R-GCN/CompGCN ranks. Record ambiguity, missing vocabulary, unsupported requests, no-match and clipping as distinct states. Filter **scope and permissions before indexing or retrieval**, including structural embeddings. Snapshot or encoder mismatch must invalidate a learned index; GNN-inferred edges never become source triples.

**SHACL guidance: narrow and explicit.** Accept only source-published or separately operator-authorized shapes with shape graph, license, revision/hash, RDF graph mapping and disclosed author. If unavailable, use source-authored predicate definitions and witnessed paths, not fabricated shape authority. A small documented SHACL 2017 property-shape subset (`sh:path`, supported `sh:inversePath`, `sh:datatype`, `sh:class`, `sh:nodeKind` and bounded cardinality annotations) is sufficient initially. Any demo shapes must be labelled operator-authored and remain separate from original source RDF. Do not silently treat SHACL conformance as proven or interpret cardinality as global closed-world completeness.

**Evidence packet: the critical RAG boundary.** Build it **after approved execution**, from actual Oxigraph results. The format should be small, versioned and hash/snapshot-bound. A minimal illustrative schema (not an actual receipt) is:

~~~json
{
  "version": "kg-rag-evidence-v1",
  "question": "<original NO/EN text>",
  "language": "nb",
  "confirmed_operation": "<exact Rust preview identity>",
  "scope": ["<authorized named graph>"],
  "snapshot_id": "<actual pinned snapshot>",
  "source": {"revision": "<source revision>", "license": "<license>"},
  "bindings": [{
    "id": "r1",
    "term": {"kind": "iri", "value": "<original RDF IRI>"},
    "supporting_citation_ids": ["t1"]
  }],
  "citations": [{
    "id": "t1",
    "subject": "<original subject IRI>",
    "predicate": "<original predicate IRI>",
    "object": "<original RDF term with datatype/language if literal>",
    "graph": "<original named graph>",
    "source_witness": "<verifiable source triple reference>"
  }],
  "completeness": {"rows_clipped": false, "evidence_clipped": false},
  "limits": "<actual applied row/evidence/time budgets>"
}
~~~

Actual schema must preserve lexical values, language tags, datatypes, licenses and **independent** row/evidence completeness. Generated citations are IDs referencing *these original triples*, not URLs or pseudo-sources invented by a model. Give the model a **bounded, escaped evidence view**; treat question text, labels and RDF literals as untrusted content, never higher-priority instructions. If a query asked for a language filter/count/reverse path that was not implemented, the unfiltered result must **never** be passed off as answering it.

**Generation and checking:** Prompt a separately authorized local model to produce a short NO/EN sentence grounded in these bindings with inline citation IDs and explicit snapshot/completeness caveats. Verify every citation ID resolves to permitted returned triples; quoted URLs/IRIs, numbers, languages, predicates and supported simple answer clauses match the corresponding binding and approved operation. Reject invented entities, unsupported aggregation, reversed claims, false graph provenance and “all/none/only” over incomplete results. **A valid citation ID alone does not prove semantic entailment**: the checker covers declared answer families only, so measure claim faithfulness independently and fail closed outside coverage. When a model or checker fails, show deterministic RDF values and say why a generated answer is unavailable.

**Authority:** Original RDF facts and source triples are authoritative *for the authorized snapshot*. SHACL shapes are separately provenance-checked metadata. BM25, EmbeddingGemma, R-GCN/CompGCN and LLM output are **non-authoritative suggestions**. Only the user-confirmed, scope-validated, expiring single-use Rust query can retrieve answer facts.

## 5. Prove value against ordinary RAG

Compare the **same licensed graph, question set, local machine and comparable generator**; isolate where different retrieval context sizes or answering models would confound attribution.

| Comparison | Question answered |
| --- | --- |
| **Deterministic RDF display** vs **grounded local generator** | Does generation actually improve understanding/usefulness without making up facts? |
| **Simple text-chunk RAG** over the same RDF-derived, source-tagged facts vs KG-RAG | Does structure + graph query + SHACL actually improve answers over ordinary RAG? |
| BM25 vs EmbeddingGemma/hybrid, same role/graph/scope | Do NO/EN paraphrases improve without breaking exact-ID or no-match behavior? |
| Source-witnessed adjacency vs R-GCN vs CompGCN | Does learned structural retrieval offer incremental path/entity/predicate ranking value over cheap traversal? |
| With/without trusted SHACL guidance | Does schema context reduce wrong relationships/directions, without excluding valid facts? |

Freeze evaluations before new inference/training. Separate **candidate recall**, correct entity/predicate/direction, successful approved query, exact returned bindings, **answer-level support**, real-world truth (not established by RDF), false confidence, appropriate clarification/abstention, source-citation validity, NO/EN fluency, comprehension, cold/warm latency and full-process RSS. Existing agent-authored development references are not independently human verified; zero human observations means **human comprehension remains unmeasured**. Test adverse cases: wrong direction, absent facts, clipping, private graph labels, stale SHACL/index, predicted but unobserved links, no-match, unsupported filters and malicious literal text.

**Decision:** Adopt each extra component **only if it beats a simpler baseline on the defined user task within the local resource budget**. In particular, GNNs need measured retrieval lift over direct neighborhoods; a full LLM must improve user-facing wording while maintaining source faithfulness. An impressive graph model score is not a factual RAG answer.

## 6. Small implementation roadmap

| Track | Delivery | Role in end-to-end RAG |
| --- | --- | --- |
| **#114** | BM25 + opt-in EmbeddingGemma entity/predicate suggestions, exact/no-match guards | Helps interpret the question |
| **#117 (parallel)** | Pinned graph adequacy + direct-adjacency baseline, then separately approved R-GCN/CompGCN comparison | Optional structural retrieval improvement; not a release blocker |
| **#115** | Trusted SHACL guidance, direction/scope constraints and Rust-approved RDF facts | Produces the **actual evidence** |
| **#118** | Typed evidence packet, citation/claim checks, fallback; then separately authorized native local answer generation | **Completes retrieval → augmentation → generation** |
| **Integration/release decision** | One clean NO/EN question-to-cited-answer journey; compare with simple text RAG and measure quality/cost | Ship the **smallest useful** local stack |

The first product slice should reuse the existing narrow assisted query, prove the **full pipeline with one real local generated answer** under a separately approved and measured inference gate, then extend coverage based on what users actually ask. #117 remains a first-class experiment in parallel, **not an excuse to delay a simple working RAG demo**.

## 7. Present truth and safety boundaries

**Implemented:** local graph catalog, BM25 Find, Rust/Oxigraph typed read-only query+source evidence, exact approval, narrow model-free Assisted Ask v1. **Evaluated but not product-integrated:** EmbeddingGemma 2 (paraphrase gains alongside false-candidate/exact-rank regressions). **Planned/unverified:** SHACL-guided serving, R-GCN/CompGCN retrieval, verified-evidence packet to real local answer generation, general NO/EN NL query interpretation and independent human review. The [Ask Alpha r2 trial](https://github.com/grove/graph-verity/pull/111) matched **20/29** supported *agent-written development* reference plans and produced **9/40** wrong-but-executable candidates; it did **not** prove safe free-form Ask.

**No stage of this design grants execution authority to a model.** Maintain explicit independent user approval for read-only graph execution; never execute generated SPARQL, fabricate facts from shape constraints or GNN predictions, open private graph scope or claim that missing RDF means real-world nonexistence. Keep historic experiments, registrations, consumed ledgers and sealed holdouts untouched.

Any **new** embedding, GNN or generative model inference requires distinct protocol freeze, pinned assets, exact explicit owner authorization and passing M1 Pro host gates; normal CI stays model-free. Keep [#83](https://github.com/grove/graph-verity/issues/83) open, live [#75](https://github.com/grove/graph-verity/issues/75) disabled, [#58](https://github.com/grove/graph-verity/issues/58) human review pending and **`INCONCLUSIVE_REVISE`** until separately justified.

**North star:** *A simple local assistant that uses graph structure and SHACL to retrieve trustworthy source evidence—and a local model to turn that evidence into useful, checkable language.*
