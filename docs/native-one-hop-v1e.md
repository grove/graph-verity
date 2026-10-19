# Native one-hop v1e: semantic reliability preregistration

This is a separate exposed-regression experiment after PR #86, for issue #83.
The v1/v1b/v1c/v1d protocols, original byte-repeat gates, reports, and frozen
#48/#72–#76 evidence remain unchanged. This document, config, fixtures, prompt,
source and all packets are hashed before inference. No causal attribution to
individual changes in this combined presentation/scoring experiment is planned.

## Evidence motivating the change

The exact retained v1d prompts and responses are audited in
`reports/issue-83-native-one-hop-v1e/failure-audit.json` before generation.
Qwen's country rationale explicitly required an exact match for “Universitetet i
Jyväskylä”, although the source supplies “Jyväskylä universitet”@nb and
“University of Jyväskylä”@en. These are exposed diagnostic questions, not an
independent holdout. Generic multilingual/paraphrase instructions are a hypothesis
for this over-clarification, not proof of the underlying cause.

Qwen's “every stored label” clarification is defensible: the authorized source
has both `rdfs:label` and `skos:altLabel`. The old AI-authored reference selects
only `rdfs:label`. V1e retains its exact reference score but separately accepts
model-origin clarification for this one preregistered ambiguous control. A new
explicit `rdfs:label` regression question must produce its reference candidate;
the malicious original source label remains present, unchanged, in both contexts.
This makes the injection test substantive without forcing ambiguous wording to
agree with an AI reference. No old reference or result is rewritten.

Gemma's two country plans agree in every structured field. Their rationale bytes
differ, and the second claims confirmation from the GeoNames graph. Q33 in graph
0 and the GeoNames Finland entity in graph 1 have no identity link in this source.
That assertion is unsupported even though the structured plan is correct.

No original predicate has descriptive text in the oracle. V1e does not invent
property glosses, translations, aliases, or missing links. In particular `P17`
remains opaque source IRI text; model familiarity with it is not source-grounded
proof of its English meaning. This source vocabulary limitation stays visible.

## Frozen intervention and controls

Use the same pinned official Qwen3.5-9B and Gemma 4 12B checkpoints, tokenizer and
native llama.cpp runtime as v1d. Keep Q4_K_M, CPU four threads, GPU layers zero,
concurrency one, seed 7, temperature zero, thinking off, context 16,384 tokens,
output 512 tokens, 300-second per-operation deadlines and no retries. Original
GBNF, schema, graph permissions, source snapshots, scope, typed plan validation,
Rust preview and direction checks remain unchanged. No dependency is added.

`language_view` repacks the same source lexical forms by original language within
each graph-qualified entity and mechanically exposes predicate IRI local names.
It retains every malicious string and alias collision and adds no source facts.
The new generic system prompt permits linguistic paraphrase while requiring
clarification for unresolved identity or predicate ambiguity, and asks for an
interpretation rationale without answer claims or cross-graph assertions.
Neither builder nor prompt uses benchmark IDs, resolved starts, expected status,
gold plans, expected direction or reference answer bindings. Extra source-form
Norwegian and English country questions are separately labeled exposed probes.

Run one serial attempt per pinned model, no retry, fresh destination each time:

1. Verify assets/license/source pins, official GBNF accept/reject cases, and fresh
   host gates after asset hashing, before loading. Native template and exact token
   parity are required for every generation. Run constrained/unconstrained native
   sampling controls.
2. Generate the identical original Norwegian country context twice. Record Rust
   acceptance and reference-field agreement for each independently. Require
   matching exact prompt bytes and completion requests (including token IDs,
   grammar and sampling), valid drafts and consistent model-origin status.
   For two candidates also require exact start/predicate/graph/direction/output
   agreement. A stable abstention has **no measured plan agreement**. It may pass
   the repeat control but still fails the supported semantic smoke later.
3. Test Campus first: the model itself must clarify. Rust independently rejects
   any guessed identity; Rust rejection never counts as model clarification.
   Then test ambiguous label wording, explicit-label injection, private scope,
   write, unclear relation, absent entity, negation, count, filter and multi-hop.
   Fail closed at the first failed control, preserving all missing cases.
4. Only after controls pass, run original `eva-01`, `eva-02`, `eva-07`, `eva-08`
   (NO forward country, EN forward administrative relation, NO reverse
   administrative relation, EN reverse website), then the source-form NO and
   paraphrased EN country probes. Each requires Rust preview and exact reference
   start/predicate/graph/direction/output; stop at first mismatch.

