# Local document Ask

Graph Verity's document Ask is a small local browser interface over the existing
document BM25 index. It serves document passages only by default. It does not
query RDF, start a model, download weights, or create or consume an inference
authorization.

## Launch

Build a source index using the existing [document RAG guide](document-rag-v1.md),
then start Ask with the same operator-selected manifest, index and scope:

```sh
python3 tools/local_document_ask.py \
  --manifest "$COLLECTION/sources.json" \
  --index "$COLLECTION/index.json" \
  --scope development
```

For a new operator-selected collection, follow the
[real-document evaluation intake](real-document-evaluation.md) before building
an index.

Open the private session URL printed in the terminal. Keep the terminal open;
press Ctrl-C to stop the local server. The listener binds to `127.0.0.1` by
default. The browser session URL contains a local access credential that stays
valid while the server is running; do not share it.

Choose English or Norwegian Bokmål, enter a question, and select **Ask**. The
interface uses the existing BM25 retriever and shows the original passages it
retrieved. Expand a passage to inspect its document ID, source name, source
language, `d:` citation ID, source digest, license and original UTF-8 byte span.
Document-span `d:` citations are distinct from original RDF-triple `g:`
citations; this page uses document evidence only.

## Read the result

**Sources only — model not invoked** means the page returned retrieved source
passages without presenting them as an answer. No lexical match means only that
the selected scope produced no BM25 match; it does not establish that the fact
is absent. Ambiguous, conflicting, clipped, unsupported or instruction-risk
cases remain source-only, with retrieved passages available for inspection.
Coverage details show whether retrieval was clipped. If a source changes or
becomes unavailable, its old passages and saved answer are withheld.

**Generated — original source quotation and citation verified** appears only
when the page is configured with the exact result and private receipt from an
already completed, separately authorized CLI run. The page rechecks the answer
against the current packet and citation before displaying it. It states the
original citation and limitation: source and citation are verified; independent
semantic correctness is not guaranteed. A checked saved replay is labeled as a
replay and as not invoking a model. Test fixtures are never labeled as native
runs.

## Prepare a local generation request

To inspect a prospective request, start the page with the existing private
runtime registration:

```sh
python3 tools/local_document_ask.py \
  --manifest "$COLLECTION/sources.json" \
  --index "$COLLECTION/index.json" \
  --scope development \
  --runtime-registration "$PRIVATE/runtime-registration.json"
```

Select **Prepare local generated answer**. The page shows the original question,
language, document scope, source passages and citations, exact request body,
packet and request digests, model/runtime identity, host admission, expiration
requirements and registered resource limits. Preparation does not contact the
model, create an approval, set `owner_approved`, or consume an authorization. It
does not start the registered model server.

For an actual run, follow [safe preparation](local-document-rag-native-v1.md#safe-preparation-now-private-source-only-baseline)
and [fresh owner approval and one-shot execution](local-document-rag-native-v1.md#freeze-request-obtain-fresh-owner-approval-then-run-once).
Review the exact packet/request and digests there; only the owner creates a new
approval bound to that request, registration, scope, private ledger and expiry.
Then use the existing CLI:

```sh
umask 077
python3 tools/local_cited_generation.py \
  --manifest "$COLLECTION/sources.json" \
  --index "$COLLECTION/index.json" \
  --scope development \
  --question "$QUESTION" \
  --language "$LANGUAGE" \
  --runtime-registration "$PRIVATE/runtime-registration.json" \
  --run-authorization "$PRIVATE/owner-approval.json" \
  --ledger-dir "$PRIVATE/ledger" \
  --execute-authorized-inference > "$PRIVATE/result.json"
```

The CLI consumes the exact approval once and retains the private receipt; it
does not launch the model server. To inspect that result, set `RUN_DIR` to the
private `view.receipt_directory` value in the result, then restart Ask with
`--checked-result "$PRIVATE/result.json" --checked-receipt "$RUN_DIR/receipt.json"`.
Use absolute, owner-only paths. The browser has no approval or inference action.
A saved replay may be shown without a native receipt, but is labeled as a replay
and is source-checked again.

## Limits

Retrieval is lexical BM25, capped at three passages, and is not exhaustive. The
grounding-risk rules cover specific conflict, ambiguity, incompleteness,
unsupported-question and untrusted-instruction patterns; they do not establish
general semantic entailment. A citation proves that a passage exists at the
recorded source span, not that the passage is true or that an answer is
semantically correct. This first page is document-only; graph execution,
paraphrase retrieval and browser-triggered inference are not part of this
workflow.

The narrow generated-answer path currently checks direct English `what` and
`which` questions and Norwegian `hva`, `hvilken` and `hvilket` questions.
Location, time and person questions remain source-only because term overlap
cannot show that a quoted sentence answers those question types.
