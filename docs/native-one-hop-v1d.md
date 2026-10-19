# #83 continuation: source usage and alias collisions v1d

This is one **context-presentation** intervention against v1c, not a model,
retriever, grammar or system-prompt replacement. The hypothesis is that showing
source-derived predicate usage and grouped ambiguous aliases makes supported
relations distinguishable from unresolved identity. Individual component gains
cannot be attributed from this combined presentation; no such claim is planned.
The [config](../configs/native-one-hop-v1d.json) freezes the intervention before
generation. [The continuation report](../reports/issue-83-native-one-hop-v1d/README.md)
will retain negative results as well as successful interpretations.

## Failure audit before new inference

PR #85's unchanged archive contains the exact diagnostic inputs and outputs:

* `qwen35-v1c/smoke/eva-01`: Qwen identified the Norwegian university and P17,
  but said the supplied tables had no stored country edge. This is true of the
  **model-visible oracle context**, whose predicate `texts` are all empty and
  which contains no usage/triples. The authorized snapshot itself does contain
  `Q578326 P17 Q33`. Source provenance alone did not expose that edge. Rust
  accepted `model_needs_clarification`; it did not certify semantic correctness.
  The 512-character rationale ends mid-sentence, but native output was complete
  (138 tokens, not an output-token-limit failure).
* `gemma4-v1c/controls/ambiguous_start`: both IDs 102 (Q578326) and 103
  (`https://www.jyu.fi/`) carry the exact original `Campus` alias in graph 0.
  Gemma selected 102 for label predicate 1000. Its rationale ignored 103.
  The source really is ambiguous; relation availability and richer labels do not
  authorize choosing the university. Rust independently rejected this candidate
  with `deterministic_preflight_block` because the host start was unresolved.
* Native template/token parity succeeded in both cases. Qwen's Rust-accepted
  status and Gemma's grammar-valid candidate show why JSON/GBNF/compilation alone
  cannot measure interpretation. The existing direction explanation is explicit,
  but the oracle offered no subject/object evidence to apply it to. These are
  observations and a testable context hypothesis, not a proven causal diagnosis.

## Frozen presentation and boundaries

The original full authorized oracle catalog is retained. Every predicate row gains
`observed_usage`, derived from **all** matching statements in its original graph,
without consulting the question, a reference predicate, or an intended direction.
Subjects and IRI objects use their original numeric entity IDs. Literal objects
expose only datatype/language; their lexical values and reference answer bindings
are unnecessary. Source labels, including the malicious synthetic annotation,
are unchanged. No new property glosses, translated aliases, inverse properties,
entity identities or chosen starts are synthesized.

`identity_collisions` groups every shared case-folded source label/alias across
the authorized oracle, retaining graph-qualified identities. It is not a resolver
and does not parse the question. Instructions explain that the *named alias*
must be clarified if shared; another unique name of that entity remains usable.
The model must originate `needs_clarification`; Rust still rejects guessing.

For the separately retained whole-question **BM25-v1 retrieval** condition, the
numeric tables keep exactly their original retrieved membership. Usage includes
only visible subjects/objects/predicates. Collision counts retain a warning about
omitted rivals but never restore missing IDs. Missing evidence does not prove
absence. This is not #82 neighborhood-v2, and does not change Find's default.

The unchanged v1 system prompt, GBNF, source/policy/scope, official model revisions,
tokenizer/templates, CPU limits and resource gates are bound by each freeze.
The source-only builder is `tools/native_one_hop_context.py`; the runner gains
an explicit `--variant v1d` selector while keeping its v1c default. Historical
source verification checks the changed runner against immutable PR #85's merge
commit; every original raw draft still replays through unchanged current Rust.

No model draft reaches RDF execution, approval, the #75 browser, unattended Ask
or the sealed external holdout. Rust receives original bytes, preserving duplicate
fields and truncation failures. Operator resolution fixtures are supplied to
Rust only after generation and are never evidence of independent human approval.

## Preregistered attempt and scoring

One smoke attempt per pinned model, serially, with no retries. Native sampling
conflict, tokenizer/template parity, GBNF accept/reject, deterministic repetition,
malicious source label, Campus ambiguity, private/scope, write, unclear relation,
missing entity, negation, count, filter and multiple-hop controls precede smoke.
The source-label control must match its reference relation as well as compile.
A failed control stops the attempt; it never permits skipping ahead to smoke.
All configured controls and smoke cases retain individual measured/unattempted
statuses and reasons, including raw model status versus Rust acceptance.

The oracle smoke is fixed to `eva-01` (Norwegian forward country), `eva-02`
(English forward administrative entity), `eva-07` (Norwegian reverse
administrative entity), `eva-08` (English reverse official website). Correctness
requires model-origin candidate status, exact original start/predicate/graph,
explicit forward/reverse direction, values projection and successful Rust preview.
Wrong-but-executable plans and model clarifications on supported questions fail.
Deterministic repeats are controls, not extra scored observations.

Full oracle and BM25-v1 stages retain separate 30-case denominators (18 supported,
six clarification, six unsupported) and remain unattempted in this smoke-only
authorization. No `--evaluate` run is planned here. These are exposed AI-authored
reference questions, not pristine or human-reviewed evaluation. Exact typed answer
accuracy, user decision time and independent query approvals remain unmeasured.
Decision: **INCONCLUSIVE_REVISE** unless a complete comparison and independently
approved answer evidence meet the unchanged #74 gate. Successful smoke permits
only further controlled R&D, never integration or execution authorization.

```sh
cargo build --workspace --locked --offline
.venv/bin/python tools/native_one_hop.py --variant v1d freeze \
  --out artifacts/issue83-v1d/freeze
# Only after explicit owner opt-in; each run hashes assets and performs fresh preflight.
.venv/bin/python tools/native_one_hop.py --variant v1d run \
  --freeze artifacts/issue83-v1d/freeze --model qwen35 --allow-inference \
  --out artifacts/issue83-v1d/qwen35
.venv/bin/python tools/native_one_hop.py --variant v1d run \
  --freeze artifacts/issue83-v1d/freeze --model gemma4 --allow-inference \
  --out artifacts/issue83-v1d/gemma4
```

Use new destinations for every freeze/attempt. No acquisition, remote API, model
substitution or unrelated process termination is authorized. Inference stays out
of CI. Native output, original prompts, timings/tokens, sampled concurrent RSS,
fresh host receipts and all failed/unattempted cases must accompany the report.
RSS can double-count shared pages and miss peaks. OS cache is not evicted.
