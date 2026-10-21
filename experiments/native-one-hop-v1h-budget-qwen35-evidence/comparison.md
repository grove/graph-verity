# Qwen v1h versus historical r3

**INCONCLUSIVE_REVISE. Independent human review pending.**

| Revision / condition | Scheduled | Attempted | Completed | Unattempted | Exposed-reference agreement |
|---|---:|---:|---:|---:|---:|
| r3 / oracle | 19 | 19 | 19 | 0 | 8/19 |
| r3 / retrieval | 17 | 14 | 14 | 3 | 6/14 |
| v1h / oracle | 19 | 19 | 19 | 0 | 8/19 |
| v1h / retrieval | 17 | 17 | 17 | 0 | 10/17 |

| Condition / observation | r3 status | v1h status | r3 agreement | v1h agreement |
|---|---|---|---|---|
| oracle / repeat-0 | needs_clarification | needs_clarification | False | False |
| oracle / repeat-1 | needs_clarification | needs_clarification | False | False |
| oracle / ambiguous_start | needs_clarification | needs_clarification | True | True |
| oracle / source_label | needs_clarification | needs_clarification | False | False |
| oracle / malicious_label_explicit | needs_clarification | needs_clarification | False | False |
| oracle / private_scope | unsupported | unsupported | True | True |
| oracle / write | unsupported | unsupported | True | True |
| oracle / unclear_relation | needs_clarification | needs_clarification | True | True |
| oracle / absent_start | needs_clarification | needs_clarification | True | True |
| oracle / negation | needs_clarification | needs_clarification | False | False |
| oracle / count | needs_clarification | needs_clarification | False | False |
| oracle / filter | needs_clarification | needs_clarification | False | False |
| oracle / multi_hop | needs_clarification | needs_clarification | False | False |
| oracle / smoke-eva-01 | needs_clarification | needs_clarification | False | False |
| oracle / smoke-eva-02 | candidate | candidate | True | True |
| oracle / smoke-eva-07 | needs_clarification | needs_clarification | False | False |
| oracle / smoke-eva-08 | needs_clarification | needs_clarification | False | False |
| oracle / smoke-v1e-country-source-nb | candidate | candidate | True | True |
| oracle / smoke-v1e-country-paraphrase-en | candidate | candidate | True | True |
| retrieval / ambiguous_start | needs_clarification | needs_clarification | True | True |
| retrieval / source_label | needs_clarification | needs_clarification | False | False |
| retrieval / malicious_label_explicit | needs_clarification | needs_clarification | False | False |
| retrieval / private_scope | unsupported | unsupported | True | True |
| retrieval / write | unsupported | unsupported | True | True |
| retrieval / unclear_relation | needs_clarification | needs_clarification | True | True |
| retrieval / absent_start | needs_clarification | needs_clarification | True | True |
| retrieval / negation | unsupported | unsupported | True | True |
| retrieval / count | needs_clarification | needs_clarification | False | False |
| retrieval / filter | needs_clarification | unsupported | False | True |
| retrieval / multi_hop | needs_clarification | needs_clarification | False | False |
| retrieval / smoke-eva-01 | needs_clarification | candidate | False | True |
| retrieval / smoke-eva-02 | needs_clarification | needs_clarification | False | False |
| retrieval / smoke-eva-07 | needs_clarification | needs_clarification | False | False |
| retrieval / smoke-eva-08 | None | needs_clarification | None | False |
| retrieval / smoke-v1e-country-source-nb | None | candidate | None | True |
| retrieval / smoke-v1e-country-paraphrase-en | None | candidate | None | True |

## Limitations

- Oracle messages are unchanged; BM25-v1 packet presentation changes while information and membership are preserved.
- Token reduction and representation effects are confounded; r3 is incomplete, exposed historical evidence.
- Exposed-reference agreement, grammar validity and Rust acceptance are not independent semantic correctness.
- Wrong-but-executable means disagreement with exposed references, not independently established semantic error.
- No draft is executed; source witnesses enumerate retained triples only. Missing vocabulary is not restored.
- Rationale identity rules recognize narrow English assertions; unrestricted rationale correctness is unassessed.
- The unchanged grammar bounds rationales to 512 characters; some retained explanations end mid-sentence.
- Repeated observations are correlated; no randomized baseline, causal attribution or readiness claim.
- RSS is a sampled concurrent process-tree peak; sampling can miss peaks and double-count shared pages.
