# Ask Alpha observable r2: admission blocked before invocation

**INCONCLUSIVE_REVISE. No inference command was invoked.** Fresh host admission
failed because swap usage was **2,448.94 MiB**, above the unchanged **1,024 MiB**
maximum. No admission retry, inference invocation, resume or replacement
registration followed. This is an operator-authored admission report, not a
runner result or an interrupted model attempt.

The owner separately authorized one exact invocation after the preparation gate.
The authorization required stopping on any failed gate. Identity checks passed;
the optional model-free host preflight then blocked before the invocation.
Consequently the invocation count is **zero** and r2 remains **unconsumed**.
This report grants no future execution or retry authority. A later decision must
respect the owner's stop instruction and repeat exact verification and fresh
admission before considering the same unconsumed registration.

## Exact identities and preparation

| Identity | Verified value |
|---|---|
| Experiment | `ask-alpha-preview-v1-observable-r2` |
| Merged PR | [#109](https://github.com/grove/graph-verity/pull/109) |
| Inspected `main` | `d71b544ad5ccbfdcb8b6a847c362075e5e422b83` |
| Reviewed head | `0d0a1ada6bf563ca4c094f845f6f3aaee125779c` |
| Registered source | `4c1888e441e3db26073fd06ced05447aff195346` |
| Registration SHA-256 | `3eab8a532fa45b81301df9d4fba2b50b8153433f44bd752d63d05cacd42ab98d` |
| Archive SHA-256 | `310216acbaeb34d15752b7452658a39a4eaa358c4456d451085770efb95fe516` |

The tree was clean and already at the merged source. The reviewed head has the
same tree. The committed freeze was already restored; `unpack` and `prepare` were
not run. Both required verification commands passed before admission:

```sh
.venv/bin/python tools/ask_alpha_trial_observable_r2.py verify
.venv/bin/python tools/ask_alpha_register_observable_r2.py verify
```

The unchanged equivalence checker reproduced all 64 request identities/order,
199 non-metadata freeze members, 203 original source hashes and deterministic
successor archive bytes. Prompts, packets, full tokenizer arrays, graph bindings,
scoring and resource policies remain identical to consumed v1. The original
[PR #108 forensic report](../ask-alpha-v1-interruption-evidence/README.md) was read;
its five original ledger/run files, published copies, hashes and original
modification metadata were checked without rewriting them.

The command below was authorized **but not executed**:

```sh
.venv/bin/python tools/ask_alpha_trial_observable_r2.py run --allow-inference
```

Pinned Qwen3.5-9B revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, Q4_K_M
SHA-256 `fa502d3cb95fab7a6a563b9e057d94e6bae5ca737f056a4ffd05a9c25232d951`;
CPU only, four threads, zero GPU layers, concurrency one, maximum 64 completions,
zero retries and preview only. No generated RDF may execute. All original gates
remain binding; no model asset was acquired or substituted.

## Fresh admission evidence

[Original host receipt](host-before-invocation.json), captured
`2026-10-23T21:42:49.542512+00:00`, completed
`2026-10-23T21:42:49.590208+00:00`:

| Gate | Observed | Required | Result |
|---|---:|---:|---|
| Hardware | Apple M1 Pro, 32 GiB, arm64 | exact pinned host | pass |
| Load / logical CPU | 0.4587890625 | ≤0.75 | pass |
| Swap | 2,448.94 MiB | ≤1,024 MiB | **blocked** |
| Free memory | 79% | ≥40% | pass |
| Available disk | 112.996 GiB | ≥32 GiB | pass |
| Largest competing process CPU | 25.6% | ≤150% | pass |
| Named competing model processes | none | none | pass |
| Power | AC | AC | pass |
| Thermal/performance warnings | none recorded | acceptable state | pass |

The original native preflight ran with the frozen runtime configuration; all
inventory commands succeeded. No process was interrupted, swap reset attempted,
resource threshold changed or follow-up admission taken. This snapshot is not a
continuous host-wide process history.

The four exclusive successor execution paths were absent before admission and
remain absent: `attempt.json`, `stages.jsonl`, `diagnostics.json` and `run` beneath
`artifacts/ask-alpha-preview-v1-observable-r2/`. The durable journal is an invocation
claim, so it was deliberately not created. There is no runner exception,
traceback or stage cursor to report: this was a failed admission check before
`run`, not a runner interruption. No runtime counter was created.

## Complete denominators, no semantic observations

[Assessment JSON](assessment.json) preserves all 64 ordered identities, with
explicit unattempted outcomes and null response/semantic/runtime fields.

| Schedule | Scheduled | Attempted | Completed | Failed requests | Unattempted |
|---|---:|---:|---:|---:|---:|
| Native sampling controls | 2 | 0 | 0 | 0 | 2 |
| Identical construction controls | 2 | 0 | 0 | 0 | 2 |
| Semantic questions | 60 | 0 | 0 | 0 | 60 |
| Total | 64 | 0 | 0 | 0 | 64 |

Zero requests is source-bound accounting from not invoking the command; native
attempt/completion/byte counters are **absent/null**, not measured numeric zero.
The host blocker is not a failed model response.

- **29 supported reference plans:** no five-field agreement measured. This
  includes 15 Norwegian / 14 English and 17 forward / 12 reverse plans.
- **13 determinate non-execution cases:** eight unsupported operations and five
  absent authorized predicates; classification is unmeasured.
- **18 unresolved interpretations:** conservative behavior is unmeasured.
- **Languages:** all 30 Norwegian and all 30 English questions are unattempted.
  No language or direction performance comparison is available.
- **Wrong but executable, unsupported relationship claims and rationale
  contradictions:** unmeasured; there are no proposals or rationales to audit.
- **Static retrieval vocabulary:** the unchanged registered `numeric` helper
  confirms 28/29 supported plans have complete authorized numeric bindings;
  `alpha-08` lacks its start binding. This is frozen packet coverage, not model
  performance, and was not repaired.
- **Runtime:** no model startup, cold/first-draft latency, warm latency quantiles
  or sampled process-tree RSS exist. No native model-response bytes, SSE streams, fragments,
  proposal files or partial model responses were created.

No retained `run.json` exists, so the full registered outcome scorer and native
byte replay have no input. They were not run on fabricated observations. The
registered scorer remains unchanged; only its model-free numeric lookup was used
for static coverage. Agent-authored source-bound references are not independently
reviewed human truth, and Rust validity would not prove question understanding.

## Predeclared alpha assessment and next product action

The [predeclared criteria](../../docs/ask-alpha-v1/README.md#predeclared-alpha-gates)
are not met. Full semantic completeness is 0/60, no supported agreement is
measured, all conservative controls are unattempted, and resource admission failed.
There is no evidence of fresh-question understanding or local-alpha viability.

The minimum scope is the existing eight forward official-website P856 and
official-name P1448 questions for University of Tromsø/Q279724:
`alpha-11`, `alpha-12`, `alpha-31`, `alpha-32`, `alpha-33`, `alpha-34`, `alpha-45`,
`alpha-46`. All eight are unattempted. No minimum-scope pass is claimed. Country/date/admin-location and reverse families remain outside this minimum
scope and remain in the full 60-question schedule. No family was dropped after
seeing results. Human reviewers/participants/comprehension
observations remain zero.

Keep Find/manual/saved-fixture Ask as the available product paths. The next useful
action is for the owner to restore the pinned host below the swap limit, then
make a separate decision about fresh verification/admission for this **unconsumed**
r2 registration. Do not change the model, prompts, retrieval, limits or registration
to work around the blocker. Maintain **INCONCLUSIVE_REVISE**, keep #83 open and
live #75 integration disabled. No automatic merge or release is authorized.

## Validation and preservation

See [validation](validation.json), [preservation](preservation.json), the
[before-check baseline](baseline.json), [all validation logs](validation-logs.tar.gz)
and [checksums](checksums.json). The 11 focused interruption tests are mock-only
and use temporary synthetic ledgers; they do not invoke the registered command.
All **41** complete model-free pipeline checks passed: **195 + 177** current
Python tests (no skips), historical replay, **100 Rust tests**, required browsers,
formatting/Clippy and development source/oracle checks. The published evidence
self-check also passed. The full pipeline and focused interruption suite each
ran once. Source verifiers and the publication check were repeated successfully
during packaging; no failed validation check is omitted. The failed host gate
remains preserved verbatim.
The pipeline used the existing
Cargo isolation shim to preserve the registered Rust binary. Disposable historical
exports retain their own build directories. Original check deadlines are unchanged.

Reproduce the published evidence checks without project imports or a model:

```sh
python3 experiments/ask-alpha-observable-r2-admission-evidence/check.py
```

No model assets were downloaded, no other model experiment was invoked, no sealed
holdout was accessed, no model-generated RDF executed, no issue was closed and no
registration or historical evidence was changed. No replay/scoring success or
attempt-time asset verification is inferred from preparation or validation tests.
