# Single Qwen status-precedence attempt — INCONCLUSIVE_REVISE

Refs #83. This is the one explicitly authorized Qwen3.5-9B Q4_K_M command from
PR #97, exact commit `e540f90e7624ef63cc031128a0704b1222450082`.
The owner stated **"PR #97 passed. I authorize it."** and then **"Try now"**
after the earlier admission blocker. Both CI checks at that exact PR commit
passed. The registered sources were used at that exact detached commit.

The earlier [blocked admission evidence](../native-one-hop-v1h-qwen-status-precedence-evidence/README.md)
is preserved unchanged: it loaded no model, sent no completion request and did
not consume the no-retry ledger. The renewed host check and the command's own
fresh preflight passed the original limits. The committed freeze was restored
again into a fresh directory after preserving the previous local copy.

Exact command, issued once with no retries:

```sh
.venv/bin/python tools/native_one_hop_v1h_status_precedence.py run \
  --freeze artifacts/v1h-qwen-status-precedence \
  --model qwen35 \
  --allow-inference \
  --out artifacts/issue83-v1h-qwen-status-precedence-first
```

**Execution status: `completed_diagnostic`, process exit 0.** All 38 requests
completed, with zero retries, fatal/runtime failures or unattempted observations.
Both native sampling controls passed; all 36 semantic observations completed.
There were six oracle and four BM25-v1 exposed-reference mismatches among those
completed observations; completion is not correctness. No model-generated RDF
was executed and no integration authority was granted. The consumed freeze/model
ledger contains exactly `['qwen35']`; this command must not run again.

| Schedule | Scheduled | Completed | Fatal failures | Unattempted |
|---|---:|---:|---:|---:|
| Native sampling controls | 2 | 2 | 0 | 0 |
| Oracle semantics | 19 | 19 | 0 | 0 |
| BM25-v1 semantics | 17 | 17 | 0 | 0 |

| Primary criterion | Unchanged Qwen v1h baseline | Status-precedence attempt |
|---|---:|---:|
| Oracle model-origin unsupported | 2/6 | 3/6 |
| BM25-v1 model-origin unsupported | 4/6 | 5/6 |
| Oracle genuine clarification | 3/3 | 3/3 |
| BM25-v1 genuine clarification | 3/3 | 3/3 |

All six forbidden-operation and all three genuine-clarification identities in
each condition completed. Oracle still requests clarification on `negation`,
`filter` and `multi_hop`; BM25-v1 still requests clarification on `multi_hop`.
Both conditions newly classify `count` as unsupported; the other unsupported
identities retain their baseline status. These are model statuses, not Rust
rejections. Denominators remain separate, including the original correlated
oracle repeats. This small exposed diagnostic does not establish a causal
effect, semantic correctness, model superiority or product readiness.

All **3/3 baseline valid candidates in each condition were retained**; no
baseline valid plan was lost. Oracle gains are `repeat-0`, `repeat-1`,
`source_label` and `smoke-eva-01` (the repeated university question is correlated).
BM25-v1 gains are `source_label` and `malicious_label_explicit`.

Every candidate-reference abstention remains explicit:

- Oracle: `malicious_label_explicit`, `smoke-eva-07`, `smoke-eva-08` all request
  clarification, as in the baseline.
- BM25-v1: `smoke-eva-02` and `smoke-eva-08` still request clarification;
  `smoke-eva-07` changes from clarification to **unsupported**, a new
  false-unsupported outcome on a candidate reference. Its start entity 100 is
  visibly present in graph 0, its numeric predicate table is empty, and its
  rationale's university-to-GEMET graph assignment is unsupported.

Both reverse-reference probes still fail in each condition, including
abstentions: **0/2 reverse matches** in oracle and **0/2** in BM25-v1. Forward
candidate-reference matches are 7/8 oracle and 5/6 BM25-v1. For each of all five
fields, exposed-reference agreement is **7/10 oracle** (baseline 3/10) and
**5/8 BM25-v1** (baseline 3/8), counting completed candidate-reference abstentions
as field nonmatches. These are plan diagnostics, not exact-answer accuracy.
All 19 oracle and 17 BM25-v1 identities have paired completed baseline outcomes.

The original references and separate four-case AI ambiguity audit are unchanged.
In particular, `source_label` retains its candidate reference even though its
separate ambiguity audit remains unresolved. Supported multi-value label results
retain the original values projection; no language-choice constraint is added.
Missing authorized numeric vocabulary is never repaired from packet strings,
source IRIs, adjacent triples or model knowledge.

[comparison.md](comparison.md) retains every scheduled semantic identity,
baseline/new status, Rust acceptance, direction and all five candidate fields:
start, predicate, graph, direction and output/values projection. Missing outcomes
are null, and paired completed identities are reported separately in
[analysis.json](analysis.json). The independent source review covers every
retained semantic response and is bound to exact raw/context SHA-256 values.
These coding-agent notes are not independent human review.

Three retained responses have direct source-table contradiction witnesses:

