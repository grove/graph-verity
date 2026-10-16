#!/usr/bin/env python3
"""Rebuild/check an immutable, attributed real-data second-ontology RDF snapshot.

Uses only the pinned, checked-in GeoNames-derived CSV subset. Never downloads
or changes upstream data, gold, or reviewer decisions during verification.
"""
from __future__ import annotations
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "worldcities-transfer"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SCHEMA = "https://schema.org/"
XSD_INT = "http://www.w3.org/2001/XMLSchema#integer"
CODES = {"Norway": "NO", "Sweden": "SE", "Denmark": "DK",
         "Finland": "FI", "Iceland": "IS"}

def iri(text: str) -> str:
    return f"<{text}>"

def literal(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)

def read_rows() -> list[dict[str, str]]:
    with (DATA / "source.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if (len(rows) != 328 or len({r["geonameid"] for r in rows}) != 328
            or any(set(r) != {"name", "country", "subcountry", "geonameid"}
                   or not all(r.values()) or r["country"] not in CODES
                   or not r["geonameid"].isdigit() for r in rows)):
        raise ValueError("Frozen Nordic source row membership changed")
    if rows != sorted(rows, key=lambda r: int(r["geonameid"])):
        raise ValueError("Source rows are not canonically ordered")
    return rows

def build(rows: list[dict[str, str]]) -> tuple[bytes, int]:
    lines = []
    seen_countries = set()
    seen_regions = set()
    def quad(s: str, p: str, o: str, g: str):
        lines.append(f"{s} {iri(p)} {o} {g} .")
    for row in rows:
        code = CODES[row["country"]]
        graph = iri(f"urn:graph-verity:worldcities:transfer:{code}")
        country = iri(f"urn:graph-verity:worldcities:country:{code}")
        region = iri("urn:graph-verity:worldcities:admin:"
                     + code + ":" + quote(row["subcountry"], safe="-_.!~*'()"))
        city = iri(f"https://sws.geonames.org/{row['geonameid']}/")
        if code not in seen_countries:
            seen_countries.add(code)
            quad(country, RDF_TYPE, iri(SCHEMA + "Country"), graph)
            quad(country, SCHEMA + "name", literal(row["country"]), graph)
        name = (code, row["subcountry"])
        if name not in seen_regions:
            seen_regions.add(name)
            quad(region, RDF_TYPE, iri(SCHEMA + "AdministrativeArea"), graph)
            quad(region, SCHEMA + "name", literal(row["subcountry"]), graph)
            quad(region, SCHEMA + "containedInPlace", country, graph)
        quad(city, RDF_TYPE, iri(SCHEMA + "City"), graph)
        quad(city, SCHEMA + "name", literal(row["name"]), graph)
        quad(city, SCHEMA + "containedInPlace", region, graph)
        quad(city, SCHEMA + "identifier",
             literal(row["geonameid"]) + "^^" + iri(XSD_INT), graph)
    return ("\n".join(sorted(lines)) + "\n").encode("utf-8"), len(seen_regions)

def verify() -> dict:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    source = (DATA / "source.csv").read_bytes()
    rows = read_rows()
    generated, regions = build(rows)
    snapshot = (DATA / "snapshot.nq").read_bytes()
    info = manifest["extraction"]
    expected = "sha256:" + sha256(
        b"graph-verity-snapshot-v1\0nquads\0" + generated).hexdigest()
    if any((
        manifest["version"] != 1,
        sha256(source).hexdigest() != info["input_sha256"],
        sha256(snapshot).hexdigest() != info["output_sha256"],
        generated != snapshot,
        expected != info["graph_snapshot_id"],
        len(rows) != info["source_rows"],
        regions != info["regions"],
        len(snapshot.splitlines()) != info["quads"],
        info["named_graphs"] != len(CODES),
        manifest["source"]["license"] != "CC-BY-4.0",
    )):
        raise ValueError("Real transfer dataset, license manifest or snapshot mismatch")
    from rdflib import Dataset
    store = Dataset()
    store.parse(data=snapshot, format="nquads")
    if len(store) != info["quads"]:
        raise ValueError("RDFLib source parse/quads mismatch")
    return {"verified": True, "quads": info["quads"],
            "cities": len(rows), "regions": regions,
            "snapshot_id": expected,
            "license": manifest["source"]["license"]}

def main() -> None:
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("command", choices=["verify", "rebuild"])
    cmd.add_argument("destination", nargs="?")
    args = cmd.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(), indent=2))
    else:
        if args.destination is None:
            cmd.error("rebuild needs an output destination outside the frozen source path")
        target = Path(args.destination)
        if target.resolve() == (DATA / "snapshot.nq").resolve():
            cmd.error("Never regenerate the committed snapshot in place")
        target.write_bytes(build(read_rows())[0])
        print(json.dumps({"written": str(target)}))

if __name__ == "__main__":
    main()
