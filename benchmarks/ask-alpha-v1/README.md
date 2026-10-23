# Ask alpha v1: source-grounded automation, not independent gold

60 public development questions: **30 nb / 30 en**. Twenty-four retain the exact
PR #106 question strings; 36 are new agent-authored paraphrases and controls.
No independent humans, sealed holdouts or new inference were used. Decision:
**INCONCLUSIVE_REVISE**. This package does not complete the original human review.

| Primary sampling category | Questions |
|---|---:|
| Forward one hop | 12 |
| Reverse one hop | 12 |
| Multiple values | 8 |
| Ambiguous entity or predicate | 7 |
| Missing authorized vocabulary | 5 |
| Counts, numeric filters, multi-hop, write (original controls) | 4 |
| Injection-bearing source labels | 4 |
| Type-compatible reverse empty paths | 2 |
| Graph-scope confusion | 2 |
| Negation | 2 |
| Language filtering | 2 |

Categories overlap semantic features: supported reverse cases can return multiple
subjects; the source's hostile label appears in other Wikidata contexts too.
Wrong-but-executable controls live in the explicitly labelled retained synthetic
responses, rather than changing the questions' expected meanings.

**29 determinate plan references; 13 determinate non-execution outcomes** (eight
unsupported operations, five missing-authorized-predicate clarifications).
**18 unresolved interpretations**: seven lack independently retained property
meanings, seven involve ordinary entity/predicate ambiguity, two ask for the
wrong source graph, and two use ambiguous "published labels" wording.
Unresolved cases have no definitive gold plan or answer set; clarification is a
predeclared conservative automation target. A future source review can disagree.

## Files and provenance

- `questions.json`: original question, language and identity only; model-visible.
- `source.json`: mechanical snapshot facts with original N-Quads, one-based source
  lines, synthetic-overlay markers, graph licenses/revisions, and five property
  definitions extracted verbatim from retained CC0 Wikidata Turtle. The
  `wikibase:directClaim` mapping ties each property definition to the actual
  direct-claim predicate. Source metadata is independently available archived RDF,
  not a definition invented by this agent. English meanings support the declared
  Norwegian translations; those translations/intent mappings remain agent-authored.
- `references.json`: **operator/scorer only**, never a prompt input. Each question
  has its intended start, predicate, exact graph, direction, projection, witness
  IDs, complete snapshot answer terms when supported, provenance and determinacy.
  These intent mappings are separate from mechanical facts and have no independent
  human endorsement. Empty paths are typed, source-scoped absence observations,
  not assertions about the real world.
- `packets.json.gz`: deterministic gzip of the complete question-only Rust #82
  neighborhood packets, packet-local numeric selections and prompt contexts. No
  reference plan is used by retrieval or rendering. The five retained Wikidata
  definitions enrich only matching predicates in the authorized Wikidata graph;
  they never add numeric candidates. Other predicate meanings remain missing.
- `retained-synthetic.json`: 120 explicitly synthetic engineering observations,
  including wrong predicate/direction, graph drift, duplicate JSON keys, malformed
  output, timeout, transport failure, missing/unattempted cases, and optional
  retained source-evidence comparison. This is **not a model architecture trial**.
- `manifest.json`: exact bytes of source, vocabulary, questions, references and
  fixtures. The original #106 review manifest and source manifest are pinned.

Snapshot: `sha256:48f0c13ddab7ce2a7881509192be30c1fe08693b4e7df5991e68cb302c20561b`.
Named graphs were assigned by the importer. Wikidata facts/definitions are CC0;
GeoNames and GEMET material is CC-BY-4.0 with the original attribution retained in
`studies/nl-ask-v1/manifest.json`; Campus and hostile labels are Apache-2.0 synthetic
overlays. No original source or reference was edited. No new property-definition
claim is made for Schema.org, SKOS or RDFS on the basis of IRI spelling alone.

## Reproduction and scoring

Run from repository root with the existing pinned Python environment and built
Rust binary:

```sh
.venv/bin/python tools/ask_alpha_benchmark.py
.venv/bin/python tools/ask_alpha_evaluation.py packets
.venv/bin/python tools/ask_alpha_benchmark.py
.venv/bin/python tools/ask_alpha_evaluation.py score \
  --retained benchmarks/ask-alpha-v1/retained-synthetic.json \
  --out artifacts/ask-alpha-score-fresh
```

The first three commands rebuild this preparation deterministically; future
scoring verifies the manifest and does not refresh any input. Use a fresh output
directory for each score. The scorer accepts `origin` (`synthetic_fixture` or
`retained_local_model`), distinct scheduled `conditions`, and retained `rows` with
`condition`, `id`, `outcome` (`completed`, `failed`, `timed_out`, `unattempted`),
untouched UTF-8 `raw_draft` for completed rows, and optional `failure`. Unknown or
duplicate observations fail. Omitted scheduled identities remain unattempted.
A timed-out partial object never becomes a completed model status.

All five fields are resolved against each packet's exact graph-qualified numeric
selection. Missing numeric start/predicate/graph is measured before scoring.
Rust sees the original string through `nl-ask-preview`; the scorer has **no
execution call**. Setting `resolved_start` to the proposed start is a validation
probe, not a claim that a human resolved the identity or approved execution.
Rust acceptance of abstention is distinct from acceptance of a candidate plan.

`score.json` retains per-row field/status agreement, retrieval coverage, Rust
stdout/stderr, failures, source insufficiency and unresolved guesses. It includes
scheduled and completed supported denominators, language/direction/category
strata, and paired completed identities for exactly two conditions. Wrong but
executable is an accepted candidate contradicting a determinate reference; the
rate over all accepted candidates is a **known-error lower bound**, since
unresolved candidates have unknown semantic correctness and are counted separately.
`failures.md` names cases, field errors, missing vocabulary and accepted wrong plans.

An optional `answer_evidence` holds exact N3 `terms`, `source_witnesses` fact IDs,
`snapshot_id`, `complete_rows` and `complete_evidence`. It is scored only for
matching determinate plans, against source-derived terms/witnesses. Clipped or
wrong-snapshot receipts fail. This is exposed snapshot agreement, not independent
answer correctness. No answers are produced by the scorer.

Unjustified relationship selection flags wrong/unknown predicates and candidates
on unresolved references conservatively. It does **not** read a rationale as
proof of its own meaning. Free-text rationale claims require a source audit;
existing model rationale findings are linked in the alpha assessment. Schema,
field agreement, Rust acceptance and independent semantic correctness remain
separate. Human comprehension is unmeasured.
