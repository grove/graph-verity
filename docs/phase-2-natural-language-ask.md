# Phase 2 — Grounded natural-language RDF question answering

**Status:** active R&D roadmap; implementation issues open, not a product GO  
**Date:** 18 October 2026  
**Tracking milestone/epic:** [#71 — Grounded natural-language RDF question answering](https://github.com/grove/graph-verity/issues/71)  
**First user-facing deliverable:** [#75 — Opt-in natural-language Ask prototype](https://github.com/grove/graph-verity/issues/75)

## 1. Product north star

**Graph Verity exists to let people ask natural-language questions about RDF knowledge graphs, in Norwegian or English, and obtain source-grounded answers without writing SPARQL or assembling the graph path themselves.**

The project originally chose a Find-first implementation after the tested small-model semantic parsers failed its feasibility criteria. That was a sensible **engineering fallback and foundation**, **not a new product mission**. The product-level answer to “What is Graph Verity for?” is **grounded natural-language RDF question answering**.

Accordingly:

- **Ask** is the intended primary interaction.
- **Find / graph navigation** are explicit troubleshooting, disambiguation and expert-inspection tools.
- **BM25 and EmbeddingGemma 2** are vocabulary retrieval components, not answer generators.
- **Rust validation and embedded Oxigraph** are the bounded source-of-record query path.
- **Research Review** exists only to evaluate retrieval, not as an everyday interface.

The earlier [Explore vs Research Review UX brief](find-and-research-review-ux.md) compares two *supporting surfaces*. It does **not** define or supersede the project's primary natural-language Ask experience. This Phase 2 document governs that product direction.

### The question users should be able to ask

> **User:** «Hva er hovedstaden i Norge?»  
> **System's untrusted interpretation:** Start at the RDF entity for Norway (Q20); follow the graph's capital predicate (P36) **forward**; return distinct terminal RDF values.  
> **User:** Reviews the complete interpretation and explicitly approves this one query.  
> **Graph-supported answer:** Oslo (Q585), with the original Q20 → P36 → Q585 statement, authorized named graph, snapshot and provenance.

A second directed example:

> **User:** “Which country lists Oslo as its capital?”  
> **System's untrusted interpretation:** Start at Oslo (Q585); follow the same P36 relationship **in reverse**; return terminal countries.  
> **User:** Must see and approve that reverse direction before execution.

These are **target behaviors and existing source-graph examples**, not claims that a language model currently performs them reliably.

## 2. The target flow, with trust boundaries

\`\`\`text
  Natural-language question, Norwegian or English
                 |
                 v
  Authorized graph vocabulary discovery
  BM25 baseline -> bounded candidate IDs and graph/source witnesses
  EmbeddingGemma 2 only as separately approved research variant
                 |
                 v
  Constrained local model: untrusted ONE-HOP draft
  (start candidate, predicate candidate, graph, forward/reverse,
   values) OR asks for clarification / reports unsupported
                 |
                 v
  Deterministic Rust ID resolution and verification
  (snapshot, scope, exact graph-qualified IRI, predicate, direction,
   contract, output and operator-set limits)
                 |
                 v
  AUTHORITATIVE RUST PLAN PREVIEW — no execution
                 |
                 v
  Explicit independent user confirmation of this exact plan?
          / cancel | stale | ambiguity \     \ approve once
         v                            v             |
  no execution                  clarification        v
                                            Rust read-only compiler
                                                    |
                                                    v
                                             Oxigraph execution
                                                    |
                                                    v
                                   Typed RDF bindings + source triples
                                   named graph, snapshot, license,
                                   row/evidence limits + uncertainty
\`\`\`

| Step | Authority | What it cannot prove |
| --- | --- | --- |
| Retriever | Graph-authorized source and retrieval policy | Whether a candidate means what the question asks |
| Local model | No authority: proposes references into a bounded candidate table | Semantic correctness, graph truth or query permission |
| Rust expander/validator | Exact graph, catalog, schema, datatype, snapshot, scope and read-only constraints | That the interpretation matches the question |
| Human confirmation | A deliberate choice to execute **one displayed formal plan** | That the person truly understood it or that model semantics are correct |
| Oxigraph and evidence | Result of the approved query against the retained RDF snapshot | Real-world truth, source completeness or open-world negative facts |

**Never convert “valid JSON,” “successful SELECT,” “nonempty bindings,” or “the user clicked Approve” into a semantic-accuracy claim.** Earlier models produced read-only, executable and **wrong** plans.

## 3. First deliverable: one-hop supervised Ask only

Phase 2's first working slice is deliberately narrower than the existing general typed IR, even though Oxigraph and Confirmed Ask can represent more.

| Dimension | Initially supported | Initially unsupported |
| --- | --- | --- |
| Input | A Norwegian/English natural-language question | A command to run arbitrary SPARQL or filesystem/code operations |
| Graph scope | An **operator-approved**, immutable local snapshot and explicit named graph | Cross-scope graph discovery or private/unlisted graph access |
| Start | One exact, graph-qualified **observed entity** resolved from authorized retrieval | Guessed IRIs, implicit aliases, unbound start variable, silently selected first result |
| Relation | **Exactly one** original RDF predicate and explicit **forward/reverse** direction | Two-hop joins, arbitrary path expressions, negation, SERVICE, inference of unstated inverse facts |
| Output | Distinct terminal RDF values with original term types | Counts, filters, HAVING, aggregates, free-form generated answer strings |
| Model statuses | Candidate draft, clarification request or unsupported request | Fabricated “no facts exist” or correct model abstention inferred from Rust-only preflight |
| Execution | One exact plan after independent user review/approval | Unattended execution, auto-approval, changed/stale approvals or browser replays |
| Evidence | Original source triples, graph/snapshot, source/attribution and independent row/evidence clipping | A declaration of verified external truth |

For example, “How many cities have over 100,000 residents?” should **not** be coerced into the one-hop values template; it requires count/filter semantics not yet in scope. It must be flagged as unsupported or needing a future template. Likewise, “Which cities have no capital?” is not proven by missing RDF triples under open-world assumptions.

After successfully measuring this first slice, separately decide whether to add **two-hop paths, typed comparisons, COUNT(DISTINCT)** and additional natural-language families. The deterministic Confirmed Ask core already supports some of these structures when **manually constructed**; that fact does not authorize model-driven use.

## 4. What prior experiments actually established

### Foundation retained

- The pinned Oxigraph snapshot, graph provenance, typed IR, Rust read-only compiler, bounded execution and independent source-evidence verification are implemented.
- Graph-qualified bilingual vocabulary discovery and **BM25 Find** are implemented, with real RDF source witnesses and conservative ambiguity/no-match outcome types.
- A **manually selected**, experimental Confirmed Ask flow exists with an authoritative preview and explicit approval.
- EmbeddingGemma 2 and selective hybrid show exploratory semantic retrieval recall gains on GEMET, but remain **not deployed as Find's default**. [#58](https://github.com/grove/graph-verity/issues/58) still lacks actual independent human relevance review, as of this roadmap freeze.
- The local Find browser, a clearer separately versioned Find v2, and a separate blinded Research Review exist as supporting engineering/research tools; no one has yet validated reliable NL question understanding through them.

### Unresolved

- Phase 0's tested Qwen2.5-1.5B v1 and compact-v2 adversarial configurations both achieved **0/24 strict complete supported answers** and **0/6 correct model-origin abstentions**. That was a negative result for those specific unattended configurations; [the Phase 0 STOP/REVISE decision](phase-0-decision.md) is **not** retroactively overturned.
- [#48](../reports/issue-48-grounded-models/README.md) did execute real Qwen3.5-9B and Gemma 4 12B Q4_K_M attempts on the owner's Apple M1 Pro / 32 GiB with four CPU threads. Severe host contention, **>24 GiB swap used** and 300s generation deadlines stopped a complete fair comparison: Qwen produced **two scored drafts**, including semantically unfaithful plans; Gemma yielded **no scored draft**. “REVISION needed / inconclusive” is **not** a rejection of all stronger models, nor a model-promotion GO.
- A question-only, top-ten BM25 packet missed necessary reference IDs on **4/24** supported historical #48 contexts. That is a **retrieval coverage problem**, not evidence that a language model cannot understand the question.
- **Model-origin ambiguity handling, abstention, correct forward/reverse direction, bound named constants, false-confidence and reliable exact RDF answers remain undemonstrated.**

## 5. Phase 2 implementation sequence

| Order | Issue | Outcome | Main dependency |
| --- | --- | --- | --- |
| 1 | [#72 — Narrow draft contract and frozen one-hop evaluation](https://github.com/grove/graph-verity/issues/72) | \`nl-ask-draft-v1\`, Rust expansion to current Confirmed Ask, source-audited NO/EN benchmark, strict failure taxonomy | Existing Rust core |
| 2 | [#73 — Gold-free graph vocabulary packet](https://github.com/grove/graph-verity/issues/73) | BM25 question-only candidate packets; actual graph/role/direction coverage and missing-ID analysis | #72 contract; can start in parallel |
| 3 | [#74 — Controlled local inference](https://github.com/grove/graph-verity/issues/74) | Pinned, actual one-hop Qwen3.5/Gemma4 candidate tests on quiescent M1 Pro, CPU baseline and optional separately measured Metal, real outputs and resource profile | #72, #73 |
| 4 | [#75 — User-facing opt-in NL Ask](https://github.com/grove/graph-verity/issues/75) | Ask box → bounded model draft → Rust preview → **separate approval** → source-backed Oxigraph result. Saved-draft UI tests first; live inference when supported | #72–#74 |
| 5 | [#76 — Semantic and human risk evaluation](https://github.com/grove/graph-verity/issues/76) | Full question-to-plan/answer fidelity, model abstentions, wrong-but-executable behavior, local cost, approval safety and human false-confidence screen | All preceding work + actual people for human claims |

**Highest-priority starting point: #72.** Build/validate the narrow typed contract and pre-register the question set **before** running any new models. #73 may build the real question-only retrieval packet in parallel.

## 6. Feasibility and measurement policy

### Always distinguish five metrics

1. **Retrieval recall**: does the gold-free authorized candidate table include the required entity and predicate IDs in the right named graph? A retrieved ID is only a candidate.
2. **Model semantic faithfulness**: did the model propose the *right start entity, relation, direction, bound constants and projection* for what the user actually asked? A wrong but executable plan fails here.
3. **Exact RDF answer agreement**: does the *approved* formal plan return the correct complete bindings and actual source witnesses? Accidental current-snapshot agreement cannot substitute for faithful query interpretation.
4. **Correct model-origin abstention/clarification**: unsupported, ambiguous or open-world-negative requests must not be mislabeled as successful just because deterministic Rust blocked them, a model timed out or the user cancelled.
5. **Human comprehension and false confidence**: does a real person understand the model-proposed graph interpretation *before* approving it, and do they sometimes approve a plausible but wrong plan?

Keep original query, graph/scope, source provenance, candidate and raw model tokens, selected draft, preview, approval decision, exact bindings, rows/evidence truncation and error categories as separate fields. Do not publish private source content or participant-linked judgments.

### Freeze before scoring

Freeze dataset snapshots and licenses, operator policy/scope, source-qualified index revision, benchmark question and answer provenance, development/evaluation lineage, candidate top-k, model/revision/tokenizer/template/grammar, CPU/Metal variant, generation limits and numerical continuation/stop gates **before scored inference**. Tune only on disclosed development material; do not silently edit public evaluation cases after observing ranks or answers.

The **sealed external 60-case Ask holdout is excluded** from Phase 2 development and must not be opened or injected into model prompts. Existing public Phase 0/#48 cases are useful adversarial regressions but not new independent evaluation.

### Actual local runtime

Use the known **M1 Pro / 32 GiB** as the experimental target. A quiescent host and swap/load/memory-pressure record are prerequisites to interpreting latency. CPU four-thread Q4_K_M is a historical baseline *configuration*, not a promised adequate model. If a Metal variant is supported, pin and evaluate it independently with actual hardware/memory and tokenizer/model parity; avoid claiming backend support before verifying it.

Record **process-cold and warm latency**, model load, prompt/generation tokens, p50/p95/p99 with sample counts, whole process-tree RAM, swap, vector/index overhead, and failure/timeout denominators. Never infer model reliability from model-free CI or a saved fixture replay.

### Rollout stops

- Any **unapproved model-generated query execution**, unauthorized graph/source/IRI access, private canary leak, raw-SPARQL write/SERVICE path or stale approval reuse blocks integration.
- Model proposal failure, ambiguous names, invalid model output, unsupported templates or absent required graph vocabulary produce **no execution**, with honest UI explanation and an opportunity for deliberate user clarification.
- A model producing an executable but semantically wrong plan is a **failure even if the resulting query is harmless**. Human confirmation mitigates action risk; it does **not** fix that interpretation error.
- If a new model trial is incomplete or biased by host contention, the outcome is **revise/inconclusive**, not a manufactured accuracy ranking or a negative verdict on unrelated models.
- A research prototype completing all tests does **not** constitute product release GO. A user-facing opt-in rollout beyond the explicitly experimental prototype and any default/unattended Ask require separate explicit owner approval and genuine human false-confidence evaluation.

## 7. What the first user should see

The primary, opt-in experimental entry point should look roughly like:

> **Ask a question about this RDF graph**  
> *«Hva er hovedstaden i Norge?»*  
> [Interpret question]
>
> **Proposed interpretation — please check**
> - Start resource: Norway / Q20, original graph-qualified IRI
> - Relationship: capital / P36, **outgoing**
> - Return: distinct terminal RDF values
> - Graph: authorized Wikidata development snapshot
> - Limits: exact Rust-rendered row/evidence/time caps
>
> [Approve this exact interpretation and run] [Clarify / choose a different identity] [Cancel]
>
> **Only after approval:** Oslo / Q585 — [Inspect original source triple, named graph and license].

The **Rust-produced plan preview**, not a model explanation, controls what is actually executed. If the question cannot be represented as the approved one-hop template, show **unsupported or needs clarification** without an invented answer. Make **Find / Explore graph** available as an *advanced fallback*, not the first mandatory step. Keep Research Review separate.

Do not redesign or overwrite frozen #57/#58 interfaces to achieve this. Use separately versioned opt-in UI/adapter paths and preserve existing snapshot policy, private session/Origin/Host protections, one-time confirmation, source rendering and capped query limits.

## 8. R&D milestone completion vs product release

The **Phase 2 R&D milestone** can be reviewed when the work has produced an actual, opt-in question-to-plan/approval/Oxigraph run **or** a source-backed and reproducible blocker, a fully recorded frozen end-to-end evaluation, and a plain-language **go for further supervised study / revise / stop** recommendation.

To assert human usefulness, safe understanding or opt-in release readiness, obtain **actual consenting human task observations**, separately identifying independent, owner and rehearsal judgments. If no people participate, state **human evidence: 0 / unmeasured**; do not close a human validation gate by substituting synthetic sessions.

**Default shipping Find stays BM25 and free-form unattended Ask remains disabled while this research proceeds.** The next milestone is a more constrained, more measurable attempt at the *original* product vision—not an automatic reversal of Phase 0.
