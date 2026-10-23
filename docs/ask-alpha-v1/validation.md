# Model-free validation and preservation

**All 41 unchanged full-pipeline checks pass**, on committed candidate
`6962fc54baa0641441169f2472f60c6f137b9edb`. Receipts/documentation added afterward
do not change any registered source or test. Decision: **INCONCLUSIVE_REVISE**.

[verification.json](verification.json) records every command, original deadline,
exit status and duration. [validation.json](validation.json) binds the receipts,
new unused registration, frozen prompt archive and validation logs.

- Current Python: **170 + 191 = 361 tests**, no skips. The split checks took
  352.6 and 190.4 seconds, each within the unchanged 600-second check deadline.
- Frozen pilot: 15 tests; original v1g source fingerprint guard: one; historical
  NL Ask/export checks: six + six + four. The separate historical vocabulary
  replay also passes. Original registrations are never refreshed to accept changes.
- Rust: **100 tests**, formatting and Clippy with warnings denied pass.
- Required real Chrome journeys, source/scope canaries, source integrity,
  deterministic byte rebuilds, schema parity, compiler oracles and final clean
  tree checks pass. Cold Chrome startup passes in 0.669 seconds under 45 seconds.
- Focused new package: **10 tests pass**, including the real browser extension,
  deterministic-assembly binding tests, duplicate/invalid/missing/timeout scoring,
  source-witness/definition checks, reference-free packet rendering, frozen token
  arrays and mock-only fatal-stop/no-retry behavior. Browser child deadline stays
  120 seconds. No model or tokenizer is loaded by CI; tokenizer output is checked
  from the committed archive using hashes and ordinary JSON.
- Original PR #105 evidence analysis reproduces using `analyze.py --check`, without
  inference or subprocesses. No historical evidence or score is repaired.

[preservation.json](preservation.json) verifies **1,401 of 1,402 original tracked
files unchanged**, with exactly one allowed test-only change: the four-line
opt-in hook in `tools/supervised_ask_browser.mjs`. Every product source, Rust file,
existing fixture/reference, original snapshot and security rule is unchanged.
All **18 original registration files** and the original Rust CLI binary match.
Four retained Qwen/native runtime files also match by hashing only, including
Q4 weights and llama-server. Post-pipeline checks confirm these facts again.
The new registration has **no attempt ledger and no run directory**.

The full pipeline passed on its first attempt. Earlier focused attempts found
mistakes in new test scaffolding: misuse of RDFlib's parse return value, a
sandbox-blocked loopback bind, a restrictive fixture wrapper that did not preserve
the unresolved `None` outcome, and incomplete timeout-test mocks. The corrected
tests pass; no product behavior, source data, runtime/resource gate, validation
rule or check deadline changed to obtain that pass. The isolated browser-expiry
fixture deliberately uses a shorter two-second review lease; production remains
120 seconds.

[validation-logs.tar.gz](validation-logs.tar.gz) retains **116 log files** from
focused failures/reruns, model-free preparation and every full-pipeline check.
[validation-logs-files.json](validation-logs-files.json) records original and
published SHA-256 values. One expired private loopback URL is redacted from the
published browser-failure log; the original remains under the ignored local
`artifacts/ask-local-alpha/work` directory and its original digest is retained.
No failed output is silently dropped and no deadline is extended.

[synthetic-score.json](synthetic-score.json) and
[synthetic-failures.md](synthetic-failures.md) retain the generated machine-readable
and readable failure analysis. There are 60 scheduled observations in each
explicitly synthetic arm, with **57 completed pairs**, all missing cases retained.
The five-field fixture matches 24/29 supported references; the assembly fixture
matches 25/29. Each exposes two determinate wrong-but-executable plans and one
unresolved executable guess. Different timeout/transport/graph-drift controls
were deliberately injected: these numbers demonstrate accounting and mechanical
constraints, **not model accuracy or architecture superiority**.

Retrieval coverage is 28/29 supported cases. On alpha-08, clarification is
appropriate for the actual packet's missing numeric start; its source-level plan
still does not count as produced. The raw `false_clarification` counter is relative
to the supported source reference and includes this case: use the separate
`missing_numeric_vocabulary`/retrieval fields to avoid attributing it to semantic
model failure. Free-text relationship-meaning assertions still require source
audit; field scores do not automatically establish a rationale's correctness.
Only one disclosed synthetic source-evidence receipt is scored in each arm;
real browser/source evidence is independently checked by deterministic fixture
tests. No live-model answer agreement is measured.

The new model-free preparation seals 64 requests with maximum **12,413 input +
512 reserve = 12,925 < 16,384 tokens**. The exact future command and separate
owner authorization request are in [trial.md](trial.md). Registration SHA-256:
`55af85f8f5c15e45b46653d78e6e92cfe5c03a84fabfcf75be622e63c8386464`;
archive SHA-256:
`4c094d907b8debd770a0c4c9d564cc339deb91302c166ed90164f2ad34a3998a`.

**No inference, model downloads, network inference, sealed holdout access,
model-generated RDF execution, #75 live integration, automatic merge or #83
closure. Human reviewers/participants/observations: 0.**
