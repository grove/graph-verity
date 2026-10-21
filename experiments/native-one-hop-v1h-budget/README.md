# V1h-budget registration — INCONCLUSIVE_REVISE

This separately named, **model-free** revision follows r3. It authorizes no
inference. The current task expressly prohibits live inference; earlier Qwen or
v1g permissions do not transfer. All successor observations are unattempted.

[registration.json](registration.json) binds source commit
`d485b9fcaf2de834d07788e8f15fc193b6cce664`, 76 exact source/dependency hashes,
the effective configuration, prompt/grammar, frozen contexts/messages/packets,
complete token budgets, inherited native/model/tokenizer/license identities and
registered Rust binary SHA-256
`16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.
[assets.json](assets.json) records fresh model-free rehashing of both native
checkpoints, retained Q4_K_M files, tokenizers/templates, pinned llama.cpp source
tree/executables and original licenses. No weights were loaded or downloaded.
[asset-verification.json](asset-verification.json) binds that receipt to this
registration. The freeze archive is append-only; do not reseal r3 or v1g.

## One factor, unchanged source information

Only the embedded BM25-v1 packet presentation changes: reversible ordered-column
schemas and repeated-string references. Every original value and field remains
recoverable with identical JSON serialization and key/list order. Reserved-tag
collisions fail closed. Primary graph/entity/predicate numeric tables and all
source data outside the packet are untouched. Packet bytes/IDs and exact
retrieval membership are retained; missing vocabulary is not restored.

Oracle messages, original v1e system prompt, GBNF, source, role/scope restrictions,
question schedule and Rust preview remain unchanged. The representation may
affect model interpretation; no semantic improvement is claimed. Status-rule
precedence, predicate definitions and alternative retrieval are excluded and
require separate ablations. Existing v1g design/execution registrations remain
unchanged and unrun.

Each model has two native sampling controls followed by 36 independent semantic
observations: two oracle repetitions, eleven controls plus six smokes in oracle,
then eleven controls plus six smokes in frozen BM25-v1. The exact schedule is in
the registration. Maximum 38 completion requests/model, no retries. Every
failure/rejection and unattempted denominator must be preserved. Known semantic
failures may continue; integrity, resource and authorization failures stop.
Decision is always **INCONCLUSIVE_REVISE**, even if all observations complete.

The 16,384 context, 512 output reserve, CPU four threads, zero GPU layers,
concurrency one, Q4_K_M, seed 7, temperature zero, thinking off, 300-second
deadlines, 24 GiB sampled process-tree RSS ceiling and original host gates are
unchanged. No current passing host-readiness claim is made.

## Exact budgets, no generation

The tokenization receipt inside [freeze.tar.gz](freeze.tar.gz) contains full
prompt bytes and token IDs, exact input/reserve/total/fit decisions, section
contributions, tokenizer/template hashes and package versions for all 38 prompts
per model. Original and columnar variants are measured separately. All 36
retained Qwen native parity records and ten historical Gemma records reproduce.
This is tokenizer/template work, not model loading; future native backend parity
is still mandatory.

| Model | Largest original input | Largest columnar input | Columnar plus 512 | Strict limit |
|---|---:|---:|---:|---:|
| Qwen3.5-9B | 18,926 | 14,019 | 14,531 | <16,384 |
| Gemma 4 12B | 20,353 | 14,703 | 15,215 | <16,384 |

Every proposed scheduled prompt fits. Original reverse-website retrieval exceeds
the limit for both tokenizers. [The investigation](../native-one-hop-v1h-investigation/README.md)
retains every observation's before/after budget and the source-bound failure
analysis. Source triples, raw model bytes, previous scores and r3 failures remain
unchanged; they are not silently reevaluated as independent truth.

## Fresh restoration and model-free checks

Do not extract over an existing directory. `mkdir` without `-p` deliberately
fails if the proposed destination exists; inspect it instead.

```sh
mkdir artifacts/v1h-budget &&
tar -xzf experiments/native-one-hop-v1h-budget/freeze.tar.gz -C artifacts/v1h-budget &&
.venv/bin/python tools/native_one_hop_v1h.py replay --freeze artifacts/v1h-budget
```

With the pinned local tokenizer assets, a fresh model-free recount is:

```sh
.venv/bin/python tools/native_one_hop_v1h.py budget --freeze artifacts/v1h-budget \
  --model qwen35 --out artifacts/v1h-budget-qwen-recount
```

The committed registration/source must match, including the original registered
Rust binary. On another platform, inspect archive identities and run portable
tests without executing a substitute registered binary. Never rebuild/reseal to
bypass an identity mismatch. The original source commit and exact dependency
hashes are retained; later report-only commits do not alter those sources.

## Proposed command — separate explicit authorization required

The destination below is reserved as a fresh proposal and was not created by
this task. Neither this command text nor registration permits inference.

```sh
.venv/bin/python tools/native_one_hop_v1h.py run \
  --freeze artifacts/v1h-budget --model qwen35 --allow-inference \
  --out artifacts/issue83-v1h-budget-qwen35-first
```

Before model loading the runner checks committed registration/source/binary,
fresh complete assets, every selected-model prompt's exact token identities and
fit, native character GBNF controls, and a fresh original host gate (age <=60 s).
Each completion also requires native template/token parity matching the pre-load
receipt. Concurrency and per-freeze/model no-retry ledger apply. Original raw
bytes/SSE, prompts, resource samples, native timing, Rust preview and all stops
remain retained. Only `nl-ask-preview` is called; RDF execution and #75 approval
or execution routes are absent.

Keep independent human review pending until real reviewers complete it. Gemma
requires its own exact command and separate explicit approval after Qwen review
and passing shared integrity checks. Do not run v1g, automatically retry, merge,
close #83, change thresholds, download models or connect #75.
