# Automated Ask evidence and experimental solo alpha

**INCONCLUSIVE_REVISE. No new inference, no #75 live integration, no execution of
model-generated RDF, no independent human judgments. #83 remains open.**

This is an additional automated development track authorized by the owner. It
reuses the merged PR #106 supervised Ask v2 and its public 24-question preparation,
without filling or changing any pending human fields. Unavailable reviewers do
not prevent source checks, failure measurement, browser safety tests or preparing
a preview trial. Automation cannot close the human-comprehension gate.

[Benchmark and scoring contract](../../benchmarks/ask-alpha-v1/README.md) provide
60 NO/EN questions, 29 supported source-derived plans, 13 determinate non-execution
outcomes and 18 unresolved references. The original development snapshot, original
archives, references, historical registrations and execution rules are preserved.
The only existing file changed is the browser test's opt-in extension hook.
No engine, frontend, approval adapter, source metadata or runtime rule is changed.

## What existing model evidence establishes

PR #105's [retained first evidence](../../experiments/predicate-diagnostics-v1-first-evidence/README.md)
is the relevant observed baseline, not the synthetic score in this PR:

- 126 scheduled requests; 78 attempted, 77 completed, one timeout, 48 unattempted.
- Explicit-IRI construction matches 49/60 exposed five-field references: 32/34
  forward and 17/26 reverse. All witnessed paths match; disagreements are empty
  paths. Three accepted candidates flip reverse to forward.
- Ten reverse empty references are incompatible with the unchanged compiler's
  literal-range/class contract. PR #106's [compiler assessment](../supervised-ask-v2/compiler-assessment.md)
  explains them; this benchmark includes type-compatible empty paths and does
  not weaken those checks or repair historical denominators.
- Only 6/31 natural-language metadata pairs complete. Both arms match 3/6 exposed
  references on those pairs; no superiority follows. No completed paired reverse
  comparison exists. All later live unsupported/clarification/injection controls
  remain unattempted, not passed.
- Retained rationales call inception P571 "date of birth" and official name P1448
  "date of death" without supplied meanings; another calls website IRIs literals
  despite source usage. This is source-bound investigator evidence, not human
  judgment. One model treats an omitted literal answer as missing plan vocabulary;
  values need not be enumerated as start entities to project literal answers.
- Peak sampled process-tree RSS was 12.835 GiB. Completed observation median was
  103.310 seconds, maximum 285.788 seconds; the next request timed out under the
  unchanged 300-second bound. These are not evidence of interactive alpha latency.

The new benchmark's question-only retrieval covers required numeric bindings for
**28/29 supported cases**. `alpha-08` asks for Norway by name, but the retained
snapshot has Q20 without that label; the packet lacks its start ID. This is a
retrieval/identity limitation. Supplying Q20 explicitly is a separate successful
retrieval condition in other questions, not a silent repair to alpha-08.

## Smallest architecture worth testing

| Capability | A: existing five-field draft | B: deterministic assembly from three choices |
|---|---|---|
| Model choices | start, predicate, graph, direction, values projection | authorized start, predicate, direction |
| Host guarantees | Rust checks all IDs, graph bindings, type compatibility and scope | derive graph from matching authorized entity/predicate bindings; fix output to values; then same Rust checks |
| Reverse | original object is start; same predicate; return subjects | same; swap traversal direction, never create an inverse predicate |
| Wrong relation/entity | can remain executable | can remain executable |
| Wrong direction within one graph | can remain executable | can remain executable |
| Missing numeric vocabulary | cannot recover an absent choice | cannot recover an absent choice |
| Ambiguous/unlicensed meaning | model must clarify; not solved by schema | model must clarify; not solved by assembly |
| Measured comparison | existing retained five-field evidence | synthetic controls only; no paired model evidence |

`assemble` is a small feasibility function in offline evaluation tooling. It
rejects extra keys, nonnumeric/missing/cross-graph choices, derives the graph,
retains the original predicate and fixes projection. It is not a new planner or
live adapter. Synthetic graph-drift controls show its mechanical guarantee;
synthetic wrong-predicate/direction controls still pass Rust and fail semantic
reference agreement. The synthetic arm totals deliberately include different
failure controls, so even paired fixture scores are not architecture accuracy.

**Test A next.** It already matches the product's contract and retained native
runtime. A single 60-question neighborhood-v2 + licensed-definition arm measures
the actual question path without an oracle arm, broad matrix, new model or query
planner. B is worth a separate paired trial only if A's observed errors concentrate
in graph/output construction. B cannot solve unjustified relationship meanings.

## Predeclared alpha gates

These are criteria for an **experimental solo-developer** alpha, set before new
model results. They grant no release or integration authority. Apply semantic
criteria both to the full benchmark and to any explicitly declared smaller scope;
report every excluded family. Do not drop failures after seeing answers to produce
a whole-benchmark pass. A smaller scope is a separately named product boundary.

