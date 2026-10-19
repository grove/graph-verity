# Native one-hop adapter v1 (#83)

`tools/native_one_hop.py` is a separate operator experiment for
`nl-ask-draft-v1`. It does not connect a model to the #75 browser. Its only Rust
action is `nl-ask-preview`; it cannot approve or execute a proposed RDF query.
The [retained report](../reports/issue-83-native-one-hop/README.md) records actual
attempts and distinguishes runtime controls from model-free tests.

## Frozen variant and inputs

[issue83-native-cpu-v1c](../configs/native-one-hop-v1c.json) uses the original #74
CPU budgets: official locally retained Qwen3.5-9B / Gemma 4 12B Q4_K_M, four CPU
threads, zero GPU layers, one runtime, 16,384 context tokens, 512 output tokens,
16 KiB draft bytes, greedy sampling, seed 7, thinking off, 300 seconds per runtime
operation, no generation retries. Metal and other checkpoints are not variants
of this experiment. Any changed constraint requires a new named preregistration.
A nonblocking operator lock also prevents two invocations from loading models
concurrently. This lock only coordinates this runner; host preflight separately
checks for other local model processes.

The initial `issue83-native-cpu-v1` attempt is retained with its exact source
archive: Qwen followed the strict contract even without grammar, so the conflict
control did not demonstrate enforcement. V1b freezes a separate adversarial
[control-only system prompt](../configs/native-one-hop-controls-v1.prompt.txt);
model assets, main prompt, grammar, budgets and sampling are unchanged. No scored
case preceded this revision. The retained v1b unconstrained output copied the
large enclosing context and hit the same 512-token cap. V1c keeps that control
prompt but freezes a small synthetic conflict context without RDF labels or
entity/predicate rows; normal model inputs and all CPU budgets remain unchanged.

The [new prompt](../configs/native-one-hop-v1.prompt.txt) implements the new
contract; it does not reuse #48's general parser prompt. The
[GBNF source](../configs/native-one-hop-v1.gbnf) allows exactly one candidate,
clarification or unsupported object, with bounded JSON strings and whitespace.
The adapter adds entity/predicate/graph rules containing only the numeric IDs in
the current role tables. Empty entity/predicate tables allow abstention only.
Rust remains authoritative for graph-qualified membership, policy, independently
resolved starts and the strict draft contract. Wrong direction can still compile;
reference comparison is a separate diagnostic.

`freeze` uses all 30 already exposed #72 evaluation questions (15 Norwegian,
15 English), the entire source-audited oracle catalog, and freshly generated
whole-question BM25-v1 packets from the same authorized sources. Each condition
keeps 18 supported, six clarification and six unsupported cases. No #82
neighborhood condition is substituted. Numeric retrieval tables contain only
retained graph/role matches; missing IDs are not restored from reference plans.
Original source labels, language, roles, graph and license provenance remain in
the inputs. Source-label control uses #72's explicitly synthetic injection label.
The reference plans, expected statuses, answer bindings, host blocks and resolved
start fixtures never enter a model request. The offline preview uses the existing
benchmark resolution fixtures only *after* generation; it is not a new automatic
resolver or evidence of independent user disambiguation.

## Operator commands

Ordinary CI uses only the pinned Rust/Python reference dependencies. It never
needs native model dependencies, weights, credentials or downloads. Prepare the
existing #48 assets separately; this runner has no acquisition, build or model
substitution command. Asset verification reads/hash-checks all original native
checkpoint/config/tokenizer/template files, the retained Q4 files and executable
receipts against #74, the pinned llama.cpp archive and complete extracted source
tree, and #48's original archived licenses. Missing or changed bytes block the
attempt.

```sh
cargo build --workspace --locked --offline
.venv/bin/python -m unittest discover -s tools -p test_native_one_hop.py -v
# Always use new destinations; retain every failed attempt.
.venv/bin/python tools/native_one_hop.py freeze --out artifacts/issue83-new-freeze
.venv/bin/python tools/native_one_hop.py preflight --out artifacts/issue83-host.json
# A passing preflight is not inference authorization. An operator must opt in:
.venv/bin/python tools/native_one_hop.py run \
  --freeze artifacts/issue83-new-freeze --model qwen35 --allow-inference \
  --out artifacts/issue83-qwen35-new-attempt
# Run the other pinned model serially, with another fresh preflight inside run.
.venv/bin/python tools/native_one_hop.py run \
  --freeze artifacts/issue83-new-freeze --model gemma4 --allow-inference \
  --out artifacts/issue83-gemma4-new-attempt
# Local saved-byte replay with the exact frozen Rust binary; no weights are read:
.venv/bin/python tools/native_one_hop.py replay \
  --freeze artifacts/issue83-new-freeze --run artifacts/issue83-qwen35-new-attempt
```

