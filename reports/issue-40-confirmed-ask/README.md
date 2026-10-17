# Issue #40 — experimental Confirmed Ask evaluation

Date: 17 October 2026. **Engineering prototype only; no product/release GO.**
[Owner prototype authorization](https://github.com/grove/graph-verity/issues/40#issuecomment-6234956205)
allows an opt-in deterministic selection/confirmation flow. User need is an
unproven hypothesis: some Find users may need a bounded path query or distinct
count after inspecting exact entities/predicates and scope.

## Automated regression evidence

The new model-free suites contain **12 tests: 8 core and 4 CLI**. These are
engineer-authored assertions over public/synthetic data, not independent semantic
review, participant observations or a measure of natural-language accuracy.

| Boundary / behavior | Reproducible coverage |
|---|---|
| Complete readable preview | Exact start/predicate IRIs, actual subject→object direction, every graph, snapshot, terminal projection, typed operator/lexical/datatype/language, distinct-count meaning, row/evidence limits and timeout |
| Deliberate selection | Only the `follow_path` template, 1–2 exact directed steps, optional terminal typed filter, values or distinct count; no question parser/model invocation |
| No execution without approval | EOF, Enter, cancellation, `yes`, missing approval, wrong/stale ID and malformed/oversized approval all yield cancellation/rejection; previews contain no query results |
| Approval invalidation | Edited start, predicate, direction, step graph/count, filter, output, row limit, version, snapshot; revoked policy, changed evidence limit and authorized cross-scope change reject old approval |
| Authorization before disclosure | Private graph/entity/predicate canaries never enter previews or error messages; independently validated graph-local identifiers and datatypes |
| Untrusted RDF text | Injection-bearing label (SERVICE/write/approval text and terminal escape), language/datatype and source graph preserved as quoted result/evidence data; labels never become preview instructions |
| Execution/evidence limits | Original directed source triples and immutable snapshot identity retained; row and evidence truncation separate; zero/empty result keeps open-world unknown and no truth/interpretation claim |
| Actual CLI workflow | Offline Norwegian Find → Norway IRI → exact P36 selection → preview → approval → Oslo binding/source triple; count mode also exercised |
| Four public Phase 0 wrong executions | Each original saved raw candidate and its extracted raw plan is rejected as Ask input; all four original free-text questions rejected; CLI rejects all four saved candidates before preview |
| Positive original probes | Explicitly selected inverse ownership and municipality→company→contract templates return the intended exact public source IDs, with scoped source evidence |
| Contract stability | Separate pinned Ask schema parity; existing frozen v1/compact contracts and historical reports untouched |

The four historical probes are source `inverse`, source `two-hop`, source
`alias` (ambiguous “Felles AS”), and transfer `negation` (companies with no
contracts), identified in the [original forensic analysis](../../docs/issue9-forensic-analysis.md).
Their saved Qwen outputs remain failures. Rejecting an incompatible proposal
format is containment, not successful interpretation. The two positive path
tests use deliberate, engineer-selected IRIs/directions; they do not show a user
can reliably translate those questions. Ambiguous labels require exact IRI
selection, and open-world negation has no template. No old failure was rescored
as a model success.

Verification commands from the repository root:

```sh
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
cargo test --workspace --locked --offline
.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -v
.venv/bin/python tools/verify_pre_llm.py
```

The Rust/Python suites, formatting and Clippy pass locally. The full repository
verifier must also pass on the clean publication commit and in CI; it checks
retained source/reference evidence and historical negative results without
running models or opening the sealed Ask holdout. CI status belongs to the PR,
not an inferred human-review attestation in this report.

## Usability evidence and misunderstandings

**Human participants: 0. Human task attempts: 0. Independent semantic reviewers: 0.**
No recruitment or observations occurred. Task success, misunderstanding rate,
false-confidence rate and user demand are **unmeasured**, not zero. Automated
checks that warnings appear cannot show people notice or understand them.
No expert gold or review attestation is claimed.

Engineering inspection identified the following **potential**, not observed,
misunderstandings. The preview addresses them, but its effectiveness is unknown:

| Potential misunderstanding | Current disclosure / task to evaluate |
|---|---|
| Incoming means the anchor owns the result | Display actual subject→predicate→object; ask the participant to explain owner/owned direction before deciding |
| Two hops return intermediate companies | Show both connected steps and terminal-only projection; ask which variable is returned |
| Count counts paths or proves completeness | State COUNT(DISTINCT terminal), exact graphs/snapshot, limits and unknown real-world absence; use shared-path/zero examples |
| First Find result resolves an ambiguous name | Require deliberate exact IRI selection; ask the participant to distinguish two same-label entities |
| Approval survives an edited plan/scope | Require a new exact ID; observe a stale approval and ask what must be reviewed again |
| “Executed” or evidence means the question/fact is verified | Keep interpretation not assessed, truth not established, open-world unknown and independent truncation fields; ask participants to explain the limits in their own words |
| RDF text supplies trusted instructions | Keep strings quoted as data, no labels in preview; include an injection-bearing result label and observe the response |

Before readiness claims, freeze a user-facing prototype revision and task set,
recruit actual intended Find users and disclose recruitment, experience,
participant count, completed/abandoned tasks and exclusions. Include direction,
two-hop projection, typed comparison boundaries, distinct counts/shared paths,
zero/unknown, ambiguous labels, scope/snapshot edits, cancellation and separate
row/evidence truncation. Ask participants to explain the proposed operation and
its limits **before approval**, then compare their explanation and selected plan
with independently assessed task intent. Record assistance separately.

Report each misunderstanding (including correctly executed but unintended
plans), cancellation, unsupported request, and confident incorrect belief.
Measure task success and false confidence with denominators at both participant
and task level; repeated tasks are correlated, not independent samples. Preserve
failures and qualitative comments. Do not substitute test assertions, fabricated
reviewer identities or the public AI-reference cases for independent review.
Recruitment/sample size and acceptance thresholds require a separately recorded
study plan; no release-readiness threshold is retroactively selected here.

## Release boundary and residual risk

A person can approve the wrong exact plan; the digest cannot prove understanding,
authentication or a human act. Exact IRI selection avoids label guessing but
puts domain/graph knowledge demands on users. The CLI JSON flow and long hash
may be cumbersome. There is no evidence yet that this interface is useful or
prevents false confidence. An identical immutable plan/policy approval is
replayable; this local read-only prototype has no expiry/session ledger.

No unattended free-form Ask, automatic model plan approval, stronger-model
trial, external-service execution, raw-SPARQL/write/SERVICE path, production
serving, release promotion or sealed-holdout access was added. Prior Find/model
benchmarks remain frozen, BM25 stays selected and fusion stays deferred.
Issue #40 remains open until implementation/evidence and passing CI are merged;
any product release still requires demonstrated need, usability evidence and a
separate explicit decision. See the [operator contract](../../docs/confirmed-ask.md).
