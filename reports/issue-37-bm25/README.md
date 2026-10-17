# Issue #37: measured BM25 Find baseline

**Exploratory AI-judged result: overall Recall@10 misses the proposed pilot target.** This is a reproducible lexical baseline, not stakeholder quality, Phase 0 approval, or production scale acceptance. No human review or sealed Ask holdout was used.

The baseline uses the authorized #36 catalog, fixed BM25 (`k1=1.2`, `b=0.75`), exact identifier/label/alias tiers, graph-qualified documents and graph/role filters before statistics. The [contract and commands](../../docs/find-baseline.md) describe the scope and limits.

## Public retrieval agreement

The [freeze](../../benchmarks/retrieval/manifest.json) predates ranking: **80 development + 80 separate public evaluation formulations**, each 40 Norwegian/40 English, ten per family. Both share the same 80 intents and AI judgments. Sixty relevant cases (30/language) are scored per split; ten ambiguous and ten no-match cases are reported separately. All errors/misses remain in their designated denominators. No relevance parameters or judgments were tuned after scoring. Proper names, alias variants and collision prefixes are correlated; neither set is independent human gold.

Development and evaluation happen to have identical aggregate/per-family scores. Each table entry gives mean **[descriptive 95% interval]**, from 2,000 query-level percentile bootstrap resamples (seed 37). Identical outcomes can produce degenerate intervals; these are not population guarantees. Full per-language/family cross-tabs and both splits are in [summary.json](run/summary.json).

| Group (each split) | n | Recall@1 | Recall@5 | Recall@10 | Recall@50 | MRR@10 |
| --- | ---: | --- | --- | --- | --- | --- |
| overall | 60 | 0.744 [0.644, 0.839] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] |
| language/no | 30 | 0.744 [0.594, 0.872] | 0.833 [0.700, 0.933] | 0.833 [0.700, 0.933] | 0.833 [0.700, 0.933] | 0.833 [0.700, 0.933] |
| language/en | 30 | 0.744 [0.594, 0.872] | 0.833 [0.700, 0.933] | 0.833 [0.700, 0.933] | 0.833 [0.700, 0.933] | 0.833 [0.700, 0.933] |
| family/identifier | 10 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| family/entity | 10 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| family/alias | 10 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| family/predicate | 10 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| family/description | 10 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| family/multi_relevant | 10 | 0.467 [0.417, 0.500] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

Overall Recall@10 is **0.833 < 0.90**; MRR@10 is **0.833 >= 0.75**. Each language reaches the proposed 0.80/0.65 thresholds, but the overall target fails. These targets are pilot proposals, not approval criteria for an unattended product.

**All ten predicate formulations in each split miss** (Recall@50 and MRR@10 both zero). The intent judgments target directClaim predicate IRIs. The retained Wikidata capture stores bilingual labels on separate property entity IRIs; the baseline preserves those original IDs and does not copy labels across that relationship. This is a measured metadata/retrieval gap. It remains a zero-score family, rather than being reassigned to a labelled entity or removed. A revision should explicitly evaluate provenance-preserving predicate vocabulary mapping before claiming natural-language predicate quality.

Entity/identifier/alias relevance uses the retained public Wikidata development graph. The small, disclosed Apache-2.0 synthetic supplement supplies descriptions and label collisions missing from the retained captures. GeoNames/Schema.org contributes build/runtime coverage, not a separate relevance-quality claim.

| Behavior | Development | Evaluation |
| --- | ---: | ---: |
| Ambiguous cases | 10/10 | 10/10 |
| Ambiguous cases returning candidates | 10/10 | 10/10 |
| Ambiguous cases returning both relevant IDs at 50 | 10/10 | 10/10 |
| Exact collision flags on ambiguous cases | 2/10 | 0/10 |
| No-match cases returning candidates (false positives) | 0/10 | 0/10 |
| Query processing errors (all cases) | 0/80 | 0/80 |

Each behavior group has five cases per language; language counts, mean candidate counts and descriptive intervals are in the JSON. Prefixing the shared alias usually removes the exact-collision flag even though both candidates remain. General lexical/semantic ambiguity is not detected. No-match queries returning nothing do not prove that the concept is absent from the world.

## Pinned CPU measurements

Host: **Apple M1 Pro, 10 cores, 32GiB RAM**. Linux amd64 container under Docker Desktop emulation, affinity **CPU 0**, **one CPU quota**, 4GiB cgroup cap. The CLI reports **one process thread in every warm batch and all 120 cold runs**; worker environment variables are one. These are emulated-host measurements, not deployment-hardware validation.

Compiler: `rustc 1.99.1 (58cf8f9c3 2026-10-13), x86_64-unknown-linux-gnu`; release profile, locked dependencies. Binary SHA256: `09e7e05f8721883ecff432a0dc7f53b62f1721c22ab23198a16e513d6c77f732`. Exact platform, CPU exposure, code/toolchain/input hashes, affinity, sample definitions and RSS measurements are in [environment.json](run/environment.json).

