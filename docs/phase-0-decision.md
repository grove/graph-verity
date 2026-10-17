# Phase 0 decision: stop tested unattended Ask; build Find first

**Decision date: 17 October 2026.** Engineering disposition for [#10](https://github.com/grove/graph-verity/issues/10), under [Phase 0 epic #2](https://github.com/grove/graph-verity/issues/2).

**STOP unattended, free-form Ask with the tested Qwen2.5-1.5B-Instruct Q4_K_M v1 and compact-v2 configurations. REVISE the product direction to a narrow Find-first MVP.** The deterministic RDF foundation remains useful. This decision does not say every small language model is unsuitable, and it does not implement Phase 1.

The experiments repeatedly failed to map public Norwegian questions to the expected plans and answers, even with authorized vocabulary supplied. A compact output contract improved syntax but delivered neither correct complete answers nor correct model abstentions. Retrying the identical setup or opening the sealed holdout would not repair that evidence. A new model hypothesis would require a separately versioned experiment.

**Formal gate status remains NOT READY, not GO.** This is an evidence-backed engineering STOP/REVISE, not a formally preregistered, expert-validated feasibility result. The external sealed holdout has not been evaluated; its independence and expert gold correctness are not established. No private holdout material was accessed for this decision. Human review was waived for exploratory engineering only, not performed or replaced by invented attestations.

The [machine-readable decision record](phase-0-decision.json) copies measured facts and exact identities from checksum-bound public sources. It is a decision record, not a new inference run or approval/freeze receipt. Retained reports remain historical, including their then-current status wording.

## What Phase 0 delivered

The working Rust foundation imports bounded RDF into immutable snapshots, catalogs authorized vocabulary, resolves exact identifiers/labels, validates typed query IR, compiles read-only SPARQL, executes in Oxigraph and returns bounded supporting triples with graph/snapshot provenance. It supports directed joins, typed comparisons, distinct counts, grouping and explicit scopes. Schema, reference-query and security regression tests run without a model. Compact v2 adds a separately typed indexed proposal contract and deterministic expansion through the existing compiler.

Actual CPU inference, runtime/grammar controls, public question evaluation, saved-output replay, uncertainty reporting and immutable evidence archives were also implemented. Successful evaluation infrastructure exposed unsuccessful model behavior. Neither a closed issue nor green model-free CI means a semantic-quality gate passed.

## Measurements and counterexamples

### Original v1 versus compact v2: 30 public adversarial questions

Source: [retained controlled comparison](../reports/issue-32-compact-ab/README.md), [comparison JSON](../reports/issue-32-compact-ab/comparison.json), [all 30 case outcomes](../reports/issue-32-compact-ab/case-comparison.md), and [original v1 report](../reports/issue-9-adversarial/README.md).

<!-- decision-adversarial-table -->
| Metric | v1 | Compact v2 |
|---|---:|---:|
| Valid JSON/contracts | 22/30 | 28/30 |
| Invalid contracts | 8/30 | 2/30 |
| Correct complete answers | 0/24 | 0/24 |
| Correct model abstentions | 0/6 | 0/6 |
| Executed proposals | 4/30 | 0/30 |
| Wrong-but-executable plans | 4/30 | 0/30 |
<!-- /decision-adversarial-table -->

Both ontologies have 12 supported questions and three expected abstentions: **0/12 answers and 0/3 correct abstentions in each route and ontology**. All 30 expected behaviors fail, including when answers are separately aligned by projection position. Rejections and incomplete JSON remain in the supported-question denominator. Each case received one attempt, with no retries or backend failures.

V1's outcomes are eight invalid contracts, 18 Rust validation rejections and four executions. V2's outcomes are two invalid contracts, 24 expander-only rejections and four deterministic preflight blocks. All 28 decoded v2 proposals are candidates; none is a model abstention. **Zero v2 wrong executions means containment and rejection, not successful interpretation.** The preflight covers alias ambiguity and open-world negation in both ontologies. It is explicitly attributed to deterministic code rather than credited as model abstention.

Descriptive **95% Wilson intervals**:

<!-- decision-interval-table -->
| Proportion | v1 95% interval | Compact v2 95% interval |
|---|---:|---:|
| Contract valid / 30 | 55.6–85.8% | 78.7–98.2% |
| Invalid contract / 30 | 14.2–44.4% | 1.8–21.3% |
| Complete answer / 24 | 0.0–13.8% | 0.0–13.8% |
| Correct abstention / 6 | 0.0–39.0% | 0.0–39.0% |
| Wrong execution / 30 | 5.3–29.7% | 0.0–11.4% |
<!-- /decision-interval-table -->

These are tiny, correlated, public AI-reference samples, not independent population estimates or a causal test of compactness alone. V1 uses a gold-derived oracle vocabulary shortlist; v2 includes all authorized numeric IDs with up to four labels per ID. Prompts, grammars, representation, preflight enforcement and structural diagnostics differ. The model/runtime, generation budgets, seed, temperature, threads, questions, graph data and references are pinned. The complete comparison discloses strict named-binding and positional scoring separately.

Four substantive v1 failures survived authorization and executed ([forensic detail](issue9-forensic-analysis.md)):

- **Inverse:** asked who owns a company; generated redundant forward/reverse ownership patterns and the wrong projected columns, returning a nonempty row.
- **Two-hop:** replaced municipality → company → contract with a self-join, returning an empty set despite the correct graph path being present.
- **Ambiguous alias:** selected an employee-value query rather than clarifying which of two `Felles AS` entities was intended; returned three bindings.
- **Transfer negation:** executed a self-join returning zero rows instead of refusing unsupported “no contracts” under open-world semantics.

The other probes cover `>` versus `>=`, date/date-time boundaries, distinct counting under duplicate joins, scope, missing facts/vocabulary and label/comment injection. Original failures include invented/wrong-role predicates, bad variables, changed snapshots and scopes, and eight outputs reaching the 1,024-token cap. V2 still fails all those families: source inverse emits twelve forward edges rather than the requested inverse relationship, exceeding the eight-edge limit; source two-hop uses invalid references. Seven different source questions, including injection questions, produce identical raw bytes. Each ontology has only six distinct v2 proposals (11 overall), compared with 29 overall in v1. Transfer `gt` and `ge` still exhaust 1,024 output tokens. Grammar-valid repetition is not language understanding.

### Earlier 86-question public development experiment

Sources: [original PR #20 experiment](../reports/local-parser-development/README.md), [baseline with per-family scores and intervals](../reports/phase-0-baseline/summary.md), and [separate development repeat](../reports/phase-0-development-repeat/README.md). These experiments use real Wikidata geography (600 quads) and a GeoNames-derived Schema.org city graph (1,508 quads). The adversarial comparison above instead uses synthetic paired-ontology fixtures; neither is a sealed test.

<!-- decision-development-table -->
| Metric | Wikidata dev | Schema.org transfer_dev |
|---|---:|---:|
| Questions | 46 | 40 |
| Supported / expected abstention | 38 / 8 | 35 / 5 |
| Valid contracts | 41/46 | 32/40 |
| Invalid contracts | 5/46 | 8/40 |
| Strict structural IR agreement | 0/38 | 0/35 |
| Exact answer-binding agreement | 3/38 | 0/35 |
| Correct expected-status abstentions | 0/8 | 0/5 |
| Rust safety rejections | 22 | 24 |
| Executed proposals | 19 | 8 |
<!-- /decision-development-table -->

Answer-binding agreement is **7.9% (95% Wilson 2.7–20.8%)** and **0% (0–9.9%)**. Combined, this is **3/73 supported questions, 4.1% (1.4–11.4%)**; correct abstentions are **0/13 (0–22.8%)**. No model abstention was emitted. Strict IR agreement is 0/38 (0–9.2%) and 0/35 (0–9.9%); correct abstentions are 0/8 (0–32.4%) and 0/5 (0–43.4%). The separate 86-question repeat reproduces every headline quality count; it is not an additional independent benchmark.

All 27 executions disagree structurally with reference plans (19/46 and 8/40 of all questions). That is a **structural disagreement proxy**, not 27 expert-adjudicated wrong answers: `wd-dev-008`, `013` and `018` return reference bindings despite structural differences. Ordered IR and named-column comparisons can reject equivalent renamings. Counterexamples also show real errors: `wd-dev-001` places Oslo's entity IRI in a predicate position, and `wd-dev-021` ends mid-string at the output limit. Component matches can include empty fields; they must not be treated as recovered semantic competence. Historical binding agreement without retained completeness cannot be upgraded to complete-answer accuracy; scoring v2/replay measures completeness separately.

Only the inverse-relation family has nonzero exact development answers (3/4); that small result is counterevidence to “every output is wrong,” not a reliable supported product family. Full per-family precision/recall/F1, sample sizes and bootstrap intervals remain in the baseline JSON. Aggregate macro precision/recall/F1 are 0.0445/0.0548/0.0466; their descriptive bootstrap 95% intervals are 0.0034–0.0959 / 0.0137–0.1096 / 0.0055–0.0959. Failed attempts score zero. The 76 public templated review candidates and eight same-ontology geography candidates were not evaluated as independent holdouts.

### CPU cost, cold observations and memory

All inference used **Apple M1 Pro, 32 GiB RAM, macOS 26.6.2 arm64, four CPU inference threads**, CPU only; Metal, BLAS and Accelerate were disabled. Ten visible logical CPUs does not mean ten inference threads. The model is **Qwen2.5-1.5B-Instruct Q4_K_M**, with **llama.cpp b5046**, revision `74d4f5b041ad837153b0e90fc864b8290e01d8d5`. This is the recorded experimental machine; no broader deployment benchmark is implied.

Times below are seconds, rounded from retained millisecond values. Warm sample counts are 14 per adversarial ontology, 45 Wikidata development and 39 real transfer-development. Each cold observation is one first answer with a fresh server/Rust process. **OS page cache was not evicted**; prompt-prefix caching is enabled. Warm times include failed questions, catalog/prompt work, tokenization, generation, validation and any execution/evidence, excluding independent reference scoring. Cold service time adds startup, but excludes prior asset-hash/grammar probes. Host work was not isolated; these are descriptive, not guaranteed service performance.

<!-- decision-latency-table -->
| Run / dataset | Warm p50 | Warm p95 | Warm p99 | Process-cold first |
|---|---:|---:|---:|---:|
| Original dev / Wikidata | 10.58 | 28.06 | 36.18 | 17.68 |
| Original dev / real transfer | 10.51 | 26.59 | 28.02 | 18.04 |
| Repeat dev / Wikidata | 9.61 | 26.04 | 32.52 | 16.80 |
| Repeat dev / real transfer | 9.35 | 23.28 | 23.38 | 16.72 |
| Adversarial v1 / source | 11.01 | 23.73 | 23.73 | 17.41 |
| Adversarial v1 / transfer | 13.36 | 27.38 | 27.38 | 17.00 |
| Adversarial v2 / source | 34.87 | 60.18 | 60.18 | 109.89 |
| Adversarial v2 / transfer | 53.00 | 80.78 | 80.78 | 60.66 |
<!-- /decision-latency-table -->

The source report rounds some historical figures differently; the table uses two decimal places directly from its JSON. For the 15-case adversarial distributions p95 and p99 coincide at the retained maximum; these small tails are not stable population estimates.

<!-- decision-token-table -->
| Adversarial raw tokens | v1 input / generated | Compact v2 input / generated |
|---|---:|---:|
| Source | 16,818 / 7,040 | 39,209 / 7,213 |
| Transfer | 16,743 / 8,674 | 38,819 / 12,489 |
| Total | 33,561 / 15,714 | 78,028 / 19,702 |
<!-- /decision-token-table -->

Compact v2 **increased both prompt and generation tokens**, and latency increased. Full authorized tables and lengthy enumerations outweighed representation savings. Eight v1 and two v2 generations hit the output cap; the runtime `truncated` flag remains false in all 30 for each route and is a separate field. Generation round-trip p50/p95/p99 (all 15 cases, seconds) is **11.97/23.73/23.73** and **16.55/27.38/27.38** for v1 source/transfer, **36.84/109.18/109.18** and **53.36/80.77/80.77** for v2. Original development generation percentiles are **10.57/28.05/36.17** and **10.50/26.50/28.01**; generation and warm E2E distributions have different sample inclusion.

Sampled aggregate peak RSS: original development **1,498,304 KiB (1.429 GiB)**, repeat **1,529,616 KiB (1.459 GiB)**, adversarial v1 **1,500,560 KiB (1.431 GiB)**, v2 **1,478,368 KiB (1.410 GiB)**. Sample counts are 3,862 / 4,572 / 1,955 / 5,588. Corresponding OS child-lifetime high-water values are **1,470,624 / 1,487,696 / 1,471,888 / 1,445,760 KiB**. Sampling at roughly 200ms can miss spikes and double-count shared pages; the original development sampler tracked three known processes while later runs track descendants. Grammar-probe/preparation peaks are excluded. Small RAM differences are not demonstrated improvements.

## Gate assessment: approved budgets, incomplete formal experiment

[Proposed gates](../configs/phase-0-gates.proposed.json) originally named Linux/16GiB with no CPU model. The separate [owner approval](../configs/phase-0-approval.json), recorded at `2026-10-17T08:59:26.708429+00:00`, approved the exact numerical/protocol budgets and **M1 Pro/32GiB/four-thread experimental target**. It binds source `d3984494c9dd4a6938eb2a3591f6cd1d13768172`. The proposal files intentionally retain their labels. Approval status is **owner_approved_pending_external_split_integrity**; its external integrity hash is null and freeze validation still fails closed.

The issue #32 input freeze is a real pre-inference freeze for that **public route comparison**, not the missing formal sealed-evaluation preregistration. Approval does not retroactively preregister earlier public experiments or bless changed source boundaries. Thresholds were recorded before any locked evaluation, but the formal freeze, independent split integrity and subsequent operator authorization were not completed. No sealed run was necessary to decide against deploying a setup that already fails development so severely.

| Requirement / numerical budget | Observed evidence | Disposition |
|---|---|---|
| Supported complete exact answers >=95%; every supported family >=90% | Adversarial 0/24 both routes; development raw bindings 3/38 and 0/35; every adversarial family fails | Demonstrable public development failure, not a formal locked estimate |
| Semantic plan accuracy >=95% | Strict IR 0/38 and 0/35; substantive direction/ID/join errors; no correct v2 expanded plan | Failed reference-agreement diagnostic; no expert-equivalence adjudication |
| Correct ambiguous/unsupported abstention >=95% | 0/13 development; 0/6 adversarial each route | Failed |
| False abstention <=10% of supported | Zero model abstentions (0/73 development; 0/24 each route) | Observationally within budget; says little when candidates fail anyway |
| Zero unflagged wrong-plan answers | Four v1 wrong executions; all 27 development executions structurally disagree; no complete user interface evaluated | Unflagged user-facing false confidence **unmeasured**; proxies are not this gate |
| Absolute ontology/time transfer gap <=10 percentage points | Development binding gap 7.9 points; adversarial answer gap zero because both score zero | Descriptive public gaps only; independent ontology/time generalization unavailable |
| Zero unauthorized execution/scope disclosure; zero raw-SPARQL/write execution | Adversarial 0/30 per route for scope, private/comment-canary and non-read-only observations; no shell canary created | Bounded containment evidence; complete UI/disclosure audit unavailable |
| Warm E2E p95 <=10s | 23.28–28.06s across development/repeat datasets; 23.73/27.38s v1, 60.18/80.78s v2 adversarial | Failed on measured CPU |
| Process-cold first answer <=30s | Development/repeat and v1 under 30s; v2 109.89/60.66s | V2 failed; single cached-page observations, not uncached-disk guarantees |
| Whole-process peak RSS <=8GiB | Sampled aggregate peaks 1.410–1.459GiB | Observed under budget with sampling limitations; not an OS memory limit |
| Oracle regression fraction =1 | 38 Wikidata + 35 real-transfer executable references pass deterministic checks | Compiler engineering passes; abstention fixture bookkeeping is excluded |
| Independent human gold review; independent locked split | Human ledger empty; exploratory-only owner waiver; external integrity hash absent | Not achieved; no formal GO |
| Proposed formal minimums: 100 supported +20 abstentions per dataset; five supported per family | Development 38/8 and 35/5; adversarial 12/3 each; external candidate metadata 50/10 total | Insufficient; candidate alone cannot meet minimums |
| Formal preregistration and authorized independent target evaluation | Pending approval/freeze boundary; no external evaluation | Unavailable, not waived by this decision |

Zero observed security failures in 30 attempts has Wilson upper bound **11.4%** per route, under an independent-binomial description that these correlated probes do not actually satisfy. In v2 no plan executes, so there is no evidence of a positive-query path that is both useful and safe. Similarly, a zero ontology gap between two zero-accuracy samples cannot show successful transfer. Reliable discovery, semantic interpretation, abstention, user-visible confidence and security each require their own evidence.

The [evaluation protocol](phase-0-evaluation.md) and [engineering-only AI-gold waiver](phase-0-ai-gold-risk-acceptance.md) remain intact. Formal independence, human expertise and lineage cannot be authenticated by checksums. The holdout is neither opened nor regenerated; no review record is fabricated. This decision retires the tested unattended Ask approach without claiming those unmet GO prerequisites passed.

## Selected next scope: a Find-first MVP

A user should be able to **locate a relevant RDF entity, inspect its relationships, follow a connection and view the supporting triples with source-graph and snapshot provenance**. Begin with the retained licensed snapshots and local CLI structure. Production ingestion and a hosted service are unnecessary to test this value.

| Milestone / issue | Scope and dependency | Estimate (one maintainer) | Completion / success criterion |
|---|---|---:|---|
| M1 [#36: vocabulary/entity catalog](https://github.com/grove/graph-verity/issues/36) | Extend existing authorized catalog: Norwegian/English labels, observed aliases, IDs, descriptions; deterministic scope-filtered index | 3–5 days | Every eligible retained resource indexed reproducibly; no unauthorized IDs, labels or counts; graph/index manifests match |
| M2 [#37: lexical baseline](https://github.com/grove/graph-verity/issues/37) | After M1, BM25 or comparable lexical ranking for entities, predicates and descriptions; freeze retrieval judgments/splits | 4–6 days | Reproducible Recall@1/5/10/50, MRR@10, per-language/family intervals, latency/RAM and failures; bounded scoped query CLI |
| M3 [#38: EmbeddingGemma evaluation](https://github.com/grove/graph-verity/issues/38) | After M2, pin exact Google checkpoint/tokenizer/license/quantization/runtime and compare embeddings and a declared fusion to BM25 | 4–7 days | Measured adopt/reject decision using the same judgments, raw ranks, costs and scope controls; rejection is a valid completion |
| M4 [#39: Find MVP](https://github.com/grove/graph-verity/issues/39) | After M3's decision, scoped ranked search, entity detail, directed graph navigation, triples/provenance; BM25 may ship alone | 5–8 days | Offline Norwegian/English query → entity → connection → evidence walkthrough, scope/truncation tests and release evaluation |
| M5 [#40: optional constrained Ask](https://github.com/grove/graph-verity/issues/40) | After M4 and a separate product decision; deterministic explicit intent selection or readable plan confirmation | 3–5 days, optional | No execution without selection/confirmation; reuse typed IR/validation/read-only SPARQL/evidence; measure misunderstanding and false confidence |

M1–M4 total **16–26 engineering days**, approximately **4–6 working weeks** allowing integration, excluding external review, asset/license access and unexpected runtime incompatibility. M5 is not on the Find release critical path. These are planning estimates, not a promised delivery date. No new dependencies or Phase 1 implementation are added by this decision.

Proposed **future Find pilot targets**, distinct from approved Phase 0 Ask gates: freeze at least 80 retrieval queries (40 Norwegian/40 English), with disclosed relevant-ID judgments, lineage and separate tuning/evaluation formulations; cover entities, predicates, descriptions, ambiguity and no-match cases. Aim for Recall@10 >=0.90 and MRR@10 >=0.75 overall, at least 0.80/0.65 in each language. Report denominators, descriptive intervals and failures. A stakeholder quality claim requires genuine human review; absent that, label results exploratory AI-reference relevance agreement.

Pin the CPU, four-thread configuration and actual corpus size before evaluation. Proposed lexical warm p95 <=500ms, embedding/fused E2E p95 <=1s, aggregate peak RSS <=4GiB on a frozen pilot corpus capped at 10,000 resources. Report cold/warm p50/p95/p99, build cost and index size; the tiny retained graphs cannot establish 10,000-resource or production performance. Adopt embeddings only for >=0.05 absolute Recall@10 or >=0.03 MRR@10 gain, no >0.02 per-language regression, and within latency/RAM budgets. Inconclusive evidence keeps BM25; revise the pilot rather than hiding failed criteria.

**EmbeddingGemma is a retrieval experiment, not a replacement question-to-query parser.** The initial candidate is [Google's `google/embeddinggemma-300m`](https://huggingface.co/google/embeddinggemma-300m), whose model card identifies text embeddings and Gemma usage terms. M3 must record an immutable upstream revision and exact weight/tokenizer/license hashes, local runtime/build, quantization or explicit unquantized dtype, conversion provenance, query/document prefixes, pooling/normalization and dimensions **before measuring it**. Those assets have not been selected/downloaded here; no missing model/runtime hash is invented. Do not silently conflate this candidate with another EmbeddingGemma generation, assume an ONNX export works, or assume embeddings beat lexical search. Check reference/runtime parity, Norwegian Unicode and truncation with fixed strings. The old broad architecture's EmbeddingGemma references are design alternatives, not an implemented model pin.

**Out of scope:** production-scale ingestion, unrestricted query generation, unattended free-form Ask, full SHACL support (no SHACL runtime scheduled for this MVP), GNNs, training/fine-tuning, rerankers without baseline evidence, production HTTP serving/hardening and unsupported assertions of verified real-world truth. Even a future SHACL subset needs its own requirement, pinned semantics and differential tests; it is not a prerequisite for this Find pilot.

## What “verified” will mean to a user

| Claim | What is established | What remains unknown |
|---|---|---|
| Ranked Find result | A retrieval method ranked authorized records for the query | Whether it found every relevant entity or understood a formal question |
| Correct interpretation | A selected/confirmed plan describes the intended operation, subject to measured user understanding | Grammar/type validity alone cannot establish this |
| Successful RDF query execution | The validated plan executed against the declared scoped snapshot; completeness/truncation is explicit | Whether the plan expresses the original question |
| Supporting evidence | These source-graph triples in this snapshot support those returned bindings | Whether the source is complete, current or factually correct |
| Real-world truth | Not established by retrieval, SPARQL execution or provenance | Requires external evidence and domain judgment |

Preserve IR/compiler authorization, source/snapshot identity, exact resolution, explicit origins, bounded evidence, typed comparisons and deterministic rejection in every continuation. Treat RDF labels as data; scope filtering must precede indexing statistics, ranking, snippets and navigation. Top-k results are partial discovery, and absent triples remain unknown under the open-world contract. Optional Ask requires explicit intent selection or confirmation showing relations, directions, operands and graph scope; no confirmation can certify real-world truth.

## Workstream reconciliation and closure boundary

Status inspected from GitHub on 17 October 2026; merged PRs were checked rather than inferred from stale document checklists.

| Issue | GitHub state at decision preparation | Merged implementation/evidence | Outcome |
|---|---|---|---|
| [#2](https://github.com/grove/graph-verity/issues/2) | Open, final reconciliation pending | [#1](https://github.com/grove/graph-verity/pull/1), cumulative work below | May close as Phase 0 completed with a negative result after this decision merges; never a successful feasibility demonstration |
| [#3](https://github.com/grove/graph-verity/issues/3) | Closed | [#11](https://github.com/grove/graph-verity/pull/11), [#14](https://github.com/grove/graph-verity/pull/14) | Working workspace/CI |
| [#4](https://github.com/grove/graph-verity/issues/4) | Closed | [#13](https://github.com/grove/graph-verity/pull/13), [#17](https://github.com/grove/graph-verity/pull/17) | Licensed real snapshots and explicit limitations |
| [#5](https://github.com/grove/graph-verity/issues/5) | Closed under exploratory waiver | [#15](https://github.com/grove/graph-verity/pull/15)–[#18](https://github.com/grove/graph-verity/pull/18) | Benchmark preparation; expert review not achieved |
| [#6](https://github.com/grove/graph-verity/issues/6) | Closed | [#12](https://github.com/grove/graph-verity/pull/12), [#13](https://github.com/grove/graph-verity/pull/13), [#19](https://github.com/grove/graph-verity/pull/19) | Deterministic compiler/evidence, not semantic proof |
| [#7](https://github.com/grove/graph-verity/issues/7) | Closed | [#20](https://github.com/grove/graph-verity/pull/20) | Actual public CPU spike; negative model result |
| [#8](https://github.com/grove/graph-verity/issues/8) | Closed | [#21](https://github.com/grove/graph-verity/pull/21)–[#25](https://github.com/grove/graph-verity/pull/25) | Evaluator, completeness fix, guarded external path, budget/target approval; formal preregistration and locked evaluation still incomplete |
| [#9](https://github.com/grove/graph-verity/issues/9) | Closed; behavioral pass not achieved | [#26](https://github.com/grove/graph-verity/pull/26)–[#29](https://github.com/grove/graph-verity/pull/29) | Regressions, retained failures and containment; this decision records STOP/REVISE rather than declaring behavior passed |
| [#10](https://github.com/grove/graph-verity/issues/10) | Open, this decision | Decision PR linked on issue at publication | Close after merged decision, passing verification and linked next scope |
| [#30](https://github.com/grove/graph-verity/issues/30) | Closed | [#33](https://github.com/grove/graph-verity/pull/33) | Compact contract/expander implemented |
| [#31](https://github.com/grove/graph-verity/issues/31) | Closed | [#34](https://github.com/grove/graph-verity/pull/34) | Pinned opt-in runner and boundary controls |
| [#32](https://github.com/grove/graph-verity/issues/32) | Closed | [#35](https://github.com/grove/graph-verity/pull/35) | Measured syntax improvement, semantic failure and greater CPU cost |

PR #23 was merged into a stacked branch and reached main via #24; #27's measured files reached main through #28. Their evidence is present on the decision's base main `260033a6c4b12ddd232ff33d0277fc796c3e5927`.

Epic #2's decision exit can legitimately be met by falsifying the tested unattended approach. Reconcile its stale workstream checklist and record the unmet GO prerequisites separately. The numeric proposals and owner budgets are recorded before any locked evaluation, but the incomplete formal freeze must not be checked off as complete. Closing this exploratory phase after STOP/REVISE does not waive independent validation for a future Ask release. Find has a separate future evaluation plan; it is not declared feasible by this document. If merge/CI is blocked, #10 and #2 must stay open pending publication.

## Exact retained identities and reproducibility

The appendix below is extracted from retained run manifests and the [#32 freeze](../reports/issue-32-compact-ab/freeze.json). SHA256 denotes file bytes; Git revisions are explicitly labeled. The JSON record also retains full artifact maps, model configuration, build receipt, schema/compiler binary hashes and source revisions for original development, repeat and adversarial routes. No vector/index hash exists: retrieval was disabled. V2's authorized tables are request-specific and archived with their hashes, not a single invented global index.

<!-- decision-identities -->
| Identity | Exact value |
|---|---|
| Model GGUF SHA256 | `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` |
| Qwen upstream Git revision | `91cad51170dc346986eccefdc2dd33a9da36ead9` |
| llama.cpp Git revision | `74d4f5b041ad837153b0e90fc864b8290e01d8d5` |
| llama.cpp source archive SHA256 | `8dd9fcc7c17f972673960ffdcc7521f52de5a9ec594aa6acebd9dfd8c17c0a5c` |
| llama-server binary SHA256 | `4353db648294cf6558050f5ddeadc3942b6d219d752697cbea72e8cde12de08f` |
| Embedded tokenizer | `Same GGUF SHA256 as model; no separate tokenizer file` |
| v1 prompt SHA256 | `bb309cbbe00a0ee8070e59521138c59a5e3de62145b74aaa6aedaa3566af7eb5` |
| v1 grammar SHA256 | `d85c31f9ed45a66f9c2479cae7531eb56442ba9d522499d3c3a6b1f14fb8809e` |
| v1 pinned runtime response-schema SHA256 | `988b32e4a0b5369ed035bfd561c07e3f0944bacd1b6f0bc54ba5927d839838d2` |
| v2 prompt SHA256 | `087b67786c85b5e112e283c9ed8bdf62142608c04f9f12f9e0ff2fecd56fa27b` |
| v2 grammar SHA256 | `080d0dba5b967d569223675c4ec9c4dbe5561779d34038ffd3ded73d3be6fea5` |
| v2 pinned compact-schema SHA256 | `ede9a10a46c609aa5803bd053a1c32dd0126a0b6e5250454db20d8d2de34d3da` |
| Current-at-freeze combined v1 contracts SHA256 | `8815f2522c21fbee6e1ddd5ea012c05f4b037723cc7a30cde38ff14ed491c3c2` |
| v2 source/main Git revision | `3d87b7a2021fa883e720873077ee1218d19448cb` |
| v1 adversarial source Git revision | `f9135015b528615847869082070d1cfd8ad5094f` |
| Original development base Git revision | `94f95a8a78ffc4fae20b4227e0e958aba89cc73c` |
| v1 adversarial compiler binary SHA256 | `389f53bf27c3f903d9502f352673b2114013f81a77c0616c2629ebabeb184630` |
| v2 compiler binary SHA256 | `1dff75f14c9828d21d2b563e21fa04e31e45cc59308f4e46e472a373cd09bd5e` |
<!-- /decision-identities -->

The v1 config pins a historical runtime response schema; it is distinct from the combined contracts file at the later v2 freeze. Original development records a base commit plus exact dirty-worktree artifact hashes; do not present the base commit alone as a pristine source freeze. The repeat likewise preserves its executed Python source hash and development provenance.

| Dataset | Benchmark SHA256 | Graph snapshot-file SHA256 |
|---|---|---|
| wikidata | `e648323dc0a084e992dee106d8431b55c785c65937571c1903825187c9262c7e` | `9e75055676e095fcc387f1fd93146c37b47a448b8e08c5a806ab9be4016ccc6f` |
| worldcities-transfer | `1949d6844d827b6c320753572ee3d05a1982f5ef04eca65fce5fa99a74bec6fc` | `2ee4af13fb312c006c126f9239bdbb25b2e4be10b40bff3adc5d67076f068f13` |
| adversarial | `7f246de9e10e87bc3fed58b8ea5d9f03200e48e525edf4f373fec5ef4db0d49f` | `796698f28f645ec3593a85b3db9fc805839ebff101027cb8ec098b72f02ee3ba` |
| adversarial-transfer | `593d38889ce8d2836598011f6d4b7a5c1dc465c289d394fd284ac18106000aa4` | `bd09722df63c16135a060c3c2ed3d79efcaee20de5ba5c4751092aed9d9266b3` |

Model Apache-2.0 and runtime MIT attribution/build receipts remain in the retained experiment documentation. Graph licenses and importer transformations are separate. The JSON record retains policy, configuration, runner, catalog/expander, compiler and lock hashes; the public archive manifests retain every per-case prompt/request/raw-output hash.

Model-free verification (from repository root; no weights or inference):

```sh
.venv/bin/python tools/compact_ab.py
.venv/bin/python tools/phase0.py verify reports/issue-32-compact-ab/manifest.json --check-inputs
.venv/bin/python tools/phase0.py verify reports/phase-0-baseline/manifest.json
.venv/bin/python tools/phase0.py verify reports/phase-0-development-repeat/manifest.json
.venv/bin/python -m unittest discover -s tools -p 'test_phase0_decision.py' -v
.venv/bin/python tools/verify_pre_llm.py
```

The original baseline/repeat manifests verify retained outputs without comparing historical source hashes to a newer checkout. The compact comparison verifies its pre-inference input freeze, both evidence archives and inner manifests and recomputes scores from saved public outputs. Ordinary CI additionally replays all 30 saved v2 strings through Rust, runs source/reference checks, formatting, Clippy, Rust and Python tests. Checksums establish byte integrity, not signatures or human expertise. Decision consistency tests bind copied measurements, intervals, timings, tokens, RAM, identities and local links to retained sources; GitHub existence/state is inspected at publication rather than making offline CI depend on GitHub.

Issue #48's separate [Qwen3.5-9B / Gemma 4 12B experiment](grounded-model-experiment.md)
tests new model proposals under its own exploratory criteria. It does not revise
this decision or its gates. Any model integration needs a separate explicitly
approved issue and human false-confidence evaluation; Confirmed Ask remains
deterministic and model-free by default.
