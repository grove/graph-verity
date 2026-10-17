# Local Find and Confirmed Ask browser pilot (#55 / #56)

This is an operator-started, model-free pilot over the existing Rust BM25 Find
and one-hop evidence contracts. It is not a hosted service or a usability study.
Ranked candidates are not verified answers. Source triples belong to an immutable
graph snapshot; they do not prove real-world truth. Missing matches leave factual
absence unknown. The optional Confirmed Ask editor exposes only the existing
deterministic `follow_path` template, with a separate preview and approval.
No model, fusion, free-form Ask, SPARQL input or RDF write is exposed.

## Launch locally and offline

Prerequisites: the pinned Rust toolchain/dependencies, Python 3.11+ and a modern
browser. Dependency installation requires a network once; the retained licensed
snapshots, build and UI then work offline. No Python packages or npm packages are
needed for this UI. From a clean checkout at the repository root:

```sh
# Once, while online (skip if the pinned toolchain/dependencies are already cached):
rustup show
cargo fetch --locked
# Offline from here:
cargo build --locked --offline -p verity_cli
python3 tools/local_find.py
```

Open the private loopback URL printed in the terminal. No JSON editing is needed.
The random port and 256-bit session credential change on each launch. The URL
fragment is read by the same-origin script, removed from the address bar, and
retained in tab-local sessionStorage for reloads. It never enters an HTTP URL,
access log or referrer. Do not share the session URL or the browser tab/profile.
Stop with **Ctrl-C** in the terminal; this closes the socket, removes the private
temporary bundle, and revokes browser access. Clear/close the tab to discard the
credential. Restart for a new credential after any operator input changes.

Each load also obtains a random **tab lease**, sent in `X-Verity-Tab` with the
bearer credential. Opening/reloading a second tab revokes the previous tab's
lease, selections and pending review. A lease expires after 15 minutes; reload
and explicitly resolve/select again. Credentials and tab leases authenticate
local requests; the core's content digest does not.

`--host ::1` explicitly selects IPv6. Only literal `127.0.0.1` and `::1` are
accepted, including when `--port` is supplied. Wildcards, hostnames, other local
aliases and LAN/public addresses fail. Never tunnel or proxy this pilot.

Operators may supply `--binary`, `--rdf`, `--format`, `--policy`, `--scope`,
`--config`, an optional persisted `--index`, and a subset of `--roles entity
predicate class`. Defaults use the retained CC0 Wikidata snapshot and its
development graph. The browser only selects subsets of these authorized graphs
and one authorized search role. Navigation remains within one deliberately
selected original graph. Role restrictions gate navigable resource identities;
they do not redact individual terms from already-authorized source statements.
Graph scope is the data confidentiality boundary. Restrict the operator scope
accordingly. No private source names, graphs or global counts are sent as a
session menu; the policy's broader graph list stays on the backend.

## Offline Norwegian / English walkthrough

1. Leave the authorized development graph checked. Choose **Entity**, search
   `Norge`, then `Norway`. Both rank Q20 (`http://www.wikidata.org/entity/Q20`)
   first. Inspect original IRI, observed labels, literal languages/datatypes,
   exact/partial explanation and graph identity. A score is lexical relevance,
   not confidence or question correctness.
2. Set the maximum candidates/edges to **50**, repeat the search, then deliberately
   **Select candidate** for Q20. The heading receives keyboard focus. In outgoing
   evidence find the original predicate `http://www.wikidata.org/prop/direct/P36`
   with object `http://www.wikidata.org/entity/Q585` (Oslo).
3. Use **Open resource: …/P36** on that source statement. This opens predicate
   usage, retaining the original graph. Open Q585 on that statement to inspect
   incoming evidence. The exact Q20 → P36 → Q585 source triple is present, with
   subject/predicate/object term kinds and the same graph/snapshot identity.
   Expand **Graph / source / license** for CC0 source and importer revisions and
   graph hashes. Use direction and previous/next buttons for bounded pages.
4. Separately choose **Predicate** and search `capital` or `hovedstad`. Inspect
   the `directClaim` retrieval mapping. Its original label subject is P36 in the
   entity namespace; the mapped predicate is P36 in the direct-property namespace.
   Open the original label subject to see the actual label and mapping statements.
   The UI never invents a direct-property label triple.
5. Choose Entity and search `city` for partial candidates; search `zzznomatchzzz`
   for no-match. The synthetic integration fixture additionally exercises multiple
   exact `Island` candidates and a lone partial `Observed` candidate. Ambiguity
   is determined before clipping, even with a one-candidate display limit.
   Try English / Norsk bokmål for localized controls and outcome explanations.

