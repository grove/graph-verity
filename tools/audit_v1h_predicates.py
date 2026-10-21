#!/usr/bin/env python3
"""Reproduce the predicate audit from existing public archives; no network or models."""
import argparse
import hashlib
import json

from rdflib import Dataset, Graph, Literal, URIRef

import native_one_hop_v1h as h

ROOT = h.ROOT
OUT = ROOT / 'experiments/native-one-hop-v1h-qwen-direction-only/provenance-audit.json'
RAW = 'studies/nl-ask-v1/sources/Q578326.ttl'
SNAPSHOT = 'studies/nl-ask-v1/evaluation/snapshot.nq'
GRAPH = 'urn:graph-verity:nl-ask-v1:evaluation:wikidata'
WD = 'http://www.wikidata.org/'
DIRECT = URIRef('http://wikiba.se/ontology#directClaim')
TEXT = {'http://www.w3.org/2000/01/rdf-schema#label', 'http://www.w3.org/2004/02/skos/core#prefLabel',
        'http://schema.org/name', 'http://schema.org/description'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def statement(source, triple):
    text = ' '.join(t.n3() for t in triple) + ' .'
    return dict(source=source, statement=text, statement_utf8_sha256=digest(text.encode()))


def build():
    paths = [RAW, SNAPSHOT, 'studies/nl-ask-v1/manifest.json', 'tools/nl_ask_benchmark.py',
             'studies/nl-ask-v1/cases.json', 'studies/nl-ask-v1/evaluation/discovery.json',
             'experiments/issue83-reverse-predicate-audit/review.json',
             'experiments/native-one-hop-v1h-investigation/generated/coordinator/original-host-catalog.json']
    raw = Graph().parse(ROOT / RAW, format='turtle')
    data = Dataset()
    data.parse(ROOT / SNAPSHOT, format='nquads')
    manifest = h.read(ROOT / paths[2])
    provenance = next(r for r in manifest['source_inventory'] if r['file'] == RAW)
    catalog = h.read(ROOT / paths[-1])
    cases = h.a.t.cases()
    predicates = []
    for prop, cid in [('P131', 'eva-07'), ('P856', 'eva-08')]:
        subject, predicate = URIRef(WD + 'entity/' + prop), URIRef(WD + 'prop/direct/' + prop)
        h.require((subject, DIRECT, predicate) in raw, 'Missing explicit directClaim mapping')
        rows = [dict(**statement(RAW, (subject, p, o)), language=o.language, datatype=str(o.datatype) if o.datatype else None,
                     lexical=str(o)) for p, o in sorted(raw.predicate_objects(subject)) if str(p) in TEXT and isinstance(o, Literal)]
        witness = next(t for t in raw.triples((URIRef(WD + 'entity/Q578326'), predicate, None)))
        h.require(witness in data.graph(URIRef(GRAPH)), 'Missing original graph-qualified witness')
        reference = next(c for c in cases if c['id'] == cid)['gold_draft']
        binding = next(r for r in catalog['predicates'] if r['graph'] == 0 and r['iri'] == str(predicate))
        predicates.append(dict(property=prop, case_id=cid, graph=dict(id=0, iri=GRAPH, origin=manifest['graph_origin']),
            predicate_binding=binding, exposed_AI_reference=reference,
            source_edge=statement(RAW, witness), snapshot_witness=statement(SNAPSHOT, (*witness, URIRef(GRAPH))),
            direct_claim_mapping=statement(RAW, (subject, DIRECT, predicate)), property_metadata=rows,
            languages=sorted({r['language'] for r in rows}),
            snapshot_property_subject_statements=len(list(data.quads((subject, None, None, None)))),
            snapshot_direct_predicate_literal_statements=len([o for _, o in data.graph(URIRef(GRAPH)).predicate_objects(predicate) if isinstance(o, Literal)]),
            metadata_in_frozen_prompt=False, licensing=provenance,
            statement_provenance=[statement(RAW, (s, p, o)) for s in raw.objects(witness[0], URIRef(WD + 'prop/' + prop))
                                  for p, o in sorted(raw.predicate_objects(s))],
            limitation='Archived source documentation supports predicate meaning, not independent human interpretation or real-world truth. No property-page revision identity is inferred from the enclosing item revision.'))
    observations = []
    for experiment in ['native-one-hop-v1f-diagnostic-r3-evidence', 'native-one-hop-v1h-budget-qwen35-evidence',
                       'native-one-hop-v1h-qwen-status-precedence-first-evidence', 'native-one-hop-v1h-budget-gemma4-swap2048-evidence']:
        path = 'experiments/' + experiment + '/evidence.tar.gz'
        paths.append(path)
        payload = h.a.g.archive_files(ROOT / path)
        inventory = h.read(ROOT / ('experiments/' + experiment + '/evidence-files.json'))
        h.require(h.sha(ROOT / path) == inventory['archive_sha256'] and
                  {n: digest(b) for n, b in payload.items()} == inventory['files'], 'Changed original evidence')
        prefix = 'variant/run' if 'gemma4' in experiment else 'run'
        state = json.loads(payload[prefix + '/run.json'])
        for condition in ['oracle', 'retrieval']:
            for cid in ['eva-07', 'eva-08']:
                base = prefix + '/diagnostic/' + condition + '/smoke-' + cid
                row = next(r for r in state['diagnostic']['cases'] if r['condition'] == condition and r['case_id'] == cid)
                proposal, context = payload.get(base + '/proposal.txt'), payload.get(base + '/context.json')
                draft = json.loads(proposal) if proposal else None
                completed = draft is not None and row['status'] != 'fatal_failure'
                ctx = json.loads(context) if context else None
                ref = next(r for r in predicates if r['case_id'] == cid)['exposed_AI_reference']
                observations.append(dict(experiment=experiment, model='gemma4' if 'gemma4' in experiment else 'qwen35',
                    condition=condition, case_id=cid, archive=path, raw_member=base + '/proposal.txt',
                    raw_sha256=digest(proposal) if proposal is not None else None, raw_draft=draft,
                    context_member=base + '/context.json', context_sha256=digest(context) if context else None,
                    attempted=row['generation_attempted'], completed=completed, outcome=row['status'], error=row.get('error'),
                    measured_model_status=draft.get('status') if completed else None,
                    rust_accepted=row.get('reference', {}).get('rust_accepted') if completed else None,
                    exposed_reference_agreement=row.get('exact_exposed_reference_agreement') if completed else None,
                    five_fields=row.get('plan') if completed else None,
                    numeric_vocabulary={key: any(r['id'] == ref[field] and r.get('graph', 0) == ref['graph'] for r in ctx[key])
                                        for key, field in [('entities', 'start'), ('predicates', 'predicate'), ('graphs', 'graph')]} if ctx else None,
                    independent_human_correctness=None))
    supplemental_path = 'data/wikidata/raw/P131-2555801353.ttl'
    paths += [supplemental_path, 'data/wikidata/manifest.json']
    supplemental = Graph().parse(ROOT / supplemental_path, format='turtle')
    supplemental_metadata = [dict(**statement(supplemental_path, (s, p, o)), language=o.language)
                             for s, p, o in sorted(supplemental.triples((URIRef(WD + 'entity/P131'), None, None)))
                             if str(p) in TEXT and isinstance(o, Literal) and o.language in ['en', 'nb', 'nn']]
    supplemental_manifest = h.read(ROOT / 'data/wikidata/manifest.json')
    supplemental_record = next(r for r in supplemental_manifest['sources'] if r['file'] == supplemental_path)
    return dict(version='issue83-predicate-provenance-v1', base_after_merged_pr100='82e81a3e30c315c27d86b5c125143020a172af18',
        origin='Source-grounded coding-agent audit; independent human review pending', inference_performed=False, executions=0,
        decision='INCONCLUSIVE_REVISE', input_sha256={n: h.sha(ROOT / n) for n in paths}, predicates=predicates, observations=observations,
        supplemental_P131=dict(provenance=supplemental_record, metadata=supplemental_metadata,
            membership='Separate existing archive, outside frozen evaluation source membership; never imported into prompts.'),
        evidence_classes={
            'edge_existence':'Archived direct triples and imported named-graph witnesses establish these particular stored edges.',
            'predicate_documentation':'Archived English property labels/descriptions plus explicit wikibase:directClaim mappings establish source-documented meanings. They were excluded by source_quads before freezing.',
            'model_inference':'Original raw rationales are observations, not source definitions or causal explanations.',
            'exposed_reference':'Unchanged AI-authored case references are comparison targets; agreement is not independent correctness.'},
        limitations=[
            'The original item archive contains licensed definitions for both properties; their absence from the frozen snapshot is not absence from the archive.',
            'The source_quads recipe imports only focal-entity direct fields and selected labels, then synthetic overlay; property metadata is excluded. Audit metadata is never inserted into prompts.',
            'The item archive supplies English property metadata only. A separate existing P131 property archive has multilingual metadata but is outside the frozen evaluation source membership and is not imported.',
            'Named graphs and numeric IDs are importer/host assignments. Q134620 and university-graph wording still lack source naming support in the model-visible snapshot.',
            'P131 and P856 statements have normal/best rank but no prov:wasDerivedFrom statement reference in this item archive. CC0 metadata does not independently verify the claims.',
            'Direction wording is cleanly isolatable as an input factor; its causal effect cannot be separated from missing semantic definitions using these two exposed probes alone.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = (json.dumps(build(), indent=2, ensure_ascii=False) + '\n').encode()
    if args.check:
        h.require(OUT.read_bytes() == raw, 'Predicate audit drift')
    else:
        with OUT.open('xb') as stream:
            stream.write(raw)
