# Aligned-v2 runtime-fix-2 results

## Decision

**STOP for product adoption of these GNN retrieval configurations.** The experiment completed all 48 registered fits, but no end-to-end GNN reached the pre-registered Recall@10 target or beat deterministic QV2 on the 28-question primary test. Shared-pool reranking shows a limited MRR/nDCG signal; it does not improve Recall@10 and is uncertain across only six query groups. Keep these results separate from the historical v3 STOP report.

## Run and evidence

- Frozen final manifest SHA-256: `03ac58845799c9fdde76a7717605e60a789dbf608a0b0725cc9123d718ff62e4`.
- Directional feature archive SHA-256: `a6eae9c8ee4d316af07556fc6faba17d0f9e8be1ae9a20657b383d2ced2507b6`.
- Feature manifest SHA-256: `caa194e8d8f89ae17ca0a488b33391169f0e1d4d140097aeded7f5f7c34749b3`.
- Passing training preflight SHA-256: `0262a0689bb786a9835aeaf30d5e19c4c4f9d2f3b065463ed7cb2383ac73e6ab`.
- One-time training authorization SHA-256: `586edba73aa71489ab5c13e5243c8e3457b2a4283f6e883c11e60cf919533a53` (outside the repository, mode `0600`).
- [Run receipt](training-run-runtime-fix-2/run-receipt.json) SHA-256: `f7809c17ebb6f39c467e2849d4ef4bc2cc7c860ac8ce36c0b3c24fc55f7c3332`.
- [Resource monitor summary](training-run-runtime-fix-2/resource-monitor-summary.json) SHA-256: `b9df95618fb708dbb7c8784882d7c9fa307e8c947ea76d6b21b34c43b4a99573`.
- All 48 fits completed: variants B–E × R-GCN/CompGCN × transductive/unseen-entity × seeds 117–119. The 240 checkpoint, prediction and rank-file hashes in the receipt were verified.
- CPU only, PyTorch 2.11.0, PyG 2.7.0, four intra-op and one inter-op thread. Total run time was 378.52 seconds. Peak sampled process-tree RSS was 1,657,651,200 bytes; minimum available memory during the run was 14,739,062,784 bytes (13.73 GiB), above the registered 4 GiB runtime-headroom floor. Across 75 resource samples there was no warning or stop and no swap growth. Mean per-fit epoch time was 12.82 seconds for R-GCN and 1.30 seconds for CompGCN. Checkpoints ranged from 1.58 to 2.24 MB. Inference latency was not separately timed.
- The split checks excluded validation/test witness edges and their inverse navigation rows from message passing. The fit-time source-edge and forward/reverse-pair checks completed for every fit. Unseen-entity runs excluded the registered unseen nodes and incident edges.

The benchmark references are agent-authored and source-checked, not expert gold. Generated bilingual predicate descriptions remain unreviewed text features, not RDF facts. Every prediction remains a hypothesis with original graph and IRI identifiers preserved.

## Primary end-to-end test

The transductive test has 28 relevant questions (14 English, 14 Norwegian), plus four no-match and four ambiguous questions. GNN values are the mean ± sample standard deviation across three seeds; each seed scores the same 28 relevant questions. Baselines are deterministic on this split.

| Method/configuration | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.000 | 0.107 | 0.107 | 0.023 | 0.043 |
| EmbeddingGemma 2 | 0.000 | 0.179 | 0.286 | 0.068 | 0.119 |
| QV2 one-hop neighborhoods | 0.000 | 0.321 | 0.393 | 0.111 | 0.178 |
| B — R-GCN | 0.036 ± 0.036 | 0.214 ± 0.036 | 0.369 ± 0.055 | 0.115 ± 0.036 | 0.174 ± 0.036 |
| B — CompGCN | 0.048 ± 0.041 | 0.202 ± 0.021 | 0.310 ± 0.041 | 0.102 ± 0.033 | 0.150 ± 0.033 |
| C — R-GCN | 0.024 ± 0.041 | 0.143 ± 0.036 | 0.286 ± 0.094 | 0.077 ± 0.047 | 0.125 ± 0.054 |
| C — CompGCN | 0.000 ± 0.000 | 0.143 ± 0.071 | 0.321 ± 0.062 | 0.064 ± 0.006 | 0.122 ± 0.016 |
| D — R-GCN | 0.000 ± 0.000 | 0.131 ± 0.074 | 0.250 ± 0.107 | 0.065 ± 0.023 | 0.108 ± 0.042 |
| D — CompGCN | 0.024 ± 0.041 | 0.143 ± 0.071 | 0.286 ± 0.124 | 0.075 ± 0.035 | 0.123 ± 0.053 |
| E — R-GCN | 0.000 ± 0.000 | 0.083 ± 0.055 | 0.167 ± 0.090 | 0.039 ± 0.029 | 0.069 ± 0.043 |
| E — CompGCN | 0.036 ± 0.036 | 0.155 ± 0.041 | 0.214 ± 0.071 | 0.082 ± 0.025 | 0.113 ± 0.034 |

Best end-to-end Recall@10 was B-RGCN at 0.369: +0.083 over EmbeddingGemma (below the +0.10 target) and −0.024 versus QV2. Best CompGCN was C at 0.321: +0.036 versus EmbeddingGemma and −0.071 versus QV2. The historical target is not met.

