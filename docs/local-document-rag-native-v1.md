# First native document-RAG trial: proposed CPU baseline

Preparation for #122, parent #71, after merged #123. **No weights acquired, model
started, inference performed, owner authorization granted, or native quality
validated by this change.** Keep #122 open and `INCONCLUSIVE_REVISE`. This is a
single trial of the existing document adapter, without graph execution.

## Candidate identity and unresolved assets

[Machine-readable proposal](../configs/local-document-rag-native-v1.proposal.json)
is deliberately **not** an executable registration or authorization.
Metadata was inspected on 2026-10-24 without weight downloads:

| Item | Verified published metadata / remaining limitation |
| --- | --- |
| Original | [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/tree/cdbee75f17c01a7cc42f958dc650907174af0554), revision `cdbee75f17c01a7cc42f958dc650907174af0554`; 4B instruction checkpoint, non-thinking only; no `enable_thinking` switch or `<think>` output expected ([model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)). |
| License | Original [Apache-2.0 license](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/LICENSE) permits local use subject to its terms. GGUF publisher also declares Apache-2.0. Retain licenses/notices with acquired assets. |
| Quantization | [Unsloth file at immutable revision](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/blob/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf): `a06e946bb6b655725eafa393f4a9745d460374c9`, `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, 2,497,281,120 bytes; SHA-256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`. This is the published SHA-256, **not** the different Xet hash. Local bytes remain unverified. |
| Template/tokenizer | Official `tokenizer_config.json` at the original revision: SHA-256 `a62ff0a2472a0fa1b8eaabcb57c59b58afa42a22831dc141400b6e0cf2b65ce3`; its decoded UTF-8 `chat_template` field: `64f85b198065d0fba2a81f37e10ed68161ce2c19a754c7100e67e0ca2ee9c326`. Published `tokenizer.json` LFS SHA-256: `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`. The config was read; tokenizer bytes were not acquired. |
| Requirements | [Official tokenizer config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/tokenizer_config.json) uses Qwen2Tokenizer, role delimiters `<\|im_start\|>` / `<\|im_end\|>`, assistant generation prefix, EOS `<\|im_end\|>`, no automatic BOS; apply the official template, without tools. Native Transformers examples require Qwen3 support (>=4.51.0). This is separate from llama.cpp support. |
| Runtime | [Publisher](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) and [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) describe GGUF/chat serving. **No exact llama.cpp revision/build is selected or proven operational.** Pin source, build flags and binary, inspect that revision's `--help`, and verify this Qwen3 tokenizer/template handling before registration. |

Native BF16 safetensors and lossy quantized GGUF are different bytes and
representations. A matching publisher filename does not establish the conversion's
original checkpoint revision, tokenizer equivalence or Norwegian quality. Inspect
the acquired GGUF architecture, quantization, special token IDs and embedded
metadata with the pinned runtime's GGUF inspection tooling; compare to the pinned
official config. Retain that private inspection and build log. The explicit
`--chat-template-file` selects the official extracted template, but **does not
replace or validate GGUF tokenizer tensors/metadata**. Any discrepancy stops the
trial; do not silently patch or substitute another quantization.

Memory planning is an estimate, not a measurement: the file is about 2.33 GiB.
From the [native config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75f17c01a7cc42f958dc650907174af0554/config.json),
a full 8192-token F16 K+V cache is approximately
`2 * 36 layers * 8 KV heads * 128 head dimension * 2 bytes * 8192 = 1.125 GiB`.
Weights plus KV alone are about 3.45 GiB; allocator, compute buffers, mmap and OS
memory add more. Actual llama.cpp settings and RSS must be measured. An 8 GiB
sampled **server+client process-tree** ceiling leaves room on 32 GiB; it is not an
OS memory reservation or a guarantee against a short spike.

## Safe preparation now: private source-only baseline

Use a fresh canonical directory outside the repository. All snippets assume the
repository root, Python 3.12+, and operator-selected absolute paths without spaces.
Do not replace `$HOME` or use a shared/world-readable output directory.

