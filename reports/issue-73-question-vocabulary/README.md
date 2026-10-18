# Issue #73: question-only vocabulary grounding baseline

Model-free BM25 baseline, frozen 18 October 2026. No inference, model weights,
human judgments, automatic Ask execution or sealed holdout access.

## Result

| k | Start entity / 18 | Predicate / 18 | Class / 1 | Direction witness / 18 | All required IDs / 18 cases |
| --- | --- | --- | --- | --- | --- |
| 1 | 11 | 7 | 0 | 3 | 3 |
| 5 | 18 | 11 | 0 | 9 | 10 |
| 10 | 18 | 11 | 0 | 9 | 10 |
| 20 | 18 | 11 | 0 | 9 | 10 |

These counts require the correct graph and role. **Retrieval coverage is not
model understanding, answer correctness or a product GO.** The 37 required
entity/predicate/class references are independently checked as actual entries
in the authorized real-source catalog. Duplicate graph-qualified candidates
within roles: zero. Cross-role appearances remain separately counted.

The 22 cases comprise 18 reference one-hop questions, two negative vocabulary
probes and two unsupported/open-world probes. At top 20, the lexical no-match
probe returns zero candidates; the unknown Atlantis question returns 13
candidates despite lacking an authorized start. No-match false candidates are
retained as identities, not silently discarded or called correct abstention.

The first miss, at every reported k, is `capital-inflected-no`:
«Hva er hovedstaden i Norge?» retrieves Norway but does not retrieve
`http://www.wikidata.org/prop/direct/P36` in the development graph. Unstemmed
whole-question BM25 does not match the stored `hovedstad` label to `hovedstaden`.
The parallel Swedish question and Norwegian GEMET predicates also miss;
Schema.org place predicates lack matching natural-language labels. The
Schema.org City class is a real authorized catalog entry but is not retrieved
by its case question. **No gold-driven enrichment, stemming or decomposition
was added after observing these misses.**

Direction coverage is lower than predicate coverage: bounded pages may omit the
needed statement even when both IDs were retrieved. The two Oslo/country probes
retain the correct IDs but miss the specific directional witness within the
three-statement pages. This is a separately visible evidence-budget limitation,
not an inferred inverse property or proof that the source relation is absent.
21/22 packets have at least one text or navigation clipping flag. Each raw packet
retains its precise per-collection, text and page flags.

## Evidence and reproduction

- [Protocol](../../benchmarks/question-vocabulary-v1/protocol.json): immutable
  whole original question per role, top 20, 1 MiB packet, eight texts, 2048 bytes
  per text, three witnesses/page, 4096 source-metadata bytes/graph; existing
  bilingual/untagged index universe and deterministic Find tie ordering.
- [Questions](../../benchmarks/question-vocabulary-v1/questions.json) and
  [references](../../benchmarks/question-vocabulary-v1/references.json) are
  separate. New AI-authored grounding regression wording; source/intent
  lineages are public and exposed. Independent human reviewers: **0**.
- [Freeze](freeze/freeze.json) records the baseline commit plus exact current
  implementation/input SHA256s before packet generation and scoring. Every case
  retains the operator request and compact bounded packet. Per-corpus manifests
  retain snapshot, policy, source, graph and index identities.
- [Coverage](coverage.json) contains every required identity/rank, each k's exact
  missing IDs, role/graph membership, direction coverage, clipping, negatives and
  original source triples independently audited with RDFLib. Both Wikidata
  directClaim/text witnesses are retained; labels are never fabricated on a
  direct predicate.
- [Checksums](checksums.json) bind report and raw files; the freeze has its own
  [checksums](freeze/checksums.json). Verification rebuilds each packet through
  Rust and compares coverage/source evidence exactly.

```sh
cargo build --workspace --locked --offline
python tools/question_vocabulary.py verify
# New experiment only; never replace the retained freeze/report:
python tools/question_vocabulary.py freeze --folder FRESH_DIRECTORY
python tools/question_vocabulary.py score --folder FRESH_DIRECTORY --report NEW_REPORT
```

One development-only RDFLib audit correction was made before a successful score:
RDF 1.1 plain strings and explicit `xsd:string` literals require equivalent term
comparison. The failed development attempt was not a scored trial; case wording,
reference IDs, budgets and BM25 rankings were unchanged. A model-free test now
accepts that equivalence and rejects invented source witnesses. A subsequent
JSON tuple/list replay correction changed only the scorer representation; all
22 packet files were checked byte-identical and the complete scored JSON
remained unchanged. Neither correction changed retrieval or reference policy.

## Dependency and interpretation

**#72 has not supplied its genuinely newly frozen one-hop cases.** This report
measures the packet/scorer integration on public grounding regressions; it does
not substitute these questions for #72's evaluation or claim independent gold.
The same gold-free freeze/replay/scorer can consume a separately versioned #72
question/reference protocol when available. That cross-issue coverage criterion
remains pending, so this PR references #73 without automatically closing it.

No dense/hybrid diagnostic was run. Shipping Find, prior #37–#58 study files,
external Ask holdout and historical Phase 0 evidence are unchanged. These
negative lexical results support further declared retrieval-policy work, not
silently enabling hybrid or treating #58's human gate as passed.
