# First native document-RAG trial: proposed CPU baseline

Follow-up for #122, parent #71, after merged #123, #124 and #125. The first
one-shot native trial has completed and remains historically rejected. This
change does not start a server, execute inference, create owner authorization,
or alter its private evidence. The later accepted native English and Norwegian
direct answers are separate trials and remain unchanged. Keep #122 open and
preserve the historical `INCONCLUSIVE_REVISE` conclusion.

## Prospective response normalization

The first authorized English response returned the correct original sentence
and citation in valid JSON, but omitted the required `language` field. The
adapter rejected it as `Unexpected generated fields` and served the source-only
fallback. For future runs, the document-only answer validator may supply that
one field only when the JSON object has exactly `version`, `status`, `answer`
and `citation_id`, with the supported version and `status: answer`. It copies
the request language from the already validated evidence packet, then runs the
complete existing citation, source-version, verbatim-quote, language and
relevance checks. Wrong language values, any other missing or unexpected
fields, malformed JSON, unsupported claims, invalid or stale citations, and
model abstention continue to produce the source-only fallback.

The receipt records whether normalization was applied, the supplied field and
its packet source, and whether complete validation passed or why it rejected
the candidate. The private `response.bin` remains the raw model response; a
saved-output replay is labeled `checked_saved_output_only` with
`model_invoked: false` and does not rewrite the historical receipt. The system
prompt is unchanged. Any future native run still needs a fresh model
registration, current source packet, exact request hash and host admission, and
a new unconsumed one-shot authorization with a future expiry.

This is a single document-answer trial, without graph execution.

## Deterministic grounding-risk gate

A source-exact quote and a resolvable d: citation can still be irrelevant,
ambiguous or contradicted. The model-free gate runs on the current retrieved
packet before generation authorization is read or consumed. It recognizes:

- Different identifier values attached to the same named trial and identifier
  attribute in the selected passages. The current CPU example is
  RAG-CPU-01 versus RAG-CPU-99; both original citations are retained for
  source-only review. An identifier question without a subject is withheld when
  identifier values are present.
- An incomplete packet for that identifier question. If retrieval is clipped
  and only one side is visible, the result is UNDETERMINED with a coverage
  reason; the gate does not claim to have found a conflict.
- A requested startup latency only when a retrieved sentence contains a
  startup/latency reference and a numeric value with a time unit. Startup text
  without a measurement is insufficient support.
- Explicit count/all-document requests and broad Norwegian summary/conclusion
  requests. A narrow instruction-risk pattern blocks a question about a note
  when the retrieved text combines “ignore previous instructions” with a
  fabricated-citation request; it also blocks that attack when its sentence
  matches all direct question terms. Ordinary instruction documentation is
  not rejected by that pattern.
- A simple direct question only when every meaningful question term appears in
  one retrieved source sentence. The prompt receives those exact sentence
  excerpts; the complete packet remains available for source-only fallback.

Other answer forms, clipped retrieval, missing measurements and unclear
question/evidence links return inspectable original passages with an honest
reason, or no_evidence when retrieval found no passages. No fallback claims
that an unreturned fact is false or absent. Existing exact-quote, citation,
language, scope, version, control-token, authentication, stale-source and
resource checks remain in force. CLEAR_SUPPORTED_CASE only admits the existing
quote/citation validator; it does not prove semantic entailment.

The development replay blocks the ambiguous identifier, the visible
CPU-identifier conflict, the missing startup measurement, the targeted
instruction question, counting and synthesis. English and Norwegian direct
development quotes remain saved-output-only passes. Lexical overlap and these
finite patterns cannot establish general relevance, detect every conflict or
make prompt injection impossible; independent human relevance review is still
required. Any native negative-case probe needs separate fresh owner
authorization after this change is reviewed and merged.

The [per-case model-free replay](issue-122-grounding-risk-review.md) records all
14 questions, selected original citations, source-only baselines, prior
validator outcomes, detected risks and expected safe results.

## Candidate identity and verified assets

[Machine-readable proposal](../configs/local-document-rag-native-v1.proposal.json)
is deliberately **not** an executable registration or authorization.
Published metadata was inspected on 2026-10-24; retained local asset receipts now
record byte verification for the pinned model, tokenizer and template:

