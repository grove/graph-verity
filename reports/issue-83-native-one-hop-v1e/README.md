# #83 v1e: preregistered semantic reliability experiment

The [protocol](../../docs/native-one-hop-v1e.md), config, fixtures and source will
be committed and frozen before any model inference. The current user request
explicitly opts into one offline, fresh-host-gated attempt per pinned model,
with Rust preview only. Existing v1/v1b/v1c/v1d and #48/#72–#76 evidence is unchanged.

The [pre-inference audit](failure-audit.json) binds the actual v1d diagnostics.
The new interpretation separates plan/status repeatability from JSON/rationale
bytes, keeps reference scores separate from genuine label ambiguity, and adds
source-form language and explicit malicious-label probes. No independently
unseen evaluation or query execution is authorized.
