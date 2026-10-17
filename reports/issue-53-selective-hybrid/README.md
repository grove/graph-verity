# Issue #53: keep BM25; defer selective hybrid promotion

**Recommendation: keep BM25 as the shipping Find backend.** The versioned
selective strategy is available only as an explicit local experiment. It fixes
exact-match rank-one regressions and removes the redundant concurrently resident
model, but the primary historical-text comparison fails no-match nonregression
and loses an exposed Norwegian paraphrase. The separate definition ablation
passes the numerical continuation screen; inadequate independent relevance review
still requires deferral. These are **AI-reference exploratory** results. No
production/default hybrid rollout, plan filling or Ask execution is added.

The [preregistered policy](../../benchmarks/selective-hybrid/README.md) documents
trusted exactness, lexical budgets, threshold calibration, ambiguity, abstention,
measurement definitions and the unchanged numerical screen. The [protocol](../../benchmarks/selective-hybrid/protocol.json)
was committed at `09f1d41` before new scored inference; the same-protocol repeat
was frozen at `e421bc4` after a truncation-flag correction. The entire first attempt
is retained in [first-run.tar.gz](first-run.tar.gz). Neither thresholds, judgments,
model assets, corpus nor numerical screening criteria changed after scoring.
The exact code and baseline sources are retained in [frozen-code.tar.gz](frozen-code.tar.gz).

## Inputs, source boundaries and policy

Reuse #50's unchanged licensed 2,215 graph-qualified GEMET/SKOS resources, original
IRIs, importer-assigned named graph, immutable snapshot, authorized scope/policy,
source witnesses, language/datatype metadata and truncation flags. Exact original
authorized document exports are byte-identical to #50 for each representation.
The EEA CC BY 4.0 and W3C licenses, source provenance, graph hash, policy/config/
index identities remain bound by the [freeze](freeze/freeze.json). RDF descriptions
are untrusted data; no inferred aliases, labels, answer rows or graph authority
are introduced. The [native canary](scope-canary.json) verifies private IDs,
labels, text, counts and source metadata cannot change authorized exports, and
unauthorized scopes fail before index output. Unit checks cover role/snapshot
escape, model-supplied exact flags, injected instructions, graph-qualified exact
ambiguity, source literal metadata and clipping beyond 50 exact matches.

All 122 #50 queries are now exposed regressions (102 relevant, six ambiguous,
fourteen no-match), including its original evaluation. The 50 new preregistered
queries contain **36 relevant, two ambiguous, twelve no-match**. New judged
resource lineages do not overlap #50 targets. Norwegian and English paraphrases
use different concepts; some evaluation targets repeat within evaluation. Exact
ID language is stratum metadata. Existing alias targets were already exposed,
so alias protection is tested in regressions rather than called new independent
evidence. Some new predicate/class targets had appeared in old dense candidate
lists; their target judgments are new, not an unseen ontology. Public source-
audited AI judgments are not exhaustive human relevance pools; intervals are
query-level descriptions, not independent-population guarantees. No external
human reviewer was available. No private/sealed Ask holdout was opened.

The opt-in strategy takes all trusted exact matches first, then three nonexact
lexical candidates, dense candidates scoring >=0.73, and remaining lexical
candidates; deduplicate `(graph, IRI)`, preserve original ordering and use one total
top50 role-scoped budget. The cutoff is the smallest hundredth above the exposed
negative maximum 0.7293137907981873, selected before new evaluation. Dense candidates
can enter with no BM25 hit. Unique exact remains `ranked`; several exact matches
are `ambiguous_exact`; other accepted candidates are `low_confidence` or
`ambiguous_candidates`; zero accepted candidates gives `no_match`. Every state requires user selection.
No-match describes this authorized retrieval policy, never absence of RDF facts.

## Quality and paired uncertainty

New evaluation only; each positive denominator is 36. Ambiguous and no-match
queries are excluded from these relevance averages. Brackets are descriptive
95% query-bootstrap intervals (2,000 resamples, seed37), limited by correlated
lineages, incomplete AI references and small language/role/family strata.

