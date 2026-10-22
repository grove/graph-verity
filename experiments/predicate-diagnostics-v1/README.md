# Predicate meaning and plan construction diagnostics

Refs #83; based on merged #102. Decision **INCONCLUSIVE_REVISE**. Human semantic
review is deferred; #83 remains open and #75 stays disabled. No inference is
authorized or performed by these tools.

PR #101's provenance audit demonstrates retained CC0 property documentation
and exact `wikibase:directClaim` mappings in the Q578326 item archive. PR #102's
four reverse responses still contain no candidate: oracle clarifies twice;
BM25-v1 is unsupported/clarification. Its accepted status objects establish no
reverse construction ability. BM25-v1 eva-07 also has no numeric P131. The #82
neighborhood protocol provides source witnesses and authenticated graph-local
membership, but cannot supply a missing property meaning or select a start.

The separately versioned offline adapter checks registered archive, manifest,
snapshot, catalog, policy, scope and discovery hashes, original license/revision
triples, source-to-importer-graph authorization, exact directClaim mappings and
literal language/datatype. Every one of the 17 permitted graph/predicate pairs
is considered by the same rule. Five direct predicates have four retained
English label/name/description statements each; twelve retain missing metadata.
The existing separate P131 property-page archive is excluded. Item revision
2535539461 is not claimed as a property-page revision. Parsed statement hashes
bind RDF terms; the file hash binds original bytes. Importer graph identity is
retained explicitly, not attributed to upstream Turtle.

No definitions are invented, translated, truncated or selected using question
or reference IDs. Multiple property identities stay explicit. Entity labels,
concept definitions, IRI local names and usage are not promoted to property
definitions. The RDF snapshot, authorization and retrieval remain unchanged.
The new metadata source revision and context packet IDs bind every enriched
context and all source provenance. Neither is presented as the old RDF source
or old packet. A stale packet fails before Rust preview. Metadata cannot expand
the supplied numeric vocabulary or merge the same IRI across graphs.

[protocol.json](protocol.json) freezes two distinct experiments:

* Construction uses all 60 original mechanical explicit-IRI questions with
  source-derived fields and witnesses, original oracle vocabulary and no metadata.
* Meaning uses all 30 original exposed natural-language questions and the retained
  injection control, paired at identical full oracle membership. Only the
  predicate metadata arrays change. The #102 system prompt is reused unchanged.

The single-model registration has 126 requests including two native sampling
controls and two identical construction repeats. Oracle-only avoids another
retrieval factor; BM25-v1 and neighborhood-v2 are unchanged historical baselines,
not arms in this experiment. All source metadata is included uniformly, so
unrelated definitions are present even on negative-control relations. Results
must distinguish predicates with/without newly available meanings. The original
60-question panel archive remains immutable and includes its source-derived
empty paths; an empty path is not an unsupported operation.

Generation inputs are sealed before scoring references or operator fixtures are
loaded. Those fixtures stay outside model inputs. The separate model-free scorer
retains raw bytes, failed/unattempted observations, Rust outcomes, status and all
five fields. A flipped-direction candidate accepted by Rust still fails request
fidelity. Exposed AI references, including the source-label ambiguity tension,
are not human truth. There is no exact-answer or semantic-readiness claim.

Reproduction from the committed preparation revision, with existing local assets:

```sh
.venv/bin/python -m unittest discover -s tools -p 'test_predicate*.py' -v
.venv/bin/python tools/predicate_diagnostics.py prepare --freeze artifacts/predicate-diagnostics-v1
.venv/bin/python tools/predicate_diagnostics.py register --freeze artifacts/predicate-diagnostics-v1
.venv/bin/python tools/predicate_diagnostics.py verify --freeze artifacts/predicate-diagnostics-v1
.venv/bin/python tools/predicate_diagnostics.py score --freeze artifacts/predicate-diagnostics-v1 --out artifacts/predicate-unattempted.json
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

Registration refuses an existing archive. To replay the published freeze, verify
its archive hash, extract to a fresh directory and run `verify`/`score`; do not
register again. The registration pins preparation source bytes, prompts, contexts,
source/packet identities, grammar, exact token arrays, original Rust binaries,
runtime/model/tokenizer identities, resources and scoring before any generation.
The local tokenizer worker loads tokenizer files only, with offline access.
Fresh native parity and host admission cannot be established without separately
authorized model loading and remain mandatory future gates. No inference runner
was added; authorization is not inferred from the registration.

For later model-free scoring, `--observations` accepts a JSON object keyed by
scheduled request ID. Each value has `attempted` (boolean), `failure` (null or
error text), `raw_utf8` (null or original response text) and `packet_id` (the
host packet ID saved beside the original response; null only when unattempted). Missing IDs are
unattempted; partial/failed responses are retained with null semantic outcomes.
Original SSE and native receipts must additionally be archived by the future
authorized runner. This tool invokes only the unchanged Rust preview bridge,
never a model-generated RDF query.