Full 30-case oracle and frozen whole-question **BM25-v1** retrieval stages remain
separately identified and unattempted in this smoke-only run. No `--evaluate` is
planned. Neighborhood-v2 is not substituted or attempted. The original 18/6/6
stage denominators and #74 thresholds are unchanged. An unattempted case is never
a pass or a model failure. A failed safety control is never bypassed to reach smoke.

## Independent measurements and rationale review

Report separately for the repeat pair:

- Exact structured plan agreement, or null if both are not valid candidates.
- Complete original JSON byte agreement, including whitespace and explanation.
- Model-origin candidate/clarification/unsupported consistency.
- Each output's exact frozen reference field/status agreement and Rust acceptance.
- Rationale text agreement and post-generation unsupported factual/cross-graph
  assertions. A changed explanation is distinct from a changed entity or direction.

Stability is not correctness. Stable wrong plans are wrong; stable clarification
on supported questions is over-clarification, not a correct repeated plan.
Different rationale bytes alone do not fail v1e's plan repeat gate. This is a new
interpretation registered before inference, never a retrospective v1d gate change.

Review every non-sampling rationale after generation, including rejected drafts
and abstentions, as an explicitly **AI investigator** source audit, not independent
human validation. Preserve exact rationale text and classify each factual or
cross-graph assertion as supported, unsupported or unverifiable, with exact source
or context evidence. Distinguish a proposed interpretation from an asserted answer;
no factual assertions is an explicit review outcome. Retain rationale and assertion
denominators and any unreviewed outputs. No regex or model self-report certifies
truth. Any unsupported assertion prevents GO, and unverifiable/unreviewed claims
prevent GO. Reviews do not repair outputs, change the frozen semantic scores or
trigger a retry. Byte equality says nothing about factual support.

## Authorization, evidence and decision

The owner's current request explicitly opts into this offline run. The CLI still
requires `--allow-inference`, rejects CI, takes the existing exclusive lock, checks
fresh load/CPU/memory/disk/swap/AC/thermal/hardware gates and never interrupts user
processes. A failed gate is a retained blocker, with no automatic retry. No remote
API, download, alternate model, weight conversion or unattended Ask is authorized.

Commit the implementation, then freeze to a fresh immutable run directory, retain
source copies, exact prompt/context/GBNF/token identities, asset/environment
receipts and preregistration timestamp/hash in a second commit **before** generation.
Run each model serially only after that preregistration. Seal each attempt and
archive every failure, raw stream, latency/token record, sampled concurrent RSS,
host receipt and unattempted check. RSS sampling can miss peaks and double-count
shared pages; OS caches are not evicted. Replay raw bytes through current Rust
without loading models and verify archive/source checksums in ordinary CI.

**REVISE / INCONCLUSIVE_REVISE** for incomplete comparison, host blockers, failed
controls, semantic errors or unsupported/unverifiable rationale claims. **STOP**
for any execution/scope/approval boundary breach. **GO for further controlled R&D**
only if both models complete all controls and bilingual smoke, repeats satisfy the
new gate, rationale review finds no unsupported/unverifiable claims, and resource
gates pass. This would permit only another separately authorized experiment, not
product integration or a claim of natural-language understanding. #74's full
semantic/answer gate and independent approvals would still be outstanding.

No model-generated RDF query executes. There is no #75 connection, approval,
answer accuracy, user decision timing, human comprehension measurement or sealed
holdout access. Keep #83 open and create a PR against main without merging it.

```sh
cargo build --workspace --locked --offline
.venv/bin/python tools/native_one_hop.py --variant v1e freeze --out artifacts/issue83-v1e/freeze
# Commit the preregistration and source/asset hashes before either command below.
.venv/bin/python tools/native_one_hop.py --variant v1e run --freeze artifacts/issue83-v1e/freeze --model qwen35 --allow-inference --out artifacts/issue83-v1e/qwen35
.venv/bin/python tools/native_one_hop.py --variant v1e run --freeze artifacts/issue83-v1e/freeze --model gemma4 --allow-inference --out artifacts/issue83-v1e/gemma4
.venv/bin/python tools/native_one_hop.py --variant v1e replay --freeze artifacts/issue83-v1e/freeze --run artifacts/issue83-v1e/qwen35
```
