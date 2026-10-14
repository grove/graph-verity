# RDF-Native Semantic Retrieval and Query Engine
## Detailed Implementation Plan

**Document date:** 14 October 2026  
**Status:** Proposed engineering plan  
**Initial scale:** 10,000–100,000 searchable RDF resources  
**Primary languages:** Norwegian questions; Norwegian and English graph labels  
**Runtime:** Local Rust process, without an external database or hosted AI inference service

## 1. Executive Summary

Build a local engine that accepts natural-language questions about an RDF knowledge graph, retrieves semantically relevant entities and SHACL shapes, and checks results using exact SPARQL queries and explicitly supported SHACL constraints. The initial release will use EmbeddingGemma 2 and a text-only index of verbalized RDF neighborhoods. Subsequent experiments will align a relational graph encoder, initially CompGCN with R-GCN as a comparator, to the text model's 256-dimensional embedding space. A constrained query planner will later support compositional questions involving joins, counts, filters, and comparisons.

**Core principle:** embeddings estimate relevance; RDF/SPARQL/SHACL supply verifiable evidence. A high similarity score is not a truth claim. Searching only the top-*k* vector hits is not an exhaustive answer to a structured query.

**Decision gates:** ship a valuable text-only engine first; add CompGCN only if it improves relational-question Recall@10 by at least **10 absolute percentage points** against the frozen-text baseline, without unacceptable latency, memory, or maintenance costs.

## 2. Goals, Scope, and Non-Goals

### 2.1 Product goals

1. Support Norwegian questions against RDF datasets containing English and/or Norwegian labels and descriptions.
2. Find entities, SHACL shapes, and, when enabled, ontology classes and predicates from a local index.
3. Support two execution modes:
   - **Retrieval mode:** rank relevant objects, then verify requested facts about those candidates.
   - **Structured question mode:** create a restricted, inspectable query plan and execute it over the graph, without restricting completeness to vector top-*k*.
4. Return resource IRIs, result type, named-graph provenance, and the graph facts or constraint reports supporting each result.
5. Run inference locally through ONNX Runtime in a Rust process; keep Python limited to offline preprocessing, training, evaluation, and model export.
6. Track reproducible model, graph, shapes, preprocessing, and index versions.

### 2.2 MVP boundary

- One well-defined enterprise or public-sector RDF domain, with 10,000–100,000 searchable resources.
- A bounded subset of SHACL Core: simple predicate paths, `sh:minCount`, `sh:maxCount`, `sh:datatype`, and `sh:class`; extend only after conformance tests pass.
- Exact structured plans for a controlled set of question templates: type lookup, a one-/two-hop join, conjunction, numeric/date filter, and `COUNT(DISTINCT ...)` with `HAVING`.
- One supported CPU hardware profile, defined and benchmarked before accepting latency claims.

### 2.3 Explicit non-goals for the first release

- Arbitrary natural-language-to-SPARQL generation with unrestricted SPARQL execution.
- Full SHACL 1.2 Core/advanced features, OWL entailment, or universal closed-world reasoning.
- Real-time GNN inference for every user request.
- Guaranteed exhaustive results from top-*k* vector retrieval.
- Mandatory packaging of the model weights, vector index, and graph database *inside* the Rust executable. A single deployable process with versioned local artifacts is sufficient.

## 3. Reference Architecture

```text
                          Offline build / training
RDF + shapes + source metadata ──> normalized graph + ontology catalog
             │                          │
             ├──> entity/shape verbalization ──> document embeddings ──┐
             │                                                         │
             ├──> train/validation/test pairs                          ├──> versioned index bundle
             │                                                         │
             └──> relational graph ──> CompGCN/R-GCN ──> graph vectors ┘

                              Online Rust runtime
Norwegian question
      │
      v
Tokenizer + EmbeddingGemma 2 ONNX (query embedding)
      │
      v
Intent/router: retrieval | structured query | shape lookup | unsupported
      │                                 │
      v                                 v
Vector + lexical retrieval         Restricted query-plan builder
      │                                 │
      v                                 v
Candidate ranking + filters       Schema/entity/predicate resolution
      │                                 │
      └───────────────┬─────────────────┘
                      v
             Oxigraph/SPARQL execution
                      │
                      v
          Supported SHACL validation (when needed)
                      │
                      v
           Verified results + provenance + status
```

