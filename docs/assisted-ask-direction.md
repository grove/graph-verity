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

The optional question field can request bounded BM25 property suggestions. The
suggestion request uses the exact authorized Wikidata development graph and
snapshot; results show original labels and usage evidence alongside any matching
shape guidance. Scores are BM25 ranks, not probabilities. The demo shape set is
operator-authored and Apache-2.0 licensed, and its source, graph mapping,
snapshot identifiers and content hash are shown in the interface. It provides
only `P856` IRI-node and `P1448` language-string hints. These hints are not
Wikidata statements, validation results or factual claims. A suggestion never
selects a property or changes direction; the user must make the supported
structured choice and request a separate preview. This small development graph
may return no suggestions for ordinary natural-language phrasing.

**Next #115 milestone:** evaluate the same path on an owner-selected graph and
trusted shape set with useful Norwegian/English labels, then have the owner
review candidate relevance and direction mismatches. In the retained development
graph, exact `P856` and `P1448` identifiers retrieve candidates, but
`official website for university` does not; the demo shapes therefore prove
the metadata contract, not practical retrieval usefulness. Record BM25 misses
before proposing embeddings or graph-neural ranking.

Focused model-free checks:

```sh
cargo build --locked --bins
cargo build --manifest-path crates/verity_shacl/Cargo.toml --bin shape_guidance --locked --offline
REQUIRE_FIND_BROWSER=1 .venv/bin/python -B -m unittest discover -s tools -p 'test_assisted_ask_direction.py'
```
