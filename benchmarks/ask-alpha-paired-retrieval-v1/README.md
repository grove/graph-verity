# Paired Ask-alpha retrieval results

Reproduce the capture and summary with the commands in
[`docs/ask-alpha-paired-retrieval.md`](../../docs/ask-alpha-paired-retrieval.md).
The retained [capture](capture.json) contains only graph-qualified candidate
IDs, ranks, exact-match flags, scores, clipping state, and hashes. It does not
contain candidate source text. The [machine-readable report](report.json)
contains per-case reference positions and descriptive counts.

## Results

The paired capture used the same 60 questions (30 English, 30 Norwegian),
snapshot `sha256:48f0c13ddab7ce2a7881509192be30c1fe08693b4e7df5991e68cb302c20561b`,
three-graph authorized development scope, index revision, and retrieval budget
for both methods. There are 29 agent-authored candidate references and zero
human relevance labels.

| Exact graph+IRI reference present by rank | BM25 entity / predicate / both | Neighborhood v2 entity / predicate / both |
|---|---:|---:|
| @1 | 27 / 0 / 0 of 29 | 27 / 6 / 6 of 29 |
| @5 | 28 / 0 / 0 of 29 | 28 / 20 / 20 of 29 |
| @10 | 28 / 0 / 0 of 29 | 28 / 29 / 28 of 29 |

Neighborhood v2 added 20 predicate-target hits by rank 5 and 29 by rank 10,
with no predicate-target hits lost at those cutoffs in this set. Its predicate
list combines BM25 candidates with source-witnessed neighbors; these are
candidate-position comparisons, not relevance or answer-accuracy improvements.
The v2 list found 9/14 English and 11/15 Norwegian cases with both targets by
rank 5; the BM25-only list found 0 in both language groups. By direction, v2
found 11/17 forward and 9/12 reverse cases with both targets by rank 5.

Examples: for `alpha-01` (Norwegian, forward P17), the BM25-only predicate list
was empty and v2 ranked P17 fifth. For `alpha-08` (English, reverse P17), the
BM25-only predicate list was empty and v2 ranked P17 eighth; the entity target
is still absent from the BM25 seed list and appears only through the
source-witnessed neighbor shown in the UI.

Candidate lists were returned on 6/23 clarification and 1/8 unsupported
references by BM25, versus 23/23 and 5/8 by v2. These are suggestion-return
counts, not false-positive judgments. Twenty-eight of 29 candidate-reference
packets were clipped for both methods; missing candidates in clipped packets
remain unknown. All references are coding-agent-authored and none was reviewed
for relevance by an independent human.

This paired rank capture does not measure latency, peak RSS, or index size, and
does not cover the full #114/#115 acceptance work. Those remain open.

The capture code was frozen at commit `7d9a9a631c28e5999d4de15253018dca6fe694ad`.
The paired retrieval performed no model inference or answer-query execution.
This report is separate from the frozen `ask-alpha-v1` packet set and does not
change its receipts or `INCONCLUSIVE_REVISE` decision.

## Next change

Before a dense-retrieval trial, index the already retained licensed property
labels and descriptions as graph-local predicate text, preserving their
original source and license provenance. Then rerun this paired comparison. The
observed bottleneck is the empty BM25 predicate list for all 29 expected target
predicates at rank 10; a source-backed lexical enrichment is cheaper to assess
than adding a new retrieval model.
