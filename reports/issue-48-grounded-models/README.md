# Issue #48: revise; the controlled comparison remains incomplete

**Do not integrate either model.** Both exact official checkpoints were downloaded,
fully SHA-256 verified, converted locally and attempted on the owner's Apple M1
Pro (32 GiB), four CPU threads, zero GPU layers. Qwen returned two scored
proposals before a 300-second timeout; Gemma timed out during its first smoke
completion. Severe host contention limits interpretation of timings. These are
real local CPU attempts, not model-free CI inference or a completed accuracy A/B.
The [machine-readable decision](decision.json) recommends **revise** under the
[preregistered protocol](../../docs/grounded-model-experiment.md). No model is
connected to Confirmed Ask or unattended Ask.

## What actually ran

| Configuration | Generation requests, including controls | Complete responses | Scored requests / complete proposals | Outcome |
|---|---:|---:|---:|---|
| Qwen3.5-9B, v1 | 8 | 7 | 3 / 2 | `gt` timed out; backend stopped, no generation retry |
| Gemma 4 12B, initial preflight | 0 | 0 | 0 / 0 | Adapter rejected the server's intentional BOS omission, before generation |
| Gemma 4 12B, v1b | 1 | 0 | 0 / 0 | Native prompt/token parity passed; first smoke request timed out, **69 candidate bytes retained** |

Qwen's four positive/six negative actual-runtime grammar probes, live
unconstrained/constrained conflict controls and malicious-label/Rust boundary
control completed. Its two identical smoke generations returned identical bytes.
The corrected Gemma adapter passed native template and tokenizer parity, but
its later live grammar-conflict/injection controls and scored stages were **not
reached**. Its partial JSON independently fails both the actual runtime grammar
validator and Rust's parser (`EOF ... column 69`). That saved-output check invokes
no inference.

