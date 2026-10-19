# #83: v1f evidence analysis and v1g design

**INCONCLUSIVE_REVISE. Native inference is unauthorized and unattempted.** The
model-free diagnostic milestone is complete; independent human review remains
pending and is not a completion requirement for this milestone. Keep #83 open.
No semantic GO, model ranking, query execution or product integration is claimed.

The [machine report](analysis.json) and [failure matrix](failure-matrix.md) retain
all **72 unattempted v1f observations**. Every model accuracy numerator is null
with zero measured denominator. Counts of unattempted cases are bookkeeping,
not model failures. Oracle and frozen whole-question BM25-v1, Qwen and Gemma,
forward/reverse, all five plan fields and reference question classes remain
separate. The original full 30-case strict stages also remain unattempted.

## Verified blockers and identities

[operator-verification.json](operator-verification.json) records verification of
the committed freeze, all 67 registered source inputs, the 801-file historical
inventory, source/packet archive and exact Rust binary. The registered and actual
binary SHA-256 was
`16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.
Frozen checksums SHA-256:
`8475600f50d3646feef4e954dd1ae4fb1471681a2257253b25ca10d4ed475b51`.

Both pinned official checkpoints, tokenizer/config/license bytes, Q4_K_M files,
preparation receipts, runtime source and retained runtime binaries verified
without loading weights or invoking a backend. Exact hashes, toolchain, Python
packages and native hardware/resource receipts are retained. No downloads,
conversion, native generation or model-generated RDF execution occurred.
The native tokenizer environment also exactly matches the retained v1e inventory:
Python 3.12.14; package-list SHA-256
`402becc4d2873a93331e253f9b17e62e9969c0da8cbff5e867696cb3f78f3851`.
The machine report's no-run reasons reproduce the historical frozen baseline,
including its then-unaccessed asset state; these fresh operator checks are separate.

At **2026-10-19 10:03:32 UTC**, after asset hashing, the native host probe found
**2,330.88 MiB swap used, above the 1,024 MiB limit**. Load/CPU/free-memory/disk,
M1 Pro/32 GiB/arm64, AC power and thermal checks otherwise passed at that instant.
The first sandboxed probe could not read all host statistics; it is retained as
incomplete, followed by the native read-only probe. This is a dated verification
snapshot, not permission to run later or evidence of a currently quiet host.
Separate explicit operator authorization is also absent. No attempt was issued
under the frozen inference runner. Native template/token/GBNF/sampling controls
remain unattempted for v1f.

[operator-evidence.tar.gz](operator-evidence.tar.gz) and its
[file inventory](operator-evidence-files.json) retain the exact new asset/host
receipts, stdout/stderr, initial integrity result and initial test failures.
Original v1f and all historical evidence are unchanged.

## What the automated analysis means

[tools/analyze_v1f.py](../../tools/analyze_v1f.py) reads the retained v1f archive,
its preregistration/source/reference audit, and optionally one retained run per
model. It verifies the archive/file/freeze identities before analysis, and checks
run inventories, schedule, request accounting, context identity, original raw
base64/proposal hashes and Rust receipts. It never calls inference or executes an
RDF query. It independently parses strict drafts and compares all five fields;
it does not trust a stored semantic-success flag.

The three evidence layers are independent:

- **Structure:** JSON, strict contract, native GBNF receipt and Rust acceptance.
  An executable wrong plan is a semantic reference failure. A rejected candidate
  remains a model candidate, never a correct model-origin clarification.
- **Exposed-reference agreement:** exact status/start/predicate/graph/direction/
  output, plus completed, GBNF-valid, Rust-accepted agreement. These are exposed
  AI-authored references, with zero independent validation. Numerators use only
  attempted observations; missing output on an attempted request does not pass.
  Structure metrics use available raw/native/Rust measurements independently.
- **Source evidence:** graph-qualified vocabulary membership, enumerated original
  reference-edge witnesses, literal predicate metadata and the preregistered AI
  source audit. An edge can exist while its natural-language predicate meaning is
  unestablished. Absence of a witness does not establish real-world absence.

The original “every stored label” case remains reference-supported even though
the preregistered source audit flags ambiguity. Separate `AI_source_question_group`
and `AI_source_audit_clarification_agreement` fields expose that disagreement;
they do not rewrite the reference or become human judgments. Unrestricted
rationale claims are unassessed. The bounded rationale rule flags only explicit
English ID-to-IRI assertions contradicted by the source table; zero detected
contradictions never means the entire rationale is correct.

Latency distributions, native tokens/completion counts and resource snapshots
are retained separately. RSS is the sampled process-tree run peak so far, not a
per-case peak; sampling can miss peaks or double-count shared pages. No disk-cold
or human decision latency is claimed. Repetitions are separate correlated rows,
not independent reliability estimates. Pairwise comparisons report attempted
pairs only and provide no incomplete-model ranking.

## Primary mechanism and next experiment

There are **no measured v1f semantic failures to diagnose yet**. The primary
observed v1f blocker is authorization, with a separately measured swap failure.
Earlier [v1e raw evidence](historical-mechanisms.json) preserves 17 completed
oracle responses: Qwen over-clarified an explicit label request despite available
vocabulary and made false predicate identity claims; Gemma guessed a country
relation for ambiguous location wording and Rust rejected it. Neither completed
the six smoke cases or retrieval comparison. Those facts establish interpretation
and ambiguity failures even with oracle IDs; they do not establish model ranking.

[#82](../issue-82-neighborhood/README.md) independently measured BM25-v1 predicate
coverage **6/18**, versus neighborhood-v2 **18/18** at k=20. All twelve original
misses lack matching whole-question predicate tokens, and source adjacency
recovers them. This is the measured retrieval mechanism, not an inference result.
The original source has no descriptive predicate texts for P17/P131/P856, so
additional membership does not itself establish their natural-language meanings.

The [separately versioned v1g design](../../experiments/native-one-hop-v1g/README.md)
preregisters a matched-presentation three-condition comparison, its 94-request
maximum/model, endpoints and fail-closed boundaries. It also proposes explicit
predicate-IRI tests and a separate, independently source-backed metadata experiment
if meaning remains the limit. No definitions are invented or imported here. The
design registration is not an executable freeze: the v2 bridge and every final
context/prompt/source/binary hash need a committed execution registration and
separate v1g authorization. No v1g generation occurred.

## Exact model-free reproduction and separately authorized commands

From this branch, without models:

```sh
.venv/bin/python tools/analyze_v1f.py --out artifacts/v1f-analysis-replay
.venv/bin/python -m unittest discover -s tools -p test_analyze_v1f.py -v
# Full required pipeline, with no native inference:
CARGO_NET_OFFLINE=true REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

