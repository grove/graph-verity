# Proposed status-rule-precedence ablation — not registered or authorized

Decision remains **INCONCLUSIVE_REVISE**; independent human semantic review is
deferred. This document recommends one future factor. It creates no runnable
ablation, prompt, configuration, execution registration or inference authority.
Keep #83 open and #75 integration disabled.

## Measured motivation

In the existing frozen context representation, Qwen classifies unsupported
operations correctly on 2/6 oracle and 4/6 BM25-v1 probes, while preserving
model-origin clarification on all three clarification references in each
condition. Gemma reaches 4/6 oracle and 6/6 completed BM25-v1 unsupported probes,
but only 2/3 clarification references in either condition. Its oracle filter
candidate silently drops filtering, and its multi-hop candidate returns the
first edge of a composition it describes in prose. These need status precedence,
not a richer context representation. Qwen's count/multi-hop clarifications show
the complementary confusion between a forbidden operation and unresolved inputs.

Gemma's unsupported response to the BM25-v1 unclear-relation probe and its claim
that returning multiple resources is unsupported show the risk of blanket
abstention. Both models still fail the reverse plan probes, and source-label
reference/ambiguity disagreement remains unresolved. A status-only change must
not be credited with fixing direction, missing numeric vocabulary, source
meaning, source-table contradictions, or independent semantic truth.

## Minimum future factor

Recommend Qwen first, because its retained oracle unsupported result leaves
four measured status errors and its 3/3 clarification behavior provides a clear
regression guard. This is a research prioritization, not a model ranking. Use the
original Qwen host/resource gates, including 1024 MiB swap; a blocked host must
wait rather than introduce another host change. A future Gemma run would require
its own registration and explicit authority; the used Gemma attempt cannot be
retried through this proposal.

Change only the order/explicit precedence of the existing status rules in a
future prompt:

1. An explicitly requested operation forbidden by the existing one-hop contract
   selects `unsupported` before attempting a partial candidate or asking for
   missing operands. The prohibited-operation set stays exactly as registered.
2. Otherwise, an unresolved or ambiguous start/relation for a supported one-hop
   request selects model-origin `needs_clarification`, using the existing source
   and binding rules. Absence of authorized numeric vocabulary must not be
   repaired by inventing IDs or reclassified as a forbidden operation by default.
3. Emit a candidate only when the original authorized start, predicate, graph,
   direction and projection requirements are satisfied. Supported one-hop
   multi-value results remain supported; Rust rejection is not clarification or
   unsupported classification.

Do not add examples, property meanings, translations, aliases, inferred labels,
gold IDs/directions, additional evidence, or different reverse-direction wording.
Preserve the lossless packet columns and every context value/membership, frozen
oracle and BM25-v1 retrieval, GBNF/JSON contract, numeric bindings, source/private
scope, canaries, Rust preview-only safety, model/Q4/runtime/dependencies, CPU and
generation/resource limits. This isolates status precedence as closely as the
existing exposed diagnostic permits.

## Registration and measurement required before any future execution

A separate append-only registration must identify the exact prompt diff and
hashes, immutable baseline/archive, model/runtime/binary, host gates and output
directory. Recount all 38 scheduled prompts with the pinned tokenizer, retain
exact bytes/token arrays and fit checks, and require fresh native template/token
parity before each generation. Preserve the two native sampling controls and
36-observation schedule, correlated repeat accounting, no retries and no
model-generated RDF execution. A newly presented exact command requires separate
explicit operator authorization after that concrete registration exists.

Primary measurements should be model-origin unsupported classification on the
six forbidden-operation probes, separately for oracle and BM25-v1, guarded by no
loss of the baseline three genuine clarification-reference matches in either
condition. Report the separate four-case AI ambiguity audit without rewriting
the original source-label candidate reference. Retain every partial candidate,
timeout, failure and unattempted observation; no completed-only rate may conceal
an incomplete schedule.

Secondary measurements should retain all five forward/reverse plan fields,
false unsupported/clarification on supported probes, source-bound rationale/table
contradictions with exact witnesses, source sufficiency limits, native controls,
Rust acceptance/rejection, canaries, latency and sampled process-tree RSS. Use
paired completed identities alongside full schedules, keep original references
immutable, and leave human judgments null until independently reviewed. This
small exposed, AI-authored, correlated diagnostic supports a revision decision,
not statistical significance, causal model superiority or semantic GO.
