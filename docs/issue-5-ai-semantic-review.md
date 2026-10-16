# Issue #5 — independent AI semantic audit and corrections (not human approval)

**AI reviewer:** ChatGPT / OpenAI GPT-6, 16 October 2026. This is **not** a human domain expert, a human annotation, or independent human adjudication.  
**Source:** versioned `benchmarks/wikidata.json`, frozen `data/wikidata/snapshot.nq` and the source/license manifest.  
**Individual case records:** [`benchmarks/ai-semantic-audit.json`](../benchmarks/ai-semantic-audit.json) (130 case-and-snapshot SHA-256 digests, original/current questions, separately stated meanings, expected plan signatures and caveats).  
**Human review ledger:** [`benchmarks/reviews.json`](../benchmarks/reviews.json) remains **empty**. No human approval has been asserted.

## Scope of work

I examined each of the 130 question entries against its expressed Norwegian semantics, named graph, predicates, directions, joins, filters, grouping/aggregation, expected status and actual retained RDF facts. The 38 executable development cases were individually checked against explicitly authored intent signatures, plus eight plausible clarification/unsupported cases. The other 76 entries are not fresh questions: each is a fixed prefix attached to one of those 38 development questions with exactly the same plan, reference SPARQL and result bindings. The eight Stockholm/Sweden entries use the same Wikidata ontology.

This is not proof of semantic correctness or an empirical question-answering accuracy result. The existing independent-RDFLib-vs-Oxigraph oracle checks mechanical result agreement; this supplementary AI audit checks wording versus intended query structure. No Graph Verity model inference ran and no human expert reviewed or signed off the corpus.

## Findings and corrections made

The audit found **17 material question/plan interpretation concerns**, involving three distinct problem categories. The candidate corpus was revised with **only wording and intended-meaning changes**: all raw RDF, gold IR, reference SPARQL and frozen expected bindings were preserved. The benchmark checksum and every affected case hash were repinned. All changed entries retain machine authorship and human-review-pending status.

| Finding | Affected entries | AI adjudication applied |
|---|---|---|
| Wikidata `Q25416` denotes the **municipality** of Stavanger, while the original questions named undifferentiated “Stavanger” | Development `wd-dev-016`–`020` and templated `wd-review-031`–`040` (15 records) | Questions now explicitly say “Stavanger kommune”. The Q25416 plan and its results remain unchanged. A human may instead choose to create a *separate city-entity* test in a later dataset revision. |
| “Hvilke elementer finnes **bare** i den valgte overføringsgrafen?” could imply exclusive membership, which the formal plan did not prove | `wd-transfer_candidate-006` | Reworded to request Wikidata items **recorded in the selected transfer graph**. The scope-only query is preserved; no negative/exclusion claim remains. |
| A question requesting “**land** og hovedsteder” was answered by a bare `P36` relation without checking that the subject is a country | `wd-transfer_candidate-008` | Reworded to ask for subjects with an **explicit capital relationship** and their pointed-to capitals, which matches the existing formal plan. No unsupported subject-type guarantee remains. |

The frozen data directly contains `Q25416 wdt:P31 Q755707`; [Wikidata Q25416](https://www.wikidata.org/wiki/Q25416) is the Stavanger municipality and [Q755707](https://www.wikidata.org/wiki/Q755707) denotes a Norwegian municipality. A distinct [Stavanger urban-settlement item Q26772333](https://www.wikidata.org/wiki/Q26772333) exists but is **not** substituted into this small data capture. The audited graph also contains `Q20 wdt:P17 Q20` (Norway's self-referential country statement); some population/grouping questions therefore include the country itself. This is declared data semantics, not proof of real-world identity or correctness.

The 122 previously *circular* intended-meaning strings (“Execute exactly the supplied directed plan ...”) were replaced by explicit query-specific intent descriptions prepared during the AI audit. They state direction, property, operands and/or grouping, with the limitation that the graph is open-world and results are statements of the selected snapshot. All interpretations still need separate independent human adjudication before gold promotion.

## Current AI-only dispositions

| Count | Assessment | Meaning |
|---:|---|---|
| 122 | `provisionally_consistent_ai_only` | After the explicit wording corrections, the recorded restricted graph plan matches the AI-assessed intended operation. **Not human expert-approved.** |
| 8 | `expected_abstention_is_plausible_ai_only` | Ambiguous or unsupported questions have plausible no-plan statuses. **No model abstention was measured.** |

The audit did **not** find any structural mismatch with the manually authored intent signatures after corrections, but this is not an unbiased parser accuracy estimate. All 76 development-template paraphrases are exposed and correlated; the eight geographic candidates are the same ontology; no independent locked transfer/holdout exists.

## Remaining data-quality warnings

- The source includes multiple `P571` inception dates for Norway. These questions deliberately check whether a recorded date *exists* in a range; do not infer a uniquely true historical founding date, provenance-complete temporal claim, or current-world state.
- The Oslo labels captured in the development subset include an English-only label for the particular item; this is not a demonstrated Norwegian-language parser success.
- Inverse relations returning no rows (e.g., a capital relation with Bergen) mean only that the pinned selected graph does not contain the requested statement, not that the statement is false in the world.
- The capture of 600 quads is intentionally small, not adequate procurement-domain or pilot-scale coverage. The retained earlier Oslo revision produced unchanged selected graph bytes, so it is not meaningful temporal transfer.
- A true locked holdout must contain **new, independently authored and adjudicated** question families, paraphrases, gold and reference queries with group separation and restricted access to answer keys. Publicly exposed 76 template variants or eight same-ontology geographic candidates must not simply be renamed into holdout or cross-ontology test splits.
- Review quality must not be inferred from agreement between generated IR and generated gold. The benchmark's human review ledger remains empty. A private locked test process with real independent reviewers is still missing.

## Verification

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python -m unittest discover -s tools -p 'test_ai_semantic_audit.py' -v
.venv/bin/python tools/benchmark.py verify
.venv/bin/python tools/benchmark.py review
.venv/bin/python tools/benchmark.py review --require-reviewed initial
```

The last command **must presently fail**, because the zero-approval human-review gate is deliberately unsatisfied. The tests ensure each AI assessment refers to the exact pinned question, snapshot, intended plan signature and source facts; case edits without renewed assessment fail.

## Why issue #5 cannot yet be closed

An AI model cannot truthfully be a human expert, supply human identity or independently sign 100–200 gold cases. This audit does not fulfill the issue's specifically **human-reviewed** acceptance condition. There is also no genuinely independent locked evaluation partition or qualifying different-ontology/coherent-temporal transfer set, and all present candidates are exposed. The `initial_ready` and `final_ready` human review gates must stay false.

To close #5 legitimately: recruit an independent domain/RDF reviewer to validate/adjudicate the corrected case meanings and answer sets, record their real approvals in the append-only ledger, produce independent inaccessible-to-development holdout plus valid transfer material, and freeze the approved split/hash manifest before final evaluation. Do not bypass these steps by relabeling an AI review as human or relaxing the existing acceptance criteria after the fact.
