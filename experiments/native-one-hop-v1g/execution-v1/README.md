# V1g execution registration v1

**INCONCLUSIVE_REVISE. No native inference is authorized or performed.**

This is the model-free execution release for #83, built from merged PR #89
(`721a998e49d9e6f36c65bdd2bfecf1d6166f7b1f`). The original design README,
protocol and registration remain unchanged. Source commit and all code, original
source, reference, prompt/grammar, environment, native asset and Rust binary hashes
are in [execution-registration.json](freeze/execution-registration.json).

The 30 exposed cases have 90 sealed contexts, common presentation rules and exact
#82 packet bytes. Every entity/predicate member maps to its original graph-qualified
numeric ID. All 90 host bindings passed independent Rust preflight and model-free
replay. Frozen BM25-v1 bytes match #74. No gold vocabulary supplementation occurs.
The native runtime, legal source, checkpoint, tokenizer and Q4 identities were
freshly rehashed without loading weights; [assets.json](assets.json) retains the
receipt. The native host must pass a **new** resource gate after future explicit
v1g authorization. No present host-pass claim is made.

[freeze.tar.gz](freeze.tar.gz) contains the complete execution freeze, including
original packets, requests, operator-only fixtures/references, messages, per-context
grammar and source/environment manifest. To materialize the registered bytes:

```sh
tar -xzf experiments/native-one-hop-v1g/execution-v1/freeze.tar.gz -C experiments/native-one-hop-v1g/execution-v1/freeze
.venv/bin/python tools/native_one_hop_v1g.py replay --freeze experiments/native-one-hop-v1g/execution-v1/freeze
```

The registration pins the original binaries byte for byte. A newly compiled binary
on a different path/toolchain/host may differ; portable CI checks archived source
and context identities, then builds its own fresh model-free test freeze. Never
edit this registration to accept changed binaries: retain the pinned binaries or
create a separately committed new execution registration before any inference.
See the [operator guide](../../../docs/native-one-hop-v1g.md) for the preparation,
registration, scoring and authorization boundaries.

[unattempted-score.json](unattempted-score.json) has 184 unattempted diagnostic
observations (92/model), with all model outcome numerators null. Each model's
primary paired comparison has 18 scheduled supported pairs and zero attempted
pairs; the difference is null. Oracle comparisons are separate. Repetitions do
not enter that denominator. This is an executable scoring baseline, not model
evidence or a model ranking. Human review remains pending and is not required for
diagnostic reporting. #83 remains open.

[explicit-predicate-development.tar.gz](explicit-predicate-development.tar.gz)
contains 60 separately generated development questions covering all 17 permitted
graph/predicate identities in forward/reverse wording, with witnessed and empty
paths distinguished. Its [development registration](development-registration.json)
binds the exact questions, contexts, requests, packets, grammar and prompt seal.
It contributes **zero** cases to v1g. It has no native run entry point and no
inference authorization; any future native panel needs its own execution
registration. Typed references are derived only after prompt sealing.

The tests use synthetic transport with actual independent Rust previews. Both
models' 94-request schedules, continuation after known draft rejection, fatal
boundaries, strict byte retention, pairing/missingness, gold-poison independence,
exact packet membership, numeric/graph/role forgery rejection and deterministic
development generation are covered. No model-generated RDF query is executed.
No sealed holdout, #75 integration, threshold relaxation, human-review requirement
or automatic merge is introduced.
