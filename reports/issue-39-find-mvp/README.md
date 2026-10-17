# Issue #39: scoped Find and graph-evidence CLI MVP

**Engineering MVP with revised pilot scope; no stakeholder quality or production
readiness claim.** Ship local entity/identifier/alias/description exploration of
the retained snapshots with explicit human selection, directed one-hop pages and
original graph evidence. Natural-language predicate discovery remains experimental.
No original target, frozen formulation, family or denominator is changed.

The [usage contract and offline walkthrough](../../docs/find-mvp.md) describe the
implemented surface. #36 supplies the graph-qualified discovery index; #37 supplies
BM25. The [#38 result](../issue-38-embeddinggemma/README.md) rejects embeddings alone
and defers fusion pending relevance review and ambiguity/no-match product policy.
BM25 remains the shipping implementation. No model inference or sealed Ask data
was used in this release.

## Frozen retrieval evaluation

The [fresh run](run/summary.json) uses the unchanged
[retrieval freeze](../../benchmarks/retrieval/manifest.json): 80 development and
80 public evaluation formulations, 40 Norwegian/40 English each. Each split has
60 scored relevant queries (30/language), ten ambiguous and ten no-match cases.
All 160 graph-qualified rankings, scores, exact flags, statuses and relevance
metrics exactly match #37; the reporting regression checks that equality.

Both splits retain these results (mean [descriptive 95% interval]):

| Group per split | n | Recall@1 | Recall@5 / @10 / @50 | MRR@10 |
| --- | ---: | --- | --- | --- |
| Overall | 60 | .744 [.644, .839] | .833 [.733, .917] | .833 [.733, .917] |
| Norwegian | 30 | .744 [.594, .872] | .833 [.700, .933] | .833 [.700, .933] |
| English | 30 | .744 [.594, .872] | .833 [.700, .933] | .833 [.700, .933] |
| Identifier/entity/alias/description, each | 10 | 1.000 [1, 1] | 1.000 [1, 1] | 1.000 [1, 1] |
| Predicate | 10 | .000 [0, 0] | .000 [0, 0] | .000 [0, 0] |
| Multiple relevant IDs | 10 | .467 [.417, .500] | 1.000 [1, 1] | 1.000 [1, 1] |

Overall Recall@10 **.833 < .90 fails**; MRR@10 **.833 >= .75 passes**.
Both languages reach the proposed .80/.65 thresholds. The predicate family
continues to miss because the original directClaim IRIs lack the observed labels
stored on separate property entities. The MVP does not silently copy labels or
replace the judgment IDs. Navigation instead shows original predicate IRIs in
their actual source triples. The explicit scope revision avoids presenting general
natural-language predicate discovery as ready.

All ten ambiguous cases per split return both judged IDs at 50; exact-collision
flags occur on 2/10 development and 0/10 evaluation cases. All ten no-match cases
per split return no candidates. There are **zero query/timing failures**. Unknown
concepts and non-exact ambiguity still require human interpretation. The full JSON
retains language/family cross-tabs, behavior denominators and bootstrap intervals
(2,000 query-level resamples, seed 37). Judgments are AI-authored and human-review
pending; the formulations share target intents and are correlated. Perfect small
families and degenerate intervals do not establish generalization or truth.

## Fresh native measurements

Apple M1 Pro, 10 cores, 32 GiB RAM; native macOS 26.6.2 arm64; Python 3.12.14;
Rust 1.99.1 (`58cf8f9c3`), release build, locked dependencies. Worker environment
budget one; host scheduler with **no CPU affinity/quota**. This run is a native
local observation, not fresh pinned-CPU acceptance or a deployment-hardware test.
The [prior pinned Linux/emulation run](../issue-37-bm25/README.md#pinned-cpu-measurements)
remains historical evidence with its own binary and limitations.

| Corpus | Graph-qualified resources | Index bytes | Build ms | Cold p50 / p95 / p99 ms | Warm p50 / p95 / p99 ms |
| --- | ---: | ---: | ---: | --- | --- |
| Wikidata | 40 | 141,290 | 2.094 | 8.913 / 10.164 / 10.628 | .041 / .051 / .060 |
| GeoNames cities | 430 | 491,885 | 7.301 | 16.907 / 18.054 / 18.685 | .057 / .062 / .080 |
| Descriptions | 9 | 19,610 | .474 | 5.970 / 7.266 / 8.995 | .032 / .038 / .061 |
| Synthetic scale | 10,000 | 11,980,742 | 173.828 | 247.845 / 301.844 / 510.565 | 7.503 / 7.893 / 8.191 |

There are 30 fresh-process cold and 200 resident warm samples per corpus. Cold
includes import/build/query/JSON I/O with OS caches retained; p99 is the sample
maximum. Warm includes ranking and the new explanation/result construction, but
excludes JSON serialization/I/O. Index build excludes RDF import. Aggregate RSS
upper bound is **349,028,352 bytes (332.86 MiB)**, summing CLI/controller process
high-water marks, including RDF import, index construction and retained results.
Observed synthetic warm p95 is below 500ms and memory below 4GiB. The lightweight
byte-frozen 19,996-quad corpus does not validate real-domain 10,000-resource scale,
long descriptions or navigation latency at scale. The earlier verbose allocation
failure is retained in #37 and has not been hidden by increasing index limits.

The [four-process smoke transcript](smoke.json) demonstrates fresh offline
Norwegian `Norge` and English `Norway` → Q20 → outgoing P36 → Q585 → incoming
source triple. Observed end-to-end times were 17.189 / 8.588 / 10.711 / 8.634ms,
including import, index build and JSON. These four small-snapshot samples establish
the walkthrough, not latency percentiles. Assertions check the exact edge,
graph/license and matching immutable snapshot IDs.

## Validation and reproduction

```sh
cargo build --release --locked --offline -p verity_cli
python3 tools/retrieval.py verify
python3 tools/retrieval.py run --binary target/release/verity \
  --out artifacts/find-release-new --cold 30 --warm 200 \
  --compiler 'record rustc -Vv' --cpu-description 'record actual hardware and scheduler'
python3 tools/retrieval.py verify-report --out artifacts/find-release-new
python3 tools/retrieval.py verify-report --out reports/issue-39-find-mvp/run
python3 -m unittest discover -s tools -p test_retrieval.py -v
cargo test --locked --offline -p verity_cli --test navigation
.venv/bin/python tools/verify_pre_llm.py
```

On Linux add `--cpu` with an allowed CPU for affinity-pinned repetition; macOS
has no such affinity option. Use the repository-pinned Rust toolchain and Python
dependencies. The final command requires a clean committed tree and runs the full
repository pipeline, including source rebuilds, frozen evidence/report regressions,
formatting, Clippy, Rust tests, schema parity, independent reference queries,
oracle/manual/fixture evidence and historical negative-result checks.

New tests cover directed incoming/outgoing pages, no gaps or duplicate edges across
pages, linked unlabeled entities, empty/unknown states, graph-local labels, original
language/datatype/blank-node witnesses, explicit output/row/evidence/offset limits,
policy/index/snapshot mismatches, invalid IRIs, raw-query fields, private ID/text/
source/count canaries in results and stderr, and no partial stdout on errors.
Malformed RDF errors are generic because parser diagnostics can quote inaccessible
graph data. No UI was added, so browser keyboard/accessibility checks do not apply.

[`release.json`](release.json) hashes all Rust implementation files, the lockfile,
toolchain, measured binary and smoke transcript. [`run/environment.json`](run/environment.json)
records the runner/ranking/CLI hashes, exact compiler/environment and RSS values;
[`run/artifacts.json`](run/artifacts.json) hashes raw ranks, requests, failures,
timings and the frozen synthetic corpus archive. Neither models, production
services, general ambiguity detection, human relevance quality nor real-world
truth were evaluated. Embeddings/fusion were not rerun; their pinned adopt/defer
decision and evidence remain in #38.
