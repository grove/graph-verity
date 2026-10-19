"""Synthetic native transport, independent Rust, paired missingness and forgery tests."""
import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import explicit_predicate_development as development
import native_one_hop_v1g as v


class V1gTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['cargo', 'build', '--locked', '--offline', '-q', '-p', 'verity_cli', '--example', 'v1g_preview', '--bin', 'verity'],
                       cwd=v.ROOT, check=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='v1g-tests-')
        cls.root = Path(cls.temp.name)
        cls.freeze = cls.root / 'freeze'
        v.materialize(cls.freeze)
        v.dump(cls.freeze / 'execution-registration.json', {'synthetic_transport_only': True})

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def checked(self, bound=None, raw=None, packet=None, policy=None, source=None, config=None):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            bound = bound or v.read(self.freeze / 'bindings/eva-01-neighborhood-v2.json')
            v.dump(dest / 'binding.json', bound)
            (dest / 'packet.json').write_bytes(packet if packet is not None else
                v.packet_path(self.freeze, 'eva-01', 'neighborhood-v2').read_bytes())
            (dest / 'raw.txt').write_bytes(raw or b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"test"}')
            if policy is not None:
                v.dump(dest / 'policy.json', policy)
            if source is not None:
                (dest / 'source.nq').write_bytes(source)
            if config is not None:
                v.dump(dest / 'discovery.json', config)
            args = [v.BRIDGE, dest / 'source.nq' if source is not None else v.STUDY / 'snapshot.nq',
                    dest / 'policy.json' if policy is not None else v.STUDY / 'policy.json', v.STUDY / 'scope.json',
                    dest / 'discovery.json' if config is not None else v.STUDY / 'discovery.json',
                    dest / 'binding.json', dest / 'packet.json', dest / 'raw.txt']
            return subprocess.run(list(map(str, args)), cwd=v.ROOT, capture_output=True)

    def test_independent_rust_rejects_forgery_stale_identity_role_numeric_graph_and_subset(self):
        original = v.read(self.freeze / 'bindings/eva-01-neighborhood-v2.json')
        self.assertEqual(self.checked().returncode, 0)
        mutations = []
        for field, value in [('saved_packet_id', 'forged'), ('condition', 'oracle')]:
            bound = copy.deepcopy(original)
            bound[field] = value
            mutations.append(bound)
        for collection, field, value in [('entities', 'id', 65535), ('entities', 'graph', 1),
                                         ('entities', 'iri', original['selection']['predicates'][0]['iri']),
                                         ('predicates', 'id', original['selection']['entities'][0]['id'])]:
            bound = copy.deepcopy(original)
            bound['selection'][collection][0][field] = value
            mutations.append(bound)
        for collection in ['entities', 'predicates', 'graphs']:
            bound = copy.deepcopy(original)
            bound['selection'][collection].pop()
            mutations.append(bound)
            bound = copy.deepcopy(original)
            bound['selection'][collection].append(bound['selection'][collection][0])
            mutations.append(bound)
        for field, value in [('snapshot_id', 'old'), ('index_revision', 'old'), ('question', 'different'), ('scope', [])]:
            bound = copy.deepcopy(original)
            bound['request'][field] = value
            mutations.append(bound)
        for bound in mutations:
            self.assertNotEqual(self.checked(bound).returncode, 0, bound)
        raw = v.packet_path(self.freeze, 'eva-01', 'neighborhood-v2').read_bytes()
        for forged in [raw + b' ', raw.replace(b'"clipped":false', b'"clipped":true', 1),
                       b'{"version":"forged",' + raw[1:]]:
            self.assertNotEqual(self.checked(packet=forged).returncode, 0)
        policy = v.read(v.STUDY / 'policy.json')
        policy['max_rows'] -= 1
        self.assertNotEqual(self.checked(policy=policy).returncode, 0)
        self.assertNotEqual(self.checked(source=(v.STUDY / 'snapshot.nq').read_bytes()+b'\n').returncode, 0)
        config = v.read(v.STUDY / 'discovery.json')
        config['snapshot_id'] = 'stale'
        self.assertNotEqual(self.checked(config=config).returncode, 0)
        invalid = [b'{}', b'not json', b'{"version":"nl-ask-draft-v1","status":"unsupported","status":"unsupported","rationale":"x"}',
                   b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"x","sparql":"DELETE"}']
        for raw in invalid:
            self.assertNotEqual(self.checked(raw=raw).returncode, 0)

    def test_all_conditions_exact_membership_gold_poison_and_common_policy(self):
        second = self.root / 'poisoned'
        poisoned = [{**c, 'gold_draft': {}, 'resolved_start': 65535, 'expected_status': 'poison',
                     'preflight_blocked': True} for c in v.a.t.cases()]
        with patch.object(v.a.t, 'cases', return_value=poisoned):
            v.materialize(second)
        for directory in ['contexts', 'messages', 'grammars', 'packets']:
            for p in (self.freeze / directory).rglob('*'):
                if p.is_file():
                    self.assertEqual(p.read_bytes(), (second / p.relative_to(self.freeze)).read_bytes())
        for q in v.read(self.freeze / 'questions.json'):
            cid = q['id']
            contexts = [v.read(self.freeze / 'contexts' / f'{cid}-{c}.json') for c in v.CONDITIONS]
            for ctx in contexts:
                self.assertFalse({'packet', 'gold_draft', 'gold_request', 'resolved_start', 'blocked', 'expected_status'} & ctx.keys())
                self.assertEqual(ctx['presentation_rules'], contexts[0]['presentation_rules'])
            for condition, method in [('BM25-v1', 'v1'), ('neighborhood-v2', 'v2')]:
                packet = v.read(v.packet_path(self.freeze, cid, condition))
                ctx = contexts[v.CONDITIONS.index(condition)]
                graphs = {r['id']: r['iri'] for r in ctx['graphs']}
                for collection in ['entities', 'predicates']:
                    self.assertEqual({(graphs[r['graph']], r['iri']) for r in ctx[collection]},
                                     {(r['graph'], r['iri']) for r in packet[collection]['candidates']})
                if method == 'v1':
                    self.assertEqual(v.packet_path(self.freeze,cid,condition).read_bytes(),
                                     (v.HISTORICAL / 'retrieval' / cid / 'packet.json').read_bytes())
        self.assertEqual(v.read(self.freeze / 'prompt-seal.json'), v.read(second / 'prompt-seal.json'))
        self.assertTrue(v.replay(self.freeze)['verified'])
        ambiguous = v.read(self.freeze / 'contexts/eva-20-neighborhood-v2.json')
        self.assertTrue(ambiguous['identity_collisions'])
        with self.assertRaisesRegex(ValueError, 'Never overwrite'):
            v.materialize(self.freeze)

    def mock_run(self, model='qwen35', failure=None):
        out = self.root / f'run-{model}-{failure}'
        cases = v.read(self.freeze / 'references.json')
        class Runtime:
            def __init__(self, cfg, *args):
                self.cfg = cfg
                self.generation_attempts = self.generation_completed = self.candidate_bytes_received = 0
                self.startup_ms = 1
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def generate(self, context, dest, constrained=True, system=None):
                if failure == 'template' and dest.name == 'eva-02':
                    raise ValueError('template parity failure before request')
                self.generation_attempts += 1
                if dest.name.startswith('sampling-'):
                    draft = dict(version='nl-ask-draft-v1',status='unsupported',rationale='control')
                    if not constrained:
                        draft['forbidden'] = True
                else:
                    draft = next(c['gold_draft'].copy() for c in cases if c['question'] == context['question'])
                    if dest.name in ['eva-19', 'eva-20']:
                        draft = cases[0]['gold_draft'].copy()  # Unsafe guess; rejection must never count as clarification.
                    if dest.name == 'eva-03':
                        draft = dict(version='nl-ask-draft-v1',status='needs_clarification',rationale='Unclear')
                    if dest.name == 'repeat-1':
                        draft['rationale'] = 'Different prose'
                    if failure == 'grammar' and dest.name == 'eva-02':
                        draft['forbidden'] = True
                raw = json.dumps(draft).encode()
                v.dump(dest / 'messages.json', [dict(role='system', content=system or (v.ROOT / self.cfg['prompt_file']).read_text()),
                                                dict(role='user',content=v.a.g.safe_user(context))])
                v.dump(dest / 'completion-request.json', dict(grammar=v.a.grammar(context), constrained=constrained))
                (dest / 'prompt.txt').write_text(v.a.g.safe_user(context))
                (dest / 'proposal.txt').write_bytes(raw)
                (dest / 'completion.http.sse').write_bytes(b'data: ' + raw)
                if failure == 'timeout' and dest.name == 'eva-02':
                    (dest / 'proposal.txt').write_bytes(raw[:10])
                    raise TimeoutError('deadline')
                if failure == 'parity' and dest.name == 'repeat-1':
                    (dest / 'prompt.txt').write_text('changed')
                self.generation_completed += 1
                self.candidate_bytes_received += len(raw)
                return dict(elapsed_ms=1, tokens_predicted=1)
        def sample(out, done, rss):
            rss.update(samples=1, peak_kib=25*2**20 if failure=='rss' else 100)
        host = dict(blockers=[{'metric':'swap'}] if failure=='host' else [], captured_at=datetime.now(timezone.utc).isoformat())
        with v.adapter(), patch.object(v, 'verify_registration'), patch.object(v.a, 'assets', return_value=v.runtime_identity()), \
             patch.object(v.a, 'preflight', return_value=host), patch.object(v.a, 'grammar_controls'), \
             patch.object(v.a, 'grammar_check', side_effect=lambda raw,*args:'forbidden' not in raw), \
             patch.object(v.a, 'Runtime', Runtime), patch.object(v.a, 'sample_rss', side_effect=sample):
            state = v._run(self.freeze, out, model, v.BRIDGE)
        return state, out

    def test_full_transport_real_rust_all_30_paired_and_raw_replay_both_models(self):
        runs = []
        for model in ['qwen35','gemma4']:
            state, out = self.mock_run(model)
            runs.append(out)
            self.assertEqual(state['status'], 'completed_diagnostic')
            self.assertEqual(state['generation_attempts'],94)
            self.assertEqual(state['diagnostic']['denominator'],92)
            self.assertEqual(state['diagnostic']['completed'],92)
            self.assertEqual(state['decision'],'INCONCLUSIVE_REVISE')
            self.assertEqual(state['executions'],0)
            for row in state['diagnostic']['cases']:
                raw = out / 'diagnostic' / row['condition'] / row['name'] / 'proposal.txt'
                self.assertEqual(raw.read_bytes(),base64.b64decode(row['raw_base64']))
            self.assertTrue(v.replay(self.freeze,out)['verified'])
        report = v.score(self.freeze,runs)
        self.assertFalse(report['semantic_go'])
        self.assertIsNone(report['model_ranking'])
        rows = report['cases']
        self.assertTrue(any(r['failure_stratum']=='reference_failure_with_required_vocabulary_missing' for r in rows))
        self.assertTrue(any(r['failure_stratum']=='reference_failure_with_vocabulary_available' for r in rows))
        for row in [r for r in rows if r['case_id']=='eva-20']:
            self.assertTrue(row['incorrect_guess'])
            self.assertTrue(row['rust_rejection'])
            self.assertFalse(row['correct_model_clarification'])
        for comparisons in report['paired_comparisons'].values():
            pair = comparisons['neighborhood-v2_minus_BM25-v1']['accepted_exposed_reference_agreement']
            self.assertEqual(pair['scheduled_pairs'],18)
            self.assertEqual(pair['attempted_pairs'],18)
            self.assertEqual(pair['missing_pairs'],0)
            self.assertGreater(pair['paired_difference'],0)
        self.assertEqual(len(rows),184)
        # Even a resealed outer run inventory cannot make raw bytes match retained observations.
        raw = runs[0] / 'diagnostic/oracle/eva-01/proposal.txt'
        original = raw.read_bytes()
        raw.write_bytes(original+b' ')
        v.dump(runs[0]/'checksums.json',v.a.v.inventory(runs[0]))
        with self.assertRaisesRegex(ValueError,'proposal/base64'):
            v.score(self.freeze,[runs[0]])
        raw.write_bytes(original)
        v.dump(runs[0]/'checksums.json',v.a.v.inventory(runs[0]))

    def test_fatal_boundaries_preserve_bytes_missingness_and_no_model_numerators(self):
        for failure in ['host','rss','template','timeout','grammar','parity']:
            with self.subTest(failure=failure):
                state,out = self.mock_run(failure=failure)
                self.assertEqual(state['status'],'blocked_or_failed')
                self.assertLess(state['generation_attempts'],94)
                rows = state['diagnostic']['cases']
                self.assertTrue(any(r['status']=='unattempted' for r in rows))
                self.assertTrue(all(not r['generation_attempted'] for r in rows if r['condition']!='oracle'))
                report = v.score(self.freeze,[out])
                metric = report['paired_comparisons']['qwen35']['neighborhood-v2_minus_BM25-v1']['exact_exposed_reference_agreement']
                self.assertEqual(metric['attempted_pairs'],0)
                self.assertIsNone(metric['paired_difference'])
                if failure == 'timeout':
                    row=next(r for r in rows if r['status']=='fatal_failure')
                    self.assertEqual(len(base64.b64decode(row['raw_base64'])),10)
                    self.assertIsNotNone(row['rust_preview'])
        baseline = v.score(self.freeze)
        self.assertTrue(all(r['exact_exposed_reference_agreement'] is None for r in baseline['cases']))
        self.assertIsNone(baseline['summary']['qwen35']['oracle']['metrics']['rust_accepted']['numerator'])
        with patch.object(v.a,'assets') as assets:
            with self.assertRaisesRegex(ValueError,'explicit v1g'):
                v.run(self.freeze,self.root/'denied','qwen35')
            with patch.dict(os.environ, {'CI':'1'}), self.assertRaisesRegex(ValueError,'CI'):
                v.run(self.freeze,self.root/'ci','qwen35',True)
            assets.assert_not_called()
        for value in [dict(returncode=1,stderr='not JSON'), dict(returncode=-9,stderr=''),
                      dict(returncode=1,stderr='{"status":"error","detail":"packet_integrity: forged"}')]:
            with self.assertRaisesRegex(ValueError,'integrity'):
                v.diagnostic.validator_guard(value)

    def test_separate_explicit_development_mechanical_all_predicates_and_empty_paths(self):
        first,second = self.root/'development', self.root/'development-second'
        development.generate(first)
        with patch.object(v.a.t,'cases',side_effect=AssertionError('Gold must never be read')):
            development.generate(second)
        self.assertEqual(v.a.v.inventory(first),v.a.v.inventory(second))
        panel = v.read(first/'panel.json')
        self.assertFalse(panel['v1g_denominator_member'])
        self.assertFalse(panel['inference_performed'])
        references = v.read(first/'references.json')
        table = v.read(v.STUDY/'catalog.json')
        for p in table['predicates']:
            rows = [r for r in references if r['gold_draft']['predicate']==p['id']]
            self.assertEqual({r['gold_draft']['direction'] for r in rows},{'forward','reverse'})
            self.assertTrue(any(r['witnesses'] for r in rows))
        for row in references:
            self.assertEqual(bool(row['witnesses']),row['kind']=='witnessed')
        for name,digest in v.read(first/'prompt-seal.json').items():
            self.assertEqual(v.sha(first/name),digest)
        self.assertEqual(len(v.read(self.freeze/'questions.json')),30)


if __name__ == '__main__':
    unittest.main()