**Important separation:** the planner is a separate component, not an assumed capability of EmbeddingGemma or CompGCN. The retriever suggests relevant RDF terms and candidates; the planner constructs formal operations; Oxigraph executes them.

## 4. Technology Decisions

| Layer | Initial choice | Rationale / alternative |
|---|---|---|
| Language embedding | EmbeddingGemma 2, text-only weights | Multilingual, native 256-dimensional truncation, offline CPU inference; benchmark Qwen3-Embedding-0.6B separately if needed. |
| Text embedding geometry | First 256 dimensions of native 768-dimensional output; L2-renormalize | Preserve the pretrained representation for v1. |
| Graph modeling | CompGCN, two message-passing layers, built with PyTorch Geometric primitives or a reviewed implementation | Relational node/message encoding; compare with R-GCN under the same data and training budget. |
| Training | Python, PyTorch, PyTorch Geometric, Sentence Transformers | Offline experiments and reproducibility. |
| Runtime | Rust, `ort`, Hugging Face `tokenizers` | Local inference and integration with the RDF runtime. |
| RDF store | Oxigraph `Store` | In-process RDF quads and SPARQL; choose `Store::new()` for ephemeral in-memory or `Store::open(...)` for persistent RocksDB-backed storage. |
| Vector index | FP32 flat matrix + `memmap2`, SIMD dot products | Simple, transparent exact nearest-neighbor search at MVP scale. |
| Keyword search | Rust lexical/BM25 index, e.g. Tantivy | Preserve exact IRIs, codes, and distinctive names missed by embeddings. |
| Validation oracle during development | pySHACL / W3C SHACL test cases | Differential-test any Rust-side SHACL compiler; not required as an online Python service. |
| API / CLI | Rust HTTP service and local CLI | Keep API, model execution, and graph access inside one process. |

**Model-specific precautions:** use the correct query/document prefixes; keep pooling and truncation identical in Python and Rust; re-normalize after 256-dimensional truncation; avoid FP16 for EmbeddingGemma 2 unless upstream guidance changes. Quantized ONNX exports must pass quality and numerical-parity tests before deployment.

## 5. Data Model, Ingestion, and Provenance

### 5.1 Ingestion pipeline

1. Accept RDF in an explicit set of serializations (initially Turtle, TriG, and N-Quads).
2. Parse and validate input; quarantine malformed graphs, malformed literals, and unsupported dataset conventions.
3. Preserve IRIs, language tags, literal datatypes, predicate direction, named graph identifiers, and source provenance.
4. Load data quads into Oxigraph. Keep the shapes graph logically separate and versioned, even if stored in a dedicated named graph.
5. Generate a deterministic RDF snapshot ID from canonicalized release inputs plus import configuration, not from nondeterministic insertion order.
6. Extract a vocabulary catalog: classes, predicates, human-readable labels, domain/range hints where available, and example usages.
7. Create a searchable resource registry: entity IDs, shape IDs, optional class and predicate IDs, and associated metadata.

### 5.2 Blank nodes and SHACL lists

- Do not assume blank-node labels remain stable across imports.
- Resolve RDF lists and nested shape structures into a **typed shape abstract syntax tree (AST)** that preserves ordering, conjunction, disjunction, negation, and path operators.
- For ML verbalization only, derive deterministic synthetic identifiers/edges from that AST. Keep original RDF for formal evaluation.
- Avoid silently converting a list such as `sh:or` into unrelated bag-of-words properties.

### 5.3 Entity document format

Produce several text views per resource rather than one unrestricted description:

- **Identity view:** label, aliases, class, definition, URI fragments only as supporting context.
- **Local structure view:** selected incoming and outgoing `(subject, predicate, object)` verbalizations, with direction preserved.
- **Constraint view:** applicable shapes and their human-readable descriptions; do not imply that the node conforms unless validated.
- **Source view:** domain prose with reference to named graph and source document.

Limit and deterministically order n-hop neighborhoods. Give rare predicates and task-critical relations priority; preserve language tags and datatypes in source metadata. Numeric values can appear in the document, but exact numeric logic stays in SPARQL.

### 5.4 Searchable-object schema

