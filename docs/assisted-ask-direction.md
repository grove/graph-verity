# Assisted Ask v1: explicit-direction extension

This additive local entry point makes one previously implicit choice explicit:
the user selects **forward** or **reverse** before requesting a Rust preview.
The original v1 app, its source files and its historical validation receipts stay
unchanged.

```sh
cargo build --locked --offline -p verity_cli --target-dir artifacts/assisted-ask-build
.venv/bin/python tools/assisted_ask_direction.py --binary artifacts/assisted-ask-build/debug/verity
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
SHACL-backed guidance, shape provenance or document-RAG evidence, so #115 remains
open and the release status remains `INCONCLUSIVE_REVISE`.

Focused model-free checks:

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python -B -m unittest discover -s tools -p 'test_assisted_ask_direction.py'
```
