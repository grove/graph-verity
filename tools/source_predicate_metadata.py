"""Offline, graph-qualified extraction from the separately registered source archive."""
import copy
import hashlib
import json
from pathlib import Path

from rdflib import Dataset, Graph, Literal, URIRef

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/source-predicate-metadata-v1.json'
STUDY = 'studies/nl-ask-v1/evaluation/'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return 'sha256:' + digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                       separators=(',', ':')).encode())


def statement(triple):
    text = ' '.join(t.n3() for t in triple) + ' .'
    return dict(statement=text, utf8_sha256=digest(text.encode()))


def build(config=CONFIG, root=ROOT):
    cfg = json.loads(config.read_bytes())
    require(cfg['version'] == 'source-predicate-metadata-v1' and
            cfg['mapping_predicates'] == ['http://wikiba.se/ontology#directClaim'], 'Unknown adapter rules')
    for name, expected in cfg['input_sha256'].items():
        require(digest((root / name).read_bytes()) == expected, 'Changed registered input: ' + name)
    read = lambda name: json.loads((root / name).read_bytes())
    catalog, policy, scope = [read(STUDY + n) for n in ['catalog.json', 'policy.json', 'scope.json']]
    manifest = read('studies/nl-ask-v1/manifest.json')
    graphs = {g['id']: g['iri'] for g in catalog['graphs']}
    require(len(graphs) == len(catalog['graphs']) and len(set(graphs.values())) == len(graphs), 'Duplicate graph')
    require(set(graphs.values()) == set(scope) <= set(policy['graphs']), 'Unauthorized graph')
    data = Dataset()
    data.parse(root / (STUDY + 'snapshot.nq'), format='nquads')
    archives, provenance = {}, []
    for source in cfg['sources']:
        record = source['provenance']
        require(record in manifest['source_inventory'] and record['file'] == source['file'] and
                record['license'] == 'CC0-1.0', 'Unregistered licensing/provenance')
        # Source-to-importer-graph authorization is explicit; IRI equality never transfers it.
        require(any(source['graph'] == r['graphs'][0] and
                    source['file'] == 'studies/nl-ask-v1/sources/' + r['wikidata'] + '.ttl'
                    for r in manifest['recipes']), 'Unauthorized source/graph mapping')
        require(source['graph'] in scope, 'Private metadata source')
        raw = Graph().parse(root / source['file'], format='turtle')
        dataset = URIRef(source['dataset'])
        license_triple = (dataset, URIRef('http://creativecommons.org/ns#license'),
                          URIRef('http://creativecommons.org/publicdomain/zero/1.0/'))
        revision_triple = (dataset, URIRef('http://schema.org/version'),
                           Literal(record['revision']))
        require(license_triple in raw and revision_triple in raw, 'Source license/revision triples missing')
        archives[source['file']] = raw
        provenance.append(dict(**source, file_sha256=cfg['input_sha256'][source['file']],
                               license_statement=statement(license_triple), revision_statement=statement(revision_triple)))
    rows, seen = [], set()
    for predicate in catalog['predicates']:
        key = (predicate['graph'], predicate['iri'])
        require(key not in seen and predicate['graph'] in graphs, 'Duplicate/unknown predicate binding')
        seen.add(key)
        graph, iri = graphs[predicate['graph']], URIRef(predicate['iri'])
        witnesses = sorted(data.graph(URIRef(graph)).triples((None, iri, None)),
                           key=lambda t: tuple(x.n3() for x in t))
        require(witnesses, 'Predicate has no graph-local witness')
        evidence = []
        for source in cfg['sources']:
            if source['graph'] != graph:
                continue
            raw = archives[source['file']]
            for mapping in cfg['mapping_predicates']:
                for prop in sorted(raw.subjects(URIRef(mapping), iri), key=str):
                    require(isinstance(prop, URIRef), 'Blank property identity')
                    # Multiple distinct property identities are retained, never silently merged.
                    for text_p, value in sorted(raw.predicate_objects(prop), key=lambda t: tuple(x.n3() for x in t)):
                        if (str(text_p) not in cfg['text_predicates'] or not isinstance(value, Literal)
                                or value.language not in cfg['languages']):
                            continue
                        evidence.append(dict(source=source['file'], property_iri=str(prop),
                            mapping=statement((prop, URIRef(mapping), iri)), text=statement((prop, text_p, value)),
                            text_predicate=str(text_p), lexical=str(value), language=value.language,
                            datatype=str(value.datatype) if value.datatype else None))
        rows.append(dict(**predicate, graph_iri=graph, metadata=evidence,
                         graph_witnesses=[statement((*t, URIRef(graph))) for t in witnesses],
                         missing=not evidence, property_identity_ambiguous=len({e['property_iri'] for e in evidence}) > 1))
    body = dict(version=cfg['version'], registry_sha256=digest(config.read_bytes()),
                input_sha256=cfg['input_sha256'], source_provenance=provenance, predicates=rows,
                snapshot_id=catalog['snapshot_id'], graphs=catalog['graphs'],
                graph_origin=manifest['graph_origin'], property_revision_claimed=False)
    return dict(**body, source_revision=identity(body))


def enrich(context, metadata, enabled):
    """No references, question matching, vocabulary additions or start resolution."""
    result = copy.deepcopy(context)
    validate(metadata)
    require(context['snapshot_id'] == metadata['snapshot_id'] and
            all(g in metadata['graphs'] for g in context['graphs']), 'Stale or unauthorized context source')
    graphs = {g['id']: g['iri'] for g in result['graphs']}
    available = {(r['graph'], r['iri']): r for r in metadata['predicates']}
    for row in result['predicates']:
        retained = available[(row['graph'], row['iri'])]
        require(retained['graph_iri'] == graphs[row['graph']] and retained['id'] == row['id'], 'Cross-graph metadata binding')
        row['source_metadata'] = copy.deepcopy(retained['metadata']) if enabled else []
    result['context_revision'] = 'source-predicate-metadata-ablation-v1'
    return result


def packet(context, metadata):
    validate(metadata)
    body = dict(version='source-metadata-context-packet-v1', source_revision=metadata['source_revision'],
                snapshot_sha256=metadata['input_sha256'][STUDY + 'snapshot.nq'], context=context)
    return dict(**body, packet_id=identity(body))


def validate(metadata):
    require(metadata['source_revision'] == identity({k: v for k, v in metadata.items() if k != 'source_revision'}),
            'Stale or modified metadata source revision')


def revalidate(saved, context, metadata, saved_packet_id):
    require(saved == packet(context, metadata) and saved['packet_id'] == saved_packet_id,
            'Stale or modified metadata context packet')
    return context
