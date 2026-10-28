# Local Find UI v2 prototype (#66)

Run `cargo build --locked --offline -p verity_cli`, then
`python3 tools/local_find_v2.py`. Open the private loopback session URL from the
terminal; stop with Ctrl-C. The operator arguments and trusted bundle are exactly
those of [v1](local-find-ui.md), including `--roles`, `--scope` and `--host ::1`.
`python3 tools/local_find.py` still launches the frozen v1 interface.

This is a separately named presentation prototype, **not participant-tested v1**.
The #57 and #58 frozen interfaces, tasks, reports and source hashes are untouched.
There is no claim of improved usability. The #58 independent human gate remains
open; hybrid retrieval is not promoted. BM25 remains the only runtime backend.

## What differs from v1

The v2 launcher composes the unchanged `local_find.Bundle`, `Server` and HTTP
handler. It replaces `/` and adds `/v2.js`; the v1 script and stylesheet are served
unchanged. Alongside clearer result cards, v2 offers an explicit two-hop path
explorer for an entity selected from Find. It calls the existing graph-scoped
`/api/entity` pages, joins only original statements whose endpoint and direction
match, and shows both statements with their source graph. It inspects at most
five intermediate IRIs and twenty paths; existing page clipping and these caps
are reported. Traversal order is not relevance, no path is selected, and no Ask
operation is previewed or executed. No schema, index, ranking, score, scope, role,
plan or source fact changes. There is no reranking, suppression, semantic cutoff,
automatic selection or model execution.

The receipt identifies `local-find-v2-prototype`, hashes its launcher and **all
served assets**, and retains the v1 adapter and executable hashes. It is a runtime
record, not an authentication or human-review claim. The launcher reuses the v1
operator CLI by temporarily substituting its Server class; no v1 source is edited.

An IRI-shaped input with no returned exact authorized IRI gets **No exact identifier
resolved**, even if its namespace tokens retrieve suggestions or an alias happens
to spell the requested IRI. This warning refers to the returned page and selected
role/scope/snapshot. Pre-clipping graph-qualified exact counts and distinct exact
IRI counts are shown separately. A clipped page cannot resolve identities hidden
on later pages; increase the bounded candidate limit if needed. Exact indexed
label/alias/identifier text is separately named. All exactness remains lexical,
not correctness of a question or proof of truth.

Cards retain original graph-qualified identities, unrounded BM25 ranking scores,
the core's unchanged match explanation, language/datatype and source/license.
Token lists come directly from the authorized Rust index; the UI does not attribute
a token to a particular literal or invent a token explanation. Original indexed
label/alias/identifier/definition text is displayed as an RDF statement. A `via`
association displays the actual label statement on its original subject and the
actual `directClaim` mapping statement, never a direct label on the mapped predicate.
Clipped descriptions are explicitly excerpts, not fabricated full literal witnesses.
Absent direct labels and missing indexed text are explicit.

Graph pages display original subject → predicate → object order, incoming/outgoing/
predicate-usage roles, and distinct explanations of `skos:broader` and `skos:narrower`.
These describe stored statements, not inferred inverse edges. Navigation cannot
fill an Ask predicate/direction. Ask still requires explicit choices, the entire
Rust preview, review and a separate expiring, single-use approval action.

## Text-only public walkthrough and manual inspection checklist

1. With the default public CC0 fixture, search Entity `Norway`, then `Norge`.
   Q20 is an exact text candidate. Check the original label subject, language,
   datatype, development graph, snapshot and CC0 license. Nothing opens or runs
   automatically. Paste `http://www.wikidata.org/entity/unavailable`: check the
   exact-identifier warning and separately marked namespace suggestions.
2. Search Entity `capital of Norway` / `hovedstaden i Norge`. Read the unverified
   suggestion notice and bilingual examples. Switch explicitly to Predicate and
   search `capital` / `hovedstad`. Inspect the two original P36 label/directClaim
   statements. Neither phrase has been interpreted into an answer.
3. Select Q20 deliberately; inspect the outgoing Q20 → P36 → Q585 statement.
   Open Q585, retaining its graph, and inspect incoming evidence. Compare the
   direction labels and original triple order. On the retained Wikidata graph,
   select Oslo/Q585 and use **Explore two-hop source paths**. Inspect a path via
   Norway/Q20, confirm each original triple and direction, and note that the
   other city IRIs are candidates rather than answer claims. Choose a small edge
   limit and inspect next/previous pages and the separate clipping messages.
4. Switch English/Norsk bokmål. Check exact, partial, ambiguous, low-confidence,
   no-match, clipping and catalog-limit text. Search `zzznomatchzzz`: no authorized
   lexical match does not imply real-world absence. Fictional phrases may still
   retrieve irrelevant suggestions; no new score cutoff detects that.
5. Use Tab/Space, inspect accessible names, heading focus and live statuses.
   Verify no automatic selection, external anchors, fonts or third-party requests.
   Source text, including malicious markup/instructions, must remain inert text.
6. Select a Find entity and open the exact-path editor. Verify the first step is
   blank. Choose graph/predicate/direction explicitly and preview; inspect the
   authoritative Rust preview. Approval remains disabled until separate review.
   Cancel/edit/navigate and verify a fresh preview is required. Enter never approves.

The new synthetic fixture tests also cover shared-alias ambiguity before a
one-candidate clip; exact alias text that resembles an unavailable IRI; an exact
identifier outside selected scope; missing labels; clipped definitions; and
child → `broader` → parent versus parent → `narrower` → child, in original direction.
These are engineering assertions, not actual participant observations.

## Verification and limits

```sh
REQUIRE_FIND_BROWSER=1 python3 -m unittest discover -s tools -p 'test_local_find*.py' -v
python3 tools/pilot_study.py verify
python3 tools/hybrid_review.py verify
# From the committed tree, full Rust/Python/format/Clippy/browser/reference pipeline:
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

V2 inherits the existing HTTP/approval/security tests against its composed server,
adds independent v1/v2 Find payload equality checks, and runs a separately named
Node/headless-Chrome harness on synthetic and retained public Wikidata fixtures,
including delayed v2 asset loading after the v1 session has initialized and the
Oslo → Norway → other-city path with original directions.
No npm dependencies or models are needed. Existing CI discovers the new Python
test module automatically and requires Chrome/Node.

The prototype remains restricted to the bounded authorized catalog and indexed
languages. A partial candidate can be irrelevant; score is not probability,
confidence or truth. Low-confidence wording describes uncertainty about
interpretation, not a calibrated estimate. Search top-k and bounded evidence do
not establish semantic completeness. Full source literals can still require graph
navigation, and a bounded page may omit a witness. Original RDF terms are those
returned by the existing engine, which may canonicalize typed literal spelling.
Ask controls remain English as in v1. Automated keyboard/accessibility checks are
not a screen-reader study or WCAG audit. No participants or human judgments were
collected, and no user-experience improvement or release readiness is established.
