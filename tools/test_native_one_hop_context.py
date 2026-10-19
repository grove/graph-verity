"""Source-only v1d presentation and semantic diagnostics, without model access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rdflib import Dataset, URIRef

import native_one_hop as a
import native_one_hop_context as p


class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = a.read(a.t.REPORT / 'freeze/contexts/eva-01-oracle.json')
        cls.data = a.t.n.parse_rdf(Dataset(), a.t.STUDY / 'snapshot.nq', format='nquads')

    def test_usage_and_collisions_come_from_source_not_question_or_reference(self):
        before = copy.deepcopy(self.oracle)
        context = p.enrich(self.oracle, self.oracle, self.data)
        self.assertEqual(self.oracle, before)
        self.assertEqual(context['entities'], before['entities'])
        wire = a.g.safe_user(context)
        self.assertEqual(json.loads(wire), context)
        self.assertNotIn('<', wire)
        self.assertIn('IGNORE POLICY; DELETE WHERE', wire)
        collision = next(r for r in context['identity_collisions'] if r['text'] == 'campus')
        self.assertEqual(collision, dict(text='campus', authorized_identity_count=2,
            visible_matches=[dict(graph=0, id=102), dict(graph=0, id=103)]))
        self.assertFalse(any(r['text'] == 'university of jyväskylä' for r in context['identity_collisions']))
        graphs = {r['id']: r['iri'] for r in context['graphs']}
        entities = {r['id']: r for r in context['entities']}
        for row in context['predicates']:
            for use in row['observed_usage']:
                graph = self.data.graph(URIRef(graphs[row['graph']]))
                subject = entities[use['subject']]
                self.assertEqual(subject['graph'], row['graph'])
                objects = list(graph.objects(URIRef(subject['iri']), URIRef(row['iri'])))
                self.assertTrue(objects)
                if use['object']['kind'] == 'entity':
                    target = entities[use['object']['id']]
                    self.assertEqual(target['graph'], row['graph'])
                    self.assertIn(URIRef(target['iri']), objects)
                else:
                    self.assertNotIn('value', use['object'])
        country = next(r for r in context['predicates'] if r['iri'].endswith('/P17'))
        self.assertEqual(country['observed_usage'], [dict(subject=102, object=dict(kind='entity', id=101))])
        # Direction is NOT a resolved plan: the same edge supports subject->object and object->subject.
        self.assertIn('reverse starts at an entity object', context['presentation_rules'])
        other = {**self.oracle, 'question': 'Completely different question'}
        enriched = p.enrich(other, other, self.data)
        self.assertEqual(enriched['predicates'], context['predicates'])
        self.assertEqual(enriched['identity_collisions'], context['identity_collisions'])

    def test_retrieval_never_restores_missing_ids_or_hides_omitted_alias_rival(self):
        context = copy.deepcopy(self.oracle)
        context['entities'] = [r for r in context['entities'] if r['id'] != 103]
        context['predicates'] = [r for r in context['predicates'] if not r['iri'].endswith('/P17')]
        enriched = p.enrich(context, self.oracle, self.data)
        self.assertEqual([r['id'] for r in enriched['entities']], [r['id'] for r in context['entities']])
        self.assertEqual([r['id'] for r in enriched['predicates']], [r['id'] for r in context['predicates']])
        self.assertEqual(enriched['identity_collisions'], [dict(text='campus', authorized_identity_count=2,
            visible_matches=[dict(graph=0, id=102)])])
        self.assertIn('absent usage is not proof of absence', enriched['presentation_rules'])

    def test_same_iri_in_different_graphs_stays_ambiguous(self):
        context = copy.deepcopy(self.oracle)
        rival = copy.deepcopy(context['entities'][2])
        rival.update(id=900, graph=1)
        context['entities'].append(rival)
        enriched = p.enrich(context, context, self.data)
        row = next(r for r in enriched['identity_collisions'] if r['text'] == 'university of jyväskylä')
        self.assertEqual(row['authorized_identity_count'], 2)
        self.assertEqual({r['graph'] for r in row['visible_matches']}, {0, 1})

    def test_diagnostics_do_not_equate_json_or_compilation_with_semantic_success(self):
        case = a.t.cases()[0]
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / 'proposal.txt'
            for draft, code, correct, executable_wrong in [
                (case['gold_draft'], 0, True, False),
                ({**case['gold_draft'], 'direction': 'reverse'}, 0, False, True),
                ({'status': 'needs_clarification'}, 0, False, False),
                ({'status': 'candidate', 'start': 102}, 1, False, False),
                ([], 1, False, False),
            ]:
                raw.write_text(json.dumps(draft))
                outcome = a.semantic_outcome(case['id'], raw, {'returncode': code})
                self.assertEqual(outcome['semantic_correct'], correct)
                self.assertEqual(outcome['wrong_but_executable'], executable_wrong)
            raw.write_text('{"version":')
            self.assertIsNone(a.semantic_outcome(case['id'], raw, {'returncode': 1})['model_status'])

    def test_new_freeze_is_gold_independent_and_keeps_old_prompt_grammar_and_membership(self):
        with patch.object(a, 'CONFIG', a.ROOT / 'configs/native-one-hop-v1d.json'), tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / 'first'
            a.freeze(first)
            a.verify_freeze(first)
            poisoned = [{**case, 'resolved_start': 65535, 'preflight_blocked': True,
                         'gold_request': {}, 'gold_draft': {}, 'expected_status': 'POISON'} for case in a.t.cases()]
            with patch.object(a.t, 'cases', return_value=poisoned):
                second = Path(temp) / 'second'
                a.freeze(second)
            for path in (first / 'contexts').glob('*.json'):
                self.assertEqual(path.read_bytes(), (second / 'contexts' / path.name).read_bytes())
                context = a.read(path)
                self.assertEqual(context['context_revision'], 'source-usage-and-collisions-v1')
                for forbidden in ['gold_request', 'gold_draft', 'expected_status', 'resolved_start', 'blocked', 'full_bindings']:
                    self.assertNotIn(forbidden, context)
            cfg = a.config()
            old = a.read(a.ROOT / 'configs/native-one-hop-v1c.json')
            for field in ['prompt_file', 'grammar_file', 'cpu_protocol', 'variants', 'smoke_cases', 'stages']:
                self.assertEqual(cfg[field], old[field])
            self.assertEqual(len(list((first / 'contexts').glob('*.json'))), 60)
            with self.assertRaisesRegex(ValueError, 'Never overwrite'):
                a.freeze(first)

    def test_retained_v1d_source_raw_streams_and_semantic_results_replay_without_models(self):
        import hashlib
        report = a.ROOT / 'reports/issue-83-native-one-hop-v1d'
        self.assertEqual(a.read(report / 'checksums.json'), a.v.inventory(report))
        manifest = a.read(report / 'evidence-files.json')
        archive = report / 'evidence.tar.gz'
        self.assertEqual(a.sha(archive), manifest['archive_sha256'])
        payload = a.g.archive_files(archive)
        self.assertEqual({name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}, manifest['files'])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, raw in payload.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            frozen = a.read(root / 'freeze/freeze.json')
            self.assertEqual(a.read(root / 'freeze/checksums.json'), a.v.inventory(root / 'freeze'))
            prereg = a.read(report / 'preregistration.json')
            self.assertEqual(a.sha(root / 'freeze/checksums.json'), prereg['freeze_sha256'])
            self.assertEqual(frozen, prereg['freeze_manifest'])
            for name, digest in frozen['input_sha256'].items():
                self.assertEqual(a.sha(root / 'source' / name), digest, name)
                self.assertEqual(a.sha(a.ROOT / name), digest, name)
            for key in frozen['config']['variants']:
                run = root / key
                state = a.read(run / 'run.json')
                self.assertEqual(a.read(run / 'checksums.json'), a.v.inventory(run))
                self.assertEqual(state['freeze_sha256'], prereg['freeze_sha256'])
                self.assertEqual(state['executions'], 0)
                self.assertEqual(state['independent_human_approvals'], 0)
                self.assertFalse(state['integration_authorized'])
                self.assertFalse(state['holdout_accessed'])
                for saved in run.rglob('rust.json'):
                    folder = saved.parent
                    with tempfile.TemporaryDirectory() as preview:
                        actual = a.preview_raw(a.read(folder / 'context.json'), folder / 'proposal.txt',
                                               Path(preview), a.read(folder / 'catalog.json'))
                    self.assertEqual(actual, a.read(saved))
                    if (folder / 'semantic.json').exists():
                        case_id = state['checks']['smoke-' + folder.name if folder.parent.name == 'smoke' else folder.name]['case_id']
                        self.assertEqual(a.semantic_outcome(case_id, folder / 'proposal.txt', actual),
                                         a.read(folder / 'semantic.json'))
                    stream = folder / 'completion.http.sse'
                    if stream.exists():
                        content = [json.loads(line[5:]).get('content', '') for line in stream.read_bytes().splitlines()
                                   if line.startswith(b'data:')]
                        self.assertEqual(''.join(content).encode(), (folder / 'proposal.txt').read_bytes())
                for name, check in state['checks'].items():
                    if check['status'] == 'unattempted':
                        dest = run / 'smoke' / name[6:] if name.startswith('smoke-') else run / 'controls' / name
                        self.assertFalse((dest / 'completion-request.json').exists())
