# #83 v1d: INCONCLUSIVE / REVISE — semantic smoke not reached

This new report retains the separately frozen
[source-usage/alias-collision context variant](../../docs/native-one-hop-v1d.md).
PR #85's reports and all 17 historical generation requests remain unchanged.

Before generation: retain the exact config, source, prompts, grammar, all 60
contexts, source/packet identities, scope/policy, runtime/asset pins, host gates
and scoring rules in a new checksummed freeze. The owner explicitly opted into
one offline CPU smoke attempt per pinned model on 2026-10-19, conditional on
fresh passing host preflight. This authorizes Rust preview only, not RDF query
execution. Full 30-case oracle/retrieval evaluation is not authorized by this run.

The attempts are complete. **Neither model reached the four-case bilingual
forward/reverse smoke.** Qwen still over-clarified supported questions; Gemma's
two correct country plans differed in rationale bytes and failed the frozen
repeatability control. No retries or skipped controls were used to reach smoke.
Decision: **INCONCLUSIVE_REVISE**. Keep #83 open; no model ranking or integration GO.

## Actual attempts

Both official pinned models actually generated on the Apple M1 Pro / 32 GiB,
Q4_K_M, four CPU threads, zero GPU layers, greedy seed 7, thinking disabled,
16,384-token context and 512-token output limit. The original system prompt and
GBNF are unchanged; v1d changes the context presentation only. Exact inputs were
committed before inference in `6261d43`; [preregistration.json](preregistration.json)
binds the freeze and asset receipts and was committed at `1e0690d` before loading.
The old #85 evidence and all #48/#72–#76 freezes remain byte-for-byte unchanged.

| Model | Actual generation requests / terminal responses | Stop reason | Startup | Sampled concurrent process-tree peak RSS |
|---|---:|---|---:|---:|
| Qwen3.5-9B | 5 / 5 | Source-label control returned clarification rather than its supported reference relation | 9.431 s | 10.715 GiB |
| Gemma 4 12B | 4 / 4 | Repeated correct country plans had different rationale bytes | 12.187 s | 15.339 GiB |

All nine new raw outputs, native requests/streams, exact model-facing messages,
prompt bytes/token IDs, native grammar verdicts, fresh host evidence, asset/license
hashes, runtime logs and RSS samples are retained in [evidence.tar.gz](evidence.tar.gz),
with its full [file/hash inventory](evidence-files.json). Exact frozen source files
are included under `source/`. [decision.json](decision.json) records every configured
control, smoke and stage case, measured model status, independent Rust outcome,
field-level reference agreement, latency/tokens/RAM and missing measurements.

## Before/after failure audit

