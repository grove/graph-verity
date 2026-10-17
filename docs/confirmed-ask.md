# Experimental Confirmed Ask

[Issue #40's owner decision](https://github.com/grove/graph-verity/issues/40#issuecomment-6234956205)
authorizes this **opt-in engineering prototype**. User need is a hypothesis;
there is no production/release GO, independently reviewed semantic accuracy,
or demonstrated safe user understanding. The tested Qwen Ask configurations
remain stopped. The [evaluation report](../reports/issue-40-confirmed-ask/README.md)
separates automated regressions from missing human evidence.

The [local browser pilot](local-find-ui.md#deliberate-confirmed-ask-walkthrough)
now exposes the same deterministic template without JSON editing. It adds a
session-bound, expiring, single-use UI decision while preserving the core/CLI
contracts below. Human understanding and false-confidence risk remain unmeasured.

## Offline flow after Find

1. Use [Find and entity/predicate navigation](find-mvp.md) to inspect authorized
   resources and source triples. Choose exact entity/predicate IRIs and graphs;
   never automatically promote the first ranked candidate to an Ask argument.
   Ambiguous labels require the user to select an exact IRI. Find confidence
   and confirmation do not establish correct question interpretation.
2. Deliberately select the `follow_path` template and each exact argument in a
   request file. [The capital example](../examples/ask/norway-capital.json) follows
   Wikidata's `P36` outgoing from Norway. No model or question parser is involved.
3. Inspect the preview, then use `ask` and explicitly approve its complete plan.

```sh
cargo build --workspace --locked --offline

target/debug/verity ask-preview data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json examples/ask/norway-capital.json

target/debug/verity ask data/wikidata/snapshot.nq nquads \
  data/wikidata/policy.json examples/ask/norway-capital.json
```

`ask-preview` outputs one JSON preview and never runs a query. `ask` prints a
fresh complete JSON preview, flushes stdout, and prompts on stderr. Review the
`summary` array and `plan`, then type `approve sha256:…` with the **full exact
approval ID displayed**. Enter, `cancel`, `yes`, EOF, an old ID or any other
response yields `{"status":"cancelled"}` without execution. There is no
`--yes` or model proposal option. `ask` stdout contains two consecutive JSON
objects (preview followed by outcome); JSON consumers must read both documents.
An input/output error also prevents execution; interrupts terminate the process.

An approval binds the entire generated typed plan (including scope, immutable
snapshot and row limit) and operator policy (including allowed graphs, evidence
limit and timeout). The CLI retains the loaded snapshot/request in memory, then
rebuilds and validates the plan before execution. A changed file cannot swap
that in-memory plan; the next invocation loads it afresh and requires the new
approval ID. The library also recomputes the binding under current arguments;
edited plans, scope/snapshot changes and revoked authorization reject stale IDs.

The digest is a content binding, **not** a secret, signature, login mechanism,
human-review attestation or proof someone read the preview. Library callers
must collect a deliberate decision for the displayed plan; do not auto-approve
or connect this API to model outputs. A caller can replay the same approval for
the identical immutable plan/policy; this read-only prototype has no persistent
session, expiry or one-shot approval ledger.

## Supported deterministic template

`schema-ask` emits the separate [version 1 contract](../schemas/confirmed-ask-v1.json).
The frozen v1/compact parser contracts are unchanged. The request includes
`version: 1`, exact `snapshot_id`, exact authorized `scope`, `limit`, and:

```json
{
  "kind": "follow_path",
  "start": "http://www.wikidata.org/entity/Q20",
  "steps": [{
    "graph": "urn:graph-verity:wikidata:development",
    "predicate": "http://www.wikidata.org/prop/direct/P36",
    "direction": "forward"
  }],
  "filter": null,
  "output": "values"
}
```

One or two connected steps follow explicit triples. `forward` means outgoing
from the current node; `reverse` means incoming to it. The preview shows the
actual subject → predicate → object direction in each exact graph. Variables
are assigned deterministically (`step1`, `step2`); all steps must match, and
only terminal values are projected. `scope` must equal exactly the set of
step graphs, with no unused or duplicate graph IDs. The start IRI must be an
observed entity in the first graph and each predicate must occur in its graph.

`output: "values"` returns distinct terminal values. `"count_distinct"` counts
distinct terminal RDF terms across all matching paths, not paths, edges or
intermediate entities. The [count example](../examples/ask/norway-capital-count.json)
returns one count row. Zero describes the absence of matching **stored** values;
it cannot establish real-world absence. No grouping, HAVING or branching query
builder is exposed by this small template.

The optional filter applies only to terminal values and reuses the compiler's
typed comparisons (`eq`, `ne`, `lt`, `le`, `gt`, `ge`):

```json
{"op":"gt","value":{"lexical":"50","datatype":"http://www.w3.org/2001/XMLSchema#integer","language":null}}
```

The preview shows the variable, exact operator, lexical value, datatype and
language. Existing validation rejects mixed/incompatible ranges, ill-typed
values, unbound variables, unknown identifiers, unsupported operators and
excessive limits. Language-tagged literals retain their language/datatype.

Unsupported templates, raw questions, label objects, unknown/extra JSON fields,
raw v1/compact proposals, negation, raw SPARQL, SERVICE and writes are rejected;
there is no guessing, repair or fallback to an LLM. For a label or unknown IRI,
return to scoped Find/navigation and select the intended resource explicitly.
The prototype cannot enumerate alternative meanings of an exact IRI selection.

## Security, results and release boundary

Policy authorization precedes preview/catalog construction. Independent Rust
compilation checks graph-local identifiers, types and snapshot identity before
any confirmation is offered, and again before execution. No query, count,
evidence retrieval or external service runs during preview. RDF labels are not
included in the preview; RDF/input strings remain quoted data. The runtime has
no HTTP client, no write endpoint and no new dependency.

A confirmed outcome records `method: experimental_user_confirmed_deterministic_template`,
the approval ID, and the existing execution result with `origin: manual`.
A wrapper `status: executed` means the confirmation path invoked execution;
inspect `result.status`, `complete_within_scope` and
`evidence_complete_for_returned_rows` for independent row/evidence truncation.
Bindings preserve RDF IDs and literal datatypes/languages. Evidence retains
original source triples, named graphs and the immutable snapshot ID. Count
support requires the scoped query as well as positive witnesses.

`interpretation_correctness: not_assessed` and `real_world_truth: not_established`
remain explicit. Confirmation records a user choice; successful execution
verifies that plan against a snapshot. Neither proves the choice faithfully
expresses a question, that sources are complete, or that facts are true.
Missing graph facts remain unknown under the open-world contract.

Before a release decision, recruit actual users and independently assess
misunderstandings and false confidence using the protocol in the report.
Disclose participant and task counts, failures and exclusions. Do not call
automated assertions a usability study or expert review. No sealed Ask holdout,
model trial, deployment or unattended Ask promotion is authorized by this feature.
Issue #40 stays open until implementation, required evidence and passing CI
are merged; merging this prototype still does not authorize a product release.

The separate [issue #48 model experiment](grounded-model-experiment.md) compares
public draft-plan proposals only. Even a promising result cannot enable a model
here: integration requires a separate explicitly approved issue, human
false-confidence evaluation, plan inspection/confirmation and execution-time
revalidation of the exact graph, snapshot and scope.
