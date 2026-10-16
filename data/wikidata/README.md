# First real RDF domain: bounded Wikidata geography

This is real, community-maintained RDF, not a synthetic municipal procurement graph. Raw inputs
are downloaded through Wikidata's documented entity RDF interface at explicit revisions, retained
byte-for-byte, and covered by SHA-256 in `manifest.json`. Selected IRIs, literal metadata and edge
directions are preserved; graph names are assigned by this importer, not attributed to Wikidata.

## Dataset selection

| Candidate | Primary evidence | Decision |
|---|---|---|
| Norwegian STIRData organizational RDF | [Data Norge record](https://data.norge.no/nb/datasets/9b8fbdd7-7294-39e2-959b-24dc8ab0df4a/virksomhetsinformasjon-i-henhold-til-stirdatas-modell) describes Brreg-derived organizational RDF, a SPARQL endpoint and CC BY 4.0 distribution. | Best domain fit, but a dated, reproducible RDF capture was not successfully validated in the authoring environment. This is not a claim that the service is universally unavailable. Retain for a later larger-domain capture. |
| Wikidata entity RDF | [Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing) declares structured entity data CC0. [Data access](https://www.wikidata.org/wiki/Wikidata:Data_access) documents Turtle, explicit revision retrieval, direct statements and full/dump variants. | Selected: small revision-addressed downloads, clear structured-data redistribution terms, actual Norwegian/English labels and numeric/date/relational facts. |

The repository's code/original fixtures are Apache-2.0; Wikidata structured RDF is **CC0-1.0**.
Attribution is retained voluntarily. No Wikipedia prose, media, model weights or images are copied.
Licensing of source documentation is not being confused with licensing of structured entity data.

## Exact boundary

Development records are the Wikidata entities for Oslo, Bergen, Trondheim, Stavanger and Norway.
A separate graph contains Stockholm and Sweden for future geographic transfer. Property metadata
for P17, P36, P31, P1082, P571 and P131 is retained in each graph. City entities must not be silently
interpreted as municipalities: those can have distinct Wikidata identifiers and boundaries.

Only those subjects, direct predicates, RDF types, labels and aliases in en/nb/nn are selected.
Property labels belong to their original property entity IRIs; `wikibase:directClaim` retains the
actual link to the corresponding direct-predicate IRI. Nothing is renamed to a fabricated ontology.
The catalog can resolve observed exact labels; model context must respect these RDF distinctions.

The derived graph omits qualifiers and references from query patterns, but raw dump-flavor RDF
retains them for source inspection. Population and inception values are **statements in this capture**,
not guarantees of current population, an agreed historical founding date, or latest observations.
Multiple direct values are retained. Query filters are existential over those selected statements.
Counts cover the selected records only, not all Norwegian cities, municipalities or Wikidata.
Missing facts never imply false real-world claims. There is no RDFS/OWL entailment.

The scale is intentionally tiny, suitable for compiler/oracle checks and a first parser smoke
experiment, **not** evidence for the planned 10,000–100,000-resource serving scale or broad domain
coverage. Cross-country transfer uses the same ontology; it is not a second-ontology benchmark.
Where available, an earlier Oslo revision is retained as a temporal regression asset. Other entities
remain unchanged, so it is not a coherent all-entity historical snapshot. A revision may change only
omitted metadata; the manifest states whether selected graph facts actually changed.

## Reproduction

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/dataset.py verify
.venv/bin/python tools/dataset.py rebuild /tmp/verity-snapshot.nq
cmp data/wikidata/snapshot.nq /tmp/verity-snapshot.nq
cargo run --locked -p verity_cli -- inspect data/wikidata/snapshot.nq nquads
```

Normal verification uses checked-in bytes and never contacts Wikidata. `capture` is an explicit
maintainer operation for an absent capture, not an automatic refresh command. Existing captures
are verified and left unchanged. Changes require a new reviewed release, source hashes, graph hash,
benchmark answers and split/review decision. Endpoint availability is therefore not a CI dependency.
The graph snapshot ID identifies exact derived RDF bytes. The manifest separately identifies each
raw source revision and extraction configuration; different source revisions can yield identical
selected graph bytes.
