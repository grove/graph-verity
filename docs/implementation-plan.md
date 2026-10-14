# RDF-Native Semantic Retrieval and Query Engine
## Detailed Implementation Plan

**Document date:** 14 October 2026  
**Status:** Proposed engineering plan  
**Initial scale:** 10,000–100,000 searchable RDF resources  
**Primary languages:** Norwegian questions; Norwegian and English graph labels  
**Runtime:** Local Rust process, without an external database or hosted AI inference service

## 1. Executive Summary

Build **Graph Verity**, a local-first Rust engine for natural-language exploration and verifiable question answering over RDF knowledge graphs. The MVP combines multilingual hybrid retrieval, ontology-aware semantic parsing, deterministic typed-IR-to-SPARQL compilation, and evidence from the actual graph.

The two main user-facing operations are:

1. **Find:** EmbeddingGemma 2 + BM25 locate entities, classes, predicates and SHACL shapes. An optional local cross-encoder improves ranking where it is worth the CPU cost. Exact checks can verify requested facts about candidates.
2. **Ask:** Retrieve a bounded set of actual RDF vocabulary terms; a small **local generative semantic parser** produces grammar-constrained JSON describing a query plan; Rust validates the typed IR against the schema, ontology, permissions and graph scope; a deterministic compiler produces read-only SPARQL for Oxigraph.

**Separation of responsibilities:** embeddings/rerankers estimate relevance; grammar constrains *output syntax, not semantic correctness*; typed IR validation constrains legal operations and references; SPARQL/SHACL provide verifiable evidence within the selected graph snapshot and semantics.

**MVP decisions:** start with two Rust crates, reuse SHACL libraries before building custom validation, prioritize the semantic parser, and benchmark optional reranking. **Defer CompGCN/R-GCN to post-MVP research.** Performance claims and success probabilities from architecture reviews are hypotheses, not guarantees. The proposed schedule is gate-driven and must be revised against real engineering capacity.

## 2. Goals, Scope, and Non-Goals

### 2.1 Product goals

1. Understand Norwegian questions over RDF data with English and/or Norwegian labels and descriptions.
2. Retrieve entities, classes, predicates, and SHACL shapes while preserving direction, RDF datatypes, named graphs and provenance.
3. Support **retrieval mode** for ranked discovery and **structured question mode** for supported complete-within-scope graph answers.
4. Return resolved RDF IRIs, graph snapshot, query-plan summary, formal result status and inspectable supporting triples/constraint reports.
5. Run locally in a Rust process with Oxigraph and ONNX Runtime, plus a local quantized generative semantic parser backend; never require a hosted AI API.
6. Pin and validate model, tokenizer, grammar, IR schema, vocabulary, index, graph and SHACL-semantic versions.

### 2.2 MVP boundary

- One well-defined RDF domain, initially 10,000–100,000 indexed resources and a fixed target CPU.
- **Controlled** question families: entity/class lookup, direct/two-hop traversal, conjunction, numeric/date comparisons, `COUNT(DISTINCT ...)` / `HAVING`, shape lookup, and violations in a supported SHACL subset.
- A versioned, typed JSON IR with explicit direction, scope, variables and typed values. The generator may select *only retrieved/authorized ontology IDs*; it may not invent RDF terms or raw SPARQL.
- Evaluate a maintained Rust SHACL implementation (Rudof/`shacl`) first. If needed, implement an explicit **2017 SHACL Core subset**: simple predicate paths, `sh:minCount`, `sh:maxCount`, `sh:datatype` and `sh:class`, tested against a reference validator.
- Text/BM25 retrieval baseline first, optional cross-encoder reranking after benchmark; no required GNN research for pilot release.
- Declare a graph-completeness/entailment policy and separate accuracy, latency and memory gates for retrieval, parsing, compiled queries and validation.

### 2.3 Explicit non-goals for first release

