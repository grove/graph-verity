#!/usr/bin/env python3
"""Capture once; deterministic offline verification never refreshes upstream data."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import rdflib
from rdflib import Graph, Literal, RDF, RDFS, SKOS, URIRef

rdflib.NORMALIZE_LITERALS = False
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "wikidata"
WD = "http://www.wikidata.org/entity/"
DIRECT = "http://www.wikidata.org/prop/direct/"
WB = "http://wikiba.se/ontology#"
GRAPHS = {
    "urn:graph-verity:wikidata:development": ["Q585", "Q26793", "Q25804", "Q25416", "Q20"],
    "urn:graph-verity:wikidata:transfer": ["Q1754", "Q34"],
}
EXPECTED_NAMES = {"Q585": "Oslo", "Q26793": "Bergen", "Q25804": "Trondheim", "Q25416": "Stavanger", "Q20": "Norway", "Q1754": "Stockholm", "Q34": "Sweden"}
PROPERTIES = ["P17", "P36", "P31", "P1082", "P571", "P131"]
LANGUAGES = ["en", "nb", "nn"]
AGENT = "GraphVerity/0.1 (bounded reproducible RDF research; https://github.com/grove/graph-verity)"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_id(data: bytes) -> str:
    return "sha256:" + sha(b"graph-verity-snapshot-v1\0nquads\0" + data)


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch(url: str) -> tuple[bytes, str]:
    for attempt in range(3):
        request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip", "Accept": "text/turtle,application/json;q=0.9"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(16 * 1024 * 1024 + 1)
                if response.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                if len(data) > 16 * 1024 * 1024:
                    raise ValueError("Source exceeds 16 MiB")
                time.sleep(1)
                return data, response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            delay = error.headers.get("Retry-After", "10")
            time.sleep(min(120, max(5, int(delay) if delay.isdigit() else 10)))
    raise RuntimeError("Unreachable retry state")


def capture_source(entity: str, revision: int | None = None) -> dict:
    metadata_url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity}.json"
    if revision is None:
        raw, _ = fetch(metadata_url)
        metadata = json.loads(raw)["entities"][entity]
        revision = int(metadata["lastrevid"])
        english_name = metadata.get("labels", {}).get("en", {}).get("value")
        if entity in EXPECTED_NAMES and english_name != EXPECTED_NAMES[entity]:
            raise ValueError(f"Entity identity requires review: {entity}: {english_name}")
    else:
        english_name = None
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity}.ttl?flavor=dump&revision={revision}"
    raw, content_type = fetch(url)
    parsed = Graph().parse(data=raw, format="turtle")
    if not any(parsed.triples((URIRef(WD + entity), None, None))):
        raise ValueError(f"Source has no subject {entity}")
    versions = {int(v) for predicate in (URIRef("http://schema.org/version"), URIRef("https://schema.org/version")) for v in parsed.objects(None, predicate)}
    if versions and revision not in versions:
        raise ValueError("RDF response does not match requested revision")
    path = DATA / "raw" / f"{entity}-{revision}.ttl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"entity": entity, "revision": revision, "english_label_at_capture": english_name,
            "url": url, "metadata_lookup_url": metadata_url, "file": str(path.relative_to(ROOT)),
            "sha256": sha(raw), "bytes": len(raw), "content_type": content_type,
            "license": "CC0-1.0", "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}


def source_graph(source: dict) -> Graph:
    path = (ROOT / source["file"]).resolve()
    if not path.is_relative_to(DATA.resolve()):
        raise ValueError("Manifest source path escapes dataset directory")
    raw = path.read_bytes()
    if sha(raw) != source["sha256"]:
        raise ValueError(f"Source checksum mismatch: {path}")
    return Graph().parse(data=raw, format="turtle")


def build(manifest: dict, temporal: bool = False) -> bytes:
    by_id = {source["entity"]: source for source in manifest["sources"]}
    if temporal:
        if not manifest.get("previous_oslo_source"):
            raise ValueError("No previous revision was captured")
        by_id["Q585"] = manifest["previous_oslo_source"]
    parsed = {entity: source_graph(source) for entity, source in by_id.items()}
    selected_predicates = {URIRef(DIRECT + p) for p in manifest["properties"]} | {RDF.type}
    lines = set()
    for graph_name, items in manifest["graphs"].items():
        selected = Graph()
        for entity in items + manifest["properties"]:
            subject = URIRef(WD + entity)
            for s, predicate, obj in parsed[entity].triples((subject, None, None)):
                keep = predicate in selected_predicates
                if entity.startswith("P"):
                    keep = predicate in (RDF.type, URIRef(WB + "directClaim"))
                if predicate in (RDFS.label, SKOS.altLabel):
                    keep = isinstance(obj, Literal) and obj.language in manifest["languages"]
                if keep:
                    if not isinstance(obj, (URIRef, Literal)):
                        raise ValueError("Unexpected blank node in selected direct-statement subset")
                    selected.add((s, predicate, obj))
        # The public N-Triples serializer handles escaping, including embedded newlines.
        for line in selected.serialize(format="nt").splitlines():
            if not line.strip():
                continue
            if not line.endswith(" ."):
                raise ValueError("Unexpected N-Triples serializer output")
            lines.add(line[:-2] + f" <{graph_name}> .")
    return ("\n".join(sorted(lines)) + "\n").encode("utf-8")


def capture() -> None:
    path = DATA / "manifest.json"
    if path.exists():
        verify()
        print("Existing capture retained; no upstream refresh")
        return
    manifest = {"format_version": 1, "source": "Wikidata structured entity RDF",
        "license": "CC0-1.0", "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
        "access_documentation": "https://www.wikidata.org/wiki/Wikidata:Data_access",
        "graphs": GRAPHS, "properties": PROPERTIES, "languages": LANGUAGES,
        "graph_names_origin": "assigned_by_importer_not_upstream_named_graphs",
        "source_semantics": "selected direct best-ranked statements; qualifiers/references remain in raw RDF but are not queried",
        "missing_information": "open_world; absence is not falsity", "sources": []}
    for entity in sorted(set(sum(GRAPHS.values(), []) + PROPERTIES)):
        print(f"Capturing {entity}", flush=True)
        manifest["sources"].append(capture_source(entity))
    oslo = next(source for source in manifest["sources"] if source["entity"] == "Q585")
    try:
        parameters = urllib.parse.urlencode({"action": "query", "prop": "revisions", "revids": oslo["revision"], "rvprop": "ids", "format": "json", "formatversion": 2, "maxlag": 5})
        raw, _ = fetch("https://www.wikidata.org/w/api.php?" + parameters)
        parent = json.loads(raw)["query"]["pages"][0]["revisions"][0]["parentid"]
        manifest["previous_oslo_source"] = capture_source("Q585", int(parent))
        manifest["temporal_note"] = "Previous Oslo entity revision with other entities unchanged; NOT a globally coherent historical snapshot"
    except (OSError, ValueError, KeyError, IndexError) as error:
        manifest["temporal_capture_blocker"] = str(error)
    snapshot = build(manifest)
    (DATA / "snapshot.nq").write_bytes(snapshot)
    manifest["snapshot"] = {"file": "data/wikidata/snapshot.nq", "format": "nquads", "sha256": sha(snapshot), "snapshot_id": snapshot_id(snapshot), "quads": len(snapshot.splitlines())}
    if manifest.get("previous_oslo_source"):
        previous = build(manifest, temporal=True)
        (DATA / "previous-oslo.nq").write_bytes(previous)
        manifest["previous_snapshot"] = {"file": "data/wikidata/previous-oslo.nq", "sha256": sha(previous), "snapshot_id": snapshot_id(previous), "selected_data_changed": previous != snapshot}
    dump(path, manifest)
    verify()


def verify() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    snapshot = build(manifest)
    expected = manifest["snapshot"]
    if snapshot != (ROOT / expected["file"]).read_bytes() or sha(snapshot) != expected["sha256"] or snapshot_id(snapshot) != expected["snapshot_id"]:
        raise ValueError("Derived snapshot is not byte-reproducible")
    if manifest.get("previous_snapshot"):
        previous = build(manifest, temporal=True)
        expected_previous = manifest["previous_snapshot"]
        if previous != (ROOT / expected_previous["file"]).read_bytes() or sha(previous) != expected_previous["sha256"]:
            raise ValueError("Previous revision subset mismatch")
    print(json.dumps({"verified": True, "sources": len(manifest["sources"]), **expected}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["capture", "verify", "rebuild"])
    parser.add_argument("output", nargs="?")
    args = parser.parse_args()
    if args.command == "capture":
        capture()
    elif args.command == "verify":
        verify()
    else:
        if not args.output:
            parser.error("rebuild requires an explicit output path")
        manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
        Path(args.output).write_bytes(build(manifest))


if __name__ == "__main__":
    main()