```sh
umask 077
set -C
TRIAL_DIR=$(mktemp -d /private/tmp/verity-document-trial.XXXXXX)
export TRIAL_DIR
mkdir -m 700 "$TRIAL_DIR/collection" "$TRIAL_DIR/ledger"
cp tests/fixtures/document-rag-native-v1/*.md "$TRIAL_DIR/collection/"
cp tests/fixtures/document-rag-native-v1/sources.json "$TRIAL_DIR/collection/"
python3 tools/document_rag.py build --manifest "$TRIAL_DIR/collection/sources.json" \
  --index "$TRIAL_DIR/index.json" --scope development
python3 tools/local_cited_generation.py --manifest "$TRIAL_DIR/collection/sources.json" \
  --index "$TRIAL_DIR/index.json" --scope development --language en \
  --question 'What does the default local answer mode display?' > "$TRIAL_DIR/source-only.json"
```

The checked-in collection contains original small operational notes under this
repository's Apache-2.0 license and an explicitly adversarial/conflicting note.
It is development material, not a representative benchmark. Its manifest pins
each exact source. The proposal pins the manifest. The owner must accept this
scope before inference; the adversarial note is deliberately not authoritative.
No historical Ask holdout or historical model files are used.

The [14-case protocol](../tests/fixtures/document-rag-native-v1/cases.json) contains
English/Norwegian direct, paraphrase, identifier, no-match, ambiguous, conflicting,
incomplete, injection, counting/synthesis and deliberately invalid citation probes.
All expected answers are **agent-authored development references, not independent
human gold**. Run source-only retrieval and saved-output rejection probes now.
For an invalid saved replay, take a returned exact sentence and substitute an
unreturned `d:` ID, or pair a Norwegian sentence with an English passage ID; use
`--saved-completion` and inspect the deterministic fallback. Do not manufacture a
native success by replaying the reference.

The initial proposed native order is **one English direct case**, inspect all
receipts, then one Norwegian direct case with a **new** owner authorization.
Other native probes need their own later decisions; no batch or retry is implied.
The ambiguous/conflict probes expose a real limit: lexical overlap and a valid
quote can still pass the narrow checker despite answering the wrong question or
selecting one side of a contradiction. The operator must score those as failures,
retain the raw result, and require source-only treatment; there is no automatic
semantic/conflict detector in this slice. Do not authorize such a case as a
supported user-facing answer.

## After separate owner approval: asset preparation and server startup

**The following steps require new approval and must not run during this PR.**
Approval to acquire/build assets and start the server is separate from each
one-shot completion approval. Historical Qwen3.5/Gemma runs confer no authority.

1. Acquire only the immutable GGUF above and pinned official tokenizer/config/
   license assets into a private asset directory. Verify size and `shasum -a 256`
   against the proposal; never use floating `main`, `-hf` or automatic downloads
   in a native command. Extract `json.load(...)["chat_template"].encode("utf-8")`
   to a new mode-0600 `chat.jinja`, with **no added newline**, and verify its hash.
2. Choose an immutable llama.cpp commit supporting this exact GGUF, template and
   CLI. Retain source/archive hash, compiler/build log, `--version`, `--help`, and
   all linked library identities. Prefer the proposal's static CPU build flags:
   Metal/BLAS/Accelerate/CURL off. No network support or speculative/embedding
   model, one model, one slot. No preexisting build is approved by this document.
3. Inspect `sysctl -n machdep.cpu.brand_string hw.memsize`, `vm_stat`,
   `sysctl vm.swapusage`, `memory_pressure -Q`, `uptime`, and
   `ps -axo pid,ppid,pcpu,rss,comm`. Check AC power and thermal state with
   `pmset -g batt` and `pmset -g therm`. Stop/avoid competing generative,
   embedding and GNN work through the owner's normal process controls.
   Admission requires M1 Pro/32 GiB, >=40% memory free, <=1024 MiB swap,
   load/CPU <=0.75, measured server RSS <=8 GiB and no recognized competing
   model processes. Missing metrics block. Generic Python processes cannot be
   reliably classified: the owner must explicitly attest quiescence.