- Oracle `multi_hop` denies a region-to-country edge even though numeric
  predicate 1008 explicitly supplies 109 → 110; the rationale then acknowledges
  that same edge.
- BM25-v1 `filter` correctly emits unsupported but says the only identifier is
  an IRI and denies numeric identifier data. The supplied lossless packet has
  `schema:identifier` with **630752**, datatype **xsd:integer**. The numeric
  predicate table is still empty; its missing ID is not restored.
- BM25-v1 `multi_hop` calls entity 113 Pirkanmaa, while the numeric table names
  graph-2 entity 113 biogas. It also denies the two graph-1 `containedInPlace`
  IRI edges that the supplied packet explicitly retains.

The analysis stores exact raw excerpts/hashes, context/source paths, asserted
values and supplied values. Correct status or five-field agreement does not
make a contradictory rationale correct. Separate notes retain unsupported
global-absence claims, the university-to-GEMET graph assignment in BM25-v1
`smoke-eva-07`, opaque predicate meanings, unlabeled graph-0 endpoints and lack
of cross-graph identity bridges. A narrow automatic English assertion detector
does not replace this inspection, and absence of a direct contradiction does
not establish unrestricted rationale correctness.

The baseline BM25-v1 English country rationale misidentifies 1004 as P1448 and
its entity object as a literal. The new response on that same identity names
P17/1004, entity object 101 and the correct stored direction; that particular
direct contradiction is absent. Country meaning for opaque P17 and the identity
of unlabeled graph-0 Q33/101 remain independently unestablished. The three new
contradicting responses above remain failures of source consistency; the narrow
automatic detector reports zero and does not erase the explicit witnesses.

Integrity and resource gates passed without adjustment. The fresh run preflight
at `2026-10-21T18:38:30.307722+00:00` measured **610.62 MiB swap**, below the original
1024 MiB maximum; no host blockers were recorded. Native startup took 8.67 s.
All 38 fresh native prompt-byte/token-ID parity checks passed. Every complete
original/columnar pre-load prompt and token array matches the registered receipt;
the largest columnar input remains 14,049 + 512 = 14,561 < 16,384. Both sampling
controls and all 12 model-free native grammar controls passed. All 16,916 RSS
samples are retained; peak sampled process-tree RSS was **16,135,248 KiB
(15.39 GiB)** against 24 GiB, with no monitor error. The largest-prompt observation
took 280.25 s inside the unchanged 300-second deadline. Raw timings and backend
logs are retained without causal speed or memory comparisons to the baseline.

Reproduce without weights, model calls, network or subprocesses:

```sh
.venv/bin/python experiments/native-one-hop-v1h-qwen-status-precedence-first-evidence/analyze.py --check
.venv/bin/python -m unittest discover \
  -s experiments/native-one-hop-v1h-qwen-status-precedence-first-evidence \
  -p test_analysis.py -v
```

The evidence archive and per-file inventory retain original run bytes, raw SSE,
prompts, token arrays, fresh native parity, native controls, untouched model
responses, trusted and model-output Rust previews, validators, startup/request
timing, sampled process-tree RSS, assets, fresh host gates, registration,
restored freeze, registered sources, source-audit notes, authorization,
no-retry ledger, exact operator command output and stop reasons.

[evidence.tar.gz](evidence.tar.gz) and [evidence-files.json](evidence-files.json)
bind all retained bytes. [preservation.json](preservation.json) verifies every
1,286 original tracked file, 801 historical hashes, 83 registered source hashes
and all 11 previous blocked-evidence files. The registered Rust binary is still
`16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.
The unchanged baseline analysis and Markdown reproduce byte for byte. All
74 trusted/model-output original-byte Rust previews replay with zero RDF
execution. The archive also binds the exact scorer sources and every source
inspection note. Independent human judgments remain null.

All **39 post-execution model-free pipeline checks passed** at the exact
authorized source commit in an isolated checkout after the model stopped:
304 current Python tests, 15 frozen pilot tests, 100 Rust tests, required
browsers, format/Clippy, source canaries, historical replays, deterministic
rebuild and final clean-tree verification, with no skips. Both new portable
evidence tests pass, including exact model-free reproduction and archive-tamper
rejection. No validation model was loaded or additional inference performed.
[validation.json](validation.json) records precise scope, source commit,
commands, timings and binary preservation; [verification.json](verification.json)
records every pipeline check. Complete logs and per-file hashes are retained in
[validation-logs.tar.gz](validation-logs.tar.gz) and
[validation-logs-files.json](validation-logs-files.json). Only this separate
evidence directory is added; registered sources and earlier reports are intact.

Decision remains **INCONCLUSIVE_REVISE**. Keep #83 open and #75 integration
disabled. Independent human-review fields remain pending/null. Neither #97 nor
any evidence PR is merged. No further inference, retry, automatic follow-up
experiment, Gemma/v1g run, download or threshold change is authorized by this
evidence publication. Exposed AI-authored references, small samples, correlated
repeats, historical host/cache differences, missing numeric vocabulary, opaque
source meaning and unresolved reverse direction retain their original limits.
RSS sampling can miss peaks and double-count shared pages.
