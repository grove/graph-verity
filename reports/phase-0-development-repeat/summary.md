# Phase 0 evaluation

Formal decision: **NOT READY**.

Public AI-reference agreement; no expert semantic validation or production-readiness claim.

| Dataset | Metric | Numerator / denominator | Value | 95% Wilson interval |
|---|---|---|---|---|
| wikidata | json_valid | 41/46 | 0.8913043478260869 | [0.7696189698736853, 0.9526692391725731] |
| wikidata | contract_valid | 41/46 | 0.8913043478260869 | [0.7696189698736853, 0.9526692391725731] |
| wikidata | structural_ir | 0/38 | 0.0 | [0, 0.09181293258383999] |
| wikidata | exact_answer | 3/38 | 0.07894736842105263 | [0.02721410139426493, 0.2079967892026529] |
| wikidata | correct_abstention | 0/8 | 0.0 | [0, 0.3244156195108769] |
| wikidata | false_abstention | 0/38 | 0.0 | [0, 0.09181293258383999] |
| wikidata | failure_to_abstain | 8/8 | 1.0 | [0.6755843804891231, 1] |
| wikidata | candidate_on_expected_abstention | 6/8 | 0.75 | [0.40926987910258916, 0.9285223111419724] |
| wikidata | wrong_plan_executed | 19/46 | 0.41304347826086957 | [0.2828839329710102, 0.5566075761298211] |
| wikidata | wrong_plan_among_executions | 19/19 | 1.0 | [0.8318156346315496, 1] |
| worldcities-transfer | json_valid | 32/40 | 0.8 | [0.6524239261814333, 0.8950013502683314] |
| worldcities-transfer | contract_valid | 32/40 | 0.8 | [0.6524239261814333, 0.8950013502683314] |
| worldcities-transfer | structural_ir | 0/35 | 0.0 | [0, 0.09890426758938868] |
| worldcities-transfer | exact_answer | 0/35 | 0.0 | [0, 0.09890426758938868] |
| worldcities-transfer | correct_abstention | 0/5 | 0.0 | [0, 0.43449149475208104] |
| worldcities-transfer | false_abstention | 0/35 | 0.0 | [0, 0.09890426758938868] |
| worldcities-transfer | failure_to_abstain | 5/5 | 1.0 | [0.5655085052479191, 1] |
| worldcities-transfer | candidate_on_expected_abstention | 5/5 | 1.0 | [0.5655085052479191, 1] |
| worldcities-transfer | wrong_plan_executed | 8/40 | 0.2 | [0.10499864973166874, 0.34757607381856676] |
| worldcities-transfer | wrong_plan_among_executions | 8/8 | 1.0 | [0.6755843804891231, 1] |

| Dataset / family | Exact answer | Structural IR | Correct abstention | Macro P / R / F1 (all supported) |
|---|---|---|---|---|
| wikidata / ambiguous | 0/0 | 0/0 | 0/2 | {'precision': None, 'recall': None, 'f1': None} |
| wikidata / conjunction_distinct_count | 0/1 | 0/1 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / conjunction_numeric_date | 0/1 | 0/1 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / date_comparison | 0/4 | 0/4 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / date_lookup | 0/4 | 0/4 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / direct_relation | 0/4 | 0/4 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / distinct_count | 0/2 | 0/2 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / entity_labels | 0/4 | 0/4 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / grouping | 0/1 | 0/1 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / having | 0/2 | 0/2 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / inverse_relation | 3/4 | 0/4 | 0/0 | {'precision': 0.75, 'recall': 0.75, 'f1': 0.75} |
| wikidata / named_graph_scope | 0/1 | 0/1 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / numeric_comparison | 0/6 | 0/6 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / two_hop | 0/4 | 0/4 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| wikidata / unsupported | 0/0 | 0/0 | 0/6 | {'precision': None, 'recall': None, 'f1': None} |
| worldcities-transfer / ambiguous_largest | 0/0 | 0/0 | 0/1 | {'precision': None, 'recall': None, 'f1': None} |
| worldcities-transfer / direct_region | 0/5 | 0/5 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| worldcities-transfer / distinct_city_count | 0/5 | 0/5 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| worldcities-transfer / group_having | 0/5 | 0/5 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| worldcities-transfer / identity_label | 0/5 | 0/5 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| worldcities-transfer / inverse_region | 0/5 | 0/5 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| worldcities-transfer / missing_ownership_domain | 0/0 | 0/0 | 0/1 | {'precision': None, 'recall': None, 'f1': None} |
| worldcities-transfer / missing_population | 0/0 | 0/0 | 0/1 | {'precision': None, 'recall': None, 'f1': None} |
| worldcities-transfer / numeric_identifier | 0/5 | 0/5 | 0/0 | {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} |
| worldcities-transfer / open_world_negation | 0/0 | 0/0 | 0/1 | {'precision': None, 'recall': None, 'f1': None} |
| worldcities-transfer / subjective_criterion | 0/0 | 0/0 | 0/1 | {'precision': None, 'recall': None, 'f1': None} |
| worldcities-transfer / two_hop_country | 0/5 | 0/5 | 0/0 | {'precision': 0.05, 'recall': 0.2, 'f1': 0.08} |

