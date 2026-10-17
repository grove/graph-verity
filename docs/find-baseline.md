# Measured lexical Find baseline

Issue #37 adds model-free BM25 to the [authorized discovery catalog](discovery-catalog.md).
It returns partial discovery candidates, not answers or truth judgments. No model,
network query, RDF write, raw SPARQL or sealed Ask holdout is involved.

```sh
cargo build --release --locked --offline -p verity_cli
target/release/verity find data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json \
  data/wikidata/discovery.json examples/find/oslo.json
python3 tools/retrieval.py verify
python3 tools/retrieval.py run --binary target/release/verity \
  --out artifacts/retrieval-new --cpu 0 \
  --cpu-description 'record actual CPU model, VM/emulation and budget here' \
  --compiler 'record rustc -Vv here'
python3 tools/retrieval.py verify-report --out artifacts/retrieval-new
```

`--cpu` uses Linux scheduler affinity and is inherited by the CLI. Select an
available CPU from `os.sched_getaffinity(0)`. On macOS omit it; those timings cannot
establish pinned-CPU acceptance. Use a fresh output directory. The measurements
run no build or downloader; build the release binary first on the measured host.
The [retained report](../reports/issue-37-bm25/README.md) records the tested binary,
compiler, container image, hardware context and complete reproduction command.

## Ranking contract

The strict request has `query` (1..4096 UTF-8 bytes, nonblank), a nonempty graph
`scope`, optional `role` (`entity`, `predicate`, `class`), and `limit` (1..50,
within policy). Unknown fields fail. The CLI builds an index for its operator
scope file; request scope can select a subset. Both scopes must be authorized.
An index bound to another policy fails. An optional final `INDEX` argument checks
a persisted index by rebuilding and comparing it; there is no cache fast path.
The [Find MVP guide](find-mvp.md) covers explanations and entity navigation.

All document counts, average lengths, document frequencies, candidates and returned
text are computed after graph and role filters. A document is `(graph, original
IRI)`, including duplicate IRIs across graphs. Each unique normalized query token
contributes `ln(1 + (N - df + 0.5)/(df + 0.5)) * tf * (k1 + 1) /
(tf + k1 * (1 - b + b * length/average_length))`, with fixed `k1=1.2`, `b=0.75`.
It uses #36's unweighted full-IRI/observed-text postings and Unicode tokenization,
without stemming, translation, stopwords, label propagation or synonym inference.
Repeated query tokens do not multiply scores. Nonmatching documents are omitted.

Exact original IRIs and case-folded exact observed labels, aliases and identifiers
form a tier before BM25 scores; descriptions do not get this tier. Trimmed query
text is used for matching. Ties sort by original IRI, then source graph. Several
exact distinct IDs produce `ambiguous_exact` even when top-k hides candidates.
Other responses say `ranked` or `no_match`. Partial lexical ambiguity is not
automatically detected; no candidate does not establish semantic absence.

Hits retain graph-qualified IDs, scores, exact-match flags, roles and bounded
observed text with original predicates, literal datatypes/languages and truncation
flags. The response includes immutable snapshot identity, selected graph hashes
and source/license/revision records, index/ranking revisions and algorithm rules.
Counts and provenance outside the request scope are never returned. Scores across
different scopes or role filters are not directly comparable. RDF text, including
HTML, instructions and SERVICE syntax, stays untrusted JSON data.

`find-batch` accepts an array of 1..1000 requests in the same argument position.
It builds once, returns per-query in-process timings and either `result` or `error`,
plus build time and pretty-JSON index size. Request failures remain in the batch;
batch exit success means the envelope was processed, not that every query worked.
`find` errors emit stderr JSON and no partial stdout. The evaluation runner treats
per-query errors as zero relevance scores, preserves them, and exits unsuccessfully.

## Frozen evidence and interpretation

`benchmarks/retrieval/manifest.json` pins corpus bytes, policy/scope/provenance,
judgments, parameters and two separate formulation files. Each split has 80 queries:
40 Norwegian and 40 English, ten per family (identifier, entity, alias, predicate,
description, multi-relevant, ambiguous, no-match). They were written for retrieval,
without importing Ask benchmark questions or accessing the sealed holdout. Retained
Wikidata and GeoNames/Schema.org source licenses are unchanged. Relevance scoring
uses Wikidata development and the synthetic supplement; GeoNames is measured for
build/runtime coverage only. A small Apache-2.0 AI-authored supplement supplies bilingual descriptions and duplicate labels missing
from those captures. Predicate judgments deliberately target original directClaim
IRIs, not their separately labelled Wikidata property entities.

Development and evaluation share 80 target intents/judgments with distinct public
formulations. They are correlated public development evidence, not independent
generalization estimates. Several ambiguity cases are prefixed variants of one
collision. Coverage and sample diversity are limited. All judgments are AI-authored,
exploratory and human-review pending; no stakeholder quality claim is made. There
was no relevance tuning after the freeze. See the retained scale preflight failure
and subsequent shorter load recipe; neither changes the relevance formulations.

The 60 relevant queries per split (30/language) contribute macro Recall@1/5/10/50
and MRR@10, including zero scores for errors/misses. Recall is the fraction of all
judged relevant graph-qualified IDs retrieved, not any-hit accuracy. Ten ambiguous
and ten no-match cases are reported separately, with candidate counts, exact collision
flags, coverage, false positive behavior and errors. They are never silently removed
from their denominators. Per-language, per-family and language/family scores include
sample counts and descriptive 95% percentile bootstrap intervals (2,000 query-level
resamples, seed 37). Correlated AI judgments limit inference; degenerate intervals
on uniform outcomes do not imply certainty about other queries.

Each run retains compressed raw ranks and failures, all request files, source/index
manifests, input/code/binary hashes, raw timings, and environment metadata. The report
verifier recomputes metrics and timings from ranks and checks artifact hashes. Quality
target failures are reported; they do not fail engineering verification or change the
frozen denominator. They require revision before a quality claim or adoption decision.

Cold p50/p95/p99 cover fresh process startup, RDF import, index construction, one
query and JSON I/O; OS page caches are not evicted. Warm timings cover `find` and
result construction in the same process, excluding JSON serialization/I/O; the first
query is retained. Build time excludes import and includes manifest hashing/validation.
Index size is pretty-JSON bytes. Aggregate RSS is a conservative sum of CLI and
controller process high-water marks, including the in-memory RDF store and batch
results. It is not a per-index allocator measurement. The runtime has no worker
processes. The single CPU/thread environment and emulation limits must accompany
reported performance.

The 10,000-resource synthetic corpus is generated from a byte-pinned fixed recipe
and checked before measurement, with 19,996 quads and two predicate resources counted
in the cap. It tests a modest bilingual text workload and common terms. It cannot
establish real-domain scale: the initial verbose recipe exceeded #36's conservative
64MiB allocation budget, and that failure is retained separately. Limits, security,
provenance, relevance and performance are distinct results. No embeddings, HTTP
serving, production ingestion, general ambiguity detector or Ask changes are included.