| Field | Purpose |
|---|---|
| `object_id` | Stable internal identity within the versioned registry. |
| `rdf_term` | Full IRI or controlled synthetic identifier for a shape. |
| `object_type` | `entity`, `shape`, optionally `class` or `predicate`. |
| `rdf_classes` | Known classes for filtering. |
| `language` | Language of a specific verbalization. |
| `named_graphs` | Source graph/provenance. |
| `text_view` | Identity, structural, constraint, or source description. |
| `document_text_hash` | Rebuild/change detection. |
| `graph_snapshot_id` | Exact dataset release. |
| `shape_snapshot_id` | Exact constraints release. |
| `model_id` | Checkpoint and projection configuration. |
| `embedding_kind` | `text`, `graph`, or `delta_text`. |

**Acceptance:** repeated imports of the same release yield identical resource IDs, indexes, and provenance mappings; tests cover languages, datatype literals, parallel edges, named graphs, and blank nodes.

## 6. Baseline: Text-Only Search (Build First)

### 6.1 Embedding production

1. Load **only the text component** of EmbeddingGemma 2 for the baseline.
2. Encode user questions with the documented retrieval-query prompt and indexed documents with the retrieval-document prompt, including titles where available.
3. Use the pretrained 768-dimensional representation, truncate to its first 256 dimensions, then L2-normalize the truncated vector.
4. Reject non-finite or zero-norm vectors; store `float32` in the index.
5. Save the tokenizer files, prompt templates, pooling/truncation code version, and model digest.
6. Test English labels queried in Norwegian, lexical synonyms, ambiguous company names, directional relations, and exact identifiers.

### 6.2 Search implementation

- Combine lexical BM25 matches and cosine scores using a simple rank-fusion method (for example reciprocal rank fusion) before experimenting with learned weighting.
- Support type, named-graph, and language filtering; only apply a filter when the caller requests it or the intent parser supports it reliably.
- Produce candidate lists at configurable `k` (10, 20, 50, 100, 500) and track Recall@k for each.
- Use vector similarity only for discovery/ranking; a vector hit alone is never marked “verified.”
- Record search diagnostics (without storing confidential raw questions by default): stage latencies, index version, candidate count, and reason for no result.

### 6.3 Vector format

At 100,000 resources, `100000 × 256 × 4 = 102,400,000` bytes of raw vectors (102.4 MB decimal; approximately 97.7 MiB). The file format should include a versioned header or companion manifest, followed by contiguous little-endian FP32 rows. A row-to-ID mapping must be covered by the same integrity hash.

**Index-bundle manifest:** `format_version`, `dimension`, `dtype`, `normalization`, `row_count`, `resource_registry_hash`, `model_hash`, `tokenizer_hash`, `preprocessing_hash`, `graph_snapshot_id`, `shape_snapshot_id`, `index_build_id`, and file checksums.

**Acceptance:** a deterministic Python/Rust parity test produces closely matching vectors, and a Rust scan returns the same top-k ranking as the Python reference within specified floating-point tolerance.

## 7. Exact RDF and SHACL Validation

### 7.1 Formal semantics contract

- Search relevance is distinct from SHACL conformance, support for a factual claim, and completeness of an answer set.
- Validate only against the explicit graph snapshot and entailment regime selected for the release.
- Absence of an RDF triple is **not** proof of a false-world claim. Require an explicit completeness policy for negative answers such as “has not submitted a report.”
- Separate `verified`, `nonconformant`, `unknown`, `unsupported`, and `execution_error` in responses.
- A node that violates a shape can still be a highly relevant search result for a data-quality question.

### 7.2 Bounded SHACL compiler

1. Parse supported shapes into a typed AST.
2. Implement exact evaluation of simple paths and the selected constraint types.
3. Compile applicable validation tests into SPARQL or an equivalent exact evaluation over Oxigraph.
4. Return structured validation details: focus node, shape ID, path, offending or missing value, severity, source graph, and status.
5. Reject/mark unsupported constructs rather than assuming they pass; do not label this subset compiler a full SHACL processor.
6. Differential-test against pySHACL and relevant W3C fixtures, including class/subclass behavior and ill-typed literals.

In retrieval mode, perform validation on the selected candidates. In structured mode, execute the query over the intended graph scope before selecting results; do not infer exhaustiveness from top-20 reranking.

**Acceptance:** 100% agreement with the pinned reference implementation on the explicitly supported conformance test suite, with documented exclusions for unsupported features.

## 8. Structured Question Planner

### 8.1 Release design

Implement a deterministic **intermediate query representation (IR)** first. The IR is an inspectable data structure, not a free-form SPARQL string generated by an embedding model.

Suggested IR operators:

