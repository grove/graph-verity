# Predicate discovery and conservative Find outcomes

Issue #46 extends the lexical Find representation using only explicit evidence in
an authorized named graph. BM25 remains the product implementation. No RDF is
changed, no Ask is added, and model-backed retrieval remains disabled.

## Fixed representation and policy, before evaluation

The representation and outcome rules were chosen from the RDF structure and the
public development failure, before running the revised evaluation formulations.
No stemming, synonyms, stopwords, query rewriting, scoring constants or cutoffs
were tuned. Frozen #37–#39 inputs, reports and denominators remain unchanged.

For a named source resource S, the builder requires both statements in graph G:

```text
S <http://wikiba.se/ontology#directClaim> P G .
S <recognized label or alias predicate> literal G .
```

P must also actually occur in predicate position in G. The discovery document for
P gains a retrieval association to that literal, with `via.source_iri: S` and
`via.predicate: http://wikiba.se/ontology#directClaim`. Its enclosing hit supplies
P and G; `snapshot_id`, `graph_hashes` and `sources[G]` bind the snapshot, retrieval
representation, original dataset source/revision/license and importer revision.
The text's `predicate` and `value` preserve the second statement's predicate,
lexical value, RDF language and datatype. `via` describes the first statement;
it does **not** assert that P itself has the label. Ordinary texts omit `via`.

Only labels and aliases in en/no/nb/nn language families or untagged literals
qualify, using the existing field vocabulary. Descriptions and identifiers are
not transferred. Original source documents remain distinct. Links do not chain;
blank nodes, literal targets and targets not observed as predicates do not qualify.
Multiple explicit sources are retained separately. No inference from `/P36`,
property type, an external dictionary, another graph or a model is permitted.
Missing links/labels retain unlabeled predicate retrieval. The source graph's
assertion is retrieval evidence, not an independently verified semantic mapping.
RDF strings, including instruction-like labels, remain untrusted JSON data.

Graph authorization precedes construction and both witnesses; role filtering
precedes BM25 statistics/ranking. Existing index allocation/output budgets apply
to associations too. Existing persisted indexes must be rebuilt: source revision
and full rebuild comparison reject the old representation.

Find keeps the BM25 formula, exact-match tier, original IRIs and ties (IRI, graph).
The following `find-outcomes-v1` rules use **all graph-qualified candidates before
limit clipping**, with no score/margin threshold and no candidate suppression:

| Condition, in order | `status` | Meaning |
| --- | --- | --- |
| More than one exact candidate | `ambiguous_exact` | Choose an IRI and source graph; duplicate IDs across graphs also need selection. |
| One exact candidate | `ranked` | An exact lexical candidate, still not an answer. |
| No candidates | `no_match` | No retrieved lexical match in this scope; real-world absence is unknown. |
| Multiple non-exact candidates | `ambiguous_candidates` | Conservatively ask the user to inspect/select; relevance is uncalibrated. |
| One non-exact candidate | `low_confidence` | A lexical suggestion requiring inspection; not calibrated confidence. |

`exact_ids` retains its distinct-IRI meaning; `exact_candidates` counts distinct
(IRI, graph) exact hits. The complete rule is returned as `outcome_policy`.
`matches`, exact counts and ambiguity are computed before `limit`; a one-hit page
can still be ambiguous. A shared token can return irrelevant candidates even for
an unknown IRI. No heuristic claims to detect every ambiguity, semantic absence,
or an out-of-domain question. Every candidate requires deliberate human selection.

Representative output interpretation (Norwegian / English):

- `Hovedstad` / `Capital`, role `predicate`: exact candidate P36; inspect its two
  source witnesses and usage triples before selecting it.
- `Felles alias` / `Common name` shared by two IDs: `ambiguous_exact` —
  «Velg ressurs og kildegraf» / “Choose a resource and source graph”.
- Multiple partial matches: `ambiguous_candidates` — «Flere mulige treff; se
  kildene» / “Several possible matches; inspect the sources”.
- One partial match: `low_confidence` — «Usikkert teksttreff; kontroller kilden» /
  “Uncertain text match; check the source”.
- An unmatched token: `no_match` — «Ingen hentede treff i dette omfanget;
  fravær er ukjent» / “No retrieved matches in this scope; absence is unknown”.

These phrases explain JSON states; the CLI does not translate or interpret queries.

## Offline CLI walkthrough

