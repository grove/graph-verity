# First native predicate diagnostics evidence — INCONCLUSIVE_REVISE

Refs #83; execution registration from merged PR #104. Exactly one authorized
native Qwen3.5-9B command invocation ended with exit 1: **78 requests attempted,
77 completed, one timeout, 48 unattempted, zero retries**. The registration is
consumed and cannot be resumed. #83 stays open, #75 integration stays disabled,
and independent human semantic review remains deferred. No automatic merge.

The owner authorized reviewed commit
`58faea4c3a14c1d763ce28166b0a261cad16ec7c` and registration SHA-256
`6ff9ca9824d62dc5f7457e142b308039f7ff033480b9dc871c22573892319e65`.
Both GitHub CI runs passed for that exact commit. Execution used merge commit
`d4f1fb8a3b178f0f8293e3ec2610de2eb7a1d37f`, whose tree is identical to the
authorized revision. The registration pins runner source commit
`169ae6305245b0cab381462aeb506f905ff5730c` and the original archive
`e219adf9ddaf721c65b69c2e1c5a7ad63d1e6dca464a6f1b4ea067fbdb9b670b`.
The full owner request and subsequent **“Try again now.”** are retained in the
archive's authorization record. The sole native command was:

```sh
.venv/bin/python tools/predicate_diagnostics_native.py run --allow-inference
```

The initial separate read-only host preflight blocked on 2,655.06 MiB swap
(maximum 1,024) and 37% free memory (minimum 40). No command was invoked and no
attempt was consumed. After the owner's follow-up, all identities were verified
again; the separate host gate passed with 997.81 MiB swap and 76% free memory.
The runner's own fresh gate passed with 665.75 MiB swap and 76% free memory.
Both preflights, all host checks and the exclusive attempt ledger are preserved.
No thresholds, runtime, prompts, references, source metadata or compiler changed.

## Complete accounting

| Schedule | Scheduled | Attempted | Completed | Fatal failure | Unattempted |
|---|---:|---:|---:|---:|---:|
| Native sampling controls | 2 | 2 | 2 | 0 | 0 |
| Identical construction repeats | 2 | 2 | 2 | 0 | 0 |
| Explicit-IRI construction | 60 | 60 | 60 | 0 | 0 |
| Natural language, no metadata | 31 | 7 | 7 | 0 | 24 |
| Natural language, metadata | 31 | 7 | 6 | 1 | 24 |
| **Total** | **126** | **78** | **77** | **1** | **48** |

`eva-07-metadata`, request 78, failed with `TimeoutError: timed out`. Its
**236 original bytes** and nonterminal SSE remain unchanged. The fragment
contains a partial clarification object, but it is incomplete JSON: completed
model status, plan fields and reference agreement remain **null**. Raw-fragment
measurements and its strict Rust rejection are retained separately. All 48
later requests retain their original identities and null missing outcomes.

The retained server log records 285.88 seconds of prompt processing before
generation on the failed request. Its observation took 303.762 seconds including
work outside the unchanged 300-second completion deadline. No terminal response
was received; the owned runtime was stopped and no request was retried.

## Construction fidelity and compiler compatibility

All 60 construction probes completed. **49/60** match status and all five
mechanical reference fields. Every witnessed path matches; all 11 disagreements
are empty paths. This measures explicit request-to-plan fidelity, independently
of natural-language predicate meaning and human semantic correctness.

| Construction stratum | Scheduled/completed | All-field matches |
|---|---:|---:|
| Forward, witnessed | 17 | 17 |
| Forward, empty path | 17 | 15 |
| Reverse, witnessed | 9 | 9 |
| Reverse, empty path | 17 | 8 |
| **Forward total** | **34** | **32** |
| **Reverse total** | **26** | **17** |

There are 52 actual candidates and eight model-origin `unsupported` responses.
Among actual candidates, three choose forward for a reverse request:
`explicit-010`, `explicit-032`, `explicit-038`; their other four fields match.
Across the full 60-case denominator, start/predicate/graph/output each match
52 times and direction matches 49 times. Abstentions have no actual plan fields.
All eight abstentions and every individual field remain in [analysis.json](analysis.json).

