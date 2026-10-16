# Graph Verity

**Ask naturally. Verify against the graph.**

Graph Verity is a local-first RDF question-answering project. Its **deterministic pre-LLM core is implemented on the feature-branch PR stack**: manually authored or fixture-supplied typed plans are validated in Rust, compiled into read-only SPARQL, and executed in embedded Oxigraph with scoped RDF evidence.

**Natural-language interpretation, local model inference, embeddings, Find/search, SHACL validation and HTTP serving are not implemented.** Successful graph execution does not establish that a question was understood or that the graph's statements are true in the world.

## Try the implemented pipeline

The complete implementation is on `feat/pre-llm-readiness` until the stacked PRs are reviewed and merged. Install Rust through rustup and Python 3.12 on Linux; the checked-in toolchain and dependency files pin the versions used by CI. Linux x86-64 / Ubuntu 24.04 is the tested target, not a claim of verification on every platform.

```sh
git clone --branch feat/pre-llm-readiness https://github.com/grove/graph-verity.git
cd graph-verity
rustup install
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/verify_pre_llm.py
```

The verification command acquires locked Cargo dependencies, checks formatting and Clippy, runs Rust and reporting tests, verifies retained source hashes, rebuilds the dataset byte-for-byte, checks independently written reference queries, checks schema/catalog determinism, runs the development oracle, and demonstrates manual execution, fixture replay and rejected/unsupported proposals. It never refreshes RDF sources, rewrites gold, evaluates review/transfer candidates, downloads a model or invokes inference.

Results and command logs are written to `artifacts/pre-llm/`, including `verification.json`, `summary.md`, and `oracle/report.json` / `oracle/report.md`. CI preserves the directory as a workflow artifact. Build dependencies need network access on a first checkout; data verification and the query runtime use checked-in data locally.

### Manual plan and fixture replay

```sh
cargo run --locked -p verity_cli -- inspect data/wikidata/snapshot.nq nquads
cargo run --locked -p verity_cli -- run data/wikidata/snapshot.nq nquads data/wikidata/policy.json examples/manual-plan.json
cargo run --locked -p verity_cli -- replay data/wikidata/snapshot.nq nquads data/wikidata/policy.json data/wikidata/scope.json examples/question.txt examples/fixture-response.json
cargo run --locked -p verity_cli -- evaluate data/wikidata/snapshot.nq nquads data/wikidata/policy.json benchmarks/wikidata.json dev artifacts/oracle
```

The supplied two-hop example follows Oslo's recorded country relationship and that country's recorded capital relationship. The result is an RDF identifier plus the contributing source statements, query plan, snapshot and scope. The fixture adapter replays a recorded response; it does not understand new Norwegian questions.

Other implemented commands are `schema`, `smoke`, `catalog` and exact `resolve`. The [query contract](docs/query-contract.md) describes the arguments, IR and limitations. [Example plans and responses](examples/) are executable inputs, not proposed APIs.

## What is implemented

`verity_core` contains bounded RDF ingestion, immutable byte-addressed snapshots, an authorized observed-vocabulary catalog, strict versioned JSON contracts, deterministic query compilation, local execution/evidence, a fixture-backed parser boundary and shared oracle/proposal evaluation. `verity_cli` is a thin local driver.

Supported plans include entity/class references, forward/reverse edges, connected one- and two-hop joins, conjunctions, numeric/date comparisons, projection, `COUNT(DISTINCT)`, `GROUP BY`, `HAVING` and explicit named graphs. Unsupported query syntax, identifiers, types, bindings and graph scopes fail validation. There is no public raw-SPARQL or write endpoint. See [the full contract and resource limits](docs/query-contract.md).

Results distinguish `executed`, `truncated`, abstention and errors. They disclose manual/fixture origin, `interpretation_correctness: not_assessed`, `real_world_truth: not_established`, result completeness and separately bounded evidence. Missing graph facts do not imply false real-world statements.

## Real data and benchmark status

The first retained real dataset is a **600-quad bounded Wikidata geography capture**, with revision-addressed raw RDF, source hashes, original RDF identifiers and literal metadata. It is not a synthetic procurement dataset and is not representative of the planned serving scale. Norwegian organizational RDF was evaluated as a closer domain fit but was not reproducibly captured in this implementation. See [dataset selection, licensing and extraction](data/wikidata/README.md).

The benchmark contains **130 machine-authored candidate questions**: 46 development cases, 76 templated review candidates and 8 geographic-transfer candidates. Development includes **38 executable queries and 8 recorded clarification/unsupported cases**. Those eight cases are bookkeeping, not demonstrated model abstention. Template reuse does not create independent semantic evidence. None of the gold is represented as expert-approved; no independently reviewed locked holdout has been completed.

See [benchmark review and evaluation](docs/benchmark-review.md), [proposed numerical gates](configs/phase-0-gates.proposed.json), and [pre-LLM readiness](docs/pre-llm-readiness.md). Compiler-oracle results are not natural-language accuracy or a Phase 0 go decision.

## Next: the local semantic-parser experiment

After explicit authorization, implement the local inference backend behind `SemanticParser`, pin and test the actual runtime/grammar/model combination, and preserve independent Rust validation. First evaluate development questions with authorized vocabulary; freeze the approved protocol and independent holdout before making feasibility claims. [The integration handoff](docs/local-parser-handoff.md) records prerequisites and pending measurements.

The longer-term design has two distinct modes: **Find** ranks vocabulary/entities and may miss answers; **Ask** executes a validated formal plan within a declared graph scope. Retrieval, model inference, SHACL, production serving and hardening remain future work. The [implementation plan](docs/implementation-plan.md) and [Phase 0 feasibility protocol](docs/phase-0-feasibility.md) describe those design goals; this README and readiness report describe the runnable implementation.

## Review and contribution

Review the stacked changes in order: [foundation #11](https://github.com/grove/graph-verity/pull/11), [core #12](https://github.com/grove/graph-verity/pull/12), [dataset/benchmark #13](https://github.com/grove/graph-verity/pull/13), then the readiness/verification PR. No PR is automatically merged. Human RDF/benchmark review is still needed before closing the related Phase 0 acceptance gates.

Code and original fixtures use [Apache-2.0](LICENSE). Retained Wikidata structured RDF is CC0-1.0 as documented with the dataset. Model/runtime licenses will require separate review when a model is selected.
