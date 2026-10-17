# Issue #32: controlled M1 Pro v1 / compact-v2 route comparison

This is one public development experiment against the original raw-model v1
baseline. It measures agreement with AI-authored references, not expert semantic
accuracy, unseen-ontology generalization, or Phase 0 `GO`. Issue #9's behavioral
requirements and the separately sealed holdout remain outside this result.

**Decision: fall back to deterministic templates / explicit plan confirmation.**
Compact v2 improves syntax but does not solve interpretation in this experiment:
complete exact answers remain **0/24**, correct model abstentions remain **0/6**,
and **no v2 plan reaches execution**. Do not promote unrestricted Ask or claim
Phase 0 `GO`. A further model experiment needs a separately versioned model or
new hypothesis, rather than an identical rerun or sealed-holdout tuning. This is
negative evidence for the final decision tracked by #10; it does not close #9.

## Results

The real Mac run completed all **30/30 cases once**. Its command exited zero,
meaning measurement completed, not that semantic acceptance passed. All 30
expected behaviors fail under strict scoring and under the positional diagnostic.
The [operator receipt](operator.json) records directory creation at
`11:20:08 UTC` and completion observed after process exit at `11:46:40 UTC` on
17 October 2026; [stdout](operator.stdout.log) lists every completed case and
[stderr](operator.stderr.log) is empty.

| Metric | Frozen v1 | Compact v2 |
|---|---:|---:|
| JSON / decoder-contract valid | 22/30 | 28/30 |
| Invalid JSON/contracts | 8/30 | 2/30 |
| Strict complete exact named answers / supported | 0/24 | 0/24 |
| Separately position-aligned complete exact answers / supported | 0/24 | 0/24 |
| Valid model abstentions / all | 0/30 | 0/30 |
| Correct expected-status model abstentions / expected | 0/6 | 0/6 |
| Either valid abstention status / expected | 0/6 | 0/6 |
| Deterministic preflight blocks | 0/30 | 4/30 |
| Expander-only rejections, excluding preflight | n/a | 24/30 |
| v1 Rust validator/compiler rejections | 18/30 | 0/30 |
| Expanded-v1 plans returned after validation | n/a | 0/30 |
| Subsequent v1 validation accepted | 4/30 | 0/30 |
| Executions | 4/30 | 0/30 |
| Wrong-but-executable, strict / positional | 4/30 / 4/30 | 0/30 / 0/30 |
| Generated output reached token cap | 8/30 | 2/30 |
| Runtime `truncated` flag | 0/30 | 0/30 |
| Backend failures | 0/30 | 0/30 |

The v2 terminal outcomes partition all cases: **2 invalid + 24 expander-rejected +
4 preflight-blocked = 30**. Zero compiler rejections here means no v2 candidate
survived the earlier checks; it is not evidence that the model learned v1's rules.
Zero wrong executions likewise reflects containment of every candidate, not better
semantic plans. The four preflight blocks cover alias ambiguity and unsupported
negation in both ontologies. The original v1 evaluator recorded raw model behavior
before those guards, which remains unchanged in its archive.

| Ontology | v1 → v2 strict supported answers | v1 → v2 correct abstentions | v1 → v2 invalid contracts | v2 expander / preflight blocks |
|---|---:|---:|---:|---:|
| Source | 0/12 → 0/12 | 0/3 → 0/3 | 3/15 → 0/15 | 13 / 2 |
| Schema.org adaptation | 0/12 → 0/12 | 0/3 → 0/3 | 5/15 → 2/15 | 11 / 2 |

Every family has zero complete supported answers or correct expected abstentions.
The [30-row case comparison](case-comparison.md) shows each family and ontology,
both scores, errors/statuses and output counts; [comparison.json](comparison.json)
also supplies aggregate per-family metrics, all case diagnostics and full intervals.
Both remaining syntax failures are the transfer `gt`/`ge` numeric-boundary cases,
each cut off at 1,024 generated tokens. Zero exact-answer transfer gap means both
domains failed, not successful ontology transfer.

Descriptive 95% Wilson intervals are **0–13.8%** for 0/24 exact answers and
**0–39.0%** for 0/6 correct abstentions in each route. Invalid-contract proportions
are 26.7% (14.2–44.4%) for v1 and 6.7% (1.8–21.3%) for v2. Wrong-execution
proportions are 13.3% (5.3–29.7%) and 0% (0–11.4%). These small correlated public
counts do not support an independent causal or population-accuracy claim.

The exploratory targets for syntax (<8 invalid) and fewer wrong executions (<4)
are met; the targets for any complete supported answers and any correct model
abstentions are not. The observed safety boundary remains intact. These are not
revised Phase 0 gates.

## Raw behavior and containment

