# Operator execution registration for predicate-diagnostics-v1

Refs #83, after merged #103. **INCONCLUSIVE_REVISE**. #83 stays open; #75
integration stays disabled. Independent human semantic review is deferred.
No inference has been performed or authorized by this change. Previous Qwen
experiment authorizations do not transfer.

This append-only successor binds the final runner, tests, documentation and
unchanged frozen scorer to a committed source revision. It retains #103's
original registration, archive, references, prompts, schedule and historical
artifacts byte for byte. The exact archive is reused; do not prepare or register
the original experiment again. Execution registration is model-free and
refuses replacement. The new registration binds every prompt/context/grammar,
packet identity, tokenizer prompt/token digest, Rust binary and bridge, runtime
and model identity, original host limits and fixed destinations.

Model-free preparation, from the repository root with existing pinned assets:

```sh
.venv/bin/python tools/predicate_diagnostics_native.py unpack
.venv/bin/python tools/predicate_diagnostics_native.py register
.venv/bin/python tools/predicate_diagnostics_native.py verify
.venv/bin/python -m unittest discover -s tools -p 'test_predicate*.py' -v
.venv/bin/python experiments/predicate-diagnostics-v1/verify.py
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

The runner source/test/documentation must be committed before the new
registration; the registration must also be committed before execution. The
registration is evidence of preparation, never inference authorization.

**STOP: the following exact registered command requires separate explicit
operator authorization naming the reviewed source revision, new registration
hash, original archive hash, 126-request cap and fresh destination.**

```sh
.venv/bin/python tools/predicate_diagnostics_native.py run --allow-inference
```

It always uses `artifacts/predicate-diagnostics-v1-execution-v1/freeze` and
`artifacts/predicate-diagnostics-v1-execution-v1/run`. There are no model, prompt,
limit, seed, arm, output or retry overrides. An exclusive global native lock
enforces concurrency one. The exclusive
`artifacts/predicate-diagnostics-v1-execution-v1/attempt.json` ledger consumes
this registration before asset admission or model loading. A blocked or failed
attempt cannot be resumed or retried; further work requires a new reviewed
append-only registration and separate authorization.

One CPU-only Qwen3.5-9B runtime processes exactly the frozen order: two sampling
controls, two identical explicit construction repeats, 60 construction probes,
then 31 metadata pairs (62 requests). Native template/token-array parity runs
fresh for every exact message before its completion. Pre-load token recount,
12 native grammar controls, fresh hardware/resource admission, 1024 MiB swap
limit, 24 GiB sampled process-tree RSS limit, four threads, zero GPU layers,
16384 context, 512 output reserve, strict input-plus-reserve fit, 300-second
deadlines and zero retries are inherited unchanged. Missing monitor samples,
bad parity, grammar, source/packet, host, runtime, private-canary or unexpected
Rust failures stop every remaining request. Ordinary reference disagreements
and recognized strict Rust draft rejections remain observations.

The runner retains original response bytes (file, base64 and SHA256), original
SSE, requests, prompt/token parity, native grammar, strict Rust receipts, model
status, five plan fields, latency and sampled resources. Failed/partial and
unattempted requests stay in the full 126-request report with null missing
semantic outcomes. Raw measurements remain separate from completed outcomes.
The unchanged scorer keeps construction groups and metadata paired deltas
independent, including all scheduled and paired-completed denominators. Source
audit, missing meanings and original source/rationale text remain available for
deferred review; no automated semantic approval is claimed.

All ten known reverse empty-path compiler incompatibilities remain in the
60-construction denominator: explicit-003, 006, 013, 020, 028, 035, 038, 042,
049 and 056. Field agreement, model-origin status and compiler compatibility
are independent. No reference is rewritten, no abstention substituted and no
Rust check relaxed. No generated RDF query can execute: the only model-output
consumer is the unchanged preview bridge (sampling uses unchanged strict CLI
preview). Holdout access and #75 remain disabled.

After a separately authorized attempt, model-free byte replay is:

```sh
.venv/bin/python tools/predicate_diagnostics_native.py replay
```

It checks retained checksums and registration identity, feeds original bytes to
the unchanged Rust preview, and reproduces the independent score. Engineering
tests use synthetic outputs; they establish neither model performance nor human
semantic correctness. Decision remains **INCONCLUSIVE_REVISE**.
