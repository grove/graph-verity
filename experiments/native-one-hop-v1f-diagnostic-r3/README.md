# #83 adapter configuration repair — INCONCLUSIVE_REVISE

This is an engineering repair and separately registered model-free successor.
It authorizes no inference, model-generated RDF execution, #75 integration or
issue closure. All 72 successor diagnostic observations remain unattempted;
semantic numerators are null. No model quality or semantic-readiness conclusion
follows from passing these checks.

## Baseline and correction

PR #91 merged at `a60bb8aaf653c77fe29682c0f73f46fc8790b5ab`, with its `test`
check successful on head `6de38cbc724e12420940107e1502adbff622d087`.
This branch starts there, including merged #90's v1g harness. Neither historical
PR was modified. Issue #83 remains open.

The old direct-script entry point selected v1f in `__main__`. The helper imported
`native_one_hop`, creating another namespace with default v1c configuration.
Its frozen-configuration rejection was correct. The new entry point delegates
to the named module's `main()`, so CLI selection and the helper use the same
adapter. No aliasing or synchronization is involved. Historical CLI selections
and import-based use retain their behavior. The helper and all integrity,
resource, source, binary, authorization and preview guards are unchanged.

The production change is limited to named-module dispatch and accepting the new
revision identifier. The new config differs from v1f only in `version`. New
regressions cover both entry points, the selected helper, historical variants,
config/source/packet/binary tampering, opt-in, CI denial and execution authority.
The two historical fingerprint tests use the exact original Git blobs for files
changed by this repair, following the existing v1d/v1e test pattern. They still
verify historical archives and hashes; current-source tests remain active.

## Corrected registration

[registration.json](registration.json) binds source commit
`eda247679a6b10fa2ef4f5a21ece12d0f0c53213`, 68 frozen source inputs,
the full effective config, unchanged native asset/executable pins, environment,
and [freeze.tar.gz](freeze.tar.gz). No native model runtime or model asset was loaded
to create this registration. The Rust CLI performed only model-free packet
construction and strict preview validation.

| Identity | SHA-256 |
|---|---|
| Corrected adapter | `960caae668e1101ed98b86acec0a700ca21aefc017d5af90d99366b6490101ae` |
| Unchanged helper | `f5e3ca52e5bbf03bc8350966b8f7fe5c2c0c103210fc44781e59f1aff264ac0a` |
| Rust binary | `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db` |
| Freeze inventory | `82bf3f4fa6f0e6ffcf5d664880d2b8bc98369b67c903c1cc8a9a176867de0c3d` |
| Freeze archive | `e21fa724755513425c4b676d2e830b37a1e7f17aca19b990b1e5a331a0091538` |

The 137 payload files other than `freeze.json` and `checksums.json` match the
original v1f freeze byte for byte. These include all contexts, packets, questions,
catalog, budget, index manifest and operator fixtures. Settings, prompts, grammar,
conditions, schedules and thresholds are unchanged. Native model/runtime pins
are inherited from the immutable #74 asset receipt; this is not a fresh asset
availability check. The unchanged runner requires fresh asset hashing and an
original passing host gate before any model loading.

## Model-free verification

The exact commands, exit codes and captured results are retained with this report.
The complete pipeline **passed** on commit
`e58024f56bbf0d820c8b6dce86832b3c4172be6f` (repair and registration; the later
commit adds this report only). [verification.json](verification.json) records
every pipeline command and its expected result. [validation.json](validation.json)
records supplementary commands and the corrected exploratory failures;
[validation-logs.tar.gz](validation-logs.tar.gz) contains complete captured logs.

| Check | Result |
|---|---|
| Current Python regression suite | 274 passed, no failures or skips |
| Frozen pilot Python suite | 15 passed |
| New configuration regressions | 8 passed, also included in the current suite |
| Rust workspace tests | 100 passed |
| Rust formatting and Clippy with warnings denied | Passed |
| Required browser checks, including saved-review rehearsal | Passed |
| Frozen NL Ask/vocabulary and raw-byte replays | Passed |
| Source canaries, references, schema, catalog, dataset/gold checks | Passed |
| Offline binary/example build | Passed |
| Historical identities and payload comparison | 801 hashes and 137 payload files passed |

No configured model-free checks were unavailable. Native inference and fresh
model-asset availability/host gates were deliberately outside this authorization.
The complete CI entry point is:

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

The workflow's build prerequisite also passed offline:

```sh
cargo build --locked --offline --bins --examples
```

The focused new suite is:

```sh
.venv/bin/python -m unittest discover -s tools -p test_native_one_hop_configuration.py -v
```

The historical replay used an isolated `git archive` export of baseline
`a60bb8a`, the pinned existing Rust binary and Python dependencies, then ran both
unchanged shell blocks from PR #91's report. It replayed both original raw
sampling responses, reproduced the exact configuration error, and regenerated
the analyzer JSON/Markdown byte for byte. The first auxiliary comparison used an
incorrect generated Markdown filename after both commands had passed; the
corrected comparison passed. No evidence bytes were changed.

An exploratory targeted run during implementation had a sandbox `ps` denial and
two v1g failures while the source/fingerprint tests were being updated. The
stable-source full verification uses host execution for process inspection and
browser checks. No guard was disabled to obtain a passing result.

## Preservation and next gate

All 801 historical file identities pass. A baseline diff verifies no changes
under `reports`, `studies`, the v1g experiment, original v1f config/audit, diagnostic
helper or v1g implementation. The old v1f and v1g execution freezes reject this
changed adapter source; historical replay uses their original source. No
registration, archived failure, raw bytes, denominator or comparison condition
was refreshed to accept the repair.
[preservation.json](preservation.json) records the comparison and exact baseline
diff command; [checksums.json](checksums.json) binds this report's files.

After passing model-free verification, this revision is technically ready to
request a **separately authorized, host-gated successor semantic smoke**. Remaining
gates are fresh explicit authorization naming revision/model/destinations/schedule,
fresh asset/source/binary checks and the original host/resource gates. A different
identity requires another registration before generation. Keep the two native
sampling controls and registered NO/EN forward/reverse and safety observations,
all failures and unattempted denominators. Do not retry or rewrite the old attempt.
There was no Qwen/Gemma/v1g inference, model download/update, sealed holdout access,
model-generated RDF execution, threshold change or #75 integration in this repair.