| Text / method | Recall@1 | Recall@5 | Recall@10 | Recall@50 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| bm25-46 / bm25 | 0.278 [0.139, 0.444] | 0.292 [0.153, 0.444] | 0.319 [0.181, 0.472] | 0.319 [0.181, 0.472] | 0.289 [0.147, 0.444] |
| bm25-46 / embedding | 0.472 [0.306, 0.625] | 0.694 [0.528, 0.833] | 0.819 [0.681, 0.931] | 0.875 [0.764, 0.972] | 0.580 [0.434, 0.718] |
| bm25-46 / fusion | 0.292 [0.153, 0.444] | 0.472 [0.319, 0.625] | 0.722 [0.556, 0.861] | 0.903 [0.792, 0.986] | 0.402 [0.264, 0.544] |
| bm25-46 / selective | 0.278 [0.139, 0.444] | 0.528 [0.375, 0.681] | 0.750 [0.597, 0.875] | 0.806 [0.667, 0.917] | 0.383 [0.256, 0.514] |
| skos-definitions-v1 / bm25 | 0.542 [0.389, 0.694] | 0.583 [0.417, 0.722] | 0.611 [0.444, 0.750] | 0.639 [0.472, 0.778] | 0.573 [0.417, 0.722] |
| skos-definitions-v1 / embedding | 0.694 [0.542, 0.833] | 0.861 [0.750, 0.972] | 0.917 [0.806, 1.000] | 0.931 [0.833, 1.000] | 0.774 [0.647, 0.888] |
| skos-definitions-v1 / fusion | 0.486 [0.319, 0.653] | 0.764 [0.625, 0.889] | 0.833 [0.694, 0.944] | 0.972 [0.917, 1.000] | 0.615 [0.479, 0.745] |
| skos-definitions-v1 / selective | 0.542 [0.389, 0.694] | 0.778 [0.639, 0.917] | 0.847 [0.722, 0.944] | 0.847 [0.722, 0.944] | 0.638 [0.499, 0.769] |

| Text / method / language | Recall@10 delta | MRR@10 delta |
|---|---:|---:|
| bm25-46 / bm25 / overall | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| bm25-46 / bm25 / language/en | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| bm25-46 / bm25 / language/no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| bm25-46 / embedding / overall | 0.500 [0.306, 0.681] | 0.291 [0.129, 0.454] |
| bm25-46 / embedding / language/en | 0.472 [0.167, 0.750] | 0.343 [0.091, 0.579] |
| bm25-46 / embedding / language/no | 0.528 [0.222, 0.778] | 0.240 [0.001, 0.466] |
| bm25-46 / fusion / overall | 0.403 [0.250, 0.556] | 0.114 [-0.002, 0.231] |
| bm25-46 / fusion / language/en | 0.417 [0.222, 0.667] | 0.114 [-0.058, 0.270] |
| bm25-46 / fusion / language/no | 0.389 [0.167, 0.611] | 0.113 [-0.069, 0.283] |
| bm25-46 / selective / overall | 0.431 [0.278, 0.583] | 0.094 [0.057, 0.134] |
| bm25-46 / selective / language/en | 0.472 [0.250, 0.722] | 0.096 [0.048, 0.146] |
| bm25-46 / selective / language/no | 0.389 [0.167, 0.611] | 0.092 [0.037, 0.157] |
| skos-definitions-v1 / bm25 / overall | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| skos-definitions-v1 / bm25 / language/en | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| skos-definitions-v1 / bm25 / language/no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| skos-definitions-v1 / embedding / overall | 0.306 [0.111, 0.500] | 0.201 [0.044, 0.359] |
| skos-definitions-v1 / embedding / language/en | 0.056 [-0.111, 0.222] | 0.133 [-0.083, 0.349] |
| skos-definitions-v1 / embedding / language/no | 0.556 [0.278, 0.833] | 0.270 [0.006, 0.522] |
| skos-definitions-v1 / fusion / overall | 0.222 [0.056, 0.389] | 0.042 [-0.075, 0.145] |
| skos-definitions-v1 / fusion / language/en | 0.056 [-0.111, 0.222] | 0.015 [-0.159, 0.162] |
| skos-definitions-v1 / fusion / language/no | 0.389 [0.111, 0.667] | 0.070 [-0.122, 0.220] |
| skos-definitions-v1 / selective / overall | 0.236 [0.111, 0.375] | 0.066 [0.030, 0.107] |
| skos-definitions-v1 / selective / language/en | 0.111 [0.000, 0.278] | 0.035 [0.000, 0.077] |
| skos-definitions-v1 / selective / language/no | 0.361 [0.167, 0.583] | 0.096 [0.037, 0.171] |

