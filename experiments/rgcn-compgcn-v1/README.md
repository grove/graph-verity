# R-GCN / CompGCN research, stage 1

This is a standalone research track. It does not change the Rust executor, graph
permissions, query compiler, or RDF evidence rules. A learned score is a ranking
hypothesis; only an original, graph-qualified RDF statement can be shown as
supporting evidence.

## Data adequacy

The existing GEMET pilot is a hash-selected 2,200-concept subset with 10,839
quads and 2,263 SKOS relation statements. The full retained EEA source has 5,573
concepts and produces a reproducible 36,441-quad export with 14,764 directed
SKOS edges across `broader`, `narrower`, and `related`. It has original English
and Norwegian labels/definitions, one importer-assigned graph, 14 weak
components, a largest component of 5,410 concepts, and four isolated concepts.
There are real source witnesses for every exported edge; no edge is generated.

This is adequate for a bounded bilingual SKOS taxonomy baseline, but not for
the full organization/service research question. It does not represent
organizations or services, and its three relation names are only two
independent patterns in practice because `broader`/`narrower` are reciprocal
forms. Results must not be generalized to heterogeneous organizational graphs.
The retained Norwegian Wikidata development graph has 40 graph-qualified
resources; the Nordic world-cities transfer graph has 390 and primarily one
`containedInPlace` relation. The 10,000-resource BM25 load corpus is synthetic
and is not a real-graph candidate. GEMET was the strongest retained source
before this experiment; the matched public baseline below uses GEMET.

| Full-source measure | Value |
|---|---:|
| Original GEMET concepts | 5,573 |
| Graph-qualified RDF resources including SKOS vocabulary | 5,588 |
| RDF quads | 36,441 |
| GNN concept nodes | 5,573 |
| Directed concept-to-concept SKOS edges | 14,764 |
| `skos:broader` / `skos:narrower` / `skos:related` | 5,685 / 5,689 / 3,390 |
| English / Norwegian text literals | 10,793 / 5,297 |
| Weak components / largest component / isolated concepts | 14 / 5,410 / 4 |
| Canonical N-Quads SHA256 | `151be979b5ac8f5db2c55cc724d44988d3aca6d2d7d44e55df108b2c61371b35` |

The source is EEA GEMET 4.2.3 under CC BY 4.0 plus the W3C SKOS 2009 RDF
schema under the W3C Software and Document License (2023). The importer unions
the two un-named inputs into `urn:graph-verity:gemet:4.2.3`; that graph name is
import provenance, not a publisher claim. Original identifiers, literals,
language tags, predicates, direction, and graph are preserved.

The retained public query set has no two-hop examples and only four
direction-family and four predicate-family evaluation cases. Its 70 relevant
evaluation references are exposed, AI-authored judgments, not independent gold. Training negatives are
sampled from unobserved graph-local triples; under the open-world RDF
assumption they are not known false facts. The source is therefore insufficient
for the full mission benchmark without a broader relationship graph and a
reviewed bilingual query set. It is still useful for this stage-one baseline
and a bounded taxonomy experiment.

## Richer organization graph candidate

