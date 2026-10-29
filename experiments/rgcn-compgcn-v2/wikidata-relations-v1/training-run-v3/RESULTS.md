# R-GCN vs CompGCN: authorized run v3

**Decision: STOP GNN retrieval adoption on this evidence.** Both models missed the frozen acceptance criteria and did not beat source-witnessed QV2. The results are exploratory because the primary test has 28 relevant, agent-authored questions.

## Run identity and execution

The owner-approved run completed all 12 sequential CPU fits: R-GCN and CompGCN, transductive and unseen-entity partitions, seeds 117–119. It used the unchanged two-layer, 128-dimensional protocol, AdamW at 0.001, early stopping (patience 10, at most 100 epochs), and the pinned Python 3.12.14 / PyTorch 2.11.0 / PyG 2.7.0 runtime.

| Input | SHA-256 |
|---|---|
| Final v3 run manifest | `7d1775aada1d1687eb8f36ef2b4b4f1f54ced3f0464338d100d6a3bd60e19c9f` |
| EmbeddingGemma feature manifest | `6bad882398a74802a26ed0f9f9b141d5898e04e05b7d36985eea1ea2eed36788` |
| Passing M1 Pro preflight v16 | `d78727b460b4a8d097d44672372badf2241a612d32897d9a18becee1d273ce9b` |
| Matched baseline summary v5 | `d781c38ec324e8f74f25a1478f99926d7553711223fb4d6ab2bcb2a166a205c2` |

The graph is `urn:graph-verity:wikidata:norway-org-v1` (2,157 entities, 5,756 directed edges, 84 predicates). The frozen primary test has 28 relevant questions (14 English, 14 Norwegian), plus four ambiguous and four no-match cases. Each positive reference is source-checked against the graph; references are agent-authored, not independent expert judgments.

The feature vectors, candidate identities, graph scope, questions, references, and split remained bound to the frozen manifest. Validation and test witness edges were excluded from transductive message passing. The unseen-entity split excludes 16 entity IRIs and their 206 incident edges from message passing.

## Primary transductive results

GNN values are arithmetic means over the three fixed seeds; each seed scores the same 28 relevant questions. Baselines use the same frozen questions and scope. Each method performs end-to-end candidate generation and ranking; this is not a shared-pool reranking experiment.

| Method | Relevant n | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 28 | 0.000 | 0.107 | 0.107 | 0.023 | 0.043 |
| EmbeddingGemma 2 | 28 | 0.000 | 0.179 | 0.286 | 0.068 | 0.119 |
| QV2 source-witnessed neighborhoods | 28 | 0.000 | 0.321 | **0.393** | 0.111 | 0.178 |
| R-GCN | 28 | 0.048 | 0.190 | 0.298 | 0.103 | 0.148 |
| CompGCN | 28 | 0.083 | 0.214 | 0.321 | 0.135 | 0.179 |

R-GCN Recall@10 by seed was 0.286, 0.286, 0.321; CompGCN was 0.286, 0.393, 0.286. The registered text target was at least 0.386 (EmbeddingGemma 0.286 + 0.100). Neither model's three-seed mean reached it. Neither model beat QV2's 0.393; CompGCN's best single seed only tied it.

| Test slice | n | EmbeddingGemma | QV2 | R-GCN | CompGCN |
|---|---:|---:|---:|---:|---:|
| English | 14 | 0.357 | 0.429 | 0.310 | 0.310 |
| Norwegian | 14 | 0.214 | 0.357 | 0.286 | 0.333 |
| Forward one-hop | 8 | 0.125 | 0.125 | 0.000 | 0.000 |
| Reverse one-hop | 8 | 0.250 | 0.250 | 0.042 | 0.042 |
| Predicate retrieval | 8 | 0.625 | 1.000 | 1.000 | 1.000 |
| Two-hop endpoint | 4 | 0.000 | 0.000 | 0.000 | 0.167 |

Slice values are Recall@10, with GNN values averaged over seeds. CompGCN's two-hop hits occurred in one seed only (0.500 in seed 118; zero in seeds 117 and 119). The perfect two-hop source-path metric in the run receipt is a structured traversal diagnostic supplied from the captured RDF paths; it is not a GNN path prediction and is excluded from this table.

