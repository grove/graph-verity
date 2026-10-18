# Source-witnessed neighborhood packet v2

Issue [#82](https://github.com/grove/graph-verity/issues/82) adds an opt-in,
model-free diagnostic API and CLI. Its protocol, schema, IDs and replay are
separate from [v1](question-vocabulary-packet-v1.md). It does not execute Ask,
resolve an entity, change Find, enable hybrid retrieval or connect an LLM.
The [measured regression report](../reports/issue-82-neighborhood/README.md)
compares all 30 exposed #72 evaluation questions with the unchanged v1 baseline.

## Deterministic candidate policy

`Snapshot::neighborhood_packet(index, request, policy, budget)` takes the same
operator-owned `VocabularyRequest` and `VocabularyBudget` as v1. The complete
original question is passed unchanged to authorized, graph/role-filtered BM25.
No reference IDs, answers, query decomposition or language translation enter
retrieval. Supported languages remain en/no/nb/nn and observed untagged text.

1. Retain the original top-k entity candidates, including alias collisions and
   separate identities for the same IRI in different graphs. Every retained
   candidate is a seed; none is selected as the intended start.
2. For each seed, enumerate the existing ordered original outgoing and incoming
   navigation pages in its own named graph. Inspect up to 200 statements per
   direction, paging at at most 50 within operator row/evidence limits. A
   predicate must occur in an inspected original statement and independently
   have the predicate role in that same graph's authenticated discovery index.
3. Merge those predicates with the original lexical predicate top-k. Exact
   whole-IRI, label, alias and identifier hits retain their original order first.
   Next come neighbors ordered by earliest seed rank, retained lexical BM25
   score descending, original predicate IRI, then graph. Remaining lexical hits
   follow in original score order. Added neighbors carry score zero; it is a
   sentinel for no retained lexical score, never confidence. This policy can
   retrieve irrelevant metadata predicates and does not infer question intent.
4. Retain at most k per role and enforce the same overall compact JSON byte
   budget as v1. Remove class/predicate/entity tails in rounds if needed. Original
   ambiguity counts survive clipping. Predicate `matches` is a conservative
   upper bound: hidden lexical hits can overlap neighbors added to the top-k.
   `matches_semantics` explicitly states this limitation.

Entity usage pages retain the inspected original statements, directions and
clipping. Predicate usage pages retain the existing bounded original usage
query. Labels/aliases preserve language, datatype, source text predicate and any
real, graph-local `wikibase:directClaim` association. Source/attribution and graph
hashes remain scoped. Incoming traversal never rewrites a triple or creates an
inverse property. `direction_witness` requires the retained graph-qualified
entity/predicate IDs and an original subject/object witness. A missing witness,
clipped page, clipped seed collection or lexical no-match is unknown coverage,
never proof of absence. No-match and ambiguity remain visible packet statuses.

## Bounds and identity

The [registered protocol](../benchmarks/question-vocabulary-v2-neighborhood/protocol.json)
uses k=20 for each role, at most 20 seeds, 200 edges per seed per direction
(8,000 inspected edges), 1 MiB total compact output, eight texts per candidate,
2,048 bytes per text, three statements per predicate usage page, and 4,096 source
metadata bytes per graph. API requests may lower the existing v1 budgets within
its validated ranges; changing a budget changes IDs.

The additional working evidence cap is 8 MiB of serialized statements; excess
fails closed. Existing navigation has its own 8 MiB serialized-result cap. No
new persistent index is allocated. Existing limits remain 16 MiB source bytes,
100,000 quads, eight graphs, and a conservative 64 MiB discovery allocation and
serialized-index limit. These are input/work/output budgets, not a promised
whole-process allocator or RSS cap. Transient JSON, navigation and RDF store
allocations are included in measured process memory; the report discloses that
its small-fixture RSS is not a worst-case memory bound.

A successful retrieval checks a 30,000 ms cooperative deadline, in addition to
existing per-navigation policy deadlines. Timeout and byte/index limit errors
produce no packet. The API does not claim hard real-time scheduling or preempt
index construction; CLI source loading/index construction are separately
measured. Resident sessions use one operator index, bounded 64 KiB input frames,
and no concurrency or arbitrary query execution.

Packet IDs bind version, question, language, scope, snapshot, immutable discovery
revision, policy, budgets, graph hashes, source attribution, ranking revision and
v2 implementation revision. The implementation hash includes navigation,
compiler, execution, v1 witness types and NL Ask bridge code. Candidate IDs bind
the packet, exact IRI, graph and role in a new v2 domain. The module is exported
as `verity_core::nl_ask::neighborhood` to avoid changing `lib.rs`, which is part
of v1's frozen discovery source identity. V1 code is intentionally unchanged;
v2 reuses its public witness/request types while keeping separate construction.

## Replay and numeric draft bridge

`NeighborhoodPacket` has private fields and no deserializer. Serialized packets
must pass `Snapshot::revalidate_neighborhood_packet` using independently retained
current operator inputs. V2 accepts the exact compact bytes emitted by Rust;
pretty JSON, duplicate keys, unknown fields, edited evidence and stale source,
scope, policy, question or budget are rejected. CLI output adds one newline;
remove that newline before saving/replaying, as in the capture tool.

`freeze_neighborhood_catalog(index, packet, selection, policy)` rebuilds packet
identity and independently checks every operator-owned `CatalogSelection`
graph/IRI/role against the retained packet and existing authorized #72 catalog.
Numeric IDs are assigned explicitly by the host; no table or resolved start is
generated automatically. `resolved_start: null` continues to prohibit a candidate.
Keep ambiguous choices available for independent user resolution. Choosing a
subset or setting `resolved_start` is an explicit host/user interpretation, never
an inference from ranking or evidence presence.

The returned opaque `NeighborhoodContext` binds the numeric catalog and packet
ID. The host **must store the packet ID beside each draft**, outside the unchanged
`nl-ask-draft-v1` model proposal, and pass that saved identity to
`preview_neighborhood_draft`. A different packet ID fails instead of remapping
old numeric IDs. Rebuild the context with current operator source inputs before
previewing saved material. The draft still accepts only numeric IDs, explicit
direction and values output. Rationale and RDF text are inert untrusted display
data. This API produces only the existing Confirmed Ask preview; execution still
requires independent exact-plan approval through the existing flow.

## Reproduction

```sh
cargo build --locked --offline -p verity_cli --bins --example neighborhood_session
# Use the manifest from the existing index-build CLI for request identity.
target/debug/verity neighborhood RDF nquads POLICY SCOPE CONFIG REQUEST BUDGET
target/debug/verity neighborhood-replay RDF nquads POLICY SCOPE CONFIG REQUEST BUDGET SAVED_PACKET
target/debug/verity schema-neighborhood
.venv/bin/python tools/neighborhood_vocabulary.py verify
```

The retained `registration.json` predates all new scored ranks. For a fresh
capture, use a new folder; capture refuses overwrites and never parses references.
It checks every v1 packet byte against #74, seals all packet bytes, and only then
allows a separate score command to load references and independently audit RDF
with RDFLib. Do not rerun `register` over the retained preregistration.

```sh
.venv/bin/python tools/neighborhood_vocabulary.py capture --folder artifacts/neighborhood-new-capture
.venv/bin/python tools/neighborhood_vocabulary.py score --folder artifacts/neighborhood-new-capture --report artifacts/neighborhood-new-coverage.json
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

Fresh performance capture requires host permission for read-only `ps` and
`/usr/bin/time` statistics on macOS. Replay/ordinary CI needs neither operation,
network, models nor the sealed external Ask holdout. The Python test runner
automatically discovers the new replay/security tests.
