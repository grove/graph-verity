# Query contract v1 — deterministic pre-LLM core

The runtime loads an immutable byte-identified snapshot. Operators supply a policy independently
of the query plan. The validator constructs vocabulary from only the requested authorized named
graphs. Labels are data, not executable instructions. Exact-label resolution reports ambiguity.

`verity schema` emits JSON Schema derived from the same Rust types used for strict decoding.
Structural schema validity is necessary, not sufficient: Rust additionally checks version, snapshot,
authorization, graph-local entity roles, predicate-range compatibility, variable binding, inferred
datatype compatibility, and complexity.

A plan contains `version`, `snapshot_id`, `scope`, `patterns`, `filters`, `projection`, `group_by`,
`having`, and `limit`. Every collection must be supplied, including empty collections. Unknown
fields and unsupported enum values are rejected. A pattern contains `graph`, `from`, `predicate`,
`direction` (`forward` or `reverse`), and `to`. Reversing direction swaps subject and object; it
does not infer an inverse ontology property. Nodes are tagged `variable`, `iri`, or `literal`.

Limits: 8 graph patterns, 8 graphs, 12 variables, 8 filters/projections, 4 distinct-count outputs,
1000 rows maximum (the operator may impose less). Patterns must form a connected variable join.
One- and two-hop joins are supported; longer joins remain bounded by the pattern limit. No property
paths, recursion, updates, SERVICE, OPTIONAL, general disjunction, negation, or SHACL are exposed.
Default-graph input can be inspected, but Ask requires explicit IRI-named graphs. Blank-node graph
names and blank-node constants are unsupported; blank-node bindings can participate in joins.

Filters use `eq`, `ne`, `lt`, `le`, `gt`, `ge`, with numeric or temporal ordering only. Supported
literal types are string, language-tagged string, boolean, integer (i64), bounded decimal,
finite double, YYYY-MM-DD date, and RFC3339 dateTime. Other lexical forms, timezones on xsd:date,
and datatype-derived aliases are not silently coerced. Mixed or ill-typed predicate ranges are
conservatively rejected when used in comparisons. Profile inference is scoped and observational,
not a replacement for full ontology/SHACL reasoning.

Projection is `variable` or `count_distinct`. Nonaggregated projected variables must exactly match
`group_by` when aggregates are present. HAVING refers to a projected count alias. Counts operate on
all matching graph bindings, not a retrieved top-k candidate list.

The compiler uses RDF library serialization for IRIs/literals and a strict variable grammar. Query
text cannot be supplied by a model. Compilation returns an opaque value, and execution revalidates
against the live immutable snapshot and operator policy. An extra row detects truncation; a LIMIT
alone never implies completeness. Evidence is the union of contributing BGP statements for returned
rows/groups and has an independent cap. Execution labels its query evidence `verified_against_snapshot`: this means that the scoped
query was executed against the pinned RDF snapshot, **not** that an intended interpretation
or a fact about the real world was verified. Entity/class constants must actually occur as
resource terms in the pattern's own named graph; an IRI known only as a predicate, or
only from another graph, is insufficient. IRI object constants are rejected for
literal-only predicates. Graph-specific checks retain shared entities explicitly
observed in each graph. All such invalid constants are rejected during compilation, before
any SPARQL query is executed.

Positive statements alone do not prove an exact count;
the full scoped query and snapshot are part of aggregate evidence.

A valid but reversed relationship or wrong numeric operator can still execute. The validator cannot
prove linguistic intent. Results therefore say `executed`/`truncated`, `interpretation_correctness:
not_assessed`, and `real_world_truth: not_established`, never generic 'verified truth'. Empty results
are not evidence of real-world falsity. Literal metadata and source graph accompany evidence.

Execution has a cooperative cancellation deadline, output byte cap, and joined watchdog. These are
not a hard OS memory sandbox: adversarial joins can allocate intermediate memory. Run under an OS
memory limit for untrusted workloads; production isolation and authorization services are out of
scope. Snapshot loading is limited to 16 MiB input and 100,000 stored quads; the latter is checked
after parsing. Blank-node identifiers are local to a loaded snapshot, not stable cross-import IDs.

## Parser integration boundary

`SemanticParser::propose` accepts an authorized `ParserRequest` and returns raw JSON bytes. The
boundary independently decodes and validates `ParserResponse` v1 and refuses any scope change.
The exact-request fixture adapter cannot interpret new questions. The opt-in
[local parser experiment](local-parser-experiment.md) now implements pinned CPU llama.cpp
generation through an owned stdio bridge, with grammar probes and independent Rust validation.
`SemanticParser::origin` is explicit: fixture replay stays `fixture`, actual local generation
uses `local_model`. The runner supplies the model identity independently of model-authored JSON.
The legacy schema's `FutureLocalConfig` remains a placeholder, not the runner's configuration;
the actual experiment configuration is `configs/local-parser.json`.

The evaluator accepts the same proposal trait and uses the same result scoring. Structural IR exact
match is deliberately conservative (including array order and variable names), not a proof of arbitrary
SPARQL semantic equivalence. It flags wrong plans even when they execute successfully. Reference queries
run only in a physically isolated copy of authorized graphs, with no HTTP-enabled evaluator. They are
trusted benchmark assets, not a public raw-query API. Gold bindings are never updated by evaluation.

Oracle reports include code, schema, dependency and data hashes. Fixture abstention entries are clearly
marked bookkeeping, not evidence of ambiguity detection. Legacy `pipeline_ms` timing excludes
ingestion and generation; `generation_ms` and `end_to_end_ms` record the actual parser path.
The local runner separately records process-cold startup, warm percentiles and aggregate RSS.
Process VmHWM remains lifetime peak, not per-query or incremental model memory.
Independent expert gold and a preregistered holdout remain unmet feasibility gates;
the owner's AI-reference waiver permits development measurements only.
