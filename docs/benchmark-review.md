# Benchmark coverage and independent review

## Retained development material

`benchmarks/wikidata.json` has 130 candidate questions: 46 `dev`, 76 `review_candidate`, and 8 `transfer_candidate`. The development split has 38 executable queries and eight expected clarification/unsupported entries. Its query families include label/entity lookups, direct/inverse relations, two hops, numeric/date comparisons, conjunction, distinct counting, grouping/HAVING and named-graph scoping.

Questions, interpretations and reference SPARQL were machine-authored. RDFLib computed the frozen reference bindings; the Rust oracle independently compiles IR and compares both reference-SPARQL execution and expected bindings. Mechanical agreement can detect compiler defects but cannot prove that the Norwegian question and gold describe the same intended meaning. **Independent human review is required for an expert-validated gold claim.** The project owner has explicitly waived a paid independent reviewer for the *exploratory development spike* only; see [the owner-accepted AI-gold risk exception](phase-0-ai-gold-risk-acceptance.md). The source review status remains AI-only, not human approved.

The 76 review candidates reuse development templates. They must not be promoted to an independent locked holdout by changing a split label. The eight transfer candidates use the same Wikidata ontology in another country; they are not cross-ontology evidence. The retained earlier Oslo source is a regression asset, not a coherent historical snapshot of all entities. No holdout performance is claimed.

## Reproduce without changing gold

```sh
.venv/bin/python tools/dataset.py verify
.venv/bin/python tools/benchmark.py verify
cargo run --locked -p verity_cli -- evaluate data/wikidata/snapshot.nq nquads data/wikidata/policy.json benchmarks/wikidata.json dev artifacts/oracle
```

The full check is `.venv/bin/python tools/verify_pre_llm.py`. Ordinary CI uses only `dev`. `tools/benchmark.py create` is an explicit authoring operation, not a verification or fix command. Never regenerate expected results to make a failing compiler test pass.

Each case preserves its ID, Norwegian question, intended interpretation, family, split, review status, provenance, named scope, expected status, gold IR, reference SPARQL and bindings. The benchmark pins the graph snapshot; every gold plan pins that same release. Reference queries are trusted assets executed on an isolated authorized graph copy, not an untrusted query API.

## Owner approval, distinct-ontology development, and external sealed candidate

On 16 October 2026 the project owner explicitly approved the preceding ChatGPT AI semantic audit and authorized remaining engineering work; see [the owner sign-off record](issue-5-owner-approval.md). This is a legitimate project-level approval of that work, **not** proof that a separate specialist has reviewed all 130 gold cases independently. The per-case human `reviews.json` ledger must not be silently filled with invented human decisions.

The separate [GeoNames-derived Schema.org dataset](../data/worldcities-transfer/README.md) captures 328 city records, 62 subcountry names and 1,508 quads from CC BY 4.0 data with a pinned public source commit and integrity hashes. It is a **different actual source and ontology** than the Wikidata pilot; its five named graphs and read-only rebuild are tested in normal CI. Public [transfer development probes](../benchmarks/worldcities-transfer.json) provide 35 executable no-model oracle checks plus 5 expected non-model-tested abstentions. They have **never been evaluated by a graph-querying LLM**, but they are public and thus cannot qualify as confidential locked-transfer answers.

An additional **60-case Norwegian holdout candidate** (50 executable and 10 expected abstentions) has been created independently of the 38 original Wikidata development plans and the 35 transfer development probes, using new question wording and different city IDs. The public source tree contains [only the frozen integrity commitment](../configs/locked-holdout-commitment.json) and [an opt-in local checksum/review verifier](../tools/verify_sealed_holdout.py). Questions, SPARQL/IR and bindings were delivered to the project owner as an external ZIP artifact; **they are deliberately absent from GitHub and CI**. The bundle is AI-authored and human-review pending; its creation does not establish gold accuracy or a statistically independent holdout.

