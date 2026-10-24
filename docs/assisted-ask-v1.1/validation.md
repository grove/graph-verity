# Assisted Ask v1.1 proposal: baseline validation

**INCONCLUSIVE_REVISE. No language-filter implementation or release.**
The [proposal](../assisted-ask-v1.1-proposal.md) follows the task's mandatory stop
because the required Rust changes conflict with current historical source pins.
These receipts validate existing v1 behavior and that blocker; they do not
validate English/Bokmål/Nynorsk filtered UI journeys.

## Existing product checks

Tests use `main` commit `294fcf0589b02dca1ff497b3cfe37689551e4986` in the disposable
checkout `/private/tmp/graph-verity-language-verify`, with its own offline Rust
build. The original workspace's `target/debug/verity` is never rebuilt. An extra
HTTP/Chrome probe uses a stable copy of the disposable binary so later builds
cannot replace it while a server is running. No production source, UI, tests or
historical verifier is modified.

- **10/10 focused Python tests passed** on the unchanged second run, including
  **eight real Chrome sessions**: normal bilingual journeys, expiry, empty,
  row clipping, evidence clipping, hostile labels, timeout and failure.
- **17/17 focused Rust tests passed**: eight core Confirmed Ask, five NL Ask,
  four CLI Ask. Existing original approval tests are unchanged.
- An additional **real Chrome session** asserts exact RDF lexical values,
  language tags, datatypes, rendered answer headings and subject/predicate/
  object/graph witnesses for P856 and P1448 in both interface languages.
- Four additional actual HTTP/Rust preview → approval → result journeys record
  exact original values, complete source evidence and licensing. Replayed
  approvals fail. A question saying “only English names” leaves P1448 unfiltered
  in both interface languages. [Observed previews and receipts](observations.json)
  contain no session credentials or review tokens.
- Real Rust rejects a language-only filter object and Ask version 2. Equality
  against an empty English literal returns zero rows despite the stored English
  name. This is a contract-feasibility check, not a filtered feature result.

The existing negative checks cover unknown/numeric entities and predicates,
graph/scope/snapshot/direction substitution, arbitrary filter/query fields,
missing authorization, Host/Origin/tab checks, changed source/config/policy/
scope/executable, missing/edited/replayed/expired/cancelled approvals, new tabs,
disconnect, timeout and execution failure. Successful journeys use actual Rust.
Timeout/failure paths inject exceptions at the execution boundary rather than
claiming observed Rust deadline exhaustion. Empty/hostile fixtures and reduced
row/evidence policies are isolated temporary copies, never production data.

The baseline rejects **every** added result-language field, including supported
future choices. No filter-mutation, filtered-clipping or filtered-browser success
is claimed. Those cases are specified as future gates in the proposal. Browser
automation is engineering verification; independent human usability remains
unmeasured.

## Retained failed attempt and deadlines

Focused run 1 passed all eight browser sessions but one Python test errored:
the Rust test build ran concurrently and briefly replaced the same disposable
`target/debug/verity` used by the server, causing `FileNotFoundError`. This was a
validation orchestration mistake. After builds completed, the same Python source,
tests and policies passed unchanged in focused run 2. The extra probe uses a
separate stable binary. The original registered executable was unaffected.

Both logs are retained. Existing browser subprocess deadlines remain 120 seconds,
Chrome startup 15 seconds and UI waits 20 seconds; Rust child calls retain their
45-second deadline. The standalone exact-value browser run has a 120-second
outer deadline. Focused shell/Rust runs had no added outer timeout. The complete
pipeline retains its original 600-second deadline per command. No deadline,
authorization or row/evidence limit is increased to pass a check.

## Complete pipeline and preservation

The [machine receipt](validation.json), [preservation receipt](preservation.json)
and [retained logs](validation-logs.tar.gz) record the final outcomes. The full
pipeline command is:

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

**41/41 pipeline command checks passed** on the unchanged product baseline: **181 + 201 current Python tests**, zero skips, all required browsers, **100 Rust tests**, formatting/Clippy, original historical replays, source/scope canaries, byte rebuild, schema/catalog parity, 38 Wikidata and 35 transfer-development executable oracles, and manual/fixture approval/evidence checks. The locked-holdout sentinel was rejected before access. No full-pipeline failure or deadline increase. The PR adds documentation/receipts only; these results do not imply that v1.1 is implemented.

All task-baseline tracked files and the original registered binary are compared
against a pre-work SHA-256/mtime/mode inventory. The unchanged original native
checker verifies registration/freeze pins, raw model evidence, attempt accounting,
prompt/token parity, scoring/replay, audits and preservation without inference.
The 1,481 native raw files are independently compared against the original
published inventory, including bytes, membership, mtime and mode. Its 201-file
freeze is compared to the original committed archive.

Registered model/runtime identities are verified through their original retained
identity receipts and archive checksums. Physical model weights are not opened,
loaded or rehashed. No new model or native-runtime invocation, download, consumed
registration retry, sealed holdout access, #75 integration, merge or issue closure
is performed. No historical source facts, model results or hash expectations are
rewritten or resealed. Only new proposal documentation and fresh receipts are
published.
