# Retrieval-only protocol v1, issue 50

This protocol and both text variants are frozen before any dense inference or
relevance ranking. `protocol.json` pins the source, queries, judgments, parameters,
model revision, split overlaps, numerical adoption rule and measurement definitions.
`prepare` additionally pins authorized exports, binaries, Rust sources, runtime,
model assets and legal document identities before scoring. No tuning is planned.

There are **122 queries: 40 development and 82 evaluation**, with 62 Norwegian
and 60 English stratum labels. Identifier-only strings have no intrinsic language.
Norwegian authoring includes Bokmål and Nynorsk forms, but has no independent
linguistic review; GEMET's observed Norwegian literals retain `@no`. English-only
new GEMET concepts receive Norwegian queries in the cross-language family. This
is a public evaluation, not a sealed test. Five resource lineages occur in both
splits and are explicitly listed; none is called independent unseen evidence.
The independently sealed Ask holdout is neither opened nor used.

All judgments are AI-authored and source-audited, with original graph-qualified
IRIs and exact source quad witnesses in `cases.json`. The references are not an
exhaustive, expert-reviewed relevance pool. Broad paraphrases may have additional
reasonable answers. No-match means no relevant retrievable resource judged in
this authorized pilot; it says nothing about the absence or truth of RDF facts.
Six ambiguity cases, hard negatives and no-match probes are reported apart
from relevance metrics. Direction questions retrieve relationship vocabulary;
they do not execute a directed path or demonstrate question interpretation.

The primary three-way comparison uses the **unchanged #46 BM25 representation**,
including graph-local mapping rules, exact tier, k1=1.2/b=0.75, and top 50. Dense
and equal-weight RRF use precisely that authorized document text and role pool.
A separately declared **skos-definitions-v1** variant adds the original
`skos:definition` field as a bounded description for **all three methods**.
It is never credited as a fusion-only gain. Candidate IDs and roles are identical
across variants. Both retain original source literal language/datatype and source
predicate witnesses. There is no model-generated document text or answer-ID
augmentation. Identifiers occur naturally in documents and explicitly in the
identifier query family; judgment files never enter embeddings or prompts.

Each method retains top 50 graph/snapshot-qualified hits and errors. Dense also
retains every authorized role-filtered similarity, document/query vectors and
full catalog exports for model-free replay. Fusion is unchanged top50/top50 RRF
with constant 60, weights 1/1 and ties by IRI then graph. No threshold, lexical
veto, exact-ID override, or calibrated semantic confidence is added. Candidate
states are determined before clipping: no authorized role candidates ->
`no_match`; one -> `low_confidence`; several -> `ambiguous_candidates`. BM25
retains its more conservative #46 `ambiguous_exact`/candidate/lexical no-match
behavior. Similarity and lexical scores are discovery signals, never truth.

Provisional adoption requires >=.05 absolute Recall@10 or >=.03 MRR@10 gain and
a positive paired descriptive 95% lower bound; neither language may regress
>.02 on either measure; zero exact-first-rank regressions; no-match candidate
returns may increase by at most .02 absolute; actual resident warm fusion p95
<=1000ms and aggregate RSS <=4GiB at <=10000 resources; no failures. These are
engineering screening criteria. Independent relevance/usability review and a
separate owner/release decision remain required even if every check passes.
BM25 stays the Find default. Dense or fusion never executes Ask or raw SPARQL.

Timing includes JSON framing, persistent lexical request/response, dense
inference/ranking, and result serialization for every frozen query, including the
first. Five predeclared fresh-process cold probes additionally include imports,
model load, vector load, lexical import/build, query and process teardown. OS
caches remain populated; these are process-cold observations, not cold disk.
The long query distribution is retained, not replaced with easy short strings.
Five samples cannot estimate cold tail latency reliably; p95/p99 are maxima.
Four Torch intra-op threads, one inter-op, native CPU FP32, no Metal, no isolated
CPU affinity/quota; scheduler and cache conditions are recorded. RSS sums parent
and maximum sequential child high-water marks, a conservative upper bound.
Query bootstrap intervals use 2000 resamples/seed37 and are descriptive given
public AI judgments and correlated targets. No population inference is claimed.

See [source selection and limits](../../data/gemet/README.md),
[reproduction and measured decision](../../reports/issue-50-real-rdf-hybrid/README.md),
and the separate [retrieval-grounded parser study #48](../../reports/issue-48-grounded-models/README.md).

Instrumentation note: the first complete run is retained. Its cold-worker RSS
accounting omitted the nested Rust helper; the repeat froze corrected accounting
for parent + direct child + nested child, and durable per-row logging. No model,
query, judgment, candidate, rank rule or numerical adoption threshold changed.
Both raw attempts are linked in the final report; repeats are not independent
relevance evidence.
