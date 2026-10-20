# V1f r3 retained diagnostic analysis

**INCONCLUSIVE_REVISE. Human review pending; no semantic GO.**

33/72 observations attempted; 33 completed; 39 unattempted.
Exposed AI-authored reference agreement is separate from Rust acceptance and source evidence sufficiency.

| Model / condition | Attempts / scheduled | Complete | Rust accepted | Reference agreement |
|---|---:|---:|---:|---:|
| qwen35 / oracle | 19/19 | 19 | 19/19 | 8/19 |
| qwen35 / retrieval | 14/17 | 14 | 14/14 | 6/14 |
| gemma4 / oracle | 0/19 | 0 | unmeasured | unmeasured |
| gemma4 / retrieval | 0/17 | 0 | unmeasured | unmeasured |

## Failure matrix

Vocabulary is relative to exposed references. Missing IDs limit interpretation; available IDs do not define predicate meaning.

| Condition / observation | Reference | Start / predicate in packet | Qwen | Gemma |
|---|---|---|---|---|
| oracle / repeat-0 | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / repeat-1 | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / ambiguous_start | needs_clarification  | n/a | reference_match | unattempted |
| oracle / source_label | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / malicious_label_explicit | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / private_scope | unsupported  | n/a | reference_match | unattempted |
| oracle / write | unsupported  | n/a | reference_match | unattempted |
| oracle / unclear_relation | needs_clarification  | n/a | reference_match | unattempted |
| oracle / absent_start | needs_clarification  | n/a | reference_match | unattempted |
| oracle / negation | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| oracle / count | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| oracle / filter | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| oracle / multi_hop | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| oracle / smoke-eva-01 | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / smoke-eva-02 | candidate forward | True / True | reference_match | unattempted |
| oracle / smoke-eva-07 | candidate reverse | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / smoke-eva-08 | candidate reverse | True / True | reference_failure_with_vocabulary_available | unattempted |
| oracle / smoke-v1e-country-source-nb | candidate forward | True / True | reference_match | unattempted |
| oracle / smoke-v1e-country-paraphrase-en | candidate forward | True / True | reference_match | unattempted |
| retrieval / ambiguous_start | needs_clarification  | n/a | reference_match | unattempted |
| retrieval / source_label | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| retrieval / malicious_label_explicit | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| retrieval / private_scope | unsupported  | n/a | reference_match | unattempted |
| retrieval / write | unsupported  | n/a | reference_match | unattempted |
| retrieval / unclear_relation | needs_clarification  | n/a | reference_match | unattempted |
| retrieval / absent_start | needs_clarification  | n/a | reference_match | unattempted |
| retrieval / negation | unsupported  | n/a | reference_match | unattempted |
| retrieval / count | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| retrieval / filter | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| retrieval / multi_hop | unsupported  | n/a | abstention_or_structural_failure | unattempted |
| retrieval / smoke-eva-01 | candidate forward | True / True | reference_failure_with_vocabulary_available | unattempted |
| retrieval / smoke-eva-02 | candidate forward | True / False | reference_failure_with_required_vocabulary_missing | unattempted |
| retrieval / smoke-eva-07 | candidate reverse | True / False | reference_failure_with_required_vocabulary_missing | unattempted |
| retrieval / smoke-eva-08 | candidate reverse | True / True | unattempted | unattempted |
| retrieval / smoke-v1e-country-source-nb | candidate forward | True / True | unattempted | unattempted |
| retrieval / smoke-v1e-country-paraphrase-en | candidate forward | True / True | unattempted | unattempted |

## Measurement limits

- Original inference authorization provenance is unresolved; present approval does not retroactively establish it.
- All reference agreement is against exposed AI-authored plans; independent semantic review is pending.
- Missing observations have null outcomes and never enter measured denominators. Gemma was not run by this review.
- Rust acceptance is distinct from model-origin clarification. Replay uses original bytes and does not execute RDF queries.
- Predicate IDs, adjacency and IRI local names do not independently establish predicate meaning.
- Rationale checks cover explicit English ID assertions only; other prose remains unassessed.
- RSS is a sampled concurrent process-tree run peak; sampling may miss peaks or double-count shared pages.
- No causal, model-ranking, exact-answer-accuracy or product-readiness claim.

Machine report contains field agreement, source witnesses/metadata, statuses, rationale checks, latency, tokens and resource samples per observation and by model/condition/direction/question class.
