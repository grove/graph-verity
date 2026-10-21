# Controlled v1h-budget Qwen evidence — INCONCLUSIVE_REVISE

The single explicitly authorized Qwen run completed **both native sampling controls
and all 36 semantic diagnostic observations**, with 38/38 native completions,
zero retries, zero fatal/runtime/resource stops and zero unattempted observations.
Oracle responses are byte-identical to historical r3. On the 14 shared BM25-v1
observations, exposed-reference agreement changes from **6/14 to 8/14**; the
three newly measured observations contribute two additional reference matches.
Full BM25-v1 agreement is **10/17**. This is a bounded diagnostic result, not
independently verified semantic correctness.

**Independent human semantic review is deferred, not completed or passed.** All
36 human-judgment fields remain null. This does not prevent further separately
authorized controlled research, but prevents independently validated semantic
readiness claims. Decision remains **INCONCLUSIVE_REVISE**, with no model ranking,
semantic GO, exact-answer accuracy or product-readiness claim. Keep #83 open and
#75 integration disabled. No model-generated RDF execution, sealed holdout access,
Gemma/v1g inference, threshold change, download, user-process interruption or
automatic retry occurred. No further inference or automatic merge is proposed.

## Authorization and registered identities

PR [#94](https://github.com/grove/graph-verity/pull/94) was verified merged, and
execution started from its main commit
`7c689ca97082bf3969b1d98d3274ed824efd26a9`. The owner replied exactly
**“I authorize it.”** immediately after the exact command proposal in the active
conversation. [authorization.json](authorization.json) retains that message,
proposal, revision/model/schedule/output boundaries and pre-run receipt recording
time, `2026-10-21T07:46:25.201090+00:00`. That is the receipt time; no independent
user-message timestamp was supplied. The task prompt was not used as inference
authorization. The output directory and no-retry ledger were absent at receipt.

The command was executed exactly once and exited zero:

```sh
.venv/bin/python tools/native_one_hop_v1h.py run \
  --freeze artifacts/v1h-budget \
  --model qwen35 \
  --allow-inference \
  --out artifacts/issue83-v1h-budget-qwen35-first
```

The unchanged [registration](../native-one-hop-v1h-budget/registration.json)
binds registered source commit `d485b9fcaf2de834d07788e8f15fc193b6cce664`, all
76 source/dependency hashes and the following original assets:

| Identity | Registered value |
|---|---|
| Experiment | `issue83-native-cpu-v1h-budget` |
| Freeze archive SHA-256 | `61e2feb6883bcbcadfa8ace259b3e2f9ef2f2c8c3d771a0523ebbba7e8d295df` |
| Freeze inventory SHA-256 | `d73ba8e301bd488b6fa60b75f3569f64d5d5ec981139a76fbecc66a1948613e8` |
| Original Rust binary SHA-256 | `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db` |
| Model | `Qwen/Qwen3.5-9B`, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, Apache-2.0 |
| Q4_K_M SHA-256 | `fa502d3cb95fab7a6a563b9e057d94e6bae5ca737f056a4ffd05a9c25232d951` |
| llama.cpp revision | `c0fd78626405c6d9b934efef0ec7291fcc20e3d6` |
| llama-server SHA-256 | `40188c617d6dc1d7f060587233a9eaf7d3929e1740db0e4650c31b74616be78a` |

Fresh model-free asset rehashing exactly reproduced the registered receipt,
including native checkpoints, retained Q4 files, runtime source tree/executables,
tokenizers/templates and original license receipts. Python and pinned package
identities also match: transformers 5.20.1, tokenizers 0.23.3, Jinja2 3.1.6. Assets
were hashed, never downloaded, converted, rebuilt or substituted. A pre-existing
matching freeze was preserved at
`artifacts/v1h-budget-preserved-20261021T074056Z`; the committed archive was then
restored into a fresh `artifacts/v1h-budget`. Nothing was extracted over it.

[evidence.tar.gz](evidence.tar.gz) contains **1,729 hash-bound original files**:
the unchanged run and restored freeze, all 76 registered source files, original
registration, authorization, no-retry ledger, readiness/recount receipts, source
audit notes and packaging/analysis sources. It retains original prompt bytes,
packets/IDs, model response bytes/base64, complete SSE streams, template/token IDs,
GBNF and Rust decisions, proposed plans, native timings, host inventory and
concurrent process-tree RSS observations. No weights or executable binaries are
packaged. [evidence-files.json](evidence-files.json) binds every file and archive
SHA-256 `6d15494ea7b8dedf33f5a95529d0a96075d18158c7700b2214db6411fd969eb7`.

## Controls, integrity and complete denominators

The two native sampling controls are outside the semantic denominator.
Unconstrained sampling emitted the forbidden extra field and was rejected by
native GBNF/Rust; constrained sampling omitted it and was accepted. Both controls
passed their registered expectations. Native character controls gave all three
expected acceptances and nine expected rejections. All 38 terminal SSE streams
reconstruct their original response bytes. All 38 actual native HTTP
template/token results, request token arrays and prompt bytes match the sealed
pre-load receipt. All 36 semantic responses are strict-contract/GBNF valid and
Rust accepted; there are no deterministic draft rejections. The runner's broader
`controls_passed`/`smoke_passed` fields remain false and are not relabeled as a
semantic pass.

| Revision / condition | Scheduled | Attempted | Completed | Fatal failures | Unattempted | Reference matches | Reference disagreements |
|---|---:|---:|---:|---:|---:|---:|---:|
| r3 oracle | 19 | 19 | 19 | 0 | 0 | 8/19 | 11/19 |
| v1h oracle | 19 | 19 | 19 | 0 | 0 | 8/19 | 11/19 |
| r3 BM25-v1 | 17 | 14 | 14 | 1 pre-generation context stop | 3 | 6/14 | 8/14 |
| v1h BM25-v1 | 17 | 17 | 17 | 0 | 0 | 10/17 | 7/17 |

The r3 context failure occurred before a completion request at the first of its
three unattempted observations; it is not a model answer or semantic error.
Every observation, including r3's missing outcomes, remains in
[comparison.md](comparison.md), [analysis.json](analysis.json) and the complete
[semantic failure matrix](failure-matrix.md). Gemma is not part of this authorized
Qwen denominator and was not loaded. The separate original strict 30-case stages
remain unrun by this diagnostic.

## Semantic observations, separated from reference agreement

| Measure | v1h oracle | v1h BM25-v1 |
|---|---:|---:|
| Exposed candidate-reference fields all match | 3/10 | 3/8 |
| Forward candidate-reference agreement | 3/8 | 3/6 |
| Reverse candidate-reference agreement | 0/2 | 0/2 |
| Model-origin clarification on clarification references | 3/3 | 3/3 |
| Clarification matching the separate AI ambiguity audit | 4/4 | 4/4 |
| Unsupported-reference classification | 2/6 | 4/6 |
| Preview-accepted candidate with exposed-plan mismatch | 0 of 3 candidates | 0 of 3 candidates |

All five plan fields—start, predicate, graph, direction and projection—have the
same 3/10 oracle and 3/8 BM25-v1 agreement denominators, including abstentions.
Clarification is emitted by the model, never inferred from Rust rejection.
The fourth AI-audit ambiguity is the source-label probe: clarification disagrees
with its original candidate reference but agrees with the separately registered
source ambiguity audit. Neither audit nor exposed reference is independent human
truth.

Oracle prompts and all 19 responses are byte-identical to r3: three forward
candidates, fourteen clarifications and two unsupported responses. Both reverse
smokes still clarify. The P131 rationale recognizes reverse traversal but
abstains over other subjects; the website rationale also abstains. Recognizing a
direction in prose does not produce a reference-matching reverse plan.

On the **14 paired, completed BM25-v1 identities**, reference agreement changes
6/14 -> 8/14, with two gains and no lost matches. Only the write response is
byte-identical; the other thirteen rationales change. The gains are:

- `filter`: clarification becomes unsupported, correctly citing the filtering
  prohibition and dropping r3's false assertion that 630752 is not greater than
  100000. Both representations already fit context (3,137 -> 3,085 input tokens).
- `smoke-eva-01`: clarification becomes a candidate matching the exposed country
  plan. Its rationale now follows visible 102 -> 101 usage, but calls opaque P17
  the country relation and unlabeled graph-0 Q33/101 Finland without a supplied
  definition or identity bridge.

The three newly measured BM25-v1 identities have **no paired r3 model response**.
`smoke-eva-08` describes the reverse website lookup (103 as object, 102 as subject,
1006/P856) but clarifies instead of proposing a reverse plan. The two explicit
country probes propose exposed-reference-matching candidates. These are added
observations, not measured before/after semantic improvements.

Concrete source/table contradictions remain despite acceptance:

- Oracle `repeat-0`, `repeat-1` and `smoke-eva-01` share the same response, which
  calls 1004 schema:Country/graph 1 and P1448. The visible binding is P17/graph 0;
  P1448 is 1003. These are three correlated observations of one response pattern.
- BM25-v1 `smoke-eva-02` falsely says Q134620 lacks an entity ID; ID 100 in graph 0
  is present. The predicate table really is empty, a separate blocker.
- BM25-v1 English explicit-country candidate calls 1004 P1448 and its object a
  literal string Finland. The binding is P17 and the object is entity 101/Q33.
  All plan fields nevertheless match the exposed reference. Thus zero measured
  wrong-but-executable **plan-field mismatches** does not validate its rationale
  or independently establish correct natural-language interpretation.

The automatic rationale rule recognizes only narrow whole English ID assertions;
its zero recognized contradictions is not a clean semantic bill of health.
The source-bound coding-agent notes in the matrix record the contradictions
above, while independent human judgments stay null. P17/P131/P856 meanings are
not established merely by opaque IDs, adjacency or reference agreement.

Compaction does not restore missing vocabulary: BM25-v1 English-forward and
Norwegian-reverse smokes still lack authorized numeric predicates. Raw adjacent
packet triples do not authorize adding those IDs. Count and multi-hop still
clarify rather than unsupported; oracle negation/count/filter/multi-hop retain
their r3 classification failures. New rationale changes are mixed: source-label
clarification now focuses on the actual label-predicate ambiguity, while the
explicit-label probe introduces an unasked Campus collision and the English
forward probe invents an ID-absence problem. Private/write statuses remain
unsupported, but the new private rationale emphasizes missing salary vocabulary;
this is not a general access-boundary certification. No private canary appeared.

## Context, latency and resource measurements

All 38 scheduled Qwen prompts were recounted before loading. Exact original and
columnar prompt bytes/token arrays reproduce registration; all 36 retained
historical Qwen native parity records reproduce offline. Actual fresh native
parity was then checked before each completion. Every scheduled columnar prompt
satisfies strict **input + 512 < 16,384**. Largest input is **14,019**, total
**14,531**, compared with original reverse-website **18,926 + 512 = 19,438**.
The small Norwegian reverse retrieval prompt increases by five tokens
(2,803 -> 2,808); not every packet saves tokens. Per-observation before/after
counts, token hashes and exact arrays remain retained.

The fresh pre-load host receipt at `2026-10-21T07:47:17.698263+00:00` passed the
unchanged gates: Apple M1 Pro, 32 GiB, arm64, ten logical CPUs, one-minute load
**5.9331 <= 7.5** (load/CPU 0.5933), free memory 49%, swap 0.75 MiB, disk
299.50 GiB, maximum competing-process CPU 93.4%, no competing model process,
AC power and no thermal/performance warnings. The runner enforced age <=60 s,
CPU four threads, zero GPU layers, concurrency one, seed 7, temperature zero,
thinking off, Q4_K_M, 512 output tokens and 300-second deadlines.

| Observation latency | r3 p50 / p95 | v1h p50 / p95 |
|---|---:|---:|
| Oracle, same 19 identities | 98.21 / 106.70 s | 99.02 / 110.33 s |
| BM25-v1, same 14 completed identities | 116.47 / 191.35 s | 103.34 / 162.07 s |
| BM25-v1, all 17 v1h observations | No complete baseline | 111.67 / 284.30 s |

Startup was **11.247 s**. Sampled concurrent process-tree peak was **11.223 GiB**
over **16,866 samples**, with no monitor error, below the 24 GiB ceiling; r3's
retained peak was 12.316 GiB. The reverse-website observation took **284.296 s**
(runtime 283.812 s), including native prompt processing 260.006 s and prediction
21.258 s. It completed within the 300-second deadline, with little margin.
The full BM25-v1 diagnostic p95 exceeds the retained 120-second engineering
target; this does not constitute a passing strict-stage evaluation.

Latency includes context verification, trusted preview and model work; runtime
elapsed includes tokenizer/template parity and completion. Native prompt/decode
timings, actual token counts, cache observations and every resource sample are
retained separately. RSS sampling can miss peaks and double-count shared pages;
cache state and unrelated host load were not controlled or evicted.

The **oracle representation is unchanged**. BM25-v1 packet presentation changes
to reversible columns/string references while source information, ordered values,
packet IDs and retrieval membership remain preserved. Representation and token
count effects are confounded. r3 is exposed, incomplete historical evidence;
observations include correlated repeats and are not a randomized baseline. Neither
observed improvements nor latency/memory differences are attributed solely to
token reduction. No significance, generalization or model-ranking claim follows.

## Model-free reproduction and validation

Portable reproduction uses repository Python dependencies and no model assets,
native executable, network or process creation:

```sh
.venv/bin/python tools/analyze_v1h_qwen.py --out artifacts/issue83-v1h-qwen-reanalysis
cmp artifacts/issue83-v1h-qwen-reanalysis/analysis.json experiments/native-one-hop-v1h-budget-qwen35-evidence/analysis.json
cmp artifacts/issue83-v1h-qwen-reanalysis/comparison.md experiments/native-one-hop-v1h-budget-qwen35-evidence/comparison.md
cmp artifacts/issue83-v1h-qwen-reanalysis/failure-matrix.md experiments/native-one-hop-v1h-budget-qwen35-evidence/failure-matrix.md
.venv/bin/python -m unittest discover -s tools -p test_analyze_v1h_qwen.py -v
```

The original-host replay, with the registered binary and a verified restored
freeze, reproduces **all 74 saved Rust previews** without loading models:

```sh
.venv/bin/python tools/native_one_hop_v1h.py replay \
  --freeze artifacts/v1h-budget --run artifacts/issue83-v1h-budget-qwen35-first
```

The complete model-free pipeline and final preservation results are recorded in
`validation.json` and `preservation.json`; complete logs are retained alongside
them. It runs in a separate source/build tree with `CARGO_NET_OFFLINE=true` and
`REQUIRE_FIND_BROWSER=1`, preserving the registered executable. No historical
hash, registration or source is refreshed to accept the new evidence.

## Recommendation

Retain this evidence and stop. A useful next research proposal is a separately
registered **status-rule-precedence ablation**, keeping packet presentation,
source membership, resources and schedule fixed, because count/multi-hop and
oracle unsupported-operation failures persist. Predicate definitions, graph-name
wording and alternative retrieval are separate factors and should not be bundled
into that proposal. Actual independent source-first semantic review remains
necessary before independently validated readiness claims, while remaining
deferred for this controlled diagnostic. Any new inference requires separate
explicit authorization. Do not automatically run Gemma, v1g, a revised prompt,
another Qwen attempt, #75 integration or merge.
