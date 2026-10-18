# Controlled one-hop trial (#74)

The [retained result](../reports/issue-74-one-hop-trial/README.md) is
**INCONCLUSIVE_REVISE: host contention before inference**. Both official pinned
CPU candidates were handled identically. The tooling records that permitted
blocker outcome, freezes the exact #72 evaluation questions through #73 BM25,
and scores saved drafts without model loading or query execution.

Ordinary CI discovers `tools/test_one_hop_trial.py` through the existing Python
runner. With the pinned Rust toolchain and existing `tools/requirements.txt`:

```sh
cargo build --workspace --locked --offline
.venv/bin/python -m unittest discover -s tools -p test_one_hop_trial.py -v
.venv/bin/python tools/one_hop_trial.py verify
```

Verification hashes the frozen source/configuration, independently replays all
30 authenticated Rust vocabulary packets, audits original RDF and checks the
complete machine-readable blocked decision. It reads no model files and performs
no downloads or inference. It intentionally fails on input drift; retain this
run and create a newly versioned freeze instead of rewriting the evidence.

The separately invoked macOS host inventory needs read-only access to `sysctl`
and `ps` (outside the local sandbox where necessary). It retains executable paths,
owners and resource use, without process arguments, environments or credentials.
Each destination must be new. For a new run under this unchanged protocol:

```sh
mkdir -p reports/issue-74-local-continuation
.venv/bin/python tools/one_hop_trial.py preflight \
  --host reports/issue-74-local-continuation/host.json
# STOP if any host blocker is present. Do not start either model.
```

The remaining commands below perform only offline preparation/verification and
are safe even when inference is blocked. Asset hashing reads the already retained
#48 native and Q4 files without loading a model, compiling a backend or acquiring
weights. Missing or changed assets fail verification.

```sh
.venv/bin/python tools/one_hop_trial.py assets \
  --out reports/issue-74-local-continuation/assets.json
.venv/bin/python tools/one_hop_trial.py freeze \
  --folder reports/issue-74-local-continuation/freeze
.venv/bin/python tools/one_hop_trial.py decision \
  --folder reports/issue-74-local-continuation/freeze \
  --host reports/issue-74-local-continuation/host.json \
  --out reports/issue-74-local-continuation/decision.json
```

`decision` only records a blocked host. A passing preflight does not authorize or
launch inference. A dedicated-host continuation must first implement and freeze
the explicitly new runtime/prompt/grammar variant, run all live controls, measure
the required startup/tokenization/generation/resource costs and retain actual raw
requests/responses/logs. This change makes no claim that these steps completed.

For saved public outputs, use one JSONL record per exact evaluation case, with
`id`, `origin` (`model` or `fixture`), `runtime_status` and original `raw_response`.
The existing #72 optional separately approved saved execution record is supported.
No missing case, repaired JSON, invented model output or implicit approval is
accepted. Keep model runs separate from fixture controls and use a fresh output:

```sh
.venv/bin/python tools/one_hop_trial.py score --stage retrieval \
  --records /path/to/saved-evaluation.jsonl --out artifacts/issue74-score.json
```

The scorer uses #72's trusted **benchmark-only resolution fixtures** for Rust
preview after reading the saved output. Those resolved starts/host blocks are not
model input or a question-only resolver. It independently rejects retrieval-stage
IDs absent from the frozen packet and separates vocabulary misses, malformed
contracts, wrong executable drafts, direction/constant/scope diagnostics,
model-origin statuses and strict semantic-plus-answer agreement. Cancellation
leaves answers unmeasured. No live inference or user-facing execution command is
provided; #75 remains a separate implementation and authorization boundary.
