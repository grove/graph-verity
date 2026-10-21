# V1h-budget Gemma swap2048 host-gate variant — INCONCLUSIVE_REVISE

The owner requested a **2,048 MiB** host swap-used ceiling after the original
1,024 MiB gate blocked Gemma before any attempt. This separately named,
append-only registration changes that one host admission threshold. It does not
change the frozen v1h registration, archive, original sources or retained Qwen
evidence. The original Gemma command remains subject to its original ceiling.

The variant inherits the exact original freeze and all 38 Gemma prompt/token
budgets, source tables, packet representation/membership, system prompt, grammar,
model/tokenizer/runtime identities and registered Rust executable. CPU four
threads, zero GPU layers, concurrency one, 16,384 context, 512 output reserve,
seed 7, temperature zero, thinking off, 300-second deadlines and the **24 GiB
sampled process-tree RSS ceiling** are unchanged. Every other host gate, native
control, identity check, failure stop and preview-only safety boundary remains.
This is a host-admission variant, not the proposed status-rule-precedence ablation.

The wrapper retains the fresh original 1,024 MiB host receipt and all its blockers
alongside a clearly labeled effective 2,048 MiB receipt. Only the swap blocker is
reevaluated. Missing swap measurements and all other blockers still stop the run.
The unchanged base runner verifies all original bytes, rehashes assets and
recounts all 38 prompts before loading. Fresh native parity remains mandatory.
The original per-freeze/model attempt ledger is shared: this variant does not
grant a second Gemma attempt or permit retries. Two native sampling controls and
36 semantic observations remain the maximum 38 completion requests.

`run/` holds the unchanged runner's complete raw output, including its parent
version identifier and original freeze binding. `variant-registration.json` and
`variant.json` identify the amended execution protocol. The outer inventory binds
the entire inner run, including its own inventory. Retain both levels; never
describe the inner output alone as an unchanged-protocol v1h run. No model output
is executed as RDF. All failures and unattempted observations remain evidence.

## Model-free registration and verification

The registration binds this wrapper, its tests and this document by exact hashes,
and inherits the committed parent registration and freeze. Commit those bytes
and the registration before preflight or inference; no rebuild or reseal occurs.

```sh
.venv/bin/python tools/native_one_hop_v1h_swap2048.py register --freeze artifacts/v1h-budget
.venv/bin/python tools/native_one_hop_v1h_swap2048.py verify --freeze artifacts/v1h-budget
.venv/bin/python -m unittest discover -s tools -p test_native_one_hop_v1h_swap2048.py -v
```

The full model-free pipeline remains `.venv/bin/python tools/verify_pre_llm.py`.
Use a separate source/build tree to preserve the registered Rust binary.

## Proposed command — separate explicit authorization required

The owner's earlier **“I authorize it!”** named the original unchanged-gate Gemma
command. Raising the ceiling authorizes preparation of this variant, not its
inference. After review and a fresh passing variant preflight, obtain separate
authorization for this exact command and fresh destination:

```sh
.venv/bin/python tools/native_one_hop_v1h_swap2048.py run \
  --freeze artifacts/v1h-budget \
  --allow-inference \
  --out artifacts/issue83-v1h-budget-gemma4-swap2048-first
```

Fresh model-free preflight uses a new output path each time:

```sh
.venv/bin/python tools/native_one_hop_v1h_swap2048.py preflight \
  --freeze artifacts/v1h-budget --out artifacts/issue83-v1h-swap2048-host-first.json
```

## Comparison limits and next research

Retain Qwen's original 1,024 MiB admission rule separately from this Gemma variant.
Host swap allowance can affect paging, timing and resources; latency/RSS
differences cannot be attributed solely to model identity. Report actual host
swap and every sample. A higher admission ceiling does not establish acceptable
latency, memory safety or semantic quality. Keep oracle and frozen BM25-v1 results
separate, distinguish model-origin clarification from Rust rejection, and retain
source-table contradictions separately from exposed-reference agreement. Missing
Gemma outcomes remain unavailable, not zero or reference errors.

Keep #83 open, #75 integration disabled and independent human review deferred.
Decision remains **INCONCLUSIVE_REVISE**. No model ranking, automatic merge or
semantic/product GO is authorized. A later status-rule-precedence experiment must
be separately preregistered and explicitly authorized; none is implemented here.