Recorded inference performance: inherited_from_recorded_run. Replay stage timings are not model measurements.

| Dataset | Warm E2E p50 / p95 / p99 ms | Generation p50 / p95 / p99 ms | Process-cold first answer ms |
|---|---|---|---|
| wikidata | {'p50': 9612.649583999999, 'p95': 26039.330959000003, 'p99': 32521.308458999996} | {'p50': 9595.811042, 'p95': 26028.816124999998, 'p99': 32515.438375} | 16800.91829219809 |
| worldcities-transfer | {'p50': 9346.818292, 'p95': 23280.955250000003, 'p99': 23376.896167000003} | {'p50': 9338.583875, 'p95': 23207.349125, 'p99': 23374.071042} | 16722.118292018302 |

Recorded CPU: Apple M1 Pro; OS: macOS-26.6.2-arm64-arm-64bit; logical cores: 10; threads: 4; system RAM bytes: 34359738368; accelerators disabled by recorded CPU-only build.
Sampled aggregate peak RSS KiB: 1529616; samples: 4572. 200ms descendant samples include startup and ps overhead, may miss spikes and double-count shared pages; OS child high-water mark is separate
Cache: new server per dataset; OS page cache not evicted; cache_prompt=True. No disk-cold measurement. Target deployment CPU is not designated.
Historical M1 Pro warm p95 (28.06/26.59 seconds) exceeds the proposed 10-second budget; cold first answers (17.68/18.04 seconds) and sampled RSS (1.43 GiB) are below proposed budgets. These are descriptive historical comparisons, not target-CPU gate passes.

