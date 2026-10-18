# #74: blocked before inference; INCONCLUSIVE / REVISE

The required host preflight stopped this trial. **Neither candidate was loaded or
run. There is no model accuracy, latency leaderboard or integration approval.**
This is the resource-blocker outcome permitted by #74, not a completed inference
comparison. The historical #48 attempts and all earlier evidence are unchanged.

At **2026-10-18 16:57:44 UTC**, the Apple M1 Pro / 32 GiB / 10 logical CPU host
had load averages **18.96 / 14.92 / 16.83**. The frozen load gate is at most
0.75 per logical CPU (7.5 on this machine). A separate user-owned virtualization
process used **150.3% CPU and 6.53 GiB RSS**, exceeding the competing-process
CPU gate of 150%. Swap was **0 MiB**, system memory free was **67%**, and disk
space passed. This is CPU contention, not a repetition of #48's swap exhaustion.
No other process was stopped or modified to improve the result.

[host.json](host.json) retains complete read-only command outputs, macOS/build,
CPU/GPU, memory pressure, disk and process ownership/executable inventories.
Process arguments and environments were not collected. RSS is a host snapshot,
not a model measurement. No process startup, concurrent model RSS, HWM sum,
generation/tokenization, thermal/power or end-to-end latency was measured.

[decision.json](decision.json) keeps **30 cases × two stages × two candidates =
120 unattempted outcomes**. Each stage retains 18 supported, six clarification
and six unsupported cases. Model rates and performance measurements are null;
unattempted cases are neither model abstentions nor parser failures. All seven
required live control groups are explicitly unattempted. The decision binds the
host record, asset evidence and input freeze.

## Frozen public inputs and retrieval finding

[freeze/](freeze/) binds the exact #72 evaluation split and schema, all current
Rust source hashes through #73's index identity, graph/snapshot/policy/provenance,
question-only retrieval budgets, raw packets, source witnesses, runtime/model
identities, proposed CPU generation budgets and numeric engineering gates.
The code commit and complete relevant input hashes are recorded. No evaluation
question, gold reference or ranking was revised in response to these packets.

The existing #73 whole-question BM25/top-20 retriever was applied to all **30
new #72 evaluation questions**, without reference IDs in the retrieval request.
All packets were saved and checksummed before reference scoring. The
[coverage report](freeze/coverage.json) independently audits original source
triples, roles, labels and graph-qualified membership. At k=20:

| Vocabulary membership | Covered / required |
|---|---:|
| Start entity | 18 / 18 |
| Predicate | 6 / 18 |
| Both required IDs | 6 / 18 supported cases |

The other **12/18** supported cases lack the required predicate. This is a
retriever coverage limitation, not measured model failure. No directional
reference was passed to retrieval or added to the reference membership file;
this report's directional-coverage denominator is zero. Raw packets retain
bounded observed navigation; they do not establish semantic direction accuracy.

The oracle vocabulary is the entire bounded, source-audited #72 catalog, with
observed labels and distractors. Gold supplies no step, operator, expected status,
answer row or resolved start to either model context. Retrieval contexts retain
the actual authenticated #73 packet plus a numeric mapping into the same catalog
namespace. `oracle-source.nq`, references and coverage are **audit-only**, never
model input. Context files are not native templated prompts or evidence of
runtime compatibility: no new-contract backend/template/grammar was exercised.

## Assets, offline scoring and continuation boundary

[assets.json](assets.json) records fresh full-byte SHA-256 verification of both
official pinned native checkpoints, tokenizer/config/template files, retained
Q4_K_M files and runtime executables against #48's preparation receipts. It also
records the runtime source archive, original build/conversion commands and
environment, F16 intermediate hashes, licenses and complete upstream revisions.
Native files plus quantized weights occupy 25,109,482,843 bytes for Qwen and
31,333,158,651 bytes for Gemma; these are selected persistent assets, not whole
environment disk totals. No weights are committed or downloaded. Original legal
material remains in [#48's archive](../issue-48-grounded-models/README.md).

[replay-controls.json](replay-controls.json) contains clearly labeled **fixture**
serialized drafts. Ordinary Python CI automatically replays them through Rust
preview, checks the decision and source-audited packets, and exercises wrong
inverse direction, dropped start, graph scope, prohibited fields, duplicate
fields, truncation, timeouts, inert malicious labels and stage-missing IDs.
These controls are not actual-runtime grammar tests or model inference. The
offline scorer separates strict structural interpretation from saved exact typed
RDF answer sets; coincidentally correct answers cannot rescue a wrong plan.
Fixture statuses do not count as model abstentions. Saved execution claims need
the existing exact approval/plan/snapshot/scope identity and remain unauthenticated
operator evidence. The scorer never approves or executes a proposed query.

The [protocol](../../configs/one-hop-trial-v1.json) fixes semantic/answer gates
17/18, model clarification 5/6, model unsupported 5/6, at most one false positive,
zero timeouts/truncations/safety violations, p95 end-to-end at most 120 seconds
and sampled concurrent process-tree RSS at most 24 GiB, separately per stage.
An incomplete comparison is inconclusive/revise; a complete inadequate run is
defer. Passing permits only a supervised opt-in #75 experiment.

A continuation needs a **new run directory on a dedicated, passing host** and an
explicit new-contract runtime variant with frozen prompt/GBNF and native-token
parity, grammar, reverse-edge, injection, repeat and source/scope controls before
any scored weight inference. This blocked run deliberately adds no untested live
inference adapter. CPU remains four threads, zero GPU layers and one concurrent
task. Metal support is unverified and requires a separate variant and table.
Do not invoke #48's v1 runner as if it implements this new contract.

The public gold is AI-authored, with **zero independent human reviews**; source
audits do not establish question faithfulness. The sealed external Ask holdout was
not accessed. Find and Confirmed Ask have no new model or execution connection.
See [reproduction instructions](../../docs/one-hop-trial.md).
