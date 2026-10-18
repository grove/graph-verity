# One-hop NL Ask v1 preregistration (#72)

This is a **model-free contract and exploratory public benchmark**, not evidence
of successful natural-language interpretation. Independent human reviews: **0**;
AI-authored questions and interpretation gold await independent review. The source
audit checks original triples and mappings, not the faithfulness of the questions.

The 60 new questions comprise **30 development and 30 evaluation cases**. Each
split has 15 Norwegian Bokmål and 15 English questions: 18 supported one-hop paths,
6 clarification requests and 6 unsupported requests. `cases.json` records every
question, instantiated intent/resource lineage, author/reviewer status, exact
reference request, full typed answer set and original graph-qualified witnesses.

Development uses the University of Tromsø, Kiruna/Piteå and GEMET acid rain;
evaluation uses the University of Jyväskylä, Ylöjärvi/Tampere and GEMET biogas.
The focal resources and instantiated intents stay in one split. Task families,
source archives, ontology vocabulary and some terminal IRIs are shared. This is
resource transfer within disclosed families, **not independent expert gold or
an unseen-domain evaluation**. Curated candidate catalogs test the contract with
explicitly resolved starts; they do not measure question-only retrieval (#73).

`manifest.json` pins extraction recipes, source revisions, capture timestamps,
licenses, graph origins and provenance. The Wikidata RDF archives are new.
GeoNames rows reuse the existing attributed CSV and Schema.org mapper; GEMET
concepts are extracted from the archived EEA 4.2.3 source, outside the prior
2200-concept selection. Importer graph names are explicit. `overlay.nq` contains
only synthetic adversarial labels: a duplicate Campus alias on two real IRIs and
an inert malicious label. These are **not upstream source assertions**. Missing
matches remain unknown under open-world semantics. No ontology inference occurs.

`freeze.json` pins payload/scorer/schema/source hashes, the split freeze date and
an exact Git payload commit. That commit contains the frozen payload; the next
commit adds its identity without a circular self-hash. Verification rejects
payload or hash changes. Future changes require a new version/freeze and must
retain this evidence. No model inference preceded this freeze.

`protocol.json` preregisters per-split exploratory goals: at least **17/18**
structurally faithful supported drafts and strict complete answer sets, **5/6**
correct model-origin clarifications and **5/6** unsupported statuses; at most **1**
false-positive candidate, **0** timeouts and **0** row/evidence truncations. Any
unapproved/non-read-only execution, scope access, private-canary breach or stale
approval acceptance stops the trial immediately (all maximum **0**). These goals
are fixed before model outputs. Failure means revise; an incomplete trial is
inconclusive. Passing is never production/release GO.

Historical Phase 0, #48 and #58 cases remain **exposed regressions**. Their
judgments and frozen evidence are unchanged. The external sealed 60-case Ask
holdout is excluded and untouched; nothing here opens, copies or scores it.

From the repository root, with the existing pinned Python dependencies:

```sh
cargo build --workspace --locked --offline
.venv/bin/python tools/nl_ask_benchmark.py verify
.venv/bin/python tools/nl_ask_benchmark.py baseline --split development
.venv/bin/python tools/nl_ask_benchmark.py baseline --split evaluation
```

The baseline traverses only frozen **gold references**, retaining full bindings
and witnesses. Its abstention fixtures are bookkeeping, not model performance.
Rust tests deliberately approve those gold fixtures to compare Oxigraph results
with the independent RDFLib reference. Ordinary CI requires no model runtime.

For a later separately authorized trial, first freeze retrieval/model/runtime
configuration as specified in `protocol.json`. Score exactly one JSONL record per
case in the requested split, preserving the original raw model text:

```json
{"id":"dev-01","runtime_status":"completed","raw_response":"{...original bytes as JSON text...}","decision":"cancelled"}
```

`runtime_status` is `completed`, `timeout`, `error` or `cancelled`. A completed record needs
raw text. An optional separately approved execution record includes `decision:
"approved"`, `approval_id`, and the original Confirmed Ask `execution` object.
Identity must match the Rust preview's plan, graph, snapshot and approval. Saved
execution records are operator-supplied evidence, not authenticated attestations;
the scorer cannot prove how they were obtained. Cancellation without execution
leaves answer agreement unmeasured; it never counts as model abstention.

```sh
.venv/bin/python tools/nl_ask_benchmark.py score --split development \
  --records /path/to/outcomes.jsonl --out artifacts/nl-ask/run-1.json
```

The scorer **only previews** drafts and scores saved results. It never invokes a
model, approves a proposal or executes its path. Reports retain raw records and
separate `invalid_json`, `invalid_contract`, `invalid_catalog_reference`,
`deterministic_preflight_block`, `model_needs_clarification`, `model_unsupported`,
`valid_draft_semantically_wrong`, runtime errors/timeouts, cancellation and both
truncation flags. Structural request agreement and strict complete RDF answer-set
agreement are separate metrics. All supported cases remain in denominators;
unmeasured answers are explicit. A valid executable plan leaves interpretation
`not_assessed_by_compiler`. Even a wrong path can return a coincidentally correct
empty set, which has a regression test. Report destinations must be new and
outside the frozen study directory.
