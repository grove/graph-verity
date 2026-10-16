# Pre-LLM engineering readiness

Historical report for the deterministic milestone. The subsequently authorized
local-model experiment is documented in [local-parser-experiment.md](local-parser-experiment.md).

## Scope and status

The deterministic chain is implemented and has passed clean-checkout verification: **manual/fixture IR -> Rust validation -> deterministic SPARQL -> Oxigraph -> scoped evidence -> oracle report**. No model inference is implemented or authorized by this milestone. This is readiness for a first local development experiment, not a Phase 0 feasibility pass, production release, independently reviewed benchmark or authorization to start inference.

Review order is [foundation #11](https://github.com/grove/graph-verity/pull/11), [core #12](https://github.com/grove/graph-verity/pull/12), [dataset/benchmark #13](https://github.com/grove/graph-verity/pull/13), then [readiness/verification #14](https://github.com/grove/graph-verity/pull/14). Each PR targets its predecessor's branch; the cumulative implementation is `feat/pre-llm-readiness`. Nothing is merged automatically and `main` is not modified by this work.

## Implemented components

Two Rust crates; pinned toolchain and dependency lock; bounded Turtle/TriG/N-Quads input; immutable byte-identified snapshots; scoped classes/predicates/entities and exact-label ambiguity handling; typed IR/JSON Schema; directed connected joins, numeric/date filters, distinct counts/grouping/HAVING/projection; strict scope and vocabulary validation; bounded results and separately bounded contributing statements; manual/fixture provenance and honest truth/completeness fields; parser contracts with exact fixture replay; shared oracle/proposal result scoring; retained real RDF and frozen reference bindings; read-only full verification and CI artifacts.

See `docs/query-contract.md` for supported semantics and bounds, `docs/benchmark-review.md` for scoring/review, `data/wikidata/README.md` for source selection, and `docs/local-parser-handoff.md` for the actual next runtime task.

## Observed clean-checkout verification

[Actions run 38905166389](https://github.com/grove/graph-verity/actions/runs/38905166389), job `116986790888`, completed successfully on **16 October 2026**, testing commit **`86257d58a2dfe203b17c66a4a1eda94303503cb8`** from a fresh checkout. The downloaded artifact's `verification.json`, command logs and oracle report were inspected; these are observed results, not expected outcomes.

| Check | Observed result |
|---|---|
| Rust formatting and Clippy with warnings denied | Passed |
| Rust unit tests | 2 passed, 0 failed |
| Rust integration tests | 19 passed, 0 failed |
| Reporting/denominator regression tests | 5 passed, 0 failed |
| Source hashes and byte-identical dataset rebuild | Passed |
| Independent development reference queries and frozen bindings | Passed |
| Generated JSON Schema parity and independently reloaded catalog determinism | Passed |
| Executable development oracle cases | 38/38 passed |
| Expected clarification/unsupported records | 8 recorded; not model-tested and excluded from executable accuracy |
| Manual plan and fixture replay with scoped evidence | Passed |
| Malformed proposal rejection and fixture unsupported outcome | Passed |
| Tracked source unchanged before/after verification | Passed |
| Model invocation / locked holdout evaluation | Neither performed |

The runner reported Linux x86-64, four visible logical CPUs, an AMD EPYC 7763 CPU model and Rust 1.99.1. This is **CI provenance**, not the approved local-model target hardware or a performance guarantee. The oracle was a debug build over a small graph; do not extrapolate its timings to inference or pilot scale.

The run artifact is `pre-llm-verification-86257d58a2dfe203b17c66a4a1eda94303503cb8`, artifact ID `12047383673`, retained by Actions for 30 days. It contains `verification.json`, `summary.md`, `oracle/report.json`, `oracle/report.md`, reconstructed RDF and per-command stdout/stderr. The verification command regenerates reports after artifact expiry without refreshing source data or gold. This documentation-only update records that immutable run; later source changes require their own successful verification.

The final read-only workflow never fixes files or commits to branches. A failed command exits nonzero and is retained in the artifact. No failed check may be replaced by regenerated gold. The malformed-response demonstration intentionally returns a nonzero status and is recorded as an expected rejection, not a failing test.

For historical context, [capture run 38901596716](https://github.com/grove/graph-verity/actions/runs/38901596716) also passed the earlier Rust/oracle/manual checks, but it changed its worktree while capturing assets. The clean-checkout run above supersedes it as reproducibility evidence. The temporary write-enabled capture workflow has been removed.

The authoring container has no Rust toolchain and could not resolve GitHub for a direct clone. Rust verification was performed on GitHub Actions, not in the chat container. The documented command reproduces the checks on a suitably provisioned local checkout.

## Coverage and limits

The selected real capture has **600 quads**, 13 primary source entities plus a retained earlier Oslo revision, original identifiers and typed/language-tagged literals. It is tiny compared with the intended serving scale and uses geography rather than the preferred organizational/procurement domain. Wikidata structured entity RDF is CC0-1.0; retain the source manifest and consult its licensing references. Assigned named graphs belong to this importer, not the source publisher.

There are **130 candidate questions**, not 130 independent approved tests: 46 development cases (38 executable, eight recorded abstentions), 76 templated review candidates, eight same-ontology geographic-transfer candidates. All are human-review pending. The retained older Oslo revision is not a coherent historical snapshot across all entities. Some raw Wikidata temporal literals are outside the supported Python/Rust comparison ranges; source bytes remain retained, and unsupported comparisons must fail rather than silently coerce dates. RDFLib reports warnings for retained out-of-range temporal literals; these did not fail the source-byte verification or the supported development queries.

Evidence is a bounded union of contributing statements, not proof that a natural-language interpretation is right. Aggregate counts require the full scoped query and snapshot, not just positive witnesses. Empty results are not proof of absence in the world. Default-graph Ask, unrestricted SPARQL/paths/negation, full entailment, SHACL, embeddings, HTTP serving and production authorization infrastructure remain out of scope.

Cancellation is cooperative, not hard memory isolation; adversarial intermediate joins still require OS-level limits. General blank-node canonicalization is not implemented. Snapshot hashes identify exact input bytes/configuration, not graph-isomorphism classes. Observed datatype profiles can conservatively reject valid questions over mixed data. Structural IR equality can reject equivalent plans and needs a declared policy before model scoring.

## Outstanding human work

Review the Rust authorization/compiler/evidence boundary and PR diffs. Independently review Norwegian questions, graph interpretation, missing-data cases and gold SPARQL/results. Confirm the source/domain is suitable for the first experiment and plan a larger realistic domain before a pilot. Create an independently authored locked holdout with paraphrase/template separation; approve and freeze numerical gates and actual target hardware. Confirm model/runtime licenses when choosing a checkpoint.

Issues #3–#9 remain open for PR review and any unmet acceptance criteria; the model-dependent portions of #7/#8/#9, expert gold in #5/#6, meaningful transfer and true locked holdout are not represented as complete. Parent #2 and decision #10 cannot be closed on compiler results alone.

## Reproduce

```sh
git clone --branch feat/pre-llm-readiness https://github.com/grove/graph-verity.git
cd graph-verity
rustup install
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/verify_pre_llm.py
```

For the exact recorded implementation, check out commit `86257d58a2dfe203b17c66a4a1eda94303503cb8` before running the commands. For only the oracle: `cargo run --locked -p verity_cli -- evaluate data/wikidata/snapshot.nq nquads data/wikidata/policy.json benchmarks/wikidata.json dev artifacts/oracle`.

## Exact next task

After explicit authorization, integrate one bounded local llama.cpp proposal backend behind `SemanticParser`, with pinned artifacts, real grammar enforcement tests and honest model origin/metadata, then run development-only semantic comparisons. See the handoff. Before that authorization, no inference step should be executed. Full feasibility additionally depends on the human/holdout/target-device gates above.