- `ResolveEntity`, `ResolveClass`, `ResolvePredicate`
- `Traverse(subject, predicate, direction, object)`
- `And`, `Or`, scoped `NotExists`
- `FilterNumeric`, `FilterDate`, `FilterDatatype`
- `CountDistinct`, `GroupBy`, `Having`
- `Project`, `OrderBy`, `Limit`
- `GraphScope`, `ProvenanceRequirement`

Use the retriever to rank candidate IRIs for labels such as “owned by” or “active contract”; verify schema compatibility, edge direction, and graph scope before compiling the plan. The exact compiler must parameterize or safely construct RDF terms and restrict predicates/operators to an approved vocabulary. Run only read-only, bounded queries for normal users.

### 8.2 First supported question families

1. Entity or concept lookup.
2. Find all entities of a resolved class.
3. Follow one directed relation to a known entity.
4. Combine two conditions with `AND`.
5. Follow a two-hop relation chain.
6. Compare typed numeric or date values.
7. Count distinct related objects and require a minimum/maximum.
8. Retrieve SHACL shapes relevant to a property or class.
9. Identify nodes that fail a supported SHACL constraint.

If the planner cannot resolve an essential predicate, direction, scope, or negation policy, return an explicit `needs_clarification` or `unsupported` status instead of inventing an answer.

### 8.3 Illustrative structured query

This is an **example ontology**, not an assertion about the user's actual RDF vocabulary:

```sparql
PREFIX ex: <https://example.org/ontology/>
SELECT ?supplier (COUNT(DISTINCT ?contract) AS ?activeCount)
WHERE {
  ?supplier a ex:Company ; ex:hasContract ?contract .
  ?contract ex:customer ex:OsloMunicipality ;
            ex:status ex:Active .
}
GROUP BY ?supplier
HAVING (COUNT(DISTINCT ?contract) >= 3)
```

The ontology resolver must discover the real class and predicate IRIs; the plan compiler should not hard-code the example names. The result can be exhaustive relative to the selected RDF graph and query semantics even when no vector search over supplier entities was used.

**Acceptance:** compare compiled query results to expert-authored gold SPARQL queries over the same frozen snapshot. Evaluate both exact answer-set F1 and whether the returned provenance supports each answer.

## 9. Graph Encoder Experiments (Optional Upgrade)

### 9.1 Default alignment strategy

**Start with a frozen EmbeddingGemma 2 encoder and its native 256-dimensional truncated search space.** Train the graph encoder plus a graph projection head to map node/shape representations into that space. This minimizes runtime changes and keeps temporary text embeddings for new nodes meaningfully comparable, subject to calibration tests.

Do not independently compare two 256-dimensional vector spaces without alignment. If later training introduces a learned text projection, export **the exact same projection** for online Rust inference; the default document-text fallback must pass through the matching representation path.

### 9.2 CompGCN implementation

1. Construct directed typed edges from resource-to-resource RDF triples, adding inverse relation IDs and self-loops.
2. Initialize node features from frozen embeddings of node identity/description views, augmented with carefully encoded categorical attributes; avoid solely learned ID vectors.
3. Initialize relation features from labels/descriptions or trainable embeddings; maintain stable predicate IDs.
4. Use two CompGCN message-passing layers with a tunable composition function (multiplication/subtraction/correlation) and normalization.
5. Use relation-stratified neighbor sampling (initial experiment: up to 15 edges per relation and direction per layer), with safeguards for rare or required edges.
6. Apply a 256-dimensional output projection and L2-normalize.
7. Compare with an R-GCN baseline under identical train/validation/test splits and compute budgets.
8. Cache graph embeddings offline; **no GNN execution on the online query path**.

### 9.3 Training data

Store one row per natural-language-to-target link, with at least:

`text`, `target_id`, `target_type`, `language`, `source`, `source_uri`, `named_graph`, `graph_snapshot_id`, `shape_snapshot_id`, `split`, `positive_group_id`, and `generation_template_version`.

Sources: labels/definitions, directed triple verbalizations, natural question templates, reviewed user questions, SHACL explanations, and sourced document passages. Include meaningful Norwegian/English pairs. Tag the target role explicitly for a path description: start node, end node, predicate, shape, or another declared type.

Build **multi-positive** text↔graph contrastive training masks to avoid treating several correct resources for one question as negatives. In-batch negatives must exclude known positives and ambiguous cases. Add hard negatives from verified structural distinctions (including same-class, different-predicate cases), but never assume an absent triple proves falsity under the open-world assumption.

