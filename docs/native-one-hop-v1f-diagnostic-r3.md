# v1f diagnostic revision 3: adapter identity repair

Decision: **INCONCLUSIVE_REVISE**. This revision repairs engineering orchestration
only. No inference is authorized or performed by this repair, registration, or CI.
Issue #83 stays open. There is no #75 integration or model-generated RDF execution.

PR #91 preserved a valid fail-closed stop before semantic generation. Running
`native_one_hop.py` as `__main__` selected v1f in that namespace, while the helper's
`import native_one_hop as a` loaded a second namespace with the v1c default. Its
`verify_freeze()` correctly rejected the v1f configuration. Import-based tests
shared a namespace and therefore missed the direct-script failure.

The direct-script entry point now delegates to the named module's `main()`. All
CLI work, including variant selection, runs in the same module the helper imports.
Imported `main()` uses that module too. There is no module alias, global-state
synchronization, fallback, or change to the helper, integrity guards, runtime,
resource thresholds, source authorization, packet construction or Rust preview.
The default remains v1c; explicit historical variant selections still work with
new test freezes. A historical freeze continues to require its original source.

`v1f-diagnostic-r3` / `issue83-native-cpu-v1f-diagnostic-r3` is a separately
registered successor. Its configuration differs from v1f only in the version.
It retains the exact oracle and frozen BM25-v1 conditions, exposed questions,
source-language renderer, prompt, GBNF, numeric IDs, AI source audit, host gates,
sampling settings, 36 diagnostic observations plus two sampling controls per model,
zero retries and preview-only authority. It does not change v1g or substitute its
neighborhood condition. Completion still cannot yield semantic GO.

## Registration and restoration

The model-free [registration](../experiments/native-one-hop-v1f-diagnostic-r3/registration.json)
binds the corrected adapter and unchanged helper, full effective configuration,
frozen contexts/packets, source inputs, current Rust binary identity, historical
pinned runtime/model/tokenizer/license identities and environment. The sibling
archive contains the freeze and its checksums. Model assets are neither packaged
nor loaded. Their registered identities are inherited pins, not a claim of fresh
asset availability or host readiness. The unchanged `assets()` path must rehash
and verify them before any future model loading, followed by a fresh host gate.

Model-free restoration and verification on the registered host:

```sh
mkdir -p artifacts/v1f-diagnostic-r3
tar -xzf experiments/native-one-hop-v1f-diagnostic-r3/freeze.tar.gz -C artifacts/v1f-diagnostic-r3
PYTHONPATH=tools .venv/bin/python - <<'PY'
from pathlib import Path
import native_one_hop as a
a.CONFIG = a.ROOT / 'configs/native-one-hop-v1f-diagnostic-r3.json'
a.verify_freeze(Path('artifacts/v1f-diagnostic-r3'))
PY
```

A different binary, source input, configuration or packet must fail verification.
On another platform, inspect archive hashes without executing the registered
binary. Do not reseal this registration to accommodate a rebuild. Create a new
named registration before generation if an identity or experimental setting
changes. Commit the registration and archive before requesting inference.

The original v1f registration, superseded registration, PR #91 attempt, all
reports/raw bytes/hashes/failures/denominators and v1g registrations are immutable.
Their historical source checks use the exact original Git blobs, as earlier
v1d/v1e tests already do. Current-code regressions separately verify the repaired
entry point and reject changed frozen sources, packets, configurations and binaries.
Historical replay requires the original source and registered executable; the
corrected source must reject an old v1f or v1g execution freeze.

## Verification and next experiment

The regression suite first reproduces the original namespace split with archived
source. It checks direct subprocess freezing, direct-script dispatch, imported
CLI dispatch, actual helper verification and trusted Rust preview with a fake
transport stop, historical configurations, tampering, operator opt-in, CI denial
and zero execution authority. Existing synthetic full schedules retain original
raw-byte Rust replay and fatal resource/authorization/integrity checks.

See the [repair report](../experiments/native-one-hop-v1f-diagnostic-r3/README.md)
for exact commands and results. All checks are model-free.

After this PR, the engineering repair can be considered for a **separately
authorized, host-gated** semantic smoke under this successor registration.
Authorization must name the revision, model(s), fresh output destinations and
bounded schedule. Fresh source/binary/asset verification and passing original
host gates remain mandatory. Retain both native sampling controls and all
NO/EN forward/reverse, ambiguity, scope and unsupported observations, including
failures and unattempted denominators. This is a new attempt, never a retry or
rewrite of the historical attempt. Do not infer semantic quality, model accuracy
or product readiness from the engineering repair.
