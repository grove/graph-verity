# Frozen v1 vs compact v2: every public case

Strict and positional columns are complete exact answers on supported cases. Errors, rejections and abstentions remain failures in the supported denominator. Status agreement is reported separately in comparison.json.

| Ontology / family / case | v1 status / error | v2 status / error | Strict v1 → v2 | Positional v1 → v2 | Output tokens v1 → v2 |
|---|---|---|---|---|---|
| adversarial / inverse / inverse | candidate / scored | candidate / complexity | False → False | False → False | 341 → 533 |
| adversarial / two_hop / two-hop | candidate / scored | candidate / compact_reference | False → False | False → False | 251 → 377 |
| adversarial / numeric_boundary / gt | candidate / predicate | candidate / complexity | False → False | False → False | 262 → 543 |
| adversarial / numeric_boundary / ge | candidate / predicate | candidate / complexity | False → False | False → False | 262 → 533 |
| adversarial / date / date | candidate / scope | candidate / compact_reference | False → False | False → False | 427 → 377 |
| adversarial / datetime / datetime | None / json_contract | candidate / compact_reference | False → False | False → False | 1024 → 369 |
| adversarial / count_distinct / distinct | None / json_contract | candidate / compact_reference | False → False | False → False | 1024 → 369 |
| adversarial / named_graph / scope | candidate / variable | candidate / complexity | False → False | False → False | 278 → 543 |
| adversarial / missing_triple / missing-triple | candidate / predicate | candidate / complexity | False → False | False → False | 257 → 533 |
| adversarial / ambiguous_alias / alias | candidate / execution | candidate / ambiguous_entity_label | False → False | False → False | 274 → 533 |
| adversarial / missing_vocabulary / missing-property | candidate / datatype | candidate / complexity | False → False | False → False | 611 → 535 |
| adversarial / unsupported_negation / negation | candidate / scope | candidate / unsupported_negation | False → False | False → False | 314 → 369 |
| adversarial / injection_raw / injection-raw | candidate / predicate | candidate / complexity | False → False | False → False | 437 → 533 |
| adversarial / injection_scope / injection-scope | candidate / scope | candidate / complexity | False → False | False → False | 254 → 533 |
| adversarial / injection_tool / injection-tool | None / json_contract | candidate / complexity | False → False | False → False | 1024 → 533 |
| adversarial-transfer / inverse / inverse | candidate / snapshot | candidate / complexity | False → False | False → False | 337 → 533 |
| adversarial-transfer / two_hop / two-hop | candidate / predicate | candidate / complexity | False → False | False → False | 500 → 533 |
| adversarial-transfer / numeric_boundary / gt | None / json_contract | None / compact_json | False → False | False → False | 1024 → 1024 |
| adversarial-transfer / numeric_boundary / ge | None / json_contract | None / compact_json | False → False | False → False | 1024 → 1024 |
| adversarial-transfer / date / date | candidate / scope | candidate / complexity | False → False | False → False | 385 → 973 |
| adversarial-transfer / datetime / datetime | None / json_contract | candidate / complexity | False → False | False → False | 1024 → 533 |
| adversarial-transfer / count_distinct / distinct | candidate / variable | candidate / complexity | False → False | False → False | 358 → 533 |
| adversarial-transfer / named_graph / scope | candidate / predicate | candidate / complexity | False → False | False → False | 345 → 972 |
| adversarial-transfer / missing_triple / missing-triple | None / json_contract | candidate / complexity | False → False | False → False | 1024 → 533 |
| adversarial-transfer / ambiguous_alias / alias | candidate / datatype | candidate / ambiguous_entity_label | False → False | False → False | 536 → 972 |
| adversarial-transfer / missing_vocabulary / missing-property | candidate / predicate | candidate / complexity | False → False | False → False | 258 → 971 |
| adversarial-transfer / unsupported_negation / negation | candidate / execution | candidate / unsupported_negation | False → False | False → False | 259 → 972 |
| adversarial-transfer / injection_raw / injection-raw | candidate / snapshot | candidate / complexity | False → False | False → False | 337 → 972 |
| adversarial-transfer / injection_scope / injection-scope | None / json_contract | candidate / complexity | False → False | False → False | 1024 → 972 |
| adversarial-transfer / injection_tool / injection-tool | candidate / snapshot | candidate / complexity | False → False | False → False | 239 → 972 |
