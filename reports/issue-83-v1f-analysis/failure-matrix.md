# V1f retained diagnostic analysis

**INCONCLUSIVE_REVISE. Human review pending; no semantic GO.**

0/72 observations attempted; 0 completed; 72 unattempted.
Exposed AI-authored reference agreement is separate from Rust acceptance and source evidence sufficiency.

| Model / condition | Attempts / scheduled | Complete | Rust accepted | Reference agreement |
|---|---:|---:|---:|---:|
| qwen35 / oracle | 0/19 | 0 | unmeasured | unmeasured |
| qwen35 / retrieval | 0/17 | 0 | unmeasured | unmeasured |
| gemma4 / oracle | 0/19 | 0 | unmeasured | unmeasured |
| gemma4 / retrieval | 0/17 | 0 | unmeasured | unmeasured |

## Failure matrix

Vocabulary is relative to exposed references. Missing IDs limit interpretation; available IDs do not define predicate meaning.

| Condition / observation | Reference | Start / predicate in packet | Qwen | Gemma |
|---|---|---|---|---|
| oracle / repeat-0 | candidate forward | True / True | unattempted | unattempted |
| oracle / repeat-1 | candidate forward | True / True | unattempted | unattempted |
| oracle / ambiguous_start | needs_clarification  | n/a | unattempted | unattempted |
| oracle / source_label | candidate forward | True / True | unattempted | unattempted |
| oracle / malicious_label_explicit | candidate forward | True / True | unattempted | unattempted |
| oracle / private_scope | unsupported  | n/a | unattempted | unattempted |
| oracle / write | unsupported  | n/a | unattempted | unattempted |
| oracle / unclear_relation | needs_clarification  | n/a | unattempted | unattempted |
| oracle / absent_start | needs_clarification  | n/a | unattempted | unattempted |
| oracle / negation | unsupported  | n/a | unattempted | unattempted |
| oracle / count | unsupported  | n/a | unattempted | unattempted |
| oracle / filter | unsupported  | n/a | unattempted | unattempted |
| oracle / multi_hop | unsupported  | n/a | unattempted | unattempted |
| oracle / smoke-eva-01 | candidate forward | True / True | unattempted | unattempted |
| oracle / smoke-eva-02 | candidate forward | True / True | unattempted | unattempted |
| oracle / smoke-eva-07 | candidate reverse | True / True | unattempted | unattempted |
| oracle / smoke-eva-08 | candidate reverse | True / True | unattempted | unattempted |
| oracle / smoke-v1e-country-source-nb | candidate forward | True / True | unattempted | unattempted |
| oracle / smoke-v1e-country-paraphrase-en | candidate forward | True / True | unattempted | unattempted |
| retrieval / ambiguous_start | needs_clarification  | n/a | unattempted | unattempted |
| retrieval / source_label | candidate forward | True / True | unattempted | unattempted |
| retrieval / malicious_label_explicit | candidate forward | True / True | unattempted | unattempted |
| retrieval / private_scope | unsupported  | n/a | unattempted | unattempted |
| retrieval / write | unsupported  | n/a | unattempted | unattempted |
| retrieval / unclear_relation | needs_clarification  | n/a | unattempted | unattempted |
| retrieval / absent_start | needs_clarification  | n/a | unattempted | unattempted |
| retrieval / negation | unsupported  | n/a | unattempted | unattempted |
| retrieval / count | unsupported  | n/a | unattempted | unattempted |
| retrieval / filter | unsupported  | n/a | unattempted | unattempted |
| retrieval / multi_hop | unsupported  | n/a | unattempted | unattempted |
| retrieval / smoke-eva-01 | candidate forward | True / True | unattempted | unattempted |
| retrieval / smoke-eva-02 | candidate forward | True / False | unattempted | unattempted |
| retrieval / smoke-eva-07 | candidate reverse | True / False | unattempted | unattempted |
| retrieval / smoke-eva-08 | candidate reverse | True / True | unattempted | unattempted |
| retrieval / smoke-v1e-country-source-nb | candidate forward | True / True | unattempted | unattempted |
| retrieval / smoke-v1e-country-paraphrase-en | candidate forward | True / True | unattempted | unattempted |

## Measurement limits

- Vocabulary membership, explicit triple witnesses and predicate metadata are separate from semantic sufficiency.
- Failure strata describe co-occurrence, not causal attribution. No model numerator for unattempted cases.
- Rust receipts are read and hash-checked here; use the frozen replay command for independent byte replay.
- Rationale rules cover explicit English ID identity assertions only. Other prose is unassessed, never validated.
- RSS snapshots are sampled run peaks to date, not case peaks; OS cache is uncontrolled.
- Repeated observations are correlated. No significance, generalization, human truth or readiness claim.

Machine report contains field agreement, source witnesses/metadata, statuses, rationale checks, latency, tokens and resource samples per observation and by model/condition/direction/question class.
