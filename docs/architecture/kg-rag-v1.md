# Graph Verity — a simple, graph-enhanced local RAG (Phase 2)

**Status:** Architecture proposal, **not yet implemented**. **Decision:** `INCONCLUSIVE_REVISE`.  
**Product north star:** Ask naturally in Norwegian or English. Graph Verity retrieves relevant **source documents and/or original RDF facts**, uses knowledge-graph relationships and trusted SHACL constraints when they help, then a **local generative model produces a short cited answer**.  
**Project decision:** **Evolve Graph Verity in the same repository.** The traditional RAG foundation and graph-enhancement modules are parts of **one** product, not rival applications.

Tracking: [#71 Phase 2](https://github.com/grove/graph-verity/issues/71), [#119 document/vector RAG foundation](https://github.com/grove/graph-verity/issues/119), [#114 graph vocabulary retrieval](https://github.com/grove/graph-verity/issues/114), [#115 SHACL/verified graph evidence](https://github.com/grove/graph-verity/issues/115), [#117 R-GCN/CompGCN research](https://github.com/grove/graph-verity/issues/117), [#118 grounded generation](https://github.com/grove/graph-verity/issues/118). Build on the existing [Phase 2 roadmap](../phase-2-natural-language-ask.md) and [Assisted Ask v1](../assisted-ask-v1.md), not a second graph planner/executor.

## 1. Product outcome — better RAG, not just graph QA

**RAG = RETRIEVE → AUGMENT → GENERATE.** Returning RDF rows or retrieving candidate predicate names alone does not complete RAG. Our goal is a **useful, locally generated, citation-backed answer**, not a more complicated interface than ordinary RAG.

A user might ask either:

- **Document question:** “What does this policy say about application deadlines?” A plain text passage may be enough. Retrieve matching chunks from an authorized local document index, cite the actual document span, and generate a short answer. **No graph operation is required.**
- **Graph-rich question:** “Which organization is responsible for this service, and what is its official website?” Text search may find the service and organization; **graph-linked entities, original directed edges and SHACL property guidance** may disambiguate roles and supply an additional, original source-witnessed fact. If a supported graph query is needed, display the exact operation and require **distinct user approval** before it runs. Combine the document and graph evidence in one cited answer.

The product should **selectively enrich conventional RAG with a knowledge graph**, not force every question through a GNN, a SHACL validator, a multi-hop planner or an approval dialog. Keep the interface a single Ask flow with unobtrusive citations and expandable source details.

**We must earn the word “better.”** A vector database and a graph are not improvements by themselves. Compare against a strong **plain local text-RAG baseline using the same content, answer model and machine**. Demonstrate material gains in grounded answer quality, difficult relations/multi-hop coverage, NO/EN retrieval, citations or usefulness **without unacceptable false positives, memory, latency or complexity**.

## 2. One coherent architecture

~~~mermaid
flowchart TD
    Q["User question (Norwegian / English)"] --> B["Local document retrieval: BM25 + vector index"]
    Q --> V["Optional graph vocabulary and entity linking"]
    D["Authorized documents, stable chunks and source spans"] --> B
    R["Authorized RDF graph and original triples"] --> V
    R --> N["Observed directed neighborhoods and paths"]
    N --> V
    N --> G["Optional R-GCN / CompGCN graph reranking (research)"]
    G --> V
    S["Trusted SHACL shapes / property descriptions"] --> V
    V --> I["Graph interpretation candidates; clarify or ask for exact approval"]
    I --> X["Existing Rust preview + single-use approval"]
    X --> O["Bounded read-only Oxigraph results and RDF triple witnesses"]
    B --> E["Unified source evidence packet: document spans + RDF facts"]
    O --> E
    E --> A["AUGMENT: small provenance-bearing local model context"]
    A --> L["GENERATE: natural NO/EN cited answer"]
    L --> C["Check citations, supported claims and incompleteness"]
    C --> Y["Answer with expandable original sources"]
    C --> F["On failure: deterministic evidence or truthful abstention"]
~~~

**Important branch:** The path `B → E` works **without** `V/X/O` for ordinary document questions. The graph path adds evidence only when it is actually appropriate and authorized; the diagram does not imply free-text prompts automatically execute graph queries. The model **never** chooses execution permission.

Three different retrieval concepts must not be confused:

1. **Document retrieval** fetches authorized, citeable *source text spans* (traditional RAG). A vector score is a relevance estimate, not proof.
2. **Graph discovery** finds candidate entities, predicates and paths using BM25, EmbeddingGemma, witnessed adjacency and optionally GNN reranking. Its top-k outputs are **not answer facts**.
3. **Verified graph fact retrieval** uses the *exact user-approved* typed Rust plan in Oxigraph, returning recorded RDF terms and supporting triples from a named graph/snapshot. Only this third kind supplies **original RDF source claims** for the answer packet.

The source material and resulting evidence are then **augmented into one bounded prompt** for the generator. SHACL guidance and learned graph predictions are explanatory *metadata*, not replacement source facts.

## 3. Components and interfaces — keep the stack small

| Component | Concrete job | Scope/decision |
| --- | --- | --- |
| **Local document ingester + chunk store (#119)** | Turn approved Markdown/text (other formats later) into stable versioned chunks, language/source spans and citations | **New baseline**; permissions/licensing and index freshness are checked before text enters retrieval or a model |
| **BM25 + local vector search (#119)** | Lexical and embedding-based retrieval of document chunks, with optional fusion | A **local vector database or simple persistent vector index** is an implementation choice, not an automatic extra server. Reuse indexed embeddings; benchmark first |
| **EmbeddingGemma 2 (#114/#119)** | NO/EN semantic matching of chunks and graph vocabulary/relationships | Pinned research model exists; graph-Ask and document chunk-serving integration are **not yet implemented**. Keep exact-ID/no-match protections |
| **Original RDF graph + neighborhoods** | Real directed edges, typed entities and paths, graph-qualified identifiers and original witnesses | Reuse Rust/Oxigraph, deterministic traversal and source scope. Never invent an inverse source triple |
| **R-GCN / CompGCN (#117)** | Learn multi-relational patterns that might rerank *witnessed* graph entities/paths beyond text similarity | **Original core research motivation**; first-class paired study against simple adjacency. Not a mandatory runtime or source-truth authority |
| **SHACL / property metadata (#115)** | Explain expected property paths, classes, node kinds and datatypes; constrain/clarify where trusted shapes exist | Separate licensed shape provenance; no guarantee a question was interpreted or all facts conform |
| **Rust approved graph query (#115)** | Exact interpreted graph operation, manual review, expiring single-use approval, bounded read-only Oxigraph | Reuse the working Confirmed/Assisted Ask boundary. Plain permitted document retrieval does **not** require a fake graph approval |
| **Evidence pack, local LLM and checks (#118)** | Combine citeable document spans **and/or** original RDF bindings; write and verify a short natural answer | **Required RAG stage**. Model inference is separate opt-in/authorization; deterministic evidence fallback stays available |

**Practical code organization:** stay in the current repository, keep `verity_core`/Oxigraph as the graph authority, and add small modular adapters for document ingestion, lexical/vector retrieval and evidence-grounded generation. One local UI and a versioned *evidence interface* suffice. Do not introduce independent microservices, new graph databases, multiple vector backends or mandatory concurrent model processes without benchmark evidence.

**Resource policy:** A single-user M1 Pro / 32 GiB should not have to keep EmbeddingGemma, a GNN and a generative model resident concurrently. Cheap exact/BM25 paths first; optional dense/graph reranking when they help; bounded retrieval context and source clipping; cold/warm time, peak total RSS, build/index/refresh cost and disk measured honestly.

## 4. Provenance and evidence contracts

**Document citations:** source document ID, version/content digest, license/permission, local language, exact original span/offset, chunk ID, truncation and a stable citation target. The vector index contains **no privileged text** outside the source's authorized scope. A snippet is a citation to a *document passage*, not automatically proof of an RDF relationship.

**Graph candidates:** source-scoped entity/predicate/path IRI, graph, role, label/language/definition, original edge witnesses and separate BM25/dense/neighborhood/GNN ranking metadata. Missing SHACL or learned scores are ordinary states. A GNN-predicted link is a **hypothesis**, never a source triple, no matter how plausible. Structural embeddings are keyed to model+weights, graph, scope, relation IDs and snapshot; stale results fail closed.

**SHACL shapes:** use only source-published or clearly operator-authorized shapes. Keep shape source/license, shape-graph, hash/version and named-graph mapping separate from imported RDF. For an initial subset, consider simple `sh:path` and supported `sh:inversePath`, `sh:datatype`, `sh:class`, `sh:nodeKind` and cardinality metadata; fail transparently on unsupported constructs. A shape's expectation is not evidence that an edge exists and missing triples are not necessarily false.

**Unified generation evidence packet:** Build it **after permitted document retrieval and, if invoked, approved graph execution**. The packet should be small, typed, source/version-bound and model-independent. Illustrative (not a currently implemented API):

~~~json
{
  "version": "kg-rag-evidence-v1",
  "question": "<original Norwegian or English question>",
  "language": "en",
  "document_evidence": [{
    "citation_id": "d1",
    "document_id": "<source ID>",
    "version_digest": "<source digest>",
    "span": {"start": 0, "end": 42},
    "text": "<exact permitted document excerpt>",
    "license": "<license/permission>"
  }],
  "graph_evidence": [{
    "citation_id": "g1",
    "confirmed_operation": "<Rust approval-bound plan ID>",
    "snapshot": "<exact authorized graph snapshot>",
    "graph": "<named graph>",
    "subject": "<original subject IRI>",
    "predicate": "<original predicate IRI>",
    "object": "<original typed RDF term incl language/datatype>",
    "source_revision": "<source revision>",
    "license": "<license>"
  }],
  "completeness": {
    "documents_clipped": false,
    "graph_rows_clipped": false,
    "graph_evidence_clipped": false,
    "graph_not_invoked": false
  }
}
~~~

Both arrays are **optional**, but generation needs **at least one valid authorized factual source**. When `graph_not_invoked` is true, `graph_evidence` is empty; do not invent a graph query or citation to fill it. In a real implementation preserve full result bindings, graph limits/timeouts, document retrieval truncation and separate source identities, not just the simplified example.

An RDF triple **derived from a document by automated extraction** is *derived information*; retain a verifiable document-span origin, extraction/verification status and clearly separate it from externally supplied original RDF. Do not silently assert extracted links as ground truth, conflate document claims with graph authority or hide source conflicts.

**Generation:** A pinned local LLM receives only the bounded authorized evidence plus the approved operation/uncertainty status if relevant. Source text is **untrusted input**, not a system instruction. The answer may cite `d1` for a document statement and `g1` for an original RDF statement. The post-check validates citation IDs, exact quoted IDs/URLs/numeric values where supported, mapping to genuine spans/triples and known answer-family constraints. **A real citation does not guarantee the whole sentence is entailed**; measure claim faithfulness against independent references, fail closed outside checker coverage, and use a deterministic evidence/abstention fallback when generation is invalid or absent.

**Authorization:** Retrieval and indexing must respect source permissions before any text, private graph membership, embedding or score is exposed. **Only graph operations** use the existing distinct approval and Rust/Oxigraph revalidation. No model can mint scope, create facts, issue raw SPARQL or approve execution.

## 5. Prove we deliver *better* RAG

An honest comparison uses the same licensed source material, questions, machine, evaluation rules and (where possible) generation model and context budget. Report both **controlled matched-source ablations** and **realistic mixed documents + RDF** conditions; never attribute more available source data to the model architecture itself.

| Experiment | What it determines |
| --- | --- |
| **Document chunks + BM25 + local cited generation** | Cheapest baseline people can actually use |
| **Document chunks + vector search / hybrid retrieval + same generator** | Whether embeddings improve NO/EN paraphrases and answer support without false matches |
| **Same document RAG + source-linked RDF graph retrieval** | Incremental gain for entity relations, multi-hop paths and original graph evidence |
| **Graph enrichment with/without trusted SHACL** | Better structural choices or fewer bad interpretations, without suppressing real witnessed facts |
| **Witnessed adjacency vs R-GCN vs CompGCN** | Whether learned graph structures add value over cheap deterministic traversal and text search |
| **Generated cited answers vs deterministic retrieved evidence** | Whether an LLM makes results easier to understand without inventing claims |

Metrics: answer-level factual grounding and citation support **by type** (document span vs RDF triple), exact entity/predicate/direction, multi-hop evidence coverage, positive/negative retrieval recall, no-match/abstention false confidence, question-answer usefulness, NO/EN performance, cold/warm latency p50/p95, total process-tree RSS, model/index storage and refresh cost.

**Do not confuse benchmarks:** #50/#53 demonstrated some embedding retrieval gains and false-candidate regressions, but did not prove better answer generation. [PR #111](https://github.com/grove/graph-verity/pull/111) showed **20/29** matched supported *agent-authored development* plans and **9/40** wrong-but-executable candidates; syntactic Rust acceptance isn't question correctness. Existing agent-authored relevance/intent gold isn't independent human review. Gather real feedback when practical; do not fabricate participants.

**Promotion rule:** each extra step—dense retrieval, graph traversal, SHACL, GNN, LLM reranking—must earn its runtime/maintenance cost against the **simpler local RAG** under explicit error, quality, resource and UX gates. The **product includes actual evidence-grounded local generation**, but for simple questions it may legitimately use text-only evidence. Unanswered/conflicting/incomplete cases should be visible, not disguised.

## 6. Staged deliveries, one evolving project

| Issue | Small first output | Product role |
| --- | --- | --- |
| **#119 — traditional RAG foundation** | Authorized local documents, stable chunks/spans, BM25 and optional persistent vector search, unified document evidence | Usable documents-only retrieval baseline |
| **#114 — graph semantic discovery** | Authorized NO/EN entities and predicates from BM25/EmbeddingGemma, exact/no-match protections | Helps select when graph relations matter |
| **#115 — SHACL and graph evidence** | Trusted shape metadata, supported directed graph operations, independent user approval, original RDF witnesses | Adds source-backed graph facts to the shared evidence packet |
| **#117 — R-GCN/CompGCN (parallel)** | Real graph adequacy, simple witnessed neighborhoods, later separately authorized GNN comparisons | Optional structural ranking enhancement; **first-class research, not a product blocker** |
| **#118 — local grounded generation** | Typed mixed-evidence packet, citation/claim checks, deterministic fallback; after new explicit authorization, real local model answer generation | Completes traditional and graph-augmented **RETRIEVE → AUGMENT → GENERATE** |

Build thin vertical slices rather than waiting until every algorithm works. An initial **documents-only RAG** can run before graph enrichment, and a graph-assisted slice can reuse the proven Rust path; both use the **same UI, evidence contract and generator**. After both are available, evaluate their incremental advantage before additional complexity.

**When to split repositories:** only if later there are genuinely separate independently deployed products, incompatible target users/platforms or clearly reusable published libraries needing independent release cycles. Do **not** fork now; use modular components/feature gates within Graph Verity.

## 7. Current implementation and safety truth

**Working today:** the existing graph catalog, BM25 Find, typed Rust/Oxigraph read-only retrieval and original RDF evidence, one-shot operator approval and narrow model-free Assisted Ask v1. **Measured but not integrated:** EmbeddingGemma 2 experiments. **Not yet shipped:** general document-chunk RAG/vector store, SHACL-guided serving, R-GCN/CompGCN, a mixed doc/graph evidence pack, local source-grounded RAG generation and independently verified human answer understanding. This document is a proposal, not retrospective proof those components exist.

Keep **INCONCLUSIVE_REVISE**. Historical one-hop inference [#83](https://github.com/grove/graph-verity/issues/83) and live-model Ask integration [#75](https://github.com/grove/graph-verity/issues/75) are **closed as not planned, not validated or shipped**; live #75 integration remains **disabled**. The separate [#58](https://github.com/grove/graph-verity/issues/58) independent relevance review remains open and unfulfilled. No model-generated graph writes/queries, remote `SERVICE`, cross-scope leakage, unproven GNN links as RDF facts, or silent result-language/filter substitution.

Any **new embedding/GNN/generative inference**, assets/downloads or training requires a newly frozen version and **separate explicit owner authorization** with applicable host memory/swap and provenance gates; normal CI stays model-free. Do not modify historical model evidence, consumed ledgers, original snapshots or sealed holdouts. A failed model check must fall back to source evidence, not be represented as success.

**North star:** *One local RAG application that works on ordinary documents and becomes significantly better where trusted graph relationships, SHACL and learned graph structure genuinely help.*