Suggested objective: multi-positive contrastive retrieval loss, with modest optional auxiliary losses for relation/type or link prediction. Tune temperature on validation data; retain training-time temperature and calibration settings in the model manifest.

### 9.4 Training and evaluation protocol

- Keep separate held-out query formulations for ordinary retrieval quality.
- Add named-graph, domain, time-based, and new-node holdouts for transfer and graph-drift evaluation.
- Prevent leaked future edges or unseen test nodes from entering graph message passing in an inductive test.
- Use early stopping on retrieval metrics rather than training loss.
- Run ablations: remove relation types, reverse edge directions, remove hard negatives, remove SHACL-generated data, and remove node initial text features.
- Monitor modal collapse, oversmoothing, per-dimension variance, high-degree-node errors, and performance on unseen entities.

### 9.5 Graph encoder promotion gate

Promote CompGCN only if, on a locked independent relational-question test set:

- Recall@10 improves by **at least 10 absolute percentage points** over the text-only baseline.
- MRR/nDCG and cross-lingual performance do not show unacceptable regressions.
- Improvements persist across three random seeds and at least one held-out domain/time/new-node evaluation.
- The expanded build, refresh, and operational cost is justified by the gain.

If the gate fails, retain the text-plus-lexical-plus-SPARQL architecture, and evaluate a targeted reranker or R-GCN before further GNN complexity.

## 10. Rust Runtime and Interface Contracts

### 10.1 Core modules

| Module | Responsibilities |
|---|---|
| `rdf_store` | Oxigraph store lifecycle, named-graph selection, snapshot access, safe SPARQL execution. |
| `text_encoder` | Tokenization, ONNX invocation, pooling, MRL truncation, L2 normalization. |
| `vector_index` | Memory mapping, manifest verification, SIMD scan, top-k selection. |
| `lexical_index` | Exact-term and BM25 lookup. |
| `registry` | Object IDs, IRIs, type/class/language metadata, provenance. |
| `retrieval` | Candidate fusion and filtering. |
| `planner` | Intent detection, IR creation, vocabulary resolution, plan validation. |
| `sparql_compiler` | Restricted IR-to-SPARQL compilation. |
| `shape_validator` | Supported SHACL subset, traceable validation results. |
| `api` | HTTP/CLI input/output, error handling, metrics. |
| `bundle_manager` | Model/index/graph version checks and atomic activation. |

### 10.2 Suggested API

- `POST /v1/search`: ranked relevant RDF objects; `k`, object types, named graphs, and optional validation requested.
- `POST /v1/ask`: ask a supported structured question; return rows, query-plan summary, answer-set scope, and evidence.
- `POST /v1/validate`: validate specified focus nodes against specified supported shapes.
- `GET /v1/status`: active snapshot, model/index versions, supported features, health.
- Administrative CLI commands: `ingest`, `index-build`, `verify-bundle`, `activate-bundle`, `benchmark`.

Illustrative answer envelope:

```json
{
  "status": "verified",
  "mode": "structured",
  "graph_snapshot_id": "graph-2026-10-14-a",
  "model_id": "embeddinggemma2-text-256-v1",
  "results": [{"rdf_term": "https://example.org/company/123", "evidence": []}],
  "complete_within_scope": true,
  "scope": {"named_graphs": ["https://example.org/source/registry"]},
  "plan_id": "plan-7f23"
}
```

`complete_within_scope` must be `false` or omitted for finite top-*k* candidate retrieval; only a successfully executed exhaustive formal plan may claim it within the explicitly stated graph scope and semantics.

### 10.3 Index read safety and scoring

- Verify checksums, dimensions, row count, endianness, finiteness, normalization tolerances, and registry alignment before serving queries.
- Use SIMD dot products for normalized vectors; test against a scalar reference implementation.
- Benchmark cold and warm memory mapping separately. Mapping a file does not guarantee that its pages are resident or that first-query latency is zero.
- Track exact per-stage p50/p95/p99 latency rather than only vector scan time.

## 11. Updates, Versioning, and Refresh

Use a two-tier index lifecycle:

1. **Immutable base bundle:** graph snapshot, embeddings, registry, tokenizer, model, and shapes manifest.
2. **Mutable delta index:** new/changed node text embeddings and a tombstone set for removed objects, with provenance and a clear update watermark.
3. **Serving snapshot:** Oxigraph read view pinned for each request. The response identifies which graph version was checked and whether any graph-based embeddings were computed on an older snapshot.

