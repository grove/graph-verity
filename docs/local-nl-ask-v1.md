# Experimental local NL Ask v1 (#75)

**Opt-in prototype; no product/release GO. Live inference remains blocked.**
The new Ask-first browser entrypoint implements the model-free saved-draft replay
stage of #75. It does not understand new questions. The default launcher reports
`model_unavailable` and offers optional BM25 Find expert mode. It starts no model,
downloader, network API, telemetry or prompt upload.

[#74's retained result](../reports/issue-74-one-hop-trial/README.md) stopped both
candidates before inference because the host failed its resource gates. There is
also no validated new-contract runtime/prompt/grammar adapter. Consequently this
change deliberately has no live-model switch. A passing dedicated-host trial and
separately reviewed adapter are prerequisites for the live integration stage.
The earlier #48 runner does not implement this contract and cannot be substituted.
Neither the bilingual demo nor CI is evidence of live NL understanding.

## Launch and stop

Build with the pinned Rust toolchain and retained dependencies. Python 3.11+ and
its standard library suffice for the launcher. No model weights are required.

```sh
cargo build --locked --offline -p verity_cli
# Default: honest unavailable state, with optional Find expert mode.
python3 tools/local_nl_ask.py
# Or explicitly enable the model-free saved-draft demonstration:
python3 tools/local_nl_ask.py \
  --saved-drafts-demo examples/nl-ask-v1/saved-drafts-demo.json
```

Run one local instance. Open its private terminal URL in one browser tab. The URL
contains a session credential in its fragment; keep it private. The browser removes
the fragment from history after loading. A second tab/session revokes the first
tab's lease and reviews. Stop with **Ctrl-C**, which removes private temporary
copies and stops the listener. Nothing is hosted or published. Only `127.0.0.1`
and `::1` are accepted binds; an OS-selected port is the default.

The CLI is an operator launcher for the browser, not an unattended question runner.
To use another retained source bundle, specify all of its inputs explicitly:

```sh
python3 tools/local_nl_ask.py \
  --rdf studies/nl-ask-v1/development/snapshot.nq --format nquads \
  --policy studies/nl-ask-v1/development/policy.json \
  --scope studies/nl-ask-v1/development/scope.json \
  --config studies/nl-ask-v1/development/discovery.json
```

The operator supplies the RDF, format, policy, authorized graph scope, discovery
source/license metadata and executable. These inputs are copied privately and
their original bytes rechecked on every request and after subprocesses. The scope
and snapshot are visible but cannot be supplied by a draft or changed in the
browser. Changing any input requires restarting and a new preview. Sources remain
inert text, including source URLs, labels, rationale, datatypes and RDF literals.

## Demonstration journey

1. Select a saved demo question and its English/Norwegian language. The entire
   original question goes unchanged to #73's gold-free, graph-authorized BM25
   packet builder. All demos are prominently marked **no live inference**.
2. Read the untrusted saved proposal and choose an **exact original entity** from
   the packet's graph-qualified candidates. There is no selected default or model
   confidence shortcut. An alias can have several candidates. Choosing a different
   entity from the saved draft fails preflight: edit/clarify rather than silently
   rewriting the draft. Every changed choice needs a new Rust preview.
3. Compare your original question with the **entire authoritative Rust preview**
   side-by-side. It includes exact start/predicate IRIs, direction, graph,
   projection, snapshot, plan digest, row/evidence/time bounds and limitations.
   Source/license metadata is shown directly below. The explanation remains
   explicitly model-authored/unverified; a valid plan can misunderstand the question.
4. Only **Approve this exact interpretation and run**, as a separate deliberate
   action, redeems the random single-use token. The server rebuilds the authorized
   packet, #72 catalog and full Rust preview under the current bundle, then invokes
   the existing read-only Confirmed Ask executor with its exact approval digest.
5. Results retain exact original term IDs, literal datatypes/languages, original
   directed source triples **per answer**, snapshot, named graph, provenance and
   license. Rows and evidence have separate completeness flags; an answer whose
   evidence was clipped is explicitly marked incomplete. No rows means no matches
   under that plan/snapshot, never proof of real-world nonexistence.

The public replay includes Norwegian **“Hvilken hovedstad har Norge?” → Q20,
forward P36 → Q585**, English **“Which country lists Oslo as its capital?” →
Q585, reverse P36 → Q20**, and a deliberately wrong inverse for **“What is the
capital of Norway?”**. The inverse is displayed without being auto-executed;
cancel it. These are synthetic engineering fixtures on retained real RDF.

The exact question **“Hva er hovedstaden i Norge?”** currently lacks P36 in its
whole-question BM25 packet. Its saved fixture reports clarification rather than
adding gold vocabulary or silently rewriting the input. The count question reports
unsupported. New questions report that no saved draft exists; a timeout or invalid
draft is an error, not a successful unsupported inference. Find is a separate
optional action and invalidates any Ask review.

## Boundaries and receipts

The new versioned adapter/assets/routes reuse #56's loopback HTTP parser,
same-origin credential, bounded bodies, CSP, private operator bundle, 15-minute
tab lease and two-minute review expiry. Legacy execution endpoints are unavailable
in this server. Old Find v1/v2, #40 Confirmed Ask and frozen #57/#58 code and hashes
are unchanged. There are no dependencies or core contract changes.

The bridge assigns #72 numeric IDs from the ordered, authenticated #73 packet:
graphs are 1-based in packet scope order; entity and predicate IDs are separately
1-based in their candidate order. Only these retrieved rows enter the frozen
catalog. The raw draft is passed unchanged to Rust (including duplicate fields);
Rust rejects arbitrary IRIs, unknown IDs, graph/role mismatches, unrecognized
fields, extra steps, filters, counts, scope/policy/snapshot/approval authority,
SPARQL and writes. The packet is independently rebuilt before every preview and
approval. Stored JSON alone has no authority.

Approval binds the server-held exact request/preview, original question, packet,
raw draft and exact user resolution to a random token and current tab lease.
The token is consumed **before** validation. Cancel, Escape, Enter, edits, changed
candidate, Find/reranking, new tab, navigation/hiding, expired review/session,
changed source/policy/binary, failed preflight and token replay cannot redeem it.
A closed connection detected after preflight also prevents execution. Once a
deliberate approval has passed all checks and execution has begun, closing a tab
cannot undo that read-only execution. The serial loopback server bounds concurrent
work to one Rust process; each child has a 45-second wall deadline, and Oxigraph
also enforces the operator's timeout.

The full result receipt keeps these separately:

- original question and language;
- complete retrieved packet with its ID, source/ranking revisions and provenance;
- packet-local table and unchanged `nl-ask-draft-v1` raw proposal;
- `proposal_origin: saved_draft_demo`, `inference_performed: false`;
- explicit operator resolution/approval, exact Rust digest and single-use status;
- authoritative Rust execution, per-answer original source statements and clipping.

The existing executor still reports `origin: manual`; this does **not** erase the
separate proposal provenance. Receipts stay in the local browser and server memory;
requests and questions are not logged or persisted automatically. Copy the complete
receipt only if you deliberately want to retain it, respecting the source scope.

Saved-demo files use `version: nl-ask-demo-v1` and a `cases` array containing only
`question`, `language`, `packet_id`, and the original JSON string `raw_draft`.
An exact question/language and current packet-ID match is mandatory. They contain
no resolution choice, plan, execution result or approval token. They are local,
operator-provided fixtures, never an inference backend or unreviewed answers.

## Verification and remaining blocker

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python -m unittest discover \
  -s tools -p test_local_nl_ask.py -v
.venv/bin/python tools/verify_pre_llm.py
```

The standard Python runner discovers these tests without loading model weights.
They replay #72 development fixtures through new question packets, preserve literal
metadata and injected source text, test actual HTTP/Chrome forward and reverse
journeys, and cover wrong inverses, ambiguous resolution, unauthorized IDs/private
data, clipping, edit/cancel/Enter/Escape, changed bundles, timeouts, disconnects,
expired/replayed tokens and protected rendering.

The [#75 report](../reports/issue-75-nl-ask/README.md) records the engineering
result and blocker separately. Actual Norwegian/English **inference → independent
confirmation → source result** remains unattempted pending #74's viable runtime.
This is not product readiness, human usability evidence or unattended Ask approval.