Every page explicitly distinguishes candidate ambiguity, partial/low confidence,
no-match, search clipping, evidence clipping, and empty direction/page. Unclipped
top-k never establishes semantic completeness. No row is selected automatically.
Blank nodes retain their kind and identifier but cannot be opened as IRI entities.

## Deliberate Confirmed Ask walkthrough

Keep the selected entity's **Graph evidence** open after step 2 above. Click
**Build exact follow_path plan from this selected Find entity**. This button is
available only for an explicitly selected entity from the latest entity Find
results, with both entity and predicate roles allowed. Direct resource navigation
or a predicate search does not silently establish an Ask start.

1. Choose the first step explicitly: development graph, original predicate
   `http://www.wikidata.org/prop/direct/P36`, **forward (outgoing)**. The catalog
   also shows reverse (incoming) choices and graph-qualified original IRIs,
   observed labels and datatype profiles. Missing direct labels, multiple labels
   and retrieval-mapping witnesses remain explicit and inspectable. Shared
   aliases never merge identities. No first step/predicate is preselected.
2. Leave the second step empty and choose **Distinct terminal RDF values**.
   Click **Preview exact plan**. Read the authoritative Rust summary, including
   actual subject → predicate → object direction, terminal-only projection,
   graphs, immutable snapshot, typed filter, rows, evidence cap and timeout.
   Expand the entire resolved plan and source provenance. This does not execute.
3. Separately check that you reviewed the exact plan, then click **Approve this
   exact plan and execute once** (keyboard: Space). Enter alone never approves,
   including when this enabled button has focus. The answer is Q585 (Oslo) for
   this formal plan. Inspect the original Q20 → P36 → Q585 triple and its named
   graph/snapshot. **Rows truncated** and **Evidence truncated** are independent.
4. Change projection to **COUNT(DISTINCT terminal RDF terms)**. Review a fresh
   preview and approve separately: one count row, value 1. This counts distinct
   terminal RDF terms, not paths; zero would mean no matching stored terms,
   without establishing real-world absence or dataset completeness.
5. For a two-hop typed comparison, retain outgoing P36 and explicitly choose
   outgoing `http://www.wikidata.org/prop/direct/P1082` as the second step. Choose
   greater than (`gt`), the observed exact datatype
   `http://www.w3.org/2001/XMLSchema#decimal`, lexical value `700000`, and leave
   language empty. Preview/approve again. The retained source file spells the
   literal `+717710` with datatype `xsd:decimal`; the existing RDF engine returns
   lexical `717710` with that same datatype. The UI displays the engine's RDF
   terms without string/integer/decimal coercion. Count mode over the same
   filtered path returns 1.
6. To inspect incoming semantics, Find and deliberately select Q585, then choose
   P36 **reverse (incoming)**: terminal countries → P36 → selected Oslo. Preview
   states the actual direction. Choose Cancel, edit a value or scope, navigate,
   rerank Find, hide the tab, or use browser history: approval disappears and a
   new preview is required. Unsupported selections require exact Find resolution
   or explicit operator changes; no question interpretation or fallback runs.

The editor catalogs predicates only in the operator's permitted graphs. The first
step uses the explicitly selected entity's graph; the optional second step may
use another permitted graph and always starts at `?step1`. Every step must match;
only `?step1` for one hop or `?step2` for two hops is projected. Catalog membership
does not promise that a particular path has matches. Rust rejects incompatible
ranges, unknown predicates, unsupported operators, ill-typed literals and invalid
plans before offering confirmation. Typed-filter datatypes must occur in the
selected predicate's graph profile; reverse steps end at resources and have no
literal filter. Labels and source strings remain inert text even if they contain
markup, model instructions or SPARQL.

The browser submits a fresh Ask request only for preview. The server holds that
exact request, the complete Rust preview and approval digest, and a random UI
nonce with a two-minute expiry. Confirmation sends only this nonce and the
explicit decision, never a replacement plan or a browser-supplied core digest.
The server consumes the pending decision **before** validation/execution, checks
the lease and operator bundle, rebuilds the preview under the current Rust
policy, then passes the retained exact digest to the existing `ask` CLI. That
CLI independently previews/revalidates and invokes `execute_confirmed_ask`.
A changed request, snapshot, scope, policy or cap cannot reuse an approval.
Cancel, incomplete/disconnected requests, missing/wrong/expired decisions and
replays never execute. Double-submit is blocked synchronously in the UI and by
the server's single-use record. Concurrent operator-file edits are detected
before/after CLI calls; the process always uses private frozen copies, and a
changed original revokes pending review/results rather than hot-reloading data.
An execution timeout or failed response consumes the decision; inspect a new
preview before any retry.

