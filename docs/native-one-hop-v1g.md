# V1g execution harness

This implements the unchanged [design](../experiments/native-one-hop-v1g/protocol.json)
for #83. It does not authorize inference. The semantic decision stays
`INCONCLUSIVE_REVISE`, including after a completed diagnostic. No model RDF query
is executed. No holdout, #75 integration, human approval gate, model ranking,
metadata enrichment, or resource-threshold change is introduced.

The primary panel is exactly eva-01 through eva-30 in original order, per
condition: oracle, BM25-v1, neighborhood-v2. Models run serially, qwen35 then
gemma4. Each model has two oracle eva-01 repetitions before the three condition
blocks and two native sampling controls: 92 diagnostic observations and at most
94 completion requests, no retries. A local ledger reserves each model's single
attempt under the shared native adapter lock. Keep the ledger when moving
artifacts; do not reset it to retry a failed campaign.

`tools/native_one_hop_v1g.py` delegates native transport, host gates, tokenizer
and template parity, CPU settings, GBNF validation and process-tree monitoring
to the unchanged v1f adapter. It does not add a historical variant or loosen
strict evaluation. The source-language/usage/collision renderer is identical
in every condition. Only authorized membership varies. Transport packets,
operator resolution/block fixtures and references stay outside all prompts.
The original untrusted language forms, source provenance, local names and
collisions remain visible. Missing vocabulary is never restored from a reference.

The dedicated `v1g_preview` Rust example embeds the original authorized numeric
table and policy, checks graph/IRI/role/ID identity and complete entity/predicate
membership, revalidates original canonical packet bytes independently against
snapshot, policy and discovery index, and binds v2 proposals through
`NeighborhoodContext` and `preview_neighborhood_draft`. Unknown, omitted,
duplicated, substituted or remapped entries fail before decoding even an
abstention. A model candidate on an unresolved/blocked start remains a validator
rejection; it is never reported as model clarification. Packet-integrity failures
are fatal. Known individual draft failures may continue, as in v1f. Resource,
deadline, process, grammar, template/token, source, asset and binary failures stop
later observations. Partial original response bytes are retained and previewed.

Model-free preparation (from the repository root, pinned dependencies installed):

```sh
cargo build --locked --offline -p verity_cli --bin verity --examples
.venv/bin/python -m unittest discover -s tools -p test_native_one_hop_v1g.py -v
.venv/bin/python tools/native_one_hop_v1g.py freeze --freeze artifacts/v1g-new
.venv/bin/python tools/native_one_hop_v1g.py replay --freeze artifacts/v1g-new
.venv/bin/python tools/native_one_hop_v1g.py score --freeze artifacts/v1g-new --out artifacts/v1g-unattempted.json
```

`freeze` never reads references until packet/context/message/grammar bytes have
been sealed. It copies all 60 exact #82 packets and checks BM25 byte equality
with #74. Rust independently checks all 90 contexts before the freeze is sealed.
It records source/config/code/toolchain/environment hashes, both Rust binaries,
original source and references, exact prompt messages and per-context grammar,
and the retained native checkpoint/tokenizer/license/runtime identities.
`replay` authenticates the complete freeze and revalidates all packets without a
model. With `--run DIR`, it checks raw-byte/observation/request/context identity
and independently repeats each diagnostic Rust preview. Scoring reads original
bytes and uses the strict contract; it never repairs a model response.

Commit implementation and docs before creating the final freeze. To create the
separately committed execution registration, hash retained native assets without
loading weights, then register the final freeze (both commands are model-free):

```sh
.venv/bin/python tools/native_one_hop_v1g.py assets --freeze artifacts/v1g-new --out artifacts/v1g-assets.json
.venv/bin/python tools/native_one_hop_v1g.py register --freeze artifacts/v1g-new --assets-receipt artifacts/v1g-assets.json
```

Registration rejects uncommitted source inputs and writes a deterministic sibling
`DIR.tar.gz` containing all frozen bytes. Commit that archive, `checksums.json`
and `execution-registration.json`; other generated files can be omitted from Git.
On another checkout, extract the archive into the same freeze directory before
verification (`tar -xzf DIR.tar.gz -C DIR`). The archive is hash-bound and checked
byte for byte during registration. Registration rejects uncommitted source inputs. Commit the evidence archive and registration before any future generation. The registration is
append-only and deliberately outside the freeze's checksum inventory; it binds
that inventory and the complete freeze manifest. It does not authorize model
loading. Native execution additionally requires a separate explicit v1g operator
authorization, `--allow-inference`, verified assets and a fresh passing original
host gate. CI cannot run inference. The run rejects an uncommitted registration.

After that separate authorization, the operator may invoke `run --freeze DIR
--out NEW_ATTEMPT --model qwen35 --allow-inference`, then the same command for
`gemma4` with a different new attempt directory. Never run either command on the
basis of this implementation request. Native templates/tokens are checked on
every request; runtime-rendered messages and grammar must match sealed bytes.
Actual tokenized prompts are retained at generation because tokenizer execution
belongs to the authorized native phase. Their source templates, tokenizers and
message bytes are bound before generation.

Paired machine-readable analysis:

```sh
.venv/bin/python tools/native_one_hop_v1g.py score --freeze DIR --run QWEN_RUN --run GEMMA_RUN --out NEW_SCORE.json
```

The per-model primary comparison is neighborhood-v2 minus BM25-v1 on the 18
supported cases. Oracle comparisons are separate. Repetitions are excluded.
Each comparison reports raw exact five-field plus model-status agreement and
Rust-accepted/GBNF-valid completed agreement, attempted and completed pair counts,
missing pairs/IDs, discordant counts and the paired difference. An empty
numerator stays null. Raw results may include attempted partial outputs;
accepted comparisons require two completed observations. The full case matrix
reports source vocabulary availability, available-but-reference-disagreed,
unsafe candidate guesses, validator rejection, per-field agreement, original
triple witnesses, literal predicate metadata and bounded rationale contradictions.
Abstentions, direction strata, token/latency and sampled RSS summaries remain
separate from the primary pairs. #82's retained packet budgets, clipping and
retrieval timing are bound as source evidence. Fixed order, cache/time effects,
exposed AI references and source-meaning limits prohibit causal, significance,
pristine-generalization or semantic-readiness claims. P17/P131/P856 do not acquire
natural-language definitions merely because their IDs/edges are available.

The explicit-predicate development panel is generated independently:

```sh
.venv/bin/python tools/explicit_predicate_development.py --out artifacts/explicit-predicate-new
```

For every authorized graph/predicate, it uses lexically sorted original
subject/object witnesses for forward/reverse explicit full-IRI wording. Empty
paths have a distinct `empty_path` kind; literal objects cannot be entity starts.
It applies the same rule to every predicate, builds all three contexts from source
and retrieval alone, seals prompts, then derives typed fields and witnesses.
There is no native run entry point for this panel. It is neither part of the
30-case v1g denominator nor a natural-language or pristine holdout test. Its exact
new questions/requests need separate registration before any future inference.

Run the complete unchanged pre-LLM pipeline from a committed clean checkout:

```sh
.venv/bin/python tools/verify_pre_llm.py
```

The current Python test discovery automatically includes the v1g suite. Synthetic
native transport exercises all 94 requests for both models using actual Rust
previews; native assets are mocked and no model is loaded. Frozen historical
source-fingerprint checks continue to use their existing immutable exports.
