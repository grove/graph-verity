# Historical Phase 0 baseline

This immutable reassessment uses PR #20's preserved public development outputs;
**no model inference was performed to generate this baseline**. The original
[raw reports, hardware receipt and evidence archive](../local-parser-development/README.md)
remain unchanged. The new [JSON summary](summary.json), [readable decision matrix](summary.md)
and [checksum manifest](manifest.json) were generated with implementation commit
`4168a64` from a clean tracked tree.

```sh
.venv/bin/python tools/phase0.py report --out artifacts/phase0/new-baseline
.venv/bin/python tools/phase0.py verify reports/phase-0-baseline/manifest.json --check-inputs
```

Both datasets have 0 strict IR matches (0/38 and 0/35); answer binding agreement is
3/38 and 0/35; correct expected abstentions are 0/8 and 0/5. Historical M1 Pro warm
p95 is 28.06/26.59 seconds, above the proposed 10-second budget. These are AI-reference
agreement measurements, not independent expert semantic accuracy.

Formal decision: **NOT READY**. Thresholds, protocol/sample budgets and deployment CPU
are unapproved; independent expert review, locked evaluation and complete user-facing
false-confidence/disclosure measurements are absent. Individual failed proposal
comparisons remain visible. The separate engineering recommendation is to revise this
configuration and abandon unattended unrestricted Ask with it, retaining exact
resolution/manual typed plans. Full protocol and commands: [issue #8 implementation](../../docs/phase-0-evaluation.md).
