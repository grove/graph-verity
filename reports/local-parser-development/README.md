# Issue #7: measured CPU parser development spike

**The selected setup is inadequate for unattended Ask.** It often emits JSON that
is structurally acceptable while misunderstanding the question. These are public
development measurements against AI-authored references under the owner's
[gold-review waiver](../../docs/phase-0-ai-gold-risk-acceptance.md), not independently
verified Norwegian accuracy, a holdout result or an approved Phase 0 decision.

Measured on the owner-approved **Apple M1 Pro, macOS arm64, 32 GiB RAM**, with four
model threads, CPU only, Metal/BLAS/Accelerate disabled. The model is official
Qwen2.5-1.5B-Instruct Q4_K_M, with llama.cpp b5046. Full model/runtime/tokenizer,
grammar, prompt, build and input identities are in [run.json](run.json) and
[the pinned configuration](../../configs/local-parser.json).

| Measurement | Wikidata `dev` | Schema.org `transfer_dev` |
|---|---:|---:|
| Questions | 46 | 40 |
| Supported / expected abstention | 38 / 8 | 35 / 5 |
| JSON valid | 41 / 46 | 32 / 40 |
| Rust response-contract valid | 41 / 46 | 32 / 40 |
| Incomplete JSON at 1,024-token limit | 5 | 8 |
| Backend failures / retries / timeouts | 0 / 0 / 0 | 0 / 0 / 0 |
| Candidate plans rejected by Rust safety checks | 22 | 24 |
| Candidate plans successfully executed | 19 | 8 |
| Exact structural IR reference matches, all supported cases | 0 / 38 | 0 / 35 |
| Exact answer-binding reference matches, all supported cases | 3 / 38 | 0 / 35 |
| Executed candidates with structural reference mismatch | 19 | 8 |
| Correct expected-status abstentions | 0 / 8 | 0 / 5 |
| Any model abstention / false abstention | 0 / 0 | 0 / 0 |
| Warm end-to-end p50 / p95 / p99, seconds | 10.58 / 28.06 / 36.18 | 10.51 / 26.59 / 28.02 |
| Process-cold first answer, seconds (one sample each) | 17.68 | 18.04 |

The sampled aggregate peak RSS of runner + server + Rust was **1.43 GiB** over
3,862 samples. The OS child-process lifetime high-water mark was **1.40 GiB**.
RSS sampling can miss short spikes and can double-count shared pages; neither is
an isolated incremental model-memory measure. Cold means a new server and Rust
process with **OS page cache not evicted**. Warm measurements reuse a prompt prefix,
exclude the first case, and include failures/abstention questions. Artifact I/O is
inside the measured path. The proposed numerical gates remain unapproved.

Strict structural and answer-binding comparisons include variable/column names and
array order; equivalent alpha-renamed plans can miss a match. Thus 0 structural
matches is not a human judgment that every plan is semantically inequivalent.
However, predicate/entity confusion, invalid bindings, extra patterns and absence
of expected abstention are substantive observed failures. For example,
`wd-dev-001` put Oslo's **entity IRI in the predicate position** and was rejected;
`wd-dev-021` exhausted the output budget inside a string. `wd-dev-008`, `013` and
`018` matched reference answer bindings despite structural mismatches. JSON
validity, safe execution and question understanding must remain separate.

The [summary](summary.json) adds executed-candidate counts and rejection-code
counts derived from the original reports' pipeline/safety fields; these are
postprocessing only. It includes component match counts and per-family strict
pass counts. Component matches include empty fields, so inspect individual cases
for meaningful datatype/number comparisons. See the original
[Wikidata report](wikidata-report.json) and
[transfer report](worldcities-transfer-report.json) for every question's output,
stage, mismatch diagnostics, timings and failure details. All supported questions
remain in denominators; a rejection or unfinished response cannot disappear from
the agreement calculation.

## Constraint and safety evidence

The exact runtime accepted four valid response variants and rejected seven negative
grammar fixtures: non-JSON, truncated JSON, raw SPARQL, an invalid direction enum,
extra plan/root fields and a missing scope. Its validator **exits zero even on
rejection**, so the harness checks its verdict text and has a regression test.
The live unconstrained control obeyed a request to add a forbidden root field;
the same prompt with the production grammar omitted it. A malicious RDF-label /
ChatML-delimiter probe remained within the grammar and was independently rejected
by Rust for an unauthorized predicate. These bounded probes demonstrate the actual
combination; they do not prove universal robustness. Output limits can still yield
incomplete valid prefixes, which Rust rejects.

Rust regressions separately check malformed/raw-query responses, unknown fields,
scope expansion, changed snapshots, unknown identifiers, invalid types/operators,
wrong-but-valid numeric plans, and actual `local_model` versus fixture attribution.
Model JSON never becomes executable query text. No authorization-boundary execution
failure was observed. The external sealed holdout was neither opened nor evaluated.

## Reproduce and inspect

Follow [the setup and offline command](../../docs/local-parser-experiment.md#repeat-the-experiment).
The experiment's runner, config, prompt, schema and Rust sources are frozen in
`development-v4/` inside [evidence.tar.gz](evidence.tar.gz), along with all 86
authorized requests, oracle contexts, exact prompts, raw runtime responses,
proposals and logs. It contains **no model weights or hidden cases**. Verify and
extract from this directory:

```sh
shasum -a 256 -c evidence.sha256
mkdir -p /tmp/graph-verity-parser-evidence
tar -xzf evidence.tar.gz -C /tmp/graph-verity-parser-evidence
```

Earlier failures are preserved too: `development-v1` stopped before inference due
to an incorrectly named CLI path; `v2`'s unconstrained-word probe caused a constrained
but unfinished output at 1,400 tokens; `v3` was interrupted after an overly broad
substring label selector included the Norwegian word “er”. `v4` fixed the selector,
bounded oracle vocabulary/labels, enabled prompt-prefix caching and used the frozen
1,024-token budget for the entire 86-question run. No question was retried within
that run. These are disclosed development revisions, not a hidden-test protocol.

The deterministic fallback is the existing authorized exact `resolve` + user-selected
typed `run` path, with plan confirmation or abstention where intent is unclear.
Fixture replay is not language understanding. This result does not establish that
every small model will fail; a revised model/prompt needs fresh development evidence
and a separately authorized frozen holdout before any feasibility claim.
