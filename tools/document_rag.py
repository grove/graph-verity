#!/usr/bin/env python3
"""#119: Explicitly scoped, source-pinned document BM25; no model or graph execution.

A small standard-library CLI. Indexes are local operator-owned artifacts, not
authorization tokens. A caller must supply the original manifest and scope on
every operation, and current source bytes are checked before results are shown.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

VERSION = "document-bm25-v1"
MAX_MANIFEST = 64 * 1024
MAX_SOURCE = 512 * 1024
MAX_DOCUMENTS = 32
MAX_INDEX = 64 * 1024 * 1024
MAX_CHUNKS = 30000
CHUNK_BYTES = 1024
OVERLAP_BYTES = 128
MAX_QUERY = 4096
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
WORD = re.compile(r"\S+", re.UNICODE)
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
LANGUAGES = {"en", "no", "nb", "nn"}


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def serialized(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def limited_file(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("A regular, non-symlink file is required")
    with path.open("rb") as source:
        contents = source.read(limit + 1)
    if len(contents) > limit:
        raise ValueError("File exceeds the configured limit")
    return contents


def tokens(value: str) -> list[str]:
    return [m.group().casefold() for m in TOKEN.finditer(value)]


def keys(value, expected: set[str], description: str):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Invalid " + description)


def source_path(folder: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("Invalid document path")
    pure = PurePosixPath(relative)
    if (pure.is_absolute() or not pure.parts or
            any(part in (".", "..") for part in pure.parts) or
            pure.suffix.lower() not in (".md", ".txt")):
        raise ValueError("Only relative Markdown/text paths are supported")
    target = folder
    for part in pure.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("Symlinked document paths are not accepted")
    if not target.resolve(strict=True).is_relative_to(folder.resolve(strict=True)):
        raise ValueError("Document must remain under manifest directory")
    return target


def load_sources(manifest_path: Path, scope: str):
    if not IDENT.fullmatch(scope):
        raise ValueError("Explicit, valid --scope required")
    manifest_path = manifest_path.resolve(strict=False)
    raw = limited_file(manifest_path, MAX_MANIFEST)
    payload = json.loads(raw)
    keys(payload, {"version", "documents"}, "source manifest")
    if payload["version"] != 1 or not isinstance(payload["documents"], list):
        raise ValueError("Unsupported manifest version")
    if not (1 <= len(payload["documents"]) <= MAX_DOCUMENTS):
        raise ValueError("Document manifest is empty or too large")

    seen_ids, seen_paths, selected = set(), set(), []
    for record in payload["documents"]:
        keys(record, {"id", "path", "sha256", "language", "license", "scope"},
             "document record")
        doc_id, relative = record["id"], record["path"]
        if not isinstance(doc_id, str) or not IDENT.fullmatch(doc_id) or doc_id in seen_ids:
            raise ValueError("Invalid or duplicate document ID")
        if not isinstance(relative, str) or relative in seen_paths:
            raise ValueError("Duplicate or invalid document path")
        seen_ids.add(doc_id)
        seen_paths.add(relative)
        if (not isinstance(record["sha256"], str) or
                not DIGEST.fullmatch(record["sha256"])):
            raise ValueError("Each source must be pinned to a SHA-256 digest")
        if record["language"] not in LANGUAGES:
            raise ValueError("Only declared Norwegian/English text is supported")
        if (not isinstance(record["license"], str) or
                not 1 <= len(record["license"]) <= 128 or
                not isinstance(record["scope"], str) or
                not IDENT.fullmatch(record["scope"])):
            raise ValueError("Every document needs an explicit license and scope")
        if record["scope"] != scope:
            continue  # Never open or embed non-selected documents.
        target = source_path(manifest_path.parent, relative)
        raw_document = limited_file(target, MAX_SOURCE)
        if sha(raw_document) != record["sha256"]:
            raise ValueError("Source changed: rebuild only after explicitly repinning")
        text = raw_document.decode("utf-8", errors="strict")
        if "\x00" in text:
            raise ValueError("NUL/binary source is unsupported")
        selected.append((dict(record), raw_document, text))
    if not selected:
        raise ValueError("No documents explicitly authorized for the selected scope")
    selected.sort(key=lambda x: x[0]["id"])
    return sha(raw), selected


def passage_id(record: dict, start: int, end: int) -> str:
    value = f'{VERSION}\0{record["id"]}\0{record["sha256"]}\0{start}\0{end}'
    return "d:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def chunks_for(record: dict, original: bytes, text: str):
    # Compute exact UTF-8 byte offsets in one left-to-right pass.
    words = []
    cursor_char = cursor_byte = 0
    for match in WORD.finditer(text):
        cursor_byte += len(text[cursor_char:match.start()].encode("utf-8"))
        start = cursor_byte
        cursor_byte += len(match.group().encode("utf-8"))
        words.append((start, cursor_byte))
        cursor_char = match.end()
    result = []
    first = 0
    while first < len(words):
        stop = first
        while stop < len(words) and words[stop][1] - words[first][0] <= CHUNK_BYTES:
            stop += 1
        if stop == first:
            raise ValueError("A source token exceeds the chunk byte budget")
        start, end = words[first][0], words[stop - 1][1]
        excerpt = original[start:end].decode("utf-8")
        frequency = Counter(tokens(excerpt))
        result.append({
            "citation_id": passage_id(record, start, end),
            "document_id": record["id"], "source": record["path"],
            "version_digest": record["sha256"], "language": record["language"],
            "license": record["license"], "scope": record["scope"],
            "span": {"start_byte": start, "end_byte": end},
            "text": excerpt, "tf": dict(sorted(frequency.items())),
            "length": sum(frequency.values()),
        })
        if stop == len(words):
            break
        # Retain at most OVERLAP_BYTES of prior whole words. Always progress.
        next_first = stop
        while (next_first > first + 1 and
               words[stop - 1][1] - words[next_first - 1][0] <= OVERLAP_BYTES):
            next_first -= 1
        first = next_first
    return result


def make_index(manifest_path: Path, scope: str):
    manifest_digest, sources = load_sources(manifest_path, scope)
    chunks = []
    for record, original, text in sources:
        chunks.extend(chunks_for(record, original, text))
        if len(chunks) > MAX_CHUNKS:
            raise ValueError("Chunk limit exceeded")
    if not chunks:
        raise ValueError("No searchable source passages")
    payload = {
        "version": VERSION, "manifest_sha256": manifest_digest, "scope": scope,
        "documents": [{k: r[k] for k in ("id", "path", "sha256", "language",
                                         "license", "scope")} for r, _, _ in sources],
        "chunks": chunks, "parameters": {"k1": 1.2, "b": 0.75,
                                         "chunk_bytes": CHUNK_BYTES,
                                         "overlap_bytes": OVERLAP_BYTES},
    }
    return {"index_sha256": sha(serialized(payload)), "payload": payload}


def write_index(path: Path, index: dict, manifest_path: Path):
    path = path.absolute()
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Index destination must be a regular file")
    if path.resolve(strict=False) == manifest_path.resolve(strict=False):
        raise ValueError("Index cannot overwrite its source manifest")
    # Never silently replace a source/other file or a different-scope index.
    if path.exists():
        try:
            previous = json.loads(limited_file(path, MAX_INDEX))
            if (not isinstance(previous, dict) or
                    not isinstance(previous.get("payload"), dict) or
                    previous["payload"].get("version") != VERSION or
                    previous["payload"].get("scope") != index["payload"]["scope"] or
                    previous.get("index_sha256") != sha(serialized(previous["payload"]))):
                raise ValueError("Index identity mismatch")
        except (ValueError, UnicodeError, OSError, TypeError,
                json.JSONDecodeError) as error:
            raise ValueError("Refuse to overwrite a non-index or modified file") from error
    data = serialized(index) + b"\n"
    if len(data) > MAX_INDEX:
        raise ValueError("Index exceeds size limit")
    parent = path.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("Index parent must be an existing directory")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix=".verity-index-",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_index(manifest_path: Path, index_path: Path, scope: str):
    raw = limited_file(index_path, MAX_INDEX)
    index = json.loads(raw)
    keys(index, {"index_sha256", "payload"}, "index envelope")
    payload = index["payload"]
    keys(payload, {"version", "manifest_sha256", "scope", "documents",
                   "chunks", "parameters"}, "index payload")
    if (index["index_sha256"] != sha(serialized(payload)) or
            payload["version"] != VERSION or payload["scope"] != scope or
            payload["parameters"] != {"k1": 1.2, "b": 0.75,
                                       "chunk_bytes": CHUNK_BYTES,
                                       "overlap_bytes": OVERLAP_BYTES}):
        raise ValueError("Unrecognized or modified index")
    manifest_digest, sources = load_sources(manifest_path, scope)
    if payload["manifest_sha256"] != manifest_digest:
        raise ValueError("Stale manifest/index; rebuild after authorized changes")
    if (payload["documents"] != [record for record, _, _ in sources] or
            not isinstance(payload["chunks"], list) or
            not 1 <= len(payload["chunks"]) <= MAX_CHUNKS):
        raise ValueError("Index documents do not match the selected sources")
    by_id = {record["id"]: (record, source) for record, source, _ in sources}
    seen = set()
    for chunk in payload["chunks"]:
        if not isinstance(chunk, dict):
            raise ValueError("Invalid indexed passage")
        doc_id = chunk.get("document_id")
        if doc_id not in by_id:
            raise ValueError("Index contains unapproved document")
        record, source = by_id[doc_id]
        span = chunk.get("span")
        if not isinstance(span, dict):
            raise ValueError("Invalid source span")
        start, end = span.get("start_byte"), span.get("end_byte")
        if (type(start) is not int or type(end) is not int or
                not 0 <= start < end <= len(source)):
            raise ValueError("Indexed source offset is invalid")
        excerpt = source[start:end].decode("utf-8")
        identity = (doc_id, start, end)
        frequency = Counter(tokens(excerpt))
        if (identity in seen or excerpt != chunk.get("text") or
                chunk.get("citation_id") != passage_id(record, start, end) or
                chunk.get("source") != record["path"] or
                chunk.get("version_digest") != record["sha256"] or
                chunk.get("scope") != scope or
                chunk.get("language") != record["language"] or
                chunk.get("license") != record["license"] or
                chunk.get("tf") != dict(frequency) or
                chunk.get("length") != sum(frequency.values())):
            raise ValueError("Stored passage cannot be verified against original bytes")
        seen.add(identity)
    return index


def evidence(chunk: dict) -> dict:
    # Do not expose ranking-only postings in generation-facing evidence.
    return {k: chunk[k] for k in (
        "citation_id", "document_id", "source", "version_digest",
        "language", "license", "scope", "span", "text"
    )}


def search_index(index: dict, query: str, limit: int = 5):
    if (not isinstance(query, str) or not query.strip() or
            len(query.encode("utf-8")) > MAX_QUERY or
            type(limit) is not int or not 1 <= limit <= 20):
        raise ValueError("Invalid query or result limit")
    query_terms = tuple(sorted(set(tokens(query))))
    if not query_terms:
        raise ValueError("Query contains no searchable terms")
    chunks = index["payload"]["chunks"]
    count = len(chunks)
    avg_length = sum(c["length"] for c in chunks) / count
    doc_frequency = Counter()
    for chunk in chunks:
        doc_frequency.update(chunk["tf"].keys())
    scored = []
    for chunk in chunks:
        score = 0.0
        for term in query_terms:
            tf = chunk["tf"].get(term, 0)
            if not tf:
                continue
            df = doc_frequency[term]
            idf = math.log1p((count - df + 0.5) / (df + 0.5))
            normalizer = 1.2 * (0.25 + 0.75 * chunk["length"] / max(avg_length, 1))
            score += idf * (tf * 2.2) / (tf + normalizer)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["document_id"],
                                  pair[1]["span"]["start_byte"]))
    return {
        "version": VERSION, "retriever": "bm25-only",
        "index_sha256": index["index_sha256"], "scope": index["payload"]["scope"],
        "query": query, "status": "matches" if scored else "no_match",
        "matches": len(scored), "truncated": len(scored) > limit,
        "hits": [dict(evidence(chunk), score=round(score, 8),
                      score_kind="bm25_not_confidence")
                 for score, chunk in scored[:limit]],
    }


def cite(index: dict, citation_id: str):
    if not isinstance(citation_id, str):
        raise ValueError("Invalid citation")
    hits = [chunk for chunk in index["payload"]["chunks"]
            if chunk["citation_id"] == citation_id]
    if len(hits) != 1:
        raise ValueError("Citation not found in current authorized index")
    return {"version": VERSION, "index_sha256": index["index_sha256"],
            "evidence": evidence(hits[0])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "search", "cite"):
        cmd = commands.add_parser(command)
        cmd.add_argument("--manifest", required=True, type=Path)
        cmd.add_argument("--index", required=True, type=Path)
        cmd.add_argument("--scope", required=True)
        if command == "search":
            cmd.add_argument("--query", required=True)
            cmd.add_argument("--limit", type=int, default=5)
        if command == "cite":
            cmd.add_argument("--citation-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            indexed = make_index(args.manifest, args.scope)
            # Prevent accidental clobbering of source files.
            paths = [args.manifest.resolve(strict=True)]
            paths.extend(source_path(args.manifest.parent, doc["path"]).resolve(strict=True)
                         for doc in indexed["payload"]["documents"])
            if args.index.resolve(strict=False) in paths:
                raise ValueError("Index cannot overwrite an authorized source")
            write_index(args.index, indexed, args.manifest)
            result = {"version": VERSION, "scope": args.scope,
                      "index_sha256": indexed["index_sha256"],
                      "documents": len(indexed["payload"]["documents"]),
                      "chunks": len(indexed["payload"]["chunks"])}
        else:
            indexed = load_index(args.manifest, args.index, args.scope)
            result = (search_index(indexed, args.query, args.limit)
                      if args.command == "search" else cite(indexed, args.citation_id))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    except (ValueError, OSError, UnicodeError, TypeError, KeyError,
            json.JSONDecodeError) as error:
        parser.exit(2, "document-rag: " + str(error) + "\n")


if __name__ == "__main__":
    main()
