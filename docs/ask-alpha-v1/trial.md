# Frozen next trial — not authorized, not executed

This registration is **new**. None of the consumed #83 ledgers/registrations is
reused. The [registration](registration.json) binds the [compressed freeze](freeze.tar.gz)
and reviewed source bytes. The archive includes exact contexts, messages,
grammars, schedule, tokenizer job, rendered templates, full token arrays/hashes,
operator-only references and input identities. No model output has been acquired.
The original v2 human review remains pending; this is the separately authorized
preparation of an **agent-reference automated** trial, with zero humans claimed.

## Fixed experiment

- One arm, existing `nl-ask-draft-v1` five-field generation. All 60 original frozen
  questions, 30 nb / 30 en; no oracle arm, prompt tuning, retries or model switch.
- Actual merged #82 question-only neighborhood retrieval as used in supervised
  Ask v2, including source usages and graph-qualified numeric aliases. Only five
  verified development-source Wikidata property definitions are added to matching
  authorized predicate rows; no reference plan, target ID, selected direction,
  answer key or operator reference is passed to a prompt. Original question text
  is unchanged. Full references stay in a distinct `operator/` archive directory.
- Existing direction-only/status-precedence system prompt, unchanged; source
  labels/definitions remain untrusted JSON data escaped through `safe_user`.
  The public source facts may contain answer values; that is disclosed source
  context, not a reference answer key. Missing vocabulary is not repaired.
- **64 completion requests maximum:** two fixed native sampling controls, two
  identical-prompt construction repeats, then 60 semantic cases, round robin by
  declared category in original per-category order. The two repeats are controls,
  not additional semantic cases or retries. This bounds completion time to at
  most 19,200 seconds plus loading, parity, host/source checks and scoring; any
  fatal failure stops earlier. There is no continuation command.
- Pinned Qwen3.5-9B revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`,
  Apache-2.0, existing Q4_K_M SHA-256
  `fa502d3cb95fab7a6a563b9e057d94e6bae5ca737f056a4ffd05a9c25232d951`.
  Existing llama.cpp revision `c0fd78626405c6d9b934efef0ec7291fcc20e3d6`,
  CPU-only llama-server SHA-256
  `40188c617d6dc1d7f060587233a9eaf7d3929e1740db0e4650c31b74616be78a`.
  Full identities, preparation receipts, tokenizer/template/environment and
  original asset licenses are retained in the freeze. No asset acquisition.
- Same M1 Pro / 32 GiB, arm64, CPU four threads, zero GPU layers, one slot,
  temperature 0, seed 7, thinking disabled, 16,384 context, 512-token output
  reserve; **input + 512 strictly below 16,384** for every request. No raw query
  generation, remote service or RDF execution command.

## Admission, stopping and retained outputs

The runner refuses CI and requires `--allow-inference` plus separate explicit owner
authorization. It verifies the committed registration, complete frozen/source
hashes and Rust binary; takes the existing exclusive native lock; and creates a
new exclusive ledger **before model loading**. A blocked/failed command consumes
this registration. An optional separate read-only host preflight does not consume
an attempt. Existing historical ledgers are never opened for writing.

Before loading: verify retained native/Q4/license/source identities, recount the
exact prompts with the pinned local tokenizer, run the existing 12 model-free
GBNF accept/reject controls, then require fresh (≤60 s) unchanged CPU/host admission:
load/CPU ≤0.75, swap ≤1,024 MiB, free memory ≥40%, disk ≥32 GiB, competing process
CPU ≤150%, correct hardware, AC power, no thermal/performance warning. Never
interrupt user processes or relax a gate to proceed.

Every generation requires fresh native template/token-array parity against the
sealed pre-load tokens. Before each semantic request, independently regenerate
and compare the complete authorized Rust packet, and pass a trusted source/catalog
preflight. Repeat prompts/completion-request bytes must match exactly. Enforce
300-second startup/completion bounds, 16,384-byte drafts, 2 MiB stream limit,
0.2-second sampled process-tree RSS monitor and ≤24 GiB sampled RSS. These inherit
the established runner's policy; sampling can miss peaks and double-count shared
pages. Do not change deadlines or treat partial JSON as terminal output.

Keep raw SSE and draft bytes, fragments, model-origin status, strict JSON and Rust
preview results, complete source inputs, prompt/token parity, latency, startup
and memory records for successes and failures. Each fatal integrity, transport,
timeout, resource or runtime error stops the schedule; ordinary wrong
interpretations remain observations. Remaining identities stay unattempted.
There are zero retries. Source/binary drift blocks the registration.

Scoring is model-free and preview-only. It reports all 60 scheduled cases and
completed subsets separately, with language/direction/category strata, unsupported
and clarification dispositions, five fields, wrong accepted plans, retrieval
misses, source-meaning insufficiency, and source-audit tasks for rationales.
There is no paired architecture result in this one-arm trial. A fatal failure
retains its logs, ledger, fragments, null semantic outcomes and full denominator.
The model's proposals never connect to Ask's approval/execution route.

## Exact future command and authorization request

After review, on the pinned operator host, verify the registration with:

```sh
.venv/bin/python tools/ask_alpha_trial.py verify
```

If the local freeze is absent, `unpack` restores this exact archive into the fixed
fresh destination; it does not generate prompts, tokenize or infer. The exact
registered future inference command is:

```sh
.venv/bin/python tools/ask_alpha_trial.py run --allow-inference
```

Fixed new destinations: `artifacts/ask-alpha-v1/run` and
`artifacts/ask-alpha-v1/attempt.json`. Do not run `prepare` again or reuse those
paths after an attempt. `prepare` has already frozen this version model-free.

**Authorization request to be made separately after PR review:** authorize one
invocation of the exact command above for the reviewed PR head, registration
SHA-256 and archive SHA-256 recorded in `validation.json`, maximum 64 completions,
under unchanged fresh admission/resource gates and zero retries, preview only.
This PR and this text grant no inference, execution, #75 integration, merge or
issue-closure authority. Do not treat elapsed time or preparation approval as
inference approval. `INCONCLUSIVE_REVISE` remains the decision.
