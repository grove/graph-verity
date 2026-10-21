# #83: r3 semantic failures and a lossless context-budget successor

**INCONCLUSIVE_REVISE. No live inference was authorized or performed.** PR #93
was merged only after the owner explicitly replied “Merge PR #93”. This work
starts at merged `main`, `221a6d644eea597bc1d2786c3fdcac6d212f4058`. Original
r3 outputs, failures, source identities and all v1g registrations remain intact.
#83 stays open; #75 remains disabled. There is no model ranking, exact answer
accuracy, semantic GO or independent-human-validation claim.

## What failed semantically

R3 retained 33/36 Qwen semantic observations: 19 oracle and 14 frozen BM25-v1.
Every measured draft passed grammar and Rust preview, but exposed-reference
agreement was 8/19 and 6/14. Only 3/10 oracle candidate-reference observations
produced matching candidates. None of the measured reverse smokes produced a
candidate. Rust acceptance of clarification validates neither its explanation
nor the interpretation of a natural-language relation.

[Failure-by-failure JSON](generated/failure-by-failure.json) and
[the complete table](generated/failure-by-failure.md) cover all 36 observations,
including the three with no generation. They retain exact context/raw hashes,
actual statuses, rationales, source witnesses and exposed-reference comparisons.
The investigator notes are explicitly AI analysis; human judgments remain null.

| Priority | Observed behavior and source-grounded finding | What remains uncertain |
|---|---|---|
| Norwegian forward | The original country wording clarifies in both conditions. Oracle repeats and smoke share a rationale assigning 1004 to schema:Country/graph 1 and repeatedly P1448. The visible table binds 1004 to P17/graph 0 and 1003 to P1448. Retrieval invents a second university at ID 100, which has no visible name group. | Exact source-label Norwegian and English country probes produced oracle candidates. Wording, identity binding and undefined predicate meaning are distinct factors; this is not evidence that Norwegian alone causes failure. |
| Reverse direction | Oracle P131 rationale explicitly recognizes 102 -> 100 and reverse traversal, then asks for other subjects. P856 rationale also treats plural resources as requiring more than one candidate. The original prompt already defines reverse traversal using the same predicate. | The graph phrase university graph and natural-language P131/P856 meanings lack explicit source definitions. Recognizing a path in rationale is not generating a correct plan. |
| Over-abstention | The explicit rdfs:label question is recognized with entity 102 and predicate 1000, but Qwen still asks for direction/plurality clarification. One-to-many values fit the one-hop contract; plural wording alone does not require multiple hops. | A plan-construction versus answer-completeness confusion is a possible mechanism, not a demonstrated causal prompt defect. |
| Unsupported versus clarification | Counts, filters, negation and multiple hops are explicitly excluded by the system contract. Several rationales name those operations yet emit clarification, sometimes discussing missing vocabulary instead. The retrieval filter rationale also incorrectly says 630752 is not greater than 100000. | Ambiguity instructions precede unsupported instructions and may dominate model behavior. Test status precedence separately; it is unchanged in the budget successor. |
| Missing BM25 vocabulary | Measured English-forward and Norwegian-reverse retrieval cases have no authorized numeric predicate. Other count/filter/multi-hop retrieval cases also lack predicates. Source packet adjacency does not authorize restoring missing table IDs. | More vocabulary would change a retrieval factor. It cannot by itself establish predicate meaning or correct operation classification. |
| Genuine ambiguity and missing meanings | Every stored label can refer to multiple predicates; Campus has multiple identities. All original predicate text lists and descriptive literal metadata are empty. P17/P131/P856 appear as edge identities, not source-backed natural-language definitions. | Exposed AI plans, adjacency, local names and model prior knowledge do not supply independent semantic truth. Human/source review is necessary. |

Private-scope and write controls emitted unsupported in both measured conditions.
Campus, unclear relation and absent start produced model-origin clarification.
These limited observations are distinct from global safety claims. No proposed
candidate disagreed with an exposed plan, but most supported requests abstained.
Injection text was sometimes described as identity conflict; this is evidence
about the rationale, not proof that an instruction was followed or a query ran.
Repetition matched bytes/status/rationale while repeating the same binding error.

The findings support a targeted investigation, not a causal attribution. There
is no independently justified reason to relabel every reference disagreement as
a semantic error: source ambiguity and absent predicate definitions are real.

## Exact context accounting

The pinned official tokenizer and retained native chat-template file measured
**every scheduled prompt for both models**: 36 semantic observations plus two
native sampling controls each, under both original and proposed presentations.
All 36 retained Qwen native prompt/token records and ten historical Gemma native
records reproduce exactly. No llama-server or weight loading was used. Fresh
native backend parity remains mandatory in a future authorized run.

[Every budget](generated/context-budgets.md) and
[all section contributions](generated/context-budgets.json) retain input tokens,
512-token reserve, required total, fit decision, prompt/token hashes and section
accounting. Section contributions are telescoping token differences in original
key order; they sum exactly but depend on order and BPE boundaries. They are not
independent additive importance estimates.

| Largest scheduled prompt | Original input | Original total | Columnar input | Columnar total | Limit |
|---|---:|---:|---:|---:|---:|
| Qwen, retrieval reverse website | 18,926 | 19,438 | 14,019 | 14,531 | 16,384 |
| Gemma, same case | 20,353 | 20,865 | 14,703 | 15,215 | 16,384 |

