# Aligned v2 implementation and admission status

## Prepared artifacts

- Frozen preregistration SHA-256: `a1ea7d14ba72b0c96682795004a9b243b68934dc182b1e6df0c567d7d238ac69`.
- Frozen dataset manifest SHA-256: `8814fd107b756f2f6a38decf293b9cf918a22232901665057752a1b928cb9616`.
- Frozen benchmark manifest SHA-256: `9e3e92142297a9d08c1a29a5a4c0634b8de47073e398bf8adfddd9657d6fecc4`.
- Frozen questions SHA-256: `108c401a798cde55eac97c0a5b6d9f69cef69527c6901855769ffd069ff028b9`.
- Directional export manifest SHA-256: `27a29ff548025ddf95da069f5292cb21f1f2b1940858baa02c6a887eacdc28e7`.
- Directional feature-input SHA-256: `ad1d32cb4fae8fcc5130cdfe0dbd6249dd74e11eb88bf09846619aa49f8b4ef1`.
- Feature operation SHA-256: `7e7d87980369977b912c03dbfaff6d47ab8e0f21d411c02e6c47c894646c7feb`.
- The graph has 2,157 entities, 5,756 original RDF edges, 84 predicates, 5,756 derived reverse navigation rows, and 168 direction-specific relation IDs. Five predicates account for 72.116% of edges. The export found English labels for 84/84 predicates and Norwegian (`nb`/`nn`/`no`) labels for 83/84. No source aliases or definitions were present in the retained predicate export.

## Verified without inference

- The original v3 final manifest still hashes to `7d1775aada1d1687eb8f36ef2b4b4f1f54ced3f0464338d100d6a3bd60e19c9f`; its training receipt and results report remain unchanged.
- The v2 directional export passed deterministic clean rebuild verification. Forward and reverse rows preserve original source quads; reverse rows are navigation records, not RDF assertions.
- 32 focused model, runner, benchmark, alignment, and provenance tests passed in `/private/tmp/graph-verity-rgcn-env` (Python 3.12.14, PyTorch 2.11.0, PyG 2.7.0). `py_compile` passed. Synthetic checks cover real R-GCN/CompGCN behavior, alignment gradients, direction-sensitive candidates, path ranking, paired inverse filtering, balanced sampling, and shared-pool limits.
- The separate EmbeddingGemma environment matched all 43 pinned package versions. The 14 local model/tokenizer assets matched their exact upstream hashes. Model: `google/embeddinggemma-2` revision `914f7f89142e33e77833254d9c9b90c3cef7303b`; declared upstream license: Apache-2.0. Verification receipt SHA-256: `4ef33e6a2509ff6a926fe9d745cdbcccc308197358d3abc14ad563a9cc8db214`; asset-set SHA-256: `ce59ee1e825fa1e5dd96967b622ae259adcfb5f566d8332698ed8aa76e61fbc4`; runtime SHA-256: `8c97417ef6d8c3a943d9033890f5fb0ea610eb299657adbff1627e6b151a4c34`.
- Asset verification hashed the local weights but did not load them, download files, or run inference. No aligned feature vectors or scored ablations have been generated.

## Fresh host preflight: failed admission

The default sandbox could not read macOS process/VM details, so the same read-only preflight was rerun outside the sandbox and written to a distinct receipt. Nothing was terminated or changed.

- Preflight receipt: `host-preflight-aligned-v2-host.json`.
- Receipt SHA-256: `a2b621a101c4a36c70c835010193261c1466d328ed841b5ff33140a0fee66f9e`.
- Hardware: target M1 Pro, arm64, 32 GiB. Runtime identity: valid. Resource metrics: valid.
- Available memory: `15,079,587,840` bytes. This is `5,920,412,160` bytes below the 21,000,000,000-byte feature-inference gate and `4,247,764,992` bytes below the 18 GiB training admission gate.
- Memory-pressure free percentage: 88%. Swap used: 0 bytes. 568 processes were visible, 331 inaccessible, with the largest visible entries retained in the receipt.
- Result: `fail-resource-or-integrity-gate`; both feature and training resource gates are false. No inference authorization was requested or used, and no training authorization applies to this run.

## Exact next authorization boundary

After available memory meets the feature gate, create a new preflight receipt bound to this frozen preregistration and the asset-verification receipt. The owner must then separately approve `allow_aligned_embeddinggemma_inference=true`, bound to:

- preregistration SHA-256 `a1ea7d14ba72b0c96682795004a9b243b68934dc182b1e6df0c567d7d238ac69`;
- dataset, benchmark, question, directional export, input, and operation hashes listed above;
- model/revision plus asset-set SHA-256 `ce59ee1e825fa1e5dd96967b622ae259adcfb5f566d8332698ed8aa76e61fbc4` and runtime SHA-256 `8c97417ef6d8c3a943d9033890f5fb0ea610eb299657adbff1627e6b151a4c34`;
- the new passing preflight SHA-256.

The current failed receipt cannot serve as that authorization's resource binding. The feature operation is 168 CPU EmbeddingGemma encodes to float32 `[168, 768]`, four intra-op/one inter-op threads, 30-minute limit, 6 GiB process RSS ceiling, no network downloads, and 21,000,000,000 bytes minimum available memory.

After feature inference, the finalized feature manifest and a new training preflight will establish the second, separate authorization request. That training request will bind the final run manifest, exact feature manifest, and passing training preflight. It will cover 48 sequential CPU fits, seeds 117–119, both models, B–E, both partitions, 18 GiB admission/RSS limits, 12 GiB early warning, four/one threads, and six hours total. These observational resource safeguards are not OS-level isolation.

The original research result remains **STOP** for product adoption. This v2 iteration has no result yet and cannot change that decision.
