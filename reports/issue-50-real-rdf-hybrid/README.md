# Issue #50: keep BM25; defer hybrid

**Recommendation: keep BM25 as the shipping Find backend and defer a hybrid
product trial.** The pinned EmbeddingGemma 2 + fixed RRF experiment finds real
paraphrase/cross-language recall gains, but fails the preregistered exact-match,
no-match, language-nonregression and aggregate-memory screening criteria. No
hybrid backend is enabled. This is retrieval-only AI-reference evidence, not
human-reviewed search quality, question interpretation, verified facts or a
production approval. Future adoption requires a separate owner/release decision.

## Frozen inputs and scope

The new [protocol](../../benchmarks/hybrid/README.md) and
[machine-readable preregistration](../../benchmarks/hybrid/protocol.json) contain
**122 public retrieval queries: 40 development / 82 evaluation**, with 62
Norwegian / 60 English stratum labels. The relevance denominators are **32 / 70**;
2 / 4 ambiguous cases and 6 / 8 no-match cases are reported separately. Four
no-match cases are realistic hard negatives. Exact-identifier strings have no
intrinsic language. Norwegian includes Bokmål/Nynorsk authoring, without
independent linguistic review. The five resource lineages shared across splits
are listed explicitly; these correlated cases are never called unseen tests.
No parameters, queries or judgments were tuned on either split.

The [source pilot](../../data/gemet/README.md) is **2,200 real GEMET 4.2.3 concepts,
2,215 graph-qualified resources, 10,839 quads**, including original W3C SKOS
predicate/class witnesses. EEA publishes GEMET under CC BY 4.0; original W3C
schema statements have their retained W3C license and attribution. Source URLs,
release identities, raw/canonical hashes, importer, language/datatype witnesses,
policy and discovery scope are pinned. The source files are un-named RDF;
assignment to one explicit importer release graph is documented, not represented
as an original publisher named-graph claim. No source facts or labels are invented.

Both variants use the same original IRIs, roles, scope and snapshot. Within each
variant, all three methods use the exact same authorized document text:

- **bm25-46:** unchanged #46 revised BM25 and its label/alias/comment/IRI
  representation; original GEMET SKOS definitions remain visible in source but
  are not indexed by the historical implementation.
- **skos-definitions-v1:** add original `skos:definition` literals to the existing
  bounded description field, retaining predicate, language, datatype and
  truncation witnesses. This is an explicit text-representation ablation for
  all three methods; it is never attributed to fusion alone. Shipping BM25 now
  recognizes that field. The rules identity changes, requiring persisted indexes
  to be rebuilt. No allocation/import limit is relaxed.

Model: exact official **`google/embeddinggemma-2`**, revision
`914f7f89142e33e77833254d9c9b90c3cef7303b`, original #38 pinned text-only CPU FP32
runtime, four intra-op / one inter-op threads, unquantized, eager attention,
768 normalized dimensions, official prefixes/mean pooling, 256-token cap and
batch size eight for documents. Fresh official Sentence Transformers reference
parity precedes document inference. The [freeze](freeze/freeze.json) binds
model assets, runtime packages/build, compiler, binaries, authorized exports,
code, protocol and original #38 legal-document hashes. Weights remain outside Git.

Fixed equal-weight top50/top50 RRF uses constant 60 and IRI/graph tie-breaking.
There is **no exact-ID override, lexical veto or similarity cutoff**. Dense/fusion
state reflects the role-filtered pool before clipping: zero -> `no_match`, one ->
`low_confidence`, several -> `ambiguous_candidates`. BM25 keeps #46's conservative
exact/ambiguous/no-match states. Vector scores are not interpretation confidence.
Every query retains top50 hits, all dense similarities, source-qualified catalog,
query/document vectors, snapshot, judgments, lineage and errors.

## Measured quality

