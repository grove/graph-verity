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
partition still fails verification. Existing frozen-only exclusions are retained.

Each command retains its 600-second deadline; the workflow retains its 20-minute
job limit. The combined stage is split rather than given a larger timeout. All
Rust, source, exact approval and inference boundaries are unchanged. Five added
unit tests cover partition completeness, default/history behavior, failure handling,
and byte-exact partial timeout logs (including empty output). The driver now
records the timed-out command with `returncode: null` and `timed_out: true` before
failing, so CI artifacts retain the last observed tests on a future timeout.

The runner correction changes these four current verification files:
`tools/run_python_tests.py`, `tools/verify_pre_llm.py`,
`tools/test_run_python_tests.py`, and `tools/test_verify_pre_llm.py`.
The unchanged v1g fingerprint test also pins those files, so it now runs in a
source export of the original PR #105 baseline, using the same isolation pattern
as the existing pilot/Ask history replays. The complete current v1g release tree
must match that export, and every other registered input still has its original
current-file hash check. The three previously corrected source files and these
four verifier files are checked by the original test against their registered
source identities. No hash is refreshed. The current v1g registration test file
itself remains byte-for-byte unchanged, preserving its later r3 fingerprint too.

The first 185-test partition exposed this guard in 183.073 seconds. The source
export replay and all eight r3 configuration checks pass. No historical
registration, frozen source snapshot, raw response, reference, evidence archive
or old validation receipt is edited or rehashed. The original 1,378-file
preservation receipt describes its earlier validated commit; this follow-up
changes only the four current verification files listed above.

Focused checks:

```sh
.venv/bin/python -m unittest discover -s tools -p test_run_python_tests.py -v
.venv/bin/python -m unittest discover -s tools -p test_verify_pre_llm.py -v
```

These passed 4 and 7 tests. Full verification uses the same required command:

```sh
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

The split pipeline has 41 checks: 351 current tests, 15 original pilot tests,
one original v1g fingerprint test, the Ask/vocabulary replays, Rust tests and
mandatory browsers. This retains all 347 original current regressions and adds
five runner/logging tests, with the one fingerprint check isolated in history. Full-run results must be observed;
the old success receipt is not a claim that this new candidate has passed CI.
Live model integration remains disabled; decision stays INCONCLUSIVE_REVISE.