| Item | Verified published metadata / remaining limitation |
| --- | --- |
| Original | [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/tree/cdbee75f17c01a7cc42f958dc650907174af0554), revision `cdbee75f17c01a7cc42f958dc650907174af0554`; 4B instruction checkpoint, non-thinking only; no `enable_thinking` switch or `<think>` output expected ([model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)). |
| License | Original [Apache-2.0 license](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/LICENSE) permits local use subject to its terms. GGUF publisher also declares Apache-2.0. Retain licenses/notices with acquired assets. |
| Quantization | [Unsloth file at immutable revision](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/blob/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf): `a06e946bb6b655725eafa393f4a9745d460374c9`, `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, 2,497,281,120 bytes; SHA-256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`. The local asset receipt records byte verification against this SHA-256. |
| Template/tokenizer | Official `tokenizer_config.json` SHA-256 `a62ff0a2472a0fa1b8eaabcb57c59b58afa42a22831dc141400b6e0cf2b65ce3`, `tokenizer.json` SHA-256 `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`, and extracted `chat.jinja` SHA-256 `64f85b198065d0fba2a81f37e10ed68161ce2c19a754c7100e67e0ca2ee9c326`; retained asset receipts record local hash matches. |
| Requirements | [Official tokenizer config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/tokenizer_config.json) uses Qwen2Tokenizer, role delimiters `<\|im_start\|>` / `<\|im_end\|>`, assistant generation prefix, EOS `<\|im_end\|>`, no automatic BOS; apply the official template, without tools. Native Transformers examples require Qwen3 support (>=4.51.0). This is separate from llama.cpp support. |
| Runtime | llama.cpp source is pinned to `d327bf1f0780f87b8c01b367b61853b0c291d7c4`; the built `llama-server` SHA-256 is `197566eb62ab049eb9625c8e99c676875ee6f2aa1c61e59bc1a57af1b095caf1`. The exact binary help and source were checked for this security change. The code now requires a fresh version-3 registration and secure restart. |

Native BF16 safetensors and lossy quantized GGUF are different bytes and
representations. A matching publisher filename does not establish the conversion's
original checkpoint revision, tokenizer equivalence or Norwegian quality. Inspect
the acquired GGUF architecture, quantization, special token IDs and embedded
metadata with the pinned runtime's GGUF inspection tooling; compare to the pinned
official config. Retain that private inspection and build log. The explicit
`--chat-template-file` selects the official extracted template, but **does not
replace or validate GGUF tokenizer tensors/metadata**. A non-generative audit of
the pinned assets and llama.cpp commit `d327bf1f0780f87b8c01b367b61853b0c291d7c4`
found that the official and embedded templates produce byte-identical prompts
and token IDs for this adapter's system-plus-user request path (including its
assistant generation prefix, with no tools or assistant history). The embedded
template additionally handles assistant reasoning and history after the last
user message; that branch is not used by this path. The official override is
accepted by the pinned runtime. This is a narrow exception for the distinct
template hashes only; retain and verify both identities, and stop on any other
tokenizer, model, template-rendering or runtime discrepancy.

The same audit found that llama.cpp reparses the rendered prompt with special
token recognition enabled, so a special-token spelling inside untrusted question
or document text becomes a control token even when JSON-quoted. The adapter now
fails closed if question or retrieved passage text contains one of the pinned
Qwen tokenizer's special-token spellings. Keep that guard for this supported
path; rerun the non-generative audit if the tokenizer, GGUF, runtime or request
format changes. This limitation may
reject source text containing those spellings, but prevents it from changing
message boundaries or entering thinking/tool control paths.

Memory planning is an estimate, not a measurement: the file is about 2.33 GiB.
From the [native config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75f17c01a7cc42f958dc650907174af0554/config.json),
a full 8192-token F16 K+V cache is approximately
`2 * 36 layers * 8 KV heads * 128 head dimension * 2 bytes * 8192 = 1.125 GiB`.
Weights plus KV alone are about 3.45 GiB; allocator, compute buffers, mmap and OS
memory add more. Actual llama.cpp settings and RSS must be measured. An 8 GiB
sampled **server+client process-tree** ceiling leaves room on 32 GiB; it is not an
OS memory reservation or a guarantee against a short spike.

## Secure local server boundary

The pinned server's `--help` and source at
`d327bf1f0780f87b8c01b367b61853b0c291d7c4` confirm `--api-key-file`,
`--cors-origins`, `--cors-methods`, `--cors-headers`,
`--no-cors-credentials` and `--no-webui`. The version-3 runtime registration
binds the credential path and file hash. It accepts one URL-safe key in an
operator-owned private directory, with a private regular file, restrictive
mode, no symlink and matching SHA-256. Rotating or changing the key requires a
new registration and a server restart.

