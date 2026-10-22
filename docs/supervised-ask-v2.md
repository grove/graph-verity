# Supervised Ask v2 — model-free vertical slice

**Experimental, opt-in, loopback only. INCONCLUSIVE_REVISE.** This demonstrates
question → saved interpretation → authoritative Rust preview → separate approval
→ read-only RDF values → original graph evidence. It does not understand fresh
questions. All interpretations are synthetic saved fixtures, explicitly labelled
in the UI and separately retained in the execution provenance. There is no live
model adapter, model switch, asset download or network inference.

## Run the demonstration

```sh
cargo build --locked --offline -p verity_cli
.venv/bin/python tools/supervised_ask.py \
  --saved-drafts-demo examples/nl-ask-v2/saved-drafts-demo.json
```

Open the private terminal URL in one tab. Its fragment credential is removed
from browser history. Select a saved question, or type its exact text/language.
Stop with Ctrl-C. A new tab revokes the old tab's reviews. No questions or receipts
are persisted automatically. Keep the private URL and source-bearing receipts
within the authorized local context.

The selected dataset is the existing `studies/nl-ask-v1/development` bundle,
snapshot `sha256:48f0c13ddab7ce2a7881509192be30c1fe08693b4e7df5991e68cb302c20561b`.
It has Wikidata university facts, GeoNames city facts and GEMET concepts in three
separately authorized named graphs. A plan uses **one graph only**, with exact
plan scope. No cross-graph inference is supported. Source and licenses are in
`discovery.json` and the original study manifest. The Campus aliases and hostile
label are explicitly synthetic overlays. These bytes are unchanged.

Try these paths:

1. **English, multiple values:** “Which official websites does the University of
   Tromsø list?” Choose Q279724, build the Rust preview, inspect outgoing P856
   and the exact graph/snapshot. Only then click **Approve this exact interpretation
   and run**. Two original website IRIs appear, each with its P856 source triple.
2. **Norwegian, multiple language-tagged literals:** “Hvilke offisielle navn har
   Universitetet i Tromsø?” Review outgoing P1448; deliberate approval returns
   the three original names with en/nb/nn metadata and source witnesses.
3. **Reverse:** “Which institution has https://uit.no as its official website?”
   Choose that exact website, inspect **Incoming: returned value → predicate →
   start**, approve and receive Q279724 with the original forward source triple.
   No inverse predicate is invented.
4. **Clarify:** “Which country is Campus in?” shows both graph-qualified identities
   and cannot be approved. Edit to the separately saved Norwegian country question
   “Hvilket land ligger Universitetet i Tromsø i?”; choose the intended original
   entity and get a new independent preview. The system does not rewrite the old
   proposal or infer which Campus you meant.
5. **Missing vocabulary:** the saved postal-code question explains that this
   relationship is absent from the authorized vocabulary. It asserts no answer.
   **Unsupported:** the saved count question reports the one-hop values limit.
   **Unknown fresh question:** an honest “no saved draft” message, never canned NL
   understanding. Find remains an optional supporting surface.
6. **Incorrect but executable control:** “Which country is the University of Tromsø
   in?” deliberately uses P131 (administrative location) rather than P17 (country).
   Cancel it. If explicitly approved in the engineering demonstration it returns
   Tromsø/Q26087: a valid, nonempty result that fails the question. Confirmation
   and successful execution do not prove understanding.
7. The saved reverse-university-website question returns no rows; this establishes
   only no matches under the exact plan/snapshot. The published-label fixture
   displays injection-bearing source text inertly. The inception fixture preserves
   the original dateTime datatype. Row/evidence clipping remain distinct.

## Implementation and authority

The new adapter, routes `/api/nl-ask-v2/`, assets and fixtures are separately
versioned. Existing Find, NL Ask v1, Rust contracts, native adapters, frozen source
fingerprints and historical evidence are untouched. V2 reuses `local_nl_ask.Bundle`
and its exact review/approval/Confirmed Ask bridge, plus the existing loopback
transport. This task explicitly authorizes this **fixture-only** reuse; no new
execution authority or change to approval architecture is needed.

V2 uses existing #82 `question-vocabulary-packet-v2-neighborhood` discovery:
whole-original-question entity seeds plus witnessed predicates, within current
authorized scope. It is a new named retrieval condition, not a change to frozen
BM25-v1. Before every preview and approval the complete packet is independently
rebuilt in Rust and compared with the server-held packet. Python does not attempt
to serialize canonical bytes for the Rust neighborhood-replay command. Its numeric
IDs remain packet-local, separately numbered per role, and graph-qualified.
Rust validates the actual source/catalog and exact start resolution again.

Only the existing confirm route can invoke the read-only executor. It consumes
the random single-use review token **before** revalidation and requires the same
live tab, unexpired review, unchanged complete Rust preview and unchanged source,
policy, scope, config and executable. The server owns the exact request; browser
requests cannot edit the plan or provide scope. Edits, cancellation, new questions,
new tabs, expiry, Find and stale/replayed tokens invalidate approval. Enter alone
cannot approve; Escape cancels. Generation/fixture lookup never auto-executes an
answer plan. Authorized vocabulary discovery inspects source neighborhoods before
approval; it grants no answer execution authority. A closed transport detected
during preflight prevents execution; closing a tab after approved execution starts
cannot undo that read-only execution.

Results retain manual executor origin **and** separate `saved_draft_demo` proposal
origin, `inference_performed: false`, question/language, full packet, numeric table,
unchanged raw draft, exact Rust approval digest and operator decision. Evidence
uses original subject/predicate/object, graph, snapshot, license and revision;
source labels and URLs are inert text, never HTML or active links. Rust limits and
45-second child deadlines are inherited. Errors/timeouts assert no answer; once
confirmation is consumed it cannot retry execution. Only one local Rust subprocess
runs at a time. There is no arbitrary query, count/filter or two-hop generation.

## Evaluation and remaining gates

[Fresh review materials](../examples/nl-ask-v2/review/protocol.md) contain 24 new
NO/EN questions and separate source, system and usability packages. All human
judgments and actual fresh-system fields are **pending**. Human evidence is zero;
this public source-derived preparation is not a pristine holdout. Metrics and
stop rules are predeclared before any new model generation. Model-free CI and
fixture browser replay establish engineering behavior only.

[Compiler assessment](supervised-ask-v2/compiler-assessment.md) explains
each of #105's ten incompatible reverse references and proposes an independent
probe-generator follow-up. No compiler check or historical reference is changed.
[Validation receipts](supervised-ask-v2/README.md) record checks, failures,
reruns and historical preservation.

The next smallest live milestone is a separately authorized, registered local-model
preview trial on these frozen questions after independent Phase A review, with
actual NO/EN users and fresh host/resource admission. Connecting its fresh drafts
to this approval/execution path remains a **separate reviewed and authorized #75
integration change**. #83 stays open; #75 live integration stays disabled. No
product readiness, release, merge or human evaluation completion is claimed.