The retained Wikidata development graph has only 40 resources, so I captured a
bounded CC0 slice from the read-only Wikidata Query Service. It selects 1,000
items ordered by IRI with direct `P17=Norway` and `P31=Organization`, then keeps
their original direct claims whose objects are Wikidata Q entities, plus
English, Norwegian, Bokmål, and Nynorsk labels. The importer assigns one graph
name; it does not add reverse or inferred edges. [Wikidata's licensing
policy](https://www.wikidata.org/wiki/Wikidata:Licensing) releases structured
data under CC0, and its [data-access
documentation](https://www.wikidata.org/wiki/Wikidata:Data_access) describes
RDF access.

The frozen source response has 2,157 entity nodes, 5,756 directed source edges
over 84 predicates, 1,449 directed two-hop reachable pairs, and 2,067 nodes
with English or Norwegian labels. The largest weak component contains all
2,157 nodes, largely through common country, type, and industry nodes; the top
five predicates make up 72.1% of edges. It is adequate for a bounded
organization-entity pilot, but `P137` has only one operator edge, so service
operator questions need a separate service-focused slice. The 1,000-root cap
is deterministic, not representative; 90 entity nodes have no retained en/no/
nb/nn label.

Queries and exact JSON responses are retained with their hashes, and the RDF to
GNN export is checked in at
[`wikidata-norway-org-v1`](wikidata-norway-org-v1/). Rebuild it offline with:

```sh
.venv/bin/python tools/rgcn_compgcn_wikidata.py queries
.venv/bin/python tools/rgcn_compgcn_wikidata.py export \
  --out /tmp/rgcn-wikidata-export
.venv/bin/python tools/rgcn_compgcn_wikidata.py verify \
  --export /tmp/rgcn-wikidata-export
```

The native Graph Verity index builder accepted its single-graph N-Quads export
and produced a 3,399,114-byte index in 0.92s. The BM25 and neighborhood
retrieval task is still measured only on GEMET; no Wikidata question suite has
been captured yet.

## Reproduce the data export

The exporter reuses `tools/gemet.py`, verifies its retained source hashes, and
requires its output to match the preserved full-source artifact from #50.
`export` refuses to overwrite an existing directory.

```sh
.venv/bin/python tools/rgcn_compgcn.py audit
.venv/bin/python tools/rgcn_compgcn.py export --out /tmp/rgcn-compgcn-export
.venv/bin/python tools/rgcn_compgcn.py verify --export /tmp/rgcn-compgcn-export
```

The export contains the exact full N-Quads plus a lexical retrieval view,
graph-qualified concept rows, predicate text rows, and directed adjacency
rows. Node indices are local to the export; original IRIs and graph names
remain in every row. Only original concept-to-concept SKOS edges enter the
model adjacency. No reverse edge, inferred relation, or cross-graph join is
added. All methods use original `prefLabel`/`altLabel` for concepts and
original W3C labels/comments for predicates. The lexical view omits only
concept `skos:definition` literals; it retains all source edges and labels.
That keeps native BM25 within its existing 64 MiB limit without changing the
executor's budget.

## Model-free matched baseline

The current baseline uses the same 122 public #50 questions, full GEMET graph,
candidate roles and top-k rules for native BM25 and the existing Rust
source-witnessed neighborhood retriever. It captures questions separately
from references, then verifies neighborhood evidence and every positive
reference against the full source snapshot before scoring.

```sh
cargo build --locked --offline -p verity_cli --example retrieval_session --example neighborhood_session
.venv/bin/python tools/rgcn_compgcn.py capture \
  --export /tmp/rgcn-compgcn-export \
  --questions experiments/rgcn-compgcn-v1/cases-v1/questions.json \
  --out experiments/rgcn-compgcn-v1/baseline-capture-v2 \
  --bm25-session target/debug/examples/retrieval_session \
  --neighborhood-session target/debug/examples/neighborhood_session
.venv/bin/python tools/rgcn_compgcn.py score \
  --export /tmp/rgcn-compgcn-export \
  --questions experiments/rgcn-compgcn-v1/cases-v1/questions.json \
  --references experiments/rgcn-compgcn-v1/cases-v1/references.json \
  --capture experiments/rgcn-compgcn-v1/baseline-capture-v2 \
  --out experiments/rgcn-compgcn-v1/baseline-score-v2
```

The final capture and score are retained in
[`baseline-capture-v2`](baseline-capture-v2/) and
[`baseline-score-v2`](baseline-score-v2/). On this run, the 82-case public
evaluation split has 70 relevant cases, four ambiguous cases and eight no-match
cases. BM25 achieved Recall@10 **0.571**,
MRR@10 **0.519**, and nDCG@10 **0.530**; source-witnessed neighborhood retrieval
achieved **0.614**, **0.521**, and **0.542**. The paired Recall@10 change is
**+4.3 points**. Neighborhood candidate-pool recall was **0.643**, versus
**0.600** for BM25. On evaluation, each method returned candidates on 4/8
no-match cases and all four ambiguous cases. These are exposed AI-authored references, not
independent semantic judgments; no-match means no judged target in this bounded
case set, not real-world absence. No two-hop question family is present in this
case set, so these numbers do not measure two-hop retrieval.

Both indexes contain 5,588 graph-qualified resources. The resident index JSON
is 6,282,732 bytes; build time was 2.57s for BM25 and 2.56s for neighborhood.
Warm request p50/p95 were 6.5/67.0ms for BM25 and 981/1,601ms for
neighborhood. The neighborhood timing includes packet and source-evidence
construction. The capture recorded a 102,694,912-byte largest child high-water
mark; it is not a simultaneous process-tree peak. These are one-run
measurements, not service guarantees.

EmbeddingGemma was not re-run on either full snapshot: its pinned prior results
use the 2,200-concept representation and cannot serve as a matched comparison
here. The full five-way baseline is not ready until new embedding inference is
authorized, a two-hop bilingual question/reference set is added, and BM25 plus
neighborhood retrieval are captured on the selected Wikidata graph. The #50
references also remain AI-authored and publicly exposed.

## Reuse of prior baselines

The repository already has a pinned BM25/EmbeddingGemma pipeline and measured
GEMET results in [#50](../../reports/issue-50-real-rdf-hybrid/README.md), plus
source-witnessed one-hop results in [#82](../../reports/issue-82-neighborhood/README.md)
and two-hop source-path navigation in [the Assisted Ask direction notes](../../docs/assisted-ask-direction.md).
Those runs use different snapshots, query tasks, and candidate definitions, so
they are provenance for reuse, not a matched five-way comparison. They remain
unchanged. The new ranking functions preserve graph-qualified IDs, report
candidate recall separately, and expose Recall@1/5/10, MRR@10, nDCG@10, and
no-match returns.

References generated from source edges will be marked machine-authored and
exploratory. They can establish reproducibility and source membership, not
independent semantic accuracy. The final operator run still needs a frozen
query/reference/split artifact and owner review before inference or training.

## Prepared model comparison

[`prepared-run.json`](prepared-run.json) records the proposed dataset, pinned
EmbeddingGemma revision and input format, R-GCN and CompGCN definitions,
three seeds, negative sampling, split isolation, metrics, thresholds, and
resource ceilings. CompGCN uses subtraction composition
`phi(entity, relation) = entity - relation`, updates relation embeddings each
layer, and scores directed triples. R-GCN uses a separate weight matrix per
original RDF predicate. Both use the same 128-dimensional entity/query space
and retrieval objective.

R-GCN and CompGCN encoder, scoring, negative sampling, loss, and early-stop
training code are in `tools/rgcn_compgcn_models.py`. The end-to-end feature
tensor loader, final split writer, and GNN command-line workflow are still
unfinished. PyTorch is pinned by `tools/embedding-requirements.txt`, but is not
installed in this environment; the PyTorch forward-shape test was skipped.
The subtraction operator and deterministic negative-sampling checks pass. No
new EmbeddingGemma inference, model-asset download, or GNN training has run.
The prepared file is not yet a runnable score freeze: matched Wikidata BM25 and
neighborhood runs, a bilingual one-hop/two-hop query/reference/split artifact,
service-focused coverage, and a passing M1 Pro resource preflight must be added
and bound before owner authorization.

## Model-free verification

```sh
.venv/bin/python tools/test_rgcn_compgcn.py
.venv/bin/python -m py_compile tools/rgcn_compgcn.py tools/rgcn_compgcn_models.py
```

The small fixture tests check export semantics and model I/O only. No model was
trained for this verification.
