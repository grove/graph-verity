# Gemma swap2048 evidence and retained Qwen comparison

**INCONCLUSIVE_REVISE. Independent human semantic review remains deferred.**
The separately authorized, single Gemma run completed 33/36 semantic observations:
19/19 oracle and 14/17 frozen whole-question BM25-v1. One BM25-v1 completion
timed out, stopping the run; the last two observations were unattempted. The
command exited 1 with `blocked_or_failed`, not a successful experiment. There
were no retries or model-generated RDF executions.

Keep [#83](https://github.com/grove/graph-verity/issues/83) open and
[#75](https://github.com/grove/graph-verity/issues/75) integration disabled.
No semantic GO, model ranking, exact-answer accuracy, human approval, new
status-rule ablation, or automatic merge follows from this evidence.

## Registration, authorization and original bytes

PR [#95](https://github.com/grove/graph-verity/pull/95) was verified merged into
main at `5ee7354465e02ea5ac5ef03f296f7dd60ded7dab` before preparation. The
original 1024 MiB swap gate was blocked by 1877.44 MiB swap usage. Its authorized
command was never invoked. The owner then requested exactly “Can we change the
ceiling to be 2048MiB instead?” The separate, append-only
[Gemma host-gate variant](../native-one-hop-v1h-budget-swap2048/README.md) was
registered at `60b9fa3de6fdb6f0c49c7a51d7267067ed817281` before inference.
Only `host_gates.swap_used_mib_max` changes, 1024 -> 2048 MiB. The original
registration, freeze, sources, contexts, model/runtime identities and limits
remain unchanged. The shared original freeze/model ledger prevents a second
attempt through either wrapper.

After the exact new command was presented, the owner replied **“I authorize it”**.
[authorization.json](authorization.json) binds that message, command, identities,
schedule and initially absent output. Its receipt recording time is
`2026-10-21T10:45:45.561644+00:00`; no independent user-message timestamp was
supplied. The command below was invoked exactly once:

```sh
.venv/bin/python tools/native_one_hop_v1h_swap2048.py run \
  --freeze artifacts/v1h-budget \
  --allow-inference \
  --out artifacts/issue83-v1h-budget-gemma4-swap2048-first
```

| Identity | Registered value |
|---|---|
| Parent experiment | `issue83-native-cpu-v1h-budget` |
| Parent source commit | `d485b9fcaf2de834d07788e8f15fc193b6cce664` |
| Parent registration SHA-256 | `beb4e84519294d9f6b870236573c3728f4ccc028465db73c0cb97ab36a414bc7` |
| Variant registration SHA-256 | `b70476e3ae2118c7a4e5fd15cc581a26697d6286afd5f31e123d693345200c05` |
| Original freeze archive SHA-256 | `61e2feb6883bcbcadfa8ace259b3e2f9ef2f2c8c3d771a0523ebbba7e8d295df` |
| Original freeze inventory SHA-256 | `d73ba8e301bd488b6fa60b75f3569f64d5d5ec981139a76fbecc66a1948613e8` |
| Original Rust binary SHA-256 | `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db` |
| Gemma model | `google/gemma-4-12B-it`, revision `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` |
| Gemma Q4_K_M SHA-256 | `6f25c570ce17ff06980ecb03edea67ce0e1bad39419a8e8091ba2298ae014431` |
| llama.cpp revision | `c0fd78626405c6d9b934efef0ec7291fcc20e3d6` |
| llama-server SHA-256 | `40188c617d6dc1d7f060587233a9eaf7d3929e1740db0e4650c31b74616be78a` |

All 76 original registered source hashes and 801 historical hashes matched.
Model/checkpoint, Q4, runtime source/executable, tokenizer/template and license
receipts were freshly rehashed before and after the run; the asset receipts are
byte-identical. No registered binary was rebuilt or substituted. All 38 scheduled
Gemma original and columnar prompts were recounted before loading with Python
3.12.14, transformers 5.20.1, tokenizers 0.23.3 and Jinja2 3.1.6. Exact prompt
bytes/token arrays matched registration; ten historical Gemma native parity
records reproduced offline. Largest columnar input is 14,703 tokens, so
14,703 + 512 = 15,215 < 16,384. Original overflow records remain preserved.

## Failures, controls and resources

| Condition | Scheduled | Attempted | Completed | Fatal runtime failures | Unattempted |
|---|---:|---:|---:|---:|---:|
| Oracle | 19 | 19 | 19 | 0 | 0 |
| BM25-v1 | 17 | 15 | 14 | 1 | 2 |

The fatal observation is `retrieval/smoke-eva-08`, the reverse website probe.
It fit the context but raised `TimeoutError: timed out`; its SSE/proposal have
zero response bytes. The empty-byte Rust rejection is retained as a raw
diagnostic, not classified as a model answer, unsupported operation or genuine
clarification. Primary semantic agreement fields remain null. The subsequent
`smoke-v1e-country-source-nb` and `smoke-v1e-country-paraphrase-en` observations
are explicitly unattempted, with null outcomes. No retry was made.

Including two sampling controls, there were 36 native requests and 35 completed
responses. Both sampling controls passed; native character controls gave three
expected acceptances and nine expected rejections. All 36 attempted native
template/token parities match the frozen requests, including documented Gemma
BOS restoration. All 35 terminal streams reconstruct the original output bytes.
All 33 completed semantic responses satisfy strict JSON/GBNF. Five oracle
candidates are Rust rejected: unclear relation, filter, multi-hop and both
reverse probes. All 14 completed BM25-v1 drafts are Rust accepted, including
abstentions disagreeing with references. Acceptance is not semantic correctness.
The runner's broader `controls_passed` and `smoke_passed` remain false.

Repeated oracle structured plans match, but full response/rationale bytes differ.
The registered protocol records this as diagnostic repeatability, not a fatal
gate. All 70 retained native proposal Rust previews were replayed against the
exact original binary and matched. No generated plan was executed as RDF.

The initial read-only variant preflight passed at 1877.44 MiB swap; the original
1024 MiB rejection is retained beside it. The host was Apple M1 Pro, 32 GiB,
arm64, ten logical CPUs, AC powered, with no competing model or thermal warning.
Only the owner-requested swap admission gate changed. CPU four threads, GPU zero,
concurrency one, temperature zero, seed seven, thinking off, 512 output tokens,
300-second deadlines and the 24 GiB process-tree RSS limit remained in force.
User processes were not interrupted and no OS resource limit was relaxed.

Gemma's sampled peak process-tree RSS is 16,557,424 KiB (15.790 GiB), across
25,835 samples with no sampler error. Qwen's retained peak is 11.223 GiB. Gemma
oracle observation p50/p95 is 166.55/176.51 seconds; BM25-v1 attempted-observation
p50/p95 is 174.69/304.17 seconds. The latter includes the fatal request and
parity/preview overhead; completed native-generation BM25-v1 p50/p95 is
171.73/264.45 seconds. Raw native prompt/decode timing is retained separately.
Different host/cache state, model/tokenization and swap admission confound causal
timing/RSS comparisons.

A post-run read-only receipt at 12:26 UTC records 3820.06 MiB swap, blocking both
admission gates, with no remaining model process. This is a post-run observation,
not a retroactive new stopping rule or evidence of readiness for another run.

## Separate oracle and BM25-v1 measurements

[comparison.md](comparison.md), [analysis.json](analysis.json) and the complete
[failure matrix](failure-matrix.md) retain all 72 model/condition observations,
36 pairs, native controls, full schedules and completed-only paired denominators.
The historical [Qwen evidence](../native-one-hop-v1h-budget-qwen35-evidence/README.md)
is reproduced exactly before comparison; its scores are not rewritten.

| Model / condition | Exposed-reference agreement | Unsupported classification | Clarification references | AI ambiguity audit clarification |
|---|---:|---:|---:|---:|
| Qwen oracle | 8/19 | 2/6 | 3/3 | 4/4 |
| Gemma oracle | 14/19 | 4/6 | 2/3 | 2/4 |
| Qwen BM25-v1, full completed | 10/17 | 4/6 | 3/3 | 4/4 |
| Gemma BM25-v1, completed | 11/14 | 6/6 | 2/3 | 2/4 |

On the exact same 14 completed BM25-v1 pairs, reference agreement is **8/14 Qwen
versus 11/14 Gemma**. This excludes no failure from the full schedule: one fatal
and two unattempted Gemma observations remain separate. Gemma's oracle forward
candidate-reference agreement is 8/8 versus Qwen's 3/8; completed BM25-v1 figures
are 3/4 versus Qwen's full 3/6, with differing coverage. Neither model produces a
reference-matching reverse plan: Qwen 0/2 in each condition; Gemma 0/2 oracle and
0/1 completed BM25-v1, with the other reverse outcome unmeasured.

Gemma's oracle filter and multi-hop responses guess a candidate for a forbidden
operation; Rust rejection is not model-origin unsupported classification. Their
BM25-v1 responses explicitly emit unsupported. Conversely, its unclear-relation
oracle guess and BM25-v1 unsupported response both miss genuine clarification.
Both source-label candidates match the original candidate reference while the
separate AI ambiguity audit calls for clarification among label predicates.
That unresolved disagreement explains why reference matches and ambiguity
handling must be reported separately. All independent human judgments stay null.

Source-table contradictions also differ from plan-reference agreement. Qwen's
oracle repeat pair and country smoke share one response falsely assigning 1004
to schema:Country/graph 1 and P1448; the actual binding is P17/graph 0, with
P1448 at 1003. BM25-v1 Qwen incorrectly claims supplied entity 100/Q134620 lacks
an ID, and its English country candidate calls 1004 P1448 and the object a
literal Finland despite matching all reference plan fields. These are five
observations but only three distinct response hashes. Gemma has no annotated
hard literal table mismatch in its completed responses; that bounded result does
not validate unrestricted rationale or missing source meanings. The last Qwen
country contradiction has an unattempted Gemma counterpart, not a measured fix.

Both models sometimes assign Finland or ordinary country/administrative meaning
without a supplied name, definition or identity bridge. BM25-v1 administrative
and reverse-administrative predicate tables are empty even though adjacent
packet triples remain: those triples do not authorize restoring numeric IDs.
Gemma's reverse-administrative rationale additionally calls multiple returned
resources unsupported although one-hop `values` projection allows them. This
supports guarding genuine clarification and supported operations against blanket
unsupported responses. Source-bound notes are coding-agent inspection tied to
exact raw excerpts/source values, not independent semantic review. Zero narrow
automatic rationale-rule matches is not evidence that all prose is correct.

## Reproduction and next research decision

[evidence.tar.gz](evidence.tar.gz) retains 1,602 hash-bound original files:
unchanged outer/inner run inventories, freeze and original archive, raw prompts,
requests, SSE/proposals, controls, Rust previews, native timing/resources, exact
authorization, shared ledger, original/variant preflights, post-run identity and
replay receipts, source annotations and packaging/analysis sources. No model
weights or executable binaries are packaged.
[evidence-files.json](evidence-files.json) binds archive SHA-256
`02bc0e64418eb3d0bdf71825940e89b7f956aefc11b4410dd2b66a5a81abbde5`
and every member. Archived filesystem timing metadata preserves observations
separately from normalized archive timestamps.

Reproduce into a fresh output directory using pinned project dependencies:

```sh
.venv/bin/python tools/compare_v1h_models.py --out artifacts/qwen-gemma-reproduced
.venv/bin/python -m unittest discover -s tools -p test_compare_v1h_models.py -v
```

The analyzer starts no subprocesses, loads no models and executes no RDF queries.
It verifies archived source/registration/auth identities, all 38 scheduled token
budgets, native parity/SSE, complete denominators and source-bound annotations.
Tests reject changed archives, rebound frozen prompt sources and forged annotation
witnesses, and preserve null runtime/missing semantics. See the final validation
receipt and logs in this directory for the complete model-free pipeline.

The [status-rule-precedence recommendation](status-rule-precedence-proposal.md)
is a proposal for a minimal future separately registered and authorized experiment.
No new status-rule prompt, configuration, registration or run is implemented here.
