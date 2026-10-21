# Full scheduled comparison

All new outcomes are null: admission failed before any completion request. BM25-v1 is stored as `retrieval`. Independent human review is pending.

Fields are start / predicate / graph / direction / output (values projection). T/F denotes baseline exposed-reference field agreement, including abstentions. It does not establish semantic correctness.

| Condition / observation | Reference | Direction | Baseline status | Baseline five fields | New status | New five fields |
|---|---|---|---|---|---|---|
| oracle / repeat-0 | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / repeat-1 | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / ambiguous_start | needs_clarification | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / source_label | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / malicious_label_explicit | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / private_scope | unsupported | n/a | unsupported | n/a | null | null/null/null/null/null |
| oracle / write | unsupported | n/a | unsupported | n/a | null | null/null/null/null/null |
| oracle / unclear_relation | needs_clarification | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / absent_start | needs_clarification | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / negation | unsupported | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / count | unsupported | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / filter | unsupported | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / multi_hop | unsupported | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| oracle / smoke-eva-01 | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / smoke-eva-02 | candidate | forward | candidate | T/T/T/T/T | null | null/null/null/null/null |
| oracle / smoke-eva-07 | candidate | reverse | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / smoke-eva-08 | candidate | reverse | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| oracle / smoke-v1e-country-source-nb | candidate | forward | candidate | T/T/T/T/T | null | null/null/null/null/null |
| oracle / smoke-v1e-country-paraphrase-en | candidate | forward | candidate | T/T/T/T/T | null | null/null/null/null/null |
| retrieval / ambiguous_start | needs_clarification | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| retrieval / source_label | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| retrieval / malicious_label_explicit | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| retrieval / private_scope | unsupported | n/a | unsupported | n/a | null | null/null/null/null/null |
| retrieval / write | unsupported | n/a | unsupported | n/a | null | null/null/null/null/null |
| retrieval / unclear_relation | needs_clarification | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| retrieval / absent_start | needs_clarification | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| retrieval / negation | unsupported | n/a | unsupported | n/a | null | null/null/null/null/null |
| retrieval / count | unsupported | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| retrieval / filter | unsupported | n/a | unsupported | n/a | null | null/null/null/null/null |
| retrieval / multi_hop | unsupported | n/a | needs_clarification | n/a | null | null/null/null/null/null |
| retrieval / smoke-eva-01 | candidate | forward | candidate | T/T/T/T/T | null | null/null/null/null/null |
| retrieval / smoke-eva-02 | candidate | forward | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| retrieval / smoke-eva-07 | candidate | reverse | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| retrieval / smoke-eva-08 | candidate | reverse | needs_clarification | F/F/F/F/F | null | null/null/null/null/null |
| retrieval / smoke-v1e-country-source-nb | candidate | forward | candidate | T/T/T/T/T | null | null/null/null/null/null |
| retrieval / smoke-v1e-country-paraphrase-en | candidate | forward | candidate | T/T/T/T/T | null | null/null/null/null/null |