The owner/reviewer must securely store the external archive, independently adjudicate each gold case and record human approvals in a **separate external** append-only ledger, resolve exclusions without reusing test data in tuning, then freeze model/runtime/grammar and numerical acceptance thresholds before the **first** hidden-set inference. If the private case set becomes exposed to a coding agent or used in prompt tuning, treat it as compromised and commission a new holdout. Schema.org is also represented in the public transfer-development set, so the archive is separated at the *case* level and is **not** an unseen-ontology holdout.

No model-dependent Phase 0 accuracy, abstention, injection-resilience or transfer gate can be marked passed from these no-model oracle results. **Owner-approved scope update (16 October 2026):** issue #5 may be closed as *AI-audited engineering preparation with a documented review waiver*; that closure is **not** independent expert validation. Preserve existing human-review gates. See [the explicit risk acceptance](phase-0-ai-gold-risk-acceptance.md).


## Two review standards, not interchangeable

1. **Exploratory engineering baseline (owner accepted):** machine-authored and AI-audited questions, pinned reference SPARQL, case hashes, an exposed development split and a sequestered AI-authored candidate holdout are sufficient to *start* local-model development. Use only the public development data for tuning. Model agreement with AI gold is a **proxy** for semantic correctness, not independently adjudicated correctness.
2. **Independent gold / generalization claims (not available):** true case-by-case specialist review, independently verified answers, guaranteed lineage separation and a protected final holdout have not been completed. The `--require-reviewed initial|final` commands must remain false. Nothing in a GitHub issue closure, project-owner waiver or Rust CI can turn proxy accuracy into validated ground truth.

The phase-0 feasibility gates still require measured local-model results, scoped safety checks, real CPU measurements and a candid go/revise/stop decision. Review waivers and their potential effects on conclusions must be disclosed in that decision.

## Review records and gates

`schemas/contracts-v1.json` includes the version-1 `benchmark` JSON Schema, generated from the Rust evaluator's actual `Benchmark`/`Case` types with `verity schema`. Runtime validation additionally checks expected-status/gold consistency and plan semantics. `benchmarks/split-manifest.json` version 1 pins the benchmark bytes, partitions every case ID exactly once, and assigns every case to one lineage group. Related templates, paraphrases and geographic variants belong to the same group. `exposed_groups` records material already visible during development; all current groups are exposed. Lineage groups cannot straddle `locked_holdout` or `transfer_test` boundaries, and exposed groups cannot enter either test split. Do not remove exposure history or rename a group to evade this check.

`benchmarks/reviews.json` version 1 is an append-only ledger. It intentionally starts with no records. The existing `review_status` and `provenance` fields describe machine authorship; retain them when recording human review. Generate a read-only report with the current per-case hashes:

```sh
mkdir -p artifacts
.venv/bin/python tools/benchmark.py review > artifacts/benchmark-review.json
.venv/bin/python tools/benchmark.py review --require-reviewed initial
.venv/bin/python tools/benchmark.py review --require-reviewed final
```

The last two commands currently fail, as expected. `initial_ready` requires at least 30 approved development cases (start with 30–50). `final_ready` requires 100–200 cases across `dev`, `locked_holdout` and `transfer_test`, all approved, with nonempty independent holdout and transfer splits. Candidate pools never contribute to the final total. These are review-completeness checks, not a Phase 0 go decision or verification of reviewer expertise/independence. The raw Rust `evaluate` command does not enforce these gates; the evaluation operator must run the applicable gate before an authorized model test. Ordinary CI verifies metadata and development queries without requiring human approval or executing test/candidate queries.

After checking a case, append a record in this exact format, replacing the illustrative values with the actual identity, review date, current hash and decision:

```json
{
  "case_id": "wd-dev-001",
  "case_sha256": "COPY_CURRENT_HASH_FROM_REVIEW_REPORT",
  "reviewer": "Reviewer identity",
  "reviewed_at": "2026-10-16",
  "decision": "approved",
  "rationale": "Explain the source evidence and any adjudication or corrections."
}
```

