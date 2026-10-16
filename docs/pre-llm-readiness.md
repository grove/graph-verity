# Pre-LLM engineering readiness

## Scope and status

The deterministic chain is implemented: **manual/fixture IR -> Rust validation -> deterministic SPARQL -> Oxigraph -> scoped evidence -> oracle report**. No model inference is implemented or authorized by this milestone. This is readiness for a first local development experiment, not a Phase 0 feasibility pass, production release, independently reviewed benchmark or authorization to start inference.

Review order is foundation PR #11, core PR #12, dataset/benchmark PR #13, then the readiness/verification PR. Each PR targets its predecessor's branch; the cumulative implementation is `feat/pre-llm-readiness`. Nothing is merged automatically and `main` is not modified by this work.

## Implemented components

Two Rust crates; pinned toolchain and dependency lock; bounded Turtle/TriG/N-Quads input; immutable byte-identified snapshots; scoped classes/predicates/entities and exact-label ambiguity handling; typed IR/JSON Schema; directed connected joins, numeric/date filters, distinct counts/grouping/HAVING/projection; strict scope and vocabulary validation; bounded results and separately bounded contributing statements; manual/fixture provenance and honest truth/completeness fields; parser contracts with exact fixture replay; shared oracle/proposal result scoring; retained real RDF and frozen reference bindings; read-only full verification and CI artifacts.

See `docs/query-contract.md` for supported semantics and bounds, `docs/benchmark-review.md` for scoring/review, `data/wikidata/README.md` for source selection, and `docs/local-parser-handoff.md` for the actual next runtime task.

## Observed verification before this final verification PR

[Actions run 38901596716](https://github.com/grove/graph-verity/actions/runs/38901596716), job 116974910574, completed successfully on 16 October 2026. It captured/committed assets and then tested the resulting worktree ending at commit `816a48837fcf21efb1ea9db966f342426815df7c`; its starting event SHA was earlier, so it must not be represented as a clean-checkout test of that starting SHA.

Its logs show formatting and Clippy passing, **2 Rust unit tests plus 19 integration tests passing**, source/rebuild/reference checks passing, **38/38 executable development oracle queries matching frozen gold**, and eight expected abstention records. The manual and exact-fixture two-hop examples executed with scoped supporting statements. The original one-time capture workflow has now been removed.

The final read-only workflow runs from an ordinary checkout, never fixes files or commits to branches, checks source/schema/catalog reproducibility and saves precise command outcomes. Its authoritative results are `artifacts/pre-llm/verification.json`, `summary.md`, captured stdout/stderr, and the oracle reports. Consult the actual latest Actions run rather than treating the historical run above as evidence for untested later changes. A failed command exits nonzero and is retained in the artifact. No failed check may be replaced by regenerated gold.

The authoring container has no Rust toolchain and cannot resolve GitHub for a direct clone. Rust verification is therefore performed on GitHub Actions, not claimed to have run in the chat container. The documented command reproduces the checks on a suitably provisioned local checkout.

## Coverage and limits

The selected real capture has **600 quads**, 13 primary source entities plus a retained earlier Oslo revision, original identifiers and typed/language-tagged literals. It is tiny compared with the intended serving scale and uses geography rather than the preferred organizational/procurement domain. Wikidata structured entity RDF is CC0-1.0; retain the source manifest and consult its licensing references. Assigned named graphs belong to this importer, not the source publisher.

There are **130 candidate questions**, not 130 independent approved tests: 46 development cases (38 executable, eight recorded abstentions), 76 templated review candidates, eight same-ontology geographic-transfer candidates. All are human-review pending. The retained older Oslo revision is not a coherent historical snapshot across all entities. Some raw Wikidata temporal literals are outside Python/Rust's supported comparison ranges; source bytes remain retained, and unsupported comparison cases must fail rather than silently coerce dates.

Evidence is a bounded union of contributing statements, not a proof that a natural-language interpretation is right. Aggregate counts require the full scoped query and snapshot, not just positive witnesses. Empty results are not proof of absence in the world. Default-graph Ask, unrestricted SPARQL/paths/negation, full entailment, SHACL, embeddings, HTTP serving and production authorization infrastructure remain out of scope.

Cancellation is cooperative, not hard memory isolation; adversarial intermediate joins still require OS-level limits. General blank-node canonicalization is not implemented. Snapshot hashes identify exact input bytes/configuration, not graph-isomorphism classes. Observed datatype profiles can conservatively reject valid questions over mixed data. Structural IR equality can reject equivalent plans and needs a declared policy before model scoring. CI debug-mode timings are not a local-model performance guarantee.

## Outstanding human work

Review the Rust authorization/compiler/evidence boundary and PR diffs. Independently review Norwegian questions, graph interpretation, missing-data cases and gold SPARQL/results. Confirm the source/domain is suitable for the first experiment and plan a larger realistic domain before a pilot. Create an independently authored locked holdout with paraphrase/template separation; approve and freeze numerical gates and actual target hardware. Confirm model/runtime licenses when choosing a checkpoint.

Issues #4/#5/#8/#9 remain partially open where acceptance depends on independent review, meaningful transfer, model behavior, final target-device measurements or a true locked holdout. Issue #7 remains open because inference is deliberately absent. Parent #2 and decision #10 cannot be closed on compiler results alone.

## Reproduce

```sh
git clone --branch feat/pre-llm-readiness https://github.com/grove/graph-verity.git
cd graph-verity
rustup install
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/verify_pre_llm.py
```

For only the oracle: `cargo run --locked -p verity_cli -- evaluate data/wikidata/snapshot.nq nquads data/wikidata/policy.json benchmarks/wikidata.json dev artifacts/oracle`.

## Exact next task

After explicit authorization, integrate one bounded local llama.cpp proposal backend behind `SemanticParser`, with pinned artifacts, real grammar enforcement tests and honest model origin/metadata, then run development-only semantic comparisons. See the handoff. Before that authorization, no further inference step should be executed. Full feasibility additionally depends on the human/holdout/target-device gates above.
