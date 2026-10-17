# Issue #38: pinned EmbeddingGemma 2 vs BM25

**Decision: reject embeddings alone as a BM25 replacement; defer automatic adoption of fusion and nominate the fixed fusion baseline for review.** Fusion passes the preregistered engineering pilot rule, but exploratory AI judgments and its 10/10 no-match candidate returns do not establish product readiness. Find remains BM25. No human-reviewed quality, production rollout, Phase 0 approval, question understanding or truth verification is claimed.

The owner explicitly replaced the issue’s original `google/embeddinggemma-300m` candidate with Apache-2.0 **`google/embeddinggemma-2` before inference**. Official upstream commit: `914f7f89142e33e77833254d9c9b90c3cef7303b`. No community conversion or Ollama model was substituted. See the [protocol and reproduction commands](../../docs/embedding-experiment.md), [preregistration](../../benchmarks/embeddinggemma/manifest.json), [exact freeze](freeze.json) and [decision checks](decision.json).

## Retrieval evidence

The unchanged #37 public split contains 80 development + 80 separate evaluation formulations, each 40 Norwegian/40 English. Each split scores 60 relevant cases (30 per language), plus ten ambiguous and ten no-match cases reported separately. They share target intents and AI-authored judgments; the evaluation is not an independent holdout. No parameters or judgments were tuned and no sealed Ask data was accessed. All 160 fresh native BM25 rankings and metrics exactly match #37’s retained baseline.

Each entry is mean [descriptive 95% interval], using 2,000 query-level percentile bootstrap resamples, seed 37. Correlated formulations, tiny families and degenerate intervals limit inference. The [full JSON](summary.json) retains Recall@1/5/10/50, MRR@10, all language/family cross-tabs, paired deltas and separate behavior counts for both splits.

| Split / method | Recall@1 | Recall@5 | Recall@10 | Recall@50 | MRR@10 |
| --- | --- | --- | --- | --- | --- |
| development / bm25 | 0.744 [0.644, 0.839] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] |
| development / embedding | 0.594 [0.478, 0.706] | 0.833 [0.733, 0.933] | 0.867 [0.783, 0.950] | 1.000 [1.000, 1.000] | 0.736 [0.636, 0.837] |
| development / fusion | 0.628 [0.514, 0.739] | 0.867 [0.783, 0.950] | 0.983 [0.950, 1.000] | 1.000 [1.000, 1.000] | 0.778 [0.684, 0.864] |
| evaluation / bm25 | 0.744 [0.644, 0.839] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] | 0.833 [0.733, 0.917] |
| evaluation / embedding | 0.644 [0.533, 0.750] | 0.883 [0.800, 0.967] | 0.933 [0.867, 0.983] | 1.000 [1.000, 1.000] | 0.796 [0.706, 0.879] |
| evaluation / fusion | 0.761 [0.661, 0.856] | 0.950 [0.883, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.890 [0.818, 0.952] |

Evaluation language and family detail:

| Group | n | BM25 R@10 / MRR@10 | Embedding R@10 / MRR@10 | Fusion R@10 / MRR@10 |
| --- | ---: | --- | --- | --- |
| language/no | 30 | 0.833 [0.700, 0.933] / 0.833 [0.700, 0.933] | 0.967 [0.900, 1.000] / 0.805 [0.677, 0.913] | 1.000 [1.000, 1.000] / 0.877 [0.766, 0.967] |
| language/en | 30 | 0.833 [0.700, 0.933] / 0.833 [0.700, 0.933] | 0.900 [0.767, 1.000] / 0.786 [0.642, 0.906] | 1.000 [1.000, 1.000] / 0.903 [0.803, 0.975] |
| family/identifier | 10 | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 0.600 [0.300, 0.900] / 0.433 [0.183, 0.700] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] |
| family/entity | 10 | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] |
| family/alias | 10 | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] |
| family/predicate | 10 | 0.000 [0.000, 0.000] / 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] / 0.340 [0.215, 0.520] | 1.000 [1.000, 1.000] / 0.340 [0.215, 0.520] |
| family/description | 10 | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] |
| family/multi_relevant | 10 | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] / 1.000 [1.000, 1.000] |

Evaluation paired gains against BM25:

| Method | Recall@10 gain | MRR@10 gain |
| --- | --- | --- |
| embedding | 0.100 [-0.017, 0.217] | -0.038 [-0.121, 0.043] |
| fusion | 0.167 [0.083, 0.267] | 0.057 [0.021, 0.104] |

Fusion’s evaluation Recall@10 gain is **+0.167 [0.083, 0.267]** and MRR@10 gain **+0.057 [0.021, 0.104]**. Each language improves both point estimates. Both qualifying gains exclude zero in their descriptive paired intervals, satisfying the frozen uncertainty rule. Development has lower MRR (0.778 vs BM25 0.833); its distinct formulations matter and are not hidden.

Embeddings alone improves Recall@10 but loses identifier quality: identifier Recall@10 is 0.600 and MRR@10 0.433 vs BM25 1.000/1.000. Overall MRR decreases by 0.038, including Norwegian -0.028 and English -0.047, exceeding the 0.02 language regression allowance. Its Recall@10 paired interval includes zero. It is rejected as a replacement.

The predicate family moves from BM25 0.000 Recall@10 to 1.000 for dense/fusion, but MRR is only 0.340. This is retrieval of original graph-qualified directClaim IRIs using the existing IRI/text representation; no labels were silently copied from property entities and no predicate vocabulary mapping was added.

**Behavior limits:** all three methods return both relevant IDs at 50 for all ten ambiguous cases in both splits. Dense/fusion provide no ambiguity flag. Dense/fusion return candidates for **10/10 no-match cases in both splits**, versus BM25 0/10; no abstention cutoff was tuned or invented. There are zero query or timing failures in the successful run. Relevance denominators are unchanged. Returning candidates is not evidence that a concept exists, and BM25 returning none is not evidence of absence.

