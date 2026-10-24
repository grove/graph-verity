# Graph Verity — local, verifiable Knowledge Graph RAG v1

**Status:** Proposed architecture for review; **not implemented by this document**.  
**Product goal:** Natural-language exploration of an authorized RDF graph in Norwegian or English, with explicit uncertainty, controlled interpretation, read-only execution and inspectable original evidence.  
**Tracking:** [#71](https://github.com/grove/graph-verity/issues/71), [#114 — lexical/semantic suggestions](https://github.com/grove/graph-verity/issues/114), [#115 — SHACL-guided choices](https://github.com/grove/graph-verity/issues/115), [#117 — R-GCN/CompGCN structural retrieval](https://github.com/grove/graph-verity/issues/117).  
**Existing product:** [Assisted Ask v1](../assisted-ask-v1.md), [Phase 2 roadmap](../phase-2-natural-language-ask.md). This document refines their component integration; it does **not** replace the roadmap or authorize a release.

## 1. Product contract and scope

**North star:** A person asks about a local knowledge graph without knowing SPARQL. Graph Verity retrieves likely *entities and relationships*, shows how the question could map to a directed graph operation, asks the person to resolve uncertainty, then returns results and their source triples **only for the operation explicitly approved**.

Version 1 is **retrieval-assisted, user-confirmed KG-RAG**, not autonomous LLM-to-SPARQL and not an LLM writing an unverified factual answer. A question may produce several choices, a clarification, an unsupported operation or no suitable candidate. Ranking is not intent recognition.

**Original research motivation, explicitly restored:** learning useful representations of typed knowledge-graph structure—particularly with **R-GCN and CompGCN**—was a major reason to start this project. The historical [implementation plan](../implementation-plan.md) scheduled their comparison after the first MVP to control complexity; that was a sequencing decision, **not a rejection** of graph neural retrieval. This architecture makes structural learning a **first-class research workstream (#117)** alongside textual semantic retrieval (#114) and SHACL guidance (#115). We will measure it against exact graph neighborhoods rather than assume a GNN is better, and it remains non-authoritative until independently demonstrated.

The first implementation slice builds on the existing, opt-in university development snapshot and one-hop Assisted Ask. Scope expansion (additional entities, predicates, inverse traversal, filters or datasets) requires the corresponding typed-contract, graph/source and regression review; it is **not** silently enabled by the architecture diagram.

## 2. Architecture and responsibilities

~~~mermaid
flowchart TD
    Q["Question (NO/EN), optional user text"] --> R["Authorized graph-local vocabulary retrieval"]
    R --> B["BM25 exact / lexical (current default)"]
    R --> E["EmbeddingGemma 2 semantic candidates (opt-in, gated)"]
    B --> C["Bounded, provenance-bearing candidate set"]
    E --> C
    G["Authorized named-graph RDF snapshot and original directed triples"] --> N["Deterministic source-witnessed graph neighborhoods / paths"]
    G --> H["R-GCN / CompGCN structural candidate reranking (separate research track)"]
    B -.-> H
    E -.-> H
    N --> C
    H --> C
    M["Authorized predicate metadata / optional trusted SHACL shapes"] --> C
    C --> U["Display options, ambiguity, missing vocabulary and source witnesses"]
    U --> S["User explicitly selects entity, predicate, graph and supported direction"]
    S --> P["Deterministic Rust plan and authoritative preview"]
    P --> A{"Separate, exact, time-bound, single-use approval?"}
    A -->|"no / stale / cancel"| X["No execution"]
    A -->|"yes"| V["Rust revalidation + scoped read-only Oxigraph"]
    V --> F["Original RDF bindings + triples, provenance, limits and uncertainty"]
    F --> T["Optional deterministic answer wording, never independent fact generation"]
    L["Optional local LLM: advisory intent/wording only, separately authorized"] -.-> U
~~~

| Component | Allowed responsibility | Does **not** establish |
| --- | --- | --- |
| Graph catalog and BM25 | Exact identifiers, labels/aliases and authorized, graph-qualified lexical ranking; the shipping baseline | User intent, real-world truth or completeness from no hits |
| EmbeddingGemma 2 | Paraphrase / cross-language similarity among **already authorized** entities and predicates; optional research candidate source | Confidence, a valid inverse relation, a guaranteed match or execution permission |
| Witnessed neighborhoods and paths | Deterministic graph-local incoming/outgoing edges and bounded path candidates with original triple evidence | Natural-language intent or facts outside the observed graph |
| R-GCN / CompGCN (**originating research pillar, #117**) | Learn relation-sensitive graph representations to **suggest/rerank** authorized entities, predicates or witnessed paths; benchmark against neighborhoods and text-only ranking | Proof of a missing edge, RDF truth, a request for inverse traversal, scope authorization or user approval |
| RDF metadata and SHACL | Source-backed predicate definitions, observed edge/type/direction evidence; **trusted** shapes may describe valid property paths, value kinds and constraints | That a particular user intended the property; that all data conform; closed-world absence |
| Optional local LLM (future) | Untrusted suggestion/clarification or wording from authorized candidates and, later, verified results | Query scope, source identity, authorization, independent truth |
| Deterministic assembler and Rust preview | Turn **explicit choices** into a typed, bounded, source/graph-checked plan | Whether those choices correctly interpreted free text |
| Single-use confirmation and Oxigraph | Permit only the exact current, read-only approved plan; return original scoped graph facts | A proof that approval means understanding, or external truth |

**Two kinds of retrieval are deliberately separate:** the top-k semantic/lexical results retrieve **vocabulary choices**. Once a plan is approved, Oxigraph evaluates the requested operation over the authorized graph scope; top-k vocabulary results never stand in for an exhaustive answer set.

## 3. Shared candidate and selection contracts (proposed, not a shipped API)

A suggestion is a **scoped data record**, not an executable proposal. The implementation may use existing Rust packet types rather than introduce a new wire format, but must preserve the following information and semantics:

~~~json
{
  "version": "kg-rag-candidates-v1",
  "question": "Hvilke offisielle nettsider har Universitetet i Tromsø?",
  "language": "nb",
  "snapshot_id": "sha256:<pinned-authorized-snapshot>",
  "scope": ["urn:graph-verity:nl-ask-v1:development:wikidata"],
  "index_revision": "<pinned-index-identity>",
  "status": "candidates",
  "candidates": [{
    "candidate_id": "<packet-local-opaque-id>",
    "role": "predicate",
    "graph": "urn:graph-verity:nl-ask-v1:development:wikidata",
    "iri": "http://www.wikidata.org/prop/direct/P856",
    "labels": [{"text": "official website", "lang": "en", "source": "<exact-statement-ref>"}],
    "descriptions": [{"text": "<source-authored-description>", "lang": "en", "source": "<exact-statement-ref>"}],
    "observed_usage": [{"direction": "outgoing", "witness": "<source-triple-ref>"}],
    "shape_guidance": [],
    "ranking": {"bm25_rank": null, "dense_rank": null, "neighborhood_rank": null, "rgcn_rank": null, "compgcn_rank": null, "exact_identifier": false},
    "structural_origin": {"witness": "<source-triple-ref>", "encoder_revision": null, "graph_snapshot": "<pinned-source-snapshot>", "predicted_edge_is_source_fact": false},
    "provenance": {"source_revision": "<source-version>", "license": "<license-id>"}
  }]
}
~~~

This is an **illustrative field contract only**, with placeholders rather than a real packet, hash or measured rank. The additional structural fields are **optional future extensions**, not a claim that R-GCN/CompGCN scores already exist. Production candidates must be built solely from the actual scoped Rust catalog/source, not this example. Entity and predicate candidate lists remain role-separated; graph-local ID mappings must be verified again by Rust. IDs are packet-local and cannot authorize arbitrary IRIs.

Required rules:

- **Inputs:** original question/language, operator-authorized snapshot/scope/policy, frozen index revision and bounded per-role budgets. Never use a reference answer or gold plan to retrieve candidates.
- **Sources:** original IRI, graph, role, tagged labels/descriptions, exact source witness IDs, source revision/license and any truncation or missing-metadata flags. A mechanically extracted IRI local name is **not** a natural-language definition. Shape-derived annotations identify their own origin and authority.
- **Ranking:** preserve lexical exact-ID/IRI priority and ties; return BM25, dense, neighborhood and (if separately trained) R-GCN/CompGCN ranks/scores as retrieval diagnostics, **not** probabilities of correctness. The candidate set must not silently auto-fill the user's selection.
- **Structural provenance:** observed incoming/outgoing edges and multi-edge paths require exact graph-scoped source witnesses. Record any graph-encoder revision, data snapshot and training permission separately from the original RDF evidence. A learned/predicted edge never becomes a source witness, answer binding, SHACL axiom or inferred inverse property.
- **States:** distinguish `candidates`, `ambiguous`, `no_match`, `insufficient_vocabulary`, `clipped` and `stale_or_unauthorized`. Even `no_match` says only that this retrieval policy found no candidate, not that a fact is absent.
- **Security:** filter graph/role/scope **before indexing, embedding, ranking, returning snippets or logging candidate text**. Reject stale source/index/snapshot mismatches and unauthorized graph/role IDs. Untrusted source text is data, never a prompt or UI instruction.

**Selection is a second step.** A user explicitly chooses an authorized start entity, original predicate and, for an approved query family, direction/graph. Only then does the existing Confirmed Ask Rust typed `follow_path` preview derive the final graph-qualified request, projection `values`, snapshot, limits and scope. No scored candidate can self-confirm. Unsupported filters/counts/joins may not be answered by a superficially similar unfiltered one-hop plan.

## 4. Structural graph learning: R-GCN and CompGCN

**This is a core KG-RAG research hypothesis, not an afterthought or a v1 serving requirement.** The graph is more than text: its typed edges, incoming/outgoing neighborhoods and interconnected paths can supply relevance signals absent from label/description embeddings. The original plan explicitly named **R-GCN versus CompGCN**; [#117](https://github.com/grove/graph-verity/issues/117) makes that comparison trackable **in parallel** with #114/#115 once a suitable pinned graph and evaluation task exist.

| Alternative | Role in the same retrieval task | Key distinction |
| --- | --- | --- |
| **Deterministic directed adjacency/path retrieval** | Rank witnessed neighbors/predicates/paths from actual bounded graph statements; mandatory low-complexity structural baseline | Exact existing edges; no model training or link-prediction hypothesis |
| **R-GCN** | Produce relation-aware **entity** representations from directed, typed graph structure; rerank source-authorized entity or path candidates | Relation-specific message passing, with a text-to-graph candidate anchor still required |
| **CompGCN** | Learn and compose **entity and relation** representations for predicate-aware candidate/path reranking | Joint relation/entity representation can exploit the original predicate identities, but cannot infer the user's intent by itself |

**How a question reaches the graph:** BM25/EmbeddingGemma and/or explicit user choices provide textual entity/predicate anchors. A graph encoder can *rerank only the authorized, graph-qualified candidates or witnessed paths* for those anchors; it must not silently substitute an observed edge with a predicted link. A standalone GNN embedding vector is not a Norwegian/English semantic parser. Candidate scores are ranking diagnostics, not confidence calibrated to a person's intended meaning.

**Feasibility and data fit:** do not train on the tiny university snapshot merely to have a GNN result. Check available real, properly licensed multi-relational datasets for enough nodes, edge types, directions and independent question-level supervision; source-pin the corpus and record when it is too sparse. Do not relabel AI-authored development references as independent gold. Keep training/evaluation partitions lineage-separated, avoid held-out answer-edge leakage in transductive graphs, and report where the training method necessarily accesses graph structure also used in evaluation.

**Trust, identity and freshness:** train and index only graph/role/snapshot-authorized triples; separate source graphs and permissions before constructing adjacency or embeddings. If inverse edges are materialized as **model-training features**, tag them as synthetic directional features, never original RDF claims. Pin the graph snapshot, model/training code, relation-ID map, tokenizer/text anchor if any, negative sampling, license, seed, weight digest and candidate index version. Refuse stale graph/model combinations. Rebuild or invalidate structural embeddings after source or scope changes; never expose private graph membership through rankings or scores.

**Required decision:** predeclare a controlled, bounded comparison on the **same source-authorized candidate universe**: BM25, EmbeddingGemma/hybrid, direct witnessed neighborhoods, R-GCN and CompGCN. Report entity/predicate/path Recall@k, MRR, direction consistency, observed-triple witness coverage, exact-ID first rank, no-match/ambiguity false suggestions, false exclusion of valid paths, training/refresh cost, query latency, memory and disk. Use a pinned M1 Pro resource budget and reject/defer either encoder if it provides no measured improvement worth its complexity. Structural link-prediction metrics and question-to-path retrieval metrics are **different** and must not be conflated.

The initial #117 deliverable is a **model-free adequacy and baseline proposal**. Any subsequent GNN training or inference is a separate frozen, explicitly authorized experiment; ordinary CI must not train/load the models. GNNs can be an important future retrieval module **without delaying** the current deterministic user-confirmed Assisted Ask flow.

## 5. SHACL: guidance, provenance and limits

SHACL is **optional, authoritative only to the extent the shapes themselves are authorized**. RDF source facts, property descriptions and shape constraints are distinct evidence types:

| Evidence | Safe use |
| --- | --- |
| Observed source triple | Shows a specific edge in the pinned named graph; can witness actual returned RDF facts |
| Archived licensed property definition / `wikibase:directClaim` mapping | Describes an original predicate and binds property metadata to its direct-claim IRI |
| Trusted source-published or separately operator-approved SHACL shape | Suggests expected property path, datatype/class/node kind or cardinality under its declared shape scope |
| Operator-authored demonstration shape | May exercise UI and validation, **must not** be presented as upstream source truth |
| Embedding similarity, R-GCN/CompGCN rank or LLM explanation | Helps rank/explain possible choices; learned link predictions are not original RDF facts and never override source facts or scope |

Before ingesting shapes, verify their licensing, named shape graph, source/author, shape revision/hash and mapping to the **authorized data snapshot**. Absence of published shapes is normal; #115 may use clearly labeled demo shapes stored **separately** from imported source RDF, never silently in the original snapshot.

Begin with a deliberately small **SHACL 2017 property-shape subset** for guidance: simple `sh:path`, explicitly supported `sh:inversePath`, `sh:datatype`, `sh:class`, `sh:nodeKind` and optional `sh:minCount`/`sh:maxCount` annotations. Reject or mark unsupported complex property paths, unknown shape constructs, invalid blank-node/list structure and incompatible graph bindings; do not pretend to implement full SHACL conformance. If constraint **validation** is later added, pin semantics and a reference implementation/fixtures separately.

**Direction remains explicit.** A source triple `S —P→ O` can be traversed from `S` forward or from `O` reverse when the typed Rust operation authorizes it. Neither a SHACL inverse path nor embedding similarity creates an inverse RDF statement or resolves what the person meant. Missing/incomplete shapes must **not** silently exclude otherwise authorized witnessed predicates; conflicts should surface as warnings or clarification with the source/shape identities shown.

## 6. Approval, verified answers and optional generation

Reuse the existing Assisted Ask / Confirmed Ask boundary; do not introduce a separate KG-RAG executor.

1. Display the **original question as unverified intent** alongside the exact operator-selected entity, relationship, original predicate IRI, direction, graph, snapshot, projection, source descriptions/shape guidance and any unresolved ambiguity. Label lexical, dense, deterministic adjacency and GNN-ranked suggestions by origin; display only **observed** source edges as evidence.
2. Rust builds and validates the complete plan against the current authorized catalog, policy and immutable snapshot; display the authoritative preview. The preview cannot by itself establish natural-language semantic correctness.
3. Require an **independent, deliberate, expiring, tab/session-bound, single-use approval** of that exact plan. Any edit, cancellation, stale scope, policy, shape dependency or snapshot invalidates it. Rebuild and revalidate immediately before bounded read-only execution.
4. Return **original** RDF terms (IRIs, lexical values, datatypes, language tags) and source triples, named graph/snapshot, attribution/license, empty/no-match distinction and independent row/evidence clipping flags. Preserve the existing read-only permissions, timeout and evidence limits. An empty result is not a real-world nonexistence claim.
5. Prefer deterministic result formatting first. Optional later local generative wording must only describe already retrieved **verified bindings** with traceable citations; no unsupported facts, silent answers, generated SPARQL or model-issued execution permission. This requires a separate reviewed/authorized experiment.

**Critical distinction:** Rust/SHACL can establish that an operation is structurally permitted and source-grounded. They cannot establish that the user's question was understood. User approval controls execution, not semantic truth.

## 7. Why this is the proposed direction

- The full Ask Alpha r2 run in [PR #111](https://github.com/grove/graph-verity/pull/111) completed all 60 semantic questions but matched only **20/29** agent-prepared supported references: **17/17 forward, 3/12 reverse**; **9/40** candidate proposals were wrong against determinate references despite passing Rust. Its **8/8** predeclared forward website/name core matches were insufficient for alpha readiness because surrounding safety/clarification gates failed. These are exposed, correlated development judgments, **not independent human gold**.
- Pinned EmbeddingGemma 2 improved paraphrase/cross-language vocabulary recall in [#50](../../reports/issue-50-real-rdf-hybrid/README.md), but naive fusion harmed exact-ID ranking, returned false no-match candidates and exceeded the proposed process-memory budget. The later [selective hybrid #53](../../reports/issue-53-selective-hybrid/README.md) still failed its no-match promotion rule; [#58](https://github.com/grove/graph-verity/issues/58) has no independent human review. **BM25 stays Find's default**. None of this demonstrates independent Ask semantic accuracy.
- The original [implementation plan](../implementation-plan.md) singled out **R-GCN/CompGCN** to explore learned structure beyond textual retrieval, but deferred the comparison to post-MVP for sequencing. The new **#117 structural-learning workstream** restores that core motivation, with **deterministic adjacency first** and a separate controlled model comparison before adoption; no native GNN quality is yet measured.
- Current [Assisted Ask v1](../assisted-ask-v1.md) already runs explicitly selected forward official-website/name operations with exact review, single-use approval and original graph evidence. It uses neither live model inference nor automatic question interpretation.

Thus the design treats **text semantic retrieval and learned structural retrieval as complementary candidate sources**, source/SHACL constraints as **grounding**, manual selection as **intent authority**, and Rust/Oxigraph as **execution and evidence authority**. It does not assert that the integrated approach has been tested, that a learned edge is true or that users understand plan previews.

## 8. Implementation order and decision gates

| Stage | Tracked work | Demonstration and gate |
| --- | --- | --- |
| **0 — this PR** | Architecture decision only | One document agreed, linked from PR; no runtime/benchmark/freeze changes, tests or inference |
| **1 — #114** | Add optional BM25 + EmbeddingGemma 2 **entity/predicate suggestions**, using pinned authorized catalog/source descriptions | Model-free first: replay candidate packets, exact-ID/ambiguity/no-match/private-scope tests, bilingual retrieval metrics and real-browser manual-choice flow; new live embedding measurements separately frozen and authorized; **no default Find promotion** |
| **1b — #117 (parallel first-class research)** | Build witnessed neighborhood/path baseline and evaluate **R-GCN vs CompGCN** when graph density and supervision permit | Source/role/scoped graph adequacy check; same authorized candidate set and leakage-safe paired retrieval metrics; separately frozen/authorized training; **no predicted link as fact and no required v1 runtime dependency** |
| **2 — #115** | Introduce provenance-checked trusted/demo SHACL property-shape **guidance** and a confirmed, source-backed operation slice | Manual operation remains possible without #114/#117; explicit direction, type/path guidance, stale-shape/graph rejection, unchanged Rust plan/approval, evidence rendering and negative tests; **no blanket SHACL-conformance claim** |
| **3 — later decision** | Consider integrating **measured** structural/textual rankings and optional LLM assistance/verified-result wording | Require separate promotion/evaluation and explicit user approval; learned relevance is never a source fact or execution permission |

For #114, predeclare entity/predicate Recall@1/5/10, exact-ID first-hit preservation, source/role coverage, missing-ID and no-match/ambiguity behavior, query-language strata, RSS, cold/warm latency and false suggestions. Measure alongside unchanged BM25 and retain regressions and incomplete denominators. Retrieval wins alone do **not** pass the product gate.

For #117, compare **witnessed neighborhoods against each graph encoder**, separately measure any added benefit over BM25/dense/hybrid, direction/path retrieval fidelity, train/serve/refresh cost and scope/no-match regressions. Do not measure GNN link-prediction triples as if they were observed source-backed answers. This is a **planned first-class research milestone**, not a post-product omission.

For #115, evaluate correctly retained vs falsely excluded source-valid options, shape/path authorization, forward/reverse field agreement after **user selection**, stale/unauthorized scope rejection, wrong-but-executable negative controls, preview/approval security and source/result completeness. Do not score operator-selected requests as autonomous question-understanding successes.

For any **future** combined prototype, separately measure end-to-end supported coverage, wrong-but-executable plans, user-visible ambiguity/no-match, clarification, latency and resource use. Human-comprehension and independently judged intent remain **unmeasured** until actual reviewers/users participate; an automated browser cannot substitute. Declare a release/stop decision **after** evaluating these criteria, not from a successful CI run.

## 9. Explicitly deferred

- Shipping hybrid or GNN-based search by default; automatic selection of top-ranked textual/structural hits.
- **Production GNN inference/training and presentation of predicted links as source facts** before #117 shows a measured, authorized advantage. GNN *research itself is explicitly in scope*, not indefinitely deferred.
- Broad SHACL validation, ontology inference, shape mining asserted as real constraints or closed-world completeness.
- Multi-hop free-form interpretation, natural-language filter inference, raw generated SPARQL, SERVICE, writes or private graph discovery.
- Unsupervised Qwen/Gemma interpretation or integration into live #75; model-generated RDF execution or auto-approval.
- Unapproved embedding/generative inference, asset downloads, changed model gates, reused consumed ledgers, sealed Ask holdouts or edits to historical experiments.
- Claims of verified human understanding, independent semantic truth, scalable 100k-resource production performance or product release readiness.

**Standing status:** `INCONCLUSIVE_REVISE`; [#83](https://github.com/grove/graph-verity/issues/83) remains open, live [#75](https://github.com/grove/graph-verity/issues/75) disabled. Any behavior change needs its own PR, tests and explicit authorization where inference or integration is involved.

**Design principle:** *Graph Verity combines language and learned graph-structure signals to retrieve possibilities, grounds them in authorized source facts and trusted constraints, lets the user resolve uncertainty, and uses Rust to return verifiable answers.*
