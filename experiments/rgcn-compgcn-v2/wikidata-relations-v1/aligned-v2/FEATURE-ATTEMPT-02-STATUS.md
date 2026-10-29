# Aligned-v2 feature attempt 02 — runtime-fix-2

Status: **feature generation completed; no GNN training started**.

This attempt uses the corrected one-time PyTorch CPU runtime and the new
versioned preregistration. The earlier feature-attempt-01 failure remains
unchanged and is not reclassified.

## Frozen inputs and authorization

- Preregistration: `experiment-manifest-aligned-v2-runtime-fix-2.json`
  SHA-256 `0aa68130c5195421c63ae5682ae661717bde87278cc2a8da20546a2d58533c2c`.
- Parent frozen aligned-v2 manifest SHA-256
  `a1ea7d14ba72b0c96682795004a9b243b68934dc182b1e6df0c567d7d238ac69`.
- Model: `google/embeddinggemma-2`, revision
  `914f7f89142e33e77833254d9c9b90c3cef7303b`; the local asset receipt verified
  all 14 assets. Embedding runtime SHA-256
  `8c97417ef6d8c3a943d9033890f5fb0ea610eb299657adbff1627e6b151a4c34`.
- Dataset manifest SHA-256
  `8814fd107b756f2f6a38decf293b9cf918a22232901665057752a1b928cb9616`;
  benchmark manifest SHA-256
  `9e3e92142297a9d08c1a29a5a4c0634b8de47073e398bf8adfddd9657d6fecc4`;
  question SHA-256
  `108c401a798cde55eac97c0a5b6d9f69cef69527c6901855769ffd069ff028b9`.
- Fresh feature preflight SHA-256
  `bb39ea842213c7a4f4b828e40c9d891be817b785bb3dda935318eac67dd8af03`.
- One-time owner authorization SHA-256
  `3e43279ef25b92301d555575bf1cde61d12a6cee9ac9a4d3cdf05a078318486f`;
  the authorization record is outside the repository with mode `0600`.
- Operation: encode the 168 frozen direction-aware English/Norwegian predicate
  descriptions into CPU float32 `[168,768]`; 4 intra-op / 1 inter-op threads,
  30-minute limit, 6 GiB RSS gate, local verified assets only, no downloads.

## Result

- Canonical archive:
  `runtime-fix-2/directional-relation-features.npz`, SHA-256
  `a6eae9c8ee4d316af07556fc6faba17d0f9e8be1ae9a20657b383d2ced2507b6`.
- Feature manifest:
  `runtime-fix-2/directional-relation-features.manifest.json`, SHA-256
  `caa194e8d8f89ae17ca0a488b33391169f0e1d4d140097aeded7f5f7c34749b3`.
- Post-generation verification confirmed 168 ordered IDs, shape `[168,768]`,
  float32, all finite, row norms from `0.99999976` to `1.00000024`.
- Model initialization loaded all 413/413 weights. The measured encode loop was
  5.666 seconds; total command wall time was 11.60 seconds. Model-load time was
  not measured separately.
- Peak process RSS was not captured: `/usr/bin/time -l` could not read
  `sysctl kern.clockrate` in this execution context and emitted no maximum-RSS
  value. The runner's per-batch 6 GiB RSS guard did not raise, but that is not a
  substitute for a recorded peak.
- The root-level `directional-relation-features.*` paths are hard links to the
  canonical files above, made for the existing finalizer's sibling-file
  convention; their contents and SHA-256 values are identical.

## Training preparation

- Final manifest:
  `experiment-manifest-final-aligned-v2-runtime-fix-2.json`, SHA-256
  `03ac58845799c9fdde76a7717605e60a789dbf608a0b0725cc9123d718ff62e4`.
  It binds the archive and feature-manifest hashes above, unchanged data/splits,
  corrected code identities, and the registered 48 sequential fits.
- Fresh passing training preflight:
  `runtime-fix-2/host-preflight-training-02.json`, SHA-256
  `ef1ee4335c6ed75588b7222cd12e2184846a9681807d02b1adbd6d1e7eeae90c`;
  captured `2026-10-29T19:19:49.459143Z`. Available memory was
  21,518,303,232 bytes (2,190,950,400 above 18 GiB); memory-pressure free was
  89%; swap used was 0; resource sampling was valid. Sequential execution is
  registered. A preceding sandbox-restricted preflight failed telemetry
  collection and is preserved separately.
- **Training remains unauthorized and was not run.** It requires a new explicit
  owner authorization bound to the final manifest, feature manifest, passing
  preflight, source/split/code identities, and this command:

  ```bash
  python tools/rgcn_compgcn_aligned_run_v1.py train \
    --manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v2/experiment-manifest-final-aligned-v2-runtime-fix-2.json \
    --features experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v2/directional-relation-features.npz \
    --feature-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v2/directional-relation-features.manifest.json \
    --preflight experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v2/runtime-fix-2/host-preflight-training-02.json \
    --authorization /approved/aligned-v2-runtime-fix-2-training-authorization.json \
    --out experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v2/training-run-runtime-fix-2
  ```

The original manifests, attempt-01 failure evidence, v3 results, benchmark,
references, and splits were preserved. The pinned research test suite passed:
49 tests, no skips.
