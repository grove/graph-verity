# Phase 0 — Semantic Parser Feasibility Protocol

**Status (17 October 2026): Phase 0 engineering decision published as [STOP tested unattended Ask / REVISE Find-first](phase-0-decision.md).** This document preserves the feasibility protocol, not a claim that its GO requirements passed. Numerical/protocol budgets and the M1 Pro target were owner-approved in the separate [pending approval record](../configs/phase-0-approval.json); formal freeze/external split integrity, expert gold and sealed evaluation remain incomplete. Public development and compact-v2 results are negative. The new decision supersedes the original build sequence and schedule.

## Goal and decision

Determine, before building the full serving stack, whether a small **local CPU-run** grammar-constrained model can map realistic Norwegian natural-language questions into a correct restricted RDF query plan, and whether users can distinguish execution evidence from the parser's interpretation. The outcome is **go**, **revise** (narrow scope, larger model, deterministic templates, or human confirmation), or **stop** for free-form Ask. Find can proceed independently.

## Inputs and benchmark

- Select a legally usable, real RDF dataset with imperfect Norwegian/English labels, source graphs and provenance; municipal ownership, procurement and suppliers are a useful candidate **only if usable RDF and rights are confirmed**. Document missing facts and ontology limitations. Do not replace evaluation data with only idealized synthetic triples.
- Create **100–200 expert-reviewed Norwegian questions** with source, complexity class, actual graph snapshot, exact intended meaning, gold typed IR, independently reviewed SPARQL, and expected result bindings where determinable. Mark unsupported, unclear or unanswerable cases with expected abstention. A plausible initial balance is 50 direct lookups/traversals, 50 compositional/numeric/date/count questions, 25 inverse-edge/scope/negation traps and 25 ambiguous/unsupported cases (adapt within 100–200 to available domain).
- Keep a locked test partition distinct from development examples; hold out paraphrases **and** at least one other ontology or different-time snapshot. Report per-family results and confidence intervals rather than just aggregate accuracy.
- Define the exact target CPU, thread count, RAM limits, model weight/runtime/quantization/grammar hashes and cold/warm configuration.

## Four-week feasibility sequence (indicative)

1. **Week 1 — Contract and oracle.** Specify the minimal typed IR, scope and legal operations; implement deterministic IR-to-SPARQL compilation; compare expert IR execution with reviewed gold SPARQL and inspect RDF evidence. Reject unsupported operators.
2. **Week 2 — Parser spike.** Run a ~1.5B-class quantized local model behind llama.cpp (alternatives allowed). Provide a fixed **authorized** catalog of candidate predicates/classes/entities to isolate semantic understanding from retrieval. Generate grammar-constrained IR, then validate all IDs, types, direction and scope independently in Rust.
3. **Week 3 — Hard cases and grammar integrity.** Test > vs >=, counts, inverse relations, dates, scope, ambiguous phrasing, missing facts, quoted attacker instructions in RDF labels, and unsupported query families. Verify the exact runtime/grammar combination **actually** rejects malformed outputs; do not assume grammar compliance from documentation alone.
4. **Week 4 — Holdout and decision.** Freeze prompts/configs before testing locked questions. Evaluate semantic IR, full answer sets, false-verification/wrong-plan errors, safe abstention, per-stage and end-to-end p50/p95/p99, peak RAM, and at least one ontology/time transfer split. Publish failures as well as successes.

## Comparator and attribution

Run deterministic query templates and expert IR/compiled-SPARQL as controls. Measure the local parser first with oracle ontology terms, then (if feasible) with actual retrieved candidate terms. This separates **semantic parsing errors** from **vocabulary retrieval failures**. A schema-valid IR alone is not a success.

## Release-gate agreement (set numerically before holdout)

Record predeclared thresholds for:
- **Exact answer-set match and per-question-family precision/recall/F1** against expert graph queries; use semantic IR accuracy for operator, predicate, direction, numeric value and scope.
- **Wrong-plan but successful-execution rate**, particularly incorrect queries presented as verified; high-risk false positives need the strictest gate.
- **Correct abstention and false abstention** on ambiguous, unsupported and incomplete-data questions.
- **Local deployment feasibility:** end-to-end p95, cold/warm latency, resident/peak RAM and reproducible model/grammar behavior on the target CPU.
- **Transfer gap** between same-domain holdout and second ontology/time snapshot, with disclosed catalog adaptation.
- **Reproducibility:** pinned graph, parser, grammar, IR schema, tokenizer, prompts and compiler versions.

Provisional recommendation: prioritize near-zero unflagged wrong-plan claims on the locked set, and prefer explicit clarification over plausible false answers. Avoid claiming statistical reliability from a small zero-error sample; use confidence intervals and larger pilot evaluation. If thresholds are missed, narrow supported families, ask the user to confirm a readable plan before execution, try a more capable local model, or ship Find first.

## User-facing truth contract

- **Plan interpretation:** show resolved relation names, edge directions, selected filters, aggregation, named-graph scope and any clarifications.
- **Execution verification:** SPARQL can establish that a specific compiled plan returns those bindings in the named graph snapshot. It cannot prove the model understood the question.
- **Data provenance:** cite source graph, snapshot and supporting triples, while explicitly distinguishing what the graph asserts from real-world truth.
- **Completeness:** never infer exhaustive matching from top-k retrieval; only assert complete-within-scope for an executed formal query with clearly defined scope/semantics.
- **SHACL:** report constraint conformance only for supported constraints and pinned semantics; never use it as a generic truth certification.

## Artifacts to check in

A fixture license/source manifest; question dataset schema and gold IR/SPARQL; minimal compiler, parser runtime+grammar checks; fixed splits; reproducible evaluation script; failures/abstention casebook; benchmark JSON report; go/revise/stop decision. The compiler, public data/reference fixtures, actual local parser experiment and evaluation framework are now implemented; see [the implementation status and remaining approvals](phase-0-evaluation.md). This protocol's independent-review and deployment-readiness goals remain unmet.
