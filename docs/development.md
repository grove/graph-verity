# Development: deterministic foundation

The initial verified target is Linux x86-64 (`ubuntu-24.04` CI). Other platforms require testing.
Rust is pinned in `rust-toolchain.toml`; the generated `Cargo.lock` pins transitive dependencies.
Oxigraph runs in memory, with default features disabled: no RocksDB or HTTP client.

```sh
rustup install
cargo build --workspace --locked
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
cargo run --locked -p verity_cli -- inspect tests/fixtures/smoke.trig trig
cargo run --locked -p verity_cli -- smoke tests/fixtures/smoke.trig trig
```

The original 14-quad synthetic fixture is under the repository's Apache-2.0 license.
It tests directions, named graphs, Norwegian labels, integers, decimals and dates.
It is not a real-domain feasibility benchmark.

Inputs are bounded to 16 MiB and 100,000 stored quads. Turtle, TriG and N-Quads are parsed
by Oxigraph. Named graphs and RDF term metadata are preserved by the loader. The snapshot
ID hashes release bytes plus the declared serialization, not RDF graph isomorphism.
Equivalent alternative serializations therefore have different IDs. Blank-node labels are
snapshot-local, not global resource identities. The immutable store is process-local;
commands reload supplied input. The smoke query is fixed, not an arbitrary-SPARQL API.

The one-time branch-only dependency/formatting workflow has been removed. Normal CI uses
read-only repository permissions and locked dependencies; it never updates gold results,
formats source, downloads model weights, or grants itself permission to merge a PR.

The opt-in [local parser experiment](local-parser-experiment.md) builds and runs a pinned
CPU model separately. Normal CI invokes no inference and downloads no model weights.
CI success verifies only its model-free tests, not parser feasibility on deployment hardware.

For issue #8, `tools/phase0.py report|replay|verify|assess|compare` provides the model-free evaluation workflow. `verify_pre_llm.py` runs its regressions, report generation and Rust replay in ordinary CI. See [the protocol, approval/freeze boundaries and isolated operator command](phase-0-evaluation.md).
