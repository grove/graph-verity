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

The isolated training environment is pinned to Python 3.12.14, PyTorch 2.11.0,
and PyTorch Geometric 2.7.0. R-GCN uses PyG `RGCNConv` with four relation
bases over original directed subject-to-object edges. CompGCN uses subtraction
composition `phi(e,r)=e-r` and jointly updates relation states at each layer.
Both use the same 768-dimensional EmbeddingGemma features, two 128-dimensional
layers, ten link negatives, ten query negatives, and the same link/query loss.
No inferred reverse RDF edges are added. Training and validation use the frozen
transductive and unseen-entity partitions; the test set remains untouched.

The acceptance criteria are unchanged: +0.10 absolute Recall@10 above the
strongest matched text baseline and positive paired Recall@10 change over QV2,
with the query-group bootstrap 95% lower bound above zero. Report English and
Norwegian, forward/reverse, two-hop path, no-match, exact IRI, scope and
source-witness results. The structured adjacency oracle is an upper bound, not
a natural-language comparator. References remain agent-authored development
evidence; only 28 relevant test questions are available.

### Versioned resource revision

The prior frozen manifest remains intact at
[`experiment-manifest-final.json`](experiment-manifest-final.json), SHA256
`d8dbbd8375d23972b8b07283da43e30b2ab8383039382b27c9ee4f17c1cac659`. Following
the owner's explicit resource-budget decision, the new manifest is
[`experiment-manifest-final-v2.json`](experiment-manifest-final-v2.json), SHA256
`211fe014c303d757529fbc420b16efa40e67c652407004f7a961879317016add`. It binds
the unchanged features and baseline to passing preflight v15. The revision
changes only the resource protocol; data, models, splits, seeds, hyperparameters
and evaluation criteria are unchanged. That v2 manifest was bound to preflight v15;
its approval window expired before launch, and no training was started. The
current re-admission uses the same protocol with a fresh snapshot below.

Admission requires 18 GiB available RAM (`19,327,352,832` bytes). The run has
an 18 GiB maximum sampled process-tree RSS and a 12 GiB early-warning mark.
Samples are taken every five seconds. The runner stops at an 18 GiB process-tree
RSS sample, at 5% or lower system-wide memory-free percentage, below 4 GiB
available headroom, after 2 GiB of additional `vm_stat` swapouts, or if resource
sampling fails. It also retains the six-hour total limit. These are observational
safeguards; they do not provide OS-level memory isolation. The 12 fits execute
sequentially with CPU-only PyTorch, four intra-op threads and one inter-op
thread.

Fresh read-only preflight
[`host-preflight-v15.json`](host-preflight-v15.json) passed on the Apple M1 Pro
at 2026-10-29 15:46 UTC, SHA256
`3d62ef962fad14f41e6683f97fc06ab882255726bca56a56aa69dd2fe76bdb37`. It
recorded 22,961,192,960 bytes available, 89%
system-wide memory free, zero swap in use, and zero baseline `vm_stat` swap-in
and swap-out pages. The 18 GiB admission threshold was exceeded by
3,633,840,128 bytes. It recorded the 20 largest visible competing processes;
520 processes were visible and 331 were inaccessible to the sampler. The
pinned Python/PyTorch/PyG environment, Wikidata export, benchmark, baseline,
feature archive and feature manifest hashes all verified. The receipt records
12 sequential fits. No processes or resource limits were changed.

Fresh preflight
[`host-preflight-v16.json`](host-preflight-v16.json) passed at 2026-10-29
16:32:34 UTC, SHA256
`d78727b460b4a8d097d44672372badf2241a612d32897d9a18becee1d273ce9b`. It reports
21,881,257,984 bytes available, 89% memory free, zero swap in use, and zero
`vm_stat` swap counters. 519 processes were visible and 331 were inaccessible;
the 20 largest visible competitors are retained. The frozen inputs and pinned
runtime verified again. The available-memory margin over admission is
2,553,905,152 bytes.

The current manifest is
[`experiment-manifest-final-v3.json`](experiment-manifest-final-v3.json), SHA256
`7d1775aada1d1687eb8f36ef2b4b4f1f54ced3f0464338d100d6a3bd60e19c9f`. It binds
preflight v16 and the same feature hashes. The v2 manifest and v15 receipt stay
preserved as historical evidence; the previous authorization was not reused.

The final feature manifest SHA256 is
`6bad882398a74802a26ed0f9f9b141d5898e04e05b7d36985eea1ea2eed36788`; the
feature archive SHA256 is
`888028e174d81aed59a30b0dc8cc4a703a0cbc5153e55a1cd617488463266af8`. The exact
preflight v16 SHA256 above is bound in the current run manifest.

The complete model, evaluation, export and revised-resource suite passed all
29 tests in the pinned environment:

```sh
PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python -m unittest discover -s tools -p 'test_rgcn_compgcn*.py' -v
```

### Pre-launch authorization record (superseded by run v3 completion)

This section preserves the pre-launch state. The 18 GiB budget change did not
itself authorize training. The owner's earlier approval named v15, which was
older than the runner's 30-minute freshness limit when launch was attempted;
it was not used. At that point no GNN fits had run. A later, separate owner
approval was bound to the v3 manifest, feature-manifest, and fresh v16
preflight hashes below. The old v15 approval and EmbeddingGemma inference
authorization were not reused.

The run command for the refreshed authorization is:

```sh
/private/tmp/graph-verity-rgcn-env/bin/python tools/rgcn_compgcn_run_v2.py train \
  --experiment-dir experiments/rgcn-compgcn-v2/wikidata-relations-v1 \
  --run-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/experiment-manifest-final-v3.json \
  --features experiments/rgcn-compgcn-v2/wikidata-relations-v1/embeddinggemma-features.npz \
  --feature-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/embeddinggemma-features.manifest.json \
  --preflight experiments/rgcn-compgcn-v2/wikidata-relations-v1/host-preflight-v16.json \
  --owner-authorization /approved/full-training-authorization-v3.json \
  --out experiments/rgcn-compgcn-v2/wikidata-relations-v1/training-run-v3
```

The path in this historical command was a placeholder. The completed run used
the actual one-time authorization record outside the repository. The runner
validated its bound hashes and resource gate. Predictions remain hypotheses,
never RDF evidence or executable graph operations.

### Completed owner-authorized run v3

The exact 12-fit CPU comparison completed on 2026-10-29. All checkpoints,
training histories, predictions, raw ranks, resource logs, and the run receipt
are preserved in [`training-run-v3`](training-run-v3/). The measured results,
acceptance decision, and corrected 42-question unseen-entity aggregation are
in [`training-run-v3/RESULTS.md`](training-run-v3/RESULTS.md) and
[`training-run-v3/posthoc-summary-v1.json`](training-run-v3/posthoc-summary-v1.json).