- Unrestricted natural-language-to-SPARQL or arbitrary questions with guaranteed correctness.
- Assuming a schema-valid JSON plan is semantically correct; the parser may still choose the wrong operator or predicate.
- Full SHACL 1.2/advanced constraints, arbitrary OWL entailment, or custom full-featured SHACL parsing/validation.
- Unrestricted SPARQL, write operations, remote `SERVICE`, or implicitly treating absence of a triple as evidence of falsity.
- Top-*k* vector retrieval presented as exhaustive graph query results.
- CompGCN/R-GCN and two-hop graph-embedding freshness machinery in the 20-week MVP schedule.
- Putting the entire dataset, models and indexes into a single executable; one offline-capable process with versioned local artifacts suffices.

## 3. Reference Architecture

~~~text
                      Offline ingestion / index preparation
RDF dataset + SHACL shapes + named graphs
             |
             +--> Oxigraph snapshot + provenance + ontology vocabulary catalog
             +--> resource/shape verbalization --> EmbeddingGemma --> vector index
             +--> resource/shape labels/IDs --------------------------> BM25
             +--> SHACL parser/library --> validated shape AST / cached templates
             |
             +--> compatible, versioned release bundle

                           Online Rust process
Natural-language question
             |
             +--> EmbeddingGemma + BM25 --> candidate entities/predicates/classes
             |                                   |
             |                           optional cross-encoder reranker
             |
             +--> intent router: find | ask | validate | unsupported
                         |                    |
                       find                  ask
                         |                    |
                  candidate checks    ontology-aware context
                                              |
                                   small local constrained generator
                                              |
                                       typed JSON IR
                                              |
                              schema + ontology + auth validation
                                              |
                               deterministic SPARQL compilation
                                              |
                                           Oxigraph
                         |                    |
                         +--------------------+
                                              |
                          result / evidence / scope / provenance /
                             SHACL report / explicit status
~~~

**No raw generated SPARQL:** the parser's JSON grammar limits structure, but a separate validator must verify selected class/predicate/entity IDs, edge direction, variable binding, datatype, operator semantics, authorized named graphs and resource limits. Unsupported or ambiguous plans abstain.

**No completeness from top-k:** for questions requiring all matching entities, vocabulary retrieval is allowed to *ground the query*, but SPARQL must evaluate all matching entities in the requested data scope. GNN experiments are separate post-MVP work, not part of this serving flow.

## 4. Technology Decisions

| Layer | MVP choice | Rationale / validation |
|---|---|---|
| Text retrieval | EmbeddingGemma 2 text encoder; 768→256 MRL truncation and L2 normalization | Multilingual and compact; benchmark on Norwegian↔English RDF questions, not only generic embedding leaderboards. |
| Lexical retrieval | Rust BM25 index, e.g. Tantivy | Exact names, codes, datatype terms, IRIs and rare labels. |
| Retrieval fusion | BM25 + vector search using rank fusion | Measure first-stage Recall@50 independently of reranking. |
| Reranking | **Optional** multilingual local cross-encoder | Evaluate top 10/20/50 candidates; measure uplift against B2 and real p95/RAM on target hardware. |
| Semantic parser | **Small local quantized instruction model** with grammar/JSON-constrained output, initially benchmark ~1.5B class | Integrate behind a Rust interface; evaluate llama.cpp first. Smaller/larger models and ONNX are possible, but constrained decoding is an additional requirement. |
| Query planning | Versioned typed JSON IR + deterministic Rust IR-to-SPARQL compiler | Controlled operators, bindings, scope and ontology IDs; no generated arbitrary SPARQL. |
| RDF execution | Oxigraph (`Store::new` / persistent store as appropriate) | In-process quad store and scoped read-only SPARQL. |
| SHACL | Evaluate Rudof/`shacl` first; SPARQL SELECT templates for *bounded supported subset* if needed | Pin 2017 SHACL semantics, test with pySHACL and relevant W3C fixtures; compile/cache templates on shape update. |
| Serving | `verity_core` Rust library + `verity_cli` binary (two crates) | Internal Rust modules and `pub(crate)` initially; split more only with a demonstrated need. |
| ML development | Python, PyTorch, ONNX export where needed | Offline indexing/evaluation; Python not required by the serving engine. |
| Graph ML | **Post-MVP research:** CompGCN vs R-GCN | Require quality gain over the strongest production baseline, including any adopted reranker. |

