# Assisted Ask v1.1: language selection — blocked implementation proposal

**INCONCLUSIVE_REVISE. Proposal only; language filtering is not shipped.**
Base: `main`, `294fcf0589b02dca1ff497b3cfe37689551e4986` (merged PR #112).
Related: #71, #75, #83. No inference, live #75 integration, issue closure or human
validation is part of this work.

The requested feature is useful and narrow: University of Tromsø → Official
names → All languages / English / Norwegian Bokmål / Norwegian Nynorsk.
Implementation stops at the task's explicit historical-integrity boundary:

> If the change cannot be isolated without violating historical invariants or
> significantly broadening the query language, stop and deliver a scoped
> implementation proposal rather than an unsafe workaround.

## Why the existing engine cannot implement this selection

[`TypedComparison`](../crates/verity_core/src/ask.rs) has only `op` and a complete
typed RDF `value`. [`Filter`](../crates/verity_core/src/ir.rs) adds a variable to
that comparison. Neither represents a language-only predicate. Both Ask and IR
accept version 1 only. The compiler emits a comparison against the **whole
literal**, including its lexical value, rather than applying `LANG` to the bound
value. Equality against `""@en` selects an empty English literal, not every
English name. Real Rust probes reject `{ "language": "en" }` and version 2;
`""@en` returns zero rows while the authorized snapshot has an English name.

The compiler correctly constructs result and witness queries from a shared
validated query body, before their respective limits. That is where an actual
language predicate must go. Python/browser filtering, larger read limits,
catalog enumeration, or substituting an already known complete name would not
implement the requested language-only operation.

## Historical blocker

The original [observable-r2 freeze](ask-alpha-preview-v1-observable-r2/freeze.tar.gz)
contains 206 pinned input hashes, including 39 Rust/Cargo paths. All currently
match. Its unchanged [native evidence checker](../experiments/ask-alpha-observable-r2-native-evidence/check.py)
asserts that **current repository files** match every pinned input hash:

```python
assert all(sha((ROOT / name).read_bytes()) == digest
           for name, digest in frozen['inputs'].items())
```

In particular, the pinned inputs include:

- `crates/verity_core/src/{ask,ir,compiler,execution,lib}.rs`;
- `crates/verity_cli/src/main.rs`, both crate manifests and workspace Cargo files;
- the original core/CLI Ask tests and `tools/local_nl_ask.py` approval bridge.

Adding a new language operation to the existing engine necessarily changes at
least one of these paths. Even exporting a new module requires the frozen
`lib.rs`; adding an existing-crate binary through Cargo requires a frozen
manifest, or a new example that still lacks access to the necessary internals.
The store, compiled query fields, raw reference-query path and bounded selector
are private to the core crate. Public `execute` always recompiles the existing
IR, so an external wrapper cannot safely add the predicate to the query and
witnesses. A separate executor or fork of the engine would rebuild the subsystem
and duplicate its validation, deadlines, evidence and approval behavior.

No engine, schema, adapter, UI, original verifier or registration is changed.
No source pin is refreshed, no historical evidence is resealed, and no
language-select control is added without authoritative execution support.

## Smallest proposed follow-up

First establish an explicitly authorized historical replay boundary. Preserve
the original checker, registration, freeze, attempts, prompts, model evidence,
snapshots and registered binaries byte for byte. A separately reviewed current
verification entry point could run the original source-pinned checks in an
immutable Git export whose inputs match the original hashes, while separately
testing the current engine. The repository already uses that pattern for older
studies in `tools/run_python_tests.py`. This proposal does **not** authorize or
implement that change: the observable-r2 check currently binds the live checkout.
Do not merely suppress its assertion or replace its expected hashes.

After that boundary is approved and verified, implement one explicitly versioned
language-only Ask/IR extension, retaining the v1 request/preview/approval/schema
behavior for existing callers. The new structured predicate must carry a bound
terminal variable and an enumerated language, with no operator expression or
raw query field. The authoritative preview and approval digest must contain it.
Keep version-specific schema output explicit; do not change historical schemas
to disguise an extension. Reject the new predicate in v1 plans.

The extension should compile a fixed predicate equivalent to
`isLiteral(?step1) && LCASE(LANG(?step1)) = "en"` (or `nb` / `nn`) into the shared
result/evidence body **before** distinct selection, row lookahead, limits and
evidence completeness. Rust must validate the predicate independently, including
version, bound variable and the finite language operand. No arbitrary SPARQL,
language ranges, fallback, translation, joins or retrieval changes are needed.

The product adapter remains restricted to the existing entity, one forward step,
values projection, pinned snapshot and single Wikidata graph. P856 accepts only
the existing unfiltered operation. P1448 requires an explicit result-language
choice for the new selector; distinguish a missing choice from All languages.
Use a separate `result_language` field (`all`, `en`, `nb`, `nn`); the existing
interface `language` field never supplies it. Preserve legacy unfiltered
requests explicitly as v1 for compatibility.

| Structured P1448 choice | Proposed exact semantics |
| --- | --- |
| All languages | No predicate; complete existing distinct RDF values, subject to unchanged limits |
| English (`en`) | Only literals whose RDF language tag equals `en` |
| Norwegian Bokmål (`nb`) | Only literals whose RDF language tag equals `nb` |
| Norwegian Nynorsk (`nn`) | Only literals whose RDF language tag equals `nn` |

Accept only the lowercase selector tokens `en`, `nb`, `nn` and an explicit
`all` token; reject other spellings and malformed values. Compare RDF
tags case-insensitively using lowercase normalization at the RDF term/matching
boundary. This normalization concerns tag case only, not lexical content.
Original snapshot bytes stay unchanged; returned RDF terms and evidence retain
their lexical values, RDF language and datatype. An untagged literal or IRI does
not match a language. `en-GB` does not match `en`; `no` does not match `nb`.
Do not translate, infer a language, rewrite lexical values or use `LANGMATCHES`
to silently include regional subtags. Test the parser's treatment of uppercase
source tags explicitly before claiming normalization behavior.

Add just one accessible selector to the existing UI, shown only for P1448.
Keep interface language independent and retain the result-language selection
when translating the interface. Show the operation before preview, for example
“University of Tromsø → Official names → English only”. Reuse the existing
120-second, single-use, server-held review and its unchanged confirmation bridge.
Store the language in the manual proposal so confirmation rebuilds and compares
the entire restriction. Changes to entity, relationship, result language,
question, cancellation or review expiry revoke approval; changing UI language
may conservatively require fresh review without changing the result filter.
Bind the exact graph, snapshot, row/evidence/time limits and current executable
as before. No text in the optional question may define a filter or establish
that the selected operation answers that question.

Implementation reaches the Ask request/preview, typed IR/compiler, versioned
schemas and affected constructors/callers; the Assisted Ask proposal/resolver
and UI; focused Rust/Python/browser tests; and launch/validation documentation.
Historical model/draft adapters, source data and registered assets stay intact.

## Required regression gates for that follow-up

Keep the current suites and add only tests for the new boundary:

- Real Rust fixtures with multiple different `en` values, mixed-case source
  tags, `en-GB`, `no`, `nb`, `nn`, untagged/typed literals and IRIs. Assert exact
  lexical values, language/datatype and matching source witnesses. Put a matching
  value beyond the unfiltered row cap to catch filtering after clipping; test
  matching rows exceeding the cap and evidence clipping independently.
- Reject unsupported/malformed/missing language choices, language on P856,
  unknown/numeric identities, changed graph/snapshot, raw SPARQL/filter
  expressions and missing authorization. Reject v2 predicates under v1.
- Mutate only the language after preview, including server-held proposals and
  client selections; reject the old approval. Retain cancellation, expiry,
  replay, changed executable/config/policy, timeout and execution-failure tests.
- Actual loopback server + Rust + Chrome journeys for P856, P1448 All/en/nb/nn,
  interface-language changes, edited language, cancellation/fresh approval,
  empty/matching-row clipping/evidence clipping and malicious labels/literals.
  Assert RDF values/tags, not only displayed operation text. Text-only intent
  must leave the chosen operation unchanged.
- Run the full required model-free pipeline and original preservation checks
  under the separately approved replay boundary, keeping failed attempts and
  unchanged successful reruns with their original deadlines. No human
  comprehension or filtered-journey success claim follows from this proposal.

## Observed existing product

The existing [v1 launch instructions](assisted-ask-v1.md) remain valid. Use an
isolated checkout/build to protect the historically registered executable. No
new flag, endpoint or language selector is available from this proposal.

Real HTTP/Rust approval journeys in **both English and Norwegian interfaces**
returned the following original values, source triples, graph, pinned snapshot
and source/license metadata. The unchanged Chrome suite exercised the actual UI.

| Existing operation | Observed RDF values |
| --- | --- |
| P856, unfiltered | `https://uit.no`, `https://en.uit.no/startsida` (IRIs) |
| P1448, all languages | `University of Tromsø – The Arctic University of Norway`@en; `Universitetet i Tromsø – Norges arktiske universitet`@nb; `Universitetet i Tromsø – Noregs arktiske universitet`@nn |

All three names have datatype
`http://www.w3.org/1999/02/22-rdf-syntax-ns#langString`. The result graph is
`urn:graph-verity:nl-ask-v1:development:wikidata`, snapshot
`sha256:48f0c13ddab7ce2a7881509192be30c1fe08693b4e7df5991e68cb302c20561b`.
These observations predict which retained values a correct en/nb/nn selection
would return; **they are not observed language-filtered executions**. No such
operation is implemented or browser-tested. Empty results remain statements
only about matches returned under the authorized operation/snapshot.

[Fresh validation and preservation receipts](assisted-ask-v1.1/validation.md)
document the baseline checks and the preserved failed attempt. Human usability
remains unmeasured. The smallest next step is the historical-replay boundary
decision, followed by this single language predicate and selector, without a
model experiment or interface redesign.
