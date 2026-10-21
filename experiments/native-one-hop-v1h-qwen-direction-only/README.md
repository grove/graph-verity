# Qwen direction-only preregistration — INCONCLUSIVE_REVISE

Refs #83, after merged #100 (`82e81a3e30c315c27d86b5c125143020a172af18`).
No inference is authorized or performed. #83 stays open; #75 stays disabled.
Independent human review is pending. This is an isolated successor to Qwen
status precedence, not a semantic-readiness or exact-answer experiment.

## Predicate provenance and reverse diagnosis

[provenance-audit.json](provenance-audit.json) is reproducible with
`tools/audit_v1h_predicates.py --check`. It binds exact source paths, file hashes,
RDF statements and statement hashes, licensing/revision records, numeric/graph
bindings, unchanged exposed references, and all 16 historical reverse observations
across original r3 Qwen, v1h Qwen, status-precedence Qwen and v1h Gemma. Original
response/context/archive hashes and full retained rationales remain available;
missing/timeout observations have null measured semantics, not failure scores.

The existing licensed item archive `studies/nl-ask-v1/sources/Q578326.ttl`
(SHA-256 `3cf5c243dab29b603e3db395f2c1d3c093ac47abd6a68da34d86ddf27f79e6f3`,
archived item revision **2535539461**, CC0-1.0) contains English property labels,
names and descriptions for **both** predicates. Explicit `wikibase:directClaim`
triples bind each property entity to its direct predicate IRI. P131's source
label is “located in the administrative territorial entity”; its description
concerns territorial administrative location, with separate guidance for
non-administrative/event locations and partial territorial inclusion. P856's
source label is “official website”; its description identifies an official-page
URL, current or former, and gives guidance about hijacked/dead URLs. Exact
language-tagged descriptions are retained as source statements in the audit.

These definitions are available in an authorized archive, but **absent from the
frozen evaluation snapshot and model-visible predicate tables**. The pinned
`source_quads` extraction recipe imports the focal entity's selected direct
claims and en/nb/nn labels, then overlays synthetic annotations; it does not
import property metadata. This refines #100's source-availability limitation
without changing that historical report. A separate pre-existing P131 property
archive (revision 2555801353, CC0) contains en/nb/nn metadata; its relevant
statements are separately recorded, outside evaluation source membership.
The enclosing item's revision is not asserted to be a property-page revision.
Both item statements have normal/best rank, with no statement-level
`prov:wasDerivedFrom` citation retained in this archive.

Distinguish four evidence classes:

- Original triples establish these particular stored edges, not their meaning
  or independently verified real-world truth.
- Archived property documentation plus explicit directClaim mappings supports
  the predicate meanings independently of model memory and local IRI names.
- Model rationales are observations and can invent meanings or confuse scope.
- AI-authored exposed references are unchanged comparison targets; source-backed
  meanings do not turn them into independent human judgments.

Both imported witnesses belong to graph **0**,
`urn:graph-verity:nl-ask-v1:evaluation:wikidata`, assigned by the importer:

| Probe | Original subject → predicate → object | Exposed reverse fields |
|---|---|---|
| eva-07 | Q578326 → P131 → Q134620 | start 100, predicate 1002, graph 0, reverse, values |
| eva-08 | Q578326 → P856 → https://www.jyu.fi/ | start 103, predicate 1006, graph 0, reverse, values |

The original Qwen r3/v1h oracle eva-07 rationale explicitly recognizes the
incoming edge and the reverse start, then asks for other subjects. Its eva-08
rationale mixes missing predicate meaning with a supposed requirement for more
than one resource. Latest status-precedence oracle eva-08 still asks for all
resources despite recognizing the visible edge. Plural wording does not impose
a minimum cardinality, count or extra hop. Observed usage is not an exhaustive
absence assertion; a plan may return zero, one or multiple subjects.

Latest Qwen oracle eva-07 also calls P131 “part of” and requires a vocabulary
identity for “resources”; these are model-authored interpretations. Latest
retrieval eva-07 invents a university-graph/GEMET mapping. The snapshot labels
the graph Wikidata and leaves Q134620 without a descriptive label, so graph
naming and predicate meaning remain distinct semantic limitations.

BM25-v1 eva-07 lacks the authorized P131 numeric predicate. Adjacency in a packet
cannot restore that ID; a supported one-hop request with missing numeric
vocabulary still requires clarification under the unchanged status rule.
Latest Qwen and Gemma instead emit unsupported. BM25-v1 eva-08 has the original
P856 numeric ID, but no predicate gloss; it is not the same retrieval failure.
Original r3 eva-08 overflowed before generation. Gemma eva-08 retrieval timed
out with zero completed response bytes; neither is a semantic answer.

Gemma's two oracle reverse drafts retain the original predicate/graph/values
but emit subject start **102** and **forward**. Its eva-08 rationale describes
the stored edge accurately while assembling the wrong requested plan. Rust
rejects both through the original start-resolution fixture. Synthetic tests
also document that a wrong direction with valid IDs and the authorized start
can pass structural validation: Rust does not assess question meaning.

These support hypotheses of over-abstention, missing semantic metadata and plan
assembly errors; raw rationales alone do not establish their causal weights.
The direction instruction is separable as a prompt factor. These two exposed
probes cannot disentangle its causal effect from missing meaning, so semantic
interpretation remains unresolved even if future reference agreement improves.

## Sole factor and frozen protocol

[prompt.diff](prompt.diff) replaces only the sentence explaining reverse
construction. It specifies original-object start, original predicate, original
graph and graph-qualified numeric IDs, matching subjects via `values`, and no
plural-cardinality/count/extra-hop requirement. It adds no examples, intended
IDs, gold plans, translated aliases, descriptions or source assertions.
Every other system-prompt byte, including current status precedence, is retained.