| Variant / split / method | n | Recall@1 | Recall@5 | Recall@10 | Recall@50 | MRR@10 |
|---|---:|---|---|---|---|---|
| bm25-46 / development / bm25 | 32 | 0.531 [0.359, 0.688] | 0.562 [0.375, 0.719] | 0.594 [0.438, 0.750] | 0.594 [0.438, 0.750] | 0.568 [0.385, 0.724] |
| bm25-46 / development / embedding | 32 | 0.531 [0.359, 0.703] | 0.594 [0.406, 0.750] | 0.594 [0.406, 0.750] | 0.812 [0.656, 0.938] | 0.573 [0.406, 0.740] |
| bm25-46 / development / fusion | 32 | 0.500 [0.328, 0.656] | 0.594 [0.438, 0.750] | 0.656 [0.500, 0.812] | 0.875 [0.750, 0.969] | 0.563 [0.399, 0.723] |
| bm25-46 / evaluation / bm25 | 70 | 0.486 [0.364, 0.607] | 0.557 [0.443, 0.686] | 0.571 [0.457, 0.686] | 0.571 [0.457, 0.686] | 0.530 [0.415, 0.653] |
| bm25-46 / evaluation / embedding | 70 | 0.550 [0.429, 0.664] | 0.729 [0.614, 0.829] | 0.843 [0.757, 0.929] | 0.871 [0.786, 0.943] | 0.654 [0.550, 0.749] |
| bm25-46 / evaluation / fusion | 70 | 0.457 [0.343, 0.571] | 0.629 [0.514, 0.743] | 0.800 [0.700, 0.886] | 0.957 [0.900, 1.000] | 0.556 [0.452, 0.666] |
| skos-definitions-v1 / development / bm25 | 32 | 0.516 [0.344, 0.672] | 0.562 [0.375, 0.719] | 0.562 [0.375, 0.719] | 0.656 [0.500, 0.812] | 0.547 [0.375, 0.719] |
| skos-definitions-v1 / development / embedding | 32 | 0.531 [0.359, 0.703] | 0.656 [0.500, 0.812] | 0.656 [0.500, 0.812] | 0.781 [0.625, 0.906] | 0.604 [0.438, 0.760] |
| skos-definitions-v1 / development / fusion | 32 | 0.438 [0.266, 0.594] | 0.562 [0.406, 0.719] | 0.594 [0.406, 0.750] | 0.906 [0.781, 1.000] | 0.514 [0.349, 0.667] |
| skos-definitions-v1 / evaluation / bm25 | 70 | 0.493 [0.371, 0.614] | 0.586 [0.471, 0.700] | 0.629 [0.514, 0.743] | 0.686 [0.571, 0.800] | 0.534 [0.419, 0.651] |
| skos-definitions-v1 / evaluation / embedding | 70 | 0.536 [0.429, 0.650] | 0.750 [0.643, 0.850] | 0.793 [0.693, 0.886] | 0.871 [0.786, 0.943] | 0.637 [0.538, 0.738] |
| skos-definitions-v1 / evaluation / fusion | 70 | 0.514 [0.400, 0.636] | 0.707 [0.600, 0.814] | 0.771 [0.671, 0.871] | 0.957 [0.900, 1.000] | 0.601 [0.497, 0.709] |

Evaluation paired deltas against each variant’s BM25:

| Variant / method | Recall@10 delta | MRR@10 delta |
|---|---|---|
| bm25-46 / embedding | 0.271 [0.129, 0.414] | 0.123 [-0.000, 0.242] |
| bm25-46 / fusion | 0.229 [0.129, 0.343] | 0.025 [-0.060, 0.108] |
| skos-definitions-v1 / embedding | 0.164 [0.021, 0.307] | 0.103 [-0.031, 0.228] |
| skos-definitions-v1 / fusion | 0.143 [0.014, 0.271] | 0.068 [-0.040, 0.174] |

Fusion gains recall in both representations, but the historical-text variant’s English MRR delta is **−0.054**, beyond the allowed −0.02. The definition variant’s English Recall@10 / MRR deltas are **−0.059 / −0.023**. All six exact-identifier evaluation queries lose first-rank behavior under fusion in both variants; the definition variant also regresses the exact `water pollution` label. Evaluation no-match returns increase from **4/8 to 8/8**; this is retrieval-candidate behavior, not a claim that BM25 correctly handles every unsupported query.

| Variant / evaluation method | New wins with BM25 Recall@10=0 | Exact-first rank regressions | No-match returns |
|---|---:|---:|---:|
| bm25-46 / embedding | 25 | 6 | 8/8 |
| bm25-46 / fusion | 17 | 6 | 8/8 |
| skos-definitions-v1 / embedding | 19 | 9 | 8/8 |
| skos-definitions-v1 / fusion | 16 | 7 | 8/8 |

