# Qwen status-precedence admission blocked — INCONCLUSIVE_REVISE

Refs #83; stacked on unmerged PR #97 at exact authorized commit
`e540f90e7624ef63cc031128a0704b1222450082`.
The owner stated **"PR #97 passed. I authorize it."** for the registered
Qwen3.5-9B Q4_K_M command, contingent on every original gate passing.
Both GitHub CI checks succeeded at that commit.

**Blocked before issuing the inference command.** The fresh registered host
preflight measured **2519.38 MiB swap**, exceeding the unchanged **1024 MiB**
admission limit. No model loaded, no completion request was sent, no retry was
made, and no model-generated RDF was executed. No process was interrupted and
no threshold, registered source, prompt, reference or previous evidence changed.
This session stops after publishing this separate evidence PR.

| Schedule | Scheduled | Completed | Failed observations | Unattempted |
|---|---:|---:|---:|---:|
| Native sampling controls | 2 | 0 | 0 | 2 |
| Oracle semantic observations | 19 | 0 | 0 | 19 |
| BM25-v1 semantic observations | 17 | 0 | 0 | 17 |
| Total | 38 | 0 | 0 | 38 |

The admission gate failed; no observation failed because none was attempted.
The inference output directory and freeze/model no-retry ledger remain absent.
No attempt is claimed or reconstructed. Native sampling results, native template
parity, raw response bytes, SSE streams, model-output Rust previews, completion
timing and runtime RSS are absent and reported as **null**. Static frozen prompt
bytes, token IDs and complete independent tokenizer receipts are retained.

| Primary criterion | Unchanged Qwen v1h baseline | This blocked experiment |
|---|---:|---|
| Oracle unsupported | 2/6 | null; 0 measured / 6 scheduled |
| BM25-v1 unsupported | 4/6 | null; 0 measured / 6 scheduled |
| Oracle genuine clarification | 3/3 | null; 0 measured / 3 scheduled |
| BM25-v1 genuine clarification | 3/3 | null; 0 measured / 3 scheduled |

There are zero paired completed identities. Supported-candidate regressions and
loss of baseline valid candidates are unmeasured, not zero. Baseline valid
candidate identities remain visible in [analysis.json](analysis.json): oracle
`smoke-eva-02`, `smoke-v1e-country-source-nb`, `smoke-v1e-country-paraphrase-en`;
BM25-v1 `smoke-eva-01` and the same two country cases. The baseline reverse probes
`smoke-eva-07` and `smoke-eva-08` abstain in both conditions; these failures remain
visible alongside forward failures and all five fields (start, predicate, graph,
direction, output/values projection) in [comparison.md](comparison.md).

Rationale/source-table consistency is reported independently. The unchanged
baseline BM25-v1 `smoke-v1e-country-paraphrase-en` matches all five plan fields,
yet its rationale calls predicate 1004 “P1448” and the object a literal string
“Finland.” Supplied predicate 1004 is P17 with observed usage 102 → entity 101;
P1448 is predicate 1003. Exact raw excerpt, SHA-256, context path/hash and supplied
values are retained in `baseline_rationale_source_table_witness` in the analysis.
The narrow automatic English detector reports zero for that response; this does
not erase the explicit contradiction. No new rationale exists to inspect; its
contradiction outcome is null. This source-grounded coding-agent witness is not
independent human semantic review.

The committed freeze was restored into a fresh directory after preserving the
pre-existing local freeze. Archive/inventory, all 83 registered source hashes,
Rust binary, pinned assets and tokenizer environment verified. All 38 independent
recounts match complete frozen receipts, including exact prompts, token arrays,
original/columnar variants and section contributions. The largest columnar input
is 14,049 tokens, or 14,561 with the 512 reserve, strictly below 16,384. All 12
model-free native grammar accept/reject controls passed. These are distinct from
the two unattempted native sampling controls. The sole host blocker was swap;
no inference was launched to evade the failed admission limit.

Reproduce the retained, model-free analysis (no assets or subprocesses):

```sh
.venv/bin/python experiments/native-one-hop-v1h-qwen-status-precedence-evidence/analyze.py --check
```

[evidence-files.json](evidence-files.json) hashes every original byte in
[evidence.tar.gz](evidence.tar.gz): authorization, exact GitHub/CI receipt,
pre/post ledger and output inspection, gate operator script and results, fresh
host inventory, assets, tokenizer and grammar receipts, committed registration,
restored freeze and all registered source files. [preservation.json](preservation.json)
verifies every 1,286 original tracked file, 801 historical hashes and 76 parent
source hashes, plus byte-for-byte baseline analysis and Markdown reproduction.
The original registered binary remains
`16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.
All **39 full model-free pipeline checks passed** at the exact authorized PR
commit in an isolated checkout: 304 current Python tests, 15 frozen pilot tests,
100 Rust tests, required browsers, format/Clippy, source canaries, historical
replays, deterministic rebuild and clean-tree verification, with no skips.
All 74 baseline original-byte Qwen Rust previews also replayed without RDF
execution. The evidence analyzer separately reproduces exactly without
subprocesses and rejects archive tampering.
[validation.json](validation.json) records the precise validation scope and
commands; [verification.json](verification.json) records every pipeline check.
Complete logs and their individual hashes are in
[validation-logs.tar.gz](validation-logs.tar.gz) and
[validation-logs-files.json](validation-logs-files.json). No registered source
changed after validation; this PR adds only this separate evidence directory.

Decision remains **INCONCLUSIVE_REVISE**. Issue #83 stays open; #75 integration
is disabled. Independent human-review fields remain pending/null. No merge is
authorized. No retry, follow-up inference, Gemma/v1g experiment, model download
or threshold change is included. A blocked experiment measures no prompt effect;
even a successful completion would not establish semantic correctness, model
superiority or product readiness. Historical baseline/cache/host differences,
exposed AI-authored references, correlated repeats, opaque source meaning and
unresolved direction behavior retain their original limitations.
