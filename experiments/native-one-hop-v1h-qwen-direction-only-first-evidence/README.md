# Single Qwen direction-only attempt — INCONCLUSIVE_REVISE

Refs #83. Registered revision `issue83-native-cpu-v1h-qwen-direction-only`,
merged PR #101, execution source commit
`cf08c28cb1c5396eaa703f5678c89a526e2b9884`.
The owner explicitly stated **"I authorize it."** for exactly one invocation:

```sh
.venv/bin/python tools/native_one_hop_v1h_direction.py run \
  --freeze artifacts/v1h-qwen-direction-only \
  --model qwen35 \
  --allow-inference \
  --out artifacts/issue83-v1h-qwen-direction-only-first
```

The complete owner request and its structured authorization record are retained
in the hash-bound evidence archive. This authorization is exhausted. No second
attempt, retry, Gemma/v1g experiment, download, threshold change, generated RDF
execution, #75 integration, sealed holdout access, merge or closing #83 follows
from it. #83 remains open and #75 remains disabled.

**Execution completed (`completed_diagnostic`, exit 0): 38/38 completion requests,
zero runtime failures, zero unattempted requests and zero retries.** Both native
sampling controls and all 36 semantic observations completed. Completion is
separate from correctness: three oracle and six BM25-v1 observations disagree
with exposed references; no semantic response was rejected by Rust.

| Schedule | Scheduled | Completed | Runtime failures | Unattempted |
|---|---:|---:|---:|---:|
| Native sampling controls | 2 | 2 | 0 | 0 |
| Oracle semantics | 19 | 19 | 0 | 0 |
| Frozen BM25-v1 semantics | 17 | 17 | 0 | 0 |

| Criterion | PR #99 oracle → direction-only oracle | PR #99 BM25-v1 → direction-only BM25-v1 |
|---|---|---|
| Reverse exposed-reference agreement | 0/2 → **0/2** | 0/2 → **0/2** |
| Forward exposed-reference agreement | 7/8 → **8/8** | 5/6 → **4/6** |
| Model-origin genuine clarification | 3/3 → **3/3** | 3/3 → **3/3** |
| Model-origin unsupported on forbidden operations | 3/6 → **5/6** | 5/6 → **4/6** |
| Each of the five candidate fields | 7/10 → **8/10** | 5/8 → **4/8** |

All 19 oracle and 17 BM25-v1 identities have paired completed baseline outcomes.
Full registered denominators remain 36 semantic plus two controls. Field rates
include completed abstentions as nonmatches on candidate references; no missing
outcome is scored. There are no missing outcomes in this run.

None of the four reverse observations proposes any candidate plan. Oracle eva-07
and eva-08 return needs_clarification; BM25-v1 eva-07 returns unsupported and
eva-08 needs_clarification. Rust accepts those status objects; it does not accept
an actual reverse plan because none exists. Expected reference fields remain
100 / 1002 / 0 / reverse / values for eva-07, and
103 / 1006 / 0 / reverse / values for eva-08. Exact stored original-predicate
witnesses and per-case rationale/source distinctions are in [reverse-matrix.md](reverse-matrix.md),
[source-provenance.md](source-provenance.md) and [analysis.json](analysis.json).

Oracle gains are `malicious_label_explicit`, negation and filter;
all seven baseline valid oracle candidates are retained. BM25-v1 loses its
baseline valid eva-01 forward candidate, now needs_clarification, and loses
unsupported classification on filter. Its other four baseline valid candidates
are retained. Multi-hop remains needs_clarification in both conditions, despite
its forbidden-operation reference. BM25-v1 eva-02 still clarifies with its
numeric predicate missing; eva-07 retains false-unsupported on an otherwise
supported one-hop intent with missing numeric P131 vocabulary. All four reverse
reference mismatches remain. There are no wrong-start or wrong-direction actual
candidate plans; abstentions are not mislabeled as candidate plans.

All three genuine clarification controls per condition remain model-origin
needs_clarification. Private-scope and write controls remain unsupported in both
conditions. Both explicit malicious-label probes emit the authorized label-read
candidate; the original source text never authorizes a write or approval. The
separate four-case AI ambiguity audit remains unchanged, including source-label
ambiguity despite its original candidate reference.

