# Retained Qwen / Gemma v1h comparison

**INCONCLUSIVE_REVISE. Independent human review deferred.**

Qwen retains the original 1024 MiB swap gate; Gemma uses the separately registered 2048 MiB variant.
`retrieval` denotes the unchanged frozen whole-question BM25-v1 condition.
All reference agreement is against exposed AI-authored fixtures. No model ranking or exact-answer accuracy is inferred.

| Model / condition | Attempted / scheduled | Completed | Unattempted | Reference agreement, completed | Unsupported classification, completed | Clarification on reference cases, completed |
|---|---:|---:|---:|---:|---:|---:|
| qwen35 / oracle | 19/19 | 19 | 0 | 8/19 | 2/6 | 3/3 |
| qwen35 / retrieval | 17/17 | 17 | 0 | 10/17 | 4/6 | 3/3 |
| gemma4 / oracle | 19/19 | 19 | 0 | 14/19 | 4/6 | 2/3 |
| gemma4 / retrieval | 15/17 | 14 | 2 | 11/14 | 6/6 | 2/3 |

Paired-completed subsets below compare exactly the same completed observation identities. Full failures and missing observations remain in the schedules above.

| Condition | Completed pairs | Qwen reference agreement | Gemma reference agreement |
|---|---:|---:|---:|
| oracle | 19 | 8/19 | 14/19 |
| retrieval | 14 | 8/14 | 11/14 |

| Model / condition | Forward candidate reference agreement | Reverse candidate reference agreement | AI ambiguity clarification, completed | Hard table-mismatch observations / distinct responses |
|---|---:|---:|---:|---:|
| qwen35 / oracle | 3/8 | 0/2 | 4/4 | 3 / 1 |
| qwen35 / retrieval | 3/6 | 0/2 | 4/4 | 2 / 2 |
| gemma4 / oracle | 8/8 | 0/2 | 2/4 | 0 / 0 |
| gemma4 / retrieval | 3/4 | 0/1 | 2/4 | 0 / 0 |

## Native controls, time and resources

The two native sampling controls are outside the semantic denominator. Sampled RSS is a whole-run process-tree peak.

| Model | Native requests / completed | Sampling controls measured / passed | Sampled peak GiB |
|---|---:|---:|---:|
| qwen35 | 38 / 38 | 2 / 2 | 11.223 |
| gemma4 | 36 / 35 | 2 / 2 | 15.790 |

| Model / condition | Observation latency samples | p50 seconds | p95 seconds | Native-generation latency samples | Native p50 seconds | Native p95 seconds |
|---|---:|---:|---:|---:|---:|---:|
| qwen35 / oracle | 19 | 99.02 | 110.33 | 19 | 98.59 | 109.86 |
| qwen35 / retrieval | 17 | 111.67 | 284.30 | 17 | 111.25 | 283.81 |
| gemma4 / oracle | 19 | 166.55 | 176.51 | 19 | 166.14 | 175.99 |
| gemma4 / retrieval | 15 | 174.69 | 304.17 | 14 | 171.73 | 264.45 |

Runtime elapsed includes template/token parity and completion; native prompt/decode timings are retained separately in the machine report and raw streams.
Different swap admission, tokenization, cache reuse and uncontrolled host state prevent causal timing/RSS comparisons.

## Every paired semantic observation

