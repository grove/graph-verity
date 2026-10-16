# Handoff: first authorized local parser experiment (#7)

Historical pre-integration handoff. The authorized development implementation and
current measurement protocol are now in [local-parser-experiment.md](local-parser-experiment.md).
The no-inference statements below describe the earlier pre-LLM milestone.

No inference backend, model weights, hosted inference, embeddings or grammar-constrained generation has been installed or run by this pre-LLM implementation. `SemanticParser::propose(&ParserRequest) -> Result<Vec<u8>>` and strict `ParserResponse` decoding are the integration boundary. `FixtureParser` is exact replay, not a language parser.

## Next engineering task after explicit authorization

Implement one bounded local llama.cpp adapter, initially using the approved development split and authorized fixed vocabulary. Return raw proposal JSON, not SPARQL. Keep all version/snapshot/scope/catalog/type/complexity validation in Rust after decoding. Treat labels and descriptions as quoted untrusted data; never permit them to expand tools, graph scope or execution capabilities.

Pin the model file and license, quantization, tokenizer/chat template, runtime commit, grammar, prompts, IR schema and compiler. `FutureLocalConfig` already has paths/hashes/thread/context/output/deadline fields but is not a loader or validated runtime configuration. Add configuration validation, cancellation, output bounds and actual backend identity. Change `PlanOrigin` and report attribution explicitly: the current pipeline records fixture origin; a real backend must never masquerade as a fixture, and fixture success must never masquerade as model accuracy.

Export the specific response schema from `verity schema`, compile it to the runtime's supported grammar subset and test that exact runtime/grammar combination. A generated JSON schema is not proof that constrained decoding works. The upstream [llama.cpp schema conversion implementation](https://github.com/ggml-org/llama.cpp/blob/master/common/json-schema-to-grammar.cpp) is a compatibility reference; select and pin an actual revision during integration. Give the model an explicit output contract as well as a grammar, and retain independent Rust rejection of invalid output.

Add positive and negative grammar probes, malformed/truncated outputs, changed scopes, unrecognized identifiers, wrong-but-valid operators, malicious RDF labels and exact-fixture-vs-model attribution regressions. Measure generation separately and extend full end-to-end timing/model metadata before applying model gates. The existing evaluator shares result scoring but its current timing excludes generation and its component-level semantic reporting needs expansion for a decision-quality run.

## Hardware and model assumptions, not measurements

The project proposes beginning around a 1.5-billion-parameter quantized instruction model. No particular model or checkpoint is selected or endorsed here. At a nominal four bits per parameter, 1.5 billion parameters alone imply about 0.75 GB of raw weight payload; quantization metadata, unquantized tensors, runtime buffers, tokenizer and KV cache add to this. This arithmetic is not a RAM requirement or a latency prediction.

The proposed experimental budget is CPU-only, four threads, 16 GiB system RAM, at most 8 GiB whole-process peak RSS, 10 seconds warm end-to-end p95 and 30 seconds cold first answer. These are unapproved limits in `configs/phase-0-gates.proposed.json`, not demonstrated feasibility. Record the actual CPU, OS, available RAM and context/output sizes before approval. The 128 KiB serialized catalog cap is not a token budget; measure tokenizer-specific context size and select a bounded authorized vocabulary without consulting hidden gold.

## Human and measurement gates

A local development smoke experiment can start after explicit authorization and review of the implementation. A feasibility decision additionally requires independent gold review, a genuinely locked test set, approved numerical thresholds and target hardware. Do not rebrand the templated candidate pool as an independent holdout. Cross-country Wikidata examples do not satisfy a cross-ontology claim. Run a real second-ontology or documented temporal transfer evaluation separately.

Model latency, RAM, Norwegian semantic accuracy, actual abstention, prompt-injection robustness and grammar enforcement are all **pending**, not zero or assumed passing. A successful SPARQL run still proves neither user intent nor real-world truth.