Only that original scheduled semantic prompt overflows for each tokenizer. R3
Qwen therefore stopped before its request and left both following country probes
unattempted. The embedded packet contributes 14,903 Qwen tokens (15,984 Gemma)
in the original top-level accounting; primary predicates contribute 1,711/1,842
and entities 1,092/1,270. Original serialization repeats verbose object keys,
RDF-term structures and long source strings. The proposed packet contribution
is 9,997/10,335 tokens. A boundary token can move between neighboring marginal
sections; use the complete prompt count for the fit decision.

Repeated-string interning alone and repeated-value interning did **not** fit;
those exploratory measurements are retained in the validation archive. No
threshold was raised or prompt tail clipped to obtain a pass.

## Smallest registered successor

[V1h-budget](../native-one-hop-v1h-budget/README.md) tests **one factor only**:
lossless columnar representation of the embedded original BM25-v1 packet.
Repeated ordered object keys become schemas, and repeated source strings become
references. Roundtrip checks preserve exact original JSON serialization and all
values, ordering, graph/IRI/role bindings and numeric-ID meanings. Primary tables,
names, collisions, usage and provenance outside the packet remain unchanged.
The original packet bytes and IDs remain retained. No missing predicate is added.

Oracle model messages, system prompt, grammar, question schedule, all thresholds
and Rust preview are unchanged. All proposed scheduled prompts fit strict
`input + 512 < 16384`. The runner recounts the entire selected-model schedule
before loading weights, then verifies native prompt/token identity against that
receipt before each completion. This prevents discovering overflow only after
35 requests, without increasing the context limit.

The representation itself may affect interpretation. It is an explicit
presentation/budget ablation, not proof that compaction is semantically neutral
to a model or that completion would improve quality. No natural-language
predicate gloss, status-precedence change, source-label rewrite or retrieval
substitution is bundled into it. V1g's membership comparison remains unchanged
and unrun. A later status-precedence ablation should compare against this same
representation, with retrieval fixed. Official predicate metadata would require
its own archived, licensed source revision and separate registration; none was
downloaded or invented here.

## Independent human review is ready, pending completion

[The staged review archive](generated/blind-review.tar.gz) contains all 36 source
views and 33 actual raw drafts, with three explicit missing-draft records. It
masks model identity and prior judgments; original context structure can reveal
condition, and the exposed questions are not a pristine blinded holdout.

1. **Phase 1:** original NO/EN questions, exact original model-visible contexts
   and messages, authorized source triples, graph-qualified numeric catalog,
   original labels and predicate metadata. Reviewers record interpretation,
   direction, source sufficiency, ambiguity and operation support with citations.
   Host-only catalog fields (`resolved_start`, `blocked`, `limit`) are omitted;
   the original host catalog is retained separately for the coordinator.
2. **Phase 2:** only after saving phase 1, open original draft/rationale and Rust
   preview. Judge the proposal against the independent source assessment. Rust
   acceptance is a contract/scope result, not semantic truth. Missing output is
   not scored as wrong. No draft may execute.

All reviewer identities, times and human judgments remain null/pending. Actual
reviewers must provide their own assessments; the coding agent has not completed
or simulated them. [Coordinator material](generated/coordinator/) contains the
masked-ID mapping, original host catalog, exposed-reference comparisons and
previous AI analysis, outside the initial-review archive. It must stay separate
until the independent assessments are recorded.

## Reproduction, preservation and validation

Restore the committed successor freeze into a fresh directory as documented in
its release README. Portable reconstruction needs the pinned Python dependencies
but no model assets, runtime loading or network:

```sh
.venv/bin/python tools/investigate_v1h.py --freeze artifacts/v1h-budget \
  --out artifacts/v1h-investigation-reproduced
.venv/bin/python -m unittest discover -s tools -p 'test_*v1h*.py' -v
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

The reproduction test checks generated file hashes byte for byte and forbids
process creation. Other regressions cover lossless source/ID bindings, unchanged
empty vocabulary and safety prompt, poisoned-reference independence, exact cached
token accounting and overflow equality, source/archive tampering, opt-in/CI
denial, pre-load failure before Runtime creation, native parity-cache rejection,
all 38 synthetic requests, private-canary stop, and original-byte Rust replay.
The synthetic transport is not model evidence. Ordinary CI never requires model
assets or invokes the tokenizer environment; actual pinned-tokenizer receipts
are hash-bound in the committed freeze.

The complete model-free pipeline passed on commit `048bb08`: all 39 pipeline
checks met their expected outcomes, including 286 current Python tests, 15
frozen pilot tests, 100 Rust tests, formatting, Clippy, required browser checks,
source canaries and historical replays. The nine focused regressions pass.
Fresh restored Qwen recount reproduces all 38 original and columnar prompts and
complete token arrays; original r3 Rust replay passes all 69 saved previews.
See [validation.json](validation.json), [verification.json](verification.json),
[complete logs](validation-logs.tar.gz) and [preservation.json](preservation.json). Earlier unregistered candidates, including an
oversized verbose token receipt and a null host-field review-package test
failure, are documented; no historical freeze was resealed to accept them.

## Recommendation

Stop after this model-free PR. Have actual independent reviewers complete the
staged source/draft assessment, then consider the exact Qwen command in the new
release for separate explicit authorization. It tests bounded presentation and
diagnostic coverage, not semantic GO. A fresh passing original host/asset/source/
binary/resource gate is still required. No Qwen, Gemma or v1g inference, #75
integration, sealed holdout access or automatic merge is authorized by this PR.