When graph edges change, two-hop CompGCN embeddings for neighboring nodes may become stale. Track changed nodes and the affected neighborhood; prefer a periodic rebuild or an explicit `structural_index_stale` status over claiming perfect freshness. Do not silently mix embeddings from incompatible **model/projection spaces**.

Build a replacement bundle, verify parity and regression suites, and atomically switch the active bundle pointer. Retain the prior bundle for rollback. Document the policy for partial imports, failed builds, deleted resources, and backward-incompatible ontology revisions.

**Acceptance:** crash and rollback tests show that a request never sees a mismatched registry/vector pair or an unacknowledged change of model space.

## 12. Testing and Evaluation

### 12.1 Test dataset

Prepare a frozen gold set with **all valid answers known where feasible**, sourced from expert-authored SPARQL, reviewed user questions, and verified graph snapshots. Cover:

- Entity/concept lookup; exact IRI or identifier lookup.
- One-hop relations with direction changes and near-identical labels.
- Two-hop and multi-constraint relations.
- SHACL shape retrieval and data-quality violations.
- Counts, comparison operators, dates, conjunction, and scoped negation.
- Norwegian questions over English-labeled graphs.
- New/changed nodes, partial/contradictory sources, high-degree hubs, rare classes.
- Questions with no supported answer, unknown answer, or unsupported operations.

### 12.2 Comparison matrix

| System | Retrieval | Structured execution |
|---|---|---|
| B0: lexical BM25 | Baseline | No, unless explicit template resolves. |
| B1: EmbeddingGemma text only | Baseline | Supported templates. |
| B2: lexical + embedding + RDF filtering | Expected initial production candidate | Supported templates. |
| B3: B2 + reranker | Optional quality alternative | Supported templates. |
| B4: B2 + R-GCN alignment | Controlled GNN alternative | Supported templates. |
| B5: B2 + CompGCN alignment | Experimental proposed architecture | Supported templates. |

### 12.3 Metrics and proposed gates

| Metric | Use / initial gate |
|---|---|
| Recall@1/10/20/100, MRR, nDCG@10 | Retrieval quality by query family and language. |
| Absolute Recall@10 gain on relational queries | **≥10 percentage points** for CompGCN promotion. |
| Exact-result precision/recall/F1 | Measure structured-answer correctness against gold SPARQL. |
| Planner intent/IR accuracy | Track separately from retrieval and SPARQL execution. |
| Constraint agreement | **100%** on the specifically supported and pinned SHACL test suite. |
| Evidence coverage | Every `verified` answer must carry a reproducible graph-derived justification. |
| Latency | Per-stage p50/p95/p99 on a declared CPU, question length, dataset, and cache state. |
| RAM/size/startup | Record full resident memory (including ONNX session), on-disk artifacts, and cold/warm startup. |
| Freshness/regressions | Run fixed canary questions on every graph import and model release. |

**Performance targets (hypotheses, not guaranteed specifications):** start by measuring typical short-query p95, long-query p95, cold vs warm indexing, and aggregate queries under load. Define release latency budgets after the first target-hardware benchmark rather than promising 5–15 ms full-query latency in advance.

## 13. Security and Reliability

- Default to read-only SPARQL for user-facing requests; prevent arbitrary SPARQL update and unrestricted remote-service clauses.
- Enforce named-graph permissions before retrieval, plan construction, and evidence rendering—not only after the final result is produced.
- Put limits on query timeout, join expansion, path depth, returned rows, and memory; reject pathological plans.
- Validate and sanitize RDF terms and user-controlled filters using a typed AST rather than naive string interpolation.
- Avoid storing raw confidential user questions in logs by default; document retention and deletion behavior.
- Capture structured errors for ambiguity, no evidence, unsupported constraint, stale index, timeout, and corrupt bundle.
- Test reproducibility, rollbacks, filesystem permissions, local/offline operation, and third-party binary/model license obligations.
- Document the model license and any separate acceptable-use requirements for the chosen model release.

## 14. Proposed Delivery Phases

**Indicative schedule:** 16–20 engineering weeks for a small team (one Rust engineer, one ML engineer, one RDF/semantic engineer, with part-time domain review). This is a planning estimate, not a commitment; graph quality and ontology complexity can change the duration substantially.