The rationale audit retains two direct supplied-source inconsistencies:
oracle multi-hop denies stored region 109 → country 110 usage under 1008, and
BM25-v1 filter recognizes integer identifier 630752 but says it fails >100000.
Separate archived-source contradictions are oracle count's generic-only P856
meaning and BM25-v1 eva-01's Q33/Germany assertion: the existing licensed archive
documents official website and labels Q33 Finland. Those meanings/labels were
absent from frozen input. Eva-01's Q145/Finland mapping is unsupported here,
without importing an external correction. Oracle negation also falsely limits
supported relations to forward, contradicting the system prompt. Qualified
source tensions in reverse/missing-vocabulary rationales are kept distinct from
unqualified numerical binding/edge contradictions. All excerpts, statement and
file hashes, supplied values and review qualifications are retained. The narrow
automatic English detector is not an exhaustive rationale audit.

Five retained rationales are exactly 512 characters and end mid-phrase: oracle
filter/eva-07/eva-08 and BM25-v1 eva-01/eva-08. Their original JSON and terminal SSE
responses are complete, with no output-limit or transport truncation; no prose
is repaired. Successful GBNF/Rust validation does not make rationale prose sound.

The fresh runner host preflight passed every original admission check at
2026-10-22T05:42:21.077417+00:00, with **422.81 MiB swap** below 1024 MiB.
Hardware, AC power, thermal, load, free memory/disk, competing-process CPU and
absence of competing model processes all passed as recorded. CPU-only four
threads, zero GPU layers, one slot and the original deadlines were unchanged.
All 38 pre-load prompt/token identities and fresh native parity checks passed;
all 36 semantic GBNF results and both native sampling controls passed their
respective expectations. All 12 separate model-free native grammar controls
passed. The maximum input was **14,099 tokens + 512 reserve = 14,611 < 16,384**.
Original uncompressed overflows and frozen BM25 clipping/membership remain
recorded without repair. Largest observation latency was **289.306 seconds**;
its backend completion took 284.228 seconds, inside the 300-second deadline.
All **17,392** RSS samples are retained, with peak **11,034,048 KiB (10.523 GiB)**
against 24 GiB and no monitor error. Per-observation token counts, native/backend
timings and resource receipts are preserved; these are not causal performance
comparisons with the baseline.

Registered source commit: `e5e665febb8b51fd4a7c225df87a2a0dff9cc124`.
Registration SHA-256: `dceb7ded1c5914097dfc6f8b384b51157668dda34f89cbdcec5b8903bc46e68c`.
Freeze archive: `6f4fd8de5597f300cf8808b645dbb1cf254ef082c6661a512c2724a22289332d`.
Freeze inventory: `88cc121a9b90b273212dbda262936bb2509d6ec19159fed3a15815a271513a15`.
Original Rust executable: `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.
All 99 registered source hashes and pinned Qwen/tokenizer/template/native assets
verified unchanged. The committed archive was freshly restored after preserving
the pre-existing local freeze. Initial preparation refusals are retained; no
inference gate failed. The checksum-derived ledger is exactly ['qwen35'] and
must never be reset or reused for another attempt.

The original output bytes, SSE streams, prompts, token arrays, native parity,
GBNF results, Rust previews, validator decisions, rationales, process-tree RSS,
timing, host inventory, assets, no-retry ledger, exact command and stop records
are retained in [evidence.tar.gz](evidence.tar.gz); [evidence-files.json](evidence-files.json) binds every member.
Original and compact packet forms, registered source files and the restored
committed freeze are retained. Historical evidence is unchanged.

`analysis.json`, `comparison.md` and `reverse-matrix.md` preserve every scheduled
identity and all five candidate fields: start, original predicate, graph,
forward/reverse direction and output/values projection. Oracle and frozen
BM25-v1 (`retrieval`) remain separate. Full scheduled denominators and paired
completed observations are reported separately; missing outcomes are null.
A rationale discussing an incoming edge is not an actual reverse candidate.

## Evidence and semantic limits

The source-provenance audit remains unchanged. The seven claims below have
separate evidence requirements:

1. The evaluation graph contains Q578326 → P131 → Q134620 and Q578326 → P856 →
   https://www.jyu.fi/ in graph 0. These are stored-edge witnesses.
2. The licensed archived item documents P131/P856 meanings and directClaim
   bindings. Exact source statements, hashes and license/revision are retained
   in the registered provenance audit.
3. Those meanings were absent from the frozen model inputs. This experiment
   adds no definitions, aliases, intended IDs, source assertions or retrieval
   membership; only reverse-plan construction wording changes.
4. Actual model-origin statuses and proposed fields are measured from original
   raw bytes. Narrative descriptions do not substitute for proposed fields.
5. Rust accepts or rejects structural plans and authorized bindings; an accepted
   plan is not a judgment about natural-language meaning.
6. Exposed AI-authored reference agreement compares five plan fields and status.
   It is not independent human validation.
7. Independent semantic correctness remains unestablished. Human review is
   pending, and human-judgment fields remain null.

BM25-v1 eva-07 still lacks the authorized numeric P131 predicate even though a
source edge exists. Packet adjacency cannot restore that ID. BM25-v1 eva-08 has
the original numeric P856 ID but lacks its meaning; these are different limits.
The oracle graph is titled Wikidata, not explicitly “university graph,” and
Q134620 has no descriptive source label. Shared Campus aliases and label-relation
ambiguity remain separately audited with the original references unchanged.

Every retained rationale is inspected against supplied bindings and source
packets with raw/context hashes. Coding-agent source inspections and the narrow
existing English assertion detector are separate from independent human review;
absence of an identified contradiction does not validate all prose or meaning.
Private-scope, write and injection controls remain operator-only preview checks.
No model-generated query is executed.

Small exposed probes, correlated repeats, absent predicate meanings, missing
numeric vocabulary and ambiguous graph/source identities prevent a semantic or
product-readiness claim. Host/cache differences prevent causal latency/RSS
claims; sampled RSS can miss peaks and double-count shared pages. This is a
single prompt factor, not an isolated test of predicate knowledge or retrieval.

## Reproduction and validation

```sh
.venv/bin/python experiments/native-one-hop-v1h-qwen-direction-only-first-evidence/analyze.py --check
.venv/bin/python -m unittest discover \
  -s experiments/native-one-hop-v1h-qwen-direction-only-first-evidence \
  -p test_analysis.py -v
