# Graph Verity UX plan: Explore vs Research Review

**Status:** proposed experience/design specification, not an implemented feature or a user-validated design  
**Date:** 2026-10-18  
**Scope:** local-first RDF Find, graph evidence, deterministic Confirmed Ask, and the separate blinded retrieval study  
**Decision:** build **two distinct experiences**, not a single overloaded search-and-evaluation screen.

## The problem

The current review screen mixes an otherwise simple question—*“Which RDF resources match these words?”*—with expert research tasks: judging every result, browsing the complete authorized catalog, identifying missing relevant resources, checking RDF predicate direction, scoring confidence and saving a blinded comparison. A first-time user can reasonably find that overwhelming.

This feedback is a **qualitative owner observation**, not a completed participant study or a measured failure rate.

The project already has:

- A **BM25 Find and graph-evidence UI** with deliberate resource selection and optional deterministic Confirmed Ask ([v1](local-find-ui.md)).
- A separate **Find v2 presentation prototype** with clearer exact/partial matches, source witnesses and RDF direction ([#66 / PR #69](local-find-ui-v2.md)). It is not participant-validated.
- Verified **Wikidata, Norway GeoNames/Schema.org and GEMET** operator presets ([#67 / PR #70](find-pilot-presets.md)). They currently launch the unchanged v1 UI, not v2.
- A separate **blinded BM25 versus selective hybrid review** with 20 frozen Norwegian/English tasks and saved results ([#58](../studies/hybrid-review-v1/README.md)).
- An **offline handoff launcher** that runs the review from a checksummed pinned source tree ([#65 / PR #68](../studies/hybrid-review-handoff/README.md)).

**Today:** BM25 remains Find's default; EmbeddingGemma 2 selective hybrid is research-only; Confirmed Ask accepts only a deliberately constructed formal plan. Issue [#58](https://github.com/grove/graph-verity/issues/58) remains open, with **zero recorded human reviewers and judgments** in the published report. Neither good ranking metrics nor a successful Rust execution proves that the user understood a question or that an RDF statement is true outside its source graph.

## 1. Two products, two jobs

| | **Explore — Graph Verity Find** | **Evaluate — Research Review** |
| --- | --- | --- |
| Primary user | Researcher/analyst exploring an RDF dataset | Consenting independent relevance reviewer or study operator |
| User's question | “What resource or relationship am I looking for?” | “Which of these retrieved resources actually fit this query?” |
| Starting point | Search box and an authorized dataset | Short study introduction, consent and a frozen task |
| Primary action | Inspect, **select** an exact graph-qualified resource, follow its RDF edges | Judge candidate relevance, check missed resources, submit one blinded comparison |
| Search engine | **BM25 only**, until a separate promotion decision | Two frozen saved ranked lists: BM25 and experimental selective hybrid |
| Advanced evidence | Expandable RDF source triples, direction, graph/snapshot, license | Expandable candidate witnesses plus explicit full-catalog adjudication |
| Final outcome | A navigable resource and its **source evidence**, not a verified answer | Private relevance judgments and a research report, not a search result for end users |
| Must never happen | Automatic top-hit selection, inferred Ask plans, unauthorized scope changes | Unblinding before submission, fabricated reviewers, pretending a quick preference is exhaustive relevance |

These should have **separate entry points and terminology**. The reviewer is not an “advanced Find user,” and ordinary users should not encounter review metrics, forced A/B judgments or study forms while browsing an RDF graph.

### Entry-point labels

- **Explore the graph** — “Search resources and relationships in an authorized RDF dataset.”
- **Evaluate search results** — “Help assess two search methods in a blinded research study. This is not the everyday search interface.”

The second option is available **only in an explicitly started, local reviewer session**. Do not add a convenient public switch from Explore into a live study or expose the study's hidden labels, randomization seed, raw participant records or operator-only source anchors.

## 2. Explore: the everyday Find journey

**Goal:** a person with little RDF vocabulary can search, choose a resource, inspect its graph relationships, and understand what a match and a source statement do *not* establish.

### Screen E1 — Search

Recommended hierarchy (illustrative; not a claim that this exact UI exists):

> **Explore the graph**  
> Dataset: Wikidata development · Source/graph selected by the operator  
> **Search resources or relationships** [ Norway / Norge ]  
> Looking for: [Entity] [Predicate] [Class]  
> [Find resources]  
> *Search matches indexed words; it does not interpret a complete natural-language question or generate an answer.*

Keep authorized graph choice visible but unobtrusive when there is only one graph. Use plain words first; introduce “IRI,” “predicate,” “snapshot” and “named graph” through concise definitions or expandable details. Preserve the actual operator-set authorization and role choice. A query like **“capital of Norway”** is a lexical Find request, **not** a promise to answer “Oslo.”

### Screen E2 — Candidate list

Each result should prioritize:

1. **Observed label** (or explicit “No published label”) and a compact role marker: Entity, Predicate or Class.
2. **Match type**: exact graph-qualified IRI, exact indexed label/alias text, or **partial lexical suggestion**. A missing exact IRI must not be described as an identity match.
3. A short **observed** description/excerpt, only where authorized source text supports it; visible language and source link-to-evidence within the local UI.
4. **Inspect resource** as the primary action; IRI, graph, snapshot, license, raw lexical score, witnesses and truncation in “Details.”
5. A prominent, calm explanation when results are ambiguous, incomplete, clipped or absent.

Do not call the BM25 score a probability or confidence. A high-ranked suggestion may be irrelevant. If a query yields suggestions despite no relevant resource (the no-match failure seen in the AI-only #58 checks), those suggestions must **not** be presented as correct answers. We do not have a calibrated semantic-absence detector.

Example grounded in the retained Wikidata fixture:

> **Norway / Norge** — Entity  
> Exact observed text match · Original IRI: http://www.wikidata.org/entity/Q20  
> [Inspect resource] [Show original labels and source]

Avoid a generic “confidence 98%” badge and avoid autoselecting Q20.

### Screen E3 — Evidence and navigation

After deliberate selection, show the **stored RDF direction** with readable roles and a fold-out original statement:

> Norway (subject) **— capital / P36 (predicate) →** Oslo (object)  
> Graph: urn:graph-verity:wikidata:development  
> [Original RDF terms and source witness] [Incoming] [Outgoing] [Predicate usage]

For SKOS, explicitly distinguish **child — skos:broader → parent** from **parent — skos:narrower → child**. Never imply a reverse edge exists unless the source contains it. Keep source graph, importer provenance, literal datatype/language, license and independent row/evidence clipping visible.

A user must be able to say: “**This graph snapshot contains this statement**,” rather than “Graph Verity has proved that it is true.” Search returning nothing does not prove real-world absence.

### Optional: Confirmed Ask is a separate deliberate step

Only after the user explicitly selects a resource, provide **Build an exact path query**. The user chooses original predicate IRI, authorized graph, forward/reverse direction, optional second connected step, optional typed filter, and distinct values or count. Show the complete **authoritative Rust preview** before a **separate expiring, one-time approval**. Cancel, stale state, editing or missing approval never executes. **No free-text Ask interpretation and no model-generated auto-filled plan.**

The existing [v1 Confirmed Ask UX](local-find-ui.md#deliberate-confirmed-ask-walkthrough) is engineering-grounded but still requires user testing. A simpler Explore screen must not weaken the review boundary.

## 3. Evaluate: a guided research-review journey

**Goal:** retain all scientifically important #58 judgments while replacing the first screen's technical overload with a short, understandable sequence. An A/B preference alone is **not enough** for Recall@10 or MRR; reviewers must judge individual candidates and look for relevant resources missed by both lists.

### Screen R0 — Welcome, consent and explanation

> **Help compare two search methods**  
> You will review 20 short Norwegian/English searches. Each produces two lists, A and B. We hide which method made each list until you submit.  
> **Your job:** decide which RDF resources actually match the search, including any relevant resources missing from the displayed results.  
> You may skip a question or withdraw. This is an exploratory study, not a test of your ability.  
> [Start review] [What is an RDF resource?] [How are my responses stored?]

The operator must obtain **genuine informed consent** before any real session; a CLI flag is not a substitute. Describe privacy, withdrawal, retention and source scope in accessible prose. Owner, independent and rehearsal sessions remain different evidence categories. One physical person must not be counted under two independent IDs.

### Screen R1 — One question, two lists

> **Question 2 of 20**  
> “konstruksjon av bygg som tåler jordskjelv”  
> *Which concepts actually relate to designing buildings that withstand earthquakes?*  
>  
> **Results A** | **Results B**  
> Candidate title · original IRI · language  
> [Relevant] [Not relevant] [Unsure] [See evidence]

The explanatory question above is **illustrative proposed copy**. The frozen #58 task's actual original query must not be silently rewritten or replaced during collection. If helper wording affects participant decisions, that is a **new instrument** requiring a separately frozen study.

Render shared graph-qualified identities consistently; each distinct candidate is judged once across both lists. Keep ranking and A/B order as frozen/randomized. Do **not** show “BM25,” “hybrid,” similarity values, gold anchors or internal study metrics before submission. Evidence is a disclosure panel, not an initial wall of RDF quads.

### Screen R2 — “Did both lists miss anything?”

> **Check for other relevant resources**  
> Results A and B might both miss a matching concept. Search or browse the **authorized catalog**, inspect its original source evidence, and add any other relevant resources.  
> [Browse catalog] [Add relevant resource]  
> [I reviewed the authorized catalog for other relevant resources]

This is **required for scored recall**. Do not precheck it, reduce “catalog reviewed” to “I checked the top ten,” or infer exhaustive relevance from source anchors. “No relevant resource in the selected authorized role/graph” is different from no **displayed** result and from no fact in the real world.

If full catalog review is not feasible, provide an honest **Cannot assess / Exclude this task** path and retain that exclusion in the report. Never convert uncertain cases automatically to irrelevant or no-match.

### Screen R3 — Short research checklist

After resource-level judgments and catalog review, ask only the indispensable remaining questions, progressively grouped:

- **Identity and meaning:** Was the exact first result correct? Did either list suggest convincing but irrelevant resources? Was ambiguity handled clearly?
- **RDF meaning:** Were graph/scope and predicate **direction** suitable for the question? Were recovered paraphrases genuinely helpful?
- **Reviewer assessment:** Which list is preferable (A/B/tie/neither/uncertain)? Confidence in each list on a 1–5 scale; disclose clearly what “confidence” means.
- **Completion:** A no-match declaration only if **no relevant retrievable resource** exists within the authorized catalog; or an explicit exclusion if unable to assess.

Use simple examples/help on demand, not six unexplained dropdowns upfront. Translate visible instructions in Norwegian and English where practical; retain unmodified source-language RDF literals. Unknown/uncertain checks must remain unscored or defer a gate as defined by the study—not silently reclassified as passing.

### Screen R4 — Review and submit

> **Before you submit**  
> You judged every distinct displayed candidate, looked for missed relevant resources, recorded uncertainty, and checked the relationship direction where relevant.  
> Submitting saves your answers and only then reveals the search systems.  
> [Submit this assessment] [Return to the question]

The server must **validate, atomically save and consume the one-shot submission before unblinding**. No auto-fill, repeat/overwrite of an unblinded task, hidden background upload, tracking, remote model or Ask execution. The current #58 source/protocol's session/tab/security restrictions continue to apply.

### Screen R5 — Progress and close

After saving, show “Question saved — N of 20 reviewed” and move to the next task without requiring a long explanation of Recall@k. The operator, **not the participant**, runs the private aggregate report after separate reviewers finish. Do not display one reviewer's answers to another person before they submit, or leak identities through a shared browser profile.

The report must preserve complete or partial coverage, exclusions, disagreements, confidence/false-confidence and independent-vs-owner attribution. A good-looking dashboard or two saved files does not prove two independent, consenting humans reviewed all tasks.

## 4. Progressive disclosure without weakening evaluation

| Initial screen | Expand when needed | Must remain a scored requirement |
| --- | --- | --- |
| Human-readable title and short observed text | Full IRI, datatype, language, graph, license, RDF triples | Exact graph-qualified identity and evidence available |
| Relevant / Not relevant / Unsure | Source witness inspection and predicate direction | Every unique displayed candidate judged, or task excluded |
| Two easy-to-scan lists | Search/browse **all authorized** catalog candidates | Off-list relevance and legitimate no-match determination |
| “Which list helped?” | Full exact/scope/direction/ambiguity rubric | Full frozen rubric for a scored task |
| “Save” | Private consent/session and protocol details | Consent, blinding, atomic save-then-reveal, exclusions |

Do not confuse **simpler visual presentation** with **a lighter scientific protocol**. The former is welcome. The latter would change what #58 measures.

## 5. Constraints and versioning — non-negotiable

**The existing #58 protocol remains frozen.** The operator handoff pins source commit **ba9e57f8574ebf2c28797a98004dd6fbda61abfe** and protocol ID **6223e88dbca50cbc9e09b3eb8c0fa4034fe4f55ba8405e66318b37a633c84354**. Its source-file hashes include the original reviewer UI and shared local backend. Do not modify those inputs and then pretend the review is the same experiment.

- **Track A — actual #58 human evaluation:** use [the existing frozen offline handoff](../studies/hybrid-review-handoff/README.md) *as it is*, with actual consenting independent reviewers. This design document is **not** an instruction to change their assigned wording or form. Keep #58 open until real independent evidence exists.
- **Track B — redesigned researcher experience:** create a **separately named review UI v2 / instrument** and preregister its tasks, copy, interactions, randomization, measurements and comparison rules **before enrollment or model evaluation**. Preserve original data/scores as historical exposures; do not mix judgments from v1 and v2 as a single fixed instrument or call them fresh holdout data.
- **Track C — everyday Find:** build on the **already merged** [Find UI v2](local-find-ui-v2.md). Its tested lexical search and evidence components need clearer onboarding and formative user feedback, but existing #57/#58 hashed files must remain intact. Operator presets currently start **v1**; any v2 preset option must be explicit, verified and separately documented.
- Keep the local-only trust boundary: operator-approved RDF snapshot/policy/graph scope, exact Host/Origin and credential checks, expiring tab sessions, bounded top-k/rows/evidence, escaped RDF text and **no external telemetry**. Browser input may only narrow authorized scope.
- No changes to RDF source statements, source licenses, frozen metric reports or sealed Ask holdout. No automatic EmbeddingGemma rollout, raw SPARQL, graph writes, SERVICE or autonomous Ask.

## 6. Proposed implementation slices

### Slice A — documentation and prototypes

Produce text-first or static mockups for E1–E3 and R0–R5; test whether someone unfamiliar with the project can explain **what each screen asks of them** without a walk-through. Label this formative feedback separately from formal #58 relevance reviews. This document itself is the starting brief, **not evidence** that the design has been tested.

### Slice B — simplify everyday Explore

Use the existing Find v2 launcher/presentation and operator presets as foundations. Improve first-run guidance, concise evidence cards, optional source panels, plain-language query-role explanations and Norwegian/English terminology. Preserve BM25 ranking, graph authorization, exactness and the Rust Confirmed Ask approval boundary. Add automated keyboard, HTML-injection, clipping, scope and source-witness checks; then gather actual user observations.

### Slice C — design and separately freeze Research Review v2

Implement the R0–R5 flow in **new paths** rather than editing the pinned #58 UI or silently changing its task wording. Define what changed from v1, preserve blinded labels until submission, validate all judgments and full-catalog review, and collect real consented participant feedback under an explicitly new protocol. Demonstrate that the private reporter distinguishes research-v1 from v2 and cannot merge incompatible session records.

### Slice D — decide with people, not CI alone

Two genuinely independent human assessments are the **minimum** under the existing #58 protocol; they must agree on complete relevant resource sets for scored cases. Count owner/rehearsal assessments separately. A new formative usability protocol may use additional participants but cannot retroactively satisfy #58.

After human judgments exist, report task completion, misunderstandings, relevant/irrelevant resources, missing catalog resources, no-match false suggestions, predicate direction, confidence and disagreement. For a product-level opt-in hybrid trial, apply the already frozen #58 quality/resource rules and obtain a **separate owner authorization**. A reviewer UX redesign alone is never an adoption GO.

## 7. Definition of done for a future UX implementation

- [ ] A first-time Explore user can tell what is being searched, pick an original graph-qualified RDF resource and inspect a real source triple **without being asked research questions**.
- [ ] The Explore interface unambiguously distinguishes exact identity, partial lexical suggestions, ambiguous candidates, **no match in the authorized index**, clipped data, and unknown real-world truth.
- [ ] Confirmed Ask remains a distinct formal-plan preview and explicit separate approval, with no automatic interpretation or execution.
- [ ] A research reviewer can describe the A/B task in ordinary language and **every required judgment is still captured**: distinct candidate relevance, off-list catalog review, no-match, ambiguity, predicate direction, preference, per-list confidence, and exclusions.
- [ ] Source/provenance details remain inspectable without occupying the entire initial screen, including language/datatype, graph/snapshot, original direction and evidence clipping.
- [ ] Tests preserve authorization, private session/consent handling, atomic save-before-reveal, keyboard navigation and untrusted-text isolation. No model inference runs in ordinary CI.
- [ ] Frozen #57/#58 protocols, hashes, sessions and historical measurements remain intact. New UI experiments have distinct paths/protocol IDs and do not create fictitious human reviews.
- [ ] Usability and relevance claims cite **actual observed people and task denominators**; otherwise the report says “not yet evaluated.”

## Decision to carry forward

**Build two interfaces with distinct purposes.** Let the everyday Find journey show candidates and source evidence simply. Let Research Review collect rigorous blinded relevance evidence through a clearly guided, progressively disclosed workflow. Preserve the currently frozen #58 study untouched while any easier reviewer UI is separately designed, versioned and evaluated.

The next product decision is still **BM25 for Find; hybrid retrieval remains experimental pending real human relevance review and explicit owner promotion approval**.
