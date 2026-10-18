# #75: model-free confirmation harness; live runtime blocked

The separately versioned [local NL Ask v1](../../docs/local-nl-ask-v1.md) adds the
Ask → retrieved packet → exact entity choice → authoritative Rust preview →
separate approval → bounded values/original evidence workflow. It changes no
frozen study files, Rust execution contracts or default BM25 behavior.

**Inference performed: false. Live full-chain completions: 0. Product/release GO:
none.** This report is an engineering replay, not actual live model evidence.

## Reproducible blocker

The prerequisite [#74 report](../issue-74-one-hop-trial/README.md),
[decision](../issue-74-one-hop-trial/decision.json) and
[host record](../issue-74-one-hop-trial/host.json) retain both model candidates as
unattempted after host preflight. At the recorded 2026-10-18 16:57:44 UTC preflight,
load was 18.96 on 10 logical CPUs (gate 7.5), with a competing virtualization
process at 150.3% CPU (gate 150%). This is historical retained evidence, not a new
claim about current contention. #74 supplied no validated `nl-ask-draft-v1`
adapter/template/grammar or integration approval. Its evidence can be verified
offline with `.venv/bin/python tools/one_hop_trial.py verify`.

Consequently the normal launcher truthfully returns `model_unavailable`, and
only an explicit `--saved-drafts-demo` flag enables replay. No candidate is loaded,
downloaded, silently substituted or exposed as a working interpreter. Dedicated
host time and a supported, controlled runtime trial remain necessary for live
integration. Model-free tests cannot establish that feasibility.

## Replay outcomes

Reproduce with the commands in the operator guide. The committed
[saved drafts](../../examples/nl-ask-v1/saved-drafts-demo.json) are synthetic,
packet-ID-bound fixtures on the retained Wikidata snapshot:

| Original question | Fixture interpretation | Confirmed RDF result |
|---|---|---|
| Hvilken hovedstad har Norge? (nb) | Q20, forward P36 | Q585, Oslo |
| Which country lists Oslo as its capital? (en) | Q585, reverse P36 | Q20, Norway |
| What is the capital of Norway? (en) | Deliberately wrong reverse P36 from Q20 | No execution until separate approval; cancellation tested |
| Hva er hovedstaden i Norge? (nb) | Clarify: P36 absent from actual packet | No execution |
| How many capitals are there? (en) | Unsupported count | No execution |

The harness also replays #72 development cases `dev-01`, `dev-06`, `dev-10`,
`dev-18` with freshly retrieved question-only packets. Gold drafts are explicitly
remapped **after retrieval for fixture testing only**, never used to fill packet
membership or auto-resolve a user-facing proposal. Original bindings, integer
datatype, reverse direction, injected source annotation and original evidence
must match #72. The original evaluation and sealed holdout are untouched.

The model-free HTTP and headless Chrome tests require explicit approval for both
bilingual positive journeys and assert zero execution for aborted/expired/edited
reviews, wrong inverse without approval, stale tabs/policy/source/binary/packet,
unknown or unauthorized IDs, malformed/duplicate drafts, prohibited model fields,
private canaries, replay, timeout and disconnection. Per-answer evidence clipping
is tested independently of row clipping. Session/asset receipts identify the new
adapter and inert assets. All source/model text is rendered with `textContent`.

No semantic accuracy, measured human comprehension, false-confidence reduction,
live startup/latency/RSS or production reliability is claimed. #76 and a successful
live trial remain separate work; #40 and all earlier negative evidence stand.
