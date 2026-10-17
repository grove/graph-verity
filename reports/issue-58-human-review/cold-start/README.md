# Full research-worker startup — supplemental measurement

This supplement measures fresh processes without changing the original study,
ranking policy, relevance labels or existing capture. It is timing evidence only;
there are no human assessments or new retrieval claims.

The controller starts its monotonic timer immediately before launching a fresh
pinned Python interpreter, then reads and validates the first serialized top-ten
result against the committed capture. This includes interpreter startup, imports,
frozen-input/binary validation, lexical index construction and the first query.
Selective workers additionally verify checkpoint assets, initialize the pinned
Torch runtime, load the model and saved document vectors, and compute the query
embedding. IPC, serialization and controller validation are included. Process exit
and teardown have a separate timer; shutdown is not charged as first-result time.

The preregistered schedule has five exposed probes (HR-01, HR-02, HR-09, HR-19,
HR-20), three paired repetitions each and fixed seed 58: **15 observations per
method, 30 new processes**, run sequentially. Each pair uses the same query,
role, graph, snapshot, candidate universe and fixed ranking policy. Ordering of
cases and methods is randomized before measurement. Each result must reproduce
the saved authorized ranks; failures remain failures, not dropped observations.

These are **process-cold, OS-cached** research-worker measurements. No OS-cache
purging or reboot is performed. Native scheduling and concurrent desktop workload
are uncontrolled; checkpoint verification itself reads the weight files before
model loading. Saved document vectors are reused, so vector rebuilding is excluded.
The baseline is the pinned BM25 research worker, not the shipping CLI executable's
startup. Descriptive p95 with 15 observations is close to the observed maximum and
is not a population guarantee. No cold-start promotion threshold is invented.
The original <=1 s warm p95 / <=4 GiB RSS and human-review gates remain unchanged.

Reproduction requires the pinned model environment and the private capture receipt
created using the existing study's `prepare` command:

```sh
/path/to/pinned/python tools/hybrid_review_cold.py prepare \
  --receipt study-private/hybrid-owner-20261017/capture-receipt.json \
  --out study-private/hybrid-cold/plan.json
# Freeze the plan and code before starting workers:
/path/to/pinned/python tools/hybrid_review_cold.py run --allow-inference \
  --plan study-private/hybrid-cold/plan.json \
  --out study-private/hybrid-cold/results.json
# CI tests use only fake standard-library subprocesses; no model or download:
.venv/bin/python -m unittest discover -s tools -p test_hybrid_review_cold.py -v
```

The public plan excludes private receipt paths. The private plan's SHA-256 links
the report to the actual frozen input. Original runtime/checkpoint/index hashes
remain those of the study and capture receipt. The original frozen kit is not
amended; this is a separately preregistered measurement of exposed cases.

## Executed results

The [plan](protocol.json) and code were committed before the queries. All **30/30**
workers completed; every first result matched the saved authorized snapshot and
ranked identities. [Raw observations and descriptive summaries](results.json)
retain all cases, method order and repetitions. There are **no exclusions or
failed observations** and no human judgments.

| Parent-observed metric | BM25 (15) | Selective hybrid (15) |
|---|---:|---:|
| First-result p50 | 210.17 ms | 6,615.80 ms |
| First-result p95 | 232.65 ms | 9,957.69 ms |
| First-result p99 | 232.65 ms | 9,957.69 ms |
| Process-exit p50 (includes teardown) | 231.73 ms | 7,374.78 ms |
| Process-exit p95 (includes teardown) | 255.11 ms | 10,766.12 ms |

Host/runtime remain Apple M1 Pro / 32 GiB, macOS 26.6.2 arm64, pinned Python
3.14.8 and EmbeddingGemma 2 runtime/checkpoint. The new full-process values must
not be subtracted from the older single 6.994 s in-process observation: timing
boundaries, query mix, cache history, sample size and uncontrolled host load differ.
With n=15, both p95 and p99 are the observed maximum; there is no tail guarantee.

This establishes a startup cost for the declared research setup, not retrieval
usefulness or production readiness. The earlier warm p95 (110.34 ms) and
conservative RSS (1.947 GiB) remain separate observations. **Recommendation stays
defer, BM25 stays default, and actual human review remains pending.**
