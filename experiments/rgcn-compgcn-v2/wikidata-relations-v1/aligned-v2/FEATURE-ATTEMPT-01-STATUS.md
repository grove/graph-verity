# Aligned-v2 feature attempt 01

Recorded 2026-10-29. This is a supplementary operational receipt; the frozen preregistration, README, diagnosis, and v3 results are unchanged.

## Authorization and admission

- The owner explicitly approved the exact feature-generation operation in this conversation. The repository runner's `approval` schema checks `status=approved`, `allow_aligned_embeddinggemma_inference=true`, and exact top-level hash bindings; it does not require an external signature or attestation.
- The explicit approval was transcribed without claiming a signature or external attestation into `/private/tmp/graph-verity-aligned-v2-embedding-authorization-0bccf3d17ab8d0f873425e4669ad1d85ec629f1eda6c7da7e5783ca520a8e58a.json`, mode `0600`, SHA-256 `7886deb6e67aac69876b4e0dcf64679e09ab4ab5c3303ae59a91de626520cfbb`.
- Bound preregistration SHA-256: `a1ea7d14ba72b0c96682795004a9b243b68934dc182b1e6df0c567d7d238ac69`.
- Bound model asset receipt SHA-256: `4ef33e6a2509ff6a926fe9d745cdbcccc308197358d3abc14ad563a9cc8db214`; all 14 local assets matched their pins. Asset set SHA-256: `ce59ee1e825fa1e5dd96967b622ae259adcfb5f566d8332698ed8aa76e61fbc4`; runtime SHA-256: `8c97417ef6d8c3a943d9033890f5fb0ea610eb299657adbff1627e6b151a4c34`.
- Passing read-only preflight SHA-256: `0bccf3d17ab8d0f873425e4669ad1d85ec629f1eda6c7da7e5783ca520a8e58a`, captured `2026-10-29T18:48:56.616903Z`. Available memory was `21,791,195,136` bytes; memory pressure free was `88%`; swap was `0`.
- The authorized operation was 168 local-only CPU encodes to float32 `[168, 768]`, 4 intra-op / 1 inter-op threads, 30-minute wall limit, and 6 GiB sampled process RSS ceiling. No network downloads were enabled.

## Attempt result

The registered `features` command exited with code 1 before constructing `embedding_experiment.Encoder`. `embedding_runtime_identity()` calls `embedding_experiment.cpu_runtime()` at `tools/rgcn_compgcn_aligned_run_v1.py:346`, which sets PyTorch's inter-op thread count. `generate_relation_features()` calls `cpu_runtime()` again at line 436; PyTorch raises `RuntimeError: cannot set number of interop threads after parallel work has started or set_num_interop_threads called`.

No model weights were loaded, no embedding inference ran, and no feature archive or feature manifest was created. The failed-attempt JSON receipt is `feature-attempt-01-failure.json` (SHA-256 `f66e4fc346929c375105cd820da1dbe63b1c598ad831186a3a0df7e585f3759a`). No process peak RSS was sampled because the failure happened before the inference loop. No GNN training started.

## Frozen-code boundary

A minimal implementation correction would reuse the already initialized `torch` module and `identity["runtime"]` in `generate_relation_features()` instead of calling `cpu_runtime()` a second time. The frozen preregistration pins the runner's source hash; changing it makes `_validate_source_inputs()` reject the existing manifest. Therefore this authorization cannot be reused to run a modified implementation. A versioned hotfix manifest and authorization bound to its new code identity are required before a retry. No such change or retry has been made.
