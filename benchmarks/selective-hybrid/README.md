# Selective hybrid preregistration v1 (issue 53)

This is an opt-in, retrieval-only experiment. BM25 remains the shipping Find
backend. No result interprets a question, executes a plan, or establishes truth.
RDF descriptions are untrusted data. Independent human adjudication is unavailable;
every conclusion must be marked **AI-reference exploratory**, never stakeholder-ready.

## Frozen inputs and evaluation

`protocol.json` binds the corpus, model, cases, judgments, calibration and this
document. `prepare` freezes actual software sources, compiler, session binaries,
runtime package versions/RECORD hashes, weight/tokenizer hashes, legal identities,
and both authorized exports before scoring any new questions. The exact model is
`google/embeddinggemma-2`, revision
`914f7f89142e33e77833254d9c9b90c3cef7303b`, unchanged CPU FP32, eager attention,
768 normalized dimensions, 256 tokens, four intra-op/one inter-op threads. No
quantization or model substitution is attempted. Fresh official Sentence
Transformers tokenizer/vector parity runs before resident document inference.

Reuse #50's unchanged 2,215 graph-qualified licensed resources and exact saved
document exports. Compare BM25, dense alone, original equal-weight top50 RRF
(constant 60), and selective on the same role-authorized candidates in each text
variant. `bm25-46` is the primary historical-text comparison;
`skos-definitions-v1` is a separate representation ablation for all four systems.
Do not credit definition effects to the retrieval algorithm. The 64 MiB index,
input, scope, output and 10,000-resource limits remain unchanged. The retained
5,588-resource rich-description allocation failure remains a scale blocker;
this pilot does not demonstrate 10k-resource feasibility.

All 122 public #50 questions, including its former evaluation, are now
**exposed development/regressions**. No old case or judgment is changed. The
50 new questions contain 36 relevant, two ambiguous and twelve no-match probes.
Their relevant resource lineages do not overlap any #50 judged resource.
They include Norwegian/English paraphrases on different concepts, IRI/label
lookups, battery/salt polysemy, multiple relevant concepts, two original
Norwegian label ambiguities, predicate/class roles, unsupported topics, hard
negatives, nonces and private-graph canary identifiers/text. Exact identifier
language is stratum metadata. Existing GEMET aliases are all exposed in #50;
alias regressions remain there, rather than claiming new independent aliases.
Some targets recur within new evaluation and share vocabulary or ontology with
development; retain their `group_lineage`, and do not call them independent
human validation. Judgments are source-grounded AI references, not exhaustive
expert relevance pooling. No sealed Ask holdout is opened. Source witnesses,
language/datatype, predicate and truncation metadata remain in frozen documents.
Canary queries have no synthetic documents added to the corpus.

## Deterministic lexical-first policy

Exactness uses only the trusted graph-qualified authorized catalog: trim outer
query whitespace; compare IRI case-sensitively, or original observed label,
alias or identifier text with Unicode lowercase. Description equality does
not confer exactness. This mirrors Rust Find; there is no NFC, stemming,
transliteration, model-selected ID, inferred alias or cross-graph label mapping.
Filter scope and role before candidate statistics, scores or exact counts.

Use one total top50 budget per request, not per role: role is explicitly required.
Place every exact candidate first, preserving Rust's exact/BM25/IRI/graph order;
then the first three nonexact lexical candidates; then dense top50 candidates
with cosine >= **0.73**, in descending score/IRI/graph order; then unused lexical
top50 candidates. Deduplicate by `(graph, IRI)` at first occurrence, and clip only
after this ordering. An exact candidate keeps rank one whenever BM25 ranked it
first. More than one exact candidate is `ambiguous_exact` before clipping,
including the same IRI in different graphs. Exact matches can consume the whole
budget. Semantic fill can enter with zero BM25 matches; there is no lexical veto,
agreement requirement, top-one margin or single-answer assumption.

