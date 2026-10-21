# #83 reverse-direction and predicate-meaning audit (model-free)

**Decision: INCONCLUSIVE_REVISE.** This is a source-grounded **AI investigator review**, not an independent human semantic judgment, new frozen experiment, inference authorization, or product-readiness assessment. It records no new model calls, repairs, retries, downloads, query executions, or changes to old runs. #83 stays open; #75 integration stays disabled. Human review remains **pending**.

This audit builds on merged [#93](../../experiments/native-one-hop-v1f-diagnostic-r3-evidence/README.md), [#94](../native-one-hop-v1h-investigation/README.md), [#95](../native-one-hop-v1h-budget-qwen35-evidence/README.md), [#96](../native-one-hop-v1h-budget-gemma4-swap2048-evidence/README.md), and [#99](../native-one-hop-v1h-qwen-status-precedence-first-evidence/README.md). See [review.json](review.json) for the complete, machine-readable source witnesses, exposed reference fields, status results and raw-output SHA-256 identities. Source records were inspected read-only, including [evaluation N-Quads](../../studies/nl-ask-v1/evaluation/snapshot.nq), [case references](../../studies/nl-ask-v1/cases.json), the [original numeric catalog](../native-one-hop-v1h-investigation/generated/coordinator/original-host-catalog.json), [r3 case analysis](../native-one-hop-v1h-investigation/generated/failure-by-failure.json) and [latest Qwen analysis](../native-one-hop-v1h-qwen-status-precedence-first-evidence/analysis.json).

## Graph-grounded reverse paths, not independently proven meanings

Both relevant stored statements belong to graph `urn:graph-verity:nl-ask-v1:evaluation:wikidata` (graph ID **0**):

| Exposed case / original question | Stored source witness (subject → predicate → object) | Exposed AI reference draft (reverse) |
|---|---|---|
| `eva-07` — “Hvilke ressurser i universitetsgrafen har Q134620 som administrativ enhet?” | `Q578326 → P131 → Q134620` | start **100** (Q134620), predicate **1002** (P131), graph **0**, direction **reverse**, output `values` |
| `eva-08` — “Which resources list https://www.jyu.fi/ as their official website?” | `Q578326 → P856 → https://www.jyu.fi/` | start **103** (website IRI), predicate **1006** (P856), graph **0**, direction **reverse**, output `values` |

These are reproducible **graph-path witnesses** for the two exposed reference interpretations. They establish that an incoming P131 or P856 edge exists; they do **not**, by themselves, independently verify that P131 means “administrative unit” or that P856 means “official website.” The original source predicate-description lists are empty. The local names `P131` and `P856`, adjacent objects, model prior knowledge and AI-authored reference plans are not licensed source definitions. Do not silently add natural-language predicate glosses to model input or declare exposed gold independently true.

There is a separate source-naming limitation: the original named graph is titled “wikidata,” not explicitly “university graph”; the graph-0 `Q134620` resource has no descriptive label in the source. The website entity `https://www.jyu.fi/` (ID 103) also bears the shared `Campus` alias; this does not resolve other `Campus` identities or authorize graph conflation. The particular questions identify Q134620 and a URL directly, which should be distinguished from alias-only ambiguity.

## Observed failure mechanisms, separated

| Experiment and condition | `eva-07` reverse administrative case | `eva-08` reverse website case | Interpretation boundary |
|---|---|---|---|
| Original Qwen r3, oracle | `needs_clarification` | `needs_clarification` | First response recognizes P131 reverse traversal in prose yet requests additional subjects; second recognizes website adjacency but declines to map the unspecified predicate meaning |
| Original Qwen r3, BM25-v1 | `needs_clarification` | **No generation** | P131 numeric predicate absent in authorized table; website request exceeded the frozen context before completion |
| Qwen v1h, oracle | `needs_clarification` | `needs_clarification` | Context compaction did not resolve either oracle interpretation |
| Qwen v1h, BM25-v1 | `needs_clarification` | `needs_clarification` | The website case became measurable; no reverse candidate resulted |
| Qwen status-precedence, oracle | `needs_clarification` | `needs_clarification` | Status precedence alone did not produce reverse candidates |
| Qwen status-precedence, BM25-v1 | `unsupported` | `needs_clarification` | The former is a new unsupported response despite otherwise supported task intent; P131 numeric ID remains missing |
| Gemma v1h, oracle | `candidate`, start **102**, **forward**, Rust rejected | `candidate`, start **102**, **forward**, Rust rejected | Describing the stored forward edge does not supply the requested object-anchored reverse plan |
| Gemma v1h, BM25-v1 | `unsupported` | **Timed out, zero completed response bytes** | Missing authorized P131 numeric vocabulary on the first; the latter is a runtime stop, not a measured model status |

Evidence for original r3 is in the retained [failure-by-failure analysis](../native-one-hop-v1h-investigation/generated/failure-by-failure.json), for Gemma in the [original-byte failure matrix](../native-one-hop-v1h-budget-gemma4-swap2048-evidence/failure-matrix.md), and for Qwen's latest experiment in its [comparison](../native-one-hop-v1h-qwen-status-precedence-first-evidence/comparison.md) and [analysis](../native-one-hop-v1h-qwen-status-precedence-first-evidence/analysis.json). These are historical runs under distinct controlled variants. No missing result is counted as an incorrect model interpretation.

### What can and cannot be concluded

1. **Reverse plan assembly is visibly failing in these probes.** On complete oracle evidence, Qwen abstains and Gemma constructs forward, wrong-start drafts. The existing Rust preflight rejects Gemma's proposals; an accepted clarification is not evidence that Qwen correctly constructed the reverse plan.
2. **Retrieval evidence must be treated independently.** In BM25-v1 `eva-07`, the authorized numeric predicate table lacks P131 even though source triples exist elsewhere. Supplying P131 would be a new retrieval/input factor, not a parser-only correction. In `eva-08` the required numeric predicate is available, while an independently licensed natural-language predicate definition is not.
3. **Multiple returned values are allowed.** The one-hop `values` projection does not require there to be at least two source subjects, nor does plural “resources” imply a count, filter, multi-hop or unsupported query. The source witness shows at least one incoming edge, not an exhaustive real-world claim.
4. **Meaning remains a blocker to independent semantic scoring.** A proposed reverse path agreeing with exposed AI references could still be wrong relative to the natural-language question. No such paths have been independently reviewed as truth.
5. **Do not conflate failure modes.** Original context overflow and the Gemma timeout are runtime/transport stops; missing BM25 numeric IDs, ambiguity about graph description, opaque predicate semantics, model-origin abstention and wrong-direction candidates are distinct observations.

### Minimal follow-up options (NOT preregistered)

**Source provenance review, model-free first:** Have a reviewer establish whether the authorized, licensed original source includes reliable meanings for P131 and P856, preferably with exact language-bearing predicate statements and provenance. The current frozen snapshot supplies no such definitions. If additional source material exists, retain it separately with legal/graph/snapshot binding and document that it changes the evidence environment. Do not fill missing properties from model memory, external assumptions, or exposed reference plans. A human reviewer has not yet performed this check.

**Directional interpretation ablation, only after that review:** Propose one separately registered change testing inverse traversal construction while keeping the current lossless packet format, numeric IDs, prompt-status precedence, model/runtime, source membership, host gates and output reserve fixed. Do not bundle the direction wording change with predicate glosses or BM25-v1 retrieval changes. Explicitly count reverse and forward candidates, five-field start/predicate/graph/direction/projection agreement, wrong-but-executable drafts, model-origin clarification, unsupported-operation regressions and source-table contradictions. Preserve all correlated repeats, failures, missing denominators and raw byte witnesses. No inference permission is granted by this document.

**Separate retrieval factor:** If BM25-v1 `eva-07` is revisited with source-authorized predicate inclusion, create a distinct retrieval condition and registration. Do not silently “repair” the frozen BM25-v1 packet or imply it was evaluated in the earlier runs.

## Method, validation, and scope

The audit compared the two source N-Quad witnesses, the corresponding original graph-qualified IDs and exposed reference fields, all four latest Qwen oracle/BM25-v1 statuses and their exact raw response digests, older r3 Qwen findings, and the retained Gemma failure matrix. Source/ID and Qwen outcome consistency were checked read-only against the current committed artifacts while preparing `review.json`.

This is a **documentation-only** change: it neither rebuilds Rust nor executes the repository's full model-free 39-check pipeline. CI for this new PR must run before merge; no new test success or unchanged-hash verification is claimed for this branch. Historical reports, freezes, registered binaries and original receipts have not been edited by this audit. It neither supplies independent human review nor registers an inference variant.

**Decision stays `INCONCLUSIVE_REVISE`.** #83 OPEN, #75 DISABLED, v1g inference unrun, human review pending, no new inference or RDF executions.