Query-level descriptive intervals use 2,000 paired bootstrap resamples, seed 37.
Public AI references, incomplete expert relevance pooling, correlated source
concepts, small role/family samples and shared lineages limit interpretation.
Neither degenerate intervals nor repeated runs establish independent evidence.
The complete [summary](run/summary.json) retains Recall@1/5/10/50, MRR@10,
per-language/family/role/corpus/authorized-scope groups, paired deltas, errors,
zero-hit/ambiguous/hard-negative candidate-return rates, exact regressions and
new wins/failures. The raw [ranked lists](run/ranks.jsonl.gz) remain inspectable.
Ambiguous and no-match probes never enter relevance accuracy denominators.

Examples are candidate rankings in the named pilot graph, not verified answers:

- **New recall win:** `hybrid-067`, “å ta opp meir fisk enn bestanden klarer å erstatte”, has no historical-text BM25 hits. Dense/fusion recover original `http://www.eionet.europa.eu/gemet/concept/5960` (overfishing) at rank 9. The definition variant loses this top10 win; richer source text is not universally beneficial.
- **Exact-ID harm:** `hybrid-041` asks for original `.../concept/3780` (groundwater). BM25 ranks it first; historical-text fusion moves it to rank 6. The definition fusion moves it outside top10. Dense alone misses it in top50 in both representations.
- **False candidate:** `hybrid-115`, predicate `marriedTo`, has no judged retrievable relation in scope. BM25 returns `no_match`; dense/fusion rank original `http://www.w3.org/2000/01/rdf-schema#comment` first. They report `ambiguous_candidates`, not a supported interpretation. The nonce `hybrid-117` likewise receives attractive numerical similarities despite having no relevant resource.
- **Exact-label harm:** for `hybrid-064`, “water pollution”, definition BM25 preserves exact original `.../concept/9202` first. Definition fusion puts `.../concept/5959` (overfertilisation) first and the exact target third. Candidate similarity cannot replace identifier/alias usability requirements.


## Native CPU, storage and limits

Apple M1 Pro, 32 GiB, native macOS arm64, pinned Rust 1.99.1 and original #38
Python/Torch/runtime packages. Host scheduler; no CPU affinity/quota, Metal or
GPU layers. OS caches are retained. Heavy verification/builds were kept outside
the measured inference run; ordinary host activity is not isolated.

| Variant | BM25 resident p50/p95/p99 ms | Dense resident p50/p95/p99 ms | Fusion resident p50/p95/p99 ms | Process-cold fusion p50/p95/p99 ms |
|---|---|---|---|---|
| bm25-46 | 1.07 / 5.59 / 5.97 | 67.67 / 93.99 / 152.23 | 68.99 / 95.12 / 153.90 | 7676.29 / 9501.32 / 9501.32 |
| skos-definitions-v1 | 1.47 / 5.93 / 6.25 | 64.17 / 83.10 / 121.45 | 65.91 / 85.71 / 124.28 | 7555.89 / 9186.93 / 9186.93 |

| Variant | Rust import + build ms | Compact lexical index bytes | Dense build seconds (excludes serialization) | Vector bytes / gzip disk bytes | Input chars p50/p95/p99 |
|---|---:|---:|---:|---|---|
| bm25-46 | 92.33 | 2,497,151 | 76.769 | 6,804,480 / 6,332,269 | 97 / 120 / 133 |
| skos-definitions-v1 | 153.72 | 5,560,063 | 120.505 | 6,804,480 / 6,331,609 | 227 / 545 / 617 |

The corrected process-tree RSS upper bound is **4,744,151,040 bytes (4.418 GiB)**, exceeding the provisional 4GiB budget. Resident fusion p95 passes the 1s budget in both variants. Model assets total **1,525,808,822 bytes**; direct model construction is **1.639s**, excluding imports. Cold per-sample model loads are recorded separately. Each representation adds **6,804,480 raw FP32 vector bytes** (plus its frozen text/metadata export and shared model/runtime). Zero real corpus inputs exceed the 256-token cap; the 8 actual reference-parity probes separately exercise truncation. Worst parity absolute error is **5.96e-08**. Original definitions remain complete in source; the discovery export records 74 character-truncated descriptions.

