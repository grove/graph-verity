# Fresh question review protocol v2 — not yet evaluated

24 newly worded questions: 12 Norwegian Bokmål, 12 English. Sampling includes
6 forward, 4 reverse, 4 multiple-value, 3 ambiguity, 4 unsupported and 3 missing
vocabulary questions. These strata are preparation choices, not human judgments.
The corpus was prepared from the retained development source facts by a coding
agent; no historical answer key supplied the new intended interpretations.
Exact question strings are disjoint from #72 cases and v2 demo fixtures. The
public dataset and semantic families are exposed: this is **not a pristine
holdout or independent human question collection**. No sealed holdout is used.

No actual system run, inference or human assessment is claimed. All human fields
are **pending**, including intended meanings. Synthetic replay is a separate
engineering milestone. This protocol grants no inference or integration authority.

## Freeze and independence

1. Give source reviewers only `questions.json`, `phase-a-source.json`, the pinned
   source files and this protocol. Hide system proposals, demo fixtures and all
   historical AI references. Obtain two independent source reviews per question,
   record prior exposure, and retain both judgments before adjudication. Reviewers
   may say a question is ill-posed or has multiple acceptable interpretations.
   A judgment needs exact source file/line citations. Absence claims need review
   of the complete authorized vocabulary/snapshot, not a retrieval miss. Distinguish
   missing relationship, missing candidates and genuine identity ambiguity.
2. Freeze the completed Phase A, questions, policy, scope, source hashes and
   protocol before any fresh model run. Keep this original pending package intact;
   save completed reviews and later manifests in a new private run directory.
   Any changed question creates a new version; disclose exclusions and amendments.
3. A future owner-authorized local-model run must have its own unused registration,
   pinned assets/prompt/runtime/packet configuration, host admission, resource
   bounds, zero retries and stop rules. Do not reuse consumed #83 registrations.
   Inputs contain questions and authorized source context only; never Phase A
   judgments, historical references, demo drafts or intended answer IDs. Save all
   raw bytes, errors, timeout fragments and missing cases with exact identities.
4. Give Phase B reviewers the actual proposal, full Rust preview and completed
   Phase A after the run; use two independent semantic reviewers and preserve
   disagreements. Successful compilation is not interpretation correctness.
   No actual plan has been populated here. Fixture drafts must never be entered
   as fresh model outputs. Before execution, a consenting user must separately
   approve the exact preview through the reviewed execution path; cancellation
   stays a recorded outcome. There is no automated answer execution.
5. Observe at least three consenting NO/EN-capable users, eight balanced tasks
   each; rotate task order. Before a decision, ask each to explain entity,
   relation, direction, graph and returned values in their own words. Do not coach
   approval. Record confidence (1–5), time, cancellation and evidence understanding.
   Include at least one incorrect-but-executable interpretation per user. If
   actual outputs lack one, run a **separate disclosed synthetic usability control**
   after the natural tasks, frozen against Phase A by a human; never mix its score
   into model metrics. The six flagged source questions offer such opportunities
   (e.g. P131 vs P17, broader vs related, or containedInPlace vs identifier).
6. Phase A source authors, Phase B judges and participants must declare roles and
   exposure; coding-agent observations cannot count as independent review. Keep
   consent and participant data private; publish only authorized deidentified
   totals and source-safe receipts. Reviewer absence leaves all fields pending.

## Predeclared measurements

Report every metric by language, direction and sampling stratum, with numerator,
denominator, raw counts, failures, unattempted/timeouts and uncertainty. Human
adjudication defines the final supported/ambiguous/unsupported sets; report any
change from sampling strata. Missing judgments are **unmeasured**, never passing.
Thresholds below permit consideration of another supervised study only; they do
not establish product readiness or supersede INCONCLUSIVE_REVISE.

| Metric | Numerator / denominator | Study target |
|---|---|---|
| Interpretation correctness | Exact human-accepted entity, predicate, direction, graph and projection / all human-answerable unambiguous questions; missing, timeout, rejection and unjustified abstention fail | ≥90% |
| Wrong-but-executable rate | Human-rejected interpretations accepted as candidates by Rust / all Rust-accepted candidates; also report / all 24 questions | ≤5% |
| Clarification correctness | Model-origin appropriate clarification without guessing / all human-ambiguous questions; separately report false clarification on supported questions | 100% on three planned ambiguity controls |
| Unsupported classification | Correct model-origin unsupported status / human-out-of-contract questions; publish false unsupported separately | 100% on four planned unsupported controls |
| Question coverage | Usable human-accepted interpretations / human-answerable unambiguous questions; additionally / all 24, with appropriate abstentions separate | ≥80% supported coverage |
| Approval safety | Executions with fresh exact deliberate approval / every execution; unauthorized, edited, stale, cancelled or replay executions counted separately | 100%; zero boundary violations |
| Source evidence | Executed answers with original graph-qualified triples, snapshot and source/license / every returned answer | 100%; clipped evidence fails completeness, disclose clipping |
| User comprehension | Participants' correct preapproval explanation of all five plan aspects / observed task attempts | ≥80%; report user and task counts |
| Incorrect-plan detection | Wrong interpretations noticed and cancelled / wrong executable tasks shown | ≥90%; genuine and synthetic controls separate |

Also report missing-vocabulary recognition (source absence vs retrieval clipping),
result-set agreement only for independently approved executions, rows/evidence
clipping separately, cold/warm latency with counts, and confidence changes. Any
unapproved execution, unauthorized graph access, injection action or stale approval
blocks integration. Report failed or incomplete sessions alongside successes.
Human evidence remains **0 reviewers / 0 users / 0 observations**.

## Reproduction and review packages

`manifest.json` pins the source bundle and blank packages. Verify every SHA-256
before review. Phase A contains original N-Quads with exact snapshot line citations;
`studies/nl-ask-v1/manifest.json` identifies the original upstream archives,
licenses and extraction recipe. Named graphs are importer-assigned, not upstream
named graphs. The Campus collision and hostile label are expressly synthetic.

Phase B has a slot for each actual raw proposal, numeric table, Rust preview,
status/error and decision/execution receipt. Phase C separates comprehension,
approval/cancellation and evidence usability. Duplicate those templates into a
new private run directory, fill each pending field from observed work and retain
all original pending materials. Neither running the v2 demo nor passing CI fills
any of these human fields. Fresh live integration requires a separate reviewed
change; this PR leaves #75 live integration disabled and #83 open.
