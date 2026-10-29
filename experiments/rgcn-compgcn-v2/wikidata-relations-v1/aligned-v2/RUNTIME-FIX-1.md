# Aligned-v2 runtime correction 1

This version follows the frozen aligned-v2 preregistration and the genuine
`feature-attempt-01-failure.json` record. It changes runtime initialization
only; the dataset, benchmark, questions, references, splits, feature text,
EmbeddingGemma revision, operation limits, model architecture, training plan,
and scoring semantics are unchanged.

The previous attempt reached `embedding_runtime_identity()`, which called
`embedding_experiment.cpu_runtime()`, then called that initializer again in
feature generation. PyTorch rejects a second inter-op thread setting. The
runtime helper now caches the process configuration and identity after the
first successful initialization, returns the cached result on repeat calls,
and fails explicitly if a later request or observed thread state conflicts.
Feature generation reuses this initialized runtime and checks that it remains
4 intra-op / 1 inter-op threads instead of resetting thread counts.

`tools/rgcn_compgcn_aligned_run_v2.py` is the versioned entry point. Its
`model-free-preflight` command validates the versioned manifest, fresh resource
receipt, model assets and runtime, exercises the same initialized-runtime path
as feature generation, and stops before constructing `Encoder`. It reads and
hashes local model assets but does not load weights, consume authorization, or
run inference.

The original
`experiment-manifest-aligned-v2.json` remains unchanged and continues to bind
the old runner identities. This version is stored in
`experiment-manifest-aligned-v2-runtime-fix-1.json`, names the original
manifest as its parent, and binds the corrected code hashes and this document.
The first failed attempt and all v3 results remain unchanged. The new version
requires a new feature-inference authorization because the code identity is
different. No GNN training authorization is included.
