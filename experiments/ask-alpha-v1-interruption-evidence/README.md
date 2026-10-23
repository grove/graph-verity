# Consumed Ask Alpha v1: model-free forensic report

**INCONCLUSIVE_REVISE. Cause of interruption not established. No inference was
performed by this investigation. The consumed registration remains unusable.**

Inspected `grove/graph-verity` at merged PR [#107](https://github.com/grove/graph-verity/pull/107),
commit `321dee43b8ef245cc6d86fd8e1aa664b2169d8b9`, reviewed head
`a992b4628aa205950d2d6351a7c430a764d9cdd0`. The original working tree was clean.
This directory adds evidence copies and analysis only. It changes no historical
artifact, source, registration, executable, limit, retry rule or integration.

## Identity and preservation

The [inspection receipt](inspection.json) contains observed filesystem metadata,
SHA-256 values, all 64 frozen schedule identities, source comparisons and the
limited current process snapshot. [raw/attempt.json](raw/attempt.json) and the
four files in [raw/run/](raw/run/) are byte-for-byte copies of the complete
inspected attempt evidence. The original ignored paths remain untouched.

| Identity | Observed SHA-256 / commit |
|---|---|
| Registered source | `74d840108e65e5152f0a2f1542bb4baedaeafbbc` |
| Registration | `55af85f8f5c15e45b46653d78e6e92cfe5c03a84fabfcf75be622e63c8386464` |
| Frozen archive | `4c094d907b8debd770a0c4c9d564cc339deb91302c166ed90164f2ad34a3998a` |
| Attempt ledger | `076532fcac9ba5e96d6fc29812f25ec82ec1ad6d0a33be452a013f5eb382a883` |
| Run record | `9b18882ce00325d8f0191e901b14427151cc7bdaea0abf6e5b95787064671f9d` |
| Original run checksums | `3b6c6667816ed54e570b497ecc442bb24550d0dcf70bfd85ed8c601ce16d644e` |

The ledger names that exact registration and says `consumed_before_model_load`.
All three entries in the original run manifest match; its directory contains
exactly those three payload files and the manifest. All **203 registered inputs**,
**200 frozen payload files**, **201 archive members including `checksums.json`**,
and the pinned Rust binary match their frozen identities now. Six inspected
runner/helper/test files also match the merged Git objects. These are current
byte-consistency checks, not authenticated proof of the earlier process or command.
Large model/runtime assets were not rehashed; their attempted verification did
not leave a receipt. Preparation receipts are not evidence of attempt-time checks.

## Reconstructed timeline and last stage

Times below are original local filesystem wall-clock metadata rendered in UTC,
not application start/stop events. They cannot establish signal provenance.

| UTC, 2026-10-23 | Observation |
|---|---|
| 20:04:18 | GitHub reports PR #107 merged. |
| 20:05:36.263066 | Ledger birth time; last modification 20:05:36.263294. |
| 20:05:36.263352 | Run directory birth time. |
| 20:05:59.496033 | `run.json` birth time; last modification 20:05:59.496174. |
| 20:05:59.657050–20:05:59.657974 | Score, failure table, then checksums created/written. |

There are about **23.23 seconds from ledger birth to run-record birth**, and
23.39 seconds to final manifest modification; total invocation duration is unknown.

The [runner](../../tools/ask_alpha_trial.py#L150-L189) verifies sources and the
committed registration, acquires the exclusive lock, consumes the ledger, creates
the run directory and initializes all rows before its guarded work. The first
guarded operation is asset verification. Tokenizer recount, grammar controls,
host admission, RSS monitoring, runtime construction and startup follow in order.

| Stage | Evidence and conclusion |
|---|---|
| Source/registration guards and ledger creation | Ledger and initialized state are consistent with passing these on the unchanged runner path; no timestamped guard receipt survives. Current hashes independently match. |
| Asset verification | **Last localized window:** at or immediately before its first guarded call; no `assets.json` exists, so successful completion is not evidenced. Exact helper/suboperation unknown. |
| Tokenizer recount / grammar / host preflight | No tokenizer command/stdout/stderr/counts, grammar directory or host receipt. On the inspected path these stages follow writing the asset receipt and were not reached. |
| Runtime construction / model startup | Runtime counters and `startup_ms` are absent; no server command/log or RSS stream. Consistent with `runtime` remaining `None`, before construction. |
| Request dispatch | No requests directory, no control rows, all 60 semantic rows unattempted. No dispatch through the registered runner is supported. |
| Failure finalization | Run, score, failure table and matching checksums survive. Their order agrees with the runner's `finally` block. |

The first [asset helper](../../tools/one_hop_trial.py#L97-L121) hashes retained
upstream weights and native files before writing its first receipt; the
[wrapper](../../tools/native_one_hop.py#L179-L198) then checks runtime sources.
The inner helper reads the older two-variant config (Qwen and Gemma), despite this
trial's Qwen-only completion schedule. These are file hashes, not model loading.
Substantial silent hashing is therefore possible before `assets.json` appears;
neither a particular file nor a hang/resource fault is established here.

## What `KeyboardInterrupt` establishes

**Confirmed record:** `run.json` contains `status: blocked_or_failed`,
`failure: "KeyboardInterrupt: "`, `inference_performed: false`, empty controls,
and zero RSS samples. The [exception handler](../../tools/ask_alpha_trial.py#L244-L268)
formats the exception type/message, re-raises `KeyboardInterrupt`, and still writes
the final records. It does not retain traceback, stage, PID, launch command,
signal receipt/sender, exit status or application timestamps.

**Supported conclusion:** an early caught `KeyboardInterrupt` followed by completed
finalization explains these bytes on the inspected source path. A Python SIGINT
is compatible with that exception; it does not identify an operator action.
An external supervisor/terminal signal or explicit exception is also compatible.
There is no retained command transcript to distinguish them. The CLI's explicit
SIGTERM handler instead raises `SystemExit('Operator cancelled')`; the retained
record does not match that ordinary handler path. No timeout or host-gate failure
is recorded. None of these observations proves the underlying cause.

The inspected `ask-local-alpha/work` runner logs predate this ledger and name the
mock-only timeout test. They are preparation/test evidence, not this invocation's
stderr. Their metadata/hashes are retained in the receipt. No invocation stderr
or process-lifecycle log was found in the inspected attempt/related-work paths.
The empty shared lock is old and carries no owner/history information.

The current process-name snapshot found no named llama-server, but did find
unattributed Python interpreters, including two starting at 20:05:44 UTC (the raw
`ps` times are host-local, UTC+02). Names alone cannot identify them. A later
snapshot cannot prove no earlier model process existed. **No model startup by
this runner is supported; actual historical host-wide process activity is unknown.**
Scoring finalization can itself construct a model-free Rust bundle, so finalization
does not imply that no subprocess of any kind existed.

## Accounting and robustness finding

The source-bound reconstruction is **0 attempted / 0 completed / 0 failed or
timed-out completion requests / 64 unattempted**, comprising four controls and
60 semantics. There is one interrupted invocation, not a failed model response.
Native attempt/completion counters are **absent**, not measured numeric zero;
zero dispatch is inferred from the stage and untouched schedule. `executions: 0`
alone is not a completion counter. All semantic outcomes remain null, including
30 Norwegian and 30 English cases and every forward/reverse/minimum-scope case.
There is no semantic or latency result. Automated references are not human gold.
The formatter's fixed “No model invoked” text is not independent telemetry.

**SUPPORTED diagnostic gap:** early interruption consumes the registration but
leaves no precise stage/traceback or explicit pre-runtime request accounting.
This prevents determining cause from the durable evidence. Source integrity and
the no-retry ledger worked as designed; consumption before loading is intentional,
not a defect. The existing [runner timeout test](../../tools/test_ask_alpha.py#L133-L188)
mocks assets and interrupts during generation; it does not cover this early path.
No runtime reproduction was performed, and no failed guard is being relaxed.

**Smallest corrective action — PROPOSED, NOT IMPLEMENTED:** separately review
writing an initial state with zero request counters and append-only stage/time
events before each prerequisite, plus an exception traceback and cancellation
classification that does not infer its sender. Add one mock-only asset-stage
`KeyboardInterrupt` test proving final evidence persists, runtime is never
constructed and the ledger remains consumed. Preserve existing limits and zero
retries. These diagnostics would localize a future interruption; identifying its
external sender also requires a timestamped launcher stdout/stderr and lifecycle
record. Do not modify or reuse this freeze to add diagnostics.

The supplied later owner statement “I do” is context, not a timestamped original
launch receipt; no authorization event or missing preceding question is invented.
Unresolved: original launcher/command/exit status, interruption source, precise
asset suboperation and identity of the contemporaneous Python processes.

## Reproduction and limits

From the repository root, the following **standard-library-only** inspection
checks the published bytes, scheduled identities, accounting and registered
sources. It never imports project modules or starts a backend:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json
p = Path('experiments/ask-alpha-v1-interruption-evidence')
receipt = json.loads((p / 'inspection.json').read_bytes())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
prefix = 'artifacts/ask-alpha-v1/'
for row in receipt['original_evidence']:
    if 'sha256' in row and row['path'].startswith(prefix):
        assert sha(p / 'raw' / row['path'][len(prefix):]) == row['sha256']
checks = json.loads((p / 'raw/run/checksums.json').read_bytes())
assert {f.name: sha(f) for f in (p / 'raw/run').iterdir()
        if f.name != 'checksums.json'} == checks
run = json.loads((p / 'raw/run/run.json').read_bytes())
assert run['failure'] == 'KeyboardInterrupt: ' and not run['controls']
assert len(run['rows']) == 60
assert all(r['outcome'] == 'unattempted' for r in run['rows'])
assert 'generation_attempts' not in run and not run['inference_performed']
schedule = receipt['scheduled_requests']
assert len(schedule) == len({r['id'] for r in schedule}) == 64
assert sum(r['kind'] == 'semantic' for r in schedule) == 60
assert {n: sha(Path(n)) for n in receipt['registered_input_sha256']} == receipt['registered_input_sha256']
assert sha(Path('docs/ask-alpha-v1/registration.json')) == receipt['registration_sha256']
assert sha(Path('docs/ask-alpha-v1/freeze.tar.gz')) == receipt['archive_sha256']
print('PASS: published evidence, accounting, registration, archive and 203 source inputs')
PY
```

This check and the receipt's independent original/freeze/source comparisons passed.
The first reproduction attempt used `hashlib.file_digest`, unavailable in the
subprocess Python 3.9 interpreter; [its failure](validation-attempts.json) is retained.
Only this new report's hash snippet was made compatible; original sources and
evidence were unchanged.
Final validation also rechecked that original bytes and recorded modification
metadata were unchanged. Project code, tests and builds executed: **NONE**.
No tokenizer recount, grammar controls, model loading, Rust preview, holdout access,
full validation pipeline or semantic rescoring was performed. Delegation: none.
No terminal-session store, general user history or historical OS signal audit was
searched. Checksums detect byte disagreement; they cannot authenticate causality
or exclude unrecorded external file/process activity.

Keep **#83 open**, **#75 live integration disabled**, and **INCONCLUSIVE_REVISE**.
The next useful product action is to review the diagnostic change before any
separately reviewed fresh registration; no retry, replacement registration or
inference is authorized by this report.