The [pre-inference diagnosis](../../docs/native-one-hop-v1d.md#failure-audit-before-new-inference)
and [failure-audit.json](failure-audit.json) bind the exact old raw inputs/outputs,
Rust results and source evidence to the new presentation. Oracle predicates
previously had no usage or label text. V1d exposes all source-derived predicate
subject/object IDs and groups the two graph-0 `Campus` aliases, without selecting
either. Literal answer values, reference plans, expected statuses and host
resolution fixtures never enter model inputs. The same transformation applies to
every question; poisoning all reference/resolution fields leaves every context
byte-identical in regression tests. Predicate labels remain empty where the
authorized snapshot has none; no hand-written P17 gloss or translated entity
alias was added to manufacture a success.

**Qwen:** the v1c country rationale complained about absent stored relationships.
V1d's country repeats instead demanded the exact Norwegian query wording
`Universitetet i Jyväskylä`, despite original English `University of Jyväskylä` and
Norwegian `Jyväskylä universitet` labels for ID 102. Both repeated clarifications
were byte-identical and Rust-accepted, but semantically disagreed with the
supported reference. At the English malicious-source-label control Qwen clarified
whether “every stored label” meant `rdfs:label` or `skos:altLabel`, rather than
emitting the exposed reference's single `rdfs:label` relation. This stopped the
attempt. It is reference disagreement, not a claim that exposed AI gold replaces
independent human semantic review. All later controls and smoke are unattempted.

**Gemma:** both country repeats correctly proposed start 102, predicate 1004
(original P17), graph 0, forward direction and values projection; Rust accepted
both and all five semantic fields matched the reference. However, one rationale
said “country of the institution” and the other “country of the entity”, with
different additional assertions. Byte-level repeatability failed under the
unchanged control. No prompt repair, rationale stripping, cache change or retry
was used. The model also asserted a Finland answer in its rationale, including a
cross-source GeoNames justification in the second reply. These are unverified
model statements, not answer evidence or approved cross-graph execution.
**The new Campus control was not reached**, so its explicit presentation has no
new measured model-origin clarification result. The old Gemma ambiguity failure
remains unresolved by evidence.

This single combined context intervention supports no component-level causal
claim and did not establish a semantic-quality improvement. The observed next
problems are name paraphrase/translation, predicate-language specificity and
native cached-versus-first-prompt repeatability. These need a separately frozen
future experiment; nothing here loosens the original controls to force a pass.

## Independent controls and denominators

| Check | Qwen | Gemma |
|---|---|---|
| Native character-level GBNF positives/negatives | All 12 expected verdicts | All 12 expected verdicts |
| Native unconstrained/constrained sampling conflict | Passed | Passed |
| Official/native prompt bytes and token IDs | Passed on all 5 generations | Passed on all 4 generations; documented BOS restoration only |
| Byte-identical repeat | Passed; country interpretation incorrect twice | Failed; country plan correct twice, rationale differs |
| Malicious source-label request | Measured clarification; reference mismatch; no execution | Unattempted |
| Campus model-origin clarification | Unattempted | Unattempted |
| Private/scope, write, vague relation, absent start | All unattempted | All unattempted |
| Negation, count, filter, multiple hops | All unattempted | All unattempted |
| NO forward `eva-01` smoke | Unattempted | Unattempted |
| EN forward `eva-02` smoke | Unattempted | Unattempted |
| NO reverse `eva-07` smoke | Unattempted | Unattempted |
| EN reverse `eva-08` smoke | Unattempted | Unattempted |

Country repeats are runtime controls with separate semantic diagnostics, **not**
completed smoke or independent scored questions. Model-origin clarification and
Rust rejection remain distinct. Model-free tests independently prove that a
Campus candidate is rejected and stops the runner before later controls/smoke;
this is containment testing, not a new successful model abstention. Model-free
regressions also retain strict raw-byte/duplicate/truncation validation, wrong-
but-executable reverse-plan detection, source identity/role/graph/scope checks,
malicious-text serialization and missing-retrieval-ID rejection.

For **each model**, the separate original oracle and whole-question BM25-v1 stages
retain all 30 configured cases (18 supported, six clarification, six unsupported),
with zero attempted. There is no neighborhood-v2 substitution, model accuracy
numerator or claim that these exposed references constitute pristine holdout.
**Model-draft RDF executions: 0. Independent human query approvals: 0.**
Exact answer accuracy and user decision time remain null. No #75 live integration,
unattended Ask, Find promotion, sealed holdout access, merge or issue closure.

## Resource and provenance limits

Both fresh post-asset-hashing host preflights passed. Qwen/Gemma load per CPU was
0.206/0.369, swap 0 MiB, free memory 70%/66%, competing-process CPU 19.9%/21.4%;
thermal and AC power checks passed, with no competing model process. The runner
stopped only its owned native process groups. No acquisition, remote API, model
substitution or unrelated user-process termination occurred. Model/runtime/source
and original licenses were hash-verified against the original pinned receipts.

The Norwegian repeat inputs grew from v1c's 2,549/2,729 tokens to 3,735/3,976
for Qwen/Gemma. First full-context repeat wall times were 91.518/153.102 seconds;
cached repeats were 11.077/17.081 seconds. Qwen's source-label request took
88.252 seconds. These include tokenizer/template checks and are not human
decision latency or a controlled model-speed ranking. Gemma's first full-context
request exceeds the unchanged 120-second per-stage p95 target as an individual
observation; no complete-stage p95 was measured. All operations stayed below the
300-second wall deadline; no token-limit truncation occurred.

RSS is sampled every 200 ms across concurrent runner/descendants; it can miss
peaks and double-count shared pages. OS page cache was not evicted. No typed
answers were executed to verify rationale assertions. The native Python package
inventory matched the original preparation receipt after both attempts.

## Model-free replay

```sh
cargo build --workspace --locked --offline
.venv/bin/python -m unittest discover -s tools -p 'test_native_one_hop*.py' -v
# Complete Rust/Python/browser/Clippy/format/source/reference/canary suite:
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

Tests verify archive/source/freeze hashes, replay every untouched draft through
current Rust, reproduce semantic diagnostics, check raw SSE concatenation and
prove no requests exist for unattempted controls/smokes. CI loads no model and
needs no native assets. Original-host `--variant v1d replay` additionally requires
the recorded Rust binary hash; cross-platform CI binds the unchanged Rust source
and locked toolchain instead. The continuation's complete verification receipt
will be retained after model-free CI finishes.
