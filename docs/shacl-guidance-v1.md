# SHACL property guidance v1

This is the first model-free #115 slice. It adds bounded metadata for direct
`sh:path <IRI>` property shapes and joins that metadata to an exact predicate
candidate from the existing #114 BM25 vocabulary packet.

The operator selects a shape graph, maps it to an authorized data graph, and
supplies source, license, source revision, importer revision, and whether the
shape is source-published or an operator-authored demo. The builder binds this
claim to the exact shape source SHA-256 and the data and shape snapshot IDs.
The shape snapshot must contain exactly the selected named graph; default-graph
data and additional unmapped graphs are rejected.
The provenance fields are operator claims; the code does not verify license
terms or external source identity. The checked-in `shacl-guidance.trig` file is
an Apache-2.0 operator-authored demo for the synthetic `smoke.trig` fixture.

The supported property metadata is `sh:datatype`, `sh:class`, `sh:nodeKind`,
`sh:minCount`, and `sh:maxCount`, plus parent `sh:targetClass` labels. Direct
`sh:path <IRI>` and a simple `sh:path [ sh:inversePath <IRI> ]` are reported
with the base predicate IRI and `path_direction` (`forward` or `inverse`). An
inverse path is guidance about traversal orientation; it never creates an inverse
RDF statement. Complex paths, malformed constraints, and unsupported SHACL
property constraints are counted and omitted. They do not remove BM25 candidates.
A missing guidance entry means “no supported shape guidance”; it does not mean
“no matching property” or “invalid data”.

The Rust API is `verity_shacl::build_shape_guidance` followed by
`ShapeGuidanceIndex::for_candidate`. It takes the exact shape and data bytes,
the current `DiscoveryIndex`, `VocabularyPacket`, and `Policy`; it verifies
that the packet uses the same snapshot, policy, index revision, graph hash,
source metadata, and authorized scope before joining a predicate ID.
The output is guidance only: it does not validate graph data, infer triples,
interpret a question, build a plan, or grant execution authority. #115 still
needs the user-facing choice/preview flow, real authorized shape selection, and
separate human review.

This is a standalone crate with its own lockfile. It leaves the frozen core
source files and root `Cargo.lock` unchanged, preserving historical source
registrations. Run its model-free checks with:

```sh
cargo fmt --manifest-path crates/verity_shacl/Cargo.toml -- --check
cargo clippy --manifest-path crates/verity_shacl/Cargo.toml --all-targets --locked -- -D warnings
cargo test --manifest-path crates/verity_shacl/Cargo.toml --locked
```

The `ShapeConfig` input has this shape; replace every placeholder with values
from the selected files and operator provenance:

```json
{
  "version": 1,
  "shape_snapshot_id": "<shape Snapshot::id()>",
  "data_snapshot_id": "<data Snapshot::id()>",
  "shape_graph": "https://example.org/shapes",
  "data_graph": "https://example.org/data",
  "origin": "source_published",
  "source": {
    "source": "<selected source>",
    "license": "<verified license>",
    "source_revision": "<source release>",
    "importer_revision": "<importer version>"
  }
}
```
