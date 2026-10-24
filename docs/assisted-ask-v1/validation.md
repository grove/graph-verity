# Assisted Ask v1 validation

Decision remains **INCONCLUSIVE_REVISE**. No model, weights, consumed trial or
sealed holdout is accessed. Human comprehension remains unmeasured.

The implementation reuses the unchanged Rust engine and exact-approval bridge.
The focused suite uses the real Rust binary and loopback HTTP server, with eight
headless Chrome sessions: bilingual journeys/security, review expiry, empty
results, row clipping, evidence clipping, hostile source labels, timeout and
execution failure. Timeout/failure exceptions are injected at the execution
boundary; they are failure-path checks, not observed Rust timeouts. Empty and
hostile data and reduced policies exist only in isolated temporary fixtures.
Production has no source/snapshot override.

Focused run 4 passed **10/10 Python tests**, including all eight Chrome sessions.
It checks original website IRIs, en/nb/nn names, RDF datatypes, source witnesses,
manual origin, provenance/license, filtered/count/SPARQL text remaining unverified,
no execution before approval, missing/expired/replayed/edited/cancelled approvals,
new tabs, unknown/numeric entities, unauthorized predicates, direction/graph/scope
substitution, changed snapshot/source/policy/config/scope/binary, old routes,
Host/Origin/credential/tab checks, disconnect preflight, and consumed failures.
Keyboard preview and deliberate Space approval, Escape cancellation, and 390px
responsive layout are browser-checked. No synthetic human review is claimed.

Recorded development failures:

1. Focused run 1: all ten tests could not bind loopback inside the sandbox.
   Reran with host execution for local server/Chrome; no application change.
2. Focused run 2: the new isolated fixture retained the original config snapshot
   ID, a source-audit key was wrong, and the keyboard driver omitted Enter text.
   Corrected fixture metadata, audit lookup and actual key dispatch.
3. Focused run 3: the source assertion compared serialized N-Triples with Turtle
   bytes instead of RDF triples; corrected with the existing RDF parser. Keyboard
   testing also exposed that focus stayed on Preview: a second Enter rebuilt the
   preview. Review now focuses its accessible heading, preserving a deliberate
   separate keyboard approval action. No validator or approval check was relaxed.
4. Focused run 4: all checks passed. Earlier logs remain retained separately.
5. The PR #111 preservation checker initially rejected an edit to the historical
   adapter's pinned source bytes. Removed the shared provenance-hook change:
   Assisted Ask creates a compatible manual review record, then uses the unchanged
   confirmation method. The historical adapter and its original fixture/model
   boundaries remain byte-for-byte intact. No registration was resealed.

## Complete validation

The exact required command passed on candidate
`be8d0a71af5728e1fb1d5833f195073b0b424589` in the clean isolated checkout
`/private/tmp/graph-verity-assisted-verify`, using its own offline Rust build:

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

**41/41 command checks passed**, including **181 + 201 current Python tests**
without skips, all required existing and new browsers, frozen-history and NL Ask
history replay, formatting, Clippy with warnings denied, **100 Rust tests**,
source/scope canaries, dataset byte rebuild, schema/catalog parity, 38 executable
Wikidata development oracles, 35 transfer-development oracles, and manual/fixture
execution checks. The locked-evaluation sentinel was rejected before access;
no sealed holdout was read. No pipeline failure, deadline increase or gate change.

Focused Rust checks separately passed **8 Confirmed Ask + 5 NL Ask + 4 CLI Ask =
17 tests** in the isolated build. Focused run 5 passed **10/10 Python tests** and
all eight Chrome sessions on the final adapter. The full pipeline then reran
these unchanged successfully. A separate unchanged browser rerun also passed
while capturing the Norwegian 390px view for coding-agent visual inspection.
This is engineering/visual QA, not an independent human study. Only documentation
and receipts are added after the fully tested implementation candidate.

## Historical preservation

[Preservation receipt](preservation.json) verifies all **1,467 task-baseline tracked
files**: the only pre-existing content change is the README's Assisted Ask link.
The **1,688-file historical baseline** has no missing files and that same sole
content change. `tools/local_nl_ask.py` is byte-for-byte original; its mtime records
the removed development edit. No original registration/source hash was resealed.

All **1,481 original native files** retain bytes, membership, modification times
and modes, using the original published inventory (the freeze archive is separately
committed). Original attempt ledgers, registrations, raw model evidence, prompts,
benchmarks, scoring and snapshots remain unchanged. The unchanged PR #111
`check.py` passes after implementation and again after full validation.
The registered `target/debug/verity` retains both SHA-256
`16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`
and its original modification time. Models/assets were neither loaded nor
acquired; validation used isolated builds and never retried consumed registrations.

[Machine-readable validation](validation.json) records the complete pipeline,
tested implementation hashes, focused runs, failures and unchanged successful
reruns. [Validation logs](validation-logs.tar.gz) retain original failures and
successful runs; the [log index](validation-log-files.json) records original and
published hashes. Only ephemeral private URL/bearer credentials are redacted.
[Checksums](checksums.json) bind the published receipts. Launch and exact scope:
[Assisted Ask v1](../assisted-ask-v1.md).