| Evidence layer | Required observation |
|---|---|
| Engineering safety | Full model-free pipeline and focused real-browser tests pass. Zero execution without fresh deliberate exact approval; zero stale/replay/edit/cancel/expired execution; no injection action, unauthorized scope or fabricated error answer. |
| Source integrity | All active supported references have licensed source definitions, exact graph-qualified witnesses or type-compatible empty paths, complete vocabulary bindings and inspectable provenance. Full benchmark currently misses alpha-08's start. |
| Automated semantic evidence | Complete 60 semantic outcomes, no failed/time-out/unattempted cases. At least 27/29 five-field matches overall; at least 90% separately for each language and forward/reverse stratum. Report numerators/denominators, including all missing cases. |
| Wrong but executable | Zero observed determinate wrong accepted plans; zero candidates on unresolved/missing-vocabulary/unsupported cases. Also publish known-error lower bound over all Rust-accepted candidates and all scheduled questions. Small samples do not establish a population error bound. |
| Conservative outcomes | 23/23 predeclared clarification dispositions (18 unresolved + five absent authorized predicates), eight/eight unsupported operations. These are agent-reference outcomes, not independently proven ambiguity judgments. No invented predicate meanings or source/graph contradictions in source audit of every completed rationale. |
| Graph and direction | No unauthorized/cross-graph binding and no direction mismatch in any in-scope candidate; a correct current answer cannot excuse a wrong interpretation. |
| Evidence | Original IRIs, language/datatype literals, exact graph/snapshot/license and source triples inspectable in all deterministic fixture answers. Empty, row-clipped and evidence-clipped messages accurate. No live answer-accuracy claim from a preview-only run. |
| Runtime/resources | Existing M1 Pro/32 GiB CPU admission gates unchanged; zero retries; each completion ≤300 s and sampled process-tree RSS ≤24 GiB. For alpha usability: report process-cold load/first draft separately, warm p50 ≤30 s and p95 ≤120 s with counts; report p99 descriptively (60 is a small sample). Host contention or missing monitoring means inconclusive, not a pass. |
| Human comprehension | **0 reviewers, 0 participants, 0 comprehension observations. Unmeasured.** Browser tests prove behavior, not that users understand or detect wrong plans. |

Minimum useful first scope: one authorized Wikidata development graph, explicitly
identified University of Tromsø/Q279724, **forward official websites P856 and
official names P1448**, distinct terminal values, NO/EN wording. Require all eight
supported cases in those two families to match, all safety/clarification/unsupported
controls to pass, and resource gates to pass before even considering that scope.
This is a possible future solo experiment, not readiness claimed by this PR.
Country/date/admin-location and reverse families are measured expansion candidates;
exclude all unsupported operations and unresolved meanings from candidate execution.
Existing Find and saved-fixture Ask remain the available product paths today.

If A guesses relationships despite definitions, narrow to explicit entity and
operator-chosen relationship with deterministic assembly; fresh NL may suggest a
choice but cannot claim understanding. If only graph/output construction fails,
try B on identical paired questions with its own registration. If reverse fails,
ship the experimental scope as forward-only; do not invent inverse properties.
If latency fails, retain Find/manual/saved-fixture Ask; do not hide timeouts or
start an unspecified prompt-tuning loop. If retrieval fails, require an explicit
entity choice/IRI before interpretation in a separately reviewed change.

A future solo alpha still needs separate explicit #75 integration authorization
and must visibly state its experimental limits. A broader product/reliability or
safe-human-understanding claim additionally requires independent questions,
source/semantic judgments and genuine comprehension/false-confidence observations.
No human evidence is fabricated or substituted here.

## Browser and model-free verification

The established headless Chrome suite traverses question, interpretation, Rust
preview, separate deliberate approval, RDF values and original source evidence.
The new opt-in extension adds real typed-date rendering, server rejection after
replay/edit/expiry, a disclosed network-failure simulation, and real Rust row and
evidence clipping under separate restrictive saved-fixture policies. The isolated
expiry server uses a two-second lease; production's 120-second limit is unchanged.
All source/fixture origin labels remain intact. Original Python boundary tests
cover server timeout/truncated output, new tabs, stale source/binary/policy,
unsupported/clarification, Host/Origin/session and packet tampering.

The trial runner has a mock-only fatal-timeout/no-retry test: the first simulated
request times out, its original fragment survives, all later requests remain
unattempted, and the fresh ledger cannot be reused. CI never loads a tokenizer,
model, native inference runtime or sealed holdout. Exact tokenizer output is
validated from the committed preparation archive using standard JSON and hashes.
See [trial protocol](trial.md) and [validation receipts](validation.md).