Valid decisions are `approved`, `excluded` and `disputed`. Every record requires all six fields, a nonfuture ISO date and a nonempty rationale. The hash is SHA-256 of UTF-8 JSON encoding `{"case": CASE, "snapshot_id": BENCHMARK_SNAPSHOT_ID}` with sorted keys, unescaped Unicode and separators `,` and `:`. It covers the complete case, including its split, and the snapshot even for abstentions. Changing any of these invalidates the latest decision as `stale`. Records must be chronological per case; append order resolves same-day decisions. Keep old hashes and decisions as history, and preserve actual question/gold corrections in Git.

Use `disputed` while intended meaning or source support is unresolved. Use `excluded` with a reason for uncertain/unanswerable gold that cannot be adjudicated; it contributes no approved case. A clear unsupported/ambiguous question can instead be `approved` with its expected abstention/clarification status and null gold/query/bindings. A designated human adjudicator resolves disagreements in a new record tied to the corrected case hash. Never infer approval from query agreement. Excluded or disputed cases must stay out of decision-quality evaluation; any such case in an active final split makes the final gate fail. Development oracle runs may still mechanically check these fixtures and must not be reported as expert-reviewed model results.

Corrections and new independent material require explicit authoring: update the benchmark, its checksum, split IDs and lineage metadata together in a reviewed commit, then obtain fresh decisions for changed cases. `verify` and `review` never update gold, hashes or approvals. Review records are assertions checked for consistency, not signed attestations; repository review must establish reviewer identity, expertise and independence. No reviewed cases, locked holdout, or qualifying ontology/time-snapshot transfer set are supplied by this change.

## Review procedure before a decision-quality model test

A human reviewer checks the question against the actual raw source, directed predicates, typed comparisons, interpretation, scope, reference query and complete expected bindings. Record reviewer identity, date and correction history; do not overwrite machine-authored provenance. Review missing-data and ambiguity cases as carefully as positive cases. City and municipality identifiers, source-specific population values and incomplete qualifiers need particular care.

The reviewer should cover every query family, Norwegian wording against both Norwegian and English labels, realistic aliases, forward versus inverse direction, strict versus inclusive numeric/date boundaries, `COUNT(DISTINCT)`, `HAVING`, named-graph scope and negation with missing data. An executable empty result is different from an unsupported question. Record absent coverage rather than inventing expert approval or treating prefixed templates as new independent cases.

Independently author new test questions with held-out interpretations/combinations and graph facts; group template siblings and paraphrases so they cannot straddle tuning and holdout. Do not disclose locked answers to the agent tuning prompts. Freeze split IDs, question/graph hashes, source license, target CPU/thread/RAM configuration, model/runtime/tokenizer/grammar/prompt hashes and the approved numerical gates in a reviewed commit before evaluating the holdout. Any changes after inspection require versioned disclosure and a fresh independent test set.

## Reporting semantics

`oracle/report.json` retains case-level stage failures, exact result sets, precision/recall/F1, conservative structural IR equality, timings and source/dependency hashes. Its overall `passed` count includes `fixture_status_only` bookkeeping. The full verification summary explicitly separates 38 executable checks from eight recorded statuses, leaving model accuracy and model abstention accuracy null.

A wrong but executable plan is detected by structural disagreement even if it accidentally returns the same rows. Structural equality is conservative, including variable names and array ordering; add a reviewed normalization/equivalence policy before interpreting it as a model's definitive semantic accuracy. Report parser JSON syntax separately from schema validity, predicate/entity/direction/filter/aggregation/scope correctness and answer sets. Include timeout, validation and reference failures, false abstention and wrong-plan-successful-execution counts with explicit denominators.

Oracle latency currently covers warm validation/query/evidence, not ingestion, retrieval, model generation or a cold model startup. Process peak RSS is lifetime VmHWM on Linux, not model-only allocation. Confidence intervals over related templates are descriptive arithmetic, not independent statistical assurance. Per-family small samples and correlated templates must be disclosed.
