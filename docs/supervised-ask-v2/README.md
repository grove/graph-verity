# Supervised Ask v2 — INCONCLUSIVE_REVISE

Model-free vertical slice; refs #71, #75 and #83. Base is merged PR #105,
`e7d5dbfe3f2a80e14b08df7c2d10693fd2eb0ae9`.

The separately versioned localhost UI reuses the existing exact single-use
approval and Rust execution bridge. New synthetic saved fixtures show Norwegian
and English forward/reverse questions, multiple values, a typed date, genuine
alias ambiguity (from the disclosed synthetic overlay), missing vocabulary,
unsupported counts, wrong-but-executable interpretation and empty results.
Source triples, graph, snapshot, source/license and original term metadata remain
visible. No live draft is connected to execution.

- [Demonstration and boundaries](../supervised-ask-v2.md)
- [Fresh review protocol, metrics and packages](../../examples/nl-ask-v2/review/protocol.md)
- [All ten compiler incompatibilities](compiler-assessment.md) and [exact requests/rejections](compiler-assessment.json)
- Validation and preservation receipts are added after the complete run below.

Human evidence: **0 independent reviewers, 0 users, 0 observations**. All human
fields and fresh-system outputs remain pending. Fixture tests are engineering
checks, not natural-language accuracy or usability evidence. #83 remains open;
#75 live integration remains disabled. No model inference, model assets, sealed
holdout, historical modification, compiler relaxation, issue closure or merge.

## Validation record

All commands use `.venv/bin/python` where Python is needed. Full output from
focused attempts and the complete model-free pipeline is retained in the adjacent
validation log archive with SHA-256 inventory. Sandbox socket errors, failed
attempts, corrections and reruns are included rather than overwritten.

1. `REQUIRE_FIND_BROWSER=1 .venv/bin/python -m unittest discover -s tools -p test_supervised_ask.py -v`
   First sandbox attempt: all nine HTTP tests failed on denied listening sockets.
   Second host attempt: seven failures and one browser error from incorrectly
   reserializing Python JSON for the byte-canonical Rust neighborhood replay API.
   Correction: always rebuild the packet in Rust and compare the full server-held
   packet before resolution; no canonical or source validation is weakened.
   Third host attempt: all nine tests passed, including Chrome.
2. `ASK_SCREENSHOT=.../artifacts/supervised-ask-v2/review.png REQUIRE_FIND_BROWSER=1 .venv/bin/python -m unittest discover -s tools -p test_supervised_ask.py -v`
   This check passed 11 tests. A fifth focused run after plain-language explanations, desktop/mobile layout checks, the wrong-direction cancellation test and material relocation passed all 12 tests (26.308 seconds).
3. `cargo test --locked --offline -p verity_core --test nl_ask --test ask`
   Focused core contract and exact-plan validation.
4. `.venv/bin/python tools/assess_ask_compiler.py > docs/supervised-ask-v2/compiler-assessment.json`
   Preview only; asserts the ten cases and unchanged rejection categories. The
   initial assessment assertion expected only range errors; inspection found two
   observed-class errors, now separately recorded. No compiler behavior changed.
5. `REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py`
   First full run on `98e2e9ba09975493126f0a1c017407ae441f55a5`: 346 current
   Python tests completed in 548.553 seconds; 345 passed and one frozen-directory
   guard errored because new files were added under `reports/` and `studies/`.
   All new workflow tests passed. No historical bytes had changed. Only the new
   materials were moved to this documentation directory and the v2 demo review
   directory. The unchanged eight-test native configuration suite then passed.
   The complete pipeline is rerun on the final committed implementation with
   the same deadlines and required browsers.

See the final machine receipt for exact statuses, counts, command arguments and
hashes. Inference and human evaluation are intentionally unperformed.

The new material locations deliberately keep the existing broad frozen-directory
assertion intact. No test runner, historical assertion or historical source file
is changed. The new report and review kit live beside the separately versioned
demo rather than reopening a historical registration's protected directories.