The successor reuses the existing status-precedence and v1h freeze/runner code.
It checks equality with the immediate parent's configuration outside the
explicit experiment identity, hypothesis, evaluation and registration fields.
Contexts, original contexts, lossless columnar packets, membership, graph/role/
IRI/numeric bindings, GBNF, schema, operator fixtures and schedule remain
unchanged. Audit and synthetic drafts are bound artifacts, never prompt input.

Pinned Qwen3.5-9B/Q4_K_M, llama.cpp, tokenizer/template and binary identities are
in `registration.json` and its freeze. Runtime remains CPU, four threads, zero
GPU layers, concurrency one, seed 7, temperature zero, thinking off, 16,384
context, 512 output reserve, 300-second deadlines and 24 GiB sampled RSS ceiling.
The original **1024 MiB** swap gate and all remaining host/resource thresholds
are unchanged. Full pinned asset verification, offline tokenizer recount,
native grammar controls and a fresh <=60-second original host gate must pass
before any separately authorized future model load. A blocked gate must wait.

`freeze.tar.gz` binds committed source and all input hashes, exact messages,
prompt diff, original status-precedence evidence archive, both packet forms,
runtime identities, token arrays/section counts, and all 38 requests: two
unchanged native sampling controls, then 19 oracle and 17 BM25-v1 semantic
observations in original order, including correlated repeats. No retries.
Each scheduled columnar prompt must satisfy **input + 512 < 16,384**. Original
uncompressed overflows remain recorded. Pinned tokenizer historical native
parity must reproduce; fresh native text/token parity remains mandatory before
each future generation. Budget results are in the freeze and validation receipt.

The checksum-derived ledger belongs to this separate freeze; no old ledger may
be reset or reused. The proposed output destination is fresh and unique.
Integrity, authorization, grammar, private-canary, runtime or resource failures
stop the remaining schedule; known semantic failures remain observations.
Every failed and unattempted identity must be retained. Rust preview only;
no emitted plan or generated RDF is executed. No holdout or #75 access.

## Future measurement criteria

The primary diagnostic is exposed reverse-reference agreement, historically
**0/2 oracle and 0/2 BM25-v1** in the latest Qwen baseline. Report each condition
separately, and list every five-field match/mismatch (start, predicate, graph,
direction, projection), wrong-start/direction candidate and binding contradiction.
List all forward-candidate regressions and each lost baseline valid candidate.
Candidate-reference denominators remain **10 oracle and 8 BM25-v1**, including
abstentions as nonmatches; forward denominators are **8 and 6**, reverse **2 each**.

Measure model-origin clarification on the three genuine clarification probes
per condition (baseline **3/3 each**). Preserve the separate four-case AI
ambiguity audit and original source-label candidate reference. A rejected
candidate is not model-origin clarification. Measure model-origin unsupported
on six forbidden operations per condition (latest baseline **3/6 oracle,
5/6 BM25-v1**); Rust rejection is not unsupported classification.

Report full scheduled denominators **19 oracle, 17 BM25-v1, 36 semantic**, plus
two controls, attempted/completed/failed/unattempted totals and paired completed
identities separately. Report source insufficiency, missing numeric vocabulary,
native controls, latency and all sampled process-tree RSS. Inspect every retained
rationale against source bindings with exact excerpt/raw/context hashes; the
narrow existing contradiction detector is not exhaustive. No statistical
superiority, exact-answer accuracy, semantic-readiness or independent human
review claim is permitted. Decision remains **INCONCLUSIVE_REVISE**.

## Model-free reproduction

Commit sources before building and registering; use fresh destinations:

```sh
.venv/bin/python tools/audit_v1h_predicates.py --check
.venv/bin/python tools/native_one_hop_v1h_direction.py freeze --out artifacts/v1h-qwen-direction-only
.venv/bin/python tools/native_one_hop_v1h_direction.py register --freeze artifacts/v1h-qwen-direction-only
.venv/bin/python tools/native_one_hop_v1h_direction.py verify --freeze artifacts/v1h-qwen-direction-only
.venv/bin/python tools/native_one_hop_v1h_direction.py budget --freeze artifacts/v1h-qwen-direction-only --out artifacts/v1h-qwen-direction-only-recount
.venv/bin/python -m unittest discover -s tools -p test_native_one_hop_v1h_direction.py -v
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

To restore the committed freeze instead, extract `freeze.tar.gz` into a fresh
freeze directory, then verify. Full pipeline validation uses an isolated checkout
and build to preserve the registered binary. Validation/preservation receipts
record exact tested revisions and any subsequent receipt-only additions.
Synthetic saved drafts verify engineering contracts only, never actual model
understanding. All historical artifacts and all 801 historical hashes stay fixed.

## Proposed exact command for separate future authorization

After reviewing this committed registration, authorize its exact revision,
Qwen, the 38-request schedule and this fresh destination explicitly:

```sh
.venv/bin/python tools/native_one_hop_v1h_direction.py run --freeze artifacts/v1h-qwen-direction-only --model qwen35 --allow-inference --out artifacts/issue83-v1h-qwen-direction-only-first
```

This is a proposal only. Earlier Qwen/Gemma authorizations do not transfer.
No inference, retries, asset downloads/updates, merge or human approval is claimed.

Limitations: small exposed AI-authored probes, correlated repeats, missing
model-visible definitions, missing BM25 P131 ID and unresolved graph wording.
Source documentation improves provenance assessment without repairing frozen
input. Tests cannot establish future behavior; host/cache differences prevent
causal latency/RSS claims, and RSS sampling can miss peaks or double-count pages.