The complete [summary](run/summary.json) retains all Recall@1/5/10/50 and MRR@10
metrics and paired intervals by language, family, role, corpus and authorized
scope, including all exposed regressions. The raw `*-resident-ranks.jsonl.gz`
files retain complete query/judgment/lineage, original metadata, snapshot,
component scores, selected route and abstention/ambiguity state. `*-scores.jsonl.gz`
retain every authorized role-filtered similarity and native lexical response;
FP32 query/document vectors support model-free numerical replay.

## Exactness, false candidates and recall costs

Exact-first counts below include every case whose same-version BM25 has an
exact first hit, including ambiguous lookups; the first identity must be preserved.
No-match and ambiguity fractions use new evaluation only. Full ambiguity coverage
means all judged candidates appear at 50, distinct from merely returning something.
False confident retrieval counts no-match queries incorrectly marked `ranked`;
zero does not imply zero false candidates or calibrated confidence.

| Text / method | Exact first preserved (regression + new) | No-match returns | Ambiguous returns / full judged coverage@50 | False `ranked` negatives | New top10 wins over BM25 |
|---|---:|---:|---:|---:|---:|
| bm25-46 / bm25 | 61/61 | 8/12 | 2/2 / 2/2 | 0 | 0 |
| bm25-46 / embedding | 47/61 | 12/12 | 2/2 / 2/2 | 0 | 20 |
| bm25-46 / fusion | 49/61 | 12/12 | 2/2 / 2/2 | 0 | 14 |
| bm25-46 / selective | 61/61 | 9/12 | 2/2 / 2/2 | 0 | 16 |
| skos-definitions-v1 / bm25 | 61/61 | 8/12 | 2/2 / 2/2 | 0 | 0 |
| skos-definitions-v1 / embedding | 44/61 | 12/12 | 2/2 / 2/2 | 0 | 13 |
| skos-definitions-v1 / fusion | 47/61 | 12/12 | 2/2 / 2/2 | 0 | 10 |
| skos-definitions-v1 / selective | 61/61 | 8/12 | 2/2 / 2/2 | 0 | 9 |

The primary historical-text selective strategy returns 9/12 no-match probes
versus BM25's 8/12, **failing the frozen screen**. The definition variant returns
8/12, equal to its BM25. Dense and original RRF return all 12 in each version.
Do not hide that BM25 itself returns many unsupported candidates. No threshold
was adjusted to remove the additional false match.

Retained exposed failures and protection:

- `hybrid-041`, original groundwater IRI `.../concept/3780`, and `hybrid-064`,
  original `water pollution` (`.../concept/9202`), stay first under selective.
- `hybrid-115` (`marriedTo`) and `hybrid-117` (nonce) become `no_match` under the
  fixed selective cutoff, rather than dense/RRF's unrelated candidates.
- `hybrid-067`, Norwegian “å ta opp meir fisk enn bestanden klarer å erstatte”,
  loses #50's dense/RRF top10 overfishing win. The relevant original
  `.../concept/5960` falls below 0.73. This is a real paraphrase-recall cost of the
  conservative gate; lexical absence did not veto the dense candidates above it.
- New false semantic match: `selective-039`, nonce `ZVQUNMAPPEDOMEGA`, returns
  original `.../concept/15256` (ozone precursor) at 0.7328884 in the primary
  historical-text variant. BM25 returns no candidates. The state is
  `low_confidence`, but the candidate return still fails the declared screen.
- New paraphrase win: `selective-001`, “facility that turns seawater into drinking
  water”, recovers original `.../concept/2099` (desalination plant) in top10
  where BM25 misses it, in both text versions.
- Multiple-relevant and ambiguous results are retained and scored separately;
  similarity never selects a unique semantic interpretation.

[quality-cases.json](quality-cases.json) retains all negative-return examples,
new top10 win IDs and the five exposed regression traces with their full metadata.
Both representations are compared only against their own BM25; definition effects
must not be attributed solely to the selective algorithm. Small samples and
positive point estimates cannot establish retrieval safety or usability.

