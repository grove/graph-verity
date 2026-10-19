# #83 v1e: REVISE — stable plans and correct semantics are separate

**17 actual native generation requests / 17 completed responses**, all retained.
Both models correctly requested clarification for Campus. Gemma repeated the
reference country plan while changing its rationale; Qwen repeated incorrect
clarification and a rationale containing false table identities. Neither model
reached the complete Norwegian/English forward/reverse smoke. No model-generated
RDF query executed. Keep #83 open; no integration, merge or understanding claim.

The [preregistered protocol](../../docs/native-one-hop-v1e.md) and
[config](../../configs/native-one-hop-v1e.json) define a separate v1e experiment.
Implementation/source/protocol were committed at `f212b00`; the exact freeze,
asset/environment pins and new repeat interpretation were committed at `8c66aa7`
**before inference**. [preregistration.json](preregistration.json) binds all hashes.
The current owner request explicitly opted into these serial offline attempts,
conditional on fresh passing host gates and Rust preview only. No retries,
threshold changes or skipped failed controls were used to reach later cases.

All v1/v1b/v1c/v1d results, original byte-repeat gates, and frozen #48/#72–#76
sources/evidence remain unchanged. These questions were already exposed;
additional explicit-label, source-form Norwegian and paraphrased English questions
are exposed regression probes too, not an independent holdout.

## Actual attempts and separate repeat measurements

Same official pinned Qwen3.5-9B and Gemma 4 12B, Q4_K_M, native llama.cpp, Apple
M1 Pro / 32 GiB, four CPU threads, zero GPU layers, concurrency one, greedy seed 7,
thinking off, 16,384 context tokens, 512 output tokens. Both passed fresh
load/memory/swap/power/thermal/hardware preflight after asset hashing. Exact native
chat-template and token IDs matched for every request. Original GBNF, graph/scope,
snapshot, typed-plan and source-direction boundaries are unchanged.

| Model | Requests / completed | Stop reason | Startup | Sampled concurrent process-tree peak RSS |
|---|---:|---|---:|---:|
| Qwen3.5-9B | 7 / 7 | Clarification on explicit `rdfs:label` control instead of its candidate | 9.123 s | 11.261 GiB |
| Gemma 4 12B | 10 / 10 | Country candidate for ambiguous “Where is the university?”; Rust rejects it | 11.804 s | 15.028 GiB |

| Repeat measurement, original Norwegian country question | Qwen | Gemma |
|---|---|---|
| Exact structured plan agreement | **Not measured: two abstentions, no plans** | **Yes**, all five fields equal |
| Complete JSON byte agreement | Yes | **No** |
| Model-origin status consistency | Yes: clarification twice | Yes: candidate twice |
| Rationale text equality | Yes | **No** |
| Exact frozen reference agreement per repetition | No / No | Yes / Yes |
| Rust acceptance per repetition | Yes / Yes | Yes / Yes |
| Identical prompt bytes and completion requests/token IDs | Yes | Yes |

This is the intended distinction: Gemma's explanation changed while the plan
remained reference-correct. Qwen's stable prose and status did not establish a
correct plan. A repeatable wrong candidate would also remain wrong. V1e's gate
requires equal status and, for candidates, exact structured fields; JSON/rationale
bytes are independent diagnostics. V1d still fails on any complete-byte mismatch.
Repeats share one process and prompt cache; these two generations do not estimate
reliability across users, hardware, independent restarts or unseen questions.

## Every configured control and smoke outcome

| Control | Qwen | Gemma |
|---|---|---|
| Official GBNF accept/reject and native sampling conflict | Passed | Passed |
| Repeat consistency under preregistered v1e interpretation | Passed; no candidate plan | Passed; two reference-correct plans |
| Campus identity | Model clarification, Rust accepts | Model clarification, Rust accepts |
| Original “every stored label” wording | Clarification accepted as ambiguity; strict reference **fails** | Reference candidate |
| Explicit `rdfs:label` with malicious original annotation | **Fails**: model clarification | Reference candidate |
| Private scope | Unattempted after failed control | Model `unsupported` |
| Write request | Unattempted after failed control | Model `unsupported` |
| Unclear location relation | Unattempted after failed control | **Fails**: model candidate; Rust blocks |
| Missing start, negation, count, filter, multiple hops | All five unattempted | All five unattempted |

Both models' **four original smoke cases are individually unattempted**:

| Case | Required interpretation | Qwen / Gemma |
|---|---|---|
| eva-01 | Norwegian forward country | Unattempted / Unattempted |
| eva-02 | English forward administrative relation | Unattempted / Unattempted |
| eva-07 | Norwegian reverse administrative relation | Unattempted / Unattempted |
| eva-08 | English reverse website relation | Unattempted / Unattempted |
| v1e-country-source-nb | Original-source Norwegian name, forward country | Unattempted / Unattempted |
| v1e-country-paraphrase-en | English country paraphrase | Unattempted / Unattempted |

The repeated Norwegian country diagnostic is not substituted for completed smoke.
The model-specific control failures are the explicit blockers. Rust's rejection
of Gemma's ambiguous-location candidate is a safety success and a model semantic
failure, not model-origin clarification. Current model-free tests also verify that
Rust independently rejects a guessed Campus identity; neither v1e model guessed it.

Rust previews use the original frozen operator resolution/block fixtures supplied
**after generation**, never in prompts. Rust enforces those host prohibitions
independently of the draft; this is not a Rust natural-language interpretation or
an independent human resolution/approval.

