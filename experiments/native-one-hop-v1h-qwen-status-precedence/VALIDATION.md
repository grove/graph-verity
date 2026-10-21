# Model-free validation receipt

Decision **INCONCLUSIVE_REVISE**. Zero inference attempts, retries or
model-generated RDF executions. Keep #83 open, #75 integration disabled and
independent human semantic review deferred.

The complete pipeline passed on committed candidate `fffd94b65e7f523ab86a52e6bc5a23b023782401`
in an isolated checkout. Later changes are these model-free receipts/logs only;
none of the 83 registered source inputs changed.

- All 39 pipeline checks passed, including 304 current Python tests (seven new
  ablation regressions), 15 frozen pilot tests and 100 Rust tests, required
  headless browsers, format/Clippy, source canaries, reference and historical
  replays, deterministic rebuild and final clean-tree verification. No skips.
- All 12 native GBNF accept/reject controls passed without loading a model.
- Independent pinned-tokenizer recount matches every frozen prompt byte and token
  ID. Each semantic prompt adds exactly 30 input tokens, both sampling controls
  are unchanged, and the largest columnar prompt is 14,049 + 512 = 14,561 < 16,384.
- All 801 historical hashes, 76 original parent source hashes, 83 new source hashes
  and 942 retained original files from merged #96/main verify. Original Qwen and
  Gemma analyses reproduce byte for byte. All 74 Qwen and 70 Gemma original-byte
  Rust previews replay, with zero RDF execution.
- Fresh pinned checkpoint/Q4/runtime/tokenizer/template/license hashing matches
  the original registered assets. No download, conversion, rebuild or weight
  loading occurred during asset verification. The original registered binary
  remains `16744c50a0b1e89eca6374696e6004ca9782bff4ed59834a7e5ad97485f4b2db`.

The first full pipeline attempt inside the sandbox ran 304 tests but failed
with eight failures and 44 errors caused by denied loopback socket binding and
process inspection (EPERM). The unchanged complete pipeline was rerun with host
execution permissions and passed. Both attempts' full logs are retained in
[validation-logs.tar.gz](validation-logs.tar.gz), with per-file hashes in
[validation-logs-files.json](validation-logs-files.json). This is a validation
repeat, with zero inference attempts.

The first unpublished, unrun registration is preserved under
[superseded-registration-1](superseded-registration-1/reason.json). Its whitespace
assertion was corrected before the final registration. All 83 original source
hashes verify against its own source commit; prompts, contexts, grammars, packets,
schedule and token receipts are identical to the final version. No historical
experiment was resealed.

[validation.json](validation.json) records command status, timing and exact
revision; [verification.json](verification.json) lists all 39 checks.
[preservation.json](preservation.json) binds original retained files;
[asset-verification.json](asset-verification.json) binds asset verification;
[token-budgets.json](token-budgets.json) lists every exact budget;
[prerun-state.json](prerun-state.json) retains all 38 unattempted observations.
The fresh output directory and the final freeze/model no-retry ledger entry
remain absent.

The separately proposed Qwen command is in [README.md](README.md). It requires
fresh explicit authorization naming this registration, revision, Qwen, the
38-request schedule, no retries and the exact output. No current host-readiness
claim is made. Fresh native parity and the original 1024 MiB swap gate still
apply. Model-free tests establish contract/source preservation and Rust safety;
future status, clarification, candidate and direction behavior remains unmeasured.
Independent source-meaning and human semantic judgments remain unresolved.