Warm samples cover every frozen query once, including the first and long
requests. BM25 uses a persistent, separately built Rust example with bounded
NDJSON framing and request/response serialization. Dense includes tokenization,
inference, role filtering, similarity search and JSON serialization. Fusion
adds actual resident lexical request/response and fusion/output serialization.
This is a local experiment transport, not HTTP/product serving. Cold observations
include fresh Python imports, model/vector loading, Rust RDF import/index build,
one query and process teardown. Only five preregistered cold samples per variant
were taken; their p95/p99 are maxima, not reliable tail estimates or cold-disk claims.
All sample timings and model loads are retained in [performance.json](run/performance.json). The source has **2,053 definition literals**, character p50/p95/p99 **138/444/815**, maximum **1351**. The installed embedding runtime occupies **1.084 GiB** of native allocated disk blocks, separately from model assets; this excludes the shared base interpreter/system libraries. [storage-and-descriptions.json](storage-and-descriptions.json) retains those observations and definitions.

The corrected RSS upper bound sums controller, largest sequential direct child,
and largest nested Rust child high-water marks. The resident parent remains
loaded during cold-child measurements; this is an experiment-process-tree cost,
not minimal single-model deployment memory. It is a conservative sum of maxima,
not a sampled simultaneous peak or an imposed memory cap. See
[memory.json](run/memory.json) and each cold sample's worker/helper high-water marks.
The [decision](run/decision.json) applies the unchanged numerical screening rule.

The full **5,573-concept** extraction reaches **5,588** graph-qualified resources
but the definition representation is rejected by the existing 64MiB allocation
budget, with empty stdout. The historical representation builds that full
source; that does not establish rich-description feasibility. Requesting 10,000
concepts is rejected because GEMET has only 5,573. [limits.json](limits.json),
the [failed full snapshot](full-source-attempt.nq.gz), original input manifests
and source hashes preserve both attempts. No synthetic padding or limit increase
is presented as real-scale evidence. A 10,000-resource follow-up must resolve
allocation cost or separately authorized bounded indexes and add source-pinned,
licensed distinct subjects under a new protocol.

## Retained attempts and verification

The initial transport preflight caught a stale baseline example binary from a
shared Cargo target directory. It reported definition rules inconsistent with
the legacy CLI export. The corrected baseline was built in an isolated target,
and preparation now checks session/export manifests before freezing; inference
checks them again. [preflight-1.tar.gz](preflight-1.tar.gz) preserves that attempt.
The unscored `water pollution` transport smoke occurred after query/protocol
creation and before the full binary/model/export freeze; only ready/status/
snapshot metadata were inspected. Its raw output is retained in `logs/`.
The preflight record's no-ranking flag refers to scored benchmark/inference
runs, not to that unscored transport check. No scored benchmark preceded the
correction, and no judgment or parameter changed.

The first complete quality run passed model-free vector/rank replay. Its RSS
instrumentation omitted the nested Rust helper of cold Python workers, so its
parent/direct-child sum is **not** a full process-tree bound. The entire first
freeze/run is retained in [run-1.tar.gz](run-1.tar.gz), with the exact measured
code in [frozen-code-v1.tar.gz](frozen-code-v1.tar.gz) and an explicit
[instrumentation note](run-1-instrumentation-note.json). The corrected repeat
adds nested RSS accounting and per-row durable rank logging. **The protocol,
model, assets, queries, judgments, candidate universe, text variants, fusion and
adoption thresholds are unchanged.** Both attempts remain inspectable; results
are not selected by favorable latency. The canonical corrected repeat is in
`freeze/` and `run/`, with exact code in `frozen-code.tar.gz`.

Both complete runs have **identical hits, scores, case metrics and complete summaries** across all 732 rank lists; see [repeat-comparison.json](repeat-comparison.json). Fresh native BM25 control replays produce **320 unchanged historical rank lists** (160 queries × two representations), bound by [historical-controls.json](historical-controls.json). The first and corrected attempts are repetitions of the same references, not additional independent queries. Full verification results are recorded below after the clean-tree pipeline completes.

