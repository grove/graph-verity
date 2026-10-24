# Assisted Ask v1

Opt-in, local, structured choices. **INCONCLUSIVE_REVISE.** No model is loaded,
called or downloaded. Live #75 inference stays disabled; #83 stays open.

```sh
# Separate build preserves any historically registered target/debug/verity binary.
cargo build --locked --offline -p verity_cli --target-dir artifacts/assisted-ask-build
.venv/bin/python tools/assisted_ask.py --binary artifacts/assisted-ask-build/debug/verity
```

Open the private single-tab URL printed in the terminal. Choose English or Norsk
(bokmål), select **University of Tromsø / Universitetet i Tromsø (Q279724)**,
then **Official websites / Offisielle nettsteder** or **Official names /
Offisielle navn**. Select **Preview selected operation separately**, review the
operation and authoritative Rust preview, then deliberately approve that exact
operation once. Cancel or Escape revokes the review; changing inputs requires a
fresh preview. Stop the server with Ctrl-C. No questions or receipts are saved
automatically. Keep the private URL and source-bearing receipts local.

The result shows original RDF values, observed labels when available, original
IRIs, language tags and datatypes. Expand the evidence section for original
subject/predicate/object triples, named graph, snapshot, source revision,
licensing, independent row/evidence completeness and the full execution receipt.
Source strings and URLs are inert text. Empty results mean no stored matches for
that operation and snapshot, never real-world nonexistence.

## Exact supported contract

| Choice | Original RDF identity |
| --- | --- |
| Entity | `http://www.wikidata.org/entity/Q279724` |
| Official websites | `http://www.wikidata.org/prop/direct/P856` |
| Official names | `http://www.wikidata.org/prop/direct/P1448` |
| Named graph | `urn:graph-verity:nl-ask-v1:development:wikidata` |
| Snapshot | `sha256:48f0c13ddab7ce2a7881509192be30c1fe08693b4e7df5991e68cb302c20561b` |
| Operation | One forward hop; all distinct stored terminal RDF values; no filter |

This is the existing authorized `studies/nl-ask-v1/development` snapshot, including
its disclosed synthetic label overlays. Its policy/config are retained unchanged.
The plan scope is **only the original Wikidata graph**, even though the bundle
contains separately authorized GeoNames and GEMET graphs. No union is constructed.
The retained Wikidata facts give two website IRIs (`https://uit.no`,
`https://en.uit.no/startsida`) and three official names tagged en/nb/nn. These are
snapshot observations, not a claim about current websites or institutional names.

Definitions and direct-claim mappings are checked against the original archived
[Q279724 source](../studies/nl-ask-v1/sources/Q279724.ttl), with the retained
[source audit](../benchmarks/ask-alpha-v1/source.json). P1448 denotes official
names in official languages; P856 denotes an official page URL, including retained
former/dead sites. No numeric catalog alias or prompt text establishes identity.
Wikidata source revision: `2520553171`; claims/labels CC0-1.0, synthetic overlay
Apache-2.0. Original source triples and those licenses remain inspectable.

## Interpretation and authority

`Bundle.assemble(entity, predicate)` accepts only the supported explicit IRIs,
checks their roles and predicate profiles in the current graph-local Rust-built
catalog, and derives the fixed graph, forward direction, values projection,
current pinned snapshot and single-graph scope. Rust `ask-preview` then validates
and compiles the existing Confirmed Ask request. No new planner, raw SPARQL
builder, retrieval or language-model adapter is introduced.

Optional original question text is **unverified user intent**. It never selects
entity, relationship, direction, scope or filters. There is no keyword classifier.
For example, “Show only the English official names” is unsupported as a request.
The user may independently select **Official names → All stored values**, but the
preview and result explicitly say that this does not verify an answer to the
original question. The receipt retains the question separately from the operation
and marks it `unverified_user_intent_not_interpreted`. Typing alone grants no
authority and produces no answer or proposed interpretation.

Reverse relationships, counts, filters (including language filters), negation,
joins, graph unions, writes and raw SPARQL are unsupported. Extra operation fields,
unknown entities/predicates, numeric aliases and alternate graphs are rejected.
The UI offers no alternative operation automatically.

The new `/api/assisted-ask-v1/` routes reuse the existing exact-approval bridge.
Assisted Ask creates the same server-held review record with a narrow manual
proposal origin and reuses the unchanged confirmation method. It records `manual_structured_selection_v1`, `inference_performed:
false`, and the existing Rust executor origin `manual`. It never promotes a model
or fixture to manual authority. Old preview/Find/model routes are unavailable in
this server. Session credential, Host/Origin checks, tab revocation, disconnect
preflight, single-use consumption before validation, 120-second review expiry and
15-minute session expiry are inherited. Cancellation, edited/replayed/stale tokens
and changed source/config/policy/scope/executable fail closed. Before execution,
the selection and full Rust preview are rebuilt and compared; Rust validates again
inside Confirmed Ask. No answer query executes before independent approval.

The original 100-row, 200-evidence-triple and 5000-ms Rust limits apply, alongside
the existing 45-second child deadline and response-size limits. Results may be
clipped; the UI reports row and evidence clipping separately. Execution failures
and timeouts assert no answer and consume approval. Closing a tab cannot undo an
already approved read-only execution.

## Evidence and limits of the claim

[PR #111](https://github.com/grove/graph-verity/pull/111) motivates this product
boundary: Qwen matched 20/29 supported plans (17/17 forward, 3/12 reverse), produced
nine wrong-but-executable proposals among 40 candidates and 11 candidates on 18
unresolved questions. Its eight/eight website/name matches did not satisfy the
surrounding alpha gates. Those results are not proof of this interface's reliability.
No new prompt experiment or live inference is part of Assisted Ask.

- **Deterministic correctness:** explicit choices are assembled according to this
  narrow contract and independently validated/executed by Rust.
- **Semantic correctness:** whether the manually selected operation answers the
  user's original intent remains unassessed. Approval is a choice, not proof.
- **Source correctness:** results and witnesses describe the retained RDF snapshot;
  source completeness and real-world truth are not established.
- **Human comprehension:** zero independent human observations; unmeasured.

This is a useful local assisted operation, not general natural-language question
understanding, model semantic accuracy, independent human validation or release GO.
The smallest next enhancement is a separately selected language-filter template
with explicit semantics and Rust validation, rather than inferring filters from text.

[Validation and historical preservation receipts](assisted-ask-v1/validation.md).
