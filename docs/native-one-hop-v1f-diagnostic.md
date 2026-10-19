# V1f-diagnostic: complete independent semantic observation for #83

This successor to merged PR #87 establishes diagnostic capability only. Decision:
**INCONCLUSIVE_REVISE**, never semantic GO. Keep #83 open. No inference is
authorized by this protocol or PR. Historical experiments, scores, thresholds,
hashes, decisions and evidence remain unchanged.

V1e retained 17 native responses but strict controls stopped both models before
the complete smoke. Qwen clarified the explicit-label request; Gemma guessed a
country relation for ambiguous location wording and Rust rejected it. V1f changes
only observation scheduling and reporting, with the same source-language v1e
presentation, original source, prompt, GBNF, model/runtime pins and Rust validator.
This is exposed regression evidence, not a pristine holdout or causal ablation.

## Frozen accounting and gates

Each pinned model has **36 independent diagnostic observations**: two original
Norwegian country repetitions in oracle, then 11 controls and six smoke cases in
oracle and independently in frozen whole-question BM25-v1 retrieval. The six are
eva-01, eva-02, eva-07, eva-08 and the two v1e country probes. No missing BM25 IDs
are restored. Neighborhood-v2 is not registered or run; it requires a separate
protocol and packet binding. The original full 30-case strict stages remain
separately unattempted, with their original 18/6/6 denominators. Diagnostic mode
rejects `--evaluate`. Two native sampling requests precede observations: **38
maximum requests per model**, one serial attempt each, no retries.

Semantic mismatches, model-origin false candidates and known individual Rust draft
rejections are recorded and continuation observes the next independent case.
No failed safety control becomes a pass: run-level `controls_passed` and
`smoke_passed` remain false, semantic GO remains false, and the decision remains
INCONCLUSIVE_REVISE even if all references happen to match. Repetition mismatch
is a recorded diagnostic failure; prompt/request identity mismatch is fatal.
Existing v1c/v1d/v1e strict gated paths still stop at their first failed gate.

Authorization, asset/license/source/binary/packet integrity, trusted catalog
preflight, official GBNF accept/reject and native sampling controls, native
template/token parity, operation deadlines, context/output/stream limits, process
failures, cancellation, missing RSS monitoring, RSS ceiling and private-canary
violations remain fatal. A constrained output violating GBNF is a runtime-integrity
failure, not a semantic failure to bypass. Only recognized Rust draft errors may
continue, after a separate trusted abstention validates the same host catalog.
Unknown Rust failures or abnormal process exits stop. Source and binary hashes
are checked before and after each diagnostic observation. Host preflight runs
fresh after asset hashing, before loading; concurrent process-tree RSS is checked
between observations. A stopped run preserves all missing cases as unattempted.

## Records and independent review

Every model/condition/case has its own record: raw text, exact base64 bytes and
SHA-256, model-origin status, JSON and strict-contract validity, native GBNF
validity, exact Rust stdout/stderr/exit, start/predicate/graph/direction/output
(projection), original exact exposed-reference status/field agreement, ambiguity
and source sufficiency audit, elapsed time, native timings/tokens and resource
snapshots. Rust acceptance and reference agreement are separate; rejection is
never reclassified as model clarification. Fatal, rejected, semantic mismatch and
unattempted states are distinct. Attempted-generation counts require an actual
completion request; template failures before that request do not count. Raw byte replay uses Rust directly, never repairs
or reserializes a model draft. Resource snapshots are sampled process-tree run
peaks to date, not per-case peaks; sampling may miss peaks or double-count pages.
OS caches remain intact and no disk-cold or human timing claim is made.

The report's blind review package contains only neutral review IDs, questions,
original authorized RDF, graph-qualified catalog identities and original source
vocabulary. It omits model outputs/names, expected statuses/plans/directions,
reference scores and investigator conclusions. Coordinator mapping and the
AI-authored source sufficiency audit are separate. Reviewers should independently
identify the requested relationship, ambiguities, evidence sufficiency and missing
vocabulary, citing exact graph-qualified statements. Record human findings only
when a real reviewer supplies them; blank fields mean pending, not acceptance.
Do not open the coordinator mapping or investigator audit before blind review.

The separate preregistered audit flags Campus collisions, “every stored label”,
general location wording and opaque P17/P131/P856 meanings. All predicate texts
are empty. Local names such as containedInPlace are not definitions. There is no
source identity link between graph-0 Q33 and graph-1 Finland. Review cannot change
historical scores; disagreements become separately versioned evidence. AI analysis
is not independent validation. Neither audit nor reference fixtures enter prompts.

## Freeze and separately authorized operator run

The committed report binds the model-free packet freeze, source copies, protocol,
audit, original history inventory and pending review package before inference.
Its source commit and checksums can be verified without model assets. Future
operators must use the exact registered source and binary, or preregister a new
freeze; never reseal an old run to accept changed inputs. A binary rebuilt on a
different toolchain/host may require a new preregistration. Preserve the existing
official Qwen3.5-9B/Gemma 4 12B Q4_K_M/checkpoint/tokenizer/license/llama.cpp pins,
CPU four threads, zero GPU layers, concurrency one, seed 7, temperature zero,
thinking off, 16,384 context, 512 output, 300-second deadlines and no retries.

Only **separate explicit operator authorization** permits either run below.
`--allow-inference` is still required and CI is rejected. Each run checks assets,
then fresh M1 Pro/32 GiB hardware/load/CPU/memory/disk/swap/AC/thermal preflight
before model loading. A failed gate is a retained blocker: no automatic retry,
downloads, alternate models, cache eviction or interruption of user processes.

```sh
cargo build --workspace --locked --offline
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic freeze --out artifacts/issue83-v1f/freeze
# Freeze/source/checksums must be committed and preregistered before inference.
# AFTER separate explicit operator authorization, using that exact freeze:
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic run --freeze artifacts/issue83-v1f/freeze --model qwen35 --allow-inference --out artifacts/issue83-v1f/qwen35
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic run --freeze artifacts/issue83-v1f/freeze --model gemma4 --allow-inference --out artifacts/issue83-v1f/gemma4
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic replay --freeze artifacts/issue83-v1f/freeze --run artifacts/issue83-v1f/qwen35
```

Archive every attempt, including failures, with immutable sources, raw SSE,
prompts/requests/token identities, GBNF, Rust results, timings and host/RSS receipts.
Completion means observation coverage only. There is no model-generated RDF query
execution, #75 integration, Find default change, sealed holdout access, semantic
readiness claim, issue closure or automatic merge.
