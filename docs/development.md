# Development: deterministic foundation

This branch introduces executable Rust code. It does not integrate or benchmark an LLM.
The initial target is Linux x86-64 (`ubuntu-24.04` CI); other platforms are not yet verified.
Rust is pinned in `rust-toolchain.toml`. Oxigraph runs in memory, without RocksDB or an HTTP client.

```sh
rustup show
cargo build --workspace
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo run -p verity_cli -- inspect tests/fixtures/smoke.trig trig
cargo run -p verity_cli -- smoke tests/fixtures/smoke.trig trig
```

The 14-quad fixture is original synthetic data under this repository's Apache-2.0 license.
It covers directions, named graphs, Norwegian labels, integers, decimals and dates. It is not
an acceptable substitute for the real-data feasibility benchmark.

Inputs are limited to 16 MiB and 100,000 stored quads. Turtle, TriG and N-Quads are parsed by
Oxigraph; identifiers, literal metadata and graph membership are not rewritten. The snapshot
ID hashes the original release bytes plus the declared serialization. It is intentionally not\an RDF-isomorphism or blank-node-canonicalization hash. Equivalent alternative serializations
therefore have different IDs. The immutable store is process-local; inspection and the smoke
query load the supplied release on each invocation. There is no arbitrary-SPARQL CLI.

The initial bootstrap workflow resolves a lockfile and prints it for review. Committing that
lockfile and switching CI to locked-only dependency resolution is required before calling the
build reproducible. Tests and CI must actually pass; a workflow file alone is not evidence.