Before considering inference, restore and verify the **existing** freeze, without
rebuilding/resealing it:

```sh
mkdir -p artifacts/issue83-v1f-approved
# The analyzer above verifies the archive against its committed preregistration.
tar -xzf reports/issue-83-native-one-hop-v1f-diagnostic/evidence.tar.gz -C artifacts/issue83-v1f-approved
.venv/bin/python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'tools')
import native_one_hop as a
a.CONFIG = a.ROOT / 'configs/native-one-hop-v1f-diagnostic.json'
a.verify_freeze(Path('artifacts/issue83-v1f-approved/freeze'))
print('Exact frozen source, packets and Rust binary verified')
PY
```

**Only after separate explicit operator authorization**, approve these exact
one-attempt commands, serially. Each checks pinned assets and then requires a
fresh passing native host gate before loading. A failed gate is retained; no
retry, process interruption, cache eviction or hardware-limit change is allowed.
The reported swap failure must not be treated as passing.

```sh
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic run --freeze artifacts/issue83-v1f-approved/freeze --model qwen35 --allow-inference --out artifacts/issue83-v1f-approved-qwen35
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic run --freeze artifacts/issue83-v1f-approved/freeze --model gemma4 --allow-inference --out artifacts/issue83-v1f-approved-gemma4
```

For every retained attempt that created a run directory, including stopped runs,
verify original bytes through Rust preview, then analyze; omit a nonexistent run
argument rather than inventing its measurements:

```sh
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic replay --freeze artifacts/issue83-v1f-approved/freeze --run artifacts/issue83-v1f-approved-qwen35
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic replay --freeze artifacts/issue83-v1f-approved/freeze --run artifacts/issue83-v1f-approved-gemma4
.venv/bin/python tools/analyze_v1f.py --run artifacts/issue83-v1f-approved-qwen35 --run artifacts/issue83-v1f-approved-gemma4 --out artifacts/v1f-analysis-after-authorized-attempts
```

Never refresh a historical freeze to accept changed source or binary bytes.
Native inference needs its own authorization; v1g needs both its execution freeze
and separate authorization. Zero #75 live integration, sealed-holdout access,
unattended Ask, fabricated reviewers, model-generated RDF executions or automatic
merge.

## Verification

The complete required pipeline **passed at `7e21f1c`**, including **260 current
Python tests** (six new analyzer tests), required headless-browser checks, Rust
workspace tests, Clippy, formatting, frozen-history replay, reference checks and
source-integrity/canary checks. The first full run also passed at `a2b0062`; the
only intervening change makes synthetic test transport portable across Rust hosts.
Production freeze/binary gates remain unchanged. Original frozen source, packets,
binary and all 801 historical hashes verified again after the final pipeline.

[verification.json](verification.json) and [scope notes](verification-notes.json)
record the final commands and outcomes. [Complete logs](verification-logs.tar.gz)
and their [hash inventory](verification-logs.json) retain both full passing runs,
the final six-test check and the native tokenizer environment receipt. Only these
receipts and report metadata follow the verified code commit. No native inference,
human review, v1g run or semantic readiness is implied by passing model-free tests.
