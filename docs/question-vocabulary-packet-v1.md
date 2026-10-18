# Question vocabulary packet v1

Issue [#73](https://github.com/grove/graph-verity/issues/73) adds a model-free,
question-only discovery boundary for the future one-hop draft expander (#72).
This is a research packet format, not an answer generator or an execution path.
Shipping Find remains unchanged BM25; no dense retrieval, model inference, UI
integration, Ask execution or automatic candidate selection is introduced.

## Operator inputs and frozen policy

`Snapshot::vocabulary_packet(index, request, policy, budget)` accepts only
server/operator-owned inputs. `VocabularyRequest` contains the unchanged original
question (1–4096 UTF-8 bytes), its declared `en/no/nb/nn` language, snapshot ID,
index revision and explicit graph subset. The immutable discovery index must
match the snapshot and policy. Provenance is supplied by the existing operator
`DiscoveryConfig`. A model may never provide or replace any of these inputs.

The [baseline protocol](../benchmarks/question-vocabulary-v1/protocol.json)
freezes the whole original question as the **identical Find query for each of
entity, predicate and class**, top 20 per role, 1 MiB compact serialized packet,
eight texts per candidate, 2048 bytes per text, three source statements per
navigation page, and 4096 bytes of source metadata per graph. There is no
question decomposition, stemming, translation, oracle ID injection or retry.
The existing language universe includes English/Norwegian families and untagged
text; the declared question language does not change rankings or text order.

Find filters graph and role before computing BM25 statistics. Exact whole-IRI,
label, alias and identifier matches sort first; ties use descending BM25 score,
then original IRI and graph. Text selection uses discovery's deterministic
ordered set, skips oversized texts and takes the first budgeted values. Original
text, language, datatype, text predicate and `via` mapping are retained. Existing
description prefixes remain explicitly marked `truncated`. No label is invented
on a direct predicate: a Wikidata property association retains the source
property's text statement and its explicit `wikibase:directClaim` link.

Entity candidates carry separately bounded outgoing/incoming navigation pages;
predicates carry bounded predicate-usage pages. These use existing ordered Rust
navigation. A clipped page cannot establish lack of another direction. Sources
and metadata come only from the requested graph subset; an oversized source
record fails closed. Before serialization, oversize packets remove collection
tails in class/predicate/entity rounds, preserving ranking prefixes. If the
header itself cannot fit, the operation fails. All clipped texts, navigation
pages and collections are flagged, and `clipped` summarizes the packet.
The budget counts compact JSON bytes, excluding the CLI's trailing newline.

## Packet and reference boundary

The [JSON schema](../schemas/question-vocabulary-packet-v1.json) is generated from
Rust types by `verity schema-vocabulary`. Rust validation is authoritative for
source identity, policy, budgets, status and version; JSON shape alone never
authenticates a packet.

Every candidate contains `id`, original `iri` and `graph`, `exact`,
`ranking_score`, observed `texts`, clipping and stored-usage witnesses. Candidate
tables are separate `entities`, `predicates` and `classes` collections. Their
statuses and counts describe all authorized Find matches **before clipping**.
The packet carries question/language, authenticated budgets, policy fingerprint,
scoped source and graph hashes, ranking/index/packet revisions and conservative
semantic limitations. The packet ID binds those inputs; each candidate ID binds
the packet, role, graph and IRI. IDs change with the question, budgets, snapshot,
operator policy, source metadata or implementation revisions. A shared IRI or
alias in two graphs has two identities.

`VocabularyPacket` fields are private and it has no deserializer. Its immutable
`candidates(role)` and `resolve(id, role, graph)` methods are intended for #72's
expander. `resolve` accepts only the exact retained table ID, expected role and
graph; raw IRIs, absent/clipped candidates and IDs from other packets fail.
For serialized packets, call
`Snapshot::revalidate_vocabulary_packet(index, bytes, request, policy, budget)`
with **current server-held inputs** first. It rebuilds rankings, text and source
witnesses and compares the complete packet; unknown/modified fields and stale
inputs fail. Never trust operator inputs echoed by a model or supplied alongside
an uploaded packet. Persist operator inputs independently.

`direction_witness(entity_id, predicate_id, graph, "incoming"|"outgoing")` returns
only a retained original statement linking those exact graph-local candidates.
Incoming means traversing a stored triple from object to subject; the returned
statement is never rewritten into an asserted inverse predicate. Lack of a
retained witness is a bounded-coverage block, not proof of graph absence.

When multiple graph-qualified candidates remain in any role, including matches
hidden by clipping, `requires_disambiguation` is true. A model may propose a
draft, but a consuming UI **must request independent user disambiguation before
execution**. `missing_vocabulary` covers absent entity or predicate matches;
`needs_disambiguation` and `candidates_only` otherwise describe discovery, never
semantic correctness. A single candidate is not an automatic choice. Scores are
ranking scores, never confidence. All RDF labels, source strings and rationale
text are untrusted display data and must not be interpreted as instructions.
No-match does not establish graph completeness or real-world absence.

## CLI and replay

```sh
cargo build --workspace --locked --offline
# Obtain the operator-owned snapshot_id and index_revision from the manifest:
target/debug/verity index-build RDF nquads POLICY SCOPE CONFIG
# REQUEST has question, language, snapshot_id, index_revision and scope.
# BUDGET uses the frozen protocol's budget object.
target/debug/verity vocabulary RDF nquads POLICY SCOPE CONFIG REQUEST BUDGET
target/debug/verity vocabulary-replay RDF nquads POLICY SCOPE CONFIG REQUEST BUDGET SAVED_PACKET
```

The packet commands output compact JSON and no query execution result. Request
and operator scope files must agree. They build the existing authenticated
source index; saved indices can also be validated through the existing Rust API.
No model-facing raw-SPARQL compiler or model reply repair is added.

## Coverage evidence and current dependency

[The report](../reports/issue-73-question-vocabulary/README.md) retains 22 new
AI-authored grounding regression questions against public, already exposed
Wikidata, GeoNames-derived Schema.org and GEMET snapshots. These are **not**
independent new intent/resource lineages, #72's gold, or human-reviewed semantics.
Issue #72 is still open and has not supplied its newly frozen case manifest.
Applying this scorer to that exact manifest remains a dependency before #73's
full cross-issue evaluation criterion can be claimed.

The protocol separates `questions.json` from `references.json`. `freeze` hashes
both inputs before retrieval but never parses references; no case ID enters a
Rust request. All bounded raw packets are checksummed before `score` loads any
reference ID. The scorer replays each packet through Rust, then independently
checks every candidate role, original label/alias, directClaim pair and usage
statement against the retained RDF using RDFLib. Required references and their
directions are source-audited too. Full source triples are retained per case.

Coverage is reported at k=1/5/10/20 for start entities, predicates, classes,
graph-qualified roles and retained directional witnesses. Exact misses, first
misses in frozen order, authorized catalog membership, duplicates, cross-role
repeats, clipping and negative candidate returns remain visible. An unsupported
question can retrieve vocabulary; this does not make it answerable. Absence of
reference rows on unsupported cases is excluded from coverage-success counts.
A changed packet fails at the first exact replay regression; coverage and
source-evidence changes fail report comparison.

```sh
# Existing Python reference dependencies only; no model requirements.
python tools/question_vocabulary.py freeze --folder FRESH_DIRECTORY
python tools/question_vocabulary.py score --folder FRESH_DIRECTORY --report NEW_REPORT
python tools/question_vocabulary.py verify
```

Freeze/score refuse existing destinations. To use #72's future frozen cases,
provide a new versioned protocol with separate question/reference files and
operator source paths. Do not rewrite the retained baseline. Freeze all
selection/budgets before inference, score after rankings exist, and disclose the
new manifest's actual provenance and reviewer status. The current report
explicitly records the pending #72 dependency.

Ordinary CI replays saved packets without models or network acquisition. Frozen
#37–#58 evidence and the sealed external Ask holdout are untouched.
