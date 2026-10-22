# Ten incompatible reverse empty-path references

This is an engineering assessment of public retained evidence, not a compiler
change or semantic evaluation. The historical generic Rust rejection in all ten
synthetic reference receipts is exactly:

```
deterministic_preflight_block: Host snapshot, source, scope, resolution or limits prohibit this draft
```

`nl_ask::preview_nl_ask` deliberately maps underlying `preview_ask` errors to that
preflight error. The attached [receipt](compiler-assessment.json) preserves each
original receipt verbatim, the numeric draft, original question, expanded request,
full constructed typed plan, and a new **preview-only** core rejection. No query
is executed. The underlying errors are eight `datatype` and two `class` errors;
the prior broad “range incompatibility” description did not expose that distinction.

All plans project distinct `?step1`, with no filters/aggregation, limit 100, and
one reverse pattern `from=start, to=?step1`. Thus the actual RDF triple is
`?step1 predicate <start>`. Snapshot is
`sha256:3c3566a64b607958c87de370c891eed500b0b698e78101e15df333edfaecc289`.
Graph W/G/M below means the exact evaluation graph
`urn:graph-verity:nl-ask-v1:evaluation:{wikidata,geonames,gemet}` respectively.
The JSON has every full IRI and graph-qualified numeric identity.

| Case | Graph; start ID / predicate ID | Start; original predicate | Core rejection |
|---|---|---|---|
| explicit-003 | W; 100 / 1000 | Wikidata Q134620; rdfs:label | datatype: IRI object incompatible with scoped predicate range |
| explicit-006 | W; 100 / 1001 | Q134620; skos:altLabel | datatype |
| explicit-013 | W; 100 / 1003 | Q134620; wdt:P1448 | datatype |
| explicit-020 | W; 100 / 1005 | Q134620; wdt:P571 | datatype |
| explicit-028 | G; 107 / 1007 | GeoNames 630752; rdf:type | class: Type object is not an observed class |
| explicit-035 | G; 104 / 1009 | schema:AdministrativeArea; schema:identifier | datatype |
| explicit-038 | G; 104 / 1010 | schema:AdministrativeArea; schema:name | datatype |
| explicit-042 | M; 111 / 1011 | GEMET concept 12011; rdf:type | class |
| explicit-049 | M; 111 / 1013 | GEMET concept 12011; skos:definition | datatype |
| explicit-056 | M; 111 / 1015 | GEMET concept 12011; skos:prefLabel | datatype |

For **each of the eight datatype cases**, reverse puts an IRI in the object
position of a predicate whose graph-local observed range contains only literals.
The unchanged typed contract requires rejection before execution. Valid RDF in
general could use a different object range, but that broader SPARQL capability
is not this compiler's contract. For **each rdf:type case**, the fixed object is
not an observed class in that graph; the explicit class constraint requires
rejection. All ten start entities are observed and graph-qualified, so this is
not a fabricated-ID issue. Empty paths alone do not imply incompatibility: other
well-typed empty-path requests can compile and correctly return no rows.

No compiler correction is justified by these probes. Accepting them would expand
current typed semantics (including ordinary manual callers) and require separate
contract, type propagation, source-scope, negative and empty-result analysis.
Disabling the range/class checks would weaken validation and is excluded here.

The future correction justified for every listed case is in **mechanical probe
construction**: distinguish type-compatible empty paths from deliberately invalid
negative probes. For literal-only predicates, reverse IRI starts belong in a
rejection stratum, or are omitted from the supported-empty stratum. For rdf:type,
choose an observed class if a suitable empty case exists; otherwise mark a
negative probe. Preserve raw reference and inference bytes, denominators and
original scores. A future version may add this classification beside the old
references; it must not relabel the original experiment retrospectively.

PR #105 actually proposed matching candidates for 013/020/028 and got rejection;
003/006/035/042/049/056 abstained, and 038 chose an accepted wrong forward plan.
Those are different observations from this ten-reference compatibility audit.

## Separately scoped issue proposal

**Title:** Version the explicit-predicate probe generator with typed empty-path strata.

Change only a new development panel/generator version. Use the existing graph-local
predicate profiles and observed class contract to classify each proposed empty
path before including it as supported. Keep all ten historical IDs, references,
raw outputs and hashes immutable; add lineage and separate positive/negative
denominators. Test a valid reverse empty path, a reverse IRI/literal mismatch,
and a reverse rdf:type non-class mismatch. No compiler changes, inference or #75
integration. A new generation trial requires its own registration and authorization.
This is a proposal only; no issue or compiler PR was opened by this work.

Reproduce into a **new** output file after `cargo build --locked --offline -p verity_cli`:

```sh
.venv/bin/python tools/assess_ask_compiler.py > /tmp/ask-compiler-assessment.json
```

The script asserts the exact ten identities and typed rejection categories. It
reads the exposed development archive and preview APIs only, never sealed holdouts
or model assets. Compare `cases` and `inputs_sha256` to the committed receipt.
