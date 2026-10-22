# Reverse-direction failure matrix

AI-authored exposed references; independent human review pending. A rationale describing a reverse edge is not a candidate plan.

| Condition / case | Baseline → new model status | Exposed reference fields | Actual start / predicate / graph / direction / output | Rust accepted | Reference agreement | Stored source witness |
|---|---|---|---|---|---|---|
| oracle / eva-07 | needs_clarification → needs_clarification | 100 / 1002 / 0 / reverse / values | null (no candidate) | True | False | <http://www.wikidata.org/entity/Q578326> <http://www.wikidata.org/prop/direct/P131> <http://www.wikidata.org/entity/Q134620> <urn:graph-verity:nl-ask-v1:evaluation:wikidata> |
| oracle / eva-08 | needs_clarification → needs_clarification | 103 / 1006 / 0 / reverse / values | null (no candidate) | True | False | <http://www.wikidata.org/entity/Q578326> <http://www.wikidata.org/prop/direct/P856> <https://www.jyu.fi/> <urn:graph-verity:nl-ask-v1:evaluation:wikidata> |
| retrieval / eva-07 | unsupported → unsupported | 100 / 1002 / 0 / reverse / values | null (no candidate) | True | False | <http://www.wikidata.org/entity/Q578326> <http://www.wikidata.org/prop/direct/P131> <http://www.wikidata.org/entity/Q134620> <urn:graph-verity:nl-ask-v1:evaluation:wikidata> |
| retrieval / eva-08 | needs_clarification → needs_clarification | 103 / 1006 / 0 / reverse / values | null (no candidate) | True | False | <http://www.wikidata.org/entity/Q578326> <http://www.wikidata.org/prop/direct/P856> <https://www.jyu.fi/> <urn:graph-verity:nl-ask-v1:evaluation:wikidata> |

All five expected fields, numeric vocabulary coverage, exact raw/context hashes, complete rationales, source/provenance review and baseline status are retained in analysis.json. Missing outcomes are null.
