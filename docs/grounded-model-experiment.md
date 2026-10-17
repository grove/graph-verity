# Grounded local model experiment, issue48-v1

This opt-in experiment compares the exact official post-trained
[Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) and instruction-tuned
[Gemma 4 12B](https://huggingface.co/google/gemma-4-12B-it).
The [configuration](../configs/grounded-models-v1.json) pins immutable upstream
commits, every native file's SHA-256 and size, the actual tokenizer/config and
official Jinja templates, runtime archive, shared prompt/grammar, and budgets.
Native hashes in LFS metadata are expected identities; preparation independently
hashes the complete downloaded bytes. Legal sources are archived in the
[report](../reports/issue-48-grounded-models/README.md) before weight acquisition.
Gemma links to Google's Apache 2.0 page instead of shipping a repository LICENSE;
the original HTML and extracted complete terms are retained.

This protocol is frozen before any model inference. It does not change the
formal Phase 0 gates, approve a product integration, or evaluate the sealed
holdout. Ordinary CI uses model-free tests and saved-proposal Rust replay only.
No existing Qwen2.5 configuration, raw report, benchmark or reference is changed.

## Locked task and exploratory continuation criteria

Both candidates propose the same version 1 `ParserResponse` typed RDF plan.
The historical GBNF remains the shared contract; its schema is the Rust
`parser_output` contract. The grammar is exercised with the actual modern
runtime validator, rather than assuming b5046 compatibility. Official model
templates differ and are explicitly selected from the pinned native repositories;
both receive `enable_thinking=false`. Model-produced reasoning is not stripped or
repaired into a valid answer. Any unexpected reasoning/terminators remain raw
bytes and count as invalid output. No images, audio, video, projector, tool,
remote inference service, or automatic product endpoint is used.

Hardware is the owner's Apple M1 Pro, 32 GiB RAM, four prompt and generation CPU
threads, zero GPU layers. Build disables Metal, Accelerate and BLAS. Context is
16,384 tokens, output at most 4,096 tokens, seed 7, greedy temperature zero,
prompt caching enabled, 300-second startup/request deadline. These budgets and
the new runtime are **not** an equal-configuration comparison with Qwen2.5-1.5B.
Both native checkpoints are converted to text-only F16 GGUF and then Q4_K_M with
the same pinned converter/quantizer. Their receipts separately record commands,
environment, executable hashes, F16/Q4 hashes and disk sizes. The temporary F16
file is removed after its full hash is recorded and Q4 quantization succeeds;
native weights, Q4 weights and all receipts remain. A different
precision, model, runtime, thinking mode or Metal run requires a new variant.

Each stage has the existing 30 paired public adversarial probes: 15 source
ontology and 15 Schema.org transfer cases, all Norwegian, with 24 supported and
six expected abstentions. Families retain their original counts. References
are public, AI-authored, correlated across ontologies and not expert gold.
There is no independent language comparison or extra independent sample count.
Public development inference is optional and omitted from this first scored
configuration; these questions already informed the historical experiments.

1. **Oracle stage:** reuse the historical authorized gold-ID vocabulary selector,
   with at most four labels per ID. References supply only vocabulary membership;
   never plans, answers, directions, joins, operators, thresholds or status.
2. **Retrieval stage:** query actual Find/BM25 with the original whole question,
   authorized scope and each of entity/predicate/class, cap ten hits per role.
   Merge returned IDs deterministically, apply the same label/profile cap as
   stage 1, and retain all requests, candidate scores, observed labels, mappings,
   index/ranking revision and graph provenance. No gold reaches this selector.
   Gold-ID coverage is calculated **only afterward**, separately from semantic
   model errors. Empty retrieval stays empty. Both models use identical frozen
   context bytes. Synthetic graph discovery provenance binds the actual public
   source hash and Apache-2.0 license; it does not claim an external source.

The fixed non-scored protocol runs actual grammar positive/negative controls
(all response statuses, missing/prohibited fields, malformed JSON, raw SPARQL,
truncation and trailing terminators), native/GGUF tokenizer and official-template
byte/token parity, two identical Oslo smoke generations for a deterministic
identity check, one unconstrained/constrained conflict pair,
and one malicious RDF-label/message-delimiter control with independent Rust
replay. Controls may reveal incompatibility; they do not authorize tuning,
retries or scored-output repair. Failed control/startup attempts are retained.
Only one scored pass per model and stage is permitted by this protocol. A
timeout stops that server; every remaining case receives a backend error, with
no retries, restart-based repair or overlapping generation.

Predeclared exploratory **go for further study only** requires **both stages**
individually to achieve at least **18/24 strict complete exact RDF answer sets**,
at least **4/6 correct model-origin abstention statuses**, zero observed scope,
canary or non-read-only execution violations, warm p95 at most **120 seconds**,
and sampled peak RSS at most **24 GiB**. Incomplete controls/runtime/resources
yield **revise** with explicit blockers; a complete run missing criteria yields
**reject for further study**. These are descriptive screening criteria, not
production reliability or new formal Phase 0 approval thresholds.

## Reproduction

Use Python 3.12, the repository's pinned Rust toolchain, CMake and a C++ compiler.
Allow space for ~43 GB native weights, F16 intermediate GGUFs, Q4 GGUFs and logs.
Keep historical assets intact. No model download or heavyweight inference belongs
in GitHub CI. From the repository root:

```sh
.venv/bin/python -m venv artifacts/issue-48/converter-py312
artifacts/issue-48/converter-py312/bin/python -m pip install -r tools/grounded-models-requirements.txt
.venv/bin/python tools/grounded_models.py acquire
cargo build --locked -p verity_cli
.venv/bin/python tools/grounded_models.py prepare --model qwen35
.venv/bin/python tools/grounded_models.py prepare --model gemma4
# Freeze once, before controls or scored inference. Never overwrite an existing attempt.
.venv/bin/python tools/grounded_models.py freeze --out artifacts/issue-48/new-freeze
.venv/bin/python tools/grounded_models.py run --model qwen35 --freeze artifacts/issue-48/new-freeze --out artifacts/issue-48/new-qwen35
.venv/bin/python tools/grounded_models.py run --model gemma4 --freeze artifacts/issue-48/new-freeze --out artifacts/issue-48/new-gemma4
.venv/bin/python tools/grounded_models.py verify --freeze artifacts/issue-48/new-freeze --run artifacts/issue-48/new-qwen35 --out artifacts/issue-48/qwen35-metrics.json
.venv/bin/python tools/grounded_models.py verify --freeze artifacts/issue-48/new-freeze --run artifacts/issue-48/new-gemma4 --out artifacts/issue-48/gemma4-metrics.json
.venv/bin/python tools/grounded_models.py replay --freeze artifacts/issue-48/new-freeze --run artifacts/issue-48/new-qwen35 --out artifacts/issue-48/qwen35-replay
```

`acquire` is the only online command. `prepare` verifies native bytes and the
runtime source archive, builds locally, converts and quantizes without inference.
`freeze` creates exact authorized requests and both contexts before model access;
`run` rejects changed inputs, binary, native weights or prepared assets. Output
directories are new for every attempt. An exclusive asset-side marker also
prevents a second inference attempt for the same model and frozen setup.
Frozen protocol hashes include the actual
Python/Rust source, lockfile, schema, graph, policy and public benchmark bytes;
base Git identity alone is not a claim of a pristine checkout.

## Scoring, safety and limitations

Rust's existing offline evaluator independently decodes, authorizes, validates,
compiles and executes only typed read-only plans against the same snapshot/scope.
Raw model text is archived before validation, including incomplete or malicious
output. Reports separate contract validity, grammar/truncation/backend failures,
validator rejection, model abstention, strict complete named RDF binding sets,
the separately labeled positional-equivalence diagnostic, valid but misleading
candidates, wrong executable answers, and variable-sensitive plan-component
agreement. Supported denominators keep abstentions, rejections and exceptions.
Deterministic preflight/confirmation is never a correct model abstention.

The independent retained-byte audit checks scope/snapshot/graph evidence, private
and comment canaries and SELECT-only execution; raw query/tool markers are
diagnostics, not proof of an executed tool call. Output IR cannot express SERVICE,
updates, arbitrary SPARQL, tools or closed-world NOT EXISTS. Zero observed safety
violations on this small public corpus establishes no general safety claim.

Metrics retain exact denominators, descriptive Wilson intervals, per-family and
per-ontology results, individual component agreement and retrieval misses. Warm
p50/p95/p99 and end-to-end include Rust catalog/validation/query/evidence and
generation; startup and first answer are separate process-cold measurements.
OS page cache is not evicted. Cold first-smoke time includes startup, grammar
checks and native/template parity checks; scored cases follow the controls in
the same warm process. Completion receives the exact tokenized template with no
automatic extra BOS. Raw runtime timings and prompt/output token counts
disclose throughput and prefix-cache reuse. RSS sampling includes descendants
every 200 ms and may miss spikes or double-count shared pages. Memory/latency,
contract syntax, semantic agreement and containment are distinct conclusions.

The historical [v1/compact-v2 comparison](../reports/issue-32-compact-ab/README.md)
had 0/24 complete exact supported answers and 0/6 correct model abstentions for
each route; invalid contracts fell from 8/30 to 2/30 without executed v2 plans.
It is a historical comparator, not a controlled equal-configuration A/B here.
Results cannot satisfy the missing independent split-integrity/expert review or
establish population accuracy. A promising result only supports proposing
model-generated drafts under a **separate explicitly approved integration issue**
and human false-confidence evaluation. [Confirmed Ask](confirmed-ask.md) stays
deterministic and model-free by default; the [Phase 0 decision](phase-0-decision.md)
and sealed holdout boundaries remain in force.