Paired query-group bootstrap intervals use 2,000 resamples of the six source-edge/path groups (seed 117). Overall query-macro Recall@10 differences were: R-GCN minus EmbeddingGemma **+1.2 pp**, CompGCN minus EmbeddingGemma **+3.6 pp**, R-GCN minus QV2 **−9.5 pp**, CompGCN minus QV2 **−7.1 pp**, and CompGCN minus R-GCN **+2.4 pp**. The corresponding group-bootstrap 95% intervals were:

| Paired difference | 95% interval |
|---|---:|
| R-GCN − EmbeddingGemma | −13.9 to +16.7 pp |
| CompGCN − EmbeddingGemma | −11.1 to +23.1 pp |
| R-GCN − QV2 | −22.2 to 0.0 pp |
| CompGCN − QV2 | −24.1 to +16.7 pp |
| CompGCN − R-GCN | −1.9 to +16.7 pp |

Intervals resample six query groups and are necessarily coarse; none establishes the registered positive improvement over QV2. CompGCN's modest mean advantage over R-GCN is not stable across seeds or groups.

Both GNNs returned top-10 suggestions for all four no-match questions (4/4 false suggestions); this matches the baseline behavior. On the benchmark's captured source-witness neighborhood measure, top-10 coverage averaged 2.3% for R-GCN and 2.8% for CompGCN, versus 4.4% for EmbeddingGemma and 5.3% for QV2. Model outputs retain graph-qualified original IRIs and are hypotheses, not RDF evidence.

## Unseen-entity generalization

The frozen unseen partition lists 42 relevant test questions over 16 held-out entity IRIs. Reaggregating all 42 saved raw-rank rows gives these Recall@10 results:

| Method | Relevant n | Recall@10 |
|---|---:|---:|
| BM25 | 42 | 0.190 |
| EmbeddingGemma 2 | 42 | 0.214 |
| QV2 source-witnessed neighborhoods | 42 | 0.190 |
| R-GCN | 42 | 0.000 |
| CompGCN | 42 | 0.016 |

R-GCN scored zero on all 42 questions in all three seeds. CompGCN retrieved one target in one seed (seed 118), and zero in the other two. Neither model retrieved a two-hop endpoint in this partition.

**Receipt accounting note:** the runner's `test_summary` filters rows by each question's original benchmark split label. In the frozen unseen test ID list, 32 questions carry the original `train` label, four `validation`, and six `test`; therefore the receipt's unseen summary reports only six. The original receipt is preserved unchanged. The 42-question values above are recomputed from every raw-rank row whose ID is in the frozen unseen test list, and the derivation inputs and hashes are in [`posthoc-summary-v1.json`](posthoc-summary-v1.json).

## Cost, evidence, and conclusion

The fresh admission receipt recorded 21,881,257,984 bytes available, 89% memory-pressure free, and zero swap. All 12 fits ran sequentially on CPU in 55.15 seconds total. The five-second resource monitor sampled 11 times, peaked at **977,371,136 bytes** process-tree RSS, recorded no early-warning sample, no swap growth, and no stop condition. This monitor is observational; it is not OS-level memory isolation.

R-GCN checkpoints are 1,844,981 bytes each; CompGCN checkpoints are 1,581,813 bytes. Median per-run graph encoding was 63.0 ms for R-GCN and 3.4 ms for CompGCN. Median query scoring was 1.30 ms/case for R-GCN and 1.27 ms/case for CompGCN, excluding graph encoding.

**Conclusion: STOP for product adoption.** R-GCN and CompGCN do not meet the pre-registered text or QV2 targets. Both lose on forward and reverse entity retrieval; CompGCN shows a small, seed-sensitive two-hop signal and both retrieve predicates well, but QV2 matches the predicate Recall@10 without learned-model cost. No predicted relationship is promoted to a verified triple or connected to graph execution.

The small, agent-authored test set and end-to-end candidate differences limit the strength of the conclusion. The baseline and GNN methods generate their own candidate lists, so this run does not isolate reranking quality on a fixed shared pool. No model or application code changed for this report. The historical receipt, predictions, raw ranks, losses, checkpoints, and resource logs are preserved beside this report.
