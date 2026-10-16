# Issue #5 — independent AI semantic audit (not human gold approval)

**Date:** 16 October 2026  
**Reviewer:** ChatGPT / OpenAI GPT-6 (**AI system, not a human, domain expert, or independent human annotator**)  
**Inputs:** `benchmarks/wikidata.json`, `data/wikidata/snapshot.nq`, `data/wikidata/manifest.json` and the already frozen reference queries and bindings.  
**Machine-readable case-bound record:** [`benchmarks/ai-semantic-audit.json`](../benchmarks/ai-semantic-audit.json).  
**Review ledger:** [`benchmarks/reviews.json`](../benchmarks/reviews.json) is deliberately unchanged and contains **zero human approvals**.

## What was actually examined

Every one of the 130 case IDs is represented by its exact review-tool-compatible SHA-256 case-and-snapshot digest, original Norwegian question, independently formulated statement of the intended graph operation, explicit manually specified plan signature, and a risk/decision field. In particular:

- 38 executable **development** cases: separately checked question-family meaning against direction, actual predicate identifiers, typed comparison operands, numeric strictness, projections, `COUNT(DISTINCT)`, grouping/HAVING and named-graph scope. Eight additional development cases request clarification/unsupported status instead of a gold query.
- 76 **review candidates**: verified as *two simple introductory prefixes of each of the 38 development questions with exactly the same gold IR, reference SPARQL and bindings*. These are not independent gold examples.
- Eight **geographic-transfer candidates**: checked against their same-ontology Stockholm/Sweden graph, with material semantic caveats below. The transfer graph is not a different ontology or independently authored locked holdout.

The source snapshot contains 600 quads of selected direct statements. The existing Rust/Oxigraph oracle and separately evaluated RDFLib reference queries have mechanically matched the 38 executable development results; this AI audit adds a question-to-plan inspection. A syntactically valid IR or identical result set is **not** human confirmation of user intent or factual truth.

## Findings and case dispositions

| Count | Disposition | What it means |
|---:|---|---|
| 105 | `provisionally_consistent_ai_only` | The restricted operation appears to match the specific Norwegian wording; all remain subject to human adjudication and gold review. |
| 17 | `needs_question_or_plan_adjudication` | Material ambiguity or an unstated condition needs explicit correction or expert decision. |
| 8 | `expected_abstention_is_plausible_ai_only` | Proposed clarification/unsupported status fits the question; **no model abstention has been tested**. |

There are **zero detected structural mismatches** between the explicitly authored intent signatures and the recorded IR on these 130 cases. This is a scoped AI audit, not an accuracy estimate: the 76 derived templates are correlated and the cases were designed against the same restricted graph.

### 1. Stavanger's referent is a municipality — 15 case records