**Numerical precautions:** correct query/document prompt formatting; identical Python/Rust tokenizer and pooling; truncate native embedding to 256 and re-normalize; reject non-finite values; verify quantized ONNX parity; treat FP16 cautiously per the model card.

**Do not hard-code claimed speedups:** 100,000 × 256 × 4 bytes = **102.4 MB decimal** of raw FP32 vectors, but memory mapping does not guarantee a cold scan under 3 ms, and full query latency includes tokenization, inference, semantic parsing, SPARQL and evidence generation. Benchmark those separately.

## 5. Data Model, Ingestion, and Provenance

### 5.1 Ingestion pipeline

1. Accept RDF in an explicit set of serializations (initially Turtle, TriG, and N-Quads).
2. Parse and validate input; quarantine malformed graphs, malformed literals, and unsupported dataset conventions.
3. Preserve IRIs, language tags, literal datatypes, predicate direction, named graph identifiers, and source provenance.
4. Load data quads into Oxigraph. Keep the shapes graph logically separate and versioned, even if stored in a dedicated named graph.
5. Generate a deterministic RDF snapshot ID from canonicalized release inputs plus import configuration, not from nondeterministic insertion order.
6. Extract a **versioned ontology vocabulary catalog**: classes, predicates, human-readable labels, direction, datatype/domain/range hints, authorized scope and examples, with stable candidate IDs for the semantic parser.
7. Create a searchable resource registry: entity IDs, shape IDs, optional class and predicate IDs, and associated metadata.

### 5.2 Blank nodes and SHACL lists

- Do not assume blank-node labels remain stable across imports.
- Prefer a maintained RDF/SHACL parser (evaluate Rust Rudof first); preserve RDF lists and nested shape logic in a **typed shape AST** with operator, path, cardinality and ordering semantics intact.
- For ML verbalization only, derive deterministic synthetic identifiers/edges from that AST. Keep original RDF for formal evaluation.
- Avoid silently converting a list such as `sh:or` into unrelated bag-of-words properties.
- If using a custom bounded validator, compile supported shape AST nodes to **cached SELECT violation templates during ingestion/shape updates**, keyed to the pinned SHACL semantics, graph scope and shapes version.

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
- Support type, named-graph, and language filtering; only apply a filter when requested or semantically justified by a validated plan. Enforce **authorization** before exposing vocabulary or candidate text to the local parser.
- Produce candidate lists at configurable `k` (10, 20, 50, 100, 500) and track Recall@k, **especially pre-rerank Recall@50**, separately from any reranking gains.
- Use vector similarity only for discovery/ranking; a vector hit alone is never marked “verified.”
- Record search diagnostics (without storing confidential raw questions by default): stage latencies, index version, candidate count, and reason for no result.

### 6.3 Vector format

At 100,000 resources, `100000 × 256 × 4 = 102,400,000` bytes of raw vectors (102.4 MB decimal; approximately 97.7 MiB). The file format should include a versioned header or companion manifest, followed by contiguous little-endian FP32 rows. A row-to-ID mapping must be covered by the same integrity hash.

**Index-bundle manifest:** `format_version`, `dimension`, `dtype`, `normalization`, `row_count`, `resource_registry_hash`, `model_hash`, `tokenizer_hash`, `preprocessing_hash`, `graph_snapshot_id`, `shape_snapshot_id`, `index_build_id`, and file checksums.

