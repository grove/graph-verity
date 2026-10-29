# R-GCN / CompGCN research, stage 2

This is a versioned research track. The original v1 GEMET report and scores are
unchanged. Predictions remain ranking hypotheses; only original graph-qualified
RDF statements can support an answer.

## Dataset decision

Use the retained, source-backed Wikidata graph and broaden the benchmark across
relationship families. Do not claim that it supports a service-operator
experiment: the graph contains one `P137` operator edge. The data were captured
from the read-only Wikidata Query Service by selecting the first 1,000 IRI-sorted
items with `P17=Norway` and `P31=Organization`, then retaining original direct
claims whose objects are entity IRIs. The structured data are CC0. The query
responses, original identifiers, predicates, directions, assigned graph scope,
export and their hashes are retained under
[`wikidata-norway-org-v1`](../../rgcn-compgcn-v1/wikidata-norway-org-v1/).

| Measure | Value |
|---|---:|
| Entities / directed original edges / predicates | 2,157 / 5,756 / 84 |
| Predicates with at least 20 edges | 30 |
| Top five predicate share | 72.1% |
| English / Norwegian-labeled nodes | 1,219 / 1,939 |
| Two-hop paths excluding country/type (`P17`/`P31`) | 1,552; 1,313 endpoint pairs |
| Weak components / largest component | 1 / 2,157 |
| `P137` operator edges | 1 |

The single weak component is largely joined by common country, type and industry
objects. Counts do not make the 1,000-root IRI-ordered sample representative.
Most evidence is from a few predicates. Norwegian prompts are translations;
there was no independent reviewer. Treat these as development results, not
expert relevance judgments.

Dataset freeze: export manifest SHA256
`8814fd107b756f2f6a38decf293b9cf918a22232901665057752a1b928cb9616`, snapshot
SHA256 `584e068d3a98342ff608be7b881950cb8a1f9c7ec91ecbb0747956384d6452eb`.
The exact source-response hashes and predicate histogram are in
[`dataset-audit.json`](dataset-audit.json). Rebuild the RDF export using the
v1 instructions; build the v2 question, reference and split artifacts with:

```sh
python tools/rgcn_compgcn_v2.py build --out /tmp/wikidata-relations-v1
```

Two clean builds produced identical byte hashes for questions, references,
splits and audit. Benchmark sources and score outputs are hash-bound in
[`manifest.json`](manifest.json) and each score receipt.

## Benchmark and leakage controls

The frozen benchmark has 236 English/Norwegian questions in 56 source-lineage
groups: forward one-hop, inverse-direction one-hop, predicate retrieval,
two-hop paths, ambiguous aliases and unsupported/no-match cases. The fixed
group split has 174 train, 26 validation and 36 test questions. Test contains
28 relevant cases (14 per language), four ambiguous cases and four graph-bounded
no-match cases. Each positive witness points to the original graph-qualified
quad. Out-of-scope GEMET hard negatives are source-backed; predicate and
direction distractors are contrastive candidates, not claims that those RDF
statements are false. No-match means no matching evidence in this bounded graph.

English/Norwegian variants and question families for the same source edge are
kept together. Validation/test witness edges are removed from transductive GNN
message passing. The separate unseen-entity split holds out 16 entity IRIs,
removes all 206 incident edges from message passing, and excludes touching
question groups from training; it has 94 train, 14 validation and 42 test
queries. Tests check edge/query group isolation and exact source-witness
membership; no exact prompt string occurs across splits. This controls direct
edge and duplicate-prompt leakage but does not turn these agent-authored
references into independent semantic gold.

## Matched deterministic results

`baseline-score-v4` is preserved. `baseline-score-v5` adds EmbeddingGemma, using
the same frozen questions, graph scope, references, and scoring code. Entity
questions rank within the 2,157-entity pool; predicate questions rank within
the 84-predicate pool. Each method generates and ranks its own candidates; this
is end-to-end retrieval, not shared-pool reranking. Detailed scores and raw
ranks are in [`baseline-score-v5`](baseline-score-v5/).

| Method | Relevant n | R@1 | R@5 | R@10 | MRR@10 | nDCG@10 | No-match suggestions / 4 | Mean top-10 source-witness coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 28 | 0.000 | 0.107 | 0.107 | 0.023 | 0.043 | 4 | 0.031 |
| EmbeddingGemma 2 | 28 | 0.000 | 0.179 | 0.286 | 0.068 | 0.119 | 4 | 0.044 |
| Native QV2 source-witnessed one-hop | 28 | 0.000 | 0.321 | 0.393 | 0.111 | 0.178 | 4 | 0.053 |
| Typed adjacency one-hop oracle | 28 | 0.857 | 0.857 | 0.857 | 0.857 | 0.857 | 0 | 0.889 |
| Typed adjacency two-hop oracle | 28 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0.889 |

