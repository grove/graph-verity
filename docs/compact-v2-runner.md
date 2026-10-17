# Opt-in compact v2 CPU runner (#31)

This integrates the #30 contract with the original Qwen2.5-1.5B-Instruct Q4_K_M
weights and llama.cpp b5046. It is an exploratory integration, separate from the
frozen M1 Pro A/B measurement. Existing v1 configuration, prompt, grammar, public
benchmarks, snapshots and historical reports remain byte-identical.

Build Rust, then run **offline** with previously prepared pinned assets:

```sh
cargo build --workspace --locked --offline
python3 tools/local_parser.py run --mode compact-v2 --suite development \
  --out artifacts/compact-v2-development-001
python3 tools/local_parser.py run --mode compact-v2 --suite adversarial \
  --out artifacts/compact-v2-adversarial-001
```

Development covers `wikidata/dev` and `worldcities-transfer/transfer_dev`;
adversarial covers `adversarial/dev` and `adversarial-transfer/transfer_dev`.
Choose a fresh directory every time. Runs never download assets or read private
holdout data. Explicit network acquisition/build, if needed, remains:

```sh
python3 tools/local_parser.py prepare --mode compact-v2
```

The independently runnable v1 commands remain:

```sh
python3 tools/local_parser.py run --suite development --out artifacts/v1-development-001
python3 tools/local_parser.py run --suite adversarial --out artifacts/v1-adversarial-001
```

## Pinned identities and configuration differences

`configs/local-parser-compact-v2.json` pins the new prompt, generated GBNF and
existing Rust compact schema. The only differences from v1 are mode, prompt,
grammar, schema, vocabulary policy and evaluation attribution. Model, model
revision/license, runtime archive/revision, CPU flags, four threads, chat template,
seed, temperature, context/output budgets and deadline are identical. Configuration
validation rejects drift in these shared fields.

| Artifact | SHA-256 |
|---|---|
| `configs/local-parser-compact-v2.json` | `b66119b0a00c984d1a48cd44a34c99da086bd83cfc2c5e834ad8d63192a51d3d` |
| `configs/local-parser-compact-v2.prompt.txt` | `087b67786c85b5e112e283c9ed8bdf62142608c04f9f12f9e0ff2fecd56fa27b` |
| `configs/local-parser-compact-v2.gbnf` | `080d0dba5b967d569223675c4ec9c4dbe5561779d34038ffd3ded73d3be6fea5` |
| `schemas/compact-intent-v2.json` | `ede9a10a46c609aa5803bd053a1c32dd0126a0b6e5250454db20d8d2de34d3da` |
| `configs/local-parser.json` | `144bf5437190da22d46e0ea2f894b641bc0a69320e0e75a6459fc5a98687debe` |

The model SHA-256 remains
`6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`;
runtime revision `74d4f5b041ad837153b0e90fc864b8290e01d8d5`, archive SHA-256
`8dd9fcc7c17f972673960ffdcc7521f52de5a9ec594aa6acebd9dfd8c17c0a5c`.
Each run records configuration, source/binary/input hashes and the verified local
build receipt. The Rust schema is exported again and converted using that exact
runtime's schema converter; changed schema or unreproducible GBNF fails closed.
The generated grammar fixes alphabetical field order; the prompt names this order.
It admits some semantic/type limits more broadly than Rust, intentionally tested
below. It is not an authorization mechanism.

## Request and execution boundary

The private `evaluate-local-compact` stdio bridge uses `PlanOrigin::LocalModel`.
For every benchmark case, Rust authorizes the requested scope and constructs an
immutable request-bound `CompactContext`. Python receives its table, retaining
**every** authorized numeric ID and graph-local role. The prompt includes at most
four labels per ID, preferring nb/nn/en, to bound multilingual text. No vocabulary
selection consults gold; the v1 oracle selector is never called. All labels, IRIs
and comments remain quoted untrusted JSON. ChatML delimiter escaping also applies
to questions. Duplicate-label entities remain distinct IDs; a candidate for a
recognized ambiguous label is rejected by Rust preflight.