For context, historical v3 averaged 0.298 R-GCN and 0.321 CompGCN Recall@10. B-RGCN rose by 0.071, while B-CompGCN fell by 0.012. B-RGCN's source-group-weighted paired QV2 delta averaged +0.019 across seeds, but every seed's 95% interval included zero; the ordinary 28-question Recall@10 point difference is negative. The test has only six source/query groups, so neither point estimate is stable evidence of a lift.

## Direction, language, paths and evidence coverage

| Slice (denominator) | EmbeddingGemma R@10 | QV2 R@10 | B-RGCN R@10 | Best CompGCN R@10 |
|---|---:|---:|---:|---:|
| English (14) | 0.357 | 0.429 | 0.405 ± 0.041 | 0.333 ± 0.082 (C) |
| Norwegian (14) | 0.214 | 0.357 | 0.333 ± 0.082 | 0.310 ± 0.041 (C) |
| Forward one-hop (8) | 0.125 | 0.125 | 0.000 ± 0.000 | 0.125 ± 0.217 (C) |
| Reverse one-hop (8) | 0.250 | 0.250 | 0.208 ± 0.260 | 0.167 ± 0.289 (D) |
| Predicate retrieval (8) | 0.625 | 1.000 | 1.000 ± 0.000 | 1.000 ± 0.000 (B/C) |
| Two-hop answer entity (4) | 0.000 | 0.000 | 0.167 ± 0.144 | 0.000 ± 0.000 |

B-RGCN may improve reverse answer retrieval over v3's 0.042, but this is only eight questions and varies sharply by seed. Joint predicate-and-direction top-1 accuracy is 0.131 ± 0.055 for B-RGCN and 0.143 ± 0.124 for B-CompGCN; top-1 anchor accuracy is zero. Conditional direction accuracy is 0.714 for B–D, then falls to 0.601 for E-RGCN and 0.619 for E-CompGCN. The v3 run did not record the joint direction metric, so a direct direction-accuracy change cannot be established.

Gold-free source-witnessed path retrieval was 0/4 at Recall@10 for every aligned variant. The separate oracle-assisted path diagnostic was 4/4; it supplies gold structural hints and is not a question-driven result. The older v3 4/4 path figure used captured traversal candidates, so it is not treated as a gold-free comparison.

The QV2 top-50 shared candidate pool contained the relevant target for only 11/28 questions (mean candidate-pool recall 0.393); 17/28 targets were absent and could not be recovered by reranking. B-RGCN reranking kept Recall@10 at 0.393, equal to QV2, while mean MRR@10/nDCG@10 rose to 0.198 ± 0.026 / 0.246 ± 0.019 versus QV2's 0.111/0.178. The group-weighted paired changes averaged +0.068/+0.053 across seeds, but most per-seed intervals included zero. This is a small reranking signal, not a candidate-generation or Recall@10 win.

Every GNN variant suggested candidates for all four no-match questions (4/4), as did each lexical/neighborhood baseline. Top-10 source-witness coverage (36 test cases) was 0.0287 for B-RGCN and 0.0259 for C-CompGCN, below QV2's 0.0528 and EmbeddingGemma's 0.0444. These rankings do not establish RDF facts.

## Unseen-entity generalization

The unseen test has 42 relevant questions. Matching deterministic baselines score BM25 0.190, EmbeddingGemma 0.214, and QV2 0.190 Recall@10.

| Variant | R-GCN Recall@10 | CompGCN Recall@10 |
|---|---:|---:|
| B | 0.000 ± 0.000 | 0.071 ± 0.124 |
| C | 0.008 ± 0.014 | 0.159 ± 0.027 |
| D | 0.032 ± 0.055 | 0.000 ± 0.000 |
| E | 0.056 ± 0.050 | 0.000 ± 0.000 |

The best unseen result, C-CompGCN, remains below QV2 and EmbeddingGemma; its MRR@10/nDCG@10 are 0.041 ± 0.019 / 0.068 ± 0.013. R-GCN's best unseen Recall@10 is 0.056. This confirms weak generalization for these configurations.

## Ablation findings and conclusion

| Variant | Change | R-GCN R@10 | CompGCN R@10 |
|---|---|---:|---:|
| A | Historical v3 baseline | 0.298 | 0.321 |
| B | Separate inverse navigation relations | 0.369 | 0.310 |
| C | B + bilingual relationship descriptions | 0.286 | 0.321 |
| D | C + relation-balanced sampling and direction-aware negatives | 0.250 | 0.286 |
| E | D + question-to-graph alignment | 0.167 | 0.214 |

Inverse navigation edges coincided with a reverse-retrieval gain for R-GCN, but not CompGCN, and did not get R-GCN past QV2. Bilingual descriptions helped CompGCN by only 0.011 over B and hurt R-GCN. Relation-balanced training and direction-aware negatives reduced Recall@10 for both. Explicit question alignment reduced it further for both. No tested GNN configuration met the promotion criterion or outperformed QV2 end-to-end.

**Recommendation: STOP GNN product integration for these configurations.** The fixed-pool reranking signal could justify a separately preregistered, larger evaluation if Graph Verity later needs reranking, but this 28-question, agent-authored benchmark is too small to support adoption. Do not promote the small positive slices as independent semantic accuracy.
