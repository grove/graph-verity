# Authorized discovery catalog (index v1)

Issue #36 adds local, model-free discovery data for the retained Wikidata and
GeoNames-derived snapshots. It extends `Snapshot::catalog`: each named graph gets
its own documents, roles, observed text, inverted postings and statistics. The same
IRI in two graphs remains two graph-qualified records. Issue #37 adds [scoped BM25 ranking and exact matching](find-baseline.md).

## Build and inspect

From the repository root, using the pinned Rust toolchain:

```sh
mkdir -p artifacts/discovery
cargo run --locked --offline -p verity_cli -- index-build \
  data/wikidata/snapshot.nq nquads data/wikidata/policy.json \
  data/wikidata/scope.json data/wikidata/discovery.json \
  > artifacts/discovery/wikidata.json
cargo run --locked --offline -p verity_cli -- index-inspect \
  data/wikidata/snapshot.nq nquads data/wikidata/policy.json \
  data/wikidata/scope.json data/wikidata/discovery.json \
  artifacts/discovery/wikidata.json
```

For the Norwegian Schema.org graph, use `data/worldcities-transfer/snapshot.nq`,
`data/worldcities-transfer/policy.json`, `examples/compact-v2/schema-scope.json`,
and `data/worldcities-transfer/discovery.json`. A scope JSON array can select any
nonempty subset of the policy's graphs (at most eight). The CLI emits JSON to
stdout; redirect it to a fresh artifact path. Errors emit JSON to stderr with a
nonzero exit status and no partial index on stdout.

`index-inspect` validates against the current snapshot, exact requested scope,
policy, source configuration, code revision and rules **before returning any saved
documents or counts**. It rebuilds and compares the entire JSON value, including
postings and statistics, so editing data and recalculating a digest cannot bypass
validation. Whitespace/key ordering in a saved JSON file does not matter. Inspection
currently costs a rebuild; this is a bounded local artifact format, not a production
ingestion or serving system.

## Format and rules

The JSON object contains `manifest`, `graphs`, and `digest`:

- `manifest`: version 1, immutable release-byte `snapshot_id`, sorted authorized
  scope, policy/config hashes, index source revision, normalization rules, selected
  graph source/license/revision records, and hashes of each graph's discovery data.
- `graphs[graph].documents[iri]`: existing catalog roles, observed text records and
  token count. Each text retains its field, original predicate, literal datatype,
  language tag, text and a description-truncation flag. Resources without labels
  remain present without a fabricated display name. Blank nodes have no stable
  resource document; named resources connected to them still appear.
- `graphs[graph].postings[token][iri]`: term frequency. Document frequency is the
  posting's size. Document/term/token counts and empty, omitted-language and
  truncated-description counts are local to that graph.

Observed text uses this fixed predicate allowlist (Schema.org accepts both HTTP
and HTTPS):

| Field | Predicates |
| --- | --- |
| Label | `rdfs:label`, `skos:prefLabel`, `schema:name` |
| Alias | `skos:altLabel`, `schema:alternateName` |
| Identifier | `dcterms:identifier`, `schema:identifier` |
| Description | `rdfs:comment`, `dcterms:description`, `schema:description` |

English and Norwegian language families (`en`, `no`, `nb`, `nn`, including regional
subtags), and untagged literals are eligible. Other language values are omitted
and counted, without removing the resource. Languages are never translated or
guessed; the Schema.org capture's untagged names remain untagged. Distinct literals
retain their tags/datatypes; shared labels/aliases produce multiple original IRIs
in postings. Repeated identical RDF statements follow the existing store's set
semantics. Literal values use the existing Oxigraph representation, including its
numeric lexical canonicalization; string identifiers retain leading zeroes.

Tokens come from the full original IRI plus eligible text: Rust Unicode lowercase,
then maximal alphanumeric runs. There is no NFC normalization, stemming,
transliteration, stopword list, or inferred alias/local-name mapping. RDF identifiers
and stored text are never lowercased. Descriptions retain at most 512 Unicode
scalars and explicitly report truncation; empty values remain recorded and add no
tokens. Every count and posting is computed after graph authorization. RDF text,
including HTML, instructions and query syntax, remains JSON data and is never
executed or used as a command, query or model instruction.

## Reproducibility and provenance

Each operator-supplied `discovery.json` has version 1, a snapshot ID, and graph-keyed
`source`, `license`, `source_revision`, `importer_revision` strings. Missing/empty
provenance, incompatible versions, absent/empty graphs and stale snapshots fail
closed. The retained configurations pin the source manifest's SHA256 (which binds
the captured upstream revisions, source hashes and license) and the importer's
source-file SHA256. Tests verify these pins against the checked-in files. These
are trusted operator provenance declarations, not a signature or independent
license audit. No raw capture is re-imported or refreshed by indexing.

Only selected graph provenance is emitted. The config hash covers those selected
records; the policy hash covers the complete supplied policy as an opaque digest.
The index revision hashes discovery/catalog/snapshot implementation source, the
dependency lockfile and pinned toolchain. Other digests use the existing
domain-separated `snapshot_id` SHA256 function with distinct versioned domains.
The index digest hashes the complete object with `digest` set to the empty string;
graph hashes cover their graph's documents, postings and statistics. No timestamp,
local path, random identifier or runtime measurement enters the index. Repeated
builds with the same inputs/toolchain produce byte-identical pretty JSON.

The existing 16 MiB/100,000-quad snapshot limits apply. Indexing additionally uses
a conservative 64 MiB allocation budget and a 64 MiB serialized/read limit; excessive
inputs fail explicitly instead of silently dropping resources. Empty/omitted/
truncated text statistics describe data coverage, not retrieval relevance or truth.
Normal CI checks both retained datasets and synthetic graph restrictions, private
canaries, ambiguous aliases, Unicode, language tags, literal metadata, malicious
text and manifest tampering. No model, new source capture, sealed holdout, HTTP
endpoint or production ingestion is involved.