Choose an operator-controlled private directory outside the repository, create
it with mode 0700, and generate the key there once. This writes the secret
directly to a mode-0600 file; do not print it or copy it into the registration,
command line, prompt, evidence packet, request body or logs.

```sh
umask 077
set -C
CREDENTIAL_DIR=/absolute/operator/private/credentials
mkdir -m 700 "$CREDENTIAL_DIR"
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > "$CREDENTIAL_DIR/server-api-key.txt"
chmod 600 "$CREDENTIAL_DIR/server-api-key.txt"
export API_KEY_PATH="$CREDENTIAL_DIR/server-api-key.txt"
```

The generated server command keeps only that file path in argv and adds
`--api-key-file`, `--cors-origins http://127.0.0.1:8095`,
`--cors-methods GET,POST,OPTIONS`, `--cors-headers Authorization,Content-Type`,
`--no-cors-credentials`, `--no-webui`, `--no-agent` and `--log-verbosity 3`.
This allows one exact same-origin value and no browser credentials. The UI and
agent/MCP capabilities remain disabled. Verbosity 3 suppresses trace messages;
the pinned server's trace log includes the key's last four characters. The
Python adapter reads and validates the file immediately before
transport, sends `Authorization: Bearer ...` as an HTTP header, and keeps the
header out of JSON requests and retained receipts. If an endpoint echoes the
secret, the adapter redacts it from retained response bytes and error messages.
The registration records the path and SHA-256, never the key itself. Its hash
also binds the one-shot authorization through the registration digest.

The pinned middleware leaves `GET /health` public and protects `GET /v1/models`
and all generation routes. `/v1/models` is a non-generative authentication
probe. `OPTIONS` is handled before API-key validation. Its CORS response always
uses the configured exact origin; it does not reflect an unlisted Origin.
Therefore a browser preflight using `https://example.invalid` must receive
`Access-Control-Allow-Origin: http://127.0.0.1:8095`, never the supplied origin;
the browser will deny the cross-origin request. CORS does not authenticate
local processes, so the API key remains required independently.

Before stopping any old process, compare its observed executable, full command,
start time and owned listener with the retained startup receipt. Compare the
resource monitor identity and ownership as well. Only when every field matches,
send `TERM` to those exact PIDs, then confirm the listener is gone. If a PID,
command, start identity or listener is missing or differs, do not signal it.
Historical PIDs 64792 and 67725 are observations only and must be rechecked.
Keep the original startup and shutdown receipts unchanged; write any new
observations to new private files. For the previously reported PIDs, first run
read-only checks and compare the output field-by-field with the retained
startup receipt:

```sh
OLD_SERVER_PID=64792
OLD_MONITOR_PID=67725
ps -ww -p "$OLD_SERVER_PID","$OLD_MONITOR_PID" -o pid=,ppid=,lstart=,command=
lsof -nP -a -p "$OLD_SERVER_PID" -iTCP:8095 -sTCP:LISTEN -Fn
```

Only if both process identities and the listener ownership match that receipt,
gracefully signal the verified PIDs and verify shutdown:

```sh
kill -TERM "$OLD_SERVER_PID" "$OLD_MONITOR_PID"
ps -p "$OLD_SERVER_PID","$OLD_MONITOR_PID" -o pid=,lstart=,command=
lsof -nP -iTCP:8095 -sTCP:LISTEN
```

The final `ps` and `lsof` output must show no original process and no listener.
Do not signal a reused PID or a server whose receipt cannot be matched.

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

## After this security change is reviewed and merged: secure server startup

**Do not run these steps during this PR.** After merge, reuse only the already
verified private assets and pinned runtime below, rechecking their identities.
Server startup and non-generative verification are separate from inference;
every completion still requires a fresh one-shot owner authorization.
Historical Qwen3.5/Gemma runs confer no authority.

1. Reverify the existing immutable GGUF, tokenizer/config/license assets and
   extracted `chat.jinja` against the proposal and retained asset receipts. Do
   not download from floating `main`, use `-hf` or enable automatic downloads.
2. Reverify llama.cpp revision `d327bf1f0780f87b8c01b367b61853b0c291d7c4`,
   server SHA-256 `197566eb62ab049eb9625c8e99c676875ee6f2aa1c61e59bc1a57af1b095caf1`,
   build receipt and actual `--help` output. The runtime is CPU-only, with
   Metal/BLAS/Accelerate/CURL off, one model and one inference slot.
