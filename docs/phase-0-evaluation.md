# Phase 0 evaluation framework (issue #8)

The framework works without model weights. The formal baseline decision is **NOT READY**.
Working evaluation infrastructure is an engineering result, separate from parser quality,
independent semantic validation, holdout readiness and production readiness.

## Commands from a clean checkout

Use Python 3.12 and the repository's pinned Rust toolchain. No extra Python dependency
was introduced; RDFLib remains needed by the existing reference checks.

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
cargo build --locked -p verity_cli
# Reassess immutable PR #20 evidence, without starting a model:
.venv/bin/python tools/phase0.py report --out artifacts/phase0/baseline
# Revalidate/reexecute the original raw outputs through the current Rust evaluator:
.venv/bin/python tools/phase0.py replay --out artifacts/phase0/replay
.venv/bin/python tools/phase0.py verify artifacts/phase0/baseline/manifest.json --check-inputs
.venv/bin/python tools/phase0.py assess artifacts/phase0/baseline/summary.json
.venv/bin/python tools/phase0.py compare artifacts/phase0/baseline artifacts/phase0/replay
.venv/bin/python tools/verify_pre_llm.py
```

Every output directory must be new. `summary.json` contains every case and family;
`summary.md` contains the quality and decision tables. The checksum-enveloped
`manifest.json` identifies scoring version, exact splits, source revision/dirty state,
Rust and Python environment, config, model/prompt/grammar/schema/compiler/graph/policy/
benchmark/split/lock hashes, original input reports, and generated output hashes.
The original inference environment and model/runtime build receipt remain explicitly
**inherited**, separate from the machine running the report generator. No model is
invoked by `report`, `replay`, `verify`, `assess`, `compare`, or normal CI.

`verify` checks the manifest envelope and output bytes; `--check-inputs` additionally
checks the current checkout/input files against their recorded identities. This
lets comparisons verify archived outputs after code changes without pretending the
new checkout matches an old run. Checksums establish content identity, not signatures
or reviewer identity. Keep old run directories and Git revisions. `compare` refuses
different scoring versions; explicitly replay saved outputs under a new policy
instead of rewriting an old score. Reports from failed runs preserve diagnostics.

### Public development inference (optional heavy command)

```sh
# Explicit online acquisition/build, only when assets are not already prepared:
.venv/bin/python tools/local_parser.py prepare
cargo build --locked -p verity_cli
# Offline, CPU only; creates a fresh output directory and owns a loopback server:
.venv/bin/python tools/local_parser.py run --out artifacts/local-parser/new-development-run
# Reassess that run, preserving the original files:
.venv/bin/python tools/phase0.py report --evidence artifacts/local-parser/new-development-run --out artifacts/phase0/new-development-report
```

The pinned runner verifies grammar/runtime enforcement with live controls before
public inference. It automatically archives a completed report and checksum manifest;
interrupted runs retain `run.json`, case artifacts and `failure-manifest.json`.
The latter describes an incomplete attempt, not a complete model-quality result.
Host permissions may be needed for `sysctl`, process RSS inspection and loopback.
No model downloads occur during `run`. The assets and model are described in
[the original experiment](local-parser-experiment.md).

## Three paths, one semantic evaluator

1. `verity evaluate ... dev|transfer_dev OUT`: oracle reference typed IR → existing
   validator/compiler → SPARQL → Oxigraph bindings/evidence and independent reference
   SPARQL checks. Fixture abstention bookkeeping is never model prediction accuracy.
2. `local_parser.py run`: Norwegian question → authorized catalog/oracle vocabulary →
   grammar-constrained CPU model → strict response decoding → independent Rust
   validation. JSON syntax, response contract, structural components and rejections
   are separate measurements. Oracle-provided vocabulary remains the baseline.
3. The same run continues through compiled SPARQL, scoped execution and evidence to
   compare binding sets. `phase0.py replay` feeds the saved raw strings over the same
   `evaluate-local` bridge, so there is no second IR validator/compiler or Python
   semantic evaluator. Its model identity says `saved_output_replay_no_inference`.

Replay timing measures local replay work, **not inference or a new model experiment**.
Historical failures and raw strings remain in the original reports; new summaries
reference their case IDs and SHA256 values. Rust reports now retain actual execution
bindings, SPARQL, evidence, scope, stage timings and unchanged interpretation/truth
labels. Rust's validation and compiler are intentionally one operation; the reported
`validation_compile_ms` includes both. The executor revalidates at its own boundary;
its separate `validation_ms` is not added twice to `pipeline_ms`.

## Metrics and limits

All supported questions remain in structural/answer and macro precision/recall/F1
denominators. Rejected, malformed, timed-out and falsely abstained supported questions
score zero; they do not disappear. Rates include numerator, denominator and descriptive
Wilson 95% intervals. Macro P/R/F1 also include deterministic 1,000-resample bootstrap
intervals (seed 7). Families containing only abstentions have answer metrics
`not_applicable`, rather than artificial 100% accuracy. Small/correlated template
samples do not prove population safety, even with zero observed errors.

Structural comparison is ordered and variable-name-sensitive. Component diagnostics
cover entities, predicates, edge directions, variables, operators, typed literals,
numeric/date operands, aggregation (only COUNT DISTINCT is supported), grouping,
HAVING, projection, graph scope, snapshot and limit. Matching empty components can
inflate individual component rates. A historical report lacking a newly added
component is `not_measured`; replay measures it. This conservative comparison may
reject semantically equivalent plans. Exact answer bindings are scored independently,
including variable names. A structurally different plan returning identical rows
therefore earns an answer match but remains a structural disagreement.

Scoring v2 retains raw `exact_answer` binding-set agreement and adds
`complete_exact_answer`: exact-answer quality gates require both matching bindings
and `complete_within_scope: true`. A truncated answer cannot pass those gates even
if its retained rows happen to match the reference. Historical matching outputs
without retained execution/completeness evidence are unavailable for this gate;
use `replay` to measure them. Older archived reports stay on scoring v1 and cannot
be directly compared with v2 without explicit rescoring.

JSON and Markdown reports count complete/truncated query results separately from
complete/incomplete evidence for returned rows. These execution limits do not
measure whether the graph contains every relevant real-world fact. Missing-fact
classifications remain unknown. A frozen-reference verification error has its own
`reference_validation` failure stage, separate from model disagreement.

`wrong_plan_executed` is a **structural reference-disagreement proxy**, not expert
adjudication. Observed unflagged user-facing false confidence is `not_measured` because
there is no complete interface under test. The gate does not replace that measurement
with the proxy. Rejected scopes/IDs/snapshots are safety rejections, not successful
unauthorized executions. A complete disclosure audit is unavailable and is not zero.

Expected and actual abstention statuses are retained. A correct abstention requires
matching the expected status; an accidental `parsing_error` is not a correct
`unsupported` response. Failure to abstain includes malformed outputs, while a
separate count identifies attempted candidate plans on expected-abstention cases.

Retrieval is disabled (`not_applicable`, `oracle_vocabulary`), not a measured retrieval
success. The reporting boundary can retain an explicit failed-retrieval diagnostic;
no retrieval engine or retrieval quality was invented. JSON generation, schema,
Rust rejection, compiler, execution/timeout, reference and semantic/answer disagreements
remain distinct. Empty results are query outcomes, never proof of real-world falsity.
No independent per-case completeness annotations exist; missing-fact classifications
remain unknown even when a question family mentions missing data.

## Timing and memory

New Rust reports separate catalog construction, validation/compilation, query and
evidence. The Python runner separately records oracle vocabulary selection, model
round-trip and runtime-reported prompt/prediction durations. Stage distributions
include sample counts and `not_measured` when historical evidence lacks that stage.
Warm end-to-end p50/p95/p99 include failed attempts and exclude the first case in each
fresh server. Total cold first answer adds server startup and Rust/snapshot startup;
startup is also reported separately. Cold service timing excludes the preceding asset-hash and grammar-probe preflight; it is not total command wall time. OS page cache is not evicted, so **process cold
is not uncached disk cold**. Prompt prefix caching is disclosed. Report generations,
retries, failures and timeouts with their scope; quality failures are not backend failures.

The sampler follows the runner's process descendants (including startup), every
200 ms. Sampling begins after grammar probes; probe/preparation peaks are not measured. It includes sampling overhead, may double-count shared pages and miss short
spikes. The OS child lifetime high-water mark is a separate measurement. CPU/OS/
architecture/logical cores, four threads, physical RAM and disabled acceleration
are recorded. Historical PR #20 RSS used the three known runner/server/Rust processes;
its 1.43 GiB observation is preserved, not silently upgraded to the new sampling method.
No deployment CPU has been separately designated. No CI-host timing is substituted.

## Numerical proposals, approval and freeze

[The numerical proposals](../configs/phase-0-gates.proposed.json) remain unchanged.
On 17 October 2026 the owner approved these exact experimental budgets, protocol v3,
and the measured M1 Pro target for an `ai_reference_only` experiment in conversation.
[The recorded decision](../configs/phase-0-approval.json) pins their canonical JSON
digests, the existing owner waiver, experiment assets and source revision
`d3984494c9dd4a6938eb2a3591f6cd1d13768172`. The target is Apple M1 Pro, macOS 26.6.2
arm64, 10 logical cores, 32 GiB RAM, four CPU threads and no accelerator. This is an
experimental target, not a claim that the original Linux/16 GiB proposal was measured.

The approval status is `owner_approved_pending_external_split_integrity`: the required
external split-integrity review and its SHA256 are still missing. It is **not a
completed preregistration**, and `freeze` must still fail. Do not fill the absent
evidence with a checksum of a template or a self-certified independence assertion.
The proposal files retain their original proposal labels; this separate decision
records what was approved without rewriting their bytes or historical evidence.

[The protocol](../configs/phase-0-protocol.json) versions scoring and
adds explicitly proposed sample minimums: 100 supported and 20 abstention questions
per dataset, five supported cases per family. The owner approved keeping these
formal minimums unchanged; they do not make zero-error observations proof of
negligible risk. The 60-case AI
candidate alone cannot satisfy an independent, expert-validated GO.

[The approval record](../configs/phase-0-approval.json) now includes the owner's
identity/provenance and approval recording time, exact gate/protocol hashes, actual
hardware and known experiment identities. Its missing external evidence must be
supplied before it can become an approved freeze input. Hardware fields are
`cpu_model`, `os`, `architecture`,
`logical_cores`, `threads`, `system_ram_bytes`, `accelerator`, and
`measurement_configuration`. Experiment fields are `model_sha256`,
`tokenizer_identity`, `quantization`, `runtime_revision`, `runtime_binary_sha256`, `compiler_binary_sha256`,
`prompt_sha256`, `grammar_sha256`, `compiler_revision`, `schema_sha256`,
`split_integrity_evidence_sha256`, and `independent_review_evidence_sha256`.
The tokenizer is embedded in the pinned GGUF; record that identity and Q4_K_M
quantization explicitly. A clean committed checkout and matching pinned identities
are required. No command creates owner approval or human gold-review records.
`reference_policy` defaults to `independent_human_review` (also for older approval
records without the field). An explicitly approved `ai_reference_only` experiment
instead requires `experiment_identity.owner_ai_gold_waiver_sha256` matching the
exact bytes of [the owner risk acceptance](phase-0-ai-gold-risk-acceptance.md),
and does not require or manufacture `independent_review_evidence_sha256`.
All other experiment, hardware, split-integrity and numerical-approval requirements
still apply. Approval of an AI-reference experiment cannot satisfy formal GO,
even if a supplied summary incorrectly claims all prerequisites passed.

```sh
# Only after actual human approval; this command currently fails closed:
.venv/bin/python tools/phase0.py freeze --approval configs/phase-0-approval.json --out /tmp/phase0-freeze-v1.json
# A later revision requires incremented approval revision, change_reason and prior receipt:
.venv/bin/python tools/phase0.py freeze --approval /tmp/actual-approval-v2.json --previous /tmp/phase0-freeze-v1.json --out /tmp/phase0-freeze-v2.json
```

The freeze snapshots approvals, thresholds/protocol, split manifest and public sealed
commitment, graph/model/prompt/grammar/schema/compiler/runtime identities, target CPU,
measurement configuration, source commit and inference config **before** external
locked evaluation. Later threshold changes require a new revision and linked receipt;
old runs keep their gate/protocol bindings and cannot retroactively become preregistered
passes. Commit threshold/experiment changes with reasons; do not replace old receipts.
The frozen inputs also include the owner waiver and external-bundle verifier source,
so either changing invalidates admission. Protocol v3 records this evidence-class
choice while retaining scoring v2.

The current owner decision is bound to the exact source revision above. Once the
external review exists, preserve the pending record, create a separate completed
approval file, and run `freeze --approval /path/to/completed-approval.json` from a
clean checkout of that pinned revision. A newer source/configuration requires a new
versioned decision rather than silently changing `compiler_revision`. The separate
post-freeze operator authorization remains required. The real sealed bundle has
not been opened or evaluated by this approval-recording work.

### Recovering the missing external review

The [issue #5 preparation record](https://github.com/grove/graph-verity/issues/5)
states that the unencrypted `graph-verity-sealed-holdout-candidate.zip` was delivered
directly to the owner outside GitHub. A filename-only search of the common local
document/download/project locations and temporary directories did not locate that
ZIP or a task-specific split-integrity review. This does not establish that no
external copy exists. The public commitment is not itself a completed review.

Recover the original delivery in an isolated reviewer/operator environment. A reviewer
needs the sealed candidate, the public benchmark/split records and its authoring/group
lineage before making these assertions. The reviewer may supply only this metadata
to the development session, with actual reviewed values replacing the nulls:

```json
{
  "benchmark_sha256": "653c2fe30fd0911f91c17db1ace9f46ae5b36ce5bffb0212dd37e9dbcf822e6b",
  "public_cases_disjoint": null,
  "public_lineage_disjoint": null,
  "exposed_groups_excluded": null,
  "reviewer": null,
  "provenance": null
}
```

Keep failed or uncertain findings explicit. Do not set all three assertions true
without evidence; public Schema.org examples already prevent an unseen-ontology
claim. This is an integrity review, not a fabricated human gold-review ledger or an
expertise claim. If lineage independence cannot be established, the current locked
path must remain unavailable; disclose the limitation and separately decide whether
to commission a fresh holdout. No reviewer has been invented or contacted by this work.

`assess` verifies its source report manifest and deterministically explains every
configured threshold. Unknown gates fail closed. All approved gates/prerequisites
are conjunctive. Observed unauthorized execution/disclosure or prohibited execution
means **STOP** even without approval. With complete approved evidence, unmet quality/
performance requirements mean **REVISE**; passing everything means **GO**. Missing
approval, preregistration, independent evidence, actual hardware or measurements
means **NOT READY**, with descriptive failed gates still visible. Existing public
reports can never automatically supply the missing prerequisites.

## External holdout protection and remaining operator work

No private holdout was accessed during this implementation. Only its public checksum
commitment is used. Both public Rust evaluation paths and the core evaluator refuse
non-development split names; rejection happens before reading a CLI benchmark file.
Ordinary CI has no inference, private download, private artifact or gold mutation.

The optional metadata-only `authorize-locked` command checks an approved freeze,
unchanged complete input hashes, approval-before-freeze ordering, explicit later
operator action/provenance, exact committed benchmark/bundle hashes, split/case count,
and an affirmative external split-integrity assertion. It creates an exclusive
checksum receipt without opening any payload:

```sh
.venv/bin/python tools/phase0.py authorize-locked --freeze /tmp/phase0-freeze-v1.json --operator-record /tmp/actual-external-operator-action.json --out /tmp/phase0-admission.json
```

The operator record requires `action: authorize_one_external_locked_evaluation`,
`operator`, `authorization_provenance`, `authorized_at`, `freeze_sha256`,
`benchmark_sha256`, `bundle_sha256`, `split`, `cases`, and
`split_integrity_verified: true`. No example approval/signature is fabricated.

The metadata receipt does not itself start inference. The separate isolated adapter
performs the complete preflight and actual execution, only for an explicitly authorized
external operator. **Do not invoke this command with the real bundle in a coding-agent
session, public CI, or a shell whose output is publicly captured.**

```sh
# All private paths are external; no actual approval or bundle is supplied here.
.venv/bin/python tools/locked_phase0.py --freeze /tmp/phase0-freeze-v1.json --operator-record /tmp/actual-external-operator-action.json --admission /tmp/private-admission.json --bundle /private/operator/sealed.zip --reviews /private/operator/reviews.json --split-integrity /private/operator/split-integrity.json --out /private/operator/phase0-run-1
```

It checks the frozen source commit/clean checkout, compiler and runtime binaries,
pinned assets, exact CPU/OS/architecture/cores/RAM, integrity file hash,
actual bundle/benchmark hashes,
case counts/snapshot/split and public/private case-ID disjointness. The externally
reviewed integrity record requires `benchmark_sha256`, `public_cases_disjoint`,
`public_lineage_disjoint`, `exposed_groups_excluded`, `reviewer` and `provenance`.
Software cannot infer lineage independence or expert identity; the approver must
establish those assertions before freezing. `independent_human_review` additionally
requires a frozen external review-ledger hash and complete case-bound human assertions;
omitting `--reviews` fails closed. A metadata receipt at the same path
cannot be reused; cross-host one-shot custody is still the operator's responsibility.

For the owner-waived exploratory path, approve a new record with
`reference_policy: ai_reference_only` and the exact `owner_ai_gold_waiver_sha256`
before freezing. After the separate operator authorization, run the same isolated
command **without `--reviews`**. Supplying a human-review ledger in this mode is
rejected. It still verifies the unchanged sealed commitment and split-integrity
evidence, and labels its private run and assessment **AI-reference agreement — not
expert-validated semantic accuracy**. The private human-review ledger and public
`review --require-reviewed` checks are untouched. No approval has been created
and no real locked run has been performed by implementing this path.

Only an isolated private *transport copy* uses `transfer_dev` internally to reach the
existing public Rust bridge; the private adapter restores the original `locked_holdout`
identity and original benchmark SHA in its final reports. The transport digest and
mapping are explicitly recorded. No public examples are relabeled as holdout evidence.
All question/prompt/raw-output/evidence and exception details stay under a fresh private
output directory (mode 0700) outside the repository. Terminal output is sanitized;
the adapter refuses CI. The real external bundle was never supplied or opened in
this implementation; authorized-path tests use synthetic fixtures and mock inference.

The private report includes a gate assessment, with missing oracle regression,
independent transfer or UI measurements unavailable rather than inferred from that
single run. It audits retained scopes, snapshot identities and evidence graphs through
the same audit as public reports: an observed violation forces STOP; observing none
does not establish a complete disclosure audit. AI-reference runs explicitly keep the
independent-human-review prerequisite false. An independent target run is not by itself enough for GO. Human publication
must select non-sensitive aggregates separately; there is no automatic private artifact
uploader. If a holdout is exposed to development, commission a fresh test set.

The [owner waiver](phase-0-ai-gold-risk-acceptance.md) permits exploratory development
and a separately preregistered AI-reference comparison;
it does not replace expert gold for formal GO, threshold approval, target-device approval or
production readiness. The human-only review ledger remains unchanged.

## Issue #8 status and the next decisions

Complete: public reproducible evaluator/replay, path and failure separation,
component and binding scores, denominator/uncertainty regression coverage, stage
measurement hooks, versioned gates/protocol/approval/freeze/admission mechanisms,
manifest verification/comparison, CI demonstration and truthful negative baseline;
owner approval of exact experimental numerical/protocol budgets and the M1 Pro target.

Outstanding: external split-integrity evidence and immutable freeze, new measurements
on the approved target, independent specialist review/evaluation for formal GO, an authorized external locked
run, and measured user-interface false confidence/disclosure behavior. Keep
issue #8 open for these acceptance boundaries; merging infrastructure does not finish
them. [The baseline](../reports/phase-0-baseline/summary.md) misses proposed 95%
structural, exact-answer and correct-abstention thresholds and the 10-second historical
warm p95 budget. A small false-abstention count of zero cannot establish safety.

Recommendation for **the PR #20 measured configuration**: revise model/scope and
abandon unattended unrestricted Ask with that configuration. Keep deterministic
exact identifier/label resolution and manual typed plans, which already use scoped
Rust validation/execution. Issue #9 should make interpretation confirmation and
execution-evidence/truth limits explicit and measurable. Issue #10 should choose a
bounded experiment/Find-first/manual-plan continuation separately from any formal
feasibility or production GO. A negative, reproducible evaluation is a successful
harness run and an unsuccessful model-quality result.