| Gate | Status | Actual | Requirement | Reason |
|---|---|---|---|---|
| supported_question_exact_answer_set_min | fail | 0.0 | >= 0.95 | Descriptive public AI-reference agreement; structural equality is conservative |
| per_supported_family_exact_answer_set_min | fail | 0.0 | >= 0.9 | Descriptive public AI-reference agreement; structural equality is conservative |
| semantic_plan_accuracy_min | fail | 0.0 | >= 0.95 | Descriptive public AI-reference agreement; structural equality is conservative |
| unflagged_wrong_plan_answers_max_count | unavailable | None | <= 0 | Descriptive public AI-reference agreement; structural equality is conservative |
| correct_abstention_on_unsupported_or_ambiguous_min | fail | 0.0 | >= 0.95 | Descriptive public AI-reference agreement; structural equality is conservative |
| false_abstention_on_supported_questions_max | pass | 0.0 | <= 0.1 | Descriptive public AI-reference agreement; structural equality is conservative |
| transfer_exact_answer_accuracy_gap_max_absolute | pass | 0.07894736842105263 | <= 0.1 | Descriptive public AI-reference agreement; structural equality is conservative |
| unauthorized_execution_or_scope_disclosure_max_count | unavailable | None | <= 0 | Descriptive public AI-reference agreement; structural equality is conservative |
| raw_sparql_or_write_execution_max_count | unavailable | None | <= 0 | Descriptive public AI-reference agreement; structural equality is conservative |
| wikidata_exact_answer_samples | fail | 38 | >= 100 | Proposed minimum; sample counts alone never establish negligible risk |
| wikidata_correct_abstention_samples | fail | 8 | >= 20 | Proposed minimum; sample counts alone never establish negligible risk |
| wikidata_conjunction_distinct_count_samples | fail | 1 | >= 5 |  |
| wikidata_conjunction_numeric_date_samples | fail | 1 | >= 5 |  |
| wikidata_date_comparison_samples | fail | 4 | >= 5 |  |
| wikidata_date_lookup_samples | fail | 4 | >= 5 |  |
| wikidata_direct_relation_samples | fail | 4 | >= 5 |  |
| wikidata_distinct_count_samples | fail | 2 | >= 5 |  |
| wikidata_entity_labels_samples | fail | 4 | >= 5 |  |
| wikidata_grouping_samples | fail | 1 | >= 5 |  |
| wikidata_having_samples | fail | 2 | >= 5 |  |
| wikidata_inverse_relation_samples | fail | 4 | >= 5 |  |
| wikidata_named_graph_scope_samples | fail | 1 | >= 5 |  |
| wikidata_numeric_comparison_samples | pass | 6 | >= 5 |  |
| wikidata_two_hop_samples | fail | 4 | >= 5 |  |
| worldcities-transfer_exact_answer_samples | fail | 35 | >= 100 | Proposed minimum; sample counts alone never establish negligible risk |
| worldcities-transfer_correct_abstention_samples | fail | 5 | >= 20 | Proposed minimum; sample counts alone never establish negligible risk |
| worldcities-transfer_direct_region_samples | pass | 5 | >= 5 |  |
| worldcities-transfer_distinct_city_count_samples | pass | 5 | >= 5 |  |
| worldcities-transfer_group_having_samples | pass | 5 | >= 5 |  |
| worldcities-transfer_identity_label_samples | pass | 5 | >= 5 |  |
| worldcities-transfer_inverse_region_samples | pass | 5 | >= 5 |  |
| worldcities-transfer_numeric_identifier_samples | pass | 5 | >= 5 |  |
| worldcities-transfer_two_hop_country_samples | pass | 5 | >= 5 |  |
| warm_end_to_end_p95_seconds_max | unavailable | None | <= 10 | not_measured_no_separately_designated_target_cpu |
| cold_first_answer_seconds_max | unavailable | None | <= 30 | not_measured_no_separately_designated_target_cpu |
| whole_process_peak_rss_gib_max | unavailable | None | <= 8 | not_measured_no_separately_designated_target_cpu |
| independent_human_gold_review | unavailable | False |  True | Required evidence, not inferred from engineering success |
| independent_locked_question_split | unavailable | False |  True | Required evidence, not inferred from engineering success |
| runtime_model_tokenizer_prompt_grammar_hashes | pass | True |  True | Required evidence, not inferred from engineering success |
| numerical_gates_approved_before_holdout | unavailable | False |  True | Required evidence, not inferred from engineering success |
| actual_target_cpu_recorded | unavailable | False |  True | Required evidence, not inferred from engineering success |
| oracle_regression_pass_fraction | unavailable | None |  1.0 | Required evidence, not inferred from engineering success |
| preregistered_run | unavailable | None |  frozen_before_first_holdout | Later threshold approvals cannot retroactively pass an earlier run |
| approval | unavailable | proposal_not_approved |  approved_bound_thresholds | Proposal comparisons cannot authorize GO |

Revise the measured configuration; abandon unattended unrestricted Ask for this configuration. Keep exact resolution/manual typed plans. This recommendation is separate from a formally approved gate decision.

Wilson 95% for rates and fixed-seed 1000-resample percentile bootstrap for macro P/R/F1. Descriptive only: related templates and AI reference correlation invalidate independence claims; zero errors never prove zero risk.

Wrong-plan execution is a conservative structural proxy. Observed user-facing false confidence is not measured.
Empty bindings do not establish real-world falsity; missing facts remain unknown without independent completeness evidence.