Python sends the raw generated text back as a string, without decoding, repairing,
translating or filling fields. Rust strictly decodes v2, expands using the **same
retained context**, independently compiles v1, then executes with existing scope,
read-only query and evidence checks. The model supplies no authority or SPARQL.
Malformed text, unknown/wrong-role/cross-graph IDs and extra commands/fields fail
closed. The expander compiles before returning a plan, so rejected expansion has a
reason/code instead of a partially trusted plan.

Every case reaches generation, including cases deterministic preflight would block.
A raw candidate blocked during expansion stays a candidate/rejection, never a
successful model abstention. Explicit valid `unsupported`/`needs_clarification`
responses remain model abstentions. Compiler validation cannot establish that a
well-typed plan expresses the question.

## Evidence and scoring

Each case directory preserves the full Rust request, bounded prompt context, exact
prompt, raw `proposal.json` (including invalid/truncated text), full runtime response
with tokens/timings, and actual runtime-grammar verdict. `report.json` records JSON
and compact-contract validity, raw status, preflight advice, expansion time and
expanded v1 plan or fail-closed reason, independent validation/compiler outcome,
execution/evidence, generation and end-to-end timings. The runtime's `stop_type`
and `truncated` fields are retained; `stopped_limit` derives from `stop_type=limit`.
Backend failures remain failures, with captured output and no retries.

`summary.json` keeps valid model abstentions, false/correct status abstentions,
deterministic preflight blocks, expansion/Rust rejection, exact answer agreement,
and wrong-but-executable proposals separate. Denominators include all cases.
Per-family pass/total counts are also retained. `compact-manifest.json` hashes
outputs even after failure. New compact runs use this manifest instead of the
v1/oracle-specific Phase 0 or adversarial-report adapters.

Only compact scoring normalizes variable names by first appearance in ordered
patterns, and count aliases by projection position. All operations, edge order,
direction, joins, literal types/boundaries, scope and grouping remain significant.
Answer sets align output columns by projection position, retaining RDF term
metadata; a different projection width fails exact agreement. Frozen gold and
reference queries are unchanged, and reference results must still match frozen
bindings before scoring. Raw expanded plans and bindings remain unmodified. This
is conservative reference agreement, not full query equivalence or expert gold.

## Controls and CI

With prepared runtime assets, static controls invoke the **actual pinned** GBNF
validator and Rust independently, without weights:

```sh
python3 tools/local_parser.py probes --mode compact-v2 \
  --out artifacts/compact-v2-static-controls-001
```

Opt into three generation controls (unconstrained/constrained forbidden-field
comparison and an actual malicious RDF label):

```sh
python3 tools/local_parser.py probes --mode compact-v2 --inference \
  --out artifacts/compact-v2-generation-controls-001
```

`run` includes these controls before its suite. Probes distinguish grammar acceptance
from Rust acceptance: positive/whitespace/count/abstention variants, invalid IDs,
variables, duplicate edges/fields, bad enums, missing/extra fields, commands,
SPARQL, literal injection, empty reasons, version mismatch and cutoff. A malicious
label in an authorized graph and a private-graph canary exercise the real catalog
boundary. Successful control replays have fixture origin; they are not model
semantic accuracy. Raw failed controls remain on disk and stop the run.

[Recorded controls](../reports/compact-v2-runtime-controls/README.md) show both
accepted and rejected strings with correct attribution. Normal CI discovers the
model-free Python bridge/pinning tests and Rust expansion/scoring regressions;
it neither downloads nor invokes model weights or the llama.cpp runtime.

## Risks and fallback

The [separate issue #32 M1 Pro comparison](../reports/issue-32-compact-ab/README.md)
retains the public-suite inference and its frozen protocol. The full vocabulary
differs from v1's oracle shortlist; that difference is a comparison confound.
Four-label selection may omit useful aliases; the full Rust
request is logged. Very large authorized tables may still exceed the fixed token
budget; this is a logged backend failure, never silent truncation or narrowing of
scope. Grammar can produce syntactically valid wrong interpretations, invalid IDs,
or incomplete output at the token cap. Independent rejection is safety evidence,
not successful understanding or model abstention.

If compact generation still fails, preserve its raw outputs and failure metrics,
keep v1 available as a reproducible historical baseline, and open a separate
revision experiment. Do not repair outputs, tune on sealed holdout, relabel prior
failures, or claim a feasibility pass. The externally sealed 60-case holdout is
outside this workflow.