## Actual Mac CPU, memory and storage

Native Apple M1 Pro, 32 GiB, macOS arm64; four Torch intra-op / one inter-op
threads, CPU-only, host scheduler, no affinity/quota or cache eviction. Exact
`google/embeddinggemma-2` revision
`914f7f89142e33e77833254d9c9b90c3cef7303b`, original upstream weight/tokenizer
hashes, unchanged FP32 runtime, eager attention, 768 normalized dimensions,
256-token limit and document batch size eight. No quantization, new dependency
or model download is used. Fresh actual official Sentence Transformers token and
vector reference parity precedes resident document inference.

| Text / method | Resident p50 / p95 / p99 ms |
|---|---:|
| bm25-46 / bm25 | 0.82 / 5.05 / 5.31 |
| bm25-46 / embedding | 61.13 / 86.63 / 114.31 |
| bm25-46 / fusion | 62.06 / 87.54 / 115.69 |
| bm25-46 / selective | 64.35 / 89.62 / 120.42 |
| skos-definitions-v1 / bm25 | 1.23 / 5.35 / 5.62 |
| skos-definitions-v1 / embedding | 62.50 / 73.60 / 113.55 |
| skos-definitions-v1 / fusion | 63.91 / 77.05 / 115.45 |
| skos-definitions-v1 / selective | 66.35 / 79.36 / 119.79 |

| Text | Process-cold p50 / p95 / p99 ms | Dense build ms | Rust build ms / serialized index bytes |
|---|---:|---:|---:|
| bm25-46 | 7666.75 / 8398.33 / 8398.33 | 54628.6 | 84.99 / 2,497,151 |
| skos-definitions-v1 | 8181.84 / 8447.48 / 8447.48 | 104505.4 | 139.96 / 5,560,063 |

The corrected conservative process-tree RSS upper bound is
**3,019,948,032 bytes (2.813 GiB)**,
compared with #50's unchanged **4,744,151,040 bytes (4.418 GiB)** failure.
It still sums controller HWM (159,072,256) + largest
sequential direct child HWM (2,801,778,688) + largest nested
Rust HWM (59,097,088). This conservative sum of maxima
is not a simultaneous peak and can double-count shared pages. The separately
sampled full live process-tree peak is **2,663,514,112
bytes (2.481 GiB)** from 1,260
samples at nominal 200ms intervals, with no sampler errors. Samples can miss
short spikes; passing 4 GiB uses the conservative bound, never the sampled value.

A lightweight controller owns no model. Each sequential worker owns one model,
a bounded FP32 vector matrix and one persistent Rust/index helper. Resident and
cold workers never overlap. Cold includes fresh imports, asset/hash checks,
model/vector loads, Rust import/build, query, diagnostics and teardown; this is
process-cold with warm OS caches, not cold disk. Extra integrity/diagnostic work
is included in the new cold wall time. Resident timing includes actual
request/response IO, inference, ranking, validation, full provenance construction
and serialization. Five predeclared cold samples per text version make p95/p99
maxima rather than reliable tail estimates. No heavy builds/tests ran during
measurement. The saved `*-resident.json`, `*-cold-*.json`, [performance](run/performance.json)
and [memory](run/memory.json) retain all samples, worker/helper peaks and loads.

[storage-and-allocations.json](storage-and-allocations.json) records pinned model
asset and FP32 weight tensor bytes, native runtime disk allocation, raw/gzip
vectors, export size, serialized index sizes and source/token truncation counts.
The actual text-only CPU model has 1,084,010,496 parameter bytes and 3,172
buffer bytes in FP32; the pinned runtime occupies 1,164,124,160 allocated disk
bytes, excluding the shared base interpreter/system libraries. The original
BF16 upstream assets are unchanged; inference uses the originally pinned FP32
text runtime. Serialized index bytes are not exclusive heap measurements; process RSS includes
runtime/interpreter/allocator overhead and shared pages, without claiming an
exclusive per-allocator breakdown. Each representation uses 6,804,480 raw vector
bytes; no real corpus input exceeds 256 tokens. Original source descriptions
remain complete; 74 indexed definition descriptions are character-truncated.

