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
suggestions. The request uses the exact authorized Wikidata development graph
and snapshot; results show graph-qualified candidates, available source text and
RDF usage evidence alongside any matching shape guidance. Scores are BM25
ranks, not probabilities. The demo shape set in
`examples/assisted-ask-direction/demo-shapes/` is
operator-authored and Apache-2.0 licensed, and its source, graph mapping,
snapshot identifiers and content hash are shown in the interface. It provides
only `P856` IRI-node and `P1448` language-string hints. These hints are not
Wikidata statements, validation results or factual claims. A suggestion never
selects anything. A supported entity or predicate can be added to its selector
only with an explicit button click; direction remains manual, and suggestion
selection does not request a preview. Candidates outside the current operation
are shown without a selection button. Source labels and graph text are untrusted
and rendered as text. Labels are shown only when they match the selected
language; a localized interface term is marked as interface-only when the graph
has no matching source label.

In the retained development snapshot, the natural English question “Which
official websites does the University of Tromsø list?” and Norwegian question
“Hvilke offisielle navn har Universitetet i Tromsø?” retrieve entity `Q279724`
but no predicate candidate. Exact `P856` and `P1448` identifiers retrieve their
predicate candidates, but do not retrieve an entity. These are reproducible
development observations, not owner-reviewed relevance judgments or evidence
of real-world usefulness. They show that the existing BM25 path can suggest an
entity for these two phrasings while property discovery still depends on exact
identifiers in this small graph. The demo shapes establish metadata handling,
not general retrieval quality.

**Next #114/#115 milestone:** repeat the same model-free checks on an
owner-selected graph with a trusted shape set and useful Norwegian/English
labels, then have the owner review candidate relevance and direction mismatches.
Measure BM25 misses before proposing a retrieval change.

Focused model-free checks:

```sh
cargo build --locked --bins
cargo build --manifest-path crates/verity_shacl/Cargo.toml --bin shape_guidance --locked --offline
REQUIRE_FIND_BROWSER=1 .venv/bin/python -B -m unittest discover -s tools -p 'test_assisted_ask_direction.py'
```