The original failed Gemma preflight is retained. Pinned llama.cpp
[`common/chat.cpp:938`](https://github.com/ggml-org/llama.cpp/blob/c0fd78626405c6d9b934efef0ec7291fcc20e3d6/common/chat.cpp#L938)
removes a leading BOS because normal string-completion tokenization adds it.
Our explicit-token-array adapter must restore that verified native BOS. The v1b
revision accepts **only** this exact difference and still requires complete
native prompt-byte and token-ID equality. It also streams responses to retain
partial candidate bytes within the unchanged 300-second wall deadline. Qwen's
initial final-response-only timeout returned no body; unreceived text is not
reconstructed. Qwen was not rerun, and no Gemma scored output existed before the
adapter correction. All costs/failures remain in evidence.

All 330 model-facing/context/Find packet files are byte-identical between the
v1 and v1b freezes; only `freeze.json` (source/input identities) differs.
Weights, Q4_K_M precision, questions, contexts, contract/grammar, sampling,
thinking mode, budgets and numerical criteria stayed unchanged. Transport and
source revisions differ, so this is not an equal-configuration latency A/B.

## Outcomes and semantic limits

The shared corpus has 30 public AI-authored probes per stage: 15 synthetic source
ontology cases and 15 Schema.org adaptations, all Norwegian. Each stage has 24
supported cases and six expected abstentions. The paired ontologies are
correlated, not independent samples. No independent expert reviewed the gold,
no usability participants were recruited, and no sealed Ask holdout was accessed.

| Qwen configured pipeline stage | Model requests / returned proposals | Strict complete exact supported bindings | Positional diagnostic | Correct abstention statuses | Structural IR reference matches |
|---|---:|---:|---:|---:|---:|
| Oracle | 3 / 2 | 1/24 | 1/24 | 0/6 | 0/24 |
| Find/BM25 | 0 / 0 | 0/24 | 0/24 | 0/6 | 0/24 |

These denominators keep the stopped-backend failures in the configured task.
They are **not measured model semantic-accuracy estimates**: Qwen never reached
any abstention probe or transfer/retrieval generation. Oracle has one request
timeout plus 27 unattempted backend-error cases; retrieval has 30 unattempted
backend-error cases. Gemma has no scored cases and its semantic rates are null,
not fabricated 0/24 results. Machine metrics retain every case, family, ontology,
status/error, component diagnostic and raw-response hash where a scored report
exists. Wilson intervals are descriptive only; ordering/censoring, correlated
public AI references and tiny response counts prevent population claims.

Qwen's two returned proposals were valid JSON and contracts, independently
validated, scoped and executed read-only. **Neither establishes a faithful
interpretation:**

- `inverse`: for “Hvilken eier har Eksempel AS?”, it queried a forward edge
  between two variables and returned the company as `owner`, instead of binding
  the named company and retrieving its owner. This is a **valid, executable,
  wrong answer**, with no runtime semantic-correctness flag beyond the generic
  `interpretation_correctness: not_assessed` disclaimer.
- `two-hop`: its bindings match the frozen contracts `c1`/`c2`, but its plan
  replaces the named “Eksempel kommune” constant with an unrestricted
  `municipality` variable. The current snapshot masks the missing constraint.
  The entity/variable diagnostics disagree with the reference. This AI inspection
  is not expert adjudication; **exact current-snapshot bindings alone do not
  demonstrate faithful question interpretation**. The public gold was not changed.

Both original proposals, prompts, requests, compiled plans, bindings and evidence
are under `qwen35/oracle/adversarial/{inverse,two-hop}/` in the archive. The `gt`
request and timeout are retained alongside them. Gemma's exact incomplete output
is `gemma4-v1b/controls/smoke-0/proposal.txt`; its stream, canonicalization proof,
native reference tokens and independent rejection are retained too.

Question-only, scoped Find/BM25 with ten hits per entity/predicate/class role
misses a required reference ID in **4/24** supported frozen contexts: `contract`
for source `two-hop`/`distinct`, and `schema:subjectOf` for the paired transfer
cases. This is a **model-free retrieval coverage diagnostic**, not model inference
or an explanation of the unattempted retrieval-stage model outcomes. Selection
never uses gold IDs in that stage. The 86 public development questions were not
run in this configuration; no new development gold was authored.

## Resources and independently verified blockers

| Attempt | CPU server startup | First complete smoke answer, process cold | Attempted scored warm p50 / p95 / p99 | Sampled aggregate peak RSS |
|---|---:|---:|---:|---:|
| Qwen v1 | 96.997 s | 322.460 s | 83.074 / 300.624 / 300.624 s, **n=3 including timeout** | 6.879 GiB |
| Gemma initial preflight | 57.438 s | not reached | not applicable | 9.844 GiB |
| Gemma v1b | 58.683 s | timed out | not applicable | 8.577 GiB |

The configured request limit was 300 seconds; context/output budgets were
16,384/4,096 tokens, seed 7, greedy sampling, prompt caching on, thinking off.
Warm latency excludes cheap unattempted error wrappers while all failure cases
remain in task denominators. Qwen's cold first-smoke time includes startup,
grammar/native-tokenizer checks and the first generation. OS page cache was not
evicted; asset verification reads weights before startup. RSS is sampled every
200 ms across descendants, can miss spikes/double-count shared pages, and is not
a whole-system memory guarantee. Both models loaded; usable 32 GiB feasibility
for the complete task remains unresolved.

The retained read-only resource snapshot recorded load averages
**119.60 / 196.14 / 195.94 on 10 logical CPUs**, with **24,492.88 MiB swap used**.
A later snapshot still had **24,256.56 MiB swap used** and load
17.62 / 17.47 / 33.73. The host was not quiescent. Timings and timeouts cannot be
attributed to intrinsic model performance, and no speed ranking is justified.
The configured deadlines did fail under these observed operator conditions.
Native runtime timing/token counts are retained for every completed response;
Qwen's first/repeated smoke prediction rates were 1.56/6.83 tokens/s, with very
different prefix-cache reuse. Missing final counts remain unknown. Gemma's log
records 1,076 prompt tokens processed in 88.74 seconds before cancellation;
69 received bytes do not establish an output-token throughput.

The predeclared continuation bar required **both stages** to achieve at least
18/24 strict supported binding sets, 4/6 correct model-origin abstentions, zero
observed scope/private-canary/non-read-only execution violations, warm p95 at most
120 seconds and sampled peak RSS at most 24 GiB. Neither configuration completed
the required measurements. The decision is **revise**, not a rejection of either
model's intrinsic Norwegian capability. A future controlled run needs an explicit
new version/condition declaration; these attempts are not discarded or retried
as though unseen.

## Safety and boundaries

Independent Rust decoding, scope/snapshot/ID/type/operator validation and SELECT
compilation stayed mandatory. Both scored executions used the exact authorized
public graph/snapshot; the inverse answer was still wrong. No private negative
canary or non-read-only execution violation was observed in retained evidence.
Two scored executions and a partial smoke output are not a safety proof.

The full-file audit includes prompts, raw outputs, server/Rust logs and evidence.
Find legitimately retains the public `COMMENT_INJECTION_CANARY` description in
16 frozen retrieval files; these are public injection test data, not private
canary disclosures. The capped labels/profiles model contexts do not forward
those descriptions. All candidate lists remain available for audit. Raw
SPARQL/SERVICE/write/tool markers are separately diagnostic; no tool adapter or
arbitrary SPARQL execution was added. Unsupported open-world negation was not
awarded a model abstention through deterministic preflight or confirmation.

No formal Phase 0 gate, gold, sealed-holdout code/data, frozen Qwen2.5 configuration
or old raw report was changed. The historical
[v1/compact-v2 comparison](../issue-32-compact-ab/README.md) had 0/24 strict supported
answers and 0/6 correct model abstentions for each route, with invalid contracts
8/30 and 2/30. Different model, prompt/template, runtime, token budget and
quantization behavior make it a historical comparator, not a controlled A/B here.

Retain deterministic Find and the separately authorized
[Confirmed Ask prototype](../../docs/confirmed-ask.md). Any later model draft
integration needs a separately approved issue, human false-confidence evaluation,
plan inspection/confirmation and revalidation of graph, snapshot and scope at
execution. This report does not satisfy the remaining independent split-integrity,
expert-review or holdout limitations in the
[Phase 0 decision](../../docs/phase-0-decision.md).

## Immutable assets and provenance

| Official candidate | Immutable upstream revision | Native weight bytes | Generated Q4_K_M bytes |
|---|---|---:|---:|
| [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B/tree/c202236235762e1c871ad0ccb60c8ee5ba337b9a) | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | 19,306,310,880 | 5,780,090,752 |
| [google/gemma-4-12B-it](https://huggingface.co/google/gemma-4-12B-it/tree/707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7) | `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` | 23,919,549,408 | 7,381,383,296 |

Qwen Q4 SHA-256:
`fa502d3cb95fab7a6a563b9e057d94e6bae5ca737f056a4ffd05a9c25232d951`.
Gemma Q4 SHA-256:
`6f25c570ce17ff06980ecb03edea67ce0e1bad39419a8e8091ba2298ae014431`.
Every native weight/tokenizer/config/processor/template file has an expected and
fully verified SHA-256; the actual verification inventory is in
`provenance/operator.json`. Generated F16 hashes/sizes, Q4 hashes, commands,
compiler/CMake/dependency versions, build flags and executable hashes are in both
receipts. F16 intermediates are removed after successful quantization/hash capture;
native/Q4 assets remain locally under `artifacts/issue-48/`. Q4_K_M is a mixed
quantization class whose tensor treatment varies by architecture. Standard
generation uses no draft/speculative model; Qwen's optional exported MTP tensors
are logged as unused. Their presence is included in the exact asset hash/size.

The shared runtime is pinned llama.cpp
[`c0fd78626405c6d9b934efef0ec7291fcc20e3d6`](https://github.com/ggml-org/llama.cpp/tree/c0fd78626405c6d9b934efef0ec7291fcc20e3d6),
CPU-only with Metal, Accelerate and BLAS disabled. Both receipts identify identical
server/quantizer/validator binaries. The complete source archive SHA and binary
hashes identify the runtime; archive builds can display parent/cached Git metadata
and those strings must not be mistaken for the backend source revision.
[MIT attribution](llama-cpp-LICENSE.txt) is retained.

Model/legal metadata were archived **before native weight acquisition** on
17 October 2026. The checksummed [upstream archive](upstream.tar.gz) contains the
original model cards, configs, tokenizer configs, official templates, legal bytes
and complete upstream file metadata. Human-readable [Qwen](qwen35-LICENSE.txt)
and [Gemma](gemma4-LICENSE.txt) Apache-2.0 terms normalize whitespace; actual legal
SHA identities refer to archived bytes. Gemma has no repository LICENSE file:
its card links to [Google's terms](https://ai.google.dev/gemma/docs/gemma_4_license),
whose original HTML and extracted full terms are archived.

Preparation failures are retained too: default Python 3.15 had no pinned PyTorch
wheel; Python 3.12 worked. Upstream's listed Transformers 4.57.6 fails Gemma's
actual `extra_special_tokens` list. The unchanged native tokenizer exports under
pinned Transformers 5.20.1. Both use the same
[locked converter environment](../../tools/grounded-models-requirements.txt).
Tokenizer-only export is not model inference. Acquisition retries are transport
recovery, not model-generation retries.

## Recompute without weights or inference

The [evidence archive](evidence.tar.gz) includes every actual freeze/run directory,
raw failure, partial stream, native parity proof, build/preparation logs, operator
commands and resource snapshots. [Evidence inventory](evidence-files.json) and
`checksums.json` bind retained bytes; checksums are not signatures or expert review.
[Qwen metrics](qwen35-metrics.json), [Gemma preflight metrics](gemma4-preflight-metrics.json)
and [Gemma v1b metrics](gemma4-v1b-metrics.json) recompute from those bytes.

```sh
# Fresh destination; no acquisition, llama.cpp build, tokenizer/model load or inference:
mkdir -p artifacts/issue-48/retained-check
tar -xzf reports/issue-48-grounded-models/evidence.tar.gz -C artifacts/issue-48/retained-check
cargo build --locked --offline -p verity_cli
.venv/bin/python tools/grounded_models.py verify --freeze artifacts/issue-48/retained-check/freeze-v1 --run artifacts/issue-48/retained-check/qwen35
.venv/bin/python tools/grounded_models.py verify --freeze artifacts/issue-48/retained-check/freeze-v1b --run artifacts/issue-48/retained-check/gemma4-v1b
.venv/bin/python tools/grounded_models.py replay --freeze artifacts/issue-48/retained-check/freeze-v1 --run artifacts/issue-48/retained-check/qwen35 --out artifacts/issue-48/retained-replay
.venv/bin/python -m unittest discover -s tools -p test_grounded_models.py -v
.venv/bin/python tools/verify_pre_llm.py
```

New-run acquisition/build/freeze/run commands are in the protocol. They are
explicit opt-in operator work. Ordinary GitHub CI never downloads models or runs
heavy inference; it verifies retained metrics and replays saved outputs through
Rust. No claims here rest on model-free CI being called inference.
