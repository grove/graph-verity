# Issue #5 — project-owner sign-off and review boundary

**Recorded:** 16 October 2026.

The project owner explicitly stated **“I approve it. Do the rest.”** in the Graph Verity conversation following completion of the AI semantic audit in [PR #16](https://github.com/grove/graph-verity/pull/16). This is an authentic **owner-level authorization to proceed with the audit's corrected material and the remaining engineering work**. It is not automatically an attestation that a credentialed Norwegian/RDF domain expert independently adjudicated every question, nor a line-by-line personal review of all 130 records.

The reviewed material is identified by `benchmarks/ai-semantic-audit.json` and the pinned Wikidata snapshot. The approval scope does **not** include future, independently authored holdout or Schema.org transfer cases created after the sign-off. Record separate reviewer decisions for those artifacts.

For methodological integrity, `benchmarks/reviews.json` remains an independent, case-hash-bound human-review ledger. A project-owner approval of an AI assessment may be attached as provenance, but **must not** be represented as verified independent expert approval by fabricating 130 reviewer records or claiming a held-out model evaluation has run. The human-review and independent sealed holdout gates remain separate.

A newly authored private holdout must be stored outside the public source repository; a public checksum/runner does not expose its questions or answer key. Run the final model evaluation only after the gold has been independently signed off and the model/prompt/threshold configurations are frozen in advance.