```sh
cargo build --release --locked --offline -p verity_cli
mkdir -p artifacts/find-quality
target/release/verity index-build data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json data/wikidata/discovery.json \
  > artifacts/find-quality/index.json
target/release/verity index-inspect data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json data/wikidata/discovery.json \
  artifacts/find-quality/index.json
for request in predicate-no predicate-en; do
  target/release/verity find data/wikidata/snapshot.nq nquads \
    data/wikidata/policy.json data/wikidata/scope.json data/wikidata/discovery.json \
    examples/find/$request.json artifacts/find-quality/index.json
done
target/release/verity entity data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json data/wikidata/discovery.json \
  examples/find/predicate-triples.json artifacts/find-quality/index.json
target/release/verity entity data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json data/wikidata/scope.json data/wikidata/discovery.json \
  examples/find/property-source.json artifacts/find-quality/index.json
```

The searches resolve to original `http://www.wikidata.org/prop/direct/P36` in
`urn:graph-verity:wikidata:development`, via the separate property entity
`http://www.wikidata.org/entity/P36`. `entity` direction `predicate` pages actual
`?subject P36 ?object` source statements, including Q20 → P36 → Q585. This is a
fixed validated read-only template with the existing scope, snapshot, timeout,
row/evidence, offset and output caps. Incoming/outgoing retain their meaning.
The property-source page shows the original mapping and multilingual labels;
no new RDF label statement is invented for P36. Match snapshot IDs on every page.
The CLI regression runs the walkthrough, including persisted-index validation.

## Fusion decision and remaining usability limits

**Keep BM25; defer fusion integration.** The immutable [#38 evidence](../reports/issue-38-embeddinggemma/README.md)
rejects dense replacement and retains fixed equal-weight RRF (constant 60, top 50,
IRI/graph ties) as a candidate. Its evaluation fusion Recall@10 1.000 and MRR@10
.890 coexist with candidates on 10/10 no-match queries; predicate MRR@10 was .340.
Those results remain historical, AI-judged and unvalidated independently.

The separately opt-in #46 development trial reuses the exact upstream model,
CPU runtime/parity helpers and fixed fusion from #38 against the revised index.
It freezes assets, runtime, binary, exported authorized documents, requests and
source hashes before inference. It reads development formulations only; it runs
no evaluation/scale/holdout inference and provides no rollout-performance claim.
Dense/fusion have no exact-match override. Their nonempty candidate lists receive
conservative `ambiguous_candidates` or `low_confidence` states without filtering
false candidates. No score cutoff is invented to make no-match metrics pass.

```sh
# Explicit local opt-in; requires the previously acquired pinned #38 assets/runtime.
/path/to/embedding-runtime/bin/python tools/find_quality.py fusion-dev \
  --binary target/release/verity --model-dir /path/to/pinned/assets \
  --out artifacts/find-quality-fusion-dev
# Model-free fresh lexical report, unchanged frozen 80+80 formulations:
.venv/bin/python tools/retrieval.py run --binary target/release/verity \
  --out artifacts/find-quality-run --cold 30 --warm 200 \
  --compiler 'record rustc -Vv' --cpu-description 'record hardware and scheduler'
.venv/bin/python tools/retrieval.py verify-report --out artifacts/find-quality-run
```

Ordinary CI never installs the model runtime, downloads weights or invokes the
trial. Independent relevance review and stakeholder usability evidence are still
unavailable, so no opt-in product path is authorized by this engineering trial.
Any future rollout needs a separately documented decision covering exact-match
priority, no-match false candidates, conservative selection states and deployment
performance. See [fresh measurements and comparison](../reports/issue-46-find-quality/README.md).

Optional confirmed Ask #40 still requires independently recorded user need and
an explicit product go decision. Better predicate recall and conservative JSON
states do not establish safe question interpretation, human usability or factual
truth. Scope selection, mapping coverage, language restrictions, manual candidate
inspection and real-domain scale remain limits; no unattended Ask is implemented.

The separately preregistered [real RDF hybrid retrieval study #50](../reports/issue-50-real-rdf-hybrid/README.md)
compares the original #46 representation with a new `skos-definitions-v1` text
variant. Discovery now recognizes original `skos:definition` literals as bounded
descriptions with their original predicate/language/datatype witnesses. This
changes the index rules identity; old persisted indexes require rebuilding.
BM25 remains the shipping Find backend. Neither historical reports nor fixtures
are retuned. See the [new protocol](../benchmarks/hybrid/README.md).