| Phase | Timing (indicative) | Work | Exit artifact / gate |
|---|---|---|---|
| 0. Requirements and benchmark | Weeks 1–2 | Choose ontology, dataset, exact question families, semantics contract, target CPU, gold set. | Signed-off scope and frozen benchmark definition. |
| 1. Ingestion and vocabulary | Weeks 3–4 | Oxigraph ingestion, named graphs, IDs, shape AST, provenance, verbalization. | Reproducible dataset and resource registry. |
| 2. Baseline runtime | Weeks 5–7 | EmbeddingGemma ONNX export, Rust parity, index, BM25, search API. | Working local Norwegian→English search. |
| 3. Formal checking | Weeks 8–10 | SHACL subset, validation traces, SPARQL integration and reference tests. | Verified candidate search with scoped evidence. |
| 4. Structured planner | Weeks 11–13 | Intent routing, typed IR, safe SPARQL compiler, counts/joins/filters. | Controlled multi-condition question answering. |
| 5. GNN experiment | Weeks 14–16 | PyG R-GCN and CompGCN, multi-positive training, ablations, holdouts. | Promotion/rejection report against +10 pp gate. |
| 6. Hardening and pilot | Weeks 17–20 | Delta indexing, bundle activation, regression suite, latency/security tests. | Pilot release with monitored quality and rollback. |

### 14.1 Phase-by-phase checklists

**Phase 0 — foundations**
- [ ] Freeze example RDF/SHACL datasets and expected-answer queries.
- [ ] Declare graph scope and entailment rules.
- [ ] Specify which questions require exhaustive results.
- [ ] Record the target CPU/RAM and latency measurement methodology.

**Phase 1 — data ingestion**
- [ ] Make imports deterministic and preserve named graphs.
- [ ] Implement stable object registry and shape AST.
- [ ] Generate traceable multilingual resource verbalizations.
- [ ] Add data-quality checks and import reports.

**Phase 2 — searchable baseline**
- [ ] Validate Python↔Rust embedding parity.
- [ ] Build flat index and lexical index with integrity checks.
- [ ] Implement search and object metadata APIs.
- [ ] Establish baseline Recall@k and runtime measurements.

**Phase 3 — exact validation**
- [ ] Define a supported SHACL constraint matrix.
- [ ] Implement typed AST compilation and per-focus-node reports.
- [ ] Differential-test against a reference validator.
- [ ] Return explicit unsupported/unknown statuses.

**Phase 4 — question planner**
- [ ] Add intent routing and schema/predicate resolution.
- [ ] Implement restricted query IR and safe compiler.
- [ ] Test joins, counts, comparisons, and source scope.
- [ ] Prevent top-*k* search from masquerading as an exhaustive answer.

**Phase 5 — graph ML**
- [ ] Freeze text embeddings and build multi-positive pairs.
- [ ] Train R-GCN and CompGCN under matched conditions.
- [ ] Run leakage-safe relational and cross-lingual evaluation.
- [ ] Promote CompGCN only after the agreed uplift gate.

**Phase 6 — release engineering**
- [ ] Implement base+delta lifecycle and atomic version activation.
- [ ] Run canary queries on every import or release.
- [ ] Benchmark cold/warm p95 and p99 on the real CPU.
- [ ] Test permission boundaries, timeouts, failures, and rollback.

## 15. Repository and Artifacts

```text
rdf-query-engine/
  Cargo.toml
  crates/
    api/
    rdf_store/
    registry/
    text_encoder/
    lexical_index/
    vector_index/
    retrieval/
    planner/
    sparql_compiler/
    shape_validator/
    bundle_manager/
  ml/
    data_build/
    encoders/
    compgcn/
    rgcn/
    losses/
    train/
    export/
    evaluation/
  tests/
    fixtures/rdf/
    fixtures/shacl/
    gold_queries/
    rust_python_parity/
    regression/
  configs/
    dataset.yaml
    inference.yaml
    evaluation.yaml
  artifacts/                 # generated, normally not committed
    releases/<release_id>/
      graph_snapshot/
      registry.parquet
      shapes_ast.json
      vectors.bin
      nodes.index
      text_model.onnx
      tokenizer.json
      model_manifest.json
      index_manifest.json
      checksums.sha256
  docs/
    architecture.md
    semantic_contract.md
    supported_shacl.md
    api.md
    benchmark_methodology.md
    deployment.md
```

