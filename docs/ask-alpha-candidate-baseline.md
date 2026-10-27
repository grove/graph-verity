# Exposed Ask-alpha candidate baseline

This is a descriptive readout of the immutable `benchmarks/ask-alpha-v1`
question-only packets. It does not add or refresh benchmark cases, packets,
references, or human labels. Reproduce the summary with:

```sh
python3 -B tools/ask_alpha_candidate_metrics.py
```

The script verifies the benchmark manifest before reading the saved packets. It
performs no retrieval, graph query, model inference, or holdout access.

## Candidate positions

The benchmark contains 60 exposed development questions (30 English, 30
Norwegian). Twenty-nine have coding-agent-authored determinate candidate plan
references. There are zero independent human relevance judgments.

| Reference target present by rank | @1 | @5 | @10 | Denominator |
|---|---:|---:|---:|---:|
| Entity in the BM25 seed list | 27 | 28 | 28 | 29 |
| Predicate in the v2 combined list | 6 | 20 | 29 | 29 |
| Both targets in their lists | 6 | 20 | 28 | 29 |

By language, both targets were present by rank 5 in 9/14 English and 11/15
Norwegian cases. By reference direction, both were present by rank 5 in 11/17
forward and 9/12 reverse cases. These are exact graph-and-IRI reference hits,
not human relevance or answer accuracy.

The entity list is the BM25 seed list. The predicate list is the v2 combination
of lexical candidates and source-witnessed neighboring predicates, so its ranks
are not BM25-only ranks. All 29 target predicates appear in the saved v2 packet
with score zero, which v2 assigns to added neighbors. That does not prove the
predicate has no lexical rank beyond the packet's retained BM25 list. The saved
packets do not preserve a separate full predicate BM25 ranking for these 60
cases.

The saved packet usage contains the expected directed source witness for all
27 non-empty agent-reference paths. The other two references intentionally
describe empty reverse paths and have no positive source witness. This checks
source-edge availability in the retained packet, not natural-language direction
understanding. Twenty-eight of the 29 candidate-reference packets are clipped;
missing candidates and edges therefore remain unknown.

## Observed source-witnessed entity gap

In `alpha-08`, the agent-authored reference expects Q20 as the start entity for
an incoming P17 operation. Q20 is absent from the BM25 entity seed list, while
the retained list contains Q279724 at rank 3. That seed's packet includes the
original outgoing statement `Q279724 —P17→ Q20`. The Local Ask suggestions now
show Q20 as a separate neighboring entity with that witness. It has no
question-relevance rank or selection button: this demo still permits only
Q279724, P856, and P1448. Its query scope and operation allowlist are unchanged.

Suggestion lists were non-empty on all 23 agent-reference clarification cases
and on 5/8 unsupported cases. These are candidate returns, not false-positive
labels: the references are not human gold, and the UI requires explicit manual
selection.

## Interpretation and next step

The measured miss supports surfacing an adjacent entity only as a
source-witnessed candidate, which this slice does. The v2 list improves
candidate availability but its predicate order does not show question
relevance. The next useful measurement is a separately registered comparison
of pure BM25 predicate rankings and v2 neighborhood results on the same 60
exposed cases, before considering a new retrieval model.

Nothing here changes the historical `INCONCLUSIVE_REVISE` result. Candidate
coverage on this small exposed development set is not a statistically
meaningful benchmark.