| Test stratum | n | BM25 R@10 | EmbeddingGemma R@10 | Native QV2 R@10 | 1-hop oracle R@10 | 2-hop oracle R@10 |
|---|---:|---:|---:|---:|---:|---:|
| English | 14 | 0.143 | 0.357 | 0.429 | 0.857 | 1.000 |
| Norwegian | 14 | 0.071 | 0.214 | 0.357 | 0.857 | 1.000 |
| Forward one-hop | 8 | 0.125 | 0.125 | 0.125 | 1.000 | 1.000 |
| Reverse one-hop | 8 | 0.250 | 0.250 | 0.250 | 1.000 | 1.000 |
| Predicate retrieval | 8 | 0.000 | 0.625 | 1.000 | 1.000 | 1.000 |
| Two-hop path | 4 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |

EmbeddingGemma improves over BM25 but trails QV2 overall, particularly on
predicate retrieval. BM25, EmbeddingGemma, and QV2 each suggested candidates
for all four no-match questions. Every method preserved the authorized graph
and exact identifier. One-hop and two-hop adjacency receive structured
anchor/property hints, so they are traversal oracles, not natural-language
baselines. Exact source-path Recall@10 on the four two-hop cases is 0/4 for
BM25, EmbeddingGemma, QV2, and the one-hop oracle; the structured two-hop
oracle is 4/4. References are agent-authored, source-checked development
evidence, not independent semantic gold; these small denominators support no
significance claim.

## Reproduction

Install the pinned research environment into a separate virtual environment;
this does not download any model weights:

```sh
python3.12 -m venv /tmp/gv-rgcn-v2
/tmp/gv-rgcn-v2/bin/pip install -r experiments/rgcn-compgcn-v2/requirements-gnn.lock
PYTHONPATH=tools /tmp/gv-rgcn-v2/bin/python -m unittest \
  test_rgcn_compgcn_models test_rgcn_compgcn_run_v2 test_rgcn_compgcn_v2
```

The retained native captures were made after building the existing Rust
retrieval examples. Re-capture in fresh output directories, then score only
after capture (the scoring command opens references):

```sh
cargo build --locked --offline -p verity_cli --example retrieval_session --example neighborhood_session
python tools/rgcn_compgcn_v2.py capture-native \
  --questions experiments/rgcn-compgcn-v2/wikidata-relations-v1/questions.json \
  --out /tmp/native-capture --bm25-session target/debug/examples/retrieval_session \
  --neighborhood-session target/debug/examples/neighborhood_session
python tools/rgcn_compgcn_v2.py capture-adjacency \
  --questions experiments/rgcn-compgcn-v2/wikidata-relations-v1/questions.json \
  --out /tmp/adjacency-capture
python tools/rgcn_compgcn_v2.py score \
  --questions experiments/rgcn-compgcn-v2/wikidata-relations-v1/questions.json \
  --references experiments/rgcn-compgcn-v2/wikidata-relations-v1/references.json \
  --native-capture /tmp/native-capture --adjacency-capture /tmp/adjacency-capture \
  --out /tmp/baseline-score
```

## Models and frozen comparison

The isolated environment pins Python 3.12.14, PyTorch 2.11.0 and PyTorch
Geometric 2.7.0. R-GCN uses PyG `RGCNConv` with four relation bases over the
original directed subject-to-object edges. CompGCN composes incoming entity and
relation states by subtraction, `phi(e,r)=e-r`, and learns relation updates at
each layer. Both use the same 768-dimensional EmbeddingGemma initial node,
relation and question vectors, two 128-dimensional layers, 10 link negatives
and 10 query negatives, and a combined link/query objective. Link scoring uses
the directed translation distance `-||head + relation - tail||² / sqrt(128)`;
the fixture verifies swapping subject/object changes the score. The graph
message passing is CPU-only; no inferred reverse RDF edges are added. These
models differ architecturally: R-GCN has basis-decomposed predicate weights
while CompGCN composes and updates relation states.

The synthetic fixture suite verifies genuine forward passes, output shapes,
directed head/tail scoring, loss/backward gradients, a test-only optimizer step,
checkpoint reload, deterministic seeds and split guards. No research graph
training was run. Results must report candidate generation before any shared
candidate reranking; at evaluation the frozen query head ranks all graph-local
entities and predicates. Link prediction is an auxiliary objective, not the
primary acceptance metric.

The preregistration records the dataset/code/input hashes, seeds 117/118/119,
AdamW at 0.001, max 100 epochs, patience 10, CPU with 4 intra-op / 1 inter-op
thread, six-hour total ceiling and 24 GiB process-RSS ceiling. It requires at
least +0.10 absolute Recall@10 over the stronger matched text method and a
positive paired improvement over native QV2;
the paired query-group bootstrap 95% interval must have a positive lower bound.
Direction, language, graph scope, exact IRI, no-match and witness regressions
must also be reported. R-GCN/CompGCN will use three seeds on transductive and
unseen-entity partitions. The original preregistration is in
[`experiment-manifest-v7.json`](experiment-manifest-v7.json); the completed
feature baseline is bound in the final manifest below.

