# Issue #8 public CPU development repeat

This is a **new measured 86-question public development run**, separate from the
unchanged [historical PR #20 evidence](../local-parser-development/README.md) and
[its baseline reassessment](../phase-0-baseline/README.md). It is AI-reference
agreement, not independently expert-validated semantic accuracy, a locked evaluation,
a deployment-target benchmark or production readiness. Formal assessment: **NOT READY**.

## Results

| Metric | Wikidata dev | Schema.org transfer_dev |
|---|---:|---:|
| Questions / supported / expected abstentions | 46 / 38 / 8 | 40 / 35 / 5 |
| JSON and strict response-contract valid | 41/46 | 32/40 |
| Independent Rust validation rejections | 22 | 24 |
| Strict IR reference agreement | 0/38 | 0/35 |
| Exact answer-binding reference agreement | 3/38 | 0/35 |
| Correct expected abstentions | 0/8 | 0/5 |
| False abstentions on supported cases | 0/38 | 0/35 |
| Structurally different plans successfully executed | 19 | 8 |
| Warm end-to-end p50 / p95 / p99, seconds | 9.613 / 26.039 / 32.521 | 9.347 / 23.281 / 23.377 |
| Generation round-trip p50 / p95 / p99, seconds | 9.596 / 26.029 / 32.515 | 9.339 / 23.207 / 23.374 |
| Process-cold first answer, seconds | 16.801 | 16.722 |
| Server startup / Rust+snapshot startup, ms | 445.98 / 26.78 | 434.70 / 49.56 |
| Backend failures / timeouts / retries | 0 / 0 / 0 | 0 / 0 / 0 |

All model-quality counts reproduce PR #20. The original warm p95 was 28.06/26.59
seconds; the new repeat is 26.04/23.28 seconds. Both exceed the **proposed**, unapproved
10-second budget. Contract validity does not mean correct interpretation. Structural
comparison is conservative and can reject equivalent plans, but predicate/entity/
datatype and other substantive failures are retained. Answer comparison is separate.
The low 7.9 percentage-point development transfer gap does not establish generalization.

The [JSON report](summary.json) includes all supported attempts in denominators,
case/family scores, Wilson intervals, macro P/R/F1 with descriptive bootstrap intervals,
actual bindings/evidence, errors, explicit unknown measurements and component scores.
See the [readable decision matrix](summary.md) and [checksum manifest](manifest.json).
No complete UI was tested: observed unflagged false confidence/disclosure is unavailable,
not inferred from the 27 structural wrong-plan execution proxies. Scope/evidence
checks on those 27 recorded executions found no scope violations; this is not a full
information-disclosure or population-safety claim. The human review ledger is unchanged.

## Hardware and conditions

Apple M1 Pro, macOS 26.6.2 arm64, 10 logical cores, 32 GiB system RAM, four model and
prompt-processing threads, CPU only (Metal/BLAS/Accelerate disabled). Same pinned
Qwen2.5-1.5B-Instruct Q4_K_M, embedded tokenizer, llama.cpp b5046, seed, prompt,
grammar and oracle-vocabulary configuration as PR #20.

Sampled process-tree peak RSS: **1,529,616 KiB (1.459 GiB)**, 4,572 samples, no sampler
error. Sampling every 200 ms includes descendants/startup and `ps` overhead, may
miss spikes and double-count shared pages. It starts after grammar probes; the
OS child high-water mark is retained separately in `run.json`. Historical PR #20's
three-known-process sample of 1.43 GiB has not been overwritten or reinterpreted.

New server per dataset, prompt-prefix caching enabled, OS page cache not evicted.
This is process cold, not uncached disk cold. Service cold timing adds model/server
and Rust/snapshot startup; preceding asset verification and grammar-probe preflight
are excluded. Warm sample sizes are 45/39; generation sample sizes are 46/40.
Concurrent development verification/scoring added some host load, so this is not an
isolated latency experiment. No deployment CPU has been separately designated or approved.

The inference run started from a working implementation based on `dfc6c66`; exact
model/runtime/compiler binary and input identities are in `run.json` and the Rust
reports. The exact loaded Python entry point is archived as `executed-local-parser.py`
and matches its startup SHA256, including the stage measurement and descendant sampler.
Its later optional private-adapter parameter is absent from that captured entry point;
public inference behavior/configuration was unchanged. Final report generation used
clean source commit `e28392b` and scoring policy `phase0-v1-ordered-structural-and-binding-set`.
This development provenance must not be presented as a preregistered locked run.

## Reproduce and inspect

```sh
.venv/bin/python tools/local_parser.py prepare
cargo build --locked -p verity_cli
.venv/bin/python tools/local_parser.py run --out artifacts/local-parser/another-development-repeat
```

The archive contains only public development inputs/outputs, model metadata,
prompts/raw responses, Rust reports/evidence, runtime logs, and a separate initial
sandbox-denied attempt (CPU identification was refused before inference). The
successful run used host hardware/RSS/loopback access and existing local assets;
there was no private holdout access. No weights are in the archive.

```sh
shasum -a 256 -c reports/phase-0-development-repeat/evidence.sha256
mkdir -p artifacts/local-parser
# Extract only when these archived output directories are absent; preserve old runs.
tar -xzf reports/phase-0-development-repeat/evidence.tar.gz -C artifacts/local-parser
.venv/bin/python tools/phase0.py verify artifacts/local-parser/issue-8-public-development-host/manifest.json --check-inputs
.venv/bin/python tools/phase0.py report --evidence artifacts/local-parser/issue-8-public-development-host --out artifacts/phase0/repeat-reassessment
```

Recommendation for this measured configuration: **revise; abandon unattended
unrestricted Ask with it**. Keep exact resolution and manual typed plans available.
Approval, independent expert review/evaluation, target-device designation/measurements,
an authorized external locked run and UI/disclosure evidence remain outstanding.
Issue #9 should measure interpretation confirmation and warning behavior; issue #10
must distinguish bounded experimental continuation from a formal feasibility GO.