4. Export `ASSET_DIR` for the private directory containing the verified GGUF,
   `tokenizer_config.json`, `tokenizer.json` and extracted `chat.jinja`. Export
   `RUNTIME_PATH` and `RUNTIME_REVISION` from the independently verified build.
   The following creates an **unapproved draft** and prints the full command;
   it downloads/loads no weights and starts no server.

```sh
PYTHONPATH=tools python3 - "$TRIAL_DIR" <<'PY'
import json, os, shlex, sys
from pathlib import Path
import local_cited_generation as g
p = Path(sys.argv[1]).resolve()
a = Path(os.environ['ASSET_DIR']).resolve()
proposal = json.load(open('configs/local-document-rag-native-v1.proposal.json'))
pid = int(os.environ.get('SERVER_PID', '2'))  # unusable draft placeholder
r = dict(version=2, backend=g.BACKEND, host='127.0.0.1', port=8095,
         model_name='verity-qwen3-4b-2507-q4km', cpu_threads=4, gpu_layers=0,
         context_tokens=8192, max_output_tokens=256, timeout_seconds=300,
         temperature=0, seed=7, model_revision=proposal['model']['revision'],
         gguf_revision=proposal['gguf']['revision'],
         runtime_revision=os.environ['RUNTIME_REVISION'], server_pid=pid,
         server_started='PENDING_START' if pid == 2 else
             g._command(['ps', '-p', str(pid), '-o', 'lstart=']),
         system_prompt_sha256=g.documents.sha(g.SYSTEM_INSTRUCTION.encode()))
assets = {'model': a / proposal['gguf']['file'],
          'runtime': Path(os.environ['RUNTIME_PATH']).resolve(),
          'chat_template': a / 'chat.jinja',
          'tokenizer_config': a / 'tokenizer_config.json', 'tokenizer': a / 'tokenizer.json'}
for key, path in assets.items():
    r[key + '_path'] = str(path)
    limit = g.MAX_MODEL_BYTES if key == 'model' else g.MAX_EXECUTABLE_BYTES
    r[key + '_sha256'] = g._sha_file(str(path), limit if key == 'runtime' or key == 'model' else 16 * 1024**2)
for key, expected in [('model', proposal['gguf']['published_sha256']),
                      ('chat_template', proposal['chat_template_sha256']),
                      ('tokenizer_config', proposal['tokenizer_config_sha256']),
                      ('tokenizer', proposal['published_tokenizer_json_sha256'])]:
    g.require(r[key + '_sha256'] == expected, 'Asset mismatch: ' + key)
g._private_write(p / ('registration-draft.json' if pid == 2 else 'registration.json'),
                 g.documents.serialized(r))
print(shlex.join(g.server_command(r)))
PY
```

V1 registrations are intentionally rejected. Runtime commit/binary/build provenance
must be checked independently; a binary hash does not establish its source commit.
Keep the draft, build receipt and all assets immutable.

Its shape is:

```text
/absolute/llama-server --model /absolute/Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
 --host 127.0.0.1 --port 8095 --alias verity-qwen3-4b-2507-q4km \
 --threads 4 --threads-batch 4 --n-gpu-layers 0 --ctx-size 8192 \
 --parallel 1 --n-predict 256 --no-warmup --jinja \
 --chat-template-file /absolute/chat.jinja
```