**Version-controlled:** source code, pinned dependencies, configurations, schemas, reproducible data-preparation rules, test fixtures, evaluation definitions.  
**Versioned external artifacts:** original RDF release, large trained weights, graph snapshot, vector files, model exports, manifests, and benchmark reports.

## 16. Primary Risks and Mitigations

| Risk | Likely consequence | Mitigation |
|---|---|---|
| CompGCN adds little beyond rich textual neighborhoods | High training cost without retrieval uplift | Strong text+lexical baseline and explicit 10 pp gate. |
| False negatives from incomplete RDF | Misleading alignment and weak recall | Multi-positive masks and verified structural negatives. |
| Retrieval top-*k* misses valid entities | Incomplete structured answers | Use graph-first exhaustive SPARQL for structured mode. |
| Relations are directionally ambiguous | Incorrect plans and explanations | Typed predicate resolution and direction tests. |
| SHACL AST flattening changes logic | Incorrect validation | Preserve semantics in AST; differential validation. |
| New nodes use uncalibrated text vectors | Ranking anomalies | Frozen common space, score calibration, delta index tests. |
| Graph changes stale two-hop embeddings | Missed or misranked results | Track affected neighborhoods, expose freshness, rebuild. |
| ONNX conversion changes representations | Silent retrieval regression | Python↔Rust parity, finite-value checks, model checksum. |
| Complex graph queries consume resources | Slowdowns or denial of service | Restricted IR, limits, deadlines, read-only execution. |
| License or binary packaging issues | Blocked deployment | Verify model/license obligations and runtime packaging early. |

## 17. Definition of Done

Release the pilot only when the following are all true:

- [ ] A clean offline installation starts one Rust process with a local model, index, and Oxigraph dataset.
- [ ] Norwegian questions can retrieve English-described graph objects with measured, documented Recall@k.
- [ ] All accepted results identify the relevant RDF terms and graph snapshot; any `verified` claim includes checkable evidence.
- [ ] The explicitly supported SHACL subset passes pinned reference tests; unsupported shapes are marked as such.
- [ ] Supported structured question families produce answer sets that match expert-authored gold SPARQL within the chosen graph scope.
- [ ] Users can distinguish approximate retrieval results from exhaustive formal answers.
- [ ] Python→ONNX→Rust embedding parity and index/registry consistency tests pass.
- [ ] Bundle mismatches, stale embeddings, and failures are surfaced rather than hidden.
- [ ] The system meets performance and memory targets measured on the nominated target machine.
- [ ] There is a documented rollback procedure and a fixed regression suite for every dataset/model change.
- [ ] CompGCN is used in production **only if** its independent evaluation crosses the agreed improvement threshold.

## 18. Final Recommendation

Deliver the product in **two independently useful layers**:

1. **RDF-aware retrieval and verification:** EmbeddingGemma 2, lexical search, Oxigraph, provenance, and a bounded SHACL evaluator. This should be the first production-quality milestone.
2. **Compositional question answering:** a typed query planner resolving RDF entities/predicates into SPARQL joins, counts, filters, and constraints. This is the most important extension for exact multi-condition questions.

Treat **CompGCN as a measurable enhancement, not a foundational dependency**. It may improve candidate ranking, but it does not remove the need for explicit query planning or exact graph semantics.

## 19. Reference Documentation

The implementation decisions above combine the supplied architecture notes with these technical references:

- [Google: EmbeddingGemma 2 model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2)
- [Google: EmbeddingGemma 2 with Sentence Transformers](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers)
- [Oxigraph Rust `Store` API](https://docs.rs/oxigraph/latest/oxigraph/store/struct.Store.html)
- [ONNX Runtime `ort` Rust API](https://docs.rs/ort/latest/ort/)
- [PyTorch Geometric R-GCN operator](https://pytorch-geometric.readthedocs.io/en/latest/_modules/torch_geometric/nn/conv/rgcn_conv.html)
- [W3C SHACL Recommendation (2017)](https://www.w3.org/TR/shacl/)
- [W3C SHACL 1.2 Core Working Draft (2026)](https://www.w3.org/TR/shacl12-core/)
- [pySHACL reference validator](https://github.com/RDFLib/pySHACL)

**Standards policy:** use the 2017 W3C SHACL Recommendation as the first production validation contract. SHACL 1.2 Core remained a Working Draft in October 2026 and should be evaluated/versioned separately rather than silently treated as stable.