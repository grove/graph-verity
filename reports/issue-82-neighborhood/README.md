# #82: measured neighborhood coverage on exposed regressions

**Predicate coverage at top-20: v1 6/18; v2 18/18.** Both required IDs are
present in 18/18 supported cases with v2. This is model-free candidate coverage
on the same **30 already exposed evaluation questions**, comprising 18 supported,
six clarification and six unsupported questions. It is not an untouched holdout,
model interpretation accuracy, human validation or permission to execute Ask.
No model, hybrid retriever or sealed Ask holdout was used.

The [preregistration](../../benchmarks/question-vocabulary-v2-neighborhood/registration.json)
seals the new retrieval code, protocol and source hashes before capture/scoring.
The [protocol](../../benchmarks/question-vocabulary-v2-neighborhood/protocol.json)
records examined queries and fixes ranking/bounds. The only new real-source
implementation controls were “Which resources connect with acid rain?” and
“What links into acid rain?” on the public GEMET development source, plus
synthetic authorization/exact-match/DoS controls. All 30 evaluation questions and
#74/#76 failure families were already exposed and read before implementation.
There was no rank-dependent heuristic revision or later-new study. During scorer
development the public #76 audit field name and cross-platform resource parser
were corrected; captured packet bytes and registered retrieval code did not change.

## Coverage and source direction

[coverage.json](coverage.json) retains every case, exact original IRI and named
graph, required role, rank, graph coverage, source evidence, ambiguity, duplicate
counts, clipping, misses, negative returns and packet digest at k=1/5/10/20.
All 30 regenerated v1 packets are **byte-for-byte identical** to #74's saved
packets, including IDs, evidence, scores and source metadata. Historical
#72–#76 files and v1 implementation/protocol remain unchanged.

| k | v1 start /18 | v2 start /18 | v1 predicate /18 | v2 predicate /18 | v1 both /18 | v2 both /18 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 16 | 4 | 6 | 4 | 6 |
| 5 | 18 | 18 | 5 | 16 | 5 | 16 |
| 10 | 18 | 18 | 6 | 18 | 6 | 18 |
| 20 | 18 | 18 | 6 | 18 | 6 | 18 |

No required predicate remains missing at k=10 or k=20. Two remain below k=5:
P571 (eva-03, rank 6) and P856 (eva-04, rank 7). All lower-k misses remain in the
JSON. The baseline's original direction-reference denominator remains **zero**.
A separately versioned `source-audit-v2` direction supplement uses #76's public
reference plans, verifies their exact graph/start/predicate against #74 references,
and cites original RDF triples after all packets are sealed. It finds 16 supported
paths with positive source witnesses: v1 covers 3/4/5/5 and v2 5/14/16/16 at the
four k values. Eva-13 and eva-18 are empty reference paths, excluded from this
positive-witness denominator. No inverse fact or direction gold was invented for
an empty path; membership in a packet cannot establish that a path has an answer.

## All twelve original predicate misses

Every row has its exact source-qualified identity and original adjacency triples
in `missing_predicate_audit`. Wikidata abbreviations below mean
`http://www.wikidata.org/prop/direct/`; Schema.org means `https://schema.org/`;
SKOS means `http://www.w3.org/2004/02/skos/core#`.

| Case | Original required predicate | v2 rank | Original reference direction |
|---|---|---:|---|
| eva-02 | Wikidata P131 | 3 | outgoing |
| eva-03 | Wikidata P571 | 6 | outgoing |
| eva-04 | Wikidata P856 | 7 | outgoing |
| eva-05 | Wikidata P1448 | 4 | outgoing |
| eva-07 | Wikidata P131 | 1 | incoming |
| eva-09 | Schema.org name | 4 | outgoing |
| eva-11 | Schema.org containedInPlace | 2 | outgoing |
| eva-12 | Schema.org containedInPlace | 2 | incoming |
| eva-13 | Wikidata P131 | 3 | incoming; no original answer triple |
| eva-14 | SKOS prefLabel | 5 | outgoing |
| eva-15 | SKOS definition | 5 | outgoing |
| eva-17 | SKOS related | 3 | outgoing |

For **each** of these twelve cases, the authorized predicate has **no matching
whole-question lexical token** in its graph-local discovery document. This is
not merely a score falling below top-20. Its predicate role exists, its required
start has the entity role, and its declared language is supported. Every missed
predicate occurs in real original adjacency near at least one retrieved seed;
none needs a wrong-role entity, cross-graph label or inferred inverse statement.
All twelve v1 cases also have clipped three-statement seed navigation pages;
those pages cannot enumerate all authorized predicates. V2 separately enumerates
up to 200 statements per direction. For eva-13 the original P131 witness is
outgoing from the start, while the reference asks an empty incoming path. V2
retrieves the predicate without asserting that incoming path exists.

## False suggestions, ambiguity, exacts and clipping

V2 returns **90 predicate suggestions across 10/12 clarification/unsupported
questions**, compared with v1's zero. Eva-21 and eva-23 return no vocabulary.
Eva-24's missing named institution still retrieves other resources; eva-29's
private-scope request still retrieves public vocabulary; eva-30's write text
matches inert malicious RDF labels. Those are false suggestions if treated as
interpretations. No candidate establishes answerability, satisfies an omitted
constant, authorizes a private graph or permits a write. Every case's role counts
and returned identities remain in the capture. No question is excluded.