Only after launch approval, start that exact command under `/usr/bin/time -l`,
redirecting stdout/stderr to **new private** files. Set offline environment flags
(`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `OMP_NUM_THREADS=4`,
`OPENBLAS_NUM_THREADS=4`, `VECLIB_MAXIMUM_THREADS=4`), and ensure no external clients
can use the endpoint. `--no-warmup` avoids unregistered warmup generation. Allow
**at most 300 seconds for startup**, watching memory; if `/health` is not ready,
stop the owned server and record failure without a completion. Five minutes is a
conservative first inspection window for cold CPU loading, not a speed claim.
Keep launch/startup `/usr/bin/time` receipts: the adapter samples only its request
window. No retries or fallback model launches.

Verify `ps -ww -p PID -o command=`, `ps -p PID -o lstart=`,
`lsof -nP -a -p PID -iTCP:8095 -sTCP:LISTEN -Fn`, and
`lsof -p PID` for executable/model/library mappings. Confirm server startup logs
report the expected architecture, tokenizer, template, context, CPU and GPU layers.
The adapter checks the exact process command/start and loopback listener, and
hashes on-disk files; the owner must still compare the mapped executable/model
and logs. A model alias, PID or disk hash alone cannot prove the loaded tensors.
Stop on disagreement. There is a time-of-check race with external process changes.

## Freeze request, obtain fresh owner approval, then run once

These preparation statements do not invoke inference. Export the verified actual
`SERVER_PID` and rerun the registration snippet to create `registration.json`
with the observed process start identity. A restart needs a new registration and
approval. Files are never overwritten. Then:

```sh
PYTHONPATH=tools python3 - "$TRIAL_DIR" <<'PY'
import json, sys
from pathlib import Path
import grounded_rag as e
import local_cited_generation as g
p = Path(sys.argv[1]).resolve()
r = g.load_registration(p / 'registration.json')
packet = e.retrieve(p / 'collection/sources.json', p / 'index.json', 'development',
                    'What does the default local answer mode display?', 'en', 3)
request = g.request_payload(r, g.build_messages(packet))
g._private_write(p / 'fixed-packet.json', e.documents.serialized(packet))
g._private_write(p / 'fixed-request.json', request)
print(json.dumps({'registration_sha256': g.fingerprint(r),
                  'packet_sha256': g.fingerprint(packet),
                  'question_sha256': e.documents.sha(packet['question'].encode()),
                  'request_sha256': e.documents.sha(request),
                  'ledger_path': str(p / 'ledger')}, indent=2))
PY
```

Inspect both complete files, scope, source-only passages, citation IDs, request
budgets and host before approving. Request construction conservatively budgets
UTF-8 bytes plus 256 template overhead tokens and output against context; for
this byte-BPE/no-tools template it deliberately rejects large prompts. This is
not a measured prompt-token count; preserve the server's available token usage.
The **whole HTTP exchange** is capped at 300 seconds, without streaming/retries.
Temperature=0 and seed=7 are repeatability controls, not cross-build bitwise proof.
Metal is a separately registered future experiment.

The owner now explicitly decides: **approve precisely one request for this trial,
model/runtime registration, packet, question, language and development scope,
request digest, private ledger and expiration, under the four-thread CPU budget?**
Only after that decision may the owner create mode-0600 `owner-approval.json`:

```text
version: 1
trial_id: document-rag-native-cpu-v1-en-direct
unique authorization_id: <fresh per attempt, never reused>
action: one_shot_local_document_answer
owner_identity: <owner's recorded identity>
owner_approved: true  [only the owner can grant this]
host_preflight: operator_verified_quiescent_host
registration_sha256, packet_sha256, question_sha256, request_sha256: <printed digests>
scope: development
ledger_path: <exact canonical private ledger path printed above>
expires_utc: <short future UTC ISO timestamp ending Z; at most 24h, prefer 10min>
```

This is a schema description, **not an approval file**. The agent must not create
an affirmative approval on the owner's behalf. The owner attestation is trusted
local input, not a digital signature or protection against an owner modifying it.
Do not relocate/delete the consumed ledger or change approvals to retry a failure.
The ledger-path binding prevents reuse in another ledger without altering the
approved input. Authorizations are rechecked immediately before atomic, durable
consumption. Timeout, connection refusal and rejected outputs all consume them.

Only after the exact one-shot approval:

```sh
python3 tools/local_cited_generation.py --manifest "$TRIAL_DIR/collection/sources.json" \
 --index "$TRIAL_DIR/index.json" --scope development --language en \
 --question 'What does the default local answer mode display?' \
 --runtime-registration "$TRIAL_DIR/registration.json" \
 --run-authorization "$TRIAL_DIR/owner-approval.json" --ledger-dir "$TRIAL_DIR/ledger" \
 --execute-authorized-inference > "$TRIAL_DIR/native-en-result.json"
```

Select a new result filename per attempt; use shell noclobber (`set -C`) when
redirecting operator logs/results. The adapter itself uses unique 0700 run folders,
0600 exclusive artifact creation and never overwrites receipts or consumed markers.
Stop the owned server after inspection; client disconnection does not establish
that server computation stopped. Never launch another model to recover this run.

## Inspect receipts and decide

Every admitted adapter attempt retains `packet.json`, original registration and
authorization inputs, `prepared.json` (all bindings, host/process observations,
command, adapter digest), exact `request.json`, bounded original `response.bin`
(up to 16 KiB), and final `receipt.json`. Rejected prerequisites leave a private
receipt with `model_request_attempted=false`; no-evidence skips authorization and
transport. A filesystem failure can prevent full persistence and fails the CLI.
An interrupted/killed client may leave an incomplete folder; that is incomplete
evidence, never success and never permission to reuse a consumed approval.

Inspect HTTP status, allowlisted headers, model alias, finish reason/token usage
when parseable, raw-byte hash/retained length, error type/message, timestamps,
latency, exact citation rejection, source freshness, final answer/fallback and
whether sending was attempted. `model_request_attempted` records calling the
transport, while `request_send_attempted` distinguishes a refused connection;
server-side inference remains a separate observation. A fake server in tests
produces no evidence of model inference.

RSS is sampled every ~0.2 seconds for model PID, model descendants, and combined
server+client trees. Missing values are **unmeasured**; gaps are recorded as errors.
Shared pages can be double counted; spikes between samples and startup are missed.
Above 8 GiB combined sampled RSS, the client disconnects and rejects the result.
This is an observation/abort guard, **not** an OS-enforced memory cap or server kill.
Before/after RAM pressure, swap and process tables are retained. Stop further
trials if swap grows, pressure worsens, RSS gaps occur or identity changes. There
is no external-process lock; the owner must prevent other clients/models during
startup and the request. Do not report missing peak memory as 0 or within budget.

Resolve the returned citation independently with `document_rag.py cite` using the
same manifest/index/scope and ID. Verify UTF-8 bytes at `[start_byte:end_byte]` in
the original file, compare the sentence, and compare with `source-only.json`.
Changed sources suppress the generated view **and the outer CLI evidence packet**;
private receipts still retain the originally supplied evidence for the audit.

For each case, record these distinct fields in a small private review note:

| Measure | Meaning |
| --- | --- |
| Native execution | Authorized local model actually ran, with disk/process/server logs and raw output; never inferred from a mock or alias alone. |
| Structural validity | JSON/envelope/stop/language contract passed; not correctness. |
| Citation resolution | Returned original ID maps to the retrieved, current in-scope byte span. |
| Verbatim support | Exact source sentence was copied; paraphrases remain unsupported. |
| Question relevance / factual correctness | Human inspection of whether the sentence answers this question and whether sources conflict/are incomplete; citation alone proves no entailment. |
| Wrong-but-cited / valid-looking wrong | Count as failures even if the narrow checker accepted them. |
| Abstention / no evidence / fallback | Record separately; no lexical match is not proof of absence. Safe fallback is useful but not native answer success. |
| Language | Score English and Norwegian separately; no translation competence is claimed. |
| Resources | Request latency, startup separately, available prompt/output tokens, sampled peaks/gaps and host swap/pressure. One/two cases do not establish p50/p95 performance. |

**GO for further study** requires a genuinely native useful direct answer, correct
original citation/verbatim support, human relevance review, complete receipts and
acceptable resources; obtain a fresh approval for Norwegian next. **REVISE** for
schema, retrieval, relevance, conflict, abstention or fallback problems, preserving
every failure. **STOP** for identity/source/authorization/resource violations or
unavailable measurements. No single successful answer establishes general accuracy,
production readiness or a changed historical experimental conclusion.