The digest is a **content hash**, not authentication, a signature or evidence of
human understanding. The additional UI lease/nonce does not replace or weaken
Rust checks. The underlying core/CLI digest remains replayable by independent
callers; the one-shot ledger is local to this UI. An authenticated custom client
can deliberately make its own decisions; this UI does not attest a physical
human gesture. There is no unattended or model proposal endpoint.

## Research tasks and unmeasured risk

**Participants: 0; human task attempts: 0; independent semantic reviewers: 0.**
Human misunderstanding, false confidence and demand remain **unmeasured**.
Automated engineering assertions are not user research or a product-release GO.
Approving a correctly executed plan can still encode the wrong intention, and
source evidence cannot establish real-world truth. The new editor's Ask copy is
English; the existing Find controls remain Norwegian/English. Its long catalog
and complete plan may impose considerable domain knowledge and reading burden.

The numbered walkthrough is a reproducible demo task set using retained public
sources, ready to freeze for a separately designed user study. Before each
approval, ask participants to explain the selected direction, which terminal
variable is returned, typed threshold, distinct-count meaning, scope/snapshot
and both caps. Add these tasks without coaching the answer:

- Select Oslo's incoming capital relation and explain country versus city.
- Compare Norway → capital → population in values/count mode, including a threshold
  above the stored value; explain why zero does not imply real-world absence.
- Search an ambiguous name in a synthetic fixture; distinguish graph-qualified
  exact IRIs and missing/shared labels rather than choosing by rank.
- Change a field after preview, cancel a plan, and open a new tab; explain why
  the previous approval is unusable. Inspect independent row/evidence clipping
  with a deliberately restricted operator bundle.
- Read an injection-bearing synthetic label as source data, and explain why an
  executed plan and source triples do not verify the user's question or truth.

Record assisted/unassisted completion, wrong-but-executable formal choices,
cancellations, exclusions, confidence and pre-approval explanations. Independently
assess task intent and report denominators at participant/task level. Follow the
[existing research protocol](../reports/issue-40-confirmed-ask/README.md), freezing
revision/tasks and acceptance criteria before recruitment. The four historical
Qwen failures remain failures: rejecting their raw proposals at this UI boundary
is containment, not model correctness or successful interpretation.

## Architecture and trust boundary

```text
Operator paths -> bounded reads -> private immutable temporary copies
  -> Rust index-build / index-inspect -> validate snapshot + scope + policy + config
Browser local assets -> credential from fragment -> same-origin authenticated POST
  -> bounded HTTP parser -> strict endpoint/field/scope/role checks
  -> fixed argv (no shell): Rust find / entity -> bounded JSON -> text-only DOM
```

`tools/local_find.py` uses only Python's standard library. It delegates ranking,
authorization, graph-local mapping, validation, deterministic ordering, row,
evidence, offset and query-time bounds to the existing CLI/core. CLI interfaces
and schemas remain unchanged. Each request uses a new CLI process: deliberately
simple, slower than a persistent Rust process, and suitable only for small
retained snapshots. A persisted index is fully rebuilt/compared by the core,
not trusted as a cache. Original operator input bytes and the executable are
checked before requests and again before data responses; changes fail closed.
Private copies prevent a concurrent input edit from changing the executed data.

The browser can request only `/api/session`, `/api/find`, `/api/entity`,
`/api/ask-catalog`, `/api/ask-preview`, `/api/ask-confirm`, `/api/ask-cancel`.
Requests never specify paths, policy overrides, raw Plans/SPARQL or an executable.
Only preview accepts the strict existing `follow_path` Ask schema; confirmation
accepts exactly a one-shot UI token and explicit decision.
Session metadata contains the authorized scope/roles, bounded page size and
versioned receipt. The receipt binds the adapter and three asset SHA-256 hashes,
Rust executable hash, snapshot, core policy/config hashes, index revision and
transport/backend versions; the Rust binary includes its ranking implementation
revision. Pair it with `git rev-parse HEAD`, `rustc -Vv` and `python3 --version`
for a reproduction record. Paths and full private operator metadata stay local.
The receipt identifies a runtime, not a signed security attestation.

