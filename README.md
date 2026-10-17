# Graph Verity

**Ask naturally. Verify against the graph.**

Graph Verity is a local-first RDF question-answering project. Its **deterministic pre-LLM core is implemented on `main`**: manually authored or fixture-supplied typed plans are validated in Rust, compiled into read-only SPARQL, and executed in embedded Oxigraph with scoped RDF evidence.

An opt-in **CPU-only local semantic-parser experiment** is implemented behind the same Rust validation boundary. It evaluates public development questions with oracle vocabulary, reports AI-reference agreement separately from JSON validity and query execution, and preserves model/grammar/prompt/output artifacts. See [the experiment and reproduction command](docs/local-parser-experiment.md). Embeddings, Find/search, SHACL validation and product HTTP serving remain unimplemented. Successful graph execution does not establish that a question was understood or that the graph's statements are true in the world.

## Try the implemented pipeline

The deterministic implementation is on `main`; the separate real-data transfer work is in the issue #5 follow-up PR. Install Rust through rustup and Python 3.12 on Linux; the checked-in toolchain and dependency files pin the versions used by CI. Linux x86-64 / Ubuntu 24.04 is the tested target, not a claim of verification on every platform.

```sh
git clone https://github.com/grove/graph-verity.git
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

The separate [compact intent v2 contract](docs/compact-intent-v2.md) adds indexed
proposals, trusted request context and deterministic expansion into the same validated
v1 plans. Use `schema-compact`, `compact-context` and `compact` to inspect and replay
[public fixtures](examples/compact-v2/) or arbitrary compact JSON without an LLM.
The existing local-model experiment continues to use v1.

## What is implemented

`verity_core` contains bounded RDF ingestion, immutable byte-addressed snapshots, an authorized observed-vocabulary catalog, strict versioned JSON contracts, deterministic query compilation, local execution/evidence, a fixture-backed parser boundary and shared oracle/proposal evaluation. `verity_cli` is a thin local driver.

Supported plans include entity/class references, forward/reverse edges, connected one- and two-hop joins, conjunctions, numeric/date comparisons, projection, `COUNT(DISTINCT)`, `GROUP BY`, `HAVING` and explicit named graphs. Unsupported query syntax, identifiers, types, bindings and graph scopes fail validation. There is no public raw-SPARQL or write endpoint. See [the full contract and resource limits](docs/query-contract.md).

Results distinguish `executed`, `truncated`, abstention and errors. They disclose manual/fixture/local-model origin, `interpretation_correctness: not_assessed`, `real_world_truth: not_established`, result completeness and separately bounded evidence. Missing graph facts do not imply false real-world statements.

## Real data and benchmark status

The first retained real dataset is a **600-quad bounded Wikidata geography capture**, with revision-addressed raw RDF, source hashes, original RDF identifiers and literal metadata. It is not a synthetic procurement dataset and is not representative of the planned serving scale. Norwegian organizational RDF was evaluated as a closer domain fit but was not reproducibly captured in this implementation. See [dataset selection, licensing and extraction](data/wikidata/README.md).

The benchmark contains **130 machine-authored candidate questions**: 46 development cases, 76 templated review candidates and 8 geographic-transfer candidates. Development includes **38 executable queries and 8 recorded clarification/unsupported cases**. Those eight cases are bookkeeping, not demonstrated model abstention. Template reuse does not create independent semantic evidence. None of the gold is represented as expert-approved; no independently reviewed locked holdout has been completed.

Use the [Phase 0 evaluator and preregistration commands](docs/phase-0-evaluation.md) to rescore saved parser outputs, replay them through Rust, verify manifests and assess proposed gates. The baseline is **NOT READY**; see [its decision matrix](reports/phase-0-baseline/summary.md).

The isolated external operator can preregister either independent-human-review evidence
or an explicitly approved, owner-waiver-bound AI-reference comparison. The latter
reports the missing expert review and cannot establish formal GO. The owner approved
the exact experimental budgets and the M1 Pro CPU target on 17 October 2026;
[the pending preregistration record](configs/phase-0-approval.json) pins that decision.
External split-integrity evidence, an immutable freeze and later operator authorization
are still required before the locked run. Public runners and normal CI keep the holdout sealed.

See [benchmark review and evaluation](docs/benchmark-review.md), [proposed numerical gates](configs/phase-0-gates.proposed.json), and [pre-LLM readiness](docs/pre-llm-readiness.md). Compiler-oracle results are not natural-language accuracy or a Phase 0 go decision.

## Real cross-ontology and sealed holdout preparation

A separate CC BY 4.0 **GeoNames-derived Nordic city** snapshot is available at [data/worldcities-transfer](data/worldcities-transfer/README.md): 328 real city records, 62 administrative regions and 1,508 Schema.org N-Quads in five country-named graphs. It is independently sourced from the Wikidata pilot, but the RDF relationship mapping is explicitly an importer transformation. The public [transfer-development benchmark](benchmarks/worldcities-transfer.json) contains 35 executable no-model reference cases and 5 non-model-tested abstention proposals. **These publicly exposed cases are not a locked test set or human-expert gold.**

The private **60-case candidate holdout** is intentionally distributed *outside this public repository*, with only its SHA256 and metadata pinned in [configs/locked-holdout-commitment.json](configs/locked-holdout-commitment.json). Its questions, gold IR and answer bindings must not be placed in the repo, CI artifacts, parser prompts or a coding agent's context. An opt-in, local, metadata-only checksum verifier is in [tools/verify_sealed_holdout.py](tools/verify_sealed_holdout.py). It has not been evaluated on a model or independently expert-reviewed; it also cannot be called a never-seen-ontology test, because Schema.org transfer probes are public development material.

The project owner explicitly approved the prior AI audit and authorized the additional work, as recorded in [issue #5 owner sign-off](docs/issue-5-owner-approval.md). This approval is **not** a claim of expert sign-off on all case-specific gold or on newly created private cases.

## Evaluation standard for the resource-constrained prototype

The project owner has **authorized proceeding without a paid independent human gold reviewer**. The 130 Wikidata candidates were machine-authored and source-audited by AI, and the separate Schema.org transfer cases and external 60-case holdout candidates are **not human-expert validated**. This is an explicitly accepted development limitation, not an achieved expert-review gate.

The human reviewer ledger stays empty and its `review --require-reviewed` checks are not bypassed. The next local-model experiment may compare against the exposed development cases; any later externally held candidate evaluation must be pre-frozen and described as **AI-reference agreement**, not verified Norwegian semantic accuracy. See [Phase 0 risk acceptance](docs/phase-0-ai-gold-risk-acceptance.md) and [benchmark review](docs/benchmark-review.md).

## Run the local semantic-parser experiment

The [local experiment](docs/local-parser-experiment.md) pins Qwen2.5-1.5B-Instruct Q4_K_M, llama.cpp, the embedded tokenizer, ChatML template, grammar and prompt. After one-time `python3 tools/local_parser.py prepare` and `cargo build --locked -p verity_cli`, run `python3 tools/local_parser.py run --out artifacts/local-parser/repeat-1` offline. It owns the loopback-only CPU runtime and evaluates only public `dev` / `transfer_dev` cases; normal CI still runs no inference. Each fresh run preserves raw proposals, failures, component diagnostics, complete parser timings and RAM measurements. Gold remains AI-authored, and the sealed holdout remains unevaluated. This experiment does not approve the numerical Phase 0 gates or establish unrestricted Ask feasibility.

The longer-term design has two distinct modes: **Find** ranks vocabulary/entities and may miss answers; **Ask** executes a validated formal plan within a declared graph scope. Retrieval, SHACL, production serving and hardening remain future work. The [implementation plan](docs/implementation-plan.md) and [Phase 0 feasibility protocol](docs/phase-0-feasibility.md) describe those design goals; this README and readiness report describe the runnable implementation.

## Review and contribution

The model-independent foundation was merged through PRs [#11](https://github.com/grove/graph-verity/pull/11)–[#14](https://github.com/grove/graph-verity/pull/14); benchmark review tooling and the AI audit were added through [#15](https://github.com/grove/graph-verity/pull/15) and [#16](https://github.com/grove/graph-verity/pull/16). The owner explicitly waived expert review for issue #5's **engineering-readiness milestone**; the missing independent evaluation evidence remains a disclosed limitation, not a model-feasibility pass.

Code and original fixtures use [Apache-2.0](LICENSE). Retained Wikidata structured RDF is CC0-1.0 as documented with the dataset. The selected experimental model uses Apache-2.0 and llama.cpp uses MIT; [pinned license details](docs/local-parser-experiment.md#frozen-inputs-and-attribution) remain separate from the graph licenses.

The [issue #9 adversarial suite](docs/adversarial-evaluation.md) adds 30 public
paired-ontology regressions, model-free cross-engine CI checks and an opt-in frozen
model run with per-category false positives, false abstentions and transfer gaps.
The [first frozen-model measurement](reports/issue-9-adversarial/README.md) failed all 30 expected-behavior checks; compiler containment does not establish semantic robustness.

The opt-in [compact v2 CPU runner](docs/compact-v2-runner.md) uses the same pinned
Qwen weights/runtime with Rust-authorized index tables and strict Rust expansion.
Its controls are not a frozen A/B or feasibility result; normal CI runs no inference.