**Acceptance:** a deterministic Python/Rust parity test produces closely matching vectors, and a Rust scan returns the same top-k ranking as the Python reference within specified floating-point tolerance.

## 7. Exact RDF and SHACL Validation

### 7.1 Formal semantics contract

- Relevance, factual verification, SHACL conformance, and exhaustive answer-set completeness are different claims.
- Pin **W3C SHACL Recommendation (2017)**, snapshot, graph scope, and class/entailment semantics. SHACL 1.2 is a separate future version, not silently assumed stable.
- RDF is commonly open-world. A missing triple alone cannot justify “does not have” unless a scoped completeness policy explicitly allows it.
- Return explicit statuses, e.g. `verified`, `nonconformant`, `unknown`, `unsupported`, `needs_clarification` and `execution_error`.
- A node failing a shape can be highly relevant to a question about violations.
- Formal verification of a handful of candidates does **not** prove that every matching node was found.

### 7.2 Reuse, then optimize a supported subset

1. Assess the Rust Rudof/`shacl` implementation first for shape parsing, validation, reporting and integration with Oxigraph. Do not build a full custom SHACL parser or traversal engine by default.
2. Pin a reference pySHACL version and the relevant W3C fixture suite. Define a supported-constraint matrix and explicit unsupported statuses.
3. If library integration is not viable or a fast path is justified, retain typed SHACL ASTs and **compile supported shapes into cached, parameterized/safely bound SPARQL SELECT violation queries** during shape ingestion/change.
4. `sh:minCount` and `sh:maxCount` require the correct distinct focus/value-node counting under the declared graph scope.
5. `sh:class` must correctly handle subclass membership; a query path equivalent to `rdf:type/rdfs:subClassOf*` is appropriate **where the chosen entailment policy and available triples permit it**. Test against reference semantics.
6. `sh:datatype` must handle literal-vs-resource distinctions, datatype matching and ill-typed lexical values under the selected SHACL semantics; simply comparing datatype IRIs is not always enough.
7. Return structured reports: focus node, shape, path, offending/missing value when applicable, constraint, source graph, severity and snapshot; unsupported constructs must never be silently marked conformant.

**Acceptance:** 100% differential parity on a **pinned and documented supported test subset** (not a claim of full SHACL conformance), including subclass, datatype, named-graph, blank-node and cardinality edge cases. Benchmark runtime on real CPU; avoid promises of microsecond checks or halved implementation time.

For complete structured questions, execute the formal graph plan across the authorized graph scope; do not use top-*k* candidate sets as an implicit query filter.

## 8. Ontology-Aware Semantic Parser and Structured Question Planner

**This is the critical MVP component missing from a retrieval-only design.** EmbeddingGemma ranks relevant terms but cannot itself parse arbitrary Norwegian word order, logical precedence, numbers and relational conditions into a query AST.

### 8.1 Typed intermediate representation (IR)

Build the versioned JSON IR **and deterministic compiler before model integration**. Restrict operators and validate all inputs:

- `ResolveEntity`, `ResolveClass`, `ResolvePredicate` (references must resolve to IDs in the versioned vocabulary catalog)
- `Traverse(subject, predicate_id, direction, object)`, `And` and bounded `Or`
- `FilterNumeric`, `FilterDate`, `FilterDatatype`, `CountDistinct`, `GroupBy` and `Having`
- `Project`, `OrderBy`, `Limit`, `GraphScope` and `ProvenanceRequirement`
- `NotExists` **only** if the dataset's completeness policy justifies the negative interpretation

Illustrative IR (a conceptual sketch, **not the final JSON Schema**; catalog IDs are resolved before execution):