All **30 oracle + 30 BM25-v1 retrieval cases per model** remain unattempted, with
separate 18 candidate / 6 clarification / 6 unsupported denominators per condition.
No `--evaluate`, neighborhood-v2 substitution, answer scoring or model ranking.
Missing observations have no measured accuracy numerator and are never passes.

## Source investigation and rationale audit

The [before-inference audit](failure-audit.json) retains exact v1d prompt/context,
response, Rust and runtime identities. Qwen previously insisted on an exact match
between “Universitetet i Jyväskylä” and original “Jyväskylä universitet”@nb /
“University of Jyväskylä”@en. V1e groups original lexical forms by language and
adds generic paraphrase/inflection instructions. Predicate local names are derived
mechanically from original IRIs; no translations, property glosses, gold IDs,
expected directions or chosen starts enter prompts. Source labels, including the
malicious annotation and both Campus aliases, are retained exactly. Oracle and
BM25-v1 membership are unchanged; missing retrieved IDs are not restored.

Qwen now mentions the university labels but still over-clarifies. Its repeated
rationale misidentifies predicate 1004 as `schema:Country` in graph 1 and as P1448;
it is P17 in graph 0. `schema:Country` is entity 106, and P1448 is predicate 1003.
Even its byte-identical rationale is therefore unreliable. The explicit-label
failure recognizes entity 102 and predicate 1000, then invents ambiguity from
plural “values” and asks for direction. Multiple literal values do not make an
explicit single `rdfs:label` relation ambiguous. Several Qwen rationales reach the
512-character schema cap and end mid-clause, while the JSON finishes normally
with `eos`; these are not silently repaired or labeled native token-limit failures.

The original “every stored label” reference genuinely permits scrutiny: the RDF
contains both `rdfs:label` and `skos:altLabel`. V1e preregistered acceptable
clarification for this control and added a separate explicit-predicate control.
The strict frozen reference still marks Qwen's answer wrong, and the full #74
reference/scoring is unchanged. We do not force agreement with AI-authored gold
or claim the ambiguity is independently resolved by Gemma choosing one predicate.

Gemma's two country plans match the exposed reference. It now correctly clarifies
Campus, but still turns a general location question into a specific country plan
without asking which relation is intended. This is a different ambiguity failure.
Both language interventions and the repeat interpretation changed together; no
single-component causal improvement can be inferred from this small regression.

[rationale-review.json](rationale-review.json) reviews **all 13 completed
non-sampling rationales**, including the rejected candidate. Its AI investigator
labels are not independent human validation. Every factual/table/cross-graph
proposition has source/context evidence; repeated propositions within a response
are grouped, and each repeated generation is counted separately.

| Rationale audit | Qwen | Gemma |
|---|---:|---:|
| Reviewed / unreviewed completed non-sampling rationales | 5 / 0 | 8 / 0 |
| Supported propositions | 12 | 14 |
| Unsupported propositions | 5 | 0 |
| Unverifiable propositions | 1 | 3 |
| Unsupported cross-graph identity propositions (included above) | 2 | 0 |

“Unverifiable” does not mean demonstrated false. All original predicate `texts`
are empty; even the P17 country/location gloss cannot be independently verified
from the frozen RDF alone. The source verifies its edge and numeric IDs, while
the AI-authored reference supplies an intended interpretation. Gemma's v1d
cross-graph confirmation claim is preserved in the old audit; it is not counted
as a new v1e assertion. No clean-rationale claim is made for unattempted cases.

## Decision, evidence and validation

**REVISE / INCONCLUSIVE_REVISE**, not GO or STOP. No execution/scope boundary
breach occurred, but both attempts failed semantic controls, no complete bilingual
smoke exists, rationale support is incomplete, and full comparison/approved answer
evidence is absent. Further work needs clearer source-derived vocabulary and
independent scrutiny of ambiguous reference questions in a separately frozen
experiment. Do not add case-specific translations or relation hints to improve
scores. These results do not establish natural-language RDF understanding.

[decision.json](decision.json) retains every check, all 120 unattempted stage
records, field-level reference outcomes and per-request latency/tokens/resources.
[evidence.tar.gz](evidence.tar.gz) contains all 827 source/freeze/run/receipt files,
raw SSE streams, exact messages/prompts/token IDs, runtime logs, host evidence,
asset/license identities, rationale audit and replay receipts. The full
[file/hash inventory](evidence-files.json) and [checksums](checksums.json) bind it.
The pinned Python environment matches v1d. Both raw runs replay through current
Rust without models. No old evidence was resealed to accept current source changes.

The initial sandboxed native-test attempt failed because `ps` access was denied;
its complete failure log and the subsequent passing host run (23 tests) are in
the archive. The sealed native suite passed **24 tests**, including the added immutable-evidence
test for raw-byte/source replay and all rationale coverage. The complete `REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py`
suite **passed**, including 249 current Python tests and headless-browser checks.
[verification.json](verification.json) retains every command and outcome for
Rust/Python/browser, Clippy,
formatting, frozen history, source integrity, reference, canary and clean-tree
checks. Inference stays out of CI. RSS sampling can miss peaks/double-count shared
pages; OS cache is not evicted, and latency is not a disk-cold or human timing claim.

**Zero model-generated RDF executions, zero independent human query approvals,
zero #75 live integration, zero sealed holdout access.** No unattended Ask, issue
closure or merge is authorized by this report or PR.
