# Authorized v1f attempt: native controls passed; diagnostic blocked

**INCONCLUSIVE_REVISE. Two genuine Qwen completion requests, zero semantic
diagnostic requests, zero model-generated RDF executions.** Both native sampling
controls completed. A shared adapter configuration check then stopped Qwen before
the first diagnostic request. Gemma was authorized but not launched after this
integrity failure. Neither model was retried. Keep #83 open and #75 integration
disabled; v1g remains unauthorized. No human-review campaign was performed.

The attempt used `main` after merged PR #90, commit
`ae2785d82f849e1a00b7a0c72ae73fc25c235774`, the original v1f revision-2
[registration](../issue-83-native-one-hop-v1f-diagnostic/preregistration.json),
and its exact restored freeze. The user explicitly authorized the two presented
commands with “I authorize them!” before execution. The authorization and every
earlier failed host receipt are retained in [evidence.tar.gz](evidence.tar.gz).
[campaign.json](campaign.json) records the current authorization and stop reason.

## Actual model evidence

| Qwen sampling control | Original response | Native GBNF | Rust preview | Tokens | Elapsed ms |
|---|---|---|---|---:|---:|
| Unconstrained | `{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control","forbidden":true}` | Reject | Reject, `invalid_contract` | 26 | 10329.388 |
| Constrained | `{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control"}` | Accept | Accept, `model_unsupported` | 21 | 3896.969 |

These are the registered adversarial grammar controls, not interpretations of
the evaluation questions. Both pass their control expectations: unconstrained
generation follows the forbidden-field instruction; constrained generation
omits the forbidden field. Native template bytes and token IDs match the pinned
tokenizer on both requests. Original response bytes, base64 and SHA-256 identities
are in [sampling-controls.json](sampling-controls.json); the archive retains raw
SSE, prompts, native tokens, completion requests, validator stdout/stderr, native
timings, server logs and all resource receipts without editing the run.

The authoritative host check at **2026-10-20 18:47:52 UTC** passed after asset
hashing: load/CPU 0.18994 (maximum 0.75), swap 0 MiB (maximum 1024), free memory
90% (minimum 40), disk 58.996 GiB (minimum 32), maximum process CPU 22.2%
(maximum 150), no competing model processes, registered M1 Pro/32 GiB/arm64,
AC power and no thermal/performance warnings. Model startup took 8578.018 ms.
The sampled process-tree peak was 10919200 KiB (10.413 GiB), from 104 samples;
the monitor reported no errors. Samples can miss peaks and double-count shared
pages; they are run peaks, not case peaks. OS caches were not evicted.

## Precise blocker

The fatal receipt is `ValueError: Adapter configuration changed`, on oracle
`repeat-0` / `eva-01`, before a diagnostic completion request or trusted catalog
preview. The row is retained as `fatal_failure`, with
`generation_attempted: false`; the other 35 Qwen rows remain unattempted.

