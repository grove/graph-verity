# Paired Ask-alpha retrieval baseline

This model-free baseline compares two existing candidate paths on the same
exposed `ask-alpha-v1` questions and authorized development snapshot:

1. `question-vocabulary-packet-v1`: whole-question BM25 candidates.
2. `question-vocabulary-packet-v2-neighborhood`: BM25 seeds plus witnessed
   neighborhood candidates in the combined order.

The 60 questions are 30 English and 30 Norwegian. Scoring uses the 29 existing
coding-agent-authored candidate references; those are development annotations,
not human relevance judgments. The existing scope includes the repository's
Wikidata, GeoNames, and GEMET development graphs. Their licenses and source
provenance remain those pinned in
[`ask-alpha-v1`](../benchmarks/ask-alpha-v1/README.md). This adds no source or
license.

## Predeclared method

Capture both packets for every question with the same snapshot, index revision,
scope, and retrieval budget. Capture reads the question file and verifies the
existing input manifest, including the reference file hash; it does not parse or
pass reference annotations to retrieval. The capture is saved before the
separate scoring command parses those annotations.
The capture is saved before the separate scoring command reads those references.
The capture pins its runner, protocol, Rust source, binary, and benchmark input
hashes, and stores only graph-qualified candidate identities, order, exact-match
flags, scores, clipping status, and candidate-list hashes.

Report exact graph+IRI target positions at ranks 1, 5, and 10 for entities,
predicates, and both together. Break out English/Norwegian and forward/reverse
candidate-reference cases. Count non-empty candidate lists for clarification
and unsupported references as suggestion returns; do not call them false
positives. Report clipping separately. Rank and BM25 score are retrieval
measurements, not probabilities or relevance judgments.

The v2 position is explicitly a combined lexical and witnessed-neighborhood
position; its added neighbors use score zero. BM25 scores are not probabilities.
Candidate targets absent from a clipped packet are unknown. No answer
generation, answer query execution, model inference, or sealed-holdout access is
part of this comparison. The evaluation does not
establish question understanding or answer accuracy.

## Reproduction

Build the existing Rust CLI, then capture and score to new output paths:

```sh
cargo build --locked --offline --bin verity
.venv/bin/python -B tools/ask_alpha_paired_retrieval.py capture \
  --out /private/tmp/ask-alpha-paired-capture.json
.venv/bin/python -B tools/ask_alpha_paired_retrieval.py score \
  --capture /private/tmp/ask-alpha-paired-capture.json \
  --out /private/tmp/ask-alpha-paired-report.json
```

Capture and score refuse to overwrite outputs. Scoring verifies all input hashes
and candidate-list digests before parsing the references. The paired capture is
separate from the frozen `ask-alpha-v1` packets, manifests, receipts, and
historical decision.