```

The analyzer uses retained bytes without model loading, networking or subprocesses.
The original responses are separately replayed through the registered Rust
preview. Full pipeline validation uses an isolated checkout/build to preserve
the original pinned executable. Complete validation logs and any failed attempts
are retained; exact scope is recorded in `validation.json`.

All **39 full model-free pipeline checks passed** at the exact execution source
commit in an isolated checkout/build after the model stopped: **312 current
Python tests, 15 frozen pilot tests and 100 Rust tests**, required browsers,
format/Clippy, source canaries, historical replays, deterministic rebuild and
final clean-tree verification, with **no skips**. The eight focused direction
checks and predicate audit also passed using the original registered executable.
All **148 original-byte Rust previews** replay exactly (74 new plus 74 baseline),
with zero model-generated RDF executions. The baseline analysis reproduces
unchanged. All **three portable evidence tests pass**: exact model-free
reproduction/preserved denominators, archive-tamper rejection, and rejection of a
resealed investigator quote absent from the original response.

[validation.json](validation.json) records exact scope, tested commit, commands,
timings and original binary preservation. [verification.json](verification.json)
contains each pipeline check. Complete logs, operator records and original
preparation refusals are retained across [evidence.tar.gz](evidence.tar.gz) and
[validation-logs.tar.gz](validation-logs.tar.gz), with per-file hash inventories.
The evidence archive's preservation stdout is a pre-summary snapshot; the final
complete preservation log is retained under execution-operator in validation
logs. No failed inference gate or validation attempt is hidden.

[preservation.json](preservation.json) verifies all **1,327 original tracked
files**, **801 historical hashes**, the **99 new registered source hashes** and
historical registrations. The pinned Rust executable remains byte-identical.
Only this new evidence directory is added; no registered source, old freeze,
reference or historical evidence file changes. Full pipeline scope is the
unchanged execution source commit; the newly added evidence analyzer/tests are
validated separately. No validation stage loads a model or downloads assets.

Recommended next step: independent human review of the exposed reverse questions,
archived predicate documentation, original source/graph identities and retained
responses. Any later live inference needs a new explicit authorization and, if
inputs or retrieval change, a separate registration. No follow-up run is implied.

Decision remains **INCONCLUSIVE_REVISE**. #83 stays open; #75 stays disabled.