The five original development cases `wd-dev-016`–`wd-dev-020` and their ten templated copies `wd-review-031`–`wd-review-040` use `wd:Q25416` while asking simply about *Stavanger*. In the pinned RDF, `Q25416 wdt:P31 Q755707`; [Q25416](https://www.wikidata.org/wiki/Q25416) describes the **Stavanger municipality**, and [Q755707](https://www.wikidata.org/wiki/Q755707) denotes a Norwegian municipality. The Nynorsk label explicitly reads *Stavanger kommune*. The entity also has a recorded `P36` capital relationship, rather than simply representing the city itself.

**Required adjudication:** if the intent is to query this municipality, specify “Stavanger kommune (Wikidata Q25416)” in question and interpretation, and then regenerate and rereview all changed hashes. If the intent is Stavanger city, select the correct distinct entity and freeze an appropriate new RDF snapshot/gold. Do not silently treat municipality and urban settlement as identical.

### 2. `wd-transfer_candidate-006` implies exclusivity without proving it

“Hvilke elementer finnes **bare** i den valgte overføringsgrafen?” can mean *only exist in* the transfer graph, while the gold plan merely enumerates `rdf:type wikibase:Item` **within** that graph. It performs no negative comparison with any other named graph.

**Required correction:** reword to “Hvilke Wikidata-elementer er oppført i den valgte overføringsgrafen?” if scope-only membership is intended. Do not add unrestricted `NOT EXISTS` to the currently restricted IR, or infer absence from an open-world graph.

### 3. `wd-transfer_candidate-008` has no country-type constraint

“Hvilke **land** og hovedsteder er uttrykkelig oppført i overføringsgrafen?” is compiled as `?country wdt:P36 ?capital`. This yields the expected Sweden–Stockholm pair for the tiny capture but does **not** require `?country` to actually be a country. The result alone does not establish semantic equivalence of the natural-language type restriction.

**Required correction:** independently validate and add a supported country-type restriction (e.g. `P31` to an observed country class where available), or rephrase the question to “Hvilke ressurser har en eksplisitt hovedstadsrelasjon, og hva peker den til?” Record new gold, source evidence, and a new case hash.

### 4. Cross-cutting interpretation and graph-quality limits

- All 122 executable candidates currently use essentially the same generic interpretation (“Execute exactly the supplied directed plan ...”). This is **circular** as a gold *intended meaning* annotation: it refers back to the plan instead of independently describing what the question means. The AI audit supplies explicit per-case statements, but a human reviewer must confirm or correct those statements before promoting gold.
- The selected graph includes `Q20 wdt:P17 Q20` (Norway points to itself as country). Consequently some population and country-grouping results include the country itself. This is a snapshot statement, not a model bug; a reviewer must decide whether the question wording intends that inclusion.
- `Q20` has **multiple** selected `P571` inception values, including historical dates. Questions carefully using “oppgitt etableringsdato” may be evaluated existentially over these records; do not turn them into a unique historical founding date or current real-world claim.
- The Oslo label example returns only the selected English label. Norwegian queries over English labels are useful, but this tiny lexical capture does not itself establish multilingual parser performance.
- Empty inverse-capital results (for example Bergen and Trondheim) mean no matching statements in the named graph snapshot, **not** that some global-world negative fact has been proven.
- Eight development questions with no gold plan are plausible ambiguity/unsupported examples only. Until a real model runs, safe abstention, calibration and false-abstention rates are all unknown.

### 5. No independently locked test or qualifying transfer set exists yet

The 76 templated candidates and the eight Stockholm/Sweden candidates reuse exposed question structures and the **same Wikidata ontology**. The previous Oslo entity revision retained by the repository produced identical selected graph bytes, not a different coherent dataset snapshot. Thus no existing candidate group should be relabeled as an independent `locked_holdout` or `transfer_test`. The `exposed_groups` guard in the split manifest is correct and must remain in place.

For a decision-quality test, commission or author *genuinely new* questions and interpretations, prevent prompt/model development access to their answers, version the split/graph/source and ensure no lineage/template sibling crosses splits. Use a genuinely distinct ontology or coherently changed temporal snapshot for transfer. A publicly checked-in gold benchmark should not be described as secret from agents able to read that public repository.

## Reproduce

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python -m unittest discover -s tools -p 'test_ai_semantic_audit.py' -v
.venv/bin/python tools/benchmark.py verify
.venv/bin/python tools/benchmark.py review
.venv/bin/python tools/benchmark.py review --require-reviewed initial
```

The final command **must currently fail**: all 130 review records are pending human approval. The read-only unit tests ensure the AI audit remains bound to exact cases, original questions, expected plan signatures and source facts. They must not upgrade the source of reviewer identity or modify the human ledger.

## What prevents closing issue #5

This artifact is an **independent AI review**, not the required human expert review. The 130 questions were machine-authored, no human has signed or adjudicated the 17 flagged cases, and no independent locked holdout/second-ontology (or coherent temporal) transfer set has been created or protected. The existing review infrastructure's `initial_ready` and `final_ready` checks must remain false.

The project owner may use this audit to speed up human expert review; they must not record it as a human approval, fabricate reviewer identity, or close #5 by weakening its acceptance criteria. The next legitimate step is source-aware independent human adjudication followed by new isolated test material and the approved benchmark freeze.