3. Inspect `sysctl -n machdep.cpu.brand_string hw.memsize`, `vm_stat`,
   `sysctl vm.swapusage`, `memory_pressure -Q`, `uptime`, and
   `ps -axo pid,ppid,pcpu,rss,comm`. Check AC power and thermal state with
   `pmset -g batt` and `pmset -g therm`. Stop/avoid competing generative,
   embedding and GNN work through the owner's normal process controls.
   Admission requires M1 Pro/32 GiB, >=40% memory free, <=1024 MiB swap,
   load/CPU <=0.75, measured server RSS <=8 GiB and no recognized competing
   model processes. Missing metrics block. Generic Python processes cannot be
   reliably classified: the owner must explicitly attest quiescence.
4. Create the API-key file as described above, then export `ASSET_DIR` for the
   private directory containing the verified GGUF,
   `tokenizer_config.json`, `tokenizer.json` and extracted `chat.jinja`. Export
   `API_KEY_PATH`, `RUNTIME_PATH` and `RUNTIME_REVISION` from the independently
   verified assets. The following creates an **unapproved draft** and prints the
   full command; it downloads/loads no weights and starts no server.

```sh
PYTHONPATH=tools python3 - "$TRIAL_DIR" <<'PY'
import json, os, shlex, sys
from pathlib import Path
import local_cited_generation as g
p = Path(sys.argv[1]).resolve()
a = Path(os.environ['ASSET_DIR']).resolve()
api_key_path = Path(os.environ['API_KEY_PATH'])
proposal = json.load(open('configs/local-document-rag-native-v1.proposal.json'))
pid = int(os.environ.get('SERVER_PID', '2'))  # unusable draft placeholder
r = dict(version=3, backend=g.BACKEND, host='127.0.0.1', port=8095,
         model_name='verity-qwen3-4b-2507-q4km', cpu_threads=4, gpu_layers=0,
         context_tokens=8192, max_output_tokens=256, timeout_seconds=300,
         temperature=0, seed=7, model_revision=proposal['model']['revision'],
         gguf_revision=proposal['gguf']['revision'],
         runtime_revision=os.environ['RUNTIME_REVISION'], server_pid=pid,
         server_started='PENDING_START' if pid == 2 else
             g._command(['ps', '-p', str(pid), '-o', 'lstart=']),
         system_prompt_sha256=g.documents.sha(g.SYSTEM_INSTRUCTION.encode()),
         api_key_path=str(api_key_path),
         api_key_sha256=g.documents.sha(api_key_path.read_bytes()),
         cors_origins=g.CORS_ORIGINS, cors_methods=g.CORS_METHODS,
         cors_headers=g.CORS_HEADERS, cors_credentials=False, webui_enabled=False,
         log_verbosity=g.LOG_VERBOSITY)
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
All earlier version-2 registrations are stale because they omit authentication
and restrictive CORS. Keep the draft, build receipt and all assets immutable.

Its shape is:

```text
/absolute/llama-server --model /absolute/Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
 --host 127.0.0.1 --port 8095 --alias verity-qwen3-4b-2507-q4km \
 --threads 4 --threads-batch 4 --n-gpu-layers 0 --ctx-size 8192 \
 --parallel 1 --n-predict 256 --no-warmup --jinja \
 --chat-template-file /absolute/chat.jinja \
 --api-key-file /absolute/private/server-api-key.txt \
 --cors-origins http://127.0.0.1:8095 \
 --cors-methods GET,POST,OPTIONS --cors-headers Authorization,Content-Type \
 --no-cors-credentials --no-webui --no-agent --log-verbosity 3