On supported cases, non-required predicate suggestions increase from 20 to 145.
They are source-true distractors, not false RDF statements. Duplicate role/graph/IRI
identities are zero in both methods. Cross-role identity repeats remain seven;
resources legitimately observed in multiple roles retain distinct table IDs.
Packets requiring disambiguation increase from 19/30 to 27/30. All bounded
ambiguous entities are surfaced; no first hit is automatically selected.

The 30 full questions contain no exact whole-query hits, so an exact-first rate
on them has denominator zero. Separate Rust controls verify exact IRI, label,
alias and identifier first-hit preservation, including alias collisions and
separate graphs. No partial neighbor displaces an exact authorized first hit.

The aggregate clipped flag appears in 27/30 v1 versus 9/30 v2 packets. V2 clipped
cases are eva-02, 08–12, 25, 27 and 28. Remaining clipping is bounded text or
predicate usage evidence, not evidence of a missing required candidate. The
packet byte limit is 1 MiB in both methods; largest packets are 41,527 bytes for
v1 and 45,535 for v2. Rust tests separately force tail clipping, the 200-edge
adjacency ceiling and oversized evidence failures. A missing witness is unknown.

## Latency, memory and source provenance

[capture/resources.json](capture/resources.json) records one resident Rust process
per method and one process-cold CLI run per question, in frozen order, with no
warmup/retry exclusion. Each method's packets are identical between lifecycles.
The same 25,063-byte authenticated discovery index is retained per resident
session; no neighborhood index or model is allocated. These are debug Rust
binaries on Apple M1 Pro, 32 GiB RAM, 10 logical CPUs, macOS 27.0.1 (26A434),
arm64. Cache/power/thermal state was uncontrolled; host contention and load samples
are disclosed in the raw resource record. Measurements are exploratory single
passes, not a production SLA or a worst-case allocator bound.

| Measurement | v1 p50 / p95 | v2 p50 / p95 |
|---|---:|---:|
| Resident retrieval + JSON value construction | 7.16 / 13.58 ms | 18.05 / 28.64 ms |
| Resident NDJSON round trip | 7.64 / 14.38 ms | 18.84 / 29.97 ms |
| Process-cold CLI including import/index/output | 25.01 / 31.40 ms | 35.48 / 47.85 ms |
| Sampled resident RSS after responses | 10,752 / 10,784 KiB | 11,168 / 11,168 KiB |

Maximum sampled resident RSS is 10,784 KiB for v1 and 11,184 KiB for v2. Cold
maximum RSS is 11,698,176 and 11,943,936 bytes respectively, measured by
`/usr/bin/time -l`; all 60 raw time receipts are retained beside packets. Resident
RSS samples are **not** peaks, concurrent process-tree sums or allocator traces.
Cold means a fresh process, not a flushed filesystem cache. Index build is
10.41/10.32 ms in the two resident sessions. Binary sizes/hashes, input byte sizes,
index manifests, PIDs, load-before/after and all per-case resource samples are
retained. The initial sandbox attempt failed at OS statistics collection, before
any scores; host execution supplied the measurements without changing retrieval.

Each packet binds original snapshot bytes, graph hashes, policy fingerprint,
source/importer revisions and exact attribution from the unchanged #72 operator
`discovery.json`. `source_evidence` independently checks every emitted triple,
text language/datatype and directClaim association against original retained
N-Quads using RDFLib. Required reference membership is independently checked too.
The input source is the public Wikidata, GeoNames-derived Schema.org and GEMET
#72 evaluation snapshot; existing overlay/malicious-text fixtures remain explicitly
public test data. No extra source or gold enters the retrieval request.

## Validation and reproduction

The full required model-free pipeline **passed** on retrieval-code commit
`d8eebfd`, including required browser checks, Rust/Python, format, Clippy,
reference queries, frozen replays and final clean tree. The complete
[verification receipt](verification.json) retains commands, exit statuses and
model/holdout exclusions. Subsequent changes only add this receipt and its report
link/checksums; retrieval code, protocol, captures and scores remain unchanged.

Historical source-fingerprint verifiers for #72/#74/#76 run against exact Git
export `bba81fc` with original sources, strict hashes and original reports.
The harness compares the current frozen evidence directories with that export
before replay. Current-binary #72/#74 schema/contract/scorer tests still run;
only the two checks that require historical source hashes and the #76 historical
recalculation move to the export. The existing #73/pilot export checks remain.
No old verifier, freeze or report is weakened or resealed. This was required
because adding the separate CLI/module necessarily changes current Rust sources.


The new Rust core/CLI tests cover real development-source forward/reverse
nonlexical recovery, exact ordering, graph-private canaries, graph-local roles,
snapshot/policy/index/source drift, stale IDs, whole-packet replay/tampering,
malicious text, no-match, ambiguity, explicit numeric bridge resolution,
packet-bound saved drafts, clipping and DoS limits. Python tests independently
replay/source-audit all 30 cases, retain all twelve misses and negative cases,
reject forged RDF/text/mapping provenance, test registration drift and demonstrate
that capture succeeds with a deliberately unparsable reference file.

```sh
cargo build --locked --offline -p verity_cli --bins --example neighborhood_session
.venv/bin/python tools/neighborhood_vocabulary.py verify
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

See the [API/CLI contract](../../docs/question-vocabulary-packet-v2-neighborhood.md)
for fresh capture commands and trust-boundary details. Source/protocol registration,
raw packets, source-audited scoring and outer checksums are separate receipts.
All gold remains AI-authored with **zero independent human reviews**. Larger
graphs, unexamined languages/intents and production workloads are unmeasured.
Further inference needs the separately authorized #78 trial; this result does
not promote hybrid retrieval, product integration or unattended Ask.
