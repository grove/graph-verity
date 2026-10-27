# #119 — Source-pinned local document BM25 (v1)

**Status:** First model-free implementation slice, not completed vector RAG or natural-language generation.

This adds a separate, standard-library CLI at **tools/document_rag.py**, leaving Rust/Oxigraph execution, Confirmed Ask, frozen code and model evidence untouched. Results are real source-document passage evidence, **not** RDF facts, generated answers or claims of human relevance.

## Operator workflow

1. Choose legally usable, local UTF-8 Markdown/plain-text source files and write an **explicit, trusted** source manifest with each document ID, relative path, original-file SHA-256, language, license and access scope.
2. **build** selects only the requested scope, verifies the source bytes, and writes a local, persistent BM25 index with deterministic UTF-8 byte offsets.
3. **search** requires the manifest, index and scope again; checks original sources and index integrity before returning bounded, source-citable passages.
4. **cite** resolves a returned citation ID back to verified original source text.

Example manifest at /path/to/collection/sources.json (replace the placeholder with the actual 64-character lowercase hex SHA-256):

~~~json
{
  "version": 1,
  "documents": [
    {
      "id": "policy-no",
      "path": "documents/policy-no.md",
      "sha256": "sha256:<64-lowercase-hex-characters>",
      "language": "nb",
      "license": "operator-verified-license",
      "scope": "public"
    }
  ]
}
~~~

The example hash is **not** valid input until replaced. The documents directory must live under the manifest directory. To calculate a digest on macOS, run:

~~~sh
shasum -a 256 /path/to/collection/documents/policy-no.md
~~~

Example CLI calls from the repository root:

~~~sh
python3 tools/document_rag.py build \
  --manifest /path/to/collection/sources.json \
  --index /path/to/private/document-index.json --scope public

python3 tools/document_rag.py search \
  --manifest /path/to/collection/sources.json \
  --index /path/to/private/document-index.json --scope public \
  --query "Hva er søknadsfristen?" --limit 5

python3 tools/document_rag.py cite \
  --manifest /path/to/collection/sources.json \
  --index /path/to/private/document-index.json --scope public \
  --citation-id "d:<real-ID-from-a-search-hit>"
~~~

A hit includes citation_id, document_id, source-relative path,
version_digest, language, license, scope, span.start_byte, span.end_byte,
exact text, a BM25 score and an explicit not-confidence score label.
Citations are stable for an unchanged source digest, document ID and
byte range. The source passage is exactly original_bytes[start:end]
decoded as UTF-8, with an exclusive end offset.

Chunking uses whole words, up to 1024 UTF-8 bytes per chunk and up to
128 bytes of whole-word overlap. Query ranking uses conventional BM25
(k1=1.2, b=0.75), with deterministic score and ID/offset tie-breaking.
Local Ask removes a small set of English function words before BM25 scoring;
Norwegian questions keep their original terms. The CLI `search` command accepts
optional `--language en` to use the same English filtering. If a query contains
only filtered words, it keeps the original terms.
A no-match is only **no lexical match**, never proof of real-world absence.

## Authorization and boundaries

- The manifest is a **trusted operator selection**, not an automatic source-discovery step. Scope must be named on every operation. Out-of-scope documents are not read, indexed or returned.
- This CLI does **not** implement user authentication, multiuser permissions or security boundaries against people who can modify the manifest and index. Keep private documents, their manifest and index in OS-protected directories.
- Files must be regular, non-symlink UTF-8 text/Markdown under the manifest directory. Parent traversal, absolute paths, NUL/binary inputs, missing provenance fields, bad SHA-256 and stale sources fail closed.
- Limits: 32 manifest records, 512 KiB per selected source, 30,000 chunks, 64 MiB index, 4096 UTF-8 query bytes, and 20 hits. Newly written indexes use mode 0600.
- Every search/citation reverifies original source bytes. Source revisions require deliberate repinning and explicit reindexing; do not silently refresh or reuse stale citations.
- No PDF/HTML/OCR parser, vector backend, embeddings, graph approval, browser integration, model inference or answer generator is introduced.
- The existing EmbeddingGemma and Qwen studies are historical graph research, **not** validation of this new document RAG baseline. No independent human relevance scores are claimed.

## Model-free tests

~~~sh
python3 -m unittest discover -s tools -p test_document_rag.py -v
~~~

The existing Python suite auto-discovers tools/test_document_rag.py.
Tests cover Norwegian/English lexical retrieval, original UTF-8 byte
citations, source mutation, stale or forged index rejection, scope isolation,
symlink/traversal controls, bounded queries and CLI citation round trips.

## Follow-on work

This is the **first focused PR for #119**, not the completion of all #119.
Next: present the passages in the shared Ask UI and benchmark a separately
authorized EmbeddingGemma vector/hybrid variant against the lexical baseline.
#118 then supplies actual local evidence-grounded generation after a distinct
owner authorization and host/resource checks.

Preserve all frozen experiments and **INCONCLUSIVE_REVISE**.