```

Before launch, unset `LLAMA_API_KEY`, `LLAMA_ARG_API_KEY_FILE`,
`LLAMA_ARG_HOST`, `LLAMA_ARG_PORT`, `LLAMA_ARG_API_PREFIX`,
`LLAMA_ARG_STATIC_PATH`,
`LLAMA_ARG_CORS_ORIGINS`, `LLAMA_ARG_CORS_METHODS`, `LLAMA_ARG_CORS_HEADERS`,
`LLAMA_ARG_CORS_CREDENTIALS`, `LLAMA_ARG_UI`, `LLAMA_ARG_AGENT`,
`LLAMA_ARG_TOOLS`, `LLAMA_ARG_TOOLS_RUNTIME`, `LLAMA_ARG_MCP_SERVERS_CONFIG`,
`LLAMA_ARG_MCP_SERVERS_JSON`, `LLAMA_ARG_UI_MCP_PROXY`, `LLAMA_ARG_CONNECT` and
`LLAMA_ARG_LOG_VERBOSITY`.
The CLI explicitly selects the key file, allowlist and disabled UI/agent settings;
clearing these environment overrides prevents extra keys or hidden capabilities.

```sh
unset LLAMA_API_KEY LLAMA_ARG_API_KEY_FILE LLAMA_ARG_HOST LLAMA_ARG_PORT \
  LLAMA_ARG_API_PREFIX LLAMA_ARG_STATIC_PATH LLAMA_ARG_CORS_ORIGINS \
  LLAMA_ARG_CORS_METHODS LLAMA_ARG_CORS_HEADERS LLAMA_ARG_CORS_CREDENTIALS \
  LLAMA_ARG_UI LLAMA_ARG_AGENT LLAMA_ARG_TOOLS LLAMA_ARG_TOOLS_RUNTIME \
  LLAMA_ARG_MCP_SERVERS_CONFIG LLAMA_ARG_MCP_SERVERS_JSON \
  LLAMA_ARG_UI_MCP_PROXY LLAMA_ARG_CONNECT LLAMA_ARG_LOG_VERBOSITY
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 \
  OPENBLAS_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4
```

After merge, start that exact command under `/usr/bin/time -l`, redirecting
stdout/stderr to **new private** files. Set offline environment flags
(`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `OMP_NUM_THREADS=4`,
`OPENBLAS_NUM_THREADS=4`, `VECLIB_MAXIMUM_THREADS=4`), and ensure no external
clients can use the endpoint. `--no-warmup` avoids unregistered warmup
generation. Allow **at most 300 seconds for startup**, watching memory; if
`/health` is not ready, gracefully stop the verified owned server and record
failure without a completion. Five minutes is a conservative first inspection
window for cold CPU loading, not a speed claim. Keep launch/startup `/usr/bin/time`
receipts: the adapter samples only its request window. No retries or fallback
model launches.

Verify `ps -ww -p PID -o command=`, `ps -p PID -o lstart=`,
`lsof -nP -a -p PID -iTCP:8095 -sTCP:LISTEN -Fn`, and
`lsof -p PID` for executable/model/library mappings. Confirm server startup logs
report the expected architecture, tokenizer, template, context, CPU and GPU layers.
The adapter checks the exact process command/start and loopback listener, and
hashes on-disk files; the owner must still compare the mapped executable/model
and logs. A model alias, PID or disk hash alone cannot prove the loaded tensors.
Stop on disagreement. There is a time-of-check race with external process changes.

### Non-generative server verification

After recording the new PID and `ps` start identity, create a fresh version-3
registration. Do not reuse the old registration, even if the PID appears
unchanged. Then run only these non-generative probes; they do not create or
consume an inference authorization:

```sh
PYTHONPATH=tools python3 - "$TRIAL_DIR" <<'PY'
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import local_cited_generation as g

p = Path(sys.argv[1]).resolve()
r = g.load_registration(p / 'registration.json')
key = g._read_api_key(r)
base = 'http://127.0.0.1:8095'

def probe(path, *, method='GET', headers=None):
    request = Request(base + path, method=method, headers=headers or {})
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        return error.code, error.headers
    with response:
        return response.status, response.headers

assert probe('/health')[0] == 200
assert probe('/v1/models')[0] == 401
status, _ = probe('/v1/models', headers={'Authorization': 'Bearer ' + key})
assert status == 200
status, headers = probe('/v1/models', method='OPTIONS', headers={
    'Origin': 'https://example.invalid',
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'authorization',
})
assert status == 200
assert headers.get('Access-Control-Allow-Origin') == g.CORS_ORIGINS
assert headers.get('Access-Control-Allow-Origin') != 'https://example.invalid'
print('health=200, unauthenticated_models=401, authenticated_models=200, disallowed_origin_not_reflected')
PY
```

The pinned implementation makes `/health` public, requires the key for
`/v1/models`, and handles `OPTIONS` without auth. The CORS check inspects the
fixed allowlist value returned for an unlisted origin; browser access is denied
because the response does not authorize that origin. Never send an unauthenticated
`POST` to a completion route, even with a malformed body. Confirm the listener
still belongs only to this PID at `127.0.0.1:8095`, and retain the probe result
privately without printing or storing the key.

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
