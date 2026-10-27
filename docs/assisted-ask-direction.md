# Assisted Ask v1: explicit-direction extension

This additive local entry point makes one previously implicit choice explicit:
the user selects **forward** or **reverse** before requesting a Rust preview.
The original v1 app, its source files and its historical validation receipts stay
unchanged.

```sh
cargo build --locked --offline -p verity_cli --target-dir artifacts/assisted-ask-build
cargo build --manifest-path crates/verity_shacl/Cargo.toml --bin shape_guidance --locked --offline --target-dir artifacts/assisted-ask-build
python3 tools/assisted_ask_direction.py \
  --binary artifacts/assisted-ask-build/debug/verity \
  --shape-guidance-binary artifacts/assisted-ask-build/debug/shape_guidance
```

Open the private single-tab URL printed in the terminal. Choose the entity,
relationship and direction, then review the orientation, graph, snapshot and Rust
preview. Approval remains a separate, single-use action. Changing any choice
invalidates the pending review. Stop with Ctrl-C and keep the URL and receipts
local.

By default, the app uses the checked-in operator-authored demo shapes. To select
a local SHACL bundle for this same authorized data graph and snapshot, add
`--shape-file /path/to/shapes.trig --shape-config /path/to/shape-config.json`.
The TriG file must contain one named shape graph. The JSON manifest must identify
that graph and the exact shape and data snapshot IDs, map to the current authorized
data graph, and provide origin, source, license, source revision, and importer
revision. `origin` may be `operator_authored_demo` or `source_published`.

Shape files are read only from the paths the operator supplies, copied into the
private session directory, hash-pinned, and checked for changes. The app does not
download or convert shape sources. Provenance and license values in the manifest
are operator declarations; the app does not verify source identity or license
terms. No source-published SHACL file is currently retained in this repository,
so selecting one requires the owner to supply and verify it first. The current
Ask data graph and its scope remain fixed.

Forward follows `entity —predicate→ value`. Reverse finds original triples of
the form `subject —predicate→ entity`, displayed as `value ← predicate — entity`.
Reverse does not create inverse RDF statements. Both choices query the same
authorized single Wikidata development graph and snapshot as v1. The app still
does not interpret the optional question text; it records it as unverified
intent. Empty reverse results describe this snapshot only.

The API requires the `direction` field and accepts only `forward` or `reverse`.
The preview and approval continue through the existing Rust planner and exact
approval bridge. No model is loaded or called. This slice does not yet add
document-RAG evidence, so #115 remains open and the release status remains
`INCONCLUSIVE_REVISE`.

The optional question field can request bounded BM25 entity and predicate
suggestions plus separate shape-guided properties witnessed near BM25 entity
candidates. The request uses the exact authorized Wikidata development graph
and snapshot; results show graph-qualified candidates, available source text and
RDF witnesses alongside any matching shape guidance. BM25 scores are ranks, not
probabilities; neighborhood rank does not indicate question relevance. The demo
shape set in `examples/assisted-ask-direction/demo-shapes/` is
operator-authored and Apache-2.0 licensed, and its source, graph mapping,
snapshot identifiers and content hash are shown in the interface. It provides
only `P856` IRI-node and `P1448` language-string hints. These hints are not
Wikidata statements, validation results or factual claims. A suggestion never
selects anything. A supported entity or predicate can be added to its selector
only with an explicit button click; direction remains manual, and suggestion
selection does not request a preview. The selected shape origin, source/license,
shape snapshot and hash also travel with the review and result receipt as optional
guidance context, never as query evidence. Candidates outside the current operation
are shown without a selection button. Source labels and graph text are untrusted
and rendered as text. Labels are shown only when they match the selected
language; a localized interface term is marked as interface-only when the graph
has no matching source label.

In the retained development snapshot, the natural English question “Which
official websites does the University of Tromsø list?” and Norwegian question
“Hvilke offisielle navn har Universitetet i Tromsø?” retrieve entity `Q279724`
at BM25 entity rank 1 but no BM25 predicate. The existing source-witnessed
neighborhood path adds `P1448` at neighborhood rank 4 and `P856` at rank 7 for
both questions, each backed by an original outgoing Wikidata statement from
`Q279724`. The neighborhood packet is clipped; the UI displays that limit and
does not treat missing edges as absent facts. These properties appear for both
phrasings, so this expansion supplies source-backed choices but does not
determine which one answers the question. Its displayed rank is not a question
relevance score. Exact `P856` and `P1448` identifiers retrieve their BM25
predicate candidates, but do not retrieve an entity. These are reproducible
development observations, not owner-reviewed relevance judgments or evidence
of real-world usefulness. The demo shapes establish metadata handling, not
general retrieval quality.

The exposed `ask-alpha-v1` packet review found one missing reference entity
that is present as an endpoint of a stored edge from a BM25 entity seed. The UI
shows that linked entity and its exact edge in a separate list, without a
question-relevance rank. Entities outside this demo's Q279724/P856/P1448
allowlist have no selection button. See
[`ask-alpha-candidate-baseline.md`](ask-alpha-candidate-baseline.md) for the
60-case descriptive counts and their limits.

The paired retrieval baseline found no pure BM25 predicate target among the 29
agent-authored candidate references by rank 10; neighborhood v2 found 20/29 by
rank 5 and 29/29 by rank 10. This is exact candidate-position coverage, not
human relevance or answer accuracy. The full paired counts and per-case ranks
are in
[`ask-alpha-paired-retrieval-v1`](../benchmarks/ask-alpha-paired-retrieval-v1/README.md).

**Next #114/#115 milestone:** add the already retained licensed property labels
and descriptions to graph-local BM25 predicate text, then repeat the paired
measurement before considering dense retrieval. The current data has no
independent human relevance labels, so owner review remains necessary before
any relevance or usefulness claim.

Focused model-free checks:

```sh
cargo build --locked --bins
cargo build --manifest-path crates/verity_shacl/Cargo.toml --bin shape_guidance --locked --offline
REQUIRE_FIND_BROWSER=1 .venv/bin/python -B -m unittest discover -s tools -p 'test_assisted_ask_direction.py'
```
