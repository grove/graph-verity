# Issue #48: grounded modern local model experiment

The [issue48-v1 public protocol](../../docs/grounded-model-experiment.md) and
[configuration](../../configs/grounded-models-v1.json) predeclare the shared
typed-plan task, oracle and actual Find/BM25 stages, fixed smoke controls,
CPU-only budgets, scoring and numerical continuation criteria. No model output
was used to choose those criteria. The historical Qwen2.5 reports/configurations,
public references and sealed holdout are unchanged.

Official upstream identities and legal material were archived **before native
weight acquisition** on 17 October 2026:

| Candidate | Official immutable revision | Native weight bytes | License |
|---|---|---:|---|
| [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B/tree/c202236235762e1c871ad0ccb60c8ee5ba337b9a) | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | 19,306,310,880 | [Apache-2.0](qwen35-LICENSE.txt) |
| [google/gemma-4-12B-it](https://huggingface.co/google/gemma-4-12B-it/tree/707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7) | `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` | 23,919,549,408 | [Apache-2.0](gemma4-LICENSE.txt) |

The checksummed [upstream archive](upstream.tar.gz) retains per-model folders with
the original model card, config, tokenizer config, official chat template, actual
legal bytes and complete upstream file metadata. The linked plain-text licenses
normalize whitespace for reading; actual legal-file SHA-256 identities refer to
the unmodified archived bytes. Every native file,
including full tokenizer/processor assets and all weights, has an expected
SHA-256 in the experiment config; native preparation checks actual full bytes.
Gemma's repository has no LICENSE file: its model card links to
[Google's Apache 2.0 page](https://ai.google.dev/gemma/docs/gemma_4_license).
The original HTML (`gemma4-license.html`) and extracted full terms are archived.
Qwen's repository includes its actual legal file.

Runtime is pinned llama.cpp
[`c0fd78626405c6d9b934efef0ec7291fcc20e3d6`](https://github.com/ggml-org/llama.cpp/tree/c0fd78626405c6d9b934efef0ec7291fcc20e3d6),
with Metal, Accelerate and BLAS disabled. Both exact architectures are registered
in that converter. Text-only compatibility is tested rather than inferred from
registration or the old b5046 runtime. Both native checkpoints are converted to
F16 GGUF then Q4_K_M; these generated assets and converter/runtime environments
receive independent receipts.

Preparation diagnostics retained so far: the host default Python 3.15 has no
matching pinned PyTorch wheel; Python 3.12 works. The upstream converter's listed
Transformers 4.57.6 fails Gemma 4's actual `extra_special_tokens` list with an
`AttributeError`; the separately pinned Transformers 5.20.1 environment exports
the unchanged native Gemma tokenizer successfully. Neither tokenizer export is
model inference or semantic evidence. The complete successful environment is
[locked separately](../../tools/grounded-models-requirements.txt) for both models.

The outcome and retained run evidence will be recorded here after the locked
opt-in runs. Checksums establish byte integrity, not signatures, expert review or
accuracy. A positive outcome could only justify **further study**. No model is
enabled in [Confirmed Ask](../../docs/confirmed-ask.md) or unattended Ask; promotion
requires a separate explicitly approved integration issue and user-facing
false-confidence evaluation. The existing [Phase 0 decision](../../docs/phase-0-decision.md)
and independent-review/holdout limitations remain in force.