Source v2 failures comprise nine candidates exceeding structural limits, four
unknown/wrong-role/cross-graph references, and two preflight blocks. Transfer has
eleven structural-limit failures, two incomplete JSON outputs, and two preflight
blocks. All 28 decoded proposals are candidates; none is a model abstention.

The source `inverse` proposal enumerates twelve forward edges, exceeding the
eight-edge limit, instead of expressing the requested owner relation. Its exact
raw bytes also appear for `ge`, `missing-triple`, `alias`, and all three injection
questions: seven different questions, one proposal. Source `two-hop` lists eight
edges with predicates 15–22 and variable slots 16–23, failing reference validation
before later variable checks. Source has only six distinct raw proposals for 15
questions; transfer also has six. Across both domains there are eleven distinct
v2 proposals versus 29 in v1. Valid JSON is not evidence of question understanding.

All six supported public injection cases fail v2 expected behavior through
structural rejection. This is Rust containment, not successful semantic resistance.
Observed unauthorized scopes, private/comment-canary disclosures in requests,
prompts, raw proposals or execution evidence, and non-read-only executions are all
**0/30 in both routes**. Both shell canary paths were absent before and after the
run. Model strings enter only the typed data bridge; there is no generated SPARQL
or tool-dispatch interface. The runtime controls, their raw strings and independent
Rust/grammar verdicts remain in the archive. These bounded observations do not
guarantee immunity to other prompts, graphs or attacks.

## Tokens, latency and RAM

| Raw tokens, public cases only | v1 input / output | v2 input / output |
|---|---:|---:|
| Source | 16,818 / 7,040 | 39,209 / 7,213 |
| Schema.org adaptation | 16,743 / 8,674 | 38,819 / 12,489 |
| Total | 33,561 / 15,714 | 78,028 / 19,702 |

Neither total prompt tokens nor total output tokens decreased. Full authorized
tables increased prompt cost; lengthy enumerated candidates increased output cost
despite the compact representation. Every case's input/output tokens, stop type,
token-cap and `truncated` flags, model-roundtrip and runtime prompt/generation
timings are retained. The runtime `truncated` flag is distinct from output-cap
termination; neither route silently counts cutoff output as a model abstention.

| End-to-end latency, seconds | v1 cold first / warm p50 / warm p95 | v2 cold first / warm p50 / warm p95 |
|---|---:|---:|
| Source | 17.41 / 11.01 / 23.73 | 109.89 / 34.87 / 60.18 |
| Schema.org adaptation | 17.00 / 13.36 / 27.38 | 60.66 / 53.00 / 80.78 |

Each ontology has a fresh server; OS page cache was **not evicted**. Cold first
answer includes server/Rust startup, while warm uses the remaining fourteen cases.
Case latency includes catalog, prompt/tokenization, generation, validation and any
query/evidence work, excluding independent reference-query scoring. Host work and
load were not isolated, so these are descriptive timings, not a clean speed
benchmark. Generation percentiles and each case's raw timing components are in
the comparison JSON and archived runtime responses.

Sampled aggregate peak RSS is **1.43 GiB v1 / 1.41 GiB v2** (1,500,560 /
1,478,368 KiB); OS child-lifetime high-water RSS is 1,471,888 / 1,445,760 KiB.
The runner sampled descendants at roughly 200 ms, including startup and `ps`
overhead, with 1,955 / 5,588 samples. Samples can miss spikes and double-count
shared pages; child high-water values are separate measurements. Small RAM
differences do not establish a meaningful improvement.

## Frozen protocol and machine

The [sealed input freeze](freeze.json) was recorded at
`2026-10-17T11:20:01.287745+00:00`, before runtime controls or public v2 inference.
Its file SHA-256 is
`071681c5c08cd329fd1137ea5cf94b4ce94c2c3d34e5ef2596c186bcab99dba8`.
It includes 51 input hashes, both complete configurations, the exact source/main
commit `3d87b7a2021fa883e720873077ee1218d19448cb`, prompt/grammar/schema and
expander/index-construction sources, benchmark/data/policy hashes, Rust binary,
runtime receipt and model identity. The tokenizer is embedded in the pinned GGUF.
The original v1 source revision is
`f9135015b528615847869082070d1cfd8ad5094f`; its complete identity remains in the
[unchanged baseline](../issue-9-adversarial/README.md) and its archived `run.json`.

