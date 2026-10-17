# Adversarial and paired-ontology regression tests (#9)

The public `adversarial` suite contains 15 paired questions per ontology, 30 total.
These are original synthetic Apache-2.0 fixtures with AI-authored references, not
expert gold or a sealed evaluation. Neither the private holdout nor its questions
are read, regenerated, adapted or passed to inference.

The two [snapshots](../data/adversarial/snapshot.nq) and
[transfer snapshot](../data/adversarial-transfer/snapshot.nq) represent the same
small procurement scenario. Source predicates use a private example vocabulary;
transfer predicates use Schema.org `subOrganization`, `subjectOf`,
`numberOfEmployees`, `startDate`, `dateModified` and `keywords`. The mapping is an
explicit synthetic importer convention, not an assertion that these properties
are interchangeable for arbitrary real data. Identical questions and case IDs
make the per-category gap a paired vocabulary/ontology adaptation diagnostic.
This is not independent generalization: both ontologies are exposed development
material. The independently sourced GeoNames/Schema.org benchmark and its local
model results remain separately documented in [the parser experiment](local-parser-experiment.md).

Permitted adaptation consists only of the new RDF vocabulary, authorized catalog,
reference plans/queries and frozen answer bindings. Model, tokenizer, runtime,
grammar, prompt, sampling and selection logic stay pinned to the existing config.
No tuning on results is performed. `limit=100` matches the frozen prompt.

## Run without a model (normal CI)

```sh
cargo fetch --locked
.venv/bin/python -m unittest discover -s tools -p 'test_adversarial.py' -v
```

The test builds the existing CLI offline and executes all 24 answerable plans in
Rust/Oxigraph, then independently checks the reference SPARQL against RDFLib and
frozen bindings. Six expected abstentions are explicitly **bookkeeping** in oracle
mode. All 30 authorized catalogs and exact model prompts are checked for private
canaries, excluded comment text and ChatML message boundaries. Both entities with
the ambiguous alias must reach the selected context. Existing compiler/parser
regressions independently reject unauthorized graph scopes, graph-local identifier
misuse, raw SPARQL, negation and invalid contracts; no model is involved.

`tools/verify_pre_llm.py`, used by normal CI, discovers these tests. Dependency
fetch runs before Python tests because the cross-engine test builds the Rust CLI.
No new package dependency, model download or CI inference is introduced.

## Run the actual frozen model (opt in)

```sh
# One-time online preparation, if the pinned assets are not already installed:
.venv/bin/python tools/local_parser.py prepare
cargo build --locked -p verity_cli
# Offline inference; choose a fresh directory for every run:
.venv/bin/python tools/local_parser.py run --suite adversarial --out artifacts/issue9-model/run-1
```

Expect several minutes on the approved four-thread M1 Pro CPU. The existing runner
checks hashes, regenerates/validates the grammar, executes generation controls,
starts its owned CPU-only loopback runtime, bounds each request and preserves
proposals and failures. A completed run writes `run.json`, per-dataset reports,
requests, selected vocabulary, prompts, generated text, server logs, an
`adversarial-summary.json`/`.md`, and a checksummed `adversarial-manifest.json`.
The manifest pins every retained file plus the run's source/config/input hashes.
A partial run retains a failure manifest. Nothing overwrites a previous run.

The command exits nonzero after preserving the complete measurement if any case
fails its expected behavior: complete exact bindings for supported questions;
`unsupported` or `needs_clarification` for ambiguous/unsupported ones. Parser errors
and compiler rejection are safe containment but do not satisfy semantic abstention.
An equivalent plan with identical named bindings may pass even when variable/order
sensitive structural equality misses. Runtime-dependent tests need the pinned
assets and are deliberately outside ordinary CI. Deterministic generation settings
do not promise identical tokens across native builds or hardware.

## Failure modes and metrics

- Explicit inverse direction and directed two-hop joins.
- `>` versus `>=` at exactly 51; dates and RFC3339 date-times at the boundary.
- `COUNT(DISTINCT)` with two contracts multiplied by two tags.
- Named-graph leakage: the operator can access both graphs, but the question is
  scoped to public. A conflicting private employee value must never affect answers.
- Duplicate exact aliases; missing vocabulary; unsupported open-world negation.
- Missing triples: expected empty scoped bindings, never zero employees or a
  statement of real-world absence.
- Actual RDF label attacks requesting raw SPARQL, wider scopes and shell execution,
  including ChatML delimiters. The expected result stays the requested employee
  value; prompt text and model output have no tool dispatch authority.
- Malicious RDF comments are excluded from the catalog by design, so no comment
  instruction reaches inference. Tests assert that exclusion explicitly.

JSON reports preserve the existing JSON/contract validity, compiler safety,
structural match, complete exact answers, precision/recall/F1, expected-status
abstention and error stages. Each category additionally reports false positives
(executed wrong/incomplete answers or any execution on an expected abstention,
divided by **all questions** in that category), false abstentions (divided by
supported questions), safe semantic abstentions and failure to abstain (divided by
expected abstentions). Rejections remain visible; they never count as correct
semantic abstentions. Empty denominators are `not_applicable`, not zero risk.

Absolute source/transfer gaps for complete exact answers, correct expected-status
abstention, false abstention and false positives appear **per category**, with `null` for inapplicable
gaps. Rates include Wilson intervals; tiny correlated synthetic categories cannot
establish a population error rate. The boundary audit checks requested scope,
prompt canaries, execution scope/snapshot and evidence graph identity. The typed
Rust parser and compiler, rather than model obedience, enforce executable scope.
A failed model probe is evidence of an inadequate configuration, not a reason to
weaken the reference or claim issue #9's semantic robustness is established.

The [first retained frozen-model run](../reports/issue-9-adversarial/README.md) failed all 30 expected-behavior assertions. Its complete proposals, category diagnostics and checksummed evidence remain available; issue #9's actual semantic robustness criteria remain unmet.
