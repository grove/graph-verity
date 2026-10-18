# Graph Verity

**Ask natural-language questions about RDF knowledge graphs. Inspect the source evidence.**

**Long-term product goal:** ask Norwegian or English questions about an authorized RDF graph and receive verifiable *graph-supported* answers without writing SPARQL. **Phase 2** has now begun as a controlled R&D milestone for a **local, one-hop, model-drafted question → typed Rust plan → explicit user confirmation → read-only Oxigraph answer** workflow. No reliable model interpreter or unattended Ask is currently approved or shipped. See the [Phase 2 roadmap](docs/phase-2-natural-language-ask.md) and [tracking epic #71](https://github.com/grove/graph-verity/issues/71).

As an interim engineering foundation, Graph Verity has a local-first RDF exploration implementation. **Phase 0 selected a Find-first MVP and stopped unattended free-form Ask with the tested Qwen2.5-1.5B v1/compact-v2 configurations.** See the [decision, evidence and roadmap](docs/phase-0-decision.md) and [machine-readable record](docs/phase-0-decision.json). A measured local [BM25 Find baseline](docs/find-baseline.md) is implemented; its AI-judged public evidence does not establish stakeholder quality. Its **deterministic pre-LLM core is implemented on `main`**: manually authored or fixture-supplied typed plans are validated in Rust, compiled into read-only SPARQL, and executed in embedded Oxigraph with scoped RDF evidence.

An opt-in **CPU-only local semantic-parser experiment** is implemented behind the same Rust validation boundary. It evaluates public development questions with oracle vocabulary, reports AI-reference agreement separately from JSON validity and query execution, and preserves model/grammar/prompt/output artifacts. See [the experiment and reproduction command](docs/local-parser-experiment.md). The [authorized discovery catalog](docs/discovery-catalog.md) now builds deterministic graph-scoped lexical postings from retained snapshots. The [BM25 CLI and frozen retrieval evaluation](docs/find-baseline.md) rank that catalog. An opt-in [pinned EmbeddingGemma 2 comparison](docs/embedding-experiment.md) evaluates embeddings and fixed fusion against BM25. Embedding integration into Find and SHACL validation remain unimplemented. An operator-started [local Find browser pilot](docs/local-find-ui.md) serves BM25 and graph evidence on loopback only. Successful graph execution does not establish that a question was understood or that the graph's statements are true in the world.

## Active product roadmap: Phase 2 grounded NL Ask

The intended user experience starts with **"Ask a question"**, not with a mandatory graph-exploration or A/B relevance-review screen. Search and the graph explorer remain tools for vocabulary grounding, human disambiguation, advanced inspection and debugging; the blinded Research Review is a separate experiment, **not** the product.

- **[#72](https://github.com/grove/graph-verity/issues/72):** freeze a supported one-hop Norwegian/English question-to-draft contract and semantic benchmark, distinguishing plausible-but-wrong executable plans from true question understanding.
- **[#73](https://github.com/grove/graph-verity/issues/73):** build graph-qualified, gold-free BM25 vocabulary packets for the model and diagnose missing start/predicate/direction coverage. EmbeddingGemma 2 remains an experimental retrieval variant pending its separate review.
- **[#74](https://github.com/grove/graph-verity/issues/74):** the [controlled one-hop trial](reports/issue-74-one-hop-trial/README.md) stopped at host preflight with both candidates unattempted; the frozen #72/#73 coverage and offline scorer are reproducible. Dedicated-host inference remains inconclusive. Metal requires a separate supported variant; #48 remains unchanged.
- **[#75](https://github.com/grove/graph-verity/issues/75):** build an **explicitly opted-in** NL Ask UI which presents an untrusted model draft and the complete authoritative Rust plan. A separate user approval is required before any execution.
- **[#76](https://github.com/grove/graph-verity/issues/76):** assess actual one-hop query fidelity, strict RDF answers, unsupported/clarification outcomes, wrong-but-executable plans, human false confidence and resource cost before any further promotion decision.

These are **new implementation issues, not claims of completed features**. Existing [Confirmed Ask](docs/confirmed-ask.md) remains manually assembled and user-confirmed; **no language model** is connected to its execution path today. Phase 0's [STOP/REVISE evidence](docs/phase-0-decision.md) remains valid for the earlier tested unattended configurations. A passing model-free CI or executable plan does not establish that the question was understood.

## Try the implemented pipeline

The deterministic implementation and real-data transfer fixtures are on `main`. Install Rust through rustup and Python 3.12 on Linux; the checked-in toolchain and dependency files pin the versions used by CI. Linux x86-64 / Ubuntu 24.04 is the tested target, not a claim of verification on every platform.

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

For the [offline local browser UI](docs/local-find-ui.md), run `cargo build --locked --offline -p verity_cli` then `python3 tools/local_find.py` and open the private session URL printed in the terminal. Norwegian/English controls cover scoped search, deliberate graph-qualified selection and original directed RDF evidence. The optional exact `follow_path` editor adds one/two-hop plans, typed filters and distinct counts with a complete Rust preview and a separate expiring, single-use confirmation. Stop with Ctrl-C. This is an engineering pilot, not a completed user study.

For a retained public corpus, use the [one-command offline presets](docs/find-pilot-presets.md):
`python3 tools/launch_find_pilot.py wikidata-development`, `worldcities-norway`, or
`gemet-4.2.3` (Python 3.11+). These launch the existing v1 interface with verified
source/license inputs and a fixed authorized scope. An interested pilot user's
next step is to try one corpus and bring one concrete question, chosen IRI and
original directed evidence to the maintainer. There are currently **no documented
successful human participant tasks and no product-release GO**.

The separate [Find UI v2 prototype](docs/local-find-ui-v2.md) (`python3 tools/local_find_v2.py`) adds explicit exact-identifier warnings, original text witnesses and directed RDF statements while reusing the unchanged v1 backend. It is not the frozen participant interface and makes no measured usability claim.

The [frozen local pilot study kit](studies/pilot-v1/README.md) adds consent-aware offline operator forms, source-backed bilingual tasks and deterministic aggregate reporting. **Real participants: 0; human attempts: 0.** Issue #57 remains blocked/open pending genuine volunteers; the synthetic rehearsal is not human evidence or a release GO.

Use `find` for [scoped BM25 rankings and exact identifiers/aliases](docs/find-baseline.md). The [Find and graph-evidence CLI MVP](docs/find-mvp.md) adds match explanations and `entity` for directed, paged relationships with supporting triples and snapshot provenance. Follow its offline Norwegian/English → Norway → capital relationship → Oslo walkthrough. **Pilot scope is local, scoped exploration:** [predicate-label retrieval and conservative ambiguity/no-match states](docs/find-quality.md) now use explicit graph-local mapping witnesses. See the [fresh quality report](reports/issue-46-find-quality/README.md), which compares the unchanged frozen cases against the immutable [#39 release](reports/issue-39-find-mvp/README.md). Human quality and real-domain scale readiness remain unestablished; fusion stays deferred. The separate [real RDF hybrid study #50](reports/issue-50-real-rdf-hybrid/README.md) freezes 122 retrieval-only queries and 2,215 GEMET/SKOS resources, comparing unchanged #46 text and a separately versioned SKOS-definition representation. Its opt-in CPU experiment and model-free CI replay preserve the source/scope witnesses and leave BM25 as the default.

The opt-in [selective hybrid study #53](reports/issue-53-selective-hybrid/README.md) preserves exact matches, bounds semantic fill and removes duplicate resident model ownership. Its 50 new source-grounded questions remain AI-reference exploratory: the historical-text strategy fails no-match nonregression, and independent relevance review is unavailable. BM25 remains the default; the frozen experiment and all four controls replay in CI without inference.

The [blinded hybrid review kit #58](studies/hybrid-review-v1/README.md) adds a reviewer-only offline side-by-side replay, 20 new preregistered bilingual tasks and private consent-aware judgments. **Human reviewers: 0; recommendation: defer.** The [separate promotion proposal](reports/issue-58-human-review/README.md) leaves #58 open pending real participants; BM25 remains the default. Run `python3 tools/hybrid_review.py serve --demo` for the model-free exposed-regression demo.

For the committed saved-results study, use the [frozen offline handoff](studies/hybrid-review-handoff/README.md): `python3 tools/hybrid_review_launcher.py prepare` verifies and prepares the pinned #64 source and capture with Python's standard library only. The guide covers separate consenting reviewers, source interpretation, withdrawal and private reporting; preparation creates no participant records.

Use `index-build` and `index-inspect` for the [versioned discovery catalog and manifest](docs/discovery-catalog.md), including Norwegian/English labels, observed aliases, identifiers and bounded descriptions. Each resource retains its original RDF IRI and graph provenance; all postings and statistics are authorized before construction.

The opt-in [experimental Confirmed Ask prototype](docs/confirmed-ask.md) adds `ask-preview` and `ask`: deliberately select an exact one/two-step directed path, optional typed filter and values/distinct count, then approve the complete plan bound to its graph scope, immutable snapshot and policy. Cancellation, missing/stale approval and invalid scope never execute. No model is connected. [Automated regression evidence and the pending human usability evaluation](reports/issue-40-confirmed-ask/README.md) do not establish user demand, reliable question interpretation or production/release readiness.

The model-free [NL Ask draft v1 boundary](docs/nl-ask-draft-v1.md) adds strict one-hop candidate-ID expansion to a Confirmed Ask preview, with a [60-case bilingual preregistration](studies/nl-ask-v1/README.md). No model is run or automatically approved; AI-authored references have zero independent human reviews.

The separate [compact intent v2 contract](docs/compact-intent-v2.md) adds indexed
proposals, trusted request context and deterministic expansion into the same validated
v1 plans. Use `schema-compact`, `compact-context` and `compact` to inspect and replay
[public fixtures](examples/compact-v2/) or arbitrary compact JSON without an LLM.
The local-model runner defaults to v1 and offers an opt-in compact v2 route.

## What is implemented

`verity_core` contains bounded RDF ingestion, immutable byte-addressed snapshots, an authorized observed-vocabulary catalog, strict versioned JSON contracts, deterministic query compilation, local execution/evidence, a fixture-backed parser boundary and shared oracle/proposal evaluation. `verity_cli` is a thin local driver.

Supported plans include entity/class references, forward/reverse edges, connected one- and two-hop joins, conjunctions, numeric/date comparisons, projection, `COUNT(DISTINCT)`, `GROUP BY`, `HAVING` and explicit named graphs. Unsupported query syntax, identifiers, types, bindings and graph scopes fail validation. There is no public raw-SPARQL or write endpoint. See [the full contract and resource limits](docs/query-contract.md).

Results distinguish `executed`, `truncated`, abstention and errors. They disclose manual/fixture/local-model origin, `interpretation_correctness: not_assessed`, `real_world_truth: not_established`, result completeness and separately bounded evidence. Missing graph facts do not imply false real-world statements.

## Real data and benchmark status

The first retained real dataset is a **600-quad bounded Wikidata geography capture**, with revision-addressed raw RDF, source hashes, original RDF identifiers and literal metadata. It is not a synthetic procurement dataset and is not representative of the planned serving scale. Norwegian organizational RDF was evaluated as a closer domain fit but was not reproducibly captured in this implementation. See [dataset selection, licensing and extraction](data/wikidata/README.md).

The benchmark contains **130 machine-authored candidate questions**: 46 development cases, 76 templated review candidates and 8 geographic-transfer candidates. Development includes **38 executable queries and 8 recorded clarification/unsupported cases**. Those eight cases are bookkeeping, not demonstrated model abstention. Template reuse does not create independent semantic evidence. None of the gold is represented as expert-approved; no independently reviewed locked holdout has been completed.

Use the [Phase 0 evaluator and preregistration commands](docs/phase-0-evaluation.md) to rescore saved parser outputs, replay them through Rust, verify manifests and assess proposed gates. Formal feasibility remains **NOT READY**; the engineering outcome is **STOP tested unattended Ask / REVISE Find-first**. See the [historical baseline matrix](reports/phase-0-baseline/summary.md) and [final decision](docs/phase-0-decision.md).

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

The human reviewer ledger stays empty and its `review --require-reviewed` checks are not bypassed. The retained local-model experiments compare against exposed development cases; any later externally held candidate evaluation must be pre-frozen and described as **AI-reference agreement**, not verified Norwegian semantic accuracy. See [Phase 0 risk acceptance](docs/phase-0-ai-gold-risk-acceptance.md) and [benchmark review](docs/benchmark-review.md).

## Run the local semantic-parser experiment

The [local experiment](docs/local-parser-experiment.md) pins Qwen2.5-1.5B-Instruct Q4_K_M, llama.cpp, the embedded tokenizer, ChatML template, grammar and prompt. After one-time `python3 tools/local_parser.py prepare` and `cargo build --locked -p verity_cli`, run `python3 tools/local_parser.py run --out artifacts/local-parser/repeat-1` offline. It owns the loopback-only CPU runtime and evaluates only public `dev` / `transfer_dev` cases; normal CI still runs no inference. Each fresh run preserves raw proposals, failures, component diagnostics, complete parser timings and RAM measurements. Gold remains AI-authored, and the sealed holdout remains unevaluated. This experiment does not establish unrestricted Ask feasibility. The later owner budget/target approval remains pending external split integrity and formal freeze.

## Phase 0 outcome and next build

The original 86-question development experiment returned reference answer bindings on **3/73 supported questions** and correct model abstentions on **0/13**. On 30 adversarial questions, v1 versus compact v2 improved valid contracts **22/30 → 28/30**, but complete answers stayed **0/24** and correct abstentions **0/6**. V1 executed four wrong plans; v2 executed none because deterministic checks rejected or blocked every candidate. Compact v2 also increased tokens and latency. These are public AI-reference measurements, not expert-reviewed accuracy or a sealed-holdout result. The evidence supports stopping these unattended Ask configurations, not a claim about every small model.

The [Find-first plan](docs/phase-0-decision.md#selected-next-scope-a-find-first-mvp) is ordered: [authorized bilingual catalog #36](https://github.com/grove/graph-verity/issues/36), [BM25 baseline #37](https://github.com/grove/graph-verity/issues/37), [pinned EmbeddingGemma comparison #38](https://github.com/grove/graph-verity/issues/38), then [Find/navigation/evidence MVP #39](https://github.com/grove/graph-verity/issues/39). EmbeddingGemma may improve semantic retrieval; adoption requires measured Recall@k/MRR gains within CPU/RAM budgets. A lexical-only result is acceptable. The [Find-quality iteration #46](docs/find-quality.md) adds explicit predicate mapping provenance, conservative candidate states and a separate development-only fusion review. [Optional constrained Ask #40](docs/confirmed-ask.md) now has separate owner authorization for an experimental opt-in prototype. User need remains a hypothesis; production/release GO and demonstrated usability remain separate requirements. Unattended free-form Ask stays disabled as a product direction.

Reuse the authorized catalog/exact resolution, typed IR, validation, read-only compiler, snapshot execution, bounded evidence and replay/evaluation infrastructure. **Successful query execution proves what a particular plan returned in a snapshot. Correct question interpretation is a separate claim. Supporting triples provide graph evidence; none establishes real-world truth.** Find rankings are partial discovery, and absent triples remain unknown.

Production ingestion/serving, full SHACL and GNNs are outside this next MVP. The older [architecture plan](docs/implementation-plan.md) is retained as design context and is superseded by the [Phase 0 decision](docs/phase-0-decision.md) for scope and schedule.

## Review and contribution

The model-independent foundation was merged through PRs [#11](https://github.com/grove/graph-verity/pull/11)–[#14](https://github.com/grove/graph-verity/pull/14); benchmark review tooling and the AI audit were added through [#15](https://github.com/grove/graph-verity/pull/15) and [#16](https://github.com/grove/graph-verity/pull/16). The owner explicitly waived expert review for issue #5's **engineering-readiness milestone**; the missing independent evaluation evidence remains a disclosed limitation, not a model-feasibility pass.

Code and original fixtures use [Apache-2.0](LICENSE). Retained Wikidata structured RDF is CC0-1.0 as documented with the dataset. The selected experimental model uses Apache-2.0 and llama.cpp uses MIT; [pinned license details](docs/local-parser-experiment.md#frozen-inputs-and-attribution) remain separate from the graph licenses.

The [issue #9 adversarial suite](docs/adversarial-evaluation.md) adds 30 public
paired-ontology regressions, model-free cross-engine CI checks and an opt-in frozen
model run with per-category false positives, false abstentions and transfer gaps.
The [first frozen-model measurement](reports/issue-9-adversarial/README.md) failed all 30 expected-behavior checks; compiler containment does not establish semantic robustness.

The opt-in [compact v2 CPU runner](docs/compact-v2-runner.md) uses the same pinned
Qwen weights/runtime with Rust-authorized index tables and strict Rust expansion.
The separate [M1 Pro route comparison](reports/issue-32-compact-ab/README.md)
retains the single public v2 run against frozen v1. Normal CI verifies saved evidence
without inference; this comparison does not establish Phase 0 readiness.

Experimental Phase 2 grounding: [question vocabulary packet v1](docs/question-vocabulary-packet-v1.md) provides source-authorized, graph-qualified BM25 candidate tables and model-free saved-packet replay. It does not execute natural-language questions; the [#72 contract and evaluation manifest](studies/nl-ask-v1/README.md) are frozen, with independent human review still pending.

Run all Python regressions with `python tools/run_python_tests.py`; the unchanged #57 pilot and #53 native replay use their original source fingerprints from a pinned historical commit. The remaining suites and lexical rank/score checks test current code.
