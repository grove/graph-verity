# #83 v1d preregistration

This new report is reserved for the separately frozen
[source-usage/alias-collision context variant](../../docs/native-one-hop-v1d.md).
PR #85's reports and all 17 historical generation requests remain unchanged.

Before generation: retain the exact config, source, prompts, grammar, all 60
contexts, source/packet identities, scope/policy, runtime/asset pins, host gates
and scoring rules in a new checksummed freeze. The owner explicitly opted into
one offline CPU smoke attempt per pinned model on 2026-10-19, conditional on
fresh passing host preflight. This authorizes Rust preview only, not RDF query
execution. Full 30-case oracle/retrieval evaluation is not authorized by this run.

Results will be added after the attempts, without changing their frozen inputs.
No model-quality or integration GO is claimed by preregistration itself.