Ordinary CI verifies source licenses/hashes and byte rebuilding, original source
witnesses and split lineages, private ID/text/count/source canaries, role/scope
integrity, bounded frames/vectors, actual saved parity traces, every saved dense
similarity from FP32 vectors, reconstructed dense/RRF ranks, native lexical
replay, all metrics/intervals/decisions and report inventories. It invokes no
embedding runtime, source refresh, model download, Ask holdout or heavy inference.
Original #37–#46 fixtures/reports and the frozen Phase 0 baseline remain unchanged.

## Reproduce

Model-free verification from the repository with pinned ordinary dependencies:

```sh
.venv/bin/python tools/gemet.py verify
.venv/bin/python tools/hybrid_retrieval.py verify
.venv/bin/python tools/hybrid_retrieval.py verify-report \
  --freeze reports/issue-50-real-rdf-hybrid/freeze \
  --out reports/issue-50-real-rdf-hybrid/run
cargo build --locked --offline -p verity_cli
.venv/bin/python tools/hybrid_retrieval.py scope-canary --binary target/debug/verity
.venv/bin/python tools/hybrid_retrieval.py verify-lexical \
  --binary target/debug/verity --out reports/issue-50-real-rdf-hybrid/run
.venv/bin/python tools/verify_pre_llm.py
```

The last command requires a clean committed tree and runs the complete existing
Rust/Python/format/Clippy/reference pipeline plus these new checks. Use the
pinned rustup toolchain; a Homebrew `cargo` ahead of rustup can bypass the override.
To repeat inference explicitly on a capable local host, first reuse or acquire
#38's [exact pinned assets/runtime](../../docs/embedding-experiment.md). Keep both
build target directories separate:

```sh
mkdir -p artifacts/hybrid-baseline-source
# Read-only extraction of the historical source; no checkout mutation.
git archive be68f23c5f46842d4b7bbe2942f50c4c2e6a64af Cargo.toml Cargo.lock rust-toolchain.toml crates | \
  tar -xf - -C artifacts/hybrid-baseline-source
mkdir -p artifacts/hybrid-baseline-source/crates/verity_cli/examples
cp crates/verity_cli/examples/retrieval_session.rs \
  artifacts/hybrid-baseline-source/crates/verity_cli/examples/
cargo build --release --locked --offline \
  --manifest-path artifacts/hybrid-baseline-source/Cargo.toml \
  --target-dir artifacts/hybrid-baseline-target \
  -p verity_cli --bin verity --example retrieval_session
cargo build --release --locked --offline -p verity_cli \
  --bin verity --example retrieval_session
/path/to/embedding-runtime/bin/python tools/hybrid_retrieval.py prepare \
  --model-dir /path/to/pinned/embeddinggemma-2-assets \
  --baseline-binary artifacts/hybrid-baseline-target/release/verity \
  --binary target/release/verity \
  --baseline-session artifacts/hybrid-baseline-target/release/examples/retrieval_session \
  --session target/release/examples/retrieval_session \
  --out artifacts/hybrid-repeat/freeze --cpu-description 'record actual hardware and scheduler'
/path/to/embedding-runtime/bin/python tools/hybrid_retrieval.py run --allow-inference \
  --freeze artifacts/hybrid-repeat/freeze --out artifacts/hybrid-repeat/run
.venv/bin/python tools/hybrid_retrieval.py verify-report \
  --freeze artifacts/hybrid-repeat/freeze --out artifacts/hybrid-repeat/run
```

All report files are covered by `checksums.json`; each freeze/run has its own
complete inventory. `frozen-code.tar.gz` also retains the historical Rust source
and experiment transport used for the baseline. Fresh preparations pin the
actual rebuilt binaries, so platform-specific executable hashes may differ.
Performance is not expected to reproduce byte-for-byte.

The separate [parser study #48](../issue-48-grounded-models/README.md) may use these
original graph-qualified retrieval candidates in a newly frozen, separately
scored vocabulary-grounding experiment. A retrieval hit does not count as a
correct NL→IR proposal. No model is connected to Find or Confirmed Ask, and no
Ask holdout, automatic execution, generated SPARQL, SERVICE, write endpoint,
new graph authorization or production rollout is added.
