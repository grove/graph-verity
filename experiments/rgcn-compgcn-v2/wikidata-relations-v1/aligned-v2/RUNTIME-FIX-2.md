# Aligned-v2 runtime correction 2

This version descends from `experiment-manifest-aligned-v2-runtime-fix-1.json`.
It preserves that manifest and its receipts while adding two explicit
authorization bindings required for a fresh attempt: the frozen question-file
hash and the exact unique feature-output path. The runner now rejects an
authorization if either differs, and rejects output paths outside the
repository workspace.

The output is fixed to
`experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v2/runtime-fix-2/directional-relation-features.npz`.
All graph, benchmark, question, reference, split, model, feature-operation,
training, and scoring inputs remain inherited unchanged from the original
aligned-v2 preregistration. The only runtime behavior change remains the
one-time PyTorch CPU initialization and reuse described in
`RUNTIME-FIX-1.md`; this version adds authorization/path validation only.

The model-free preflight validates the new manifest and empty output location,
then reaches the boundary immediately before `Encoder` construction. It does
not read an authorization record, construct the model, load weights, or run
inference. A new owner approval is required for this code and output binding;
the earlier feature authorization is not reused.
