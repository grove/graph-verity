# Core verification record

The deterministic core at `d865047f083f64ef7ec2d5ac261c3631c977b52e` passed GitHub Actions
[run 38899769248](https://github.com/grove/graph-verity/actions/runs/38899769248), on Ubuntu 24.04
x86-64 with the pinned Rust toolchain and committed lockfile. Formatting, Clippy with warnings
as errors, the complete workspace test suite and the CLI smoke query all succeeded.

This is an actual remote CI run, not a claim that Rust ran in the authoring environment.
The regression suite exercises real Oxigraph execution, not mocked database responses.
The branch-only formatting/lockfile helper has now been removed; normal CI is read-only.

This run does not test real model generation, constrained decoding, Norwegian interpretation,
production isolation or target-device performance. Real-data benchmark verification is recorded
separately. No issue requiring human review or model measurements is complete merely because
this core run passes.