Threats covered:

- Remote webpages and DNS rebinding: only exact loopback binds, exact Host,
  same Origin for POST, same-origin/none Fetch Metadata, unguessable bearer
  credential and JSON-only requests. No cookies, permissive CORS or preflight
  handler. Missing/incorrect origin or credential fails. Public static assets
  contain no data or credential. No data-bearing GET routes exist.
- CSRF and framing: bearer header plus mandatory matching Origin, no cross-origin
  CORS, CSP `frame-ancestors 'none'`, `form-action 'none'` and X-Frame-Options DENY.
  The credential is never embedded into HTML or script.
- Malicious RDF HTML, ChatML and URLs: `textContent`/text nodes only; IRIs open
  same-origin graph navigation buttons, never external anchors. No `innerHTML`,
  analytics, external fonts/assets, remote requests, eval or model instruction
  path. CSP restricts scripts/styles/connections to self and everything else to
  none; responses use nosniff, no-store and no-referrer.
- Scope escalation and enumeration: core authorization precedes ranking, counts,
  labels and evidence. The adapter additionally restricts the operator scope.
  Unknown and role-denied resources use the same core no-match shape, null IRI,
  and no echoed submitted identifier. Scope-denied requests and unknown scopes
  share the same generic error. CLI stderr, private source data and counts never
  enter error responses; the server does not log requests or payloads.
- Resource abuse: headers and JSON bodies each cap at 16 KiB; total input deadline
  is five seconds. Duplicate headers, transfer encodings, conflicting lengths,
  unsupported methods/routes and malformed bodies fail. Responses cap at 8 MiB;
  Rust ingestion/index/output limits also apply. Execution has a 45-second process
  deadline in addition to the existing policy query deadline. One request executes
  at a time, with no background traversal or unbounded worker creation.

Same-user malware, browser extensions, compromised operator files/executable,
OS accounts and physical access are outside this local pilot's threat boundary.
This is plain loopback HTTP, without TLS or multi-user isolation. Local processes
may cause denial of service; five-second input and execution limits bound one
connection, not an attacker's repeated connections. Snapshot IDs hash full release
bytes, as in the existing CLI; a hash is not an authorization credential.

## Model-free checks and limits

```sh
# Headless browser tests need installed Chrome/Chromium and Node >=22; no npm install.
# CHROME_BINARY=/path/to/chrome can select a binary explicitly.
REQUIRE_FIND_BROWSER=1 python3 -m unittest discover -s tools -p test_local_find.py -v
# Full pinned Python/Rust/format/Clippy/reference pipeline, from a clean commit:
.venv/bin/python tools/verify_pre_llm.py
```

CI requires browser checks, pins Node 22, and uses Chrome supplied by the Ubuntu
runner. Ordinary Python-only environments can skip the browser test when Chrome
or Node is absent. Adapter tests use actual CLI subprocesses and HTTP sockets;
browser tests drive actual headless Chrome via CDP with no automation package.
They cover scoped/private graph/source canaries, exact/partial/ambiguous/no-match
states, original typed/language terms, ordered pagination, stale policy/snapshot/
config/index rejection, malformed/oversized/hostile requests, authorization,
binding rejection and IPv6 binding, malicious HTML/ChatML, mapping evidence, the
real bilingual Q20 → P36 → Q585 walkthrough, keyboard focus and tab/space behavior,
accessible control names, no third-party page requests and the no-JavaScript
fallback. These are basic keyboard/accessibility smoke checks, not a WCAG audit
or screen-reader study. A missing credential leaves controls disabled; request
errors clear previous results and show a generic localized recovery message.

Model-free HTTP/browser coverage additionally includes exact catalog selection,
forward/reverse two-hop projection, typed comparisons without datatype guessing,
distinct counts/shared paths, independent clipping flags, one-shot decisions,
expiry, missing/wrong approval, disconnects, timeouts, Enter alone, cancel,
argument edits, history, reranking, stale tabs, policy/scope/snapshot/cap changes,
private canaries and all four historical raw Qwen candidates. Existing Rust tests
retain CLI EOF/cancel and core schema/digest validation coverage.

No model loading, relevance tuning, participant data collection, publication of
a hosted service or changes to retained #37–#53 reports are included.
Automated tests establish engineering behavior, not production readiness,
human-reviewed gold, user-validated relevance or completed usability research.
Actual-user evaluation and research-only selective hybrid remain separate #57
and #58 work; this #56 integration does not complete either.
