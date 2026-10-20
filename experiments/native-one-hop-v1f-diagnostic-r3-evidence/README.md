# Retained v1f r3 Qwen evidence — INCONCLUSIVE_REVISE

The pre-existing Qwen attempt completed **33/36 diagnostic observations** and
both native sampling controls, then stopped on the frozen context limit. This
review launched no inference and performed no retry. Original inference
authorization has now been affirmed by the owner with **“I authorize all of it.”**
The [current approval supplement](authorization-supplement.json) preserves that
message. The retained run contains no contemporaneous pre-run approval record,
and issue #83 had no comments when inspected; this remains a provenance
limitation. The earlier “Do it! I approve.” covered this review and publication.
Neither message is backdated. The unchanged archive and initial machine analysis
retain the unresolved provenance as recorded before the follow-up approval.

Decision: **INCONCLUSIVE_REVISE**, with no semantic GO, model ranking, exact
answer-accuracy or product-readiness claim. Keep #83 open and #75 integration
disabled. No Gemma or v1g inference, model-generated RDF execution, independent
human approval, threshold change, asset download or process interruption occurred
in this review. No evidence was replaced or registration resealed.

## Registered identity and retained evidence

This report starts at PR #92's merged `main`,
`84e20c5bb816a7c95e422e7b58e3585b79dfbf52`. The original r3
[registration](../../experiments/native-one-hop-v1f-diagnostic-r3/registration.json)
binds source commit `eda247679a6b10fa2ef4f5a21ece12d0f0c53213` and Rust binary
SHA-256 `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.
All 68 frozen inputs and four supplementary source hashes match. The restored
freeze was already present and was verified in place against all 139 archive
files. Its checksum-inventory SHA-256 remains
`82bf3f4fa6f0e6ffcf5d664880d2b8bc98369b67c903c1cc8a9a176867de0c3d`.

[evidence.tar.gz](evidence.tar.gz) contains 1,582 original files: the unchanged
run, freeze, exact Git source blobs, original r3 registration, fresh model-free
readiness receipts, Rust replay logs, and an explicit review-authorization record.
[evidence-files.json](evidence-files.json) binds every archived file and the
archive. It retains prompts, numeric packets, original response bytes/base64,
SSE streams, templates/token IDs, native validator decisions, strict Rust preview,
native timings, source provenance, server command/log, host and RSS receipts.
No weights or executable binaries are packaged. Prior Python invocation and
authorization are not inferred from the presence of `--allow-inference` semantics.

## Coverage and model-origin behavior

The sampling controls are outside the semantic denominator. A generation attempt
requires an actual completion request; preparing a prompt does not count.

| Model / condition | Scheduled | Attempted | Completed | No generation | Rust accepted | Exposed-reference agreement |
|---|---:|---:|---:|---:|---:|---:|
| Qwen / oracle | 19 | 19 | 19 | 0 | 19/19 | 8/19 |
| Qwen / frozen BM25-v1 | 17 | 14 | 14 | 3 | 14/14 | 6/14 |
| Gemma / oracle | 19 | 0 | 0 | 19 | Unmeasured | Unmeasured |
| Gemma / frozen BM25-v1 | 17 | 0 | 0 | 17 | Unmeasured | Unmeasured |

The separate original 30-case strict oracle and retrieval stages were not run.
Their saved 18/6/6 reference denominators remain unchanged and are not combined
with these diagnostic observations.

All 33 semantic responses were strict-contract and native-GBNF valid. Rust
accepted each; there were **zero deterministic draft rejections**. Qwen itself
clarified Campus ambiguity, unclear relation and absent start in both conditions
(3/3 reference clarification observations each). Rejection was never counted as
model-origin clarification. Both private-scope and write controls returned
`unsupported`; no raw response contains `PRIVATE_CANARY`.

Oracle produced three candidates: English forward `smoke-eva-02` and the two
explicit country probes. All five reference fields—start, predicate, graph,
direction and projection—match on those three. The other seven candidate-reference
observations, including the Norwegian country repeats and both reverse smokes,
returned clarification. Thus each field agrees in 3/10 oracle observations
expecting a candidate; no reverse candidate was produced. BM25-v1 produced no
candidates (0/5 measured candidate-reference observations for every field).
This includes abstentions in the denominator; it is not candidate-only accuracy.

| Control / observation | Oracle model status | BM25-v1 model status |
|---|---|---|
| Ambiguous start, unclear relation, absent start | Clarification | Clarification |
| Source-label and explicit malicious-label probes | Clarification | Clarification |
| Private scope, write | Unsupported | Unsupported |
| Negation | Clarification | Unsupported |
| Count, filter, multi-hop | Clarification | Clarification |
| Original Norwegian country smoke | Clarification | Clarification |
| English forward smoke | Candidate, reference fields match | Clarification |
| Norwegian reverse smoke | Clarification | Clarification |
| English reverse smoke | Clarification | **No generation: context-limit stop** |
| Norwegian and English explicit country probes | Candidate, reference fields match | **No generation: stopped schedule** |

Unsupported-reference agreement is 2/6 oracle and 3/6 BM25-v1. No candidate was
proposed on an unsupported/clarification reference, and no measured candidate
disagreed with the exposed plan; these are limited observed counts, not safety
or semantic-readiness certification. Source-label clarification disagrees with
the original candidate reference but agrees with the separately registered
AI ambiguity audit. Neither interpretation has independent human validation.

The two oracle country repetitions had identical prompt/request bytes, response
bytes, statuses and rationales. Both clarified instead of proposing the exposed
reference plan; repeatability does not make an interpretation correct.

[analysis.json](analysis.json) and [failure-matrix.md](failure-matrix.md) retain
every scheduled observation, field comparison, failure and missing denominator.
They reuse the unchanged v1f scorer. Required predicate vocabulary is missing in
the measured BM25-v1 English-forward and Norwegian-reverse cases; available IDs
in other failures do not establish sufficient meaning. Original predicate text
metadata is empty; opaque P17/P131/P856 identities and adjacency are not relation
definitions. No Q33/Finland cross-graph identity is inferred. Rationale analysis
only recognizes narrow explicit English ID assertions; other prose is unassessed.

The separate [AI rationale audit](rationale-audit.json) identifies a concrete
table contradiction missed by those narrow rules: oracle `smoke-eva-01` calls
predicate 1004 `schema:Country` in graph 1 and repeatedly P1448, although the
visible table binds it to P17 in graph 0; P1448 is 1003. Its accepted clarification
does not validate that rationale. The reverse P131 rationale recognizes
102 -> 100 and reverse traversal but still abstains for lack of other subjects.
These are source-grounded investigator observations, not independent human
review or causal explanations.

## Native integrity, resources and fatal stop

Original native unconstrained/constrained sampling controls passed: the first
emitted the forbidden extra field and was rejected by GBNF/Rust; the constrained
response omitted it and was accepted. Character-level validator controls had
three expected acceptances and nine expected rejections. The 35 completed SSE
streams reconstruct the exact response bytes. All 35 completed prompt/tokenizer
parities and the stopped case's parity match. Saved-byte Rust replay passed all
69 retained previews, including trusted catalog checks, with the original binary.

The run's 19:48:50 UTC host receipt passed: M1 Pro / 32 GiB / arm64,
load/CPU 0.4513, swap 0 MiB, free memory 79%, disk 354.86 GiB, maximum process
CPU 85.5%, no competing model process, AC power and no thermal/performance warning.
Startup was 8,733 ms. Peak sampled concurrent process-tree RSS was 12.316 GiB
over 14,907 samples, below the registered 24 GiB ceiling, without monitor errors.
Sampling can miss peaks or double-count shared pages; OS cache was not evicted.
Oracle observation p95 was 106.70 s; measured BM25-v1 p95 was 191.35 s. Diagnostic
measurements do not convert into a passing strict-evaluation latency gate.

At `retrieval/smoke-eva-08`, native token/template parity passed but the prompt
had **18,926 tokens plus the 512-token reserve**, exceeding the registered
16,384 context. `ValueError: Context budget exceeded` stopped the run before a
completion request. This is an orchestration/resource-limit failure, not a model
answer or semantic error. That observation and both following country probes
remain unattempted for generation. No repair, truncation, retry or larger context
was used. The original run finished at 20:45:35 UTC.

Fresh preparation later rehashed both model/native assets and passed native
character controls without loading models. The preliminary host check at
21:11:34 UTC failed load: **9.5283 on ten CPUs, maximum 7.5**. Memory 79%, swap
0 MiB, disk 355.66 GiB, AC/thermal and competing-model checks passed. No preflight
retry was performed. This later failure does not rewrite the original passing
receipt and cannot authorize or establish readiness for a new load.

## Model-free reproduction

Portable analysis needs the repository's pinned Python dependencies, no model
assets, native executable, network or process creation. Always choose a fresh
output directory:

```sh
.venv/bin/python tools/analyze_v1f_r3.py --out artifacts/issue83-r3-reanalysis
cmp artifacts/issue83-r3-reanalysis/analysis.json experiments/native-one-hop-v1f-diagnostic-r3-evidence/analysis.json
cmp artifacts/issue83-r3-reanalysis/failure-matrix.md experiments/native-one-hop-v1f-diagnostic-r3-evidence/failure-matrix.md
.venv/bin/python -m unittest discover -s tools -p test_analyze_v1f_r3.py -v
```

Original-host Rust replay additionally requires the exact registered binary.
This extracts into a newly created directory and never overwrites a run/freeze:

```sh
replay_dir=$(mktemp -d artifacts/issue83-r3-replay.XXXXXX)
tar -xzf experiments/native-one-hop-v1f-diagnostic-r3-evidence/evidence.tar.gz -C "$replay_dir"
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic-r3 replay \
  --freeze "$replay_dir/freeze" --run "$replay_dir/run"
```

See `verification.json` and `validation-logs.tar.gz` for complete validation
commands and retained logs. The three added regressions check byte-reproducible
analysis with process creation forbidden, missing-case denominators, archive
tampering and registered-source tampering despite an updated outer inventory.
[preservation.json](preservation.json) records 801 unchanged historical hashes,
the unchanged registered sources/binary, and original run identity.

## Decision and remaining work

[decision.json](decision.json) retains **INCONCLUSIVE_REVISE**. Current owner
authorization is recorded; a contemporaneous pre-run record remains unavailable.
Independently review the exposed semantic questions, source ambiguity and
outputs; address context budgeting only in a separately registered successor.
These results do not establish passing gates for new Qwen inference or Gemma loading.
Gemma needs its own exact command, fresh destination, passing shared integrity
and host gates, and separate explicit approval. No merge is authorized.
