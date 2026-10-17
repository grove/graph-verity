# Pinned EmbeddingGemma 2 retrieval comparison

Issue [#38](https://github.com/grove/graph-verity/issues/38) originally named
`google/embeddinggemma-300m`. The owner explicitly replaced it with
**`google/embeddinggemma-2`**, before inference, to use the Apache-2.0 checkpoint.
This is an explicit generation change, not a substitute for a measured result on
EmbeddingGemma 1. The [preregistration](../benchmarks/embeddinggemma/manifest.json)
and [upstream inventory](../benchmarks/embeddinggemma/upstream.json) bind commit
`914f7f89142e33e77833254d9c9b90c3cef7303b`, every configuration Git blob,
weights and both tokenizer files. No Ollama or community conversion is used.
The [retained measurements and adoption rationale](../reports/issue-38-embeddinggemma/README.md)
include raw ranks, manifests, failures, parity and CPU measurements.

The opt-in Python tooling compares the existing Rust BM25 baseline, embeddings
alone, and one fixed fusion baseline. It does not integrate embeddings into Find,
change the Ask workflow, or access the task-sealed holdout. Ordinary CI runs its
model-free tests without installing the inference requirements or downloading weights.

## Protocol frozen before inference

Use the unchanged #37 public retrieval manifest: 80 development and 80 separate
evaluation formulations, each 40 Norwegian/40 English, sharing intents and
AI-authored judgments. Score all 60 relevant cases per split, including failures
as zeros; report ambiguous/no-match behavior separately. These formulations are
correlated exploratory evidence, not independent human gold. Do not tune on
evaluation or silently remove a failed family.

The [official model card](https://huggingface.co/google/embeddinggemma-2) documents
text-only loading. Disable vision/audio encoders; load official BF16 safetensors
into CPU FP32. The direct Transformers path uses eager attention, projected
768-dimensional token states, attention-mask weighted mean pooling including
prompt/special tokens, then L2 normalization. There is no conversion or quantization.
Freeze package versions, distribution RECORD hashes, Torch build/git identity,
Python/platform, threads, binary/source hashes, model file SHA256s, exact downloaded
legal documents, corpora, authorized index exports, scopes and snapshot provenance.
The measured installation is separately pinned in
[embedding-requirements.txt](../tools/embedding-requirements.txt).

Quantization was investigated, then excluded from this fixed experiment.
Google describes architecture-specific INT4/INT8 QAT in its
[AI Edge deployment guide](https://developers.googleblog.com/google-ai-edge-with-embeddinggemma-2/).
The converter's [ONNX distribution](https://huggingface.co/onnx-community/embeddinggemma-2-ONNX)
also documents q8/q4 variants and precision-dependent parity. Neither establishes
parity for this Python CPU path or the repository's Qwen generation runtime.
Using them would require separately pinned conversion code/assets and fresh
reference checks. This run deliberately measures the official unquantized
checkpoint; it makes no quantized performance claim.

Use four Torch intra-op threads, one inter-op thread, batches of eight documents
and one query. Inputs are right-truncated to **256 tokens including prefixes and
special tokens**. This is a deliberately declared pilot cap; the native 8K context
is not evaluated. Query prefix: `task: search result | query: `. Document prefix:
`title: none | text: `. Document content is the original IRI followed by each
bounded observed text value in discovery order, separated by newlines. No Unicode
normalization, generated summaries, title inference or predicate-label mapping is added.

Before corpus inference, compare the official Sentence Transformers pipeline with
the direct runtime on eight [fixed inputs](../benchmarks/embeddinggemma/parity-inputs.json):
English, Norwegian, decomposed Unicode, identifiers, untrusted RDF-like text, empty
content, and query/document truncation. Retain both token-ID traces and vectors.
Require exact token IDs/untruncated lengths, 768 finite unit-vector values, maximum
absolute vector error <=1e-5 and cosine >=0.999999. A failure stops the experiment;
model-free synthetic parity vectors in tests are never measurement evidence.

Scope is enforced by the existing Rust `index-build` authorization boundary before
text is exported or embedded. Each export retains graph-qualified RDF IDs, complete
observed literal datatypes/languages/truncation flags, source manifests, graph
hashes and immutable snapshot identity. A role filter applies before similarity
and returned candidate counts. Authorized RDF text remains data; nothing executes
its SERVICE/HTML/instruction strings. The exporter cannot issue arbitrary SPARQL,
remote SERVICE or writes. Private graph/ID/text/source canaries and literal
provenance are exercised without a model.

Dense search uses cosine over normalized FP32 vectors, with IRI then graph ties,
returning up to 50 graph-qualified IDs. Fusion is equal-weight reciprocal rank
fusion, `1/(60+rank)`, over BM25 top 50 and dense top 50, with the same stable ties.
There is no exact-match override, learned weight, score cutoff or parameter search.

## Measurements and decision

Retain raw ranks, requests, failures, parity traces, vector indexes and hash
inventories. Recompute Recall@1/5/10/50, MRR@10, per-language/family and
language-by-family descriptive 95% intervals using #37's 2,000-resample seeded
query bootstrap. Also retain paired deltas against BM25. Failures remain in their
original denominators and prevent a passing recommendation.

Build vectors for the same real corpora and byte-frozen synthetic 10,000-resource
pilot from #37. Report embedding build time, vector disk size, checkpoint size,
BM25 build/index size, timing samples and aggregate process RSS. The lightweight
synthetic pilot cannot establish real-domain scale or quality.

BM25 warm samples come from its existing resident `find-batch` operation and
exclude JSON IO, as in #37. Dense warm latency includes request serialization,
tokenization, inference, ranking and result serialization with a resident model
and vector index. Fusion latency is a **conservative end-to-end upper bound**:
dense latency plus a fresh BM25 CLI import/index build/query/JSON round trip and
fusion/serialization. Its extra lexical startup/build work is included, not
subtracted. This avoids presenting batch-internal timing as end-to-end latency.
The first warm sample is retained; page caches are not evicted. Report 30 cold
BM25 samples and 200 warm samples per corpus; p99 uses nearest-rank percentiles.
Runtime model construction time is recorded separately, not called a cold-query
distribution. RSS conservatively sums controller and maximum child high-water
marks; the reference-parity load is included. The native macOS measurement uses
the host scheduler, with no isolated CPU affinity/quota.

The proposed engineering rule remains >=0.05 absolute Recall@10 **or** >=0.03
MRR@10 gain, neither metric regressing >0.02 in either language, warm end-to-end
p95 <=1s and aggregate peak RSS <=4GiB. Additionally, a qualifying gain's paired
descriptive interval must exclude zero. Inconclusive evidence retains BM25.
Passing only nominates a candidate for review; it never automatically changes
Find. These are future pilot proposals, not approved Phase 0 gates. Embeddings
provide relevance scores, not question understanding or truth verification.

## Reproduce

Use Python 3.14 on the measured macOS arm64 platform; another platform must freeze
its own runtime/build and rerun parity. Inference is entirely local and offline;
only explicit dependency/asset acquisition uses the network. Model-free report
verification uses Python 3.12+ (the CI reference interpreter); the bootstrap's
floating-point sums are not byte-identical on older Python versions.

```sh
python3.14 -m venv artifacts/embedding-runtime
artifacts/embedding-runtime/bin/pip install -r tools/embedding-requirements.txt
cargo build --release --locked --offline -p verity_cli
artifacts/embedding-runtime/bin/python tools/embedding_experiment.py verify
artifacts/embedding-runtime/bin/python tools/embedding_experiment.py download --out artifacts/embedding-assets
mkdir -p artifacts/embedding-legal
curl -fLsS https://www.apache.org/licenses/LICENSE-2.0.txt -o artifacts/embedding-legal/APACHE-2.0.txt
curl -fLsS https://ai.google.dev/gemma/terms -o artifacts/embedding-legal/gemma-terms.html
curl -fLsS https://ai.google.dev/gemma/prohibited_use_policy -o artifacts/embedding-legal/prohibited-use-policy.html
artifacts/embedding-runtime/bin/python tools/embedding_experiment.py prepare \
  --model-dir artifacts/embedding-assets --legal-dir artifacts/embedding-legal \
  --binary target/release/verity --out artifacts/embedding-freeze \
  --cpu-description 'record exact CPU, RAM, virtualization and scheduling limits'
artifacts/embedding-runtime/bin/python tools/embedding_experiment.py run \
  --freeze artifacts/embedding-freeze --out artifacts/embedding-run
artifacts/embedding-runtime/bin/python tools/embedding_experiment.py verify-report \
  --freeze artifacts/embedding-freeze --out artifacts/embedding-run
python3.12 -m unittest discover -s tools -p test_embedding_experiment.py -v
```

Every output directory/file is created exclusively. A failed attempt is retained;
fix its cause and create a new freeze/output directory. A changed runtime, model,
binary, source or corpus invalidates the freeze. Published report verification is
model-free; replaying inference additionally needs the hash-checked official assets.
