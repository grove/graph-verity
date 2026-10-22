# PR #106 CI timeout correction

The first PR check ([run 39790116170](https://github.com/grove/graph-verity/actions/runs/39790116170))
and push check ([run 39789997230](https://github.com/grove/graph-verity/actions/runs/39789997230))
stopped at the same 600-second `reporting-tests` deadline. That command combined
all current Python tests with the original pilot export, tests, source verification,
rehearsal, rebuild and strict retrieval replay. The uploaded failure receipt has
no completed Python-test count: the old driver discarded `TimeoutExpired`'s partial
stdout/stderr. It does not establish that any particular test assertion failed.
The original local 39-check success and its recorded receipts remain unchanged.

The fix partitions the same sorted current test modules into two disjoint serial
checks, then runs the unchanged pilot replay as its own check. Normal
`tools/run_python_tests.py` still runs the complete current suite and pilot replay.
No tests or imports are silently dropped; regression tests require the two module
sets to have no overlap and to cover the complete original discovery set. A failed
partition still fails verification. Existing frozen-only exclusions are unchanged.

Each command retains its 600-second deadline; the workflow retains its 20-minute
job limit. The combined stage is split rather than given a larger timeout. All
Rust, source, exact approval and inference boundaries are unchanged. Five added
unit tests cover partition completeness, default/history behavior, failure handling,
and byte-exact partial timeout logs (including empty output). The driver now
records the timed-out command with `returncode: null` and `timed_out: true` before
failing, so CI artifacts retain the last observed tests on a future timeout.

The four modified existing files are current verification code and its unit tests:
`tools/run_python_tests.py`, `tools/verify_pre_llm.py`,
`tools/test_run_python_tests.py`, and `tools/test_verify_pre_llm.py`.
No historical registration, frozen source snapshot, raw response, reference,
evidence archive or old validation receipt is edited or rehashed. The original
1,378-file preservation receipt describes its earlier validated commit; this
follow-up deliberately changes these four current verification files.

Focused checks:

```sh
.venv/bin/python -m unittest discover -s tools -p test_run_python_tests.py -v
.venv/bin/python -m unittest discover -s tools -p test_verify_pre_llm.py -v
```

These passed 4 and 7 tests. Full verification uses the same required command:

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

The split pipeline has 41 checks and includes all 352 current tests (347 original
plus the five runner/logging regressions), the original pilot and Ask/vocabulary
replays, Rust tests and mandatory browsers. Full-run results must be observed;
the old success receipt is not a claim that this new candidate has passed CI.
Live model integration remains disabled; decision stays INCONCLUSIVE_REVISE.
