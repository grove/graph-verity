# Real-document Ask evaluation

This is an operator intake and model-free evaluation procedure for a new
document collection. The repository's three-file bilingual native development
fixture is historical test material, not a real-document evaluation corpus.
Do not copy its questions or results into this evaluation.

## Choose sources

Select 5–10 useful Markdown or plain-text documents that you want Graph Verity
to answer questions about. Include English and Norwegian Bokmål when the
selected material supports both, and choose documents with varied structure and
some topic overlap. Use only files you are authorized to process. Record each
source's origin and the license or permission that covers local indexing and
display; an unclear license is not eligible. Do not use private records, sealed
holdouts, unapproved connected-account data, or documents copied from unrelated
experiments.

The manifest has no origin-URL field. Keep a private intake note for each source
with its title, original URL or owner/source reference, author or organization,
license evidence, selection scope, and the local file's path and SHA-256.

The current intake accepts regular, non-symlink `.md` and `.txt` files encoded
as valid UTF-8. It preserves exact original UTF-8 byte spans. It does not parse
PDF, HTML, scanned pages, or OCR output. For those formats, first obtain a
separate source-owner-approved text export that preserves provenance; do not
present a converted text span as an original PDF/HTML citation.

Keep the source files, manifest, index, question set, and run output in an
operator-controlled private directory. The existing limits are 32 documents,
512 KiB per source, 30,000 chunks, and a 64 MiB index. Choose one explicit scope
name and use it on every build and evaluation command.

## Pin the collection

Create a private directory with a `documents/` subdirectory. Put only the
selected source files there. Copy the manifest shape below to `sources.json`,
replace every placeholder, then calculate each digest from the exact source
bytes. These placeholder values are deliberately invalid and must never be
used as source facts or licenses.

```json
{
  "version": 1,
  "documents": [
    {
      "id": "replace-with-stable-id",
      "path": "documents/replace-with-file.md",
      "sha256": "sha256:<replace-with-64-lowercase-hex-digits>",
      "language": "en",
      "license": "<owner-verified-license-or-permission>",
      "scope": "owner-selected"
    }
  ]
}
```

Use one record per selected file. `path` is relative to the manifest directory;
`language` is `en`, `nb`, `no`, or `nn`; `license` records the actual source
license/permission; and `scope` must exactly match the command's `--scope`.
Keep the original source and its recorded SHA-256 unchanged during a run. On
macOS, calculate a digest with:

```sh
shasum -a 256 /private/path/to/collection/documents/source.md
```

Build the existing BM25 index once the manifest and hashes are complete:

```sh
python3 tools/document_rag.py build \
  --manifest /private/path/to/collection/sources.json \
  --index /private/path/to/collection/index.json \
  --scope owner-selected
```

The manifest and source list are the operator's explicit selection. The index
does not discover or authorize additional files.

## Review questions without inventing an answer key

Copy [`document-rag-evaluation-questions.csv`](document-rag-evaluation-questions.csv)
to the same private directory and fill one row per owner-selected question.
Create roughly 10–20 questions when the corpus supports them; do not force a
language split or a label that the sources cannot justify. Include supported
direct questions, paraphrases, exact terms/identifiers, later-document facts,
overlapping passages, and—where the sources support the judgment—unsupported,
ambiguous, conflicting, incomplete, instruction-like, or synthesis/counting
questions.

`source_expectation` and `human_relevance_judgment` use
`OWNER_REVIEW_REQUIRED`, `SUPPORTED_BY_SOURCE`,
`UNSUPPORTED_BY_SELECTED_SOURCES`, `AMBIGUOUS`, `CONFLICTING`, or `UNKNOWN`.
Leave the expectation blank until reviewed; the run records it as
`OWNER_REVIEW_REQUIRED`. A reviewed source expectation needs
`expectation_reviewer`; a human relevance judgment needs `human_reviewer`. Add
`expected_document_id` and, when known, `expected_citation_id` only after
verifying them against selected source bytes. An agent-authored reference is
not independent human gold. Keep human judgments, reviewer identity, and notes
distinct from machine retrieval output.

## Run source-only evaluation

The command below reuses the existing Local Document Ask and BM25 code. It does
not read a model registration, send a request, execute graph operations, or
write evaluation artifacts itself; it prints one JSONL result per question.
Use private paths and a fresh output filename:

```sh
umask 077
set -C
python3 tools/evaluate_document_rag.py \
  --manifest /private/path/to/collection/sources.json \
  --index /private/path/to/collection/index.json \
  --scope owner-selected \
  --questions /private/path/to/collection/questions.csv \
  > /private/path/to/collection/run.jsonl
git rev-parse HEAD > /private/path/to/collection/code-revision.txt
```

The result records the manifest/index digests, scope, ranked passages, BM25
scores labeled as not probabilities, exact source-span checks, clipping,
grounding-risk classification, source-only status/reason, and
`native_inference_status: NOT_RUN`. Expected-document presence is computed only
when a reviewer supplied its document ID; exact expected-passage presence
requires its citation ID. `answer_supported`, `useful_to_answer`,
`failure_category`, and absent human relevance judgments remain null for review.
The script records results; it does not decide semantic relevance, answer
correctness, or usefulness.

For a spot check, the existing CLI also supports a single question without any
generation option:

```sh
python3 tools/local_cited_generation.py \
  --manifest /private/path/to/collection/sources.json \
  --index /private/path/to/collection/index.json \
  --scope owner-selected --language nb \
  --question "<owner-selected question>"
```

## Read the results

Count questions evaluated, owner-reviewed supported cases, cases whose expected
passage appeared in the BM25 top three, and source-only results by reason. Count
a refusal as a correct safe abstention only after review confirms the evidence
or risk condition justified withholding. Show each denominator and keep missing
human labels out of precision/accuracy claims. A verified `d:` citation proves
source-byte provenance only; it does not prove the passage answers the question.
A no-match is not proof that a fact is absent. A source-only refusal is not a
failure unless reviewed evidence shows the gate withheld a clearly supported
case.

After the run, review real failures before proposing one engineering change:
retrieval miss, ranking failure, overly conservative gate, unsafe acceptance,
citation/provenance failure, usability problem, or genuinely unsupported
request. Record unresolved cases as uncertain. Keep this dataset and report
separate from historical native development runs and their receipts.
