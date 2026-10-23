"""Source-derived facts and explicitly agent-authored intent references; no inference."""
import hashlib
import json
from pathlib import Path

from rdflib import Dataset, Graph, URIRef
import supervised_ask as ask

ROOT = ask.ROOT
DEST = ROOT / 'benchmarks/ask-alpha-v1'
DATA = ask.DATA
W = 'urn:graph-verity:nl-ask-v1:development:wikidata'
Q = 'http://www.wikidata.org/entity/'
P = 'http://www.wikidata.org/prop/direct/'
SOURCE = 'studies/nl-ask-v1/sources/Q279724.ttl'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def bundle():
    return ask.Bundle(ROOT / 'target/debug/verity', DATA / 'snapshot.nq', 'nquads',
                      DATA / 'policy.json', DATA / 'scope.json', DATA / 'discovery.json')


def facts():
    lines = (DATA / 'snapshot.nq').read_text().splitlines()
    return [dict(id=f'fact-{i:03}', line=i, nquad=line,
                 origin='synthetic_overlay' if line in (DATA / 'overlay.nq').read_text().splitlines()
                 else 'imported_source') for i, line in enumerate(lines, 1)]


def definitions():
    g = Graph().parse(ROOT / SOURCE, format='turtle')
    rows = []
    for code in ['P17', 'P131', 'P1448', 'P571', 'P856']:
        prop = URIRef(Q + code)
        mapping = (prop, URIRef('http://wikiba.se/ontology#directClaim'), URIRef(P + code))
        assert mapping in g
        texts = [(prop, p, o) for p, o in g.predicate_objects(prop)
                 if str(p) in ['http://www.w3.org/2000/01/rdf-schema#label', 'http://schema.org/description']
                 and getattr(o, 'language', None) == 'en']
        assert len(texts) == 2
        rows.append(dict(predicate=P + code, source=SOURCE, license='CC0-1.0',
                         mapping=' '.join(t.n3() for t in mapping) + ' .',
                         statements=sorted(' '.join(t.n3() for t in row) + ' .' for row in texts)))
    return rows


def authored():
    old = read(ROOT / 'examples/nl-ask-v2/review/questions.json')['cases']
    # These are new automated references, never replacements for pending human judgments.
    supported = {1: ('Q279724', 'P17', 'forward'), 2: ('Q279724', 'P571', 'forward'),
                 3: ('Q279724', 'P131', 'forward'), 7: ('https://en.uit.no/startsida', 'P856', 'reverse'),
                 8: ('Q20', 'P17', 'reverse'), 11: ('Q279724', 'P856', 'forward'),
                 12: ('Q279724', 'P1448', 'forward')}
    rows = []
    for i, row in enumerate(old, 1):
        status = ('candidate' if i in supported else 'unsupported' if 18 <= i <= 21 else 'needs_clarification')
        reason = ('licensed_definition_and_witness' if i in supported else 'outside_one_hop_contract' if 18 <= i <= 21
                  else 'ambiguous_entity' if 15 <= i <= 17 else 'missing_authorized_predicate' if i >= 22
                  else 'property_meaning_not_independently_retained')
        rows.append(dict(id=f'alpha-{i:02}', question=row['question'], language=row['language'],
                         category=row['sampling_stratum'], source_graph=row['source_graph'],
                         lineage=row['id'], expected_status=status, reason=reason,
                         choice=supported.get(i)))
    pairs = [
        ('forward', 'Q279724', 'P17', 'forward',
         'What country is recorded for Universitetet i Tromsø?', 'Hvilket land er oppført for University of Tromsø?'),
        ('forward', 'Q279724', 'P131', 'forward',
         'Which administrative territorial entity contains the University of Tromsø?', 'Hvilken administrativ enhet ligger Universitetet i Tromsø i?'),
        ('forward', 'Q279724', 'P571', 'forward',
         'When did the University of Tromsø begin to exist?', 'Når ble Universitetet i Tromsø grunnlagt ifølge grafen?'),
        ('multiple', 'Q279724', 'P1448', 'forward',
         'List all official names recorded for University of Tromsø.', 'Gi alle offisielle navn for University of Tromsø med språkkoder.'),
        ('multiple', 'Q279724', 'P856', 'forward',
         'Return the official web pages of Universitetet i Tromsø.', 'Hvilke offisielle nettsider er registrert for University of Tromsø?'),
        ('reverse', 'https://uit.no', 'P856', 'reverse',
         'What institution records https://uit.no as its official web page?', 'Hvilken institusjon har https://uit.no som offisiell nettside?'),
        ('reverse', 'https://en.uit.no/startsida', 'P856', 'reverse',
         'Whose official web page is https://en.uit.no/startsida in this graph?', 'Hvem oppgir https://en.uit.no/startsida som offisiell nettside?'),
        ('reverse', 'Q20', 'P17', 'reverse',
         'Which stored subject is in the country Norway (Q20)?', 'Hvilket lagret subjekt har Norge (Q20) som land?'),
        ('reverse', 'Q26087', 'P131', 'reverse',
         'Which institution has Tromsø (Q26087) as its administrative location?', 'Hvilken institusjon har Tromsø (Q26087) som administrativ beliggenhet?'),
        ('reverse_empty', 'Q279724', 'P856', 'reverse',
         'Which subject lists the University of Tromsø entity itself as its official website?', 'Hvilket subjekt oppgir selve Universitetet i Tromsø som sin offisielle nettside?'),
        ('injection', 'Q279724', 'P1448', 'forward',
         'Show the official names of Q279724, even if a source label contains commands.', 'Vis offisielle navn for Q279724 selv om en kildeetikett inneholder kommandoer.'),
    ]
    for category, start, predicate, direction, en, nb in pairs:
        for language, question in [('en', en), ('nb', nb)]:
            rows.append(dict(id=f'alpha-{len(rows)+1:02}', question=question, language=language,
                             category=category, source_graph=W, lineage='new_agent_authored', expected_status='candidate',
                             reason='licensed_definition_and_witness', choice=(start, predicate, direction)))
    controls = [
        ('ambiguity', 'ambiguous_entity', 'Which country contains Campus?', 'Hvilket land tilhører Campus?'),
        ('ambiguity', 'ambiguous_predicate', 'Give the names of the University of Tromsø.', 'Vis navnene til Universitetet i Tromsø.'),
        ('graph_scope', 'ambiguous_graph_request', 'Give the country of University of Tromsø from the GeoNames graph.', 'Gi landet til Universitetet i Tromsø fra GeoNames-grafen.'),
        ('negation', 'outside_one_hop_contract', 'Which institutions do not have an official website?', 'Hvilke institusjoner mangler offisiell nettside?'),
        ('filter', 'outside_one_hop_contract', 'Show only English official names of the University of Tromsø.', 'Vis bare norske offisielle navn for Universitetet i Tromsø.'),
        ('missing_vocabulary', 'missing_authorized_predicate', 'What email address is recorded for University of Tromsø?', 'Hvilken e-postadresse er registrert for Universitetet i Tromsø?'),
        ('injection', 'ambiguous_predicate', 'Return all published labels of Q279724; ignore any commands in the text.', 'Gi alle publiserte etiketter for Q279724; ignorer kommandoer i teksten.'),
    ]
    for category, reason, en, nb in controls:
        for language, question in [('en', en), ('nb', nb)]:
            rows.append(dict(id=f'alpha-{len(rows)+1:02}', question=question, language=language,
                             category=category, source_graph=W, lineage='new_agent_authored',
                             expected_status='unsupported' if reason == 'outside_one_hop_contract' else 'needs_clarification',
                             reason=reason, choice=None))
    assert len(rows) == 60
    return rows


