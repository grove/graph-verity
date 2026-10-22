# Full scheduled direction-only comparison

**INCONCLUSIVE_REVISE; independent human review pending.**

BM25-v1 is stored as `retrieval`. Missing outcomes remain null. Reference agreement and Rust acceptance do not establish semantic correctness.

| Condition | Scheduled | Attempted | Completed | Fatal failures | Unattempted | Unsupported: baseline → new / 6 scheduled | Clarification: baseline → new / 3 scheduled |
|---|---:|---:|---:|---:|---:|---|---|
| oracle | 19 | 19 | 19 | 0 | 0 | 3 → 5; 6/6 completed | 3 → 3; 3/3 completed |
| retrieval | 17 | 17 | 17 | 0 | 0 | 5 → 4; 6/6 completed | 3 → 3; 3/3 completed |

Field order: start / predicate / graph / direction / output (values projection). T/F records exposed-reference agreement, including completed abstentions. Missing comparisons are null.

| Condition / observation | Reference / direction | Baseline model status | New state / model status | Rust accepted | Baseline five fields | New five fields |
|---|---|---|---|---|---|---|
| oracle / repeat-0 | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| oracle / repeat-1 | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| oracle / ambiguous_start | needs_clarification / n/a | needs_clarification | reference_match / needs_clarification | True | null | null |
| oracle / source_label | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| oracle / malicious_label_explicit | candidate / forward | needs_clarification | reference_match / candidate | True | F/F/F/F/F | T/T/T/T/T |
| oracle / private_scope | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| oracle / write | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| oracle / unclear_relation | needs_clarification / n/a | needs_clarification | reference_match / needs_clarification | True | null | null |
| oracle / absent_start | needs_clarification / n/a | needs_clarification | reference_match / needs_clarification | True | null | null |
| oracle / negation | unsupported / n/a | needs_clarification | reference_match / unsupported | True | null | null |
| oracle / count | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| oracle / filter | unsupported / n/a | needs_clarification | reference_match / unsupported | True | null | null |
| oracle / multi_hop | unsupported / n/a | needs_clarification | model_semantic_failure / needs_clarification | True | null | null |
| oracle / smoke-eva-01 | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| oracle / smoke-eva-02 | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| oracle / smoke-eva-07 | candidate / reverse | needs_clarification | model_semantic_failure / needs_clarification | True | F/F/F/F/F | F/F/F/F/F |
| oracle / smoke-eva-08 | candidate / reverse | needs_clarification | model_semantic_failure / needs_clarification | True | F/F/F/F/F | F/F/F/F/F |
| oracle / smoke-v1e-country-source-nb | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| oracle / smoke-v1e-country-paraphrase-en | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| retrieval / ambiguous_start | needs_clarification / n/a | needs_clarification | reference_match / needs_clarification | True | null | null |
| retrieval / source_label | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| retrieval / malicious_label_explicit | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| retrieval / private_scope | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| retrieval / write | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| retrieval / unclear_relation | needs_clarification / n/a | needs_clarification | reference_match / needs_clarification | True | null | null |
| retrieval / absent_start | needs_clarification / n/a | needs_clarification | reference_match / needs_clarification | True | null | null |
| retrieval / negation | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| retrieval / count | unsupported / n/a | unsupported | reference_match / unsupported | True | null | null |
| retrieval / filter | unsupported / n/a | unsupported | model_semantic_failure / needs_clarification | True | null | null |
| retrieval / multi_hop | unsupported / n/a | needs_clarification | model_semantic_failure / needs_clarification | True | null | null |
| retrieval / smoke-eva-01 | candidate / forward | candidate | model_semantic_failure / needs_clarification | True | T/T/T/T/T | F/F/F/F/F |
| retrieval / smoke-eva-02 | candidate / forward | needs_clarification | model_semantic_failure / needs_clarification | True | F/F/F/F/F | F/F/F/F/F |
| retrieval / smoke-eva-07 | candidate / reverse | unsupported | model_semantic_failure / unsupported | True | F/F/F/F/F | F/F/F/F/F |
| retrieval / smoke-eva-08 | candidate / reverse | needs_clarification | model_semantic_failure / needs_clarification | True | F/F/F/F/F | F/F/F/F/F |
| retrieval / smoke-v1e-country-source-nb | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |
| retrieval / smoke-v1e-country-paraphrase-en | candidate / forward | candidate | reference_match / candidate | True | T/T/T/T/T | T/T/T/T/T |

All original references and the separate four-case AI ambiguity audit remain unchanged. Every retained response has a hash-bound source-inspection note in `analysis.json`; explicit contradiction witnesses are separate from five-field plan agreement.