Prerequisites #30/#31 were merged as PRs #33/#34. The full model-free
[main CI run](https://github.com/grove/graph-verity/actions/runs/39028124499) passed
before the freeze. The separate local
[prerequisite verification](prerequisite-verification.json) passed 75 Python and
28 Rust tests, formatting, Clippy, source rebuilds, reference/oracle checks and
historical evidence verification. That verification invoked no model.

Both inference routes used the owner's Apple M1 Pro, 32 GiB RAM, 10 visible logical
CPUs, macOS 26.6.2 arm64, and **four CPU threads**. Qwen2.5-1.5B-Instruct Q4_K_M
model SHA-256:
`6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
llama.cpp b5046 revision:
`74d4f5b041ad837153b0e90fc864b8290e01d8d5`.
The comparison verifies identical runtime binary hashes, model/configuration pins
and recorded hardware. No Metal, BLAS or Accelerate backend was enabled.

The actual opt-in Mac command was:

```sh
.venv/bin/python tools/local_parser.py run --mode compact-v2 --suite adversarial \
  --out artifacts/issue32-compact-ab/run-1
```

This fresh directory received one generation per public question, without retries,
repair, gold changes or holdout access. The runner also executed its three
generation boundary controls before the 30 cases; those controls are excluded from
semantic metrics. The original v1 archive and reports remain byte-identical and
were not regenerated. The new analysis code does not change the model runner,
prompt, grammar, schema, expander, vocabulary selection, data or references.

## Scoring and attribution

Scoring version: `issue32-scoring-v1-strict-named-plus-positional`.
The primary metric preserves the original v1 policy: exact **named** RDF binding
sets and `complete_within_scope` on all **24 supported** cases. Invalid output,
rejection and abstention remain failures in that denominator. Strict named-set
equality, like the original evaluator, treats two empty result sets as equal;
the diagnostic below additionally checks projection width.

The separately declared positional diagnostic aligns columns by projection order,
requires equal projection widths and preserves full RDF term metadata. It is
recomputed for both routes, without rewriting frozen v1 scores. It is not proof of
query equivalence or expert adjudication. V2's existing structural IR diagnostic
normalizes variable names by first appearance and count aliases by projection
position; frozen v1 structural scores retain their original name sensitivity.
Raw plans and rows remain unchanged. All references are the same AI-authored gold,
with no independent human review added by this experiment.

Correct model abstention requires an actual valid model abstention with the exact
expected status, over **six expected abstentions**. The broader safety-oriented
metric allowing either valid abstention status is separate. A rejected candidate,
invalid reason or deterministic preflight block is never a model abstention.
Wrong-executable counts mean an execution with a result/status mismatch under the
specified binding metric, not a complete adjudication of question meaning.

JSON validity and decoder-contract validity are separate from expander limits and
v1 validator/compiler acceptance. `expanded_v1_validated` counts only returned
expanded plans: the expander compiles v1 before returning them. The subsequent
independent v1 check is also retained. Expander-only failure codes/messages are
attributed against the frozen source; compiler/validator errors reached inside
expansion are reported separately. The runner's unchanged `expansion_rejections`
summary includes preflight blocks; the comparison separates those blocks and
excludes them from its expansion-rejection count.

This compares two complete **routes**, with several deliberate differences:
v1 uses a gold-derived oracle vocabulary shortlist; v2 retains every authorized
Rust numeric ID with at most four labels. Prompt, grammar, output representation
and preflight enforcement also differ. Consequently, it cannot attribute a result
to output compactness alone. The model, runtime, generation budgets, seed,
temperature, four threads, public questions, source data and evaluation references
remain pinned. No tuning followed the observed responses.

Every proportion in [comparison.json](comparison.json) includes its denominator and
a descriptive Wilson 95% interval. The tiny synthetic paired cases and categories
are correlated; these intervals do not establish a statistically independent
improvement or general safety guarantee. The same table and raw evidence allow
separate interpretation of model behavior and deterministic containment.

## Model-free verification

From the repository root, with the normal pinned Python dependencies:

```sh
.venv/bin/python tools/compact_ab.py
.venv/bin/python tools/phase0.py verify reports/issue-32-compact-ab/manifest.json --check-inputs
.venv/bin/python -m unittest discover -s tools -p 'test_compact_ab.py' -v
```

The first command recomputes every comparison from the two archived runs and
unchanged public gold. It verifies the input freeze, both archives and their inner
manifests, raw-runtime-report agreement, source/configuration/hardware identities,
and the saved metrics and case table. Normal CI discovers these checks and also
replays all 30 saved v2 strings through the actual Rust expander/evaluator, comparing
statuses, errors, expanded plans and any executions. That replay uses saved output
in place of generation and does not load model weights or llama.cpp.

[The manifest](manifest.json) hashes every retained report file and the analysis
implementation. [The evidence archive](evidence.tar.gz), checked by
[evidence.sha256](evidence.sha256), contains the complete original `run-1/` tree:
requests, authorized tables, prompts, unmodified raw proposals, full runtime token
and stop metadata, grammar verdicts, expanded plans where available, Rust reports,
failures and logs. Extraction is unnecessary for verification. No original v1
evidence or sealed-holdout bytes are included in this new archive.