~~~json
{
  "ir_version": 1,
  "root_type_id": "catalog:Company",
  "graph_scope_id": "scope:contracts",
  "bindings": [
    {"op": "Traverse", "from": "supplier", "predicate_id": "catalog:hasContract", "direction": "out", "to": "contract"},
    {"op": "Traverse", "from": "contract", "predicate_id": "catalog:customer", "direction": "out", "to_entity_id": "catalog:OsloMunicipality"},
    {"op": "Traverse", "from": "contract", "predicate_id": "catalog:status", "direction": "out", "to_entity_id": "catalog:Active"}
  ],
  "aggregate": {"op": "CountDistinct", "variable": "contract", "as": "active_count"},
  "having": {"variable": "active_count", "comparison": ">=", "value": 3},
  "project": ["supplier", "active_count"]
}
~~~

### 8.2 Semantic parsing pipeline

1. **Route:** determine whether to retrieve, answer a supported structured question, validate, request clarification, or reject an unsupported question.
2. **Ground:** retrieve a small, authorized set of candidate entities, predicates, classes, datatype hints, direction and named graph scopes using BM25 + EmbeddingGemma. Context comes from the current vocabulary catalog, not a free-floating language-model guess.
3. **Generate:** a local, quantized instruction model (evaluate a roughly 1.5B-class model first) selects from these terms and produces **grammar-constrained JSON IR** through a backend such as llama.cpp. ONNX is an alternative only when constrained decoding is implemented. **No raw SPARQL from the model.**
4. **Validate:** check JSON Schema, IR version, permitted operators, authorized catalog IDs, edge direction, class–predicate compatibility, variable binding, datatype/comparison correctness, graph permissions, max path depth, complexity and query scope.
5. **Abstain on uncertainty:** invalid/missing IDs, ambiguous direction, unsupported negation, unidentified operator precedence or unresolved scope produce `needs_clarification` / `unsupported`. Do not repair guesses by silently choosing a likely relation.
6. **Compile and execute:** deterministic Rust compiler emits controlled read-only SPARQL with validated/bound RDF terms, time/row/resource limits and no remote `SERVICE` or arbitrary updates; Oxigraph evaluates it.
7. **Explain:** return resolved term IDs, plan summary, result scope and provenance, evidence, query snapshot and honest completeness status.

**Critical limitation:** grammar-constrained output guarantees at most structural JSON correctness; a well-formed plan can still express the wrong meaning. Measure **semantic IR accuracy** and **answer-set accuracy** independently.

### 8.3 Supported question families

Start with entity/class lookup, one directed relation, conjunction, two-hop paths, numeric/date comparison, distinct counts with bounded `HAVING`, shape search, and supported SHACL violations. Add families only after passing gold regression tests.

Illustrative gold SPARQL for a made-up ontology (the compiler must resolve *actual* RDF terms rather than hard-code these IRIs):

~~~sparql
PREFIX ex: <https://example.org/ontology/>
SELECT ?supplier (COUNT(DISTINCT ?contract) AS ?activeCount)
WHERE {
  ?supplier a ex:Company ; ex:hasContract ?contract .
  ?contract ex:customer ex:OsloMunicipality ;
            ex:status ex:Active .
}
GROUP BY ?supplier
HAVING (COUNT(DISTINCT ?contract) >= 3)
~~~

For structured questions, the retriever supplies likely *ontology terms*, not a limited list of answer rows. A complete result is possible only **relative to a declared graph scope, semantics and successfully executed query**.

### 8.4 Planner test and promotion gate

Compare generated IR with expert-authored reference IR/SPARQL over frozen snapshots. Hold out Norwegian paraphrases, reversed predicates, dates, “more than” vs “at least,” scoped negation, nested constraints and graph changes. Include ambiguity, missing evidence, unsupported logic and malicious prompt text inside RDF labels.

Measure: schema-valid vs actually correct IR, exact operator/predicate/direction/value/scope accuracy, execution success, gold answer precision/recall/F1, abstention quality, and full parser CPU p95/RAM. **Define numeric release thresholds in Phase 0** from the target dataset and device; do not infer them from general LLM benchmarks.

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