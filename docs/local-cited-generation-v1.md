# #122 — Local cited document answers

**Status:** model-free implementation and CI. Actual model inference is not authorized, attempted or proven by this PR. Preserve INCONCLUSIVE_REVISE.

## First useful flow

This slice reuses merged #119 document BM25 and #121 source-backed evidence without inventing another retrieval stack.

- An English/Norwegian question is resolved against the current operator-authorized, SHA-256-pinned Markdown/text index.
- The original question, language, document passages and real d: citation IDs form one bounded JSON prompt. Source text is explicitly untrusted data.
- The default command displays original passages and answer=null, without contacting a model.
- A separately approved mode can request one OpenAI-style chat completion from an operator-started **127.0.0.1 llama.cpp server**, then validate the result or fall back to sources. No external model API, download, autonomous graph query or automatic model process launch.
- The first checkable answer family is conservative: a SINGLE model-selected original sentence copied byte-for-byte from a returned document passage, citing that passage. Extra fields, fake citations, incorrect language, paraphrased facts, exhaustive statements, uncertain counts, invalid JSON and ungrounded answers are rejected. A correct citation and quote **do not prove semantic entailment**.

The result is a strict, source-extractive local generation slice, not reliable general Norwegian/English question understanding or human-verified factual quality.

## Source-only command (works without inference)

Prepare a #119 index following [document-rag-v1.md](document-rag-v1.md). Keep source files, index and manifest in an OS-protected operator directory.

    python3 tools/local_cited_generation.py \
      --manifest /private/collection/sources.json \
      --index /private/index.json --scope public \
      --question "Hva er søknadsfristen?" --language nb

The output contains the original kg-rag-evidence-v1 packet and a source-only view. The CLI also accepts a **model-free saved-output replay** option:

    --saved-completion /private/retained-response.json

The strict saved output format looks like this (replace the placeholder citation with an actual returned source citation):

    {
      "version": "local-cited-document-answer-v1",
      "status": "answer",
      "language": "nb",
      "answer": "Søknadsfristen er 1. mai.",
      "citation_id": "d:<real-passage-id>"
    }

A supported abstention has exactly two fields, version and status=abstain. No arbitrary model reasoning or Markdown wrappers.

## Separate owner authorization before any native inference

Actual inference requires a newly selected **small local model**, its specific license, weights, binary, official chat-template/tokenizer compatibility and current host/resource controls. This PR does **not** choose or authorize such a run. Past #83/Qwen/Gemma inference authorizations and consumed ledgers cannot be reused.

For a future owner-approved run only, supply all four deliberate opt-in arguments:

    --runtime-registration /private/run-registration.json
    --run-authorization /private/owner-approval.json
    --ledger-dir /private/inference-ledger
    --execute-authorized-inference

Registration keys are: version=1, backend=llama.cpp-openai-chat-loopback-v1, host=127.0.0.1, port, model_name, absolute model_path and sha256, absolute runtime_path and sha256, system_prompt_sha256, context_tokens (512-8192), max_output_tokens (32-256), timeout_seconds (5-120), seed and temperature=0. All registered local model/runtime file bytes are hashed before the network request.

**Important:** Hashing on-disk files and checking the HTTP model alias does not attest that the active server has loaded those files. The operator must separately confirm server PID and command, tokenizer/template identity, host contention, swap/RAM, CPU/Metal settings and offline-only behavior. This code never starts that server; the owner stops it after the run.

The run authorization must come from a new explicit owner decision and include version=1, unique authorization_id, action=one_shot_local_document_answer, canonical registration_sha256, exact packet_sha256, question_sha256, scope, short UTC expires_utc, host_preflight=operator_verified_quiescent_host and owner_approved=true. A one-use record in an existing private 0700 ledger is created as mode 0600 **before** the model request. Failed, timed-out and rejected runs consume the approval. Do not generate or edit those private authorization files merely because this PR exists.

No model request is made unless the explicit flag, strict registration, approved exact scope/question/source hashes and unused authorization all validate. Local HTTP is fixed to 127.0.0.1 with no redirects/proxy. Model output is bounded, requires a complete stop condition, and must exactly quote a real in-scope document passage. Edits to source files during inference suppress both generated answers **and stale fallback excerpts**.

## CI and evaluation truth

    python3 -m unittest discover -s tools -p test_local_cited_generation.py -v

The tests use genuine source-verified document snippets, deterministic saved responses and an in-process FAKE local HTTP chat server. They cover bilingual citations, private-document isolation, prompt-injection text as data, nonexistent/wrong citations, wrong language, unsupported absolute claims, preflight mismatch, single-use ledger, timeout, source revocation and CLI fallback. **No tests run or simulate model competence.**

Before closing #122: register/freeze one reasonable model/runtime/host authorization; perform actual local NO/EN answers on licensed development text; preserve raw completions, context/token, latency and peak memory receipts; independently evaluate question-answer relevance, citation support and wrong-but-plausible answers against deterministic source display. No GNN, SHACL or automatic graph execution is involved.