The owner set feature-inference admission to 21,000,000,000 bytes; the GNN
training admission threshold and process-RSS ceiling remain 24 GiB. All
intermediate preflight receipts v3 through v14 are preserved. The latest
training-gate result is v14 below; a memory-availability snapshot does not
estimate model RSS.

## Current feature and training status

Owner-approved EmbeddingGemma inference completed on the M1 Pro using
`google/embeddinggemma-2` revision
`914f7f89142e33e77833254d9c9b90c3cef7303b`. The authorization record used was
`/private/tmp/graph-verity-embedding-inference-authorization-v1.json`; it is
local and is not committed. It binds dataset manifest SHA
`8814fd107b756f2f6a38decf293b9cf918a22232901665057752a1b928cb9616`, benchmark
manifest SHA `9e3e92142297a9d08c1a29a5a4c0634b8de47073e398bf8adfddd9657d6fecc4`,
questions SHA `108c401a798cde55eac97c0a5b6d9f69cef69527c6901855769ffd069ff028b9`,
and feature preflight v13 SHA
`d176e6e67c50edb2474531fd05e93e953b75fbc860c4051d0ce3d46efcaee6ed`.
The exact CPU operation and feature provenance are recorded in
[`embeddinggemma-features.manifest.json`](embeddinggemma-features.manifest.json).
The pinned model repository labels its files Apache-2.0; Google’s Gemma Terms
also list EmbeddingGemma and incorporate the prohibited-use policy. See the
[pinned model page](https://huggingface.co/google/embeddinggemma-2/tree/914f7f89142e33e77833254d9c9b90c3cef7303b),
[Gemma Terms](https://ai.google.dev/gemma/terms), and
[prohibited-use policy](https://ai.google.dev/gemma/prohibited_use_policy).

The feature archive SHA256 is
`888028e174d81aed59a30b0dc8cc4a703a0cbc5153e55a1cd617488463266af8`; its
manifest SHA256 is
`6bad882398a74802a26ed0f9f9b141d5898e04e05b7d36985eea1ea2eed36788`. It
contains normalized 768-dimensional vectors for 2,157 entities, 84 predicates,
and 236 questions, using label text and question text only. Model load took
10.2 seconds, feature inference 66.7 seconds, and measured peak process RSS was
2,335,916,032 bytes. No RDF edges, references, or answer identifiers were
used as features.

The final frozen experiment is
[`experiment-manifest-final.json`](experiment-manifest-final.json), SHA256
`d8dbbd8375d23972b8b07283da43e30b2ab8383039382b27c9ee4f17c1cac659`. It binds
`baseline-score-v5`, the feature hashes above, fixed seeds 117/118/119, two
128-dimensional layers, AdamW at 0.001, at most 100 epochs with patience 10,
and 12 total fits (two architectures by two partitions by three seeds). The
acceptance target remains +0.10 absolute Recall@10 over the strongest matched
text method and positive paired Recall@10 improvement over QV2, with a positive
query-group bootstrap lower bound and no unacceptable direction, scope, exact
identifier, no-match, or resource regressions. With current test scores, the
strongest text method is EmbeddingGemma at 0.286 R@10; QV2 is 0.393.

The required fresh training preflight is
[`host-preflight-v14.json`](host-preflight-v14.json), captured on the Apple M1
Pro at 2026-10-29 15:24 UTC. It reports 21,855,436,800 bytes available, below
the registered 24 GiB threshold (25,769,803,776 bytes) by 3,914,366,976 bytes.
The feature gate passes; the training gate fails. This availability snapshot is
not an estimate of model RSS. No competing process was terminated and no
resource limit was changed. Do not start training until a fresh read-only
receipt passes the 24 GiB gate and a separate owner authorization binds that
receipt, this final manifest, and the feature manifest.

The matched model, benchmark, and export suite passed all 27 tests with the
pinned environment:

```sh
PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python -m unittest discover -s tools -p 'test_rgcn_compgcn*.py' -v
```

No GNN training or scored GNN evaluation has been run. After memory is
available and separate training approval is provided, the prepared command is:

```sh
python tools/rgcn_compgcn_run_v2.py train \
  --experiment-dir experiments/rgcn-compgcn-v2/wikidata-relations-v1 \
  --run-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/experiment-manifest-final.json \
  --features experiments/rgcn-compgcn-v2/wikidata-relations-v1/embeddinggemma-features.npz \
  --feature-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/embeddinggemma-features.manifest.json \
  --preflight experiments/rgcn-compgcn-v2/wikidata-relations-v1/host-preflight-passing.json \
  --owner-authorization /approved/full-training-authorization.json \
  --out experiments/rgcn-compgcn-v2/wikidata-relations-v1/training-run-v1
```

The authorization path above is a placeholder, not an approval file. Use the
actual owner-approved, single-use authorization after the exact final hashes
and a passing preflight are known. GNN outputs remain candidate scores, never
RDF evidence, and cannot trigger graph execution.