`calibration.json` records the exposed negative scores used to select the cutoff:
the smallest hundredth strictly above their maximum across both representations
(0.7293137907981873). Three lexical head slots are a fixed design budget, not a
searched optimum. No new evaluation ranks are inspected to change either rule.
A shared cutoff avoids fitting tiny role samples but is not probability
calibration. It can reject genuine low-score paraphrases, and lexical head slots
can push semantic results out of top10; report both costs. Retained regressions
include groundwater IRI `concept/3780`, exact `water pollution`, `marriedTo`,
nonces, and the Norwegian overfishing paraphrase. Do not adjust the rule if these
or new questions fail.

Unique exact -> `ranked`; multiple exact -> `ambiguous_exact`; no accepted
candidate -> `no_match`; one nonexact -> `low_confidence`; multiple nonexact ->
`ambiguous_candidates`. All states require deliberate user selection, including
unique exact lookup. No automatic plan filling or execution exists. No-match
means no adequately supported candidate retrieved under this policy within this
authorized index, not absence of facts. Lexical false candidates remain possible;
semantic false candidates above 0.73 remain possible. Preserve actual candidate
return fractions, ambiguous candidate coverage and false `ranked` negatives;
do not disguise failures by excluding negatives or changing denominators.

## Measurement and fixed continuation screen

Every case is run once resident, in frozen order, including first/long requests.
BM25 includes persistent Rust request/response serialization; dense includes
tokenization, CPU inference, role filtering, scoring and serialization; selective
adds actual validation, metadata construction and output serialization. Five
predeclared process-cold probes per representation include Python imports,
model/vector loading, Rust RDF import/index build, query and process teardown.
OS caches remain populated. Five cold p95/p99 observations are maxima, not
reliable tail estimates. Record model load, dense/lexical build, raw/gzip vector
bytes, model/runtime disk footprint, original source description truncation and
token truncation separately. Native Apple M1 Pro / 32 GiB; host scheduler, no
CPU affinity/quota, four CPU inference threads, CPU-only.

Memory keeps the corrected #50 metric: **controller HWM + largest sequential
direct-child HWM + largest nested Rust-child HWM**, conservative summed bound,
potentially double-counting shared pages. Never replace it with a favorable
sampled value. Also sample the complete live controller/descendant process tree
every 200 ms and report its simultaneous RSS separately. A lightweight controller
owns no model; one worker owns the model and one persistent Rust index; resident
and process-cold workers run sequentially. This explicitly investigates removal
of the duplicate concurrently resident model in #50, whose corrected **4.418 GiB**
failure remains visible. Do not claim sampled values capture instantaneous peaks.

Retain complete graph/snapshot-qualified case ranks, component scores, routes,
states, provenance, source literals and flags, all dense scores, and FP32 vectors.
Report Recall@1/5/10/50 and MRR@10 by language/family/role/scope, paired deltas and
2,000 query-bootstrap descriptive intervals, seed37. Repeated target lineages and
AI authorship limit intervals. Ambiguous/no-match cases stay outside positive
denominators. Report exact rank-one preservation, candidate returns and examples,
false confident retrieval and new top10 semantic wins separately.

Continuation requires every justified exact rank-one preserved; Recall@10 gain
>=.05 or MRR@10 gain >=.03 over same-version BM25 with positive paired descriptive
lower bound; neither language regresses >.02 on either metric; no-match return
fraction <= BM25; resident selective p95 <=1s; conservative process-tree bound
<=4 GiB; no failures. This is a continuation screen, **not formal GO**. Failure
or inadequate external review means keep BM25/defer promotion. Do not tune after
scoring. Even all numeric passes need independent relevance/usability review
and a separate owner release/promotion decision.

Normal CI replays all evidence and native current-BM25 ranks without downloading
weights, importing Torch or running inference. Original #37–#50 reports, sources
and historical metrics remain immutable. Reproduction is in the new report.
