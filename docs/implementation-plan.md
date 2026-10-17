# Graph Verity — RDF Semantic Retrieval & Question Answering
## Detailed Implementation Plan, Revised MVP

**Revised status:** 17 October 2026

**Status:** Historical architecture proposal, superseded for active scope/schedule by the [Phase 0 STOP/REVISE decision](phase-0-decision.md). The deterministic Rust foundation, local parser experiments and evaluation tooling are implemented. Tested unattended Qwen Ask failed; the next MVP is Find-first (#36–#39), with optional confirmed Ask (#40). Sections below preserve broader design alternatives, not approved release requirements.

**Initial scale:** 10,000–100,000 searchable RDF resources  
**Primary languages:** Norwegian questions; Norwegian and English graph labels  
**Runtime:** Local Rust process, without an external database or hosted AI inference service

## 1. Executive Summary

Build **Graph Verity**, a local-first Rust engine for natural-language exploration and verifiable question answering over RDF knowledge graphs. The MVP combines multilingual hybrid retrieval, ontology-aware semantic parsing, deterministic typed-IR-to-SPARQL compilation, and evidence from the actual graph.

The two main user-facing operations are:

1. **Find:** EmbeddingGemma 2 + BM25 locate entities, classes, predicates and SHACL shapes. An optional local cross-encoder improves ranking where it is worth the CPU cost. Exact checks can verify requested facts about candidates.
2. **Ask:** Retrieve a bounded set of actual RDF vocabulary terms; a small **local generative semantic parser** produces grammar-constrained JSON describing a query plan; Rust validates the typed IR against the schema, ontology, permissions and graph scope; a deterministic compiler produces read-only SPARQL for Oxigraph.

**Separation of responsibilities:** embeddings/rerankers estimate relevance; grammar constrains *output syntax, not semantic correctness*; typed IR validation constrains legal operations and references; SPARQL/SHACL provide verifiable evidence within the selected graph snapshot and semantics.

**MVP decisions:** run a small local-model semantic-parsing feasibility spike in Phase 0, before investing in the complete retrieval/verification stack; start with two Rust crates, reuse SHACL libraries before building custom validation, prioritize the semantic parser, and benchmark optional reranking. **Defer CompGCN/R-GCN to post-MVP research.** Performance claims and success probabilities from architecture reviews are hypotheses, not guarantees. The proposed schedule is gate-driven and must be revised against real engineering capacity.

## 2. Goals, Scope, and Non-Goals

### 2.1 Product goals

1. Understand Norwegian questions over RDF data with English and/or Norwegian labels and descriptions.
2. Retrieve entities, classes, predicates, and SHACL shapes while preserving direction, RDF datatypes, named graphs and provenance.
3. Support **retrieval mode** for ranked discovery and **structured question mode** for supported complete-within-scope graph answers.
4. Return resolved RDF IRIs, graph snapshot, query-plan summary, formal result status and inspectable supporting triples/constraint reports.
5. Run locally in a Rust process with Oxigraph and ONNX Runtime, plus a local quantized generative semantic parser backend; never require a hosted AI API.
6. Pin and validate model, tokenizer, grammar, IR schema, vocabulary, index, graph and SHACL-semantic versions.

### 2.2 MVP boundary

- One well-defined, **real and imperfect** RDF domain (preferably Norwegian public procurement/municipal suppliers/contracts where licensing and RDF availability permit), initially 10,000–100,000 indexed resources and a fixed target CPU. Synthetic data may supplement but must not replace the real holdout.
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

**Critical limitation:** grammar-constrained output guarantees at most structural JSON correctness; a well-formed plan can still express the wrong meaning. Measure **semantic IR accuracy** and **answer-set accuracy** independently. A verified execution means the **resolved query plan** ran against a specific graph; it does not prove the user's interpretation was captured correctly or establish real-world truth. Present the resolved relations, filters, scope and supporting triples to the user, and treat high-confidence wrong-plan answers as a primary failure mode.

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

**Run the first planner trial during Phase 0**, not after SHACL and full indexing work. Start with fixed, expert-supplied authorized ontology candidates so model semantic ability can be isolated from retrieval failures. Compare with deterministic templates and a modest grammar-constrained local model on the target CPU; confirm the exact llama.cpp version honors the selected JSON grammar, reject invalid outputs independently in Rust, and include adversarial RDF labels. Only then evaluate retrieval-grounded planning.

Compare generated IR with expert-authored reference IR/SPARQL over frozen snapshots. Hold out Norwegian paraphrases, reversed predicates, dates, “more than” vs “at least,” scoped negation, nested constraints and graph changes. Include ambiguity, missing evidence, unsupported logic and malicious prompt text inside RDF labels.

Measure: schema-valid vs actually correct IR, exact operator/predicate/direction/value/scope accuracy, execution success, gold answer precision/recall/F1, abstention quality, and full parser CPU p95/RAM. **Define numeric release thresholds in Phase 0** from the target dataset and device; do not infer them from general LLM benchmarks.

## 9. Optional MVP Enhancement: Local Cross-Encoder Reranking

The default MVP retriever is **B2 = BM25 + EmbeddingGemma 2 rank fusion**. After measuring it, evaluate **B3 = B2 + a local multilingual cross-encoder reranker**, which jointly reads the question and each candidate's concise direction-aware RDF description.

1. Review locally runnable multilingual rerankers, including BGE-family and smaller alternatives; compare license, CPU inference runtime, quantization and actual Norwegian-directional ranking performance.
2. Feed the top **10, 20 and 50** B2 candidates to the reranker; preserve predicate and edge direction in the text.
3. Track **initial Recall@50** and reranked Recall@10, MRR and nDCG@10 separately. A reranker **cannot** recover a correct object absent from the initial candidates.
4. Benchmark full p50/p95/p99 CPU latency, resident memory, batching, cold/warm startup and question/context lengths on the chosen hardware. The suggested 40–80 ms for 50 pairs is not established and is **not a performance promise**.
5. If first-stage Recall@50 is poor, improve vocabulary resolution, document verbalization, BM25/vector fusion and candidate selection *before* expecting reranking to help.
6. Promote the reranker only if measured quality gain justifies memory/latency cost for the MVP. Maintain a B2-only fallback.

**Gate:** Define a quality-and-p95 budget in Phase 0 and make the B2 vs B3 decision from held-out relational and cross-lingual questions; do not assume an 8–15 percentage-point improvement.

## 10. Rust Runtime and Interface Contracts

### 10.1 Two-crate workspace

Avoid eleven independent Rust crates for a new project with rapidly changing interfaces. Start with **two crates** (or even a single Cargo package containing lib and bin targets if simpler):

| Crate | Responsibility |
|---|---|
| `verity_core` | Engine library with normal internal modules for RDF, registry, embeddings, lexical and vector search, fusion/reranking, ontology resolver, parser adapter, IR, SPARQL compiler, SHACL integration, bundles and shared API types. |
| `verity_cli` | Thin binary for CLI commands and an optional HTTP server, delegating all domain behavior to the core. |

Use `pub(crate)`, private modules, traits and tests to express boundaries. Split a module into its own crate **only after** APIs stabilize and a real independent-reuse/build/dependency need appears.

### 10.2 Proposed API and execution contracts

- `POST /v1/search`: rank entities, classes, predicates and shapes with authorized named-graph/type filters; may request reranking and supported fact checks.
- `POST /v1/ask`: question → scoped ontology candidates → grammar-constrained JSON IR → deterministic type/authorization checks → compiled SPARQL → results/evidence.
- `POST /v1/validate`: check explicitly supported SHACL constraints on selected focus nodes, with a coverage report.
- `GET /v1/status`: active graph/shapes/model/vocabulary/IR schema/parser grammar versions, supported question families, freshness and health.
- CLI: `ingest`, `index-build`, `verify-bundle`, `activate-bundle`, `evaluate` and `benchmark`.

Illustrative response envelope (**not an implemented API**):

~~~json
{
  "status": "verified",
  "mode": "structured",
  "graph_snapshot_id": "example-graph-v1",
  "parser_grammar_id": "query-ir-v1",
  "ir_schema_version": 1,
  "results": [{"rdf_term": "https://example.org/company/123", "evidence": [{"source_graph": "https://example.org/source/registry", "statement": "illustrative checked RDF fact"}]}],
  "complete_within_scope": true,
  "scope": {"named_graphs": ["https://example.org/source/registry"]},
  "plan_id": "example-plan"
}
~~~

In production, `verified` and `complete_within_scope` can be asserted **only** if the answer's SPARQL plan ran successfully over the declared scope and its required evidence is available. Ranked top-*k* retrieval can never set `complete_within_scope` to true.

### 10.3 Index and query safety

- Verify file checksums, dimensions, row count, endian format, finiteness, row-to-ID registry hashes, normalization tolerance and model/prompt compatibility.
- Compare SIMD dot-product ranking with a scalar reference. Memory mapping is inexpensive but a cold mapping does not prefetch every page.
- Track per-stage and end-to-end p50/p95/p99 including embeddings, BM25/vector scan, reranking, ontology retrieval, local generation, plan validation, SPARQL and evidence.
- Compile a strict, read-only IR and reject unsupported complexity, scope and SPARQL operations before calling Oxigraph.

## 11. Updates, Versioning, and Refresh

The MVP does **not** need a graph-neural representation index. Use a two-tier **text index** lifecycle:

1. **Immutable base bundle:** RDF data snapshot, SHACL snapshot, ontology registry, text embedding matrix, lexical index, tokenizer, embedding-model identity and preprocessing.
2. **Delta index:** new/changed node **document embeddings** (same text prompt, truncation and normalization as the base), changed lexical documents and tombstones for deletions. Never directly compare embeddings produced by incompatible model/projection spaces.
3. **Serving view:** pin an Oxigraph read view to a specific graph snapshot; publish retrieval index watermarks/freshness. Revalidate resolved ontology IDs against the executing snapshot, especially after schema changes.
4. **Parser assets:** pin generative model+quantization digest, tokenizer/runtime, grammar/JSON Schema, **typed-IR schema version**, ontology-catalog hash, compiler revision and supported operations.
5. **SHACL assets:** pin the SHACL target semantics, validator/compiler version, shapes snapshot, graph-scope policy and cached shape templates where used.

Publish a candidate bundle, run canary answers and index/grammar/IR compatibility tests, and **atomically** switch the active release pointer with a rollback path.

Changes to RDF edges can make verbalized neighborhood descriptions stale; schedule the relevant document/delta rebuilds. Do not silently claim fresh retrieval on a stale index or exhaustive matches from an approximate index.

**CompGCN two-hop structural invalidation belongs to post-MVP R&D**, not Phase 6. If graph embeddings are introduced later, version and refresh them separately.

**Acceptance:** crash, partial-import, schema-upgrade and rollback tests demonstrate that no request silently mixes incompatible vocabulary, graph, parser, index or SHACL versions.

## 12. Testing and Evaluation

### 12.1 Frozen benchmark

Build **100–200 expert-reviewed Norwegian questions** over an actual, imperfect RDF dataset, with **all correct result bindings known where feasible**, expert-authored SPARQL, typed IR examples, ambiguity/unsupported labels and explicit selected RDF snapshots. Include at least one distinct-ontology or time-based holdout for transfer; keep a locked held-out set separate from tuning. Capture the source/quality limits of each graph. Keep held-out paraphrases and a domain/time/named-graph holdout where appropriate.

Test: entity/term lookup; inverse and similarly named relations; one/two hops; joins and conjunction; numeric/date filters; counting with `HAVING`; multilingual Norwegian→English; SHACL shape relevance and violations; subclasses, ill-typed literals, blank nodes and named-graph scope; missing/conflicting data; new/deleted nodes; ambiguous or unsupported questions; and prompt-injection text hidden in RDF labels.

### 12.2 Comparison matrix

| System | Retrieval stage | Structured question evaluation |
|---|---|---|
| B0: lexical | BM25 only | Fixed deterministic templates only. |
| B1: text vectors | EmbeddingGemma only | Fixed deterministic templates only. |
| **B2: MVP baseline** | BM25 + EmbeddingGemma hybrid | Parser uses B2 ontology candidates; same IR/compiler. |
| **B3: optional** | B2 + reranker | Same parser/IR/compiler, evaluate the effect of better ranking. |
| **Q0: compiler oracle** | Gold resolved ontology + expert IR | Measures compiler and executor independently of ML. |
| **Q1: end-to-end** | B2/B3 + local constrained parser | Measures natural language → IR → verified result set. |

CompGCN and R-GCN are **not MVP benchmarks**. After release, compare them against the **strongest approved production baseline**, including B3 if adopted.

### 12.3 Metrics and promotion gates

| Metric | Required interpretation |
|---|---|
| Initial Recall@10/20/**50**/100, MRR, nDCG@10 | Measure term/candidate coverage separately from reranker gain. |
| Reranked Recall@10, directional accuracy, p95/RAM | Promote B3 only with meaningful benefit and acceptable cost. |
| JSON Schema conformance | A syntactically invalid plan must never execute; this does **not** measure semantic correctness. |
| Typed IR correctness | Correct operators, direction, comparisons, entity/predicate IDs, variable binding, graph scope and aggregation. |
| Exact answer-set precision/recall/F1 | Compare to gold SPARQL; track query execution errors and unsupported questions. |
| Ambiguity/unsupported abstention | Test that uncertain interpretations stop rather than produce confident false answers. |
| SHACL differential parity | **100% on the pinned supported-fixture subset**, with documented exclusions. |
| Evidence coverage | Every claimed verified answer traces back to graph facts, constraints and snapshot. |
| Full CPU p50/p95/p99, resident RAM and cold/warm boot | Include local generation and reranking; no speculative 5–15 ms whole-pipeline target. |
| Freshness and rollback | Fixed canaries on every data/model/parser/grammar release. |

**Set numerical thresholds in Phase 0** using the actual graph, target CPU, question mix and domain tolerance for false positives. A grammar can achieve high JSON validity and still have poor execution accuracy; track both separately.

### 12.4 Isolation and security tests

- **IR compiler:** expert IR → expected SPARQL semantics → gold graph result sets, without a model.
- **Vocabulary resolver:** Norwegian phrases → correct class/property/entity IDs and direction.
- **Parser:** known catalog choices + paraphrases → valid and semantically correct IR, or safe abstention.
- **Complete engine:** natural question → retrieval → constrained parser → validated plan → SPARQL → evidence.
- **Operations:** corrupted bundles, inaccessible graphs, stale text documents, cancelled inference, timeouts and runtime fallback.

## 13. Security and Reliability

- **Graph text is untrusted input.** RDF labels/comments and linked document snippets may contain prompt-injection attempts; never elevate them from data into instructions for the generator.
- Grammar-constrained JSON is a serialization control, **not** a semantic or authorization boundary. Every output passes deterministic typed-IR checks and catalog/scope authorization.
- Keep allowed operators, predicate IDs, classes, graph scopes, datatype comparisons, path depths and aggregation types on a strict allowlist; the model cannot issue raw SPARQL or updates.
- Compile typed and validated RDF terms safely; avoid user-text interpolation and disable remote `SERVICE` and unbounded property-path operations by default.
- Restrict local generation tokens, candidate context size, graph-query time, path expansion, row count, output size and memory; allow cancellation and explicit failure statuses.
- Enforce named-graph access **before** retrieval, ontology-context generation, execution and evidence rendering—not merely at the output layer.
- Do not retain sensitive raw user questions by default; use opt-in diagnostic traces with appropriate access and retention policy.
- Validate model weights, local native inference dependencies, quantization, tokenizer/grammar, bundled data and third-party licenses during release.
- Include regressions for wrong-direction relations, illicit scopes, malformed IR, injection attempts and incomplete data.

## 14. Active implementation sequence and schedule

The [Phase 0 decision](phase-0-decision.md#selected-next-scope-a-find-first-mvp) replaces the former optimistic full-stack schedule. Phase 0 completed engineering experiments with a negative result for the tested unattended Ask configurations; it did not pass formal feasibility gates.

1. [#36](https://github.com/grove/graph-verity/issues/36): authorized Norwegian/English vocabulary/entity catalog (3–5 days).
2. [#37](https://github.com/grove/graph-verity/issues/37): measured BM25 lexical baseline (4–6 days), after catalog.
3. [#38](https://github.com/grove/graph-verity/issues/38): pin and compare EmbeddingGemma to BM25 (4–7 days), after baseline. No assumed embedding advantage or runtime compatibility.
4. [#39](https://github.com/grove/graph-verity/issues/39): scoped Find, graph navigation, supporting triples and source/snapshot provenance (5–8 days), after the embedding adopt/reject decision.
5. [#40](https://github.com/grove/graph-verity/issues/40): optional explicit intent selection/plan confirmation (3–5 days), only after Find and a separate product decision.

One maintainer: 16–26 engineering days, approximately 4–6 working weeks for Find, excluding review/license/runtime delays. Production ingestion, HTTP hardening, SHACL runtime, reranking and GNNs are not on this MVP critical path. The final decision defines proposed retrieval quality/performance targets; old Ask gates are not reused as retrieval approval.

## 15. Repository and Artifacts

**Original broader layout proposal:** the two-crate workspace now exists; many internal modules and artifact directories below remain design alternatives. See README for the runnable structure.

~~~text
graph-verity/
  README.md
  LICENSE
  Cargo.toml                        # Rust workspace (implemented)
  crates/
    verity_core/
      src/
        lib.rs
        rdf/
        registry/
        embeddings/
        lexical/
        retrieval/
        reranking/
        planner/                   # ontology context, constrained parser, IR
        sparql/                    # safe compiler and executor
        shacl/
        bundles/
        api_types/
    verity_cli/
      src/main.rs                  # CLI and optional HTTP server
  ml/
    evaluation/
    export/
    post_mvp_gnn_research/
  tests/
    fixtures/rdf/
    fixtures/shacl/
    golden_sparql/
    golden_ir/
    norwegian_paraphrases/
    parser/
    compiler/
    regression/
    authorization/
    rust_python_parity/
  configs/
    dataset.yaml
    inference.yaml
    evaluation.yaml
  artifacts/                      # generated, typically not committed
    releases/<release_id>/
      graph_snapshot/
      registry.parquet
      ontology_catalog.json
      shapes_ast.json
      cached_shape_queries/
      vectors.bin
      nodes.index
      bm25_index/
      embedding_model.onnx
      embedding_tokenizer.json
      parser_model/
      parser_grammar.json
      ir_schema.json
      index_manifest.json
      bundle_manifest.json
      checksums.sha256
  docs/
    implementation-plan.md
~~~

**Keep in Git:** schemas, code, test fixtures, configurations, reproducible preprocessing rules, reference queries and evaluation methods. **Keep as versioned release artifacts:** large model weights, indexes, full graph snapshots, benchmark outputs and derived bundles.

When a module needs a stronger boundary, use ordinary Rust visibility/traits first; split into a new crate only if build/reuse/dependency constraints justify it.

## 16. Primary Risks and Mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Generative parser emits valid JSON but wrong relation, operator, direction or number | False structured answers despite constrained grammar | Ontology-scoped candidates, deterministic typed checks, gold Norwegian paraphrases, IR scoring and safe abstention. |
| Relevant ontology predicate absent from retrieved context | Parser cannot form a correct plan | Measure predicate/entity candidate recall; improve lexical+vector retrieval and controlled candidate expansion before adding parser complexity. |
| Missing triples are interpreted as negatives | Incorrect compliance and data-quality claims | Explicit graph completeness/entailment contract and abstention for unsupported negation. |
| Tiny parser model lacks Norwegian competence | Incorrect IR, poor acceptance rate or high latency | Benchmark multiple local model sizes and phrasing families on target hardware before selecting one. |
| Reranker fails to improve Recall@10 or exceeds CPU budget | Added latency and RAM without value | Compare B2/B3 at top 10/20/50, track Recall@50 and retain B2 fallback. |
| Existing SHACL library integration is incomplete | Divergent reports or delayed Phase 3 | Test Rudof/`shacl` early; use a bounded, cached SPARQL subset if needed, with pinned differential tests. |
| Subclass/datatype/named-graph semantics diverge | False SHACL conformance claims | Test `rdf:type/rdfs:subClassOf*` where relevant, ill-typed literals and graph scope against reference fixtures. |
| Prompt injection in RDF labels or source documents | Model-induced unauthorized or misleading plans | Treat retrieved text as data; grammar, IR allowlist, ontology/permission validation and read-only compiler are mandatory. |
| Model, IR schema, vocabulary or graph version drift | Incompatible embeddings and unsafe plans | Hashed manifests, atomic bundle swaps, canary tests and rollback. |
| Incorrect top-*k* completeness claims | Partial result sets presented as exhaustive | Retrieval is candidate discovery; only exhaustive formal queries may claim complete-within-scope answers. |
| Eleven premature crates slow changes | Extra dependency/struct/error-conversion overhead | Two-crate workspace, internal modules, split only once interfaces stabilize. |
| CPU timing guesses treated as guarantees | Missed operational targets | Benchmark complete pipeline p50/p95/p99 and peak RAM; define budgets from actual device. |
| CompGCN brings marginal benefit and stale structural embeddings | Unnecessary training and refresh complexity | Move GNN to post-MVP research and require gain over strongest production retrieval. |

## 17. Historical broader Ask pilot definition

These original broader requirements are retained for context; they do not define the selected Find-first release. Use the [decision milestones and success criteria](phase-0-decision.md#selected-next-scope-a-find-first-mvp). The original Ask pilot would require:

- [ ] Phase 0 feasibility findings, grammar-behavior tests and an explicit documented go/revise/stop decision are recorded; no implementation claims rest solely on schema-valid JSON.
- [ ] A local/offline Rust process runs with Oxigraph, an embedding model, compatible indexes and a pinned local semantic-parser runtime.
- [ ] Norwegian↔English RDF retrieval and **pre-rerank Recall@50** are measured on the frozen benchmark; B2 works without GNNs or reranking.
- [ ] An ontology-scoped small local generator produces *candidate* typed IR; **no** invalid, unauthorized or unsupported IR can reach SPARQL execution.
- [ ] Supported Norwegian compositional questions achieve the pre-agreed **gold answer-set F1 / accuracy** and safe-abstention criteria, not merely valid JSON.
- [ ] Typed IR compilation uses resolved RDF terms, correct relation direction, typed filters, bounded aggregation, graph scopes and read-only operations.
- [ ] The documented supported SHACL subset passes its pinned differential reference suite; unsupported constraints are explicitly reported.
- [ ] Verified results have reproducible evidence; exhaustive-within-scope is asserted only after exhaustive graph execution over declared data/semantics.
- [ ] Wrong-direction, dates, amounts, more-than/at-least, blank-node, subtype, graph-scope, missing-data and prompt-injection tests pass.
- [ ] Python/ONNX/Rust embedding parity, model/grammar/IR/ontology/index compatibility, changed-node deltas and rollback tests pass.
- [ ] Target-device end-to-end p95 latency and resident-memory budgets (including parser and enabled reranker) meet **Phase 0** thresholds.
- [ ] B3 is deployed only if its measured value justifies CPU/RAM cost; otherwise B2 remains the retrieval path.
- [ ] No CompGCN/R-GCN implementation, special structural-index freshness service or related promotion gate is required to finish MVP.

## 18. Current recommendation

Ship a narrow Find-first pilot: deterministic scoped catalog, a measured lexical baseline, an adopt/reject EmbeddingGemma experiment, and graph navigation with provenance. Reuse the typed compiler and evidence foundation. The [final Phase 0 decision](phase-0-decision.md) records why unattended free-form Ask with the tested Qwen configurations stops here. Any later Ask flow requires explicit intent selection or plan confirmation and separate evaluation; no semantic-feasibility GO is claimed.

## 19. Reference Documentation

The architecture extends the original graph/text alignment proposal while reprioritizing the implementation:

- [EmbeddingGemma 2 model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2) — tokenizer, numerical format, multilingual embeddings and Matryoshka truncation.
- [EmbeddingGemma with Sentence Transformers](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers) — query/document encoding conventions.
- [Oxigraph Rust Store](https://docs.rs/oxigraph/latest/oxigraph/store/struct.Store.html) — embedded RDF quad store and SPARQL.
- [ONNX Runtime, Rust `ort`](https://docs.rs/ort/latest/ort/) — text encoder inference.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) — evaluate local small-model inference with grammar/schema-constrained decoding.
- [Rudof](https://github.com/rudof-project/rudof) and [Rust `shacl` crate](https://crates.io/crates/shacl) — evaluate existing parsing/validation before custom implementation.
- [W3C SHACL Recommendation (2017)](https://www.w3.org/TR/shacl/) — initial validation semantics contract.
- [W3C SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/) — separate future/versioned semantics target.
- [pySHACL](https://github.com/RDFLib/pySHACL) — pinned differential/reference testing.
- [PyTorch Geometric R-GCN](https://pytorch-geometric.readthedocs.io/en/latest/_modules/torch_geometric/nn/conv/rgcn_conv.html) — post-MVP GNN comparator.

**Standards policy:** pin the **2017 SHACL Recommendation** and a documented entailment/graph scope for MVP validation. Do not treat SHACL 1.2 features as automatically supported.

**Model policy:** model choices and suggested size ranges are starting hypotheses. Confirm license, Norwegian semantic-parsing accuracy, ONNX/native runtime availability, RAM and full CPU latency in Phase 0 before locking them in.

## Appendix A. Post-MVP Graph Encoder Research

**Not scheduled for the MVP.** The following is preserved as a future experiment specification. Its promotion test uses the strongest deployed B2/B3 baseline, not a weaker text-only baseline.

### A.1 Default alignment strategy

**Start with a frozen EmbeddingGemma 2 encoder and its native 256-dimensional truncated search space.** Train the graph encoder plus a graph projection head to map node/shape representations into that space. This minimizes runtime changes and keeps temporary text embeddings for new nodes meaningfully comparable, subject to calibration tests.

Do not independently compare two 256-dimensional vector spaces without alignment. If later training introduces a learned text projection, export **the exact same projection** for online Rust inference; the default document-text fallback must pass through the matching representation path.

### A.2 CompGCN implementation

1. Construct directed typed edges from resource-to-resource RDF triples, adding inverse relation IDs and self-loops.
2. Initialize node features from frozen embeddings of node identity/description views, augmented with carefully encoded categorical attributes; avoid solely learned ID vectors.
3. Initialize relation features from labels/descriptions or trainable embeddings; maintain stable predicate IDs.
4. Use two CompGCN message-passing layers with a tunable composition function (multiplication/subtraction/correlation) and normalization.
5. Use relation-stratified neighbor sampling (initial experiment: up to 15 edges per relation and direction per layer), with safeguards for rare or required edges.
6. Apply a 256-dimensional output projection and L2-normalize.
7. Compare with an R-GCN baseline under identical train/validation/test splits and compute budgets.
8. Cache graph embeddings offline; **no GNN execution on the online query path**.

### A.3 Training data

Store one row per natural-language-to-target link, with at least:

`text`, `target_id`, `target_type`, `language`, `source`, `source_uri`, `named_graph`, `graph_snapshot_id`, `shape_snapshot_id`, `split`, `positive_group_id`, and `generation_template_version`.

Sources: labels/definitions, directed triple verbalizations, natural question templates, reviewed user questions, SHACL explanations, and sourced document passages. Include meaningful Norwegian/English pairs. Tag the target role explicitly for a path description: start node, end node, predicate, shape, or another declared type.

Build **multi-positive** text↔graph contrastive training masks to avoid treating several correct resources for one question as negatives. In-batch negatives must exclude known positives and ambiguous cases. Add hard negatives from verified structural distinctions (including same-class, different-predicate cases), but never assume an absent triple proves falsity under the open-world assumption.

Suggested objective: multi-positive contrastive retrieval loss, with modest optional auxiliary losses for relation/type or link prediction. Tune temperature on validation data; retain training-time temperature and calibration settings in the model manifest.

### A.4 Training and evaluation protocol

- Keep separate held-out query formulations for ordinary retrieval quality.
- Add named-graph, domain, time-based, and new-node holdouts for transfer and graph-drift evaluation.
- Prevent leaked future edges or unseen test nodes from entering graph message passing in an inductive test.
- Use early stopping on retrieval metrics rather than training loss.
- Run ablations: remove relation types, reverse edge directions, remove hard negatives, remove SHACL-generated data, and remove node initial text features.
- Monitor modal collapse, oversmoothing, per-dimension variance, high-degree-node errors, and performance on unseen entities.

### A.5 Graph encoder promotion gate

Consider a *separate post-MVP promotion* only if, on a locked independent relational-question test set:

- Recall@10 improves by **at least 10 absolute percentage points** over the **strongest approved production retrieval baseline** (including a reranker if enabled).
- MRR/nDCG and cross-lingual performance do not show unacceptable regressions.
- Improvements persist across three random seeds and at least one held-out domain/time/new-node evaluation.
- The expanded build, refresh, and operational cost is justified by the gain.

If the gate fails, keep the MVP text/lexical/reranking + SPARQL architecture rather than introducing graph-vector lifecycle costs.
