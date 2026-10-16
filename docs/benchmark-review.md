# Benchmark coverage and independent review

## Retained development material

`benchmarks/wikidata.json` has 130 candidate questions: 46 `dev`, 76 `review_candidate`, and 8 `transfer_candidate`. The development split has 38 executable queries and eight expected clarification/unsupported entries. Its query families include label/entity lookups, direct/inverse relations, two hops, numeric/date comparisons, conjunction, distinct counting, grouping/HAVING and named-graph scoping.

Questions, interpretations and reference SPARQL were machine-authored. RDFLib computed the frozen reference bindings; the Rust oracle independently compiles IR and compares both reference-SPARQL execution and expected bindings. Mechanical agreement can detect compiler defects but cannot prove that the Norwegian question and gold describe the same intended meaning. **All gold needs independent human review.**

The 76 review candidates reuse development templates. They must not be promoted to an independent locked holdout by changing a split label. The eight transfer candidates use the same Wikidata ontology in another country; they are not cross-ontology evidence. The retained earlier Oslo source is a regression asset, not a coherent historical snapshot of all entities. No holdout performance is claimed.

## Reproduce without changing gold

```sh
.venv/bin/python tools/dataset.py verify
.venv/bin/python tools/benchmark.py verify
cargo run --locked -p verity_cli -- evaluate data/wikidata/snapshot.nq nquads data/wikidata/policy.json benchmarks/wikidata.json dev artifacts/oracle
```

The full check is `.venv/bin/python tools/verify_pre_llm.py`. Ordinary CI uses only `dev`. `tools/benchmark.py create` is an explicit authoring operation, not a verification or fix command. Never regenerate expected results to make a failing compiler test pass.

Each case preserves its ID, Norwegian question, intended interpretation, family, split, review status, provenance, named scope, expected status, gold IR, reference SPARQL and bindings. The benchmark pins the graph snapshot; every gold plan pins that same release. Reference queries are trusted assets executed on an isolated authorized graph copy, not an untrusted query API.

## Review procedure before a decision-quality model test

A human reviewer checks the question against the actual raw source, directed predicates, typed comparisons, interpretation, scope, reference query and complete expected bindings. Record reviewer identity, date and correction history; do not overwrite machine-authored provenance. Review missing-data and ambiguity cases as carefully as positive cases. City and municipality identifiers, source-specific population values and incomplete qualifiers need particular care.

Independently author new test questions with held-out interpretations/combinations and graph facts; group template siblings and paraphrases so they cannot straddle tuning and holdout. Do not disclose locked answers to the agent tuning prompts. Freeze split IDs, question/graph hashes, source license, target CPU/thread/RAM configuration, model/runtime/tokenizer/grammar/prompt hashes and the approved numerical gates in a reviewed commit before evaluating the holdout. Any changes after inspection require versioned disclosure and a fresh independent test set.

## Reporting semantics

`oracle/report.json` retains case-level stage failures, exact result sets, precision/recall/F1, conservative structural IR equality, timings and source/dependency hashes. Its overall `passed` count includes `fixture_status_only` bookkeeping. The full verification summary explicitly separates 38 executable checks from eight recorded statuses, leaving model accuracy and model abstention accuracy null.

A wrong but executable plan is detected by structural disagreement even if it accidentally returns the same rows. Structural equality is conservative, including variable names and array ordering; add a reviewed normalization/equivalence policy before interpreting it as a model's definitive semantic accuracy. Report parser JSON syntax separately from schema validity, predicate/entity/direction/filter/aggregation/scope correctness and answer sets. Include timeout, validation and reference failures, false abstention and wrong-plan-successful-execution counts with explicit denominators.

Oracle latency currently covers warm validation/query/evidence, not ingestion, retrieval, model generation or a cold model startup. Process peak RSS is lifetime VmHWM on Linux, not model-only allocation. Confidence intervals over related templates are descriptive arithmetic, not independent statistical assurance. Per-family small samples and correlated templates must be disclosed.
