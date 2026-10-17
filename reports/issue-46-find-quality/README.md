# Issue #46: predicate retrieval and conservative Find outcomes

**Decision: keep BM25, ship explicit graph-local predicate retrieval associations,
and defer fusion integration.** On the unchanged public evaluation formulations,
Recall@10 improves **.833 → 1.000** and MRR@10 **.833 → .992**. The original
predicate failure family improves from **0/10 → 10/10 retrieved at 10**, with
predicate MRR@10 **.950**. Entity/identifier/alias/description metrics do not
regress. This is exploratory agreement with correlated AI judgments, not human
quality, production readiness, a Phase 0 GO or authorization to implement #40.

## Mapping and source evidence

The [implementation contract and offline walkthrough](../../docs/find-quality.md)
describe both source witnesses and exact outcome rules. No source bytes, gold,
original identifiers, graph roles or #37–#39 reports are modified. No external
labels or inferred aliases are introduced. A `via` association explicitly records
that a separate source resource carries the text and an authorized graph-local
`wikibase:directClaim` statement links it to the predicate. The original text
predicate, language and datatype remain attached; enclosing graph/snapshot and
source/license/revision metadata identify both witnesses.

In `urn:graph-verity:wikidata:development`, six explicit links support the observed
predicates P1082, P131, P17, P31, P36 and P571. There are 230 label/alias associations:
176 English, 40 Norwegian Bokmål and 14 Nynorsk. P31 was not added as a new judged
case; the frozen predicate family still has ten formulations targeting five
predicates per split. The other four observed predicates (`directClaim`,
`rdf:type`, `rdfs:label`, `skos:altLabel`) have no qualifying mapping witness and
receive no association. The GeoNames and description supplement have no qualifying
links. Missing labels or links remain missing. No cross-graph fallback, mapping
chain, IRI-spelling guess, description/identifier transfer or RDF assertion is made.

[`smoke.json`](smoke.json) retains four fresh offline CLI processes: Norwegian
`Hovedstad` / English `Capital` → original direct P36 IRI → bounded `predicate`
usage triples → original P36 property-source statements. All pages have the same
immutable snapshot ID and CC0 source graph. The new navigation direction executes
one fixed validated read-only template with existing row/evidence, offset,
timeout and output caps. It includes Norway Q20 → P36 → Oslo Q585, and does not
infer an answer from the query words.

## Frozen lexical comparison

