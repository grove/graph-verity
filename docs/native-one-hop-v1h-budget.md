# V1h-budget: source-preserving packet compaction

Decision: **INCONCLUSIVE_REVISE**. This is a model-free successor to r3, never
inference authorization, semantic GO or #75 integration. No v1g registration or
historical evidence is amended.

The only experimental factor is reversible presentation of the embedded
whole-question BM25-v1 packet. Repeated ordered object keys become column schemas;
repeated source strings of at least 32 characters become string references.
Every original packet field, value, list order, graph-qualified IRI, role,
numeric-ID binding, ranking, clipping flag and packet ID is preserved. Packing
must reconstruct the exact original JSON serialization, including key order.
Reserved-tag collisions fail closed. The primary entity/predicate/graph tables,
source names, collisions, observed usage and source provenance outside the packet
are untouched. Oracle contexts are byte-equivalent in model messages. The
original v1e system prompt, GBNF and all semantic/safety rules are unchanged.

This is a presentation/budget ablation. It cannot separate the token reduction
from possible model effects of the columnar notation. There is no claim of
semantic improvement. r3 is exposed, incomplete historical evidence, not a fresh
randomized baseline. Status-rule precedence, direction wording, added predicate
definitions and alternative retrieval are distinct possible experiments and are
not included here. v1g remains separately registered and unrun.

CPU Q4_K_M, four threads, zero GPU layers, concurrency one, seed 7, temperature
zero, thinking off, 16,384 context, 512 output, 300-second deadlines, RSS ceiling
24 GiB and the original host gates remain unchanged. Each model has exactly two
native sampling controls and 36 semantic observations: oracle repeats (two),
eleven controls plus six smoke cases in oracle, and eleven controls plus six
smokes in frozen BM25-v1. No retries, RDF execution or automatic Gemma loading.

All 38 prompts per model are tokenized offline before registration. Exact
template bytes, token IDs, SHA-256 identities, input tokens, output reserve and
strict `input + 512 < 16384` decisions are retained. Section contributions are
telescoping differences in original top-level key order, including system,
template and empty-user-object overhead; they sum exactly but are order dependent.
They are not semantic importance scores or additive independent BPE counts.
The pinned official tokenizer uses its exact retained native chat template.
Retained native parity records are reproduced without starting llama-server;
fresh native parity is still mandatory before each future generation.

## Model-free preparation and verification

Source must be committed before registering a freeze. Always use fresh paths.
The freeze builder reads original r3 archive contexts, never reference plans.
Operator resolution fixtures are copied only after prompt sealing, for strict
post-generation Rust preview. Model inputs never contain operator selections,
intended directions, answer bindings or exposed-reference fields.

```sh
.venv/bin/python tools/native_one_hop_v1h.py freeze --out artifacts/v1h-budget
.venv/bin/python tools/native_one_hop_v1h.py register --freeze artifacts/v1h-budget
.venv/bin/python tools/native_one_hop_v1h.py verify --freeze artifacts/v1h-budget
.venv/bin/python tools/native_one_hop_v1h.py budget --freeze artifacts/v1h-budget \
  --model qwen35 --out artifacts/v1h-budget-qwen-recount
```

`freeze`/`budget` invoke the already installed pinned tokenizer environment with
local-files-only, trust-remote-code disabled and a minimal offline environment.
They load tokenizers, not model weights. Missing assets are blockers; nothing is
downloaded, rebuilt or silently substituted. Ordinary CI verifies retained
tokenization receipts and synthetic transport without requiring native assets.

## Separately authorized future command

First restore the committed `freeze.tar.gz` into a newly created directory,
verify all hashes, and obtain explicit authorization naming this exact revision,
model, schedule and fresh output. The command below is a proposal, not permission:

```sh
.venv/bin/python tools/native_one_hop_v1h.py run \
  --freeze artifacts/v1h-budget --model qwen35 --allow-inference \
  --out artifacts/issue83-v1h-budget-qwen35-first
```

The runner enforces committed registration, source/binary/asset identities,
concurrency and a per-freeze/model no-retry ledger. It recounts every prompt for
the selected model **before weight loading**, compares exact token identities
with registration, then runs native character-grammar controls and a fresh host
gate after hashing/counting. Host age must be at most 60 seconds. Native
template/token parity must match the pre-load receipt before any completion
request. The original bounded offline runtime retains prompts, raw bytes/SSE,
native timings, validator outcomes and concurrent process-tree RSS samples.

Known individual Rust draft rejections and semantic failures remain observations;
integrity, unknown Rust errors, authorization, context/output/stream/deadline,
private-canary and resource failures stop the remaining schedule. Trusted catalog
preflight and source hashes are checked per case. Prompt/request repetition
identity is fatal if changed; response disagreement is recorded. Rust receives
original bytes in `nl-ask-preview` only. Missing vocabulary is never restored.
Clarification emitted by the model is distinct from deterministic rejection.
Every failed and unattempted case remains visible with null missing outcomes.

Gemma requires a separate exact command and approval after reviewing Qwen and
shared integrity results. Nothing automatically runs it. Keep #83 open and #75
disabled. Independent human semantic review remains pending.