The historical 5,588-resource rich-definition extraction still fails the 64 MiB
index allocation limit. No input/scope/output/allocation budget was raised, no
synthetic corpus padding was added, and no 10k-resource scale claim is made.
The [immutable #50 limits and instrumentation record](../issue-50-real-rdf-hybrid/README.md)
remain visible. Memory improvement comes from process lifetime/ownership;
quantization and a new serving architecture were unnecessary for this pilot.

## Retained attempts, replay and decision

The first full run and its exact frozen code are retained in `first-run.tar.gz`.
A boundary unit test found an incorrect `truncated=false` when more than 50
exact matches existed. The fix changes that result flag only; the real pilot has
no such case. A complete same-protocol repeat freezes the fix before inference;
[repeat-note.json](repeat-note.json) and [repeat-comparison.json](repeat-comparison.json)
record the reason and compare all hits, scores, routes, states and metrics.
Repeated runs are not additional independent relevance evidence, and the new
questions are now exposed for future work. The final run is used regardless of
which latency observations are more favorable.

The [decision](run/decision.json) applies the preregistered screen. The primary
historical-text variant fails no-match nonregression. The definition ablation
passes numerical criteria, but independent relevance/usability review remains
inadequate. **Keep BM25 and defer promotion.** A future local development trial
can use this experimental tool explicitly; any product/default adoption needs a
separate owner release decision. There is no model connected to shipping Find
or Confirmed Ask, no generated SPARQL/SERVICE/write endpoint and no automatic
question interpretation or execution.

Ordinary CI checks source/license/hash rebuilding, frozen input and artifact
inventories, source witnesses, role/scope/snapshot and exactness boundaries,
private canaries, injection/metadata preservation, the >50 exact-candidate edge,
saved tokenizer/vector parity, every saved dense score, all ranks/routes/states,
metrics/intervals/decisions and current native BM25 replay. It downloads no weights
and performs no inference. The original #37–#50 reports remain unchanged.
Validation commands and results are retained in `validation.json` and `logs/`.

## Reproduce

Model-free verification (ordinary pinned dependencies):

```sh
PATH=/path/to/pinned/rust-toolchain/bin:$PATH
cargo build --locked --offline -p verity_cli --example retrieval_session
.venv/bin/python tools/selective_hybrid.py verify
.venv/bin/python tools/selective_hybrid.py verify-report \
  --freeze reports/issue-53-selective-hybrid/freeze \
  --out reports/issue-53-selective-hybrid/run \
  --binary target/debug/examples/retrieval_session
.venv/bin/python tools/verify_pre_llm.py
```

The complete pipeline requires a clean committed tree. It includes the usual
Rust/Python tests, formatting, Clippy, historical controls and source rebuilds.
For fresh local inference, first rebuild #50's isolated historical baseline
session from the retained `baseline/` sources (or follow #50's reproduction
commands). Keep its target directory separate. Reuse the exact pinned assets
and runtime described in [the model setup](../../docs/embedding-experiment.md).
The report's frozen binaries are platform-specific; fresh preparations bind the
actual rebuilt binaries and software, not an expected executable checksum.

```sh
/path/to/pinned/runtime/bin/python tools/selective_hybrid.py prepare \
  --model-dir /path/to/pinned/embeddinggemma-2/assets \
  --baseline-session /path/to/bm25-46/retrieval_session \
  --session target/release/examples/retrieval_session \
  --out artifacts/selective-repeat/freeze \
  --cpu-description 'record actual hardware, scheduler and cache conditions'
/path/to/pinned/runtime/bin/python tools/selective_hybrid.py run --allow-inference \
  --freeze artifacts/selective-repeat/freeze --out artifacts/selective-repeat/run
.venv/bin/python tools/selective_hybrid.py verify-report \
  --freeze artifacts/selective-repeat/freeze --out artifacts/selective-repeat/run \
  --baseline-session /path/to/bm25-46/retrieval_session \
  --binary target/release/examples/retrieval_session
```

`--baseline-session` adds fresh historical-text lexical replay for all 172 queries;
`--binary` adds current definition-version native lexical replay. Saved dense
scores and selective/RRF output replay on any supported CI host without inference.
All retained evidence is covered by `checksums.json`; each freeze/run has its own
complete inventory. The frozen source archive makes the exact measured version
and baseline independently inspectable and rebuildable.