The registered command executes `tools/native_one_hop.py` as `__main__` and
selects v1f in `main()`. Its diagnostic helper imports `native_one_hop` by name,
creating another module instance whose `CONFIG` defaults to v1c. Consequently
`native_one_hop_diagnostic.observe()` checks the v1f freeze against v1c
configuration and the unchanged integrity guard rejects it. Relevant source:
[default and guard](../../tools/native_one_hop.py#L27),
[diagnostic import](../../tools/native_one_hop_diagnostic.py#L8),
[observation check](../../tools/native_one_hop_diagnostic.py#L47), and
[CLI selection](../../tools/native_one_hop.py#L705).

[module-blocker.json](module-blocker.json) records a model-free reproduction:
the separately loaded CLI namespace passes the frozen verification with v1f,
while the diagnostic helper's named import reproduces exactly the observed
error with its v1c default. It loads no model and issues no completion or RDF
request. Source hashes and the actual v1f Rust binary still match registration.
This is a module configuration failure, not changed assets or semantic model
failure. The shared failure prevented launching Gemma. Nothing was patched,
resealed, rebuilt or rerun to bypass it.

## Semantic findings and limits

- **Observed semantic failures:** none measured. The failure above is an adapter
  integrity failure before diagnostic generation, not a wrong interpretation.
- **Successful interpretations:** none measured. Successful sampling enforcement
  and Rust abstention preview do not establish question understanding.
- **Missing vocabulary:** the unchanged frozen BM25-v1 diagnostic contexts lack
  the reference predicate for `eva-02` and `eva-07`; their start and graph IDs are
  present. These are source/packet observations, not observed model failures.
  No missing IDs were restored. All eight non-repetition reference-candidate
  observations per condition are unattempted; reference vocabulary is not
  semantic truth.
- **Unresolved ambiguities:** the original source audit flags the Campus identity
  collision, “every stored label” versus explicit `rdfs:label`, general location
  wording, and the absent graph-0 Q33 / graph-1 Finland identity link. Original
  predicate descriptions are empty; P17/P131/P856 meanings are not established
  by IDs, local names or adjacency. This remains AI investigator analysis, not
  independent validation or newly observed model behavior.

The unchanged [machine analysis](analysis.json) and
[failure matrix](failure-matrix.md) preserve all **72 unattempted diagnostic
observations**, with null semantic numerators and zero measured denominators.
The two sampling controls are outside that denominator. Qwen has a fatal row
without a generation attempt. The existing analyzer fills an omitted Gemma run
from its historical baseline and labels it `authorization_absent`; that label
describes the immutable baseline, **not current authorization**. The current
reason is shared integrity failure after explicit authorization, as recorded in
`campaign.json`. No missing outcome is scored as correct or incorrect. Exposed
AI-authored references are not independently validated truth. There is no model
ranking, semantic GO, causal comparison or product-readiness claim.

## Model-free reproduction

Use a fresh checkout with the pinned offline Python dependencies and retained
Rust binary. Do not extract over an existing freeze or attempt. No native model
assets are needed for replay or analysis. The registered Rust binary must have
SHA-256 `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.

```sh
mkdir -p artifacts/issue83-v1f-restored
tar -xzf reports/issue-83-native-one-hop-v1f-diagnostic/evidence.tar.gz -C artifacts/issue83-v1f-restored
tar -xzf reports/issue-83-v1f-authorized-attempt-20261020/evidence.tar.gz -C artifacts
.venv/bin/python tools/native_one_hop.py --variant v1f-diagnostic replay --freeze artifacts/issue83-v1f-restored/freeze --run artifacts/issue83-v1f-qwen35
.venv/bin/python tools/analyze_v1f.py --run artifacts/issue83-v1f-qwen35 --out artifacts/issue83-v1f-reanalysis
```

The configuration failure can be reproduced separately without inference:

```sh
.venv/bin/python - <<'PY'
import importlib.util, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import native_one_hop_diagnostic as diagnostic
spec = importlib.util.spec_from_file_location('v1f_cli_probe', 'tools/native_one_hop.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
cli.CONFIG = cli.ROOT / 'configs/native-one-hop-v1f-diagnostic.json'
freeze = Path('artifacts/issue83-v1f-restored/freeze')
cli.verify_freeze(freeze)
assert cli is not diagnostic.a
try:
    diagnostic.a.verify_freeze(freeze)
except ValueError as error:
    assert str(error) == 'Adapter configuration changed'
else:
    raise AssertionError('Expected the registered module configuration mismatch')
print('Reproduced the blocker without inference or RDF execution')
PY
```

Replay independently passed both original raw responses through Rust without
repair or reserialization. The existing v1f analyzer completed successfully.
Both reproduction blocks also passed in a fresh isolated checkout using the
retained pinned binary; regenerated analyzer JSON and Markdown matched byte for
byte. All six existing analyzer regression tests passed without model loading.
See [reproduction.log](reproduction.log) and [analyzer-tests.log](analyzer-tests.log).
[verification.json](verification.json) records checks and exact outcomes;
[evidence-files.json](evidence-files.json) inventories every archived file and
[checksums.json](checksums.json) binds this report. Historical registrations,
evidence and all 801 registered historical file hashes remain unchanged.

No inference retry, Gemma launch, v1g run, RDF execution, #75 integration,
resource-threshold change, asset download, host-process interruption or reboot
was performed. No new freeze or experimental variant was created.
