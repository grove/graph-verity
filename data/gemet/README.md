# Real GEMET 4.2.3 / SKOS retrieval pilot

Attribution: **European Environment Agency (EEA), GEMET — GEneral Multilingual
Environmental Thesaurus, version 4.2.3**, release timestamp
2021-12-06T13:37:25.364764+00:00. The original RDF explicitly declares
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the retained official
[versioned download page](https://www.eionet.europa.eu/gemet/en/exports/rdf/4.2.3)
independently links that license. `source/gemet-4.2.3.rdf.gz` is the exact official
[version-addressed export](https://www.eionet.europa.eu/gemet/4.2.3/gemet.rdf.gz).
This bounded extraction is modified selection/serialization, not EEA endorsement.

Attribution: **W3C, Alistair Miles, Sean Bechhofer and the Semantic Web Deployment
Working Group, SKOS Reference, 18 August 2009**. Original schema statements from
[the dated RDF schema](https://www.w3.org/2009/08/skos-reference/skos.rdf) provide
predicate/class labels, definitions and comments. The retained
[W3C Software and Document License (2023)](https://www.w3.org/copyright/software-license-2023/)
is included as `source/w3c-license.html`. No invented predicate labels, ontology
inference, translated source facts, or copied Wikidata labels are used.

`manifest.json` pins every raw/canonical snapshot, source page, importer and
policy/config/scope file by SHA256. Sources are retained, so offline reproduction
does not depend on an upstream URL remaining unchanged. Refresh is manual and
outside CI. Verify remote downloads against the pinned hashes before use.

`tools/gemet.py` selects 2200 real `skos:Concept` subjects from 5573, ordered by
SHA256 of the original IRI, with IRI tie-breaking. It retains original `rdf:type`,
`skos:prefLabel`, `skos:altLabel` and `skos:definition` statements in English,
Norwegian or untagged, and original broader/narrower/related edges whose two
endpoints are selected. Used SKOS terms get only original W3C schema statements
for labels/comments/definitions/types. There are 2215 graph-qualified resources
including vocabulary, 10839 quads, 2053 definition literals and 2263 relation
quads. No query-derived or fabricated text enters the corpus.

Both source files are un-named RDF graphs. The importer explicitly unions these
source triples into the named release graph `urn:graph-verity:gemet:4.2.3`;
that graph name is importer provenance, not an original publisher assertion.
No source named graph is flattened or scope enlarged. Source literal languages,
datatypes, original IRIs and directed relationship statements are preserved.
Unused publisher creation/modification dates include ill-typed empty dateTimes;
they are excluded before RDF parsing rather than repaired. Literal normalization
is disabled. Canonical N-Quads use single-line escaped literals and sorted
original terms. No blank nodes are selected. Definitions are truncated only in
the discovery representation (512 Unicode scalars / 256 model tokens), never in
the retained source snapshot. Norwegian definitions are not fabricated where
GEMET publishes only Norwegian labels and English definitions.

The complete 5573-concept extraction was also attempted, before any scoring:
it reaches the existing **64MiB conservative discovery allocation budget** and
is rejected with empty stdout. The failed input identities and error are retained
in the issue 50 report. No import/allocation limit was relaxed. Requesting 10000
concepts is rejected because this release has only 5573; no synthetic padding is
used. A path toward 10000 requires first reducing measured index allocations or
separately authorized per-scope indexes, then adding another licensed source
with distinct real subjects and a new freeze. Repeating this graph under invented
graph names would not constitute real 10000-resource evidence.

```sh
.venv/bin/python tools/gemet.py verify
.venv/bin/python tools/gemet.py build --concepts 2200 --out artifacts/gemet-rebuilt
# Compare rebuilt snapshot.nq, policy.json, scope.json, discovery.json and stats.json
# byte-for-byte with data/gemet/.
```
