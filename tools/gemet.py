#!/usr/bin/env python3
"""Offline, source-preserving GEMET 4.2.3 + W3C SKOS pilot extraction."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import rdflib
from rdflib import Graph, Literal, RDF, RDFS, SKOS, URIRef
import retrieval as r

ROOT = r.ROOT
DATA = ROOT / 'data/gemet'
GRAPH = 'urn:graph-verity:gemet:4.2.3'
BASE = 'http://www.eionet.europa.eu/gemet/concept/'


def sources():
    # Preserve even ill-typed original literals; never repair the publisher's facts.
    previous = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        xml = ET.fromstring(gzip.decompress((DATA/'source/gemet-4.2.3.rdf.gz').read_bytes()))
        # Unselected publisher dates include empty ill-typed dateTimes. Exclude
        # these unused properties before parsing, without normalizing literals.
        for subject in xml:
            for value in list(subject):
                if value.tag in {'{http://purl.org/dc/terms/}created', '{http://purl.org/dc/terms/}modified'}:
                    subject.remove(value)
        gemet = Graph().parse(data=ET.tostring(xml), format='xml')
        schema = Graph().parse(DATA/'source/skos.rdf', format='xml')
    finally:
        rdflib.NORMALIZE_LITERALS = previous
    return gemet, schema


def extract(count):
    r.require(0 < count <= 10000, 'Expected 1..10000 selected concepts')
    gemet, schema = sources()
    concepts = sorted(set(gemet.subjects(RDF.type, SKOS.Concept)),
                      key=lambda s: (hashlib.sha256(str(s).encode()).hexdigest(), str(s)))
    r.require(count <= len(concepts), 'Source has fewer concepts than requested; no synthetic padding')
    selected = set(concepts[:count])
    fields = {SKOS.prefLabel, SKOS.altLabel, SKOS.definition, RDF.type}
    relations = {SKOS.broader, SKOS.narrower, SKOS.related}
    triples = {(s, p, o) for s, p, o in gemet if s in selected and (
        (p in fields and (not isinstance(o, Literal) or o.language in {'en', 'no', None}))
        or (p in relations and o in selected))}
    # Explicit importer union of two un-named source graphs, not label borrowing
    # between original named graphs. Keep the two original source inventories.
    vocabulary = {p for _, p, _ in triples} | {SKOS.Concept}
    triples.update((s, p, o) for s, p, o in schema if s in vocabulary
                   and p in {RDFS.label, RDFS.comment, SKOS.definition, RDF.type}
                   and (not isinstance(o, Literal) or o.language in {'en', None}))
    def term(value):
        if not isinstance(value, Literal):
            return value.n3()
        suffix = ('@' + value.language if value.language else
                  '^^<' + str(value.datatype) + '>' if value.datatype else '')
        return json.dumps(str(value), ensure_ascii=False) + suffix
    lines = sorted(f'{s.n3()} {p.n3()} {term(o)} <{GRAPH}> .\n' for s, p, o in triples)
    return ''.join(lines).encode(), dict(selected_concepts=count, source_concepts=len(concepts),
        quads=len(triples), literal_languages=dict(sorted(Counter(o.language or 'untagged'
                    for _, _, o in triples if isinstance(o, Literal)).items())),
        definitions=sum(p == SKOS.definition for _, p, _ in triples),
        relation_quads=sum(p in relations for _, p, _ in triples))


def build(count, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    raw, stats = extract(count)
    (out/'snapshot.nq').write_bytes(raw)
    snapshot = 'sha256:' + hashlib.sha256(b'graph-verity-snapshot-v1\0nquads\0' + raw).hexdigest()
    r.write(out/'policy.json', dict(version=1, graphs=[GRAPH], max_rows=1000, max_evidence=10000, timeout_ms=10000))
    r.write(out/'scope.json', [GRAPH])
    r.write(out/'discovery.json', dict(version=1, snapshot_id=snapshot, graphs={GRAPH: dict(
        source='EEA GEMET 4.2.3 and W3C SKOS Reference 2009; explicit source-triple union',
        license='CC-BY-4.0 AND W3C Software and Document License (2023)',
        source_revision='sha256:' + r.sha(DATA/'source/gemet-4.2.3.rdf.gz') + ';skos-sha256:' + r.sha(DATA/'source/skos.rdf'),
        importer_revision='gemet-v1-sha256:' + r.sha(__file__))}))
    r.write(out/'stats.json', dict(stats, snapshot_id=snapshot, rdf_sha256=r.sha(out/'snapshot.nq')))
    return dict(rdf=str(out/'snapshot.nq'), format='nquads', policy=str(out/'policy.json'),
                scope=str(out/'scope.json'), config=str(out/'discovery.json'))


def verify():
    manifest = r.read(DATA/'manifest.json')
    for name, expected in manifest['sha256'].items():
        r.require(r.sha(ROOT/name) == expected, 'GEMET frozen source/import changed: ' + name)
    raw, stats = extract(manifest['selected_concepts'])
    r.require(raw == (DATA/'snapshot.nq').read_bytes(), 'GEMET snapshot is not source-reproducible')
    r.require(stats == {k: v for k, v in r.read(DATA/'stats.json').items() if k not in {'snapshot_id', 'rdf_sha256'}},
              'GEMET source denominators changed')
    r.require(b'creativecommons.org/licenses/by/4.0/' in gzip.decompress((DATA/'source/gemet-4.2.3.rdf.gz').read_bytes())
              and b'https://creativecommons.org/licenses/by/4.0/' in (DATA/'source/download.html').read_bytes(),
              'Original source license witness missing')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify')
    command = sub.add_parser('build')
    command.add_argument('--concepts', type=int, required=True)
    command.add_argument('--out', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        verify()
    else:
        build(args.concepts, args.out)