Rust accepts 57 actual outputs, including accepted abstention statuses and
wrong-direction plans. It rejects three **field-matching** reverse candidates:
`explicit-013`, `explicit-020`, `explicit-028`. These are anticipated compiler
range-check incompatibilities, not failed model field construction. All ten
original incompatible reverse empty-path references remain in the denominator:

| Explicit ID | Actual output | Field match | Rust result for actual output |
|---|---|---|---|
| 003 | unsupported | no | accepted status |
| 006 | unsupported | no | accepted status |
| 013 | correct reverse candidate | yes | rejected |
| 020 | correct reverse candidate | yes | rejected |
| 028 | correct reverse candidate | yes | rejected |
| 035 | unsupported | no | accepted status |
| 038 | wrong forward candidate | no | accepted forward plan |
| 042 | unsupported | no | accepted status |
| 049 | unsupported | no | accepted status |
| 056 | unsupported | no | accepted status |

The two repeats produce identical prompt/request bytes, response bytes,
rationales and five-field plans. Both agree with their construction reference.

## Incomplete metadata comparison

Only **6/31 pairs** have completed outcomes in both arms. On those same six
identities, each arm matches three exposed references. `eva-01` loses reference
agreement with metadata; `eva-04` gains it; the other four pair deltas are zero.
The net paired count change is zero. This incomplete comparison establishes no
metadata superiority or irrelevance.

| Complete pair | No metadata | Metadata | Reference-count delta |
|---|---|---|---:|
| eva-01 | matching candidate | clarification | -1 |
| eva-02 | matching candidate | matching candidate | 0 |
| eva-03 | clarification | unsupported | 0 |
| eva-04 | clarification | matching candidate | +1 |
| eva-05 | clarification | clarification | 0 |
| eva-06 | matching candidate | matching candidate | 0 |

| Arm | Scheduled | Completed | Reference matches among completed | Missing |
|---|---:|---:|---:|---:|
| No metadata | 31 | 7 | 3 | 24 |
| Metadata | 31 | 6 | 3 | 25 |

Missing rows are not scored as either successes or semantic failures. On the
six complete forward pairs, start/predicate/graph/direction/output each match
three times in each arm. On `eva-07`, no-metadata emits clarification; metadata
times out. There is no completed metadata reverse observation or paired reverse
comparison. All later reverse probes, genuine clarification/unsupported controls,
private/write controls and both final explicit source-injection probes remain
unattempted. They must not be reported as passed live controls.

The first five complete pairs have archived target-property meanings and each
arm matches two references there. The sixth pair has no mapped target meaning,
produces identical bytes in both arms and matches the old rdfs:label reference.
Its unchanged source audit still marks “every stored label” as underdetermined
between label relations. The analysis retains target-coverage and direction
strata, full scheduled counts and paired-completed counts. `target_metadata`
means availability in the retained source adapter; construction prompts never
receive metadata. No graph-qualified numeric membership or reference changed.

## Source and rationale investigation

Every retained complete rationale was inspected against its frozen context;
29 source-bound investigator notes retain exact rationale text, raw SHA-256,
context paths and original reference fields. The notes are coding-agent source
inspection, **not independent human review**. Examples include:

- `explicit-042` assigns predicate 1011 to graph 1 and denies its presence in
  graph 2; the supplied bindings are 1011/rdf:type in graph 2 and 1007/rdf:type
  in graph 1. `explicit-056` falsely denies supplied graph-2 prefLabel/1015.
- `explicit-043` and `explicit-044` describe reverse lookup while selecting
  correct forward fields. Other rationales say forward returns subjects, or
  name concrete answers despite the interpretation-only instruction.
- `eva-03-no_metadata` calls P571 date of birth and P1448 date of death. Their
  retained meanings are inception and official name. Those meanings are absent
  from that arm, so this is an **archive comparison**, not a contradiction with
  definitions supplied to that prompt. With metadata, P571 is recognized but
  the omitted literal answer is treated as missing plan vocabulary.
- `eva-04-metadata` calls website objects literals; supplied usage is
  102 → entity 103, an IRI. `eva-05-metadata` identifies the intended official-name
  predicate then clarifies. Plural-wording objections and absent meanings are
  recorded separately from actual missing numeric IDs.

