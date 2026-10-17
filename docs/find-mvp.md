# Scoped Find and graph evidence

The CLI MVP uses the authorized #36 discovery index, #37 BM25 ranking, and the
[#38 decision](../reports/issue-38-embeddinggemma/README.md): reject embeddings
alone and defer fusion for human review and a no-match policy. No model is needed.

**Pilot scope:** local exploration of the retained Wikidata/GeoNames snapshots,
including [explicit predicate-label retrieval with mapping provenance](find-quality.md).
Predicates without graph-local mapping evidence remain limited to original-IRI
retrieval. Conservative outcome states require human inspection and selection. This is
an engineering MVP, with no stakeholder quality or real-domain scale readiness
claim. The full frozen retrieval evaluation retains the original predicate family;
the revised product scope does not remove cases or lower the original targets.
See the [original release report](../reports/issue-39-find-mvp/README.md) and the
[fresh #46 comparison](../reports/issue-46-find-quality/README.md).

## Fresh local offline walkthrough

After installing the pinned build dependencies, everything below runs locally
without a network or model. Each CLI invocation starts a fresh process and reloads
the immutable snapshot. From the repository root:

```sh
cargo build --release --locked --offline -p verity_cli
mkdir -p artifacts/find-session
target/release/verity find data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json \
  data/wikidata/discovery.json examples/find/norway-no.json \
  > artifacts/find-session/norwegian.json
target/release/verity find data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json \
  data/wikidata/discovery.json examples/find/norway-en.json \
  > artifacts/find-session/english.json
target/release/verity entity data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json \
  data/wikidata/discovery.json examples/find/norway-entity.json \
  > artifacts/find-session/norway.json
target/release/verity entity data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json \
  data/wikidata/discovery.json examples/find/oslo-incoming.json \
  > artifacts/find-session/oslo.json
cargo test --locked --offline -p verity_cli --test navigation
```

1. `Norge` and `Norway` both rank original IRI `http://www.wikidata.org/entity/Q20`
   first. Inspect the observed Norwegian/English labels, score and `explanation`.
2. Open Q20 with `entity`, direction `outgoing`. In `evidence`, find predicate
   `http://www.wikidata.org/prop/direct/P36`, whose object is Q585 (Oslo).
3. Open that object with `entity`, direction `incoming`. The same Q20 → P36 → Q585
   statement appears with its original subject, predicate, object and source graph.
   Its enclosing `snapshot_id` matches the Find response and both entity pages;
   `sources[source_graph.value]` supplies source/license/importer revisions.
4. For larger neighborhoods, follow `next_offset` in another request, preserving
   snapshot, scope, IRI, direction and limit. Change direction to inspect the other
   side, or explicitly choose another linked IRI for the next hop. No automatic
   recursive traversal occurs.

The CLI regression checks this path and source provenance in fresh processes.
The entity examples use 50-edge pages so the capital edge is visible. The source
triples are observations in a retained snapshot; they are not current-world facts
or answers inferred from the words “Norway” and “capital”.

## Request and result boundaries

`find` keeps the [BM25 request contract](find-baseline.md#ranking-contract).
Each hit includes exact IRI/observed-field match reasons and the normalized query
tokens found in its graph-qualified IRI/text postings. The observed document
retains labels, aliases, literal language/datatype and description truncation.
The score measures lexical relevance, not confidence or interpretation accuracy.
`limit` and `truncated` describe candidate clipping. Even `truncated: false` means
only that all lexical matches were returned; top-k is never an exhaustive semantic
answer. [The outcome policy](find-quality.md#fixed-representation-and-policy-before-evaluation)
flags graph-qualified exact collisions (`ambiguous_exact`), multiple partial
candidates (`ambiguous_candidates`) and a lone partial match (`low_confidence`)
before clipping. `no_match` means no lexical candidates, never real-world absence.

`entity RDF FORMAT POLICY SCOPE CONFIG REQUEST_JSON [INDEX]` accepts exactly:

```json
{
  "snapshot_id": "copy the Find response snapshot_id",
  "scope": ["authorized named graph IRI"],
  "iri": "original resource IRI chosen by the user",
  "direction": "outgoing",
  "offset": 0,
  "limit": 10
}
```

Use `incoming` for statements whose object is this IRI; `outgoing` selects
statements whose subject is this IRI. Literal properties are included. There is
no inferred inverse relationship, generated question plan or public raw-SPARQL
input. Direction `predicate` pages statements using the chosen IRI as predicate;
explicit discovery mapping associations retain both source witnesses. Unknown fields, invalid IRIs, incompatible snapshot/index
or policy, unauthorized scope and excessive bounds fail before results are printed.

Pages contain graph-qualified documents for the chosen IRI and directed supporting
`evidence` statements, using the existing `RdfTerm`/`Statement` representation.
Datatypes, languages, original endpoints, graph and immutable snapshot identity
are preserved. Source records and graph hashes are restricted to the request scope.
Missing labels stay missing unless an explicit graph-local `directClaim` witness
permits a retrieval association; its `via` records the original label subject.
Labels are never borrowed across graphs. RDF text,
including markup and instructions, remains untrusted JSON data.

Page order is graph, subject, predicate, then object kind, lexical form, language
and datatype (with RDF term order as a final tie-break). Equal numeric values with
different datatypes receive stable page positions. Oxigraph may canonicalize
numeric spellings on import; evidence is RDF-store output, not byte-exact source
extraction. The snapshot ID binds the original release bytes.
`next_offset` is non-null only when a one-edge lookahead finds more. `truncated`
means more edges in this direction; it does not describe the opposite direction.
`no_relationships_on_page` distinguishes a known resource with an empty direction
or an offset beyond its final page. `no_match` returns an empty document/evidence
set and null IRI, disclosing nothing about identifiers outside the scope. It can
also mean an unknown IRI. Predicate-only documents can have no incident edges.

Limits are 1..50 edges within both policy row/evidence caps, offset 0..100000,
policy execution timeout and an 8 MiB entity output cap. Timeout/output-limit
failures return no partial stdout. Existing 16 MiB/100000-quad ingestion and
64 MiB index allocation limits still apply. Scope checks precede statistics,
returned text, relationship counts and evidence; there is no global neighborhood
count. Anonymous blank nodes may appear in evidence but cannot be opened as IRI
entities. Their identifiers are process/snapshot-local, so page ordering involving
anonymous nodes is not a cross-import identity guarantee.

Both `find` and `entity` accept an optional persisted `INDEX` generated by
`index-build` with the same operator scope. It is rebuilt and fully compared
before use, reusing `load_discovery`; it is an integrity check, not a cache.
Omitting it builds fresh from the supplied RDF/config. Request scope can be a
subset of the operator scope. Policy remains operator input, not end-user input;
this local CLI is not a multi-user authorization service. Administrative
`inspect`/`smoke` commands are not scoped end-user views.

Search ranks candidates. Navigation executes a fixed bounded read-only template.
`evidence_verification: verified_against_snapshot` establishes the returned triples
in that snapshot. `interpretation_correctness: not_assessed` and
`real_world_truth: not_established` remain separate. Absent triples are unknown
under the open-world policy. The separate [local browser pilot](local-find-ui.md) now wraps these contracts. No autonomous Ask, remote SERVICE, write endpoint,
production ingestion, SHACL runtime or GNN is added.