[`comparison.json`](comparison.json) recomputes the original
[#37 baseline](../issue-37-bm25/README.md) and the [fresh run](run/summary.json)
against the unchanged 80 development + 80 evaluation formulations. #39 retained
exactly the original #37 rankings. Each split remains 40 Norwegian/40 English:
60 scored relevant queries (30/language), ten ambiguous, ten no-match. No judgment,
formulation, parameter or denominator changed; no extra development questions were
needed. The mapping/outcome policy was fixed from RDF structure and development
before revised evaluation. The pinned repeat used the same implementation after
the initial environment correction described below; there was no evaluation tuning.

Means [descriptive 95% interval], using 2,000 query-level percentile bootstrap
resamples, seed 37:

| Split / system | n | Recall@1 | Recall@5 / @10 / @50 | MRR@10 |
| --- | ---: | --- | --- | --- |
| Both / original BM25 | 60 | .744 [.644, .839] | .833 [.733, .917] | .833 [.733, .917] |
| Development / revised BM25 | 60 | .911 [.856, .958] | 1.000 [1, 1] | 1.000 [1, 1] |
| Evaluation / revised BM25 | 60 | .894 [.831, .950] | 1.000 [1, 1] | .992 [.975, 1.000] |

The revised evaluation Recall@10 paired gain is **+.167 [.083, .267]**;
MRR@10 gain **+.158 [.075, .250]**. Development gains are +.167 [.083, .267]
for both. Full baseline/revised group metrics, language/family cross-tabs, sample
counts and paired intervals remain in the JSON, including non-perfect Recall@1.

| Revised group | n per split | Dev Recall@1 / MRR@10 | Eval Recall@1 / MRR@10 | Recall@5 / @10 / @50, both |
| --- | ---: | --- | --- | --- |
| Norwegian | 30 | .911 [.833, .967] / 1.000 [1, 1] | .878 [.778, .967] / .983 [.950, 1.000] | 1.000 [1, 1] |
| English | 30 | .911 [.833, .967] / 1.000 [1, 1] | .911 [.833, .967] / 1.000 [1, 1] | 1.000 [1, 1] |
| Identifier/entity/alias/description, each | 10 | 1.000 [1, 1] / 1.000 [1, 1] | 1.000 [1, 1] / 1.000 [1, 1] | 1.000 [1, 1] |
| Predicate | 10 | 1.000 [1, 1] / 1.000 [1, 1] | .900 [.700, 1.000] / .950 [.850, 1.000] | 1.000 [1, 1] |
| Multiple relevant IDs | 10 | .467 [.417, .500] / 1.000 [1, 1] | .467 [.417, .500] / 1.000 [1, 1] | 1.000 [1, 1] |

Overall Recall@10 >=.90 and MRR@10 >=.75 **pass**, and both language targets
(Recall@10 >=.80, MRR@10 >=.65) **pass**, on this recorded corpus. Small uniform
families yield degenerate intervals; public formulations share intents and are
correlated. Neither the intervals nor perfect family recall validate generalization.

The remaining relevant rank-one miss is evaluation `predicate-no-03`,
“Hvilken egenskap angir hovudstad i landet”: P131 ranks above intended P36, which
is second. It surfaces `ambiguous_candidates`. No stopword, scoring adjustment or
post-hoc threshold was introduced after observing this miss.

## Ambiguity, no-match and failures

`find-outcomes-v1` uses graph-qualified exact counts and total lexical matches
before clipping. More than one exact hit is `ambiguous_exact`; one exact hit is
`ranked`; zero hits is `no_match`; multiple non-exact hits are
`ambiguous_candidates`; a lone non-exact hit is `low_confidence`. There is no
score cutoff, automatic selection, candidate suppression or claim that scores
calibrate confidence. Duplicate IRIs across graphs require graph selection too.
`exact_ids` still counts distinct IRIs; `exact_candidates` counts (graph, IRI).

| Split | Ambiguous partial | Ambiguous exact | Low confidence | Exact ranked | No match |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development, all 80 | 37 | 2 | 21 | 10 | 10 |
| Evaluation, all 80 | 44 | 0 | 26 | 0 | 10 |

All ten judged ambiguous queries in each split retain both relevant IDs at 50;
development surfaces two exact collisions and eight conservative partial states,
evaluation ten partial states. These states intentionally overflag uncertainty:
relevant single-token matches may still require inspection. All ten no-match
queries per split return no candidates (return rate .000 [0, 0]), preserving the
original observable behavior. That observation is not a promise about unseen
no-match questions: public IRI tokens or generic words can retrieve irrelevant
candidates. No retrieved match never proves real-world absence. There are **zero
query, timing or trial failures** in the completed runs. See the [Norwegian/English
state examples](../../docs/find-quality.md#fixed-representation-and-policy-before-evaluation).

## Separate pinned development-only fusion re-check

The [#38 decision and evidence](../issue-38-embeddinggemma/README.md) remain
unchanged. The [new freeze](fusion-development/freeze.json) predates new inference
and records verified upstream assets, runtime, binary/source hashes, exact scoped
exports and requests. Model: `google/embeddinggemma-2`, upstream commit
`914f7f89142e33e77833254d9c9b90c3cef7303b`; CPU FP32, eager attention, four intra-op
threads, one inter-op thread, 256-token cap, normalized 768-dimensional vectors,
document batches of eight. Python 3.14.8, Torch 2.14.1, Transformers 5.20.1 and
Sentence Transformers 6.1.0. Exact package/build identities are retained in the
freeze. Official assets and the existing local runtime were reused offline;
no weights were downloaded. Original upstream/license evidence stays in #38.

Independent reference/runtime [parity](fusion-development/parity.json) passes all
eight cases; worst absolute vector error 5.96e-8. The tokenizer warning measures
intentional untruncated long parity input; actual inference remains capped at 256.
All 240 system/query rankings (80 development formulations × three methods),
authorized document exports, vectors, requests, summaries and failure logs are
retained under [fusion-development](fusion-development/artifacts.json).

| Development method | Recall@1 | Recall@5 | Recall@10 / @50 | MRR@10 | Predicate R@10 / MRR@10 | No-match candidate returns |
| --- | --- | --- | --- | --- | --- | ---: |
| Revised BM25 | .911 [.856, .958] | 1.000 [1, 1] | 1.000 [1, 1] | 1.000 [1, 1] | 1.000 / 1.000 | 0/10 |
| Dense | .711 [.608, .814] | .867 [.783, .950] | .867 [.783, .950] / 1.000 [1, 1] | .829 [.742, .917] | 1.000 / .900 | 10/10 |
| Fixed equal-weight fusion | .778 [.681, .867] | .900 [.817, .967] | 1.000 [1, 1] | .889 [.815, .957] | 1.000 / 1.000 | 10/10 |

Fusion uses unchanged RRF constant 60, equal weights, top 50 and IRI/graph ties,
with no exact-match override. Its paired MRR@10 change vs revised BM25 is
**-.111 [-.185, -.043]**, with zero Recall@10 gain. Norwegian/English MRR is
.911/.868 vs lexical 1.000/1.000. Dense MRR is .842/.817. Both semantic methods
return all judged ambiguous IDs, but also return candidates for 10/10 no-match
cases (candidate return rate **1.000 [1, 1]**). Their no-match lists
are conservatively marked `ambiguous_candidates`, without hiding false candidates.
They do not inherit lexical exact-match priority or a confidence calibration.

**Keep BM25 / defer fusion**, rather than adding an opt-in product path. The exact
blockers are unavailable independent relevance/usability review and unresolved
semantic false-candidate/exact-priority tradeoffs; the revised lexical representation
also removes this development trial's recall advantage. No dense/fusion evaluation
or scale inference was run for #46; #38's evaluation stays historical and is not
reinterpreted as revised-index evidence. No new semantic runtime-budget or
product-ready claim is made. A future product trial needs a separate documented
decision; ordinary CI never installs/invokes a model.

## Fresh native runtime measurements

Apple M1 Pro, ten cores, 32 GiB RAM; macOS 26.6.2 arm64; Python 3.12.14;
repository-pinned Rust 1.99.1 (`58cf8f9c3`), locked release build. Worker environment
budget one, host scheduler, no CPU affinity/quota. These are native host
observations, not pinned-CPU/deployment-hardware acceptance. Thirty fresh-process
cold and 200 resident warm samples per corpus include the first query. Cold covers
import/build/query/JSON I/O with OS caches retained; warm covers ranking/result
construction, excluding JSON serialization/I/O. Build excludes RDF import.

| Corpus | Graph-qualified resources | Index bytes | Build ms | Cold p50 / p95 / p99 ms | Warm p50 / p95 / p99 ms |
| --- | ---: | ---: | ---: | --- | --- |
| wikidata | 40 | 279,464 | 3.082 | 10.486 / 11.553 / 11.800 | 0.049 / 0.067 / 0.104 |
| cities | 430 | 492,024 | 7.409 | 16.842 / 17.812 / 19.373 | 0.057 / 0.065 / 0.078 |
| descriptions | 9 | 19,749 | 0.451 | 5.237 / 5.822 / 6.146 | 0.031 / 0.033 / 0.036 |
| scale | 10,000 | 11,980,881 | 167.883 | 240.288 / 244.257 / 253.909 | 7.250 / 7.790 / 7.917 |

Aggregate RSS upper bound: **360,841,216 bytes (344.12 MiB)**, summing controller and CLI process high-water marks.
The proposed **500ms warm p95 and 4GiB RSS budgets pass on these measured
corpora**. The 10,000-resource synthetic workload is only 19,996 modest quads;
it does not establish production or real-domain 10,000-resource readiness,
long-description behavior or a hard resource cap. The prior verbose allocation
failure remains in #37. Predicate associations increase Wikidata index size from
141,290 to 279,464 bytes; no index limit was relaxed.

The first successful measurement used Homebrew Rust 1.99.0 because it preceded
rustup on PATH. Its lexical report, development model trial, comparison and exact
reason are retained in [`initial-unpinned.tar.gz`](initial-unpinned.tar.gz).
The same source/rules/assets were repeated with the pinned toolchain; no
parameters or judgments changed. Quality results agree. The pinned release build
warned that the optional debug-info stripping tool could not load its LLVM
library; the binary built successfully and its hash is retained. This warning
and the first environment mismatch are not concealed as benchmark failures or
silently discarded trials.

## Verification and reproduction

From a clean checkout, use the pinned toolchain (`rustc -Vv` must say 1.99.1;
a standalone Homebrew cargo/rustc can bypass the rustup override). No data/model
refresh or sealed-holdout access is required:

```sh
cargo build --release --locked --offline -p verity_cli
python3 tools/retrieval.py verify
python3 tools/retrieval.py run --binary target/release/verity \
  --out artifacts/find-quality-new/run --cold 30 --warm 200 \
  --compiler "$(rustc -Vv)" --cpu-description 'record actual hardware and scheduler'
python3 tools/find_quality.py compare --out artifacts/find-quality-new
python3 tools/retrieval.py verify-report --out artifacts/find-quality-new/run
python3 tools/retrieval.py verify-report --out reports/issue-46-find-quality/run
python3 tools/find_quality.py verify-fusion-dev \
  --out reports/issue-46-find-quality/fusion-development
cargo test --locked --offline -p verity_core --test find --test navigation
cargo test --locked --offline -p verity_cli --test navigation
.venv/bin/python tools/verify_pre_llm.py
```

The last command runs the full normal Rust/Python CI pipeline on a clean committed
tree: formatting, Clippy, Rust and Python tests, byte-for-byte dataset rebuilding,
frozen report verification (including #37–#39 and this report), original negative
Ask evidence, independent reference queries and manual/oracle replay. It does
not invoke a model, refresh gold or open a private holdout. `verify-fusion-dev`
recomputes public development denominators, relevance metrics, parity and summaries
from retained evidence without importing the model runtime. Inference reproduction
is a separate explicitly opt-in command in the [usage contract](../../docs/find-quality.md).

New regressions cover the original ten predicate development formulations;
Norwegian/English labels and alias exactness; missing/unused links; blank/literal
mapping targets; no chaining or graph/role inference; omitted languages;
graph-qualified duplicate exact IDs; stable ties; private label/mapping/source/count
canaries; conservative partial/no-match states before clipping; bounded predicate
usage pages; persisted index validation; both original mapping witnesses and RDF
language/datatype provenance; unchanged frozen denominators; and rejected edits
that relabel development inference as evaluation. Existing unknown/invalid IRI,
policy/snapshot mismatch, injection-string, timeout/output/evidence cap and
no-partial-stdout tests remain in the full suite. No UI was added.

[`release.json`](release.json) binds the measured binary/Rust sources and the
report/smoke inventories. [`run/environment.json`](run/environment.json) records
compiler, hardware context, raw definitions, source hashes and RSS;
[`run/artifacts.json`](run/artifacts.json) binds raw ranks, timing/request samples,
failures and the frozen synthetic corpus archive. The separately frozen model
trial records its own runtime and source identities before inference.

Optional #40 remains gated on separately demonstrated user need/product approval.
No stakeholder relevance review, usability participants, real-domain scale or
semantic serving performance was manufactured; no autonomous Ask, raw model SPARQL,
SERVICE/write endpoint or sealed-holdout evaluation was added.