Nine complete rationales reach exactly 512 characters, several ending
mid-phrase; their JSON/SSE responses are terminal and have no output-limit or
transport truncation. The failed request's incomplete JSON is a separate
transport/runtime failure. No response, rationale, source or reference is repaired.

## Runtime, preservation and reproduction

The original CPU-only four-thread, zero-GPU, one-slot runtime, temperature 0,
seed 7, 16,384 context, 512 output reserve and zero-retry limits are unchanged.
All 126 pre-load tokenizer receipts reproduce; all 78 attempted messages pass
fresh native prompt/token parity. All 12 model-free grammar controls and both
native sampling controls pass. Completed semantic/repeat outputs pass native
GBNF, independently of their reference disagreements. The failed request has
no completed GBNF observation.

Maximum attempted input is 11,006 tokens + 512 reserve = 11,518 < 16,384;
the full registered schedule's maximum is 11,525 including reserve. All 39,960
RSS samples are retained; peak sampled process-tree RSS is 13,458,928 KiB
(12.835 GiB), below 24 GiB, with no monitor error. Completed observation latency
has median 103.310 seconds and maximum 285.788 seconds. Host/cache effects are
not isolated, and sampled RSS can miss peaks or double-count shared pages.

[evidence.tar.gz](evidence.tar.gz) retains original bytes, SSE, requests, native
parity, GBNF and strict Rust receipts, the frozen inputs and sources, registration,
attempt ledger, host/assets, authorization and investigation notes.
[evidence-files.json](evidence-files.json) binds all 2,911 archive members; archive
SHA-256 is `ccc895ab74ede072593ed8df3b0ec140edcf7454534c4316a92f605c56e6cbb1`.
Original-byte Rust replay reproduces **all 78 retained responses**, including the
incomplete one, and reproduces the unchanged independent score. Original synthetic
replay also reproduces all 124 receipts, including all ten compiler-only rejections.

```sh
.venv/bin/python experiments/predicate-diagnostics-v1-first-evidence/analyze.py --check
.venv/bin/python -m unittest discover \
  -s experiments/predicate-diagnostics-v1-first-evidence -p test_analysis.py -v
```

The three evidence tests pass: exact reproduction without subprocesses with all
126 identities and null missing outcomes, archive-tamper rejection, and rejection
of an invented investigator quote even after resealing the archive. The 23 focused
diagnostic tests also pass. The first full pipeline invocation stopped when its
Python suite exceeded the unchanged 600-second check deadline. Its failure receipt
and logs are retained. The unchanged driver records the timeout error but does
not retain the exception's partial per-test output; that missing output and an
unknown completed-test count are explicit in the validation record. A separate
serial model-free invocation uses the same source, limits and offline settings.
**All 39 serial pipeline checks pass:** 335 current Python tests, 15 frozen pilot
tests, 100 Rust tests, required browsers, format/Clippy, historical replays,
source canaries, deterministic rebuild and final clean-tree verification, with
no skips. Existing trusted model-free fixture/oracle checks use fixed inputs;
generated model outputs are preview-only. Full pipeline scope is the unchanged
execution commit; the new evidence analyzer and tests are validated separately.

[validation.json](validation.json) records both validation attempts and their
scope. [verification.json](verification.json) retains every final pipeline check.
[validation-logs.tar.gz](validation-logs.tar.gz) and
[validation-logs-files.json](validation-logs-files.json) preserve all 133 log and
operator files, including the initial pipeline failure and missing-output record.
[preservation.json](preservation.json) verifies all **1,366 original tracked files**,
all **329 registered input files** and both original Rust binaries unchanged.
Only this evidence directory is added.

**Zero model-generated RDF executions; no holdout access, downloads, user-process
interruption, reference changes, #75 integration or automatic merge.** The attempt
is exhausted. Further inference requires a new reviewed append-only execution
registration and separate authorization. Independent human evaluation of the
original sources, references and retained responses remains necessary.

Decision: **INCONCLUSIVE_REVISE**. #83 stays open; #75 stays disabled.