The fresh, authoritative preflight runs **after asset hashing**, immediately
before loading. It requires the preregistered Apple M1 Pro/32 GiB/arm64 host,
#74's load/swap/memory/disk/competing-process gates, AC power and verified thermal
conditions. Unknown metrics fail closed. It records timestamped commands,
CPU/load/swap/available memory, thermal/power and process executable/owner/resource
conditions without arguments or environment values. It never stops someone
else's VM, background process or model. A host blocker leaves all cases visibly
unattempted and model accuracy null.

The owned child processes receive a minimal offline environment and fresh HOME,
without inherited tokens, proxies or credential caches. Tokenizers use
`local_files_only=True`, `trust_remote_code=False`; llama.cpp uses local model
paths and `--offline`, CPU-only build flags, and a loopback-only endpoint. This
is an offline local experiment, not a network-isolation sandbox for arbitrary
executables. Only the exact receipt-verified native executables are supported.
Ctrl-C/SIGTERM and wall deadlines tear down the process groups this runner
created, including descendants; partial SSE and proposal bytes remain retained.

## Native controls and optional evaluation

Before generation, the pinned native GBNF validator runs positive/negative
controls for statuses, duplicate/extra fields, truncation, concatenated objects,
unknown IDs, invalid directions and rationale limits. These character-level
controls alone do **not** establish tokenizer/sampler compatibility.

For every actual generation, the official native tokenizer renders the exact
messages offline. Its prompt bytes and token IDs must equal llama.cpp's native
chat-template/tokenizer results. Gemma's documented single leading BOS omission
is the only allowed canonicalization; explicit token-array completion prevents a
second BOS. Qwen mismatches and other Gemma differences block the variant. JSON
serialization quotes both models' angle-bracket control tokens inside source
strings. Native unconstrained/constrained sampling conflict controls then test
actual grammar enforcement. The runner also requires byte-identical repeated
generation, original source-label injection, ambiguous-start clarification and
private/scope/write abstention before its bilingual forward/reverse smoke.
Original raw files, including failed or truncated outputs, reach Rust unchanged;
no JSON repair, duplicate collapse or answer execution is permitted.

After these controls, the smoke compares English/Norwegian normal and reverse
one-hop drafts against the **exposed AI-authored** reference requests. This is
reference agreement, not independent human approval. `run --evaluate` explicitly
adds one pass of all 30 cases in each of the separate oracle and BM25-v1 stages.
An interrupted backend leaves all remaining cases unattempted. Saved scorers
retain model-origin abstentions, compiler rejection, wrong-but-executable plans,
start/predicate/direction diagnostics, retrieval misses and missing outcomes.
There are no approved answer executions in this runner; typed answer accuracy
and actual user decision time remain unmeasured. The decision stays
`INCONCLUSIVE_REVISE` with no model ranking until the complete comparison and
separately approved answer evidence meet the frozen #74 thresholds.

The model-free CI replay checks the retained source/configuration hashes,
rebuilds the same Rust sources for its platform, replays every saved original
draft (including rejection), and checks raw SSE deltas against the proposal bytes.
It does not require the original macOS binary hash to equal a Linux build. The
local `replay` command additionally requires the exact recorded Rust binary.

Receipts bind source/config/schema/grammar/binary hashes and complete per-file
raw input/output/log inventories. Native timing/token counts, startup and first
completed response time, and timestamped concurrent runner/descendant RSS samples
are retained. RSS sampling can miss peaks and double-count shared pages. The
first response includes controls/tokenizer overhead; OS page cache is not evicted,
so this is not a disk-cold latency claim. Historical #48/#72–#76 freezes and
scores stay unchanged. Nothing promotes Ask or hybrid Find or opens the sealed
external holdout.
