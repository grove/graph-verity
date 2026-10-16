# Real second-ontology transfer **development** material

## Data, provenance and license

This separately pinned 1,508-quad RDF snapshot is a **derived representation** of 328 real Nordic city records and 62 administrative-region names from the publicly licensed [datasets/world-cities](https://github.com/datasets/world-cities) CSV, itself sourced from GeoNames. The repository revision is `73c9f54ab9f305168c76d0802db151e30a157b28`, with source CSV blob SHA `f5a9bdb7cd04dbf0a86695c67d2039c9ab904e18`. See `manifest.json` for extraction hashes, source URL, exact graph snapshot digest and license attribution.

**Credit:** GeoNames (https://www.geonames.org/) and [datasets/world-cities](https://github.com/datasets/world-cities). The dataset is redistributed with modifications under **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Changes: restrict to NO, SE, DK, FI and IS, extract 328 CSV city records, mint synthetic administrative/country identifiers, and map source names and relationships into Schema.org vocabulary. Source claims are not verified contemporary facts.

The original GeoNames geoname IDs are preserved in city subject URIs `https://sws.geonames.org/{id}/`. The **Schema.org relations and classification are minted by this importer**, not directly asserted by upstream as RDF. In particular, `schema:City` is a mapping of the world-cities CSV entries (which include cities and seats of government), not independent verification of formal administrative municipality status. Country/region URIs are importer-assigned; administrative region strings are the CSV subcountry names, not authority-resolved official boundary IDs. This is a source/ontology transfer test, not a full authoritative geography database.

There is no blanket entailment. A missing city or relation is unknown beyond the selected snapshot. Source data provides **no population**, time-qualified figures, ownership relationships, company identifiers, or SHACL. Numeric tests concern geoname IDs alone, not numeric population. Labels use the original CSV spellings (largely English). `schema:containedInPlace` edges are directed city → region → country.

## Scope

Five independent source-graphs are importer-assigned:

```text
urn:graph-verity:worldcities:transfer:NO
urn:graph-verity:worldcities:transfer:SE
urn:graph-verity:worldcities:transfer:DK
urn:graph-verity:worldcities:transfer:FI
urn:graph-verity:worldcities:transfer:IS
```

The 328 cities are distributed 42 NO, 111 SE, 67 DK, 102 FI, 6 IS. The named graphs contain only their own cities, region nodes and country nodes; no cross-graph inference is enabled. The source is distinct from Wikidata and uses Schema.org classes/properties, providing a legitimate **different-ontology engineering transfer fixture**; that does not prove transfer performance of a model.

## Reproduce, no network needed after checkout

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/worldcities_transfer.py verify
.venv/bin/python tools/worldcities_transfer.py rebuild /tmp/worldcities-transfer.nq
cmp /tmp/worldcities-transfer.nq data/worldcities-transfer/snapshot.nq
.venv/bin/python tools/verify_worldcities_benchmark.py verify
cargo run --locked -p verity_cli -- inspect data/worldcities-transfer/snapshot.nq nquads
cargo run --locked -p verity_cli -- evaluate \
  data/worldcities-transfer/snapshot.nq nquads \
  data/worldcities-transfer/policy.json benchmarks/worldcities-transfer.json \
  transfer_dev artifacts/transfer-oracle
```

**40 machine-authored transfer-development questions** are in `benchmarks/worldcities-transfer.json`: 35 independently formulated executable query probes across direct/inverse/two-hop joins, type counts, grouping/HAVING, typed numeric identifier comparisons, identity lookups and strict named scopes; 5 proposed clarification/unsupported cases. All are **publicly exposed development cases**. They are **not** expert-reviewed, model-generated, or a locked holdout. Their answers are frozen from the retained source and independently checked by RDFLib during normal CI. The Rust compiler then cross-checks independently authored reference SPARQL and these expected results.

The `transfer_dev` split is deliberately separate from both `locked_holdout` and `transfer_test`. **Do not relabel these exposed cases as private final tests**. Future decision-quality transfer tests need independent human gold review, controlled access, lineage separation and an actual model experiment. User/project-owner approval of a previous AI audit does not magically certify these new cases or create a private holdout.