| Corpus | Graph-qualified resources (unique IRIs) | Index bytes | Build ms | Cold p50 / p95 / p99 ms | Warm p50 / p95 / p99 ms |
| --- | ---: | ---: | ---: | --- | --- |
| wikidata | 40 (40) | 141,290 | 21.618 | 77.611 / 95.610 / 101.144 | 0.051 / 0.063 / 0.152 |
| cities | 430 (402) | 491,885 | 30.972 | 84.495 / 95.045 / 95.682 | 0.083 / 0.124 / 0.229 |
| descriptions | 9 (9) | 19,610 | 14.494 | 66.851 / 79.786 / 91.051 | 0.037 / 0.045 / 0.087 |
| scale | 10000 (10000) | 11,980,742 | 297.031 | 473.003 / 753.584 / 1030.657 | 15.121 / 20.833 / 41.574 |

Aggregate process RSS upper bound over the entire run: **256.2 MiB**, summing CLI high-water RSS (153.2 MiB) and controller high-water RSS (103.0 MiB). The sum conservatively bounds concurrent process RSS; it includes RDF ingestion, index construction, retained batch results and the Python controller, rather than just index storage.

There are 30 fresh-process cold samples and 200 in-process warm queries per corpus. Cold includes startup/import/build/query/JSON I/O, with OS page caches retained; warm includes result construction but excludes JSON serialization/I/O. The first warm query is retained. Build time excludes RDF import. Raw build times, nearest-rank percentile samples, text coverage/truncation statistics and index manifests are retained. With 30 cold samples, p99 is the sample maximum.

**Observed lightweight load budgets pass:** 10,000-resource warm p95 is below 500ms and aggregate RSS below 4GiB. **Real-domain scale acceptance is not established.** The byte-frozen synthetic corpus has 9,998 subjects plus two predicate resources and 19,996 quads; its short text is deliberately modest. The retained real corpora have only 40 and 430 graph-qualified resources, so their timings cannot establish 10,000-resource scale.

The initial verbose 10,000-resource recipe hit the pre-existing conservative 64MiB discovery allocation budget before ranking. The [failure and source/configuration](initial-scale-failure.json) and [original RDF archive](initial-scale.nq.gz) are retained. The shorter text/IRI recipe was frozen before the first ranking run without changing the resource count or any relevance formulations. No index-limit increase hides this failure. Larger descriptions/IRIs or different corpora can still exceed that limit; the passing lightweight run does not supersede it.

## Reproduce and inspect

Build with the repository-pinned toolchain, then run from the repository root on Linux (choose an allowed CPU). This reproduction records a fresh machine-specific result; timings and binary hashes need not match an emulated build.

```sh
cargo build --release --locked --offline -p verity_cli
python3 tools/retrieval.py verify
python3 tools/retrieval.py run --binary target/release/verity \
  --out artifacts/retrieval-new --cpu 0 --cold 30 --warm 200 \
  --compiler "$(rustc -Vv)" --cpu-description "record measured CPU and virtualization"
python3 tools/retrieval.py verify-report --out artifacts/retrieval-new
python3 tools/retrieval.py verify-report --out reports/issue-37-bm25/run
```

For the retained run, the source was mounted read-only at `/source` and the workspace artifact directory at `/build`, in image `sha256:8d0446c21ab3273b55c045a39c49120e9d7cde8e970954c3f81e7bee194fad95`, using `docker run --rm --network none --cpuset-cpus 0 --cpus 1 --memory 4g`. The binary was built there with `cargo +1.99.1 build --release --locked -p verity_cli` before measuring. The runner used `--binary /build/target/release/verity --out /build/final-run --cpu 0 --cold 30 --warm 200`. The image is a local build environment, not a required runtime dependency. The standard Linux command above reproduces the protocol without that image.

The [artifact inventory](run/artifacts.json) hashes compressed raw ranks, requests, failure log, environment, generated corpus archive and manifests. Raw ranks are in [ranks.jsonl.gz](run/ranks.jsonl.gz); the final [failure log](run/failures.json) is empty. Index revisions bind the catalog/discovery source and lockfile; ranking revisions and environment hashes identify the ranking/CLI/runner code. The [generated corpus archive](run/scale.nq.gz) and frozen recipe preserve exact input bytes. Decompress to a fresh path if replaying individual batch commands; archived request paths refer to the original container.

Validation covers hand-calculated BM25, stable ties, query token deduplication, exact/ambiguous aliases and identifiers, graph-local roles and statistics, private text/ID/source canaries, immutable snapshot/literal/source provenance, untrusted SERVICE/HTML text, input bounds, CLI error output, frozen inputs and report tampering/denominator regressions. No model, sealed holdout, semantic embeddings, production server or general ambiguity detector was evaluated.