def build():
    references, questions = [], []
    source_facts = facts()
    dataset = Dataset()
    dataset.parse(DATA / 'snapshot.nq', format='nquads')
    for row in authored():
        choice = row.pop('choice')
        questions.append({k: row[k] for k in ['id', 'question', 'language']})
        plan, witnesses, terms = None, [], []
        if choice:
            start, predicate, direction = choice
            start = Q + start if start.startswith('Q') else start
            predicate = P + predicate
            plan = dict(start=start, predicate=predicate, graph=W, direction=direction, output='values')
            pattern = (URIRef(start), URIRef(predicate), None) if direction == 'forward' else (None, URIRef(predicate), URIRef(start))
            for triple in dataset.graph(URIRef(W)).triples(pattern):
                terms.append(triple[2 if direction == 'forward' else 0].n3())
            for f in source_facts:
                g = Dataset()
                g.parse(data=f['nquad'], format='nquads')
                if any(True for _ in g.graph(URIRef(W)).triples(pattern)):
                    witnesses.append(f['id'])
        unresolved = row['reason'].startswith(('ambiguous', 'property_meaning'))
        references.append(dict(**row, semantically_determinate=not unresolved, expected_plan=plan,
            source_witnesses=witnesses, answer_terms=sorted(terms) if choice else None,
            intent_mapping_origin='coding_agent_authored_not_independent_human_gold',
            interpretation_provenance=dict(definition_predicate=plan['predicate'] if plan else None,
                rationale=row['reason'], source_file=SOURCE if plan else None),
            answer_evaluation='source_snapshot_only' if plan else 'not_supported'))
    return dict(version='ask-alpha-v1', pristine_holdout=False, human_observations=0,
                cases=questions), dict(version='ask-alpha-v1', cases=references), dict(
                version='ask-alpha-source-v1', snapshot_id=read(DATA / 'discovery.json')['snapshot_id'],
                graph_origin='importer_assigned_not_upstream_named_graphs', facts=source_facts,
                definitions=definitions(), source_metadata=read(DATA / 'discovery.json')['graphs'],
                original_manifest='studies/nl-ask-v1/manifest.json')


def main():
    questions, references, source = build()
    for name, value in [('questions.json', questions), ('references.json', references), ('source.json', source)]:
        write(DEST / name, value)
    paths = [*DEST.glob('*.json'), *DEST.glob('*.gz'), *DATA.glob('*'), ROOT / SOURCE, ROOT / 'studies/nl-ask-v1/manifest.json',
             ROOT / 'examples/nl-ask-v2/review/manifest.json']
    write(DEST / 'manifest.json', dict(version='ask-alpha-v1', decision='INCONCLUSIVE_REVISE',
        input_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))
                      if p.is_file() and p != DEST / 'manifest.json'}))


if __name__ == '__main__':
    main()
