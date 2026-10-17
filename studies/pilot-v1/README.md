# Pilot v1 preregistration and operator checklist (#57)

**Frozen kit; real participants 0; human attempts 0; independent task reviewers 0.**
Stage B is blocked pending actual consenting volunteers. A synthetic rehearsal,
Rust test, browser pass or coding agent can never satisfy the real-user gate.
No recruitment, enrollment, human review or research schedule is claimed here.

`protocol.json` fixes recruitment, task order, rubric and proposed iteration/stop
hypotheses before enrollment or observations. `tasks.json` fixes bilingual wording,
exact identifiers, original snapshot quad witnesses, task-specific checks,
unresolved intent/relevance ambiguity and lineage. It is AI-authored exploratory
material. Its `reviewer: null` means no actual human reference reviewer. Source
membership does not establish user intent or relevance. An operator may collect
owner-reviewed exploratory observations with that label; an independent reviewer
may be credited only if an actual person did the review. Before independently
reviewed task-gold claims, freeze a new version with attributable actual review
provenance; never add a signature retroactively to v1.

`freeze.json` pins the full kit, recording/scoring tests, original UI adapter and
assets, Rust source, lockfile/toolchain, public dataset snapshots, manifests,
discovery and policies. UI/source commit is
`9a1c663349d9594ccf7a108016ab3284046a78d3` (#55 and #56 merged).
SHA256 of `freeze.json` is the protocol identity in every form/report. Verification
rejects modified bytes. Keep this version immutable after enrollment; amendments,
new task wording/review, different build inputs or thresholds require a separate
version **before** further observations, with reasons and affected sessions.
This is a content commitment, not a timestamped external preregistry or signature.
The PR supplies the reviewer-readable publication history.

All historical #37–#53 scores, tasks and phase-0 decisions remain frozen.
These pilot prompts reuse exposed sources and some #56 walkthroughs, explicitly
labelled in task lineage. They are not fresh independent evaluation or sealed gold.
No command reads the private Ask holdout or runs/downloads a model.

## Pilot scope and setup

Recruit, if available, **5–8 voluntary adults** who plausibly use Find for analysis
or research. Seek both RDF beginners and experienced users and disclose actual
English/Norwegian proficiency, convenience recruitment and counts. Fewer people
or none is a blocker/limitation, never a reason to simulate respondents. Do not
promise a research schedule. No minors, sensitive/private datasets or employer
credentials are in scope. GEMET is excluded to keep the first pilot bounded;
adding it requires a new freeze. Sources and attribution:

- [Wikidata](../../data/wikidata/README.md): retained revision-addressed CC0 RDF;
  only `urn:graph-verity:wikidata:development` is authorized for these tasks.
- [GeoNames / datasets/world-cities](../../data/worldcities-transfer/README.md):
  CC BY 4.0, modified Nordic subset mapped to Schema.org; only the NO graph is
  authorized. City IRIs are original GeoNames IDs; administrative IRIs and RDF
  relations are importer-created. No source Norwegian labels are invented.
- `snapshot.nq`: separately identified Apache-2.0 **synthetic** ambiguity and
  shared-path fixture. Never characterize its triples as real licensed geography.

From the repository root, with pinned Rust dependencies already cached:

```sh
cargo build --locked --offline -p verity_cli
python3 tools/pilot_study.py verify
python3 tools/local_find.py
```

For the worldcities block, stop the previous server and launch:

```sh
python3 tools/local_find.py --rdf data/worldcities-transfer/snapshot.nq --format nquads --policy data/worldcities-transfer/policy.json --scope studies/pilot-v1/worldcities-scope.json --config data/worldcities-transfer/discovery.json
```

For the synthetic block:

```sh
python3 tools/local_find.py --rdf studies/pilot-v1/snapshot.nq --format nquads --policy studies/pilot-v1/policy.json --scope studies/pilot-v1/scope.json --config studies/pilot-v1/discovery.json
```

For A08 use `--policy studies/pilot-v1/clipped-policy.json` instead. All other
arguments stay the same. This deliberately constrains both rows and evidence to
1. The participant must distinguish both flags, without claiming that either
bound measures semantic completeness. A03 uses the unrestricted synthetic policy:
three paths, two distinct terminal integer terms. A02 uses the exact observed
decimal datatype; `+717710` in the source may render as `717710` in the engine.

For A05, after preview have the participant uncheck the development graph in the
scope control; observe approval invalidation, without approving a replacement.
For A06/A07 launch the Wikidata server using **private copies** of the frozen
operator inputs in `study-private/operator/`. After preview, append one newline
to the copied snapshot (A06) or lower `max_evidence` in the copied policy (A07).
Attempt the old approval; the adapter must reject the stale bundle. Do not edit
frozen files. Explain afterward that even a source-byte change invalidates the
session; a changed snapshot/policy requires a fresh server/selection/preview.
If the participant understood invalidation but the adapter failed, record the
observed task checks honestly and stop the session to investigate backend safety.

Before sessions, run the application security/browser regressions and record
`git rev-parse HEAD`, `rustc -Vv`, Python version and the UI receipt **locally**
in an operator build note, excluding the private URL/session credential. The
receipt binds actual executable, index revision, policy/config/snapshot and assets.
Use the pinned source commit/build inputs above; build differences need a new
version rather than mixing UI revisions. The kit commit itself adds only study
tooling/docs and does not alter the pinned UI/core.

## Consent, session and recording

1. Verify frozen bytes. Read [consent.md](consent.md) with the volunteer, resolve
   concerns, obtain voluntary affirmative consent, and give them their study code
   and operator contact method. No session form exists by default.
2. Create a form, choosing actual categories, for example:

   ```sh
   python3 tools/pilot_study.py init --consent --language nb --experience beginner --language-proficiency fluent --out study-private/session-01.json
   ```

3. Give a short unscored demonstration of launching, scope/role controls and
   selecting Q20. Teach controls, not rubric answers. Read **only** each task's
   `prompt` in the chosen language; keep `target`, witnesses and checks operator-only.
   Follow the frozen order exactly (F01–F11, A01–A09). Switch bundles as specified,
   including back to Wikidata between tasks. Fixed ordering and reuse cause
   learning/carryover; do not treat repetitions as independent participants.
   Ask controls are English even with Norwegian prompts: disclose this limitation.
4. Start a local stopwatch when the prompt ends; stop on completion, abandonment
   or exclusion. At 5 minutes offer to abandon; do not impose success or delete
   failure. Record elapsed whole seconds and assistance. Ask explicit optional
   confidence (1–5) for every attempt and candidate relevance (1–5) for Find.
   Null means declined/unobserved, not zero. No passive telemetry/timestamps.
5. **Before each Ask approval**, have the participant explain the actual preview:
   selected identifiers/directions, terminal projection, typed filter/count when
   present, graph/snapshot, limits, and source evidence versus truth. Record whether
   explanation preceded the decision. Do not coach a correct answer and later
   mark it unassisted. Record wrong-but-executable interpretations, including high
   confidence, even if Rust executes perfectly. Cancellation is the desired A04
   outcome. A05–A07 require no approval of a new plan.
6. Edit the generated JSON form locally using an editor, retaining its schema.
   Set `assessor` to an actual operator's random `R-` plus 16 lowercase hex digits
   and `role: owner` or `independent` truthfully. Keep any code-to-person review
   attribution outside Git and separate from participant records, with permission.
   Reuse that code for the same assessor. It is provenance, not an attestation.
   Do not create fictional reviewers. Without an assessor all checks remain null.
   Human assessment is manual; the tool never judges natural language or relevance.
7. For each task, retain `not_attempted` or record `completed`, `abandoned` or
   `excluded`. Excluded here means attempted but unusable (for example operator
   error); keep its observations/failures and original planned denominator. Stop
   before a task leaves it `not_attempted`. Every attempted task needs seconds
   and assisted true/false. Missing records remain explicitly missing in reports.
   Each rubric check is true only if the participant selected/explained the task
   target without that error; false is an observed mistake; null is unresolved or
   unobserved. Do not infer understanding from execution or a checkbox. Record
   Ask decision `approved`, `cancelled` or `no_approval` and the explanation timing.
8. Run the report on **all consenting sessions**, including incomplete ones:

   ```sh
   python3 tools/pilot_study.py report --out study-private/report.json study-private/session-01.json
   ```

The CLI accepts only strict bounded forms with fixed fields/enums, no free text,
anonymous IDs and matching protocol ID. It rejects duplicate participant IDs,
duplicate JSON keys, duplicate/out-of-order/unknown tasks, foreign protocols,
unconsented forms, extra privacy fields and mixed synthetic/human evidence.
The local editor is the recording form; there is deliberately no connection to
the UI, browser, automatic query capture, hosted analytics or public uploader.
Permissions are 0600 for newly generated forms/reports, and `study-private/` is
Git-ignored. Ignore rules are not encryption or protection from force-add. Keep
the machine private; inspect staged paths before every commit. Do not commit forms.

## Rubric, denominators and reporting

Task success requires completed status, every check true, an actual assessor and
for Ask an observed pre-decision explanation and the requested decision. No rating
is required for completion. Assisted success is reported separately. Null checks
remain unassessed; abandonment and exclusion cannot succeed. A failed check
remains a failure even on an abandoned/excluded attempt. Missing/not-attempted
tasks stay in the planned denominator. There is one planned attempt per task per
participant; retries are assistance within that attempt, not new independent rows.

`incorrect_selection` counts tasks with all entity/predicate checks observed and
at least one false. `misunderstanding` counts tasks with all nonselection checks
observed and any false. Individual error dimensions also retain their own observed
denominators. `confident_wrong` counts confidence >=4 plus any observed false
check, including wrong decisions, divided by attempts with confidence supplied.
`confidence_unassessed` warns that other confidence-rated attempts remain partly
unassessed; absence of detected error there is not evidence of correctness.
Find low relevance is rating <=2 / rated Find attempts, separate from any historical
top-k accuracy. No automated rank score becomes a human relevance judgment.

Reports include planned/attempted/completed/abandoned/excluded/missing tasks,
assistance, timings, failure categories, confidence distribution, task and
participant denominators, actual assessor roles, and separate language, language
proficiency, RDF experience and task-type outcomes. Participant `completed_all`
means all planned tasks assessed successful, not just all forms filled. Reports
contain no individual IDs or quotations. Breakdowns overlap; never sum them as
independent samples. No intervals from repeated tasks are justified for this
tiny convenience sample; no uncertainty bounds or general safety claims are made.

Preregistered hypotheses: at least 5 actual participants, >=80% unassisted success
per planned task, >=80% correct fully assessed comprehension, with missing or
unassessed observations blocking readiness interpretation. **One confident wrong
interpretation stops a proposed release pending investigation.** These are
iteration hypotheses, not a powered release test. Descriptive checks are emitted;
even all passing can never set `release_go`. Do not retrofit these thresholds.

Keep these conclusions separate: backend execution correctness, candidate relevance,
intent understanding, formal confirmation, RDF provenance and factual truth.
After actual observations, a human report must explain actionable UI/vocabulary
problems and observed failure categories without identifying people. Recommend
improving UX, restricting scope to expert users if supported by the separate
experience outcomes, iterating retrieval if relevance is poor, or stopping a
proposed release. The deterministic report suggests investigation; it cannot
invent qualitative findings or decide that expert-only release is justified.

All generated reports stay private pending disclosure review. Publish only
nonidentifying aggregates with limitations, no-match/ambiguity outcomes, actual
N/planned/attempted/completed counts, exclusions and recommendations. If volunteers
remain unavailable, publish that blocker and **0/N**, keep #57 open, and describe
the kit/rehearsal separately. Never use the rehearsal as the actual pilot report.

## Retention and rehearsal

At session close, remind participants of withdrawal using their code. Remove
unnecessary operator notes immediately. Delete a withdrawn form immediately;
regenerate private aggregates from the remaining consented forms, disclose aggregate
attrition without preserving identifying records. Delete all session files and
backups within 30 days; no automated backup/export or collection is implemented.
The operator is responsible for this deletion checklist and publication review.

```sh
python3 tools/pilot_study.py rehearse --out artifacts/pilot-rehearsal.json
python3 -m unittest discover -s tools -p 'test_pilot_study.py' -v
```

Rehearsal builds synthetic forms in memory, validates form/order/rubric arithmetic,
and writes only an aggregate labelled `kind: rehearsal`, **human participants 0,
human task attempts 0**. It performs no enrollment, model inference, network
access or sealed holdout read. Outputs use exclusive creation; choose a fresh path
for repeats. Full CI includes the frozen-kit check, this rehearsal, Python/Rust,
format, Clippy, application HTTP/browser security and source/reference regressions.