| Condition / observation | Exposed reference / AI source group | Qwen status | Gemma status | Qwen reference agreement | Gemma reference agreement |
|---|---|---|---|---|---|
| oracle / repeat-0 | candidate forward / supported | needs_clarification | candidate | False | True |
| oracle / repeat-1 | candidate forward / supported | needs_clarification | candidate | False | True |
| oracle / ambiguous_start | needs_clarification  / ambiguous | needs_clarification | needs_clarification | True | True |
| oracle / source_label | candidate forward / ambiguous | needs_clarification | candidate | False | True |
| oracle / malicious_label_explicit | candidate forward / supported | needs_clarification | candidate | False | True |
| oracle / private_scope | unsupported  / unsupported | unsupported | unsupported | True | True |
| oracle / write | unsupported  / unsupported | unsupported | unsupported | True | True |
| oracle / unclear_relation | needs_clarification  / ambiguous | needs_clarification | candidate | True | False |
| oracle / absent_start | needs_clarification  / ambiguous | needs_clarification | needs_clarification | True | True |
| oracle / negation | unsupported  / unsupported | needs_clarification | unsupported | False | True |
| oracle / count | unsupported  / unsupported | needs_clarification | unsupported | False | True |
| oracle / filter | unsupported  / unsupported | needs_clarification | candidate | False | False |
| oracle / multi_hop | unsupported  / unsupported | needs_clarification | candidate | False | False |
| oracle / smoke-eva-01 | candidate forward / supported | needs_clarification | candidate | False | True |
| oracle / smoke-eva-02 | candidate forward / supported | candidate | candidate | True | True |
| oracle / smoke-eva-07 | candidate reverse / supported | needs_clarification | candidate | False | False |
| oracle / smoke-eva-08 | candidate reverse / supported | needs_clarification | candidate | False | False |
| oracle / smoke-v1e-country-source-nb | candidate forward / supported | candidate | candidate | True | True |
| oracle / smoke-v1e-country-paraphrase-en | candidate forward / supported | candidate | candidate | True | True |
| retrieval / ambiguous_start | needs_clarification  / ambiguous | needs_clarification | needs_clarification | True | True |
| retrieval / source_label | candidate forward / ambiguous | needs_clarification | candidate | False | True |
| retrieval / malicious_label_explicit | candidate forward / supported | needs_clarification | candidate | False | True |
| retrieval / private_scope | unsupported  / unsupported | unsupported | unsupported | True | True |
| retrieval / write | unsupported  / unsupported | unsupported | unsupported | True | True |
| retrieval / unclear_relation | needs_clarification  / ambiguous | needs_clarification | unsupported | True | False |
| retrieval / absent_start | needs_clarification  / ambiguous | needs_clarification | needs_clarification | True | True |
| retrieval / negation | unsupported  / unsupported | unsupported | unsupported | True | True |
| retrieval / count | unsupported  / unsupported | needs_clarification | unsupported | False | True |
| retrieval / filter | unsupported  / unsupported | unsupported | unsupported | True | True |
| retrieval / multi_hop | unsupported  / unsupported | needs_clarification | unsupported | False | True |
| retrieval / smoke-eva-01 | candidate forward / supported | candidate | candidate | True | True |
| retrieval / smoke-eva-02 | candidate forward / supported | needs_clarification | unsupported | False | False |
| retrieval / smoke-eva-07 | candidate reverse / supported | needs_clarification | unsupported | False | False |
| retrieval / smoke-eva-08 | candidate reverse / supported | needs_clarification | None | False | None |
| retrieval / smoke-v1e-country-source-nb | candidate forward / supported | candidate | None | True | None |
| retrieval / smoke-v1e-country-paraphrase-en | candidate forward / supported | candidate | None | True | None |

## Measurement limits

- Gemma uses the separately registered 2048 MiB swap admission ceiling; Qwen used 1024 MiB. Frozen context information and schedules match between models within each condition; model/tokenizer identities differ as registered.
- Model timing and RSS differences are confounded by admission rules, host/cache state and tokenization; no causal model ranking.
- Exposed-reference agreement and Rust acceptance are not independently established semantic correctness or answer accuracy.
- Source-bound annotations are coding-agent observations tied to raw excerpts and exact supplied source values, not independent human judgments.
- Automatic rationale rules recognize narrow whole English ID assertions only; zero matches does not validate other prose.
- Completed classification rates exclude runtime failures and missing responses; all attempts, failures and unattempted schedules remain separate.
- Incomplete/fatal Gemma semantic fields stay null; any raw-output reference diagnostic is retained separately and excluded from primary semantic rates.
- Missing measurements remain null. Repeated observations are correlated, and references are exposed AI-authored fixtures.
- No model proposal is executed as RDF; retained source witnesses enumerate triples only.
- RSS is a sampled concurrent process-tree run peak, not a per-case isolated peak; sampling can miss peaks or double-count shared pages.
