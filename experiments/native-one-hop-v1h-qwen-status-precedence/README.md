# Qwen status precedence preregistration — INCONCLUSIVE_REVISE

Refs #83; builds on merged #96. **No inference is authorized or performed.**
Keep #83 open, #75 integration disabled and independent human review deferred.
All 36 semantic observations and both native sampling controls remain unattempted.

The sole factor is the order and explicit precedence of the existing status
rules: forbidden operation → unsupported before clarification or a partial
candidate; otherwise genuine ambiguity or missing authorized numeric vocabulary
→ needs_clarification; otherwise a fully supported one-hop interpretation →
candidate under the original numeric-ID, graph, scope and direction requirements.
[prompt.diff](prompt.diff) is the exact diff from the original system prompt.
The missing-vocabulary sentence resolves the existing overlap with “requests
outside the tables”; it adds no operation, definition, example or answer.

The new prompt retains every other system-contract line verbatim, including
direction wording, untrusted-source handling, identity/alias ambiguity, source
meaning limits, rationale restrictions and zero execution authority. Original
Qwen v1h contexts, source information, columnar packets, BM25-v1 membership,
numeric tables, GBNF, operator fixtures and schedule are bound byte for byte.
No source meaning, inverse wording, predicate definition or gold input is added.
Missing numeric vocabulary is never repaired. Supported multi-value one-hop
results continue to use the unchanged values projection.

The inherited pinned Qwen3.5-9B/Q4_K_M, llama.cpp, binary, tokenizer/template,
dependencies and offline runtime are unchanged: 16,384 context, 512-token reserve,
four CPU threads, zero GPU layers, concurrency one, seed 7, temperature zero,
thinking off, 300-second deadlines and 24 GiB sampled RSS ceiling. Qwen retains
the original **1024 MiB swap admission gate**; the Gemma 2048 variant is excluded.
A blocked host must wait. No process interruption or automatic model fallback.

## Frozen design and evaluation

The separate append-only registration/freeze binds committed sources, prompt
diff, original registration and Qwen evidence archive, exact message/token bytes,
token arrays, section accounting, runtime identities and a fresh output path.
All 38 prompts are recounted with the pinned local tokenizer before registration;
the original and columnar variants are retained. Each scheduled columnar prompt
must satisfy input + 512 < 16,384. Sampling-control prompts are unchanged. Fresh
native template/token parity is still required before every future completion.
The pinned recount adds exactly 30 input tokens to each semantic prompt and zero
to either sampling control. Largest columnar input is **14,049**, or **14,561**
with the reserve; largest original input is **18,956** and still overflows.

Exactly two sampling controls and the original 36 semantic observations run in
the original order: 19 oracle (including two correlated repeats), 17 BM25-v1.
Maximum 38 requests, no retries. A separate freeze/model ledger prevents a second
attempt. Known semantic failures remain observations; integrity, authorization,
private-canary, runtime and resource failures stop the remaining schedule.
Original bytes reach Rust preview only; no generated RDF query is executed.

Primary evaluation, separately for oracle and BM25-v1:

- Improve model-origin unsupported on the same six forbidden-operation probes
  (`private_scope`, `write`, `negation`, `count`, `filter`, `multi_hop`) relative to
  **2/6 oracle and 4/6 BM25-v1**. Rust rejection is not unsupported classification.
- Preserve **all three genuine clarification-reference matches** in each
  condition (`ambiguous_start`, `unclear_relation`, `absent_start`). Require the
  model to emit clarification; a rejected candidate cannot count as one.
- List every unsupported/clarification on candidate references and every lost
  baseline valid candidate by identity. Separate this from the unchanged
  four-case AI ambiguity audit: `source_label` retains its original candidate
  reference despite the separate ambiguity finding. No reference is rewritten.

Report all five candidate fields (start, predicate, graph, direction, projection),
forward and reverse failures separately, including abstentions. Report exact
source-table/rationale contradiction witnesses independently of plan agreement:
raw response excerpt/hash, context/source path, supplied value and asserted value.
In particular, do not relabel a source-contradicting rationale as correct because
the candidate's fields match. Narrow automatic English assertion checks do not
replace inspection of every retained response. Preserve original references,
source sufficiency limits and all null independent human judgments.

Use paired completed identities alongside full scheduled denominators, never a
completed-only rate that hides failures, partial outputs or unattempted cases.
Retain native controls, raw bytes/SSE, Rust outcomes, canaries, timing and sampled
process-tree RSS. No exact-answer accuracy, semantic GO or model ranking follows.
Even a future complete/improved run retains decision **INCONCLUSIVE_REVISE**.

## Model-free reproduction

Source must be committed before freeze/registration. Use fresh destinations;
never extract over an existing directory.

```sh
.venv/bin/python tools/native_one_hop_v1h_status_precedence.py freeze \
  --out artifacts/v1h-qwen-status-precedence
.venv/bin/python tools/native_one_hop_v1h_status_precedence.py register \
  --freeze artifacts/v1h-qwen-status-precedence
.venv/bin/python tools/native_one_hop_v1h_status_precedence.py verify \
  --freeze artifacts/v1h-qwen-status-precedence
.venv/bin/python tools/native_one_hop_v1h_status_precedence.py budget \
  --freeze artifacts/v1h-qwen-status-precedence \
  --out artifacts/v1h-qwen-status-precedence-recount
```

To restore instead of build: create a fresh `artifacts/v1h-qwen-status-precedence`
and extract this directory's committed `freeze.tar.gz` into it, then verify.
Portable regression tests inspect retained bytes and exercise Rust with synthetic
drafts, without model assets or weights. Full validation runs in an isolated
checkout to preserve the original registered binary. The validation receipts
and logs describe the exact tested commit and later receipt-only additions.

## Proposed Qwen command — requires fresh explicit authorization

After review of this concrete registration, request fresh authorization naming
this revision, Qwen, the 38-request schedule and this exact fresh output path:

```sh
.venv/bin/python tools/native_one_hop_v1h_status_precedence.py run \
  --freeze artifacts/v1h-qwen-status-precedence --model qwen35 \
  --allow-inference --out artifacts/issue83-v1h-qwen-status-precedence-first
```

This command is a proposal, not execution permission. No earlier Qwen/Gemma
authorization transfers. No inference, host-readiness claim or merge is included
in this PR. Full pinned asset verification, offline recount, native grammar
controls and a fresh <=60-second original host gate must pass before loading.

Limitations: the diagnostic is small, exposed, AI-authored and includes correlated
repeats. Its reference and ambiguity audits are not independent human truth.
Status wording may affect supported candidates or clarification despite unchanged
inputs; tests establish contract/source preservation, not future model behavior.
Direction failures, missing vocabulary and opaque source meaning are unresolved.
Historical baseline/cache/host differences prevent statistical, causal or model
superiority claims. RSS sampling can miss peaks and double-count shared pages.
