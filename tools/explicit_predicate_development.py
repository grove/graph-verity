#!/usr/bin/env python3
"""Mechanical source-only binding panel. Separate from v1g; no native run command."""
import argparse
import copy
import json
from pathlib import Path

from rdflib import URIRef

import native_one_hop_v1g as v


def generate(out, binary=v.a.BINARY):
    v.require(not out.exists(), 'Never overwrite development fixtures')
    out.mkdir(parents=True)
    data, table = v.source_data(), v.read(v.STUDY / 'catalog.json')
    oracle = v.read(v.HISTORICAL / 'contexts/eva-01-oracle.json')
    discovery = v.read(v.STUDY / 'discovery.json')
    budget = v.read(v.CAPTURE / 'budget.json')
    manifest = json.loads(v.a.v.cli(binary, 'index-build', v.STUDY / 'snapshot.nq', 'nquads',
                                     v.STUDY / 'policy.json', v.STUDY / 'scope.json', v.STUDY / 'discovery.json'))['manifest']
    questions, specs = [], []
    for predicate in table['predicates']:
        graph = next(g['iri'] for g in table['graphs'] if g['id'] == predicate['graph'])
        triples = sorted(data.graph(URIRef(graph)).triples((None, URIRef(predicate['iri']), None)),
                         key=lambda t: tuple(x.n3() for x in t))
        entities = sorted((e for e in table['entities'] if e['graph'] == predicate['graph']), key=lambda e: e['iri'])
        for direction in ['forward', 'reverse']:
            matches = lambda e: [t for t in triples if str(t[0 if direction == 'forward' else 2]) == e['iri']]
            witnessed = [e for e in entities if matches(e)]
            empty = [e for e in entities if not matches(e)]
            # Literal objects cannot be draft starts: retain a separately marked empty reverse path.
            starts = [('witnessed', witnessed[0])] if witnessed else []
            if empty:
                starts.append(('empty_path', empty[0]))
            v.require(starts, 'No permitted entity start')
            for kind, entity in starts:
                cid = f'explicit-{len(questions)+1:03}'
                wording = (f'List values from <{entity["iri"]}> using explicit predicate <{predicate["iri"]}>' if direction == 'forward'
                           else f'List subjects pointing to <{entity["iri"]}> using explicit predicate <{predicate["iri"]}>')
                q = dict(id=cid, question=wording + f' in graph <{graph}>.', language='en')
                questions.append(q)
                specs.append((q, entity, predicate, direction, kind, matches(entity), graph))
    v.dump(out / 'questions.json', questions)
    for directory in ['contexts', 'packets', 'messages', 'grammars']:
        (out / directory).mkdir()
    for q in questions:
        dest = out / 'packets' / q['id']
        dest.mkdir()
        request = dict(question=q['question'], language=q['language'], snapshot_id=manifest['snapshot_id'],
                       index_revision=manifest['index_revision'], scope=v.read(v.STUDY / 'scope.json'))
        v.dump(dest / 'request.json', request)
        v.dump(dest / 'budget.json', budget)
        base = copy.deepcopy(oracle)
        base.update(question=q['question'], language=q['language'])
        for condition, command in [('oracle', None), ('BM25-v1', 'vocabulary'), ('neighborhood-v2', 'neighborhood')]:
            packet = None
            if command:
                raw = v.a.v.cli(binary, command, v.STUDY / 'snapshot.nq', 'nquads', v.STUDY / 'policy.json',
                                v.STUDY / 'scope.json', v.STUDY / 'discovery.json', dest / 'request.json', dest / 'budget.json').rstrip(b'\n')
                (dest / f'{condition}.json').write_bytes(raw)
                packet = json.loads(raw)
            context = v.render(base, data, discovery, packet)
            v.dump(out / 'contexts' / f'{q["id"]}-{condition}.json', context)
            v.dump(out / 'messages' / f'{q["id"]}-{condition}.json', [
                dict(role='system', content=(v.ROOT / v.config()['prompt_file']).read_text()),
                dict(role='user', content=v.a.g.safe_user(context))])
            with v.adapter():
                (out / 'grammars' / f'{q["id"]}-{condition}.gbnf').write_text(v.a.grammar(context))
    v.dump(out / 'prompt-seal.json', v.a.v.inventory(out))
    # Derive typed references and original witnesses only after every prompt/context is sealed.
    references = []
    for q, entity, predicate, direction, kind, triples, graph in specs:
        references.append(dict(id=q['id'], kind=kind, gold_draft=dict(version='nl-ask-draft-v1', status='candidate',
            start=entity['id'], predicate=predicate['id'], graph=entity['graph'], direction=direction, output='values',
            rationale='Mechanical explicit-predicate development reference'),
            witnesses=sorted([s.n3(), p.n3(), o.n3(), URIRef(graph).n3()] for s, p, o in triples)))
    v.dump(out / 'references.json', references)
    v.dump(out / 'panel.json', dict(version='explicit-predicate-development-v1', cases=len(questions),
        permitted_graph_predicates=len(table['predicates']), generation_rule='Every permitted graph/predicate; lexical-sorted witnessed and empty starts, forward and reverse. Literal objects are not entity starts.',
        v1g_denominator_member=False, native_inference_authorized=False, inference_performed=False,
        status='Model-free development only; exact questions/requests need a separate registration before inference',
        input_sha256={str(p.relative_to(v.ROOT)): v.sha(p) for p in [Path(__file__), v.STUDY / 'snapshot.nq',
                       v.STUDY / 'catalog.json', v.STUDY / 'policy.json', v.STUDY / 'discovery.json']}))
    v.dump(out / 'checksums.json', v.a.v.inventory(out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    generate(parser.parse_args().out)