## Native CPU measurements

Apple M1 Pro (10 cores, 32 GB), native macOS 26.6.2 arm64, Python 3.14.8, Torch 2.14.1 (Accelerate/OpenMP release build), Transformers 5.20.1, Sentence Transformers 6.1.0. Four Torch intra-op threads, one inter-op thread; host scheduler, no isolated CPU quota/affinity. Vision/audio encoders disabled; 271,002,624 loaded parameters; official BF16 weights cast to FP32, unquantized, eager attention, 768-dimensional normalized vectors. Pilot inputs are capped at 256 tokens; document batch size eight, query batch size one.

Reference/runtime parity passes all eight fixed cases: exact token IDs/truncation traces, worst maximum absolute vector error **5.96e-8**, cosine at least **0.9999999999999996**. The long-input tokenizer warning comes from deliberately counting untruncated tokens; actual inference is capped at 256.

| Corpus | Graph-qualified resources | Dense build seconds | Vector index bytes on disk | BM25 build ms / index bytes | Dense warm p50 / p95 / p99 ms | Fusion upper-bound p50 / p95 / p99 ms |
| --- | ---: | ---: | ---: | --- | --- | --- |
| wikidata | 40 | 3.068 | 124,520 | 2.115 / 141,290 | 70.2 / 167.3 / 395.1 | 94.4 / 229.1 / 485.7 |
| cities | 430 | 14.562 | 1,322,586 | 7.513 / 491,885 | 66.2 / 85.4 / 101.9 | 96.4 / 121.8 / 139.8 |
| descriptions | 9 | 0.444 | 29,316 | 0.539 / 19,610 | 67.3 / 150.2 / 296.6 | 87.1 / 188.9 / 351.8 |
| scale | 10000 | 295.220 | 30,721,619 | 168.351 / 11,980,742 | 83.9 / 154.5 / 260.4 | 332.5 / 556.6 / 813.1 |

All 200 warm samples per corpus are retained, including the first. Fusion’s **10,000-resource p95 upper bound is 556.6ms**, below the proposed 1s budget. It includes resident dense inference/ranking/JSON plus a fresh BM25 process with RDF import, index build, query and JSON IO, then fusion/serialization. It is deliberately a conservative upper bound, not a claimed persistent-server measurement. Dense timing includes query serialization, tokenization, inference, similarity search and hit serialization; it does not implement snippets, HTTP or product UI. BM25’s resident batch-internal timings exclude JSON IO; cold BM25 retains 30 complete CLI samples per corpus. All raw samples and exact definitions are retained.

Aggregate process RSS upper bound is **2,832,007,168 bytes (2.64 GiB)**: controller/reference/runtime high-water 2,635,202,560 plus maximum sequential child high-water 196,804,608. This includes reference loading, index construction and retained results. It is a conservative sum, not an imposed 4GiB cgroup limit. The model construction observation is 1.550s, excluding imports; no cold-model query distribution is claimed. Official checkpoint/config/tokenizer disk footprint is 1,525,808,822 bytes; the 10,000-resource vector index is 30,721,619 bytes. Vector build timing excludes serialization. The synthetic pilot is deliberately lightweight; its timings do not validate large real-domain descriptions or deployment hardware.

## Artifacts, failures and verification

[`evidence.tar.gz`](evidence.tar.gz), bound by [`evidence.sha256`](evidence.sha256), contains `freeze/`, `run/`, exact frozen source files, original upstream small configuration/model-card files, two failed pre-inference attempts, operator logs, all raw ranks/timings, vector indexes, unchanged corpus/scope exports, legal documents and their inventories. Model weights and inference environment are not checked in. `inventory.json` hashes every retained file; `run/artifacts.json` binds every successful-run output. The top-level JSON files are readable copies of the archived originals.

The first two attempts failed before reference inference because the official multimodal processor required Pillow and then Torchvision even for text-only use. Both logs, freezes and failure records are retained. Those dependencies were installed/pinned before the successful third freeze; the successful run’s failure log is empty. No relevance run preceded parity, no trial’s scores were used to tune the method, and no asset or denominator substitution hid these failures.

To verify the retained result without a model, extract into a fresh ignored directory and use Python 3.12+:

```sh
mkdir -p artifacts/embedding-retained
python3 -c "import hashlib,pathlib; p=pathlib.Path('reports/issue-38-embeddinggemma/evidence.tar.gz'); assert hashlib.sha256(p.read_bytes()).hexdigest() == p.with_name('evidence.sha256').read_text().split()[0]"
python3.12 -m tarfile -e reports/issue-38-embeddinggemma/evidence.tar.gz artifacts/embedding-retained
python3.12 tools/embedding_experiment.py verify-report \
  --freeze artifacts/embedding-retained/freeze --out artifacts/embedding-retained/run
```

Normal CI recomputes the retained result and rejects altered denominators even if raw-rank hashes are updated. It also tests upstream asset identity, graph-qualified fusion/ties, role filtering before similarity, malformed/nonfinite parity vectors, Unicode/truncation traces, private graph/text/ID/source canaries, authorized export failures and original literal/snapshot provenance. The [full reproduction protocol](../../docs/embedding-experiment.md#reproduce) creates a new hardware-specific freeze and result.

**Adoption rationale:** the fixed fusion method deserves review in the Find-first continuation, because it recovers the predicate family while retaining exact identifiers. It is not enabled here. Keep BM25 as the current implementation and require human relevance review plus an explicit no-match/ambiguity product policy before integration. Quantized runtimes, native 8K inputs, real-domain 10,000-resource scale, human quality and serving behavior remain unmeasured.
