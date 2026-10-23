# Observable Ask Alpha successor — INCONCLUSIVE_REVISE

This is a separate, unexecuted registration, `ask-alpha-preview-v1-observable-r2`.
The consumed [original registration](../ask-alpha-v1/registration.json), its
[trial](../ask-alpha-v1/trial.md), runner, ledger and
[forensic evidence](../../experiments/ask-alpha-v1-interruption-evidence/README.md)
remain unchanged. The original `KeyboardInterrupt` origin remains unknown.
The previous owner's execution authorization does not transfer.

The [machine-readable equivalence proof](equivalence.json) compares all 64
scheduled identities in order and all 199 non-metadata archive members byte for
byte. It also binds all 203 original source inputs unchanged, including the RDF
snapshot, authorized numeric/graph vocabulary, full retrieval packets, five
licensed property descriptions, preview validator and scoring references. It
compares questions/languages, contexts, messages, grammar, exact rendered prompt
bytes, full token arrays/counts, model/runtime identities and resource policies.
Only `freeze.json` and its manifest differ inside the freeze: new version, source
commit and three additional runner/registration/test source hashes. The report
lists every changed registration field and every unchanged per-request identity.
Canonical tar/gzip metadata permits deterministic archive reproduction.

The original design applies in full: 60 questions (30 nb / 30 en), the same two
sampling controls and two construction repeats, original round-robin order,
Qwen3.5-9B revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, Q4_K_M
SHA-256 `fa502d3cb95fab7a6a563b9e057d94e6bae5ca737f056a4ffd05a9c25232d951`,
llama.cpp `c0fd78626405c6d9b934efef0ec7291fcc20e3d6` and CPU server SHA-256
`40188c617d6dc1d7f060587233a9eaf7d3929e1740db0e4650c31b74616be78a`.
The pinned tokenizer/template, prompts, grammar, Rust preview contract and scoring
are unchanged. No source repairs, extra model-visible metadata or query changes.
Maximum 64 completion requests, zero retries, preview only, no generated RDF
execution, no #75 integration and #83 stays open. Human semantic review is pending.

## Durability and failure behavior

The versioned runner creates `stages.jsonl` exclusively as its invocation claim
before registration verification. Its existence also consumes the successor: an
early verification or lock failure cannot permit another invocation. It then
verifies the committed registration, acquires the same exclusive global native
lock, checks fresh output/ledger paths and exclusively creates and fsyncs
`attempt.json` **before any assets, tokenizer, host admission or model loading**.
Never delete or reuse any of these paths. No resume command exists.

Each entered/completed/failed stage has a UTC timestamp, monotonic elapsed time,
stage name, relevant registration/model/request identity and failure class.
Entries are flushed and fsynced before blocking work. There are at most 512 events
for this fixed schedule. Directory creation and ledger/journal creation sync their
parent directories. JSON diagnostics use a flushed/fsynced temporary file and
atomic replacement, followed by directory fsync. Journal and JSON receipts use
owner-only permissions. No prompt or raw model stream is added to the stage log;
original raw-evidence retention remains in the same isolated run directory.

Stages cover registration, global lock, ledger, output initialization, assets,
tokenizer recount, grammar controls, fresh host admission, RSS monitor, runtime
construction, model startup, every scheduled observation and actual completion
transport entry (first and subsequent requests), shutdown and finalization.
The dispatch boundary is entry to the inherited completion transport, after its
existing attempt counter increments; it does not prove server receipt or response.

Caught `BaseException`, including `KeyboardInterrupt` and `SystemExit`, records
exact exception class/module, message and available traceback without locals,
failure-time last entered/completed stages, startup confirmation, measured native
attempt/completion/byte counters, remaining request identities and finalization
status. Counters remain null until available from the runtime. Startup confirmation
means health admission returned successfully; false does not prove no process was
started. Partial original receipts/streams survive. Cleanup errors are secondary;
the original exception is re-raised. Finalization-only failures also fail the run.

The standalone `diagnostics.json` survives failure before run-directory creation.
`failure_last_*` fields preserve the original failure position while `last_*`
fields can advance through cleanup. Journal transitions remain the authoritative
final cursor if a final receipt write is interrupted. A finalization failure may
leave missing scoring/checksum receipts; no successful-evidence claim follows.
The journal is intentionally outside the run payload checksum manifest and is
never rewritten. JSON diagnostics follow the original evidence-retention scope.

All host/resource gates stay unchanged: pinned M1 Pro/32 GiB arm64, AC/thermal
checks, four CPU threads, zero GPU layers, one slot, ≤60-second host receipt;
load/CPU ≤0.75, swap ≤1,024 MiB, free memory ≥40%, disk ≥32 GiB and competing CPU
≤150%; input + 512 <16,384, 300-second startup/completion deadlines,
16,384-byte drafts, 2 MiB streams, 0.2-second sampled RSS, ≤24 GiB RSS.

## Future handoff — do not execute under this PR's preparation authority

Model-free verification on the pinned host:

```sh
.venv/bin/python tools/ask_alpha_trial_observable_r2.py verify
.venv/bin/python tools/ask_alpha_register_observable_r2.py verify
```

If necessary, `unpack` restores only this successor archive into its fresh freeze
destination. Do not rerun `prepare`. The exact separately authorized future command
is fixed in the registration (destinations are bound constants, not flags):

```sh
.venv/bin/python tools/ask_alpha_trial_observable_r2.py run --allow-inference
```

- Freeze: `artifacts/ask-alpha-preview-v1-observable-r2/freeze`.
- Output: `artifacts/ask-alpha-preview-v1-observable-r2/run`.
- Ledger: `artifacts/ask-alpha-preview-v1-observable-r2/attempt.json`.
- Receipts: sibling `stages.jsonl` and `diagnostics.json`.

After review, request explicit owner authorization naming the reviewed PR URL and
exact reviewed head SHA, registration SHA-256
`3eab8a532fa45b81301df9d4fba2b50b8153433f44bd752d63d05cacd42ab98d`,
freeze archive SHA-256
`310216acbaeb34d15752b7452658a39a4eaa358c4456d451085770efb95fe516`,
the exact command above, pinned Qwen identity, maximum 64 completion requests,
original fresh host/resource gates, zero retries and preview-only execution.
The PR URL/head will be returned with the handoff; a later reviewer must use the
head actually reviewed. Opening this PR authorizes no inference, merge, issue
closure or independent-human-review claim.

## Known limits

These changes diagnose future failures; they cannot reconstruct the original
exception origin. Python cannot finalize receipts after SIGKILL, host/power loss,
filesystem failure or repeated interruption. Fsync/atomic replacement improve
ordinary interruption durability and do not promise hardware-level persistence.
An incomplete trailing JSONL record can be ignored after an uncatchable crash;
previous fsynced lines remain. Tracebacks omit locals and signal attribution.
RSS sampling retains its original missed-peak/shared-page limits. Added fsyncs
introduce small timing overhead. No native/model startup or inference is tested
or authorized here; semantic understanding and independent review stay unmeasured.
