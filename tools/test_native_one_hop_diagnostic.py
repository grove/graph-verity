"""Deterministic v1f scheduling and original-byte Rust checks. No model assets."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import native_one_hop as a
import native_one_hop_diagnostic as d

CONFIG = a.ROOT / 'configs/native-one-hop-v1f-diagnostic.json'


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.frozen = cls.root / 'freeze'
        with patch.object(a, 'CONFIG', CONFIG):
            a.freeze(cls.frozen)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_mock(self, failure=None, key='qwen35'):
        out = self.root / f'run-{key}-{failure}'
        cases = a.experiment_cases()
        class Runtime:
            def __init__(self, *args):
                self.generation_attempts = self.generation_completed = self.candidate_bytes_received = 0
                self.startup_ms = 1
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def generate(self, context, dest, constrained=True, system=None):
                if failure == 'template' and dest.name == 'private_scope':
                    raise ValueError('Native template mismatch before completion request')
                self.generation_attempts += 1
                a.dump(dest / 'completion-request.json', {'context': context, 'constrained': constrained})
                (dest / 'prompt.txt').write_text(a.g.safe_user(context))
                sampling = dest.name.startswith('sampling-')
                if sampling:
                    draft = dict(version='nl-ask-draft-v1', status='unsupported', rationale='control')
                    if not constrained:
                        draft['forbidden'] = True
                else:
                    draft = next(c['gold_draft'].copy() for c in cases if c['question'] == context['question'])
                    if dest.name == 'repeat-1':
                        draft['rationale'] = 'Different rationale'
                        draft['predicate'] = 1002
                    if dest.name in {'ambiguous_start', 'unclear_relation'}:
                        draft = cases[0]['gold_draft'].copy()
                    if dest.name == 'malicious_label_explicit':
                        draft = dict(version='nl-ask-draft-v1', status='needs_clarification', rationale='Which predicate?')
                    if dest.name == 'private_scope' and failure == 'runtime':
                        raise TimeoutError('owned runtime deadline')
                    if dest.name == 'private_scope' and failure == 'authorization':
                        draft['rationale'] = 'PRIVATE_CANARY'
                    if dest.name == 'private_scope' and failure == 'grammar':
                        draft['extra'] = 'forbidden'
                    if dest.name == 'repeat-1' and failure == 'parity':
                        (dest / 'prompt.txt').write_text('changed')
                raw = json.dumps(draft).encode()
                (dest / 'proposal.txt').write_bytes(raw)
                # A deterministic fake transport; real Rust still receives original bytes.
                (dest / 'completion.http.sse').write_bytes(b'data: ' + json.dumps({'content': raw.decode()}).encode() + b'\n')
                self.generation_completed += 1
                self.candidate_bytes_received += len(raw)
                result = dict(elapsed_ms=1, tokens_predicted=1)
                a.dump(dest / 'runtime.json', result)
                return result
        def sample(out, done, rss):
            rss.update(samples=1, peak_kib=100)
            if failure == 'resource':
                rss['peak_kib'] = 25 * 2**20
        host = dict(blockers=[{'metric': 'load'}] if failure == 'host' else [], captured_at=datetime.now(timezone.utc).isoformat())
        evidence = {'candidates': {key: {'preparation_receipt': {'commands': [[], [], ['mock']]}}}}
        verify = a.verify_freeze
        def verify_source(*args):
            if failure == 'source' and out.exists():
                raise ValueError('Changed frozen source')
            return verify(*args)
        with patch.object(a, 'assets', return_value=evidence), patch.object(a, 'grammar_controls'), \
             patch.object(a, 'preflight', return_value=host), patch.object(a, 'Runtime', Runtime), \
             patch.object(a, 'sample_rss', side_effect=sample), \
             patch.object(a, 'verify_freeze', side_effect=verify_source), \
             patch.object(a, 'grammar_check', side_effect=lambda raw, *args: 'forbidden' not in raw), \
             patch.dict(os.environ, {}, clear=True):
            state = a.run(self.frozen, out, key, True)
        return state, out

    def test_complete_independent_accounting_rejections_and_raw_replay_both_models(self):
        with patch.object(a, 'CONFIG', CONFIG):
            for key in a.config()['variants']:
                state, out = self.run_mock(key=key)
                self.assertEqual(state['status'], 'completed_diagnostic')
                diag = state['diagnostic']
                self.assertEqual((diag['denominator'], diag['attempted'], diag['completed']), (36, 36, 36))
                self.assertEqual(state['generation_completed'], 38)
                self.assertFalse(diag['semantic_go'])
                self.assertFalse(diag['repeatability']['gate_passed'])
                self.assertEqual(state['decision'], 'INCONCLUSIVE_REVISE')
                self.assertFalse(state['controls_passed'])
                self.assertFalse(state['smoke_passed'])
                for condition in ['oracle', 'retrieval']:
                    rows = {r['name']: r for r in diag['cases'] if r['condition'] == condition}
                    for name in ['ambiguous_start', 'unclear_relation']:
                        row = rows[name]
                        self.assertEqual(row['status'], 'validator_rejection')
                        self.assertEqual(row['model_origin_status'], 'candidate')
                        self.assertIn('deterministic_preflight_block' if condition == 'oracle' else 'invalid_catalog_reference', row['rust_preview']['stderr'])
                        self.assertFalse(row['reference']['semantic_correct'])
                    self.assertEqual(rows['malicious_label_explicit']['status'], 'model_semantic_failure')
                    self.assertTrue(all(rows['smoke-' + cid]['generation_attempted'] for cid in a.config()['smoke_cases']))
                for row in diag['cases']:
                    dest = out / 'diagnostic' / row['condition'] / row['name']
                    self.assertEqual(base64.b64decode(row['raw_base64']), (dest / 'proposal.txt').read_bytes())
                    self.assertEqual(hashlib.sha256(base64.b64decode(row['raw_base64'])).hexdigest(), row['raw_sha256'])
                    self.assertIsNotNone(row['latency_ms'])
                    self.assertIsNotNone(row['resources'])
                    self.assertIsNotNone(row['source_evidence_sufficiency'])
                self.assertTrue(a.replay(self.frozen, out)['verified'])
                self.assertEqual(state['executions'], 0)
                self.assertEqual(a.read(out / 'checksums.json'), a.v.inventory(out))

    def test_fatal_runtime_host_resource_authorization_and_integrity_leave_missing_cases(self):
        with patch.object(a, 'CONFIG', CONFIG):
            for failure in ['runtime', 'host', 'resource', 'authorization', 'grammar', 'parity', 'source', 'template']:
                with self.subTest(failure=failure):
                    state, out = self.run_mock(failure)
                    self.assertNotEqual(state['status'], 'completed_diagnostic')
                    rows = state['diagnostic']['cases']
                    self.assertTrue(any(r['status'] == 'unattempted' for r in rows))
                    self.assertTrue(all(not r['generation_attempted'] for r in rows if r['condition'] == 'retrieval'))
                    self.assertFalse(state['smoke_passed'])
                    self.assertEqual(state['diagnostic']['attempted'], max(0, state['generation_attempts'] - 2))
                    if failure == 'template':
                        row = next(r for r in rows if r['status'] == 'fatal_failure')
                        self.assertFalse(row['generation_attempted'])
                        self.assertIsNone(row['raw_output'])
                    if failure == 'host':
                        self.assertFalse(state['model_loaded'])
                    else:
                        self.assertTrue(any(r['status'] == 'fatal_failure' for r in rows))
                    self.assertEqual(a.read(out / 'checksums.json'), a.v.inventory(out))

    def test_opt_in_ci_strict_evaluation_and_unexpected_validator_fail_closed(self):
        with patch.object(a, 'CONFIG', CONFIG), patch.object(a, 'assets') as assets:
            with self.assertRaisesRegex(ValueError, '--allow-inference'):
                a.run(self.frozen, self.root / 'denied', 'qwen35')
            with patch.dict(os.environ, {'CI': 'true'}), self.assertRaisesRegex(ValueError, 'forbidden in CI'):
                a.run(self.frozen, self.root / 'ci-denied', 'qwen35', True)
            with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, 'separate from strict'):
                a.run(self.frozen, self.root / 'evaluation-denied', 'qwen35', True, True)
            assets.assert_not_called()
        for code, stderr in [(-9, ''), (1, 'not JSON'), (1, '{"status":"error","detail":"io: failed"}')]:
            with self.assertRaisesRegex(ValueError, 'integrity'):
                d.validator_guard(dict(returncode=code, stderr=stderr))

    def test_gold_independent_freeze_identical_v1e_contexts_and_history_immutable(self):
        with patch.object(a, 'CONFIG', CONFIG), tempfile.TemporaryDirectory() as temp:
            second = Path(temp) / 'second'
            poisoned = [{**c, 'gold_draft': {}, 'gold_request': {}, 'resolved_start': 65535,
                         'expected_status': 'POISON', 'preflight_blocked': True} for c in a.experiment_cases()]
            with patch.object(a, 'experiment_cases', return_value=poisoned):
                a.freeze(second)
            for path in (self.frozen / 'contexts').glob('*.json'):
                self.assertEqual(path.read_bytes(), (second / 'contexts' / path.name).read_bytes())
                self.assertFalse({'gold_draft', 'gold_request', 'expected_status', 'resolved_start', 'blocked'} & a.read(path).keys())
            old = Path(temp) / 'v1e'
            with patch.object(a, 'CONFIG', a.ROOT / 'configs/native-one-hop-v1e.json'):
                a.freeze(old)
            for path in (self.frozen / 'contexts').glob('*.json'):
                self.assertEqual(path.read_bytes(), (old / 'contexts' / path.name).read_bytes())
            with self.assertRaisesRegex(ValueError, 'Never overwrite'):
                a.freeze(self.frozen)
        changed = subprocess.check_output(['git', 'diff', '3b874232f77f21b3b4d976aac905f604f6054c0c', '--',
            'reports/issue-83-native-one-hop', 'reports/issue-83-native-one-hop-v1d',
            'reports/issue-83-native-one-hop-v1e', 'reports/issue-74-one-hop-trial', 'studies/nl-ask-v1'], cwd=a.ROOT)
        self.assertEqual(changed, b'')

    def test_committed_preregistration_blind_package_and_history_without_models(self):
        report = a.ROOT / 'reports/issue-83-native-one-hop-v1f-diagnostic'
        prereg = a.read(report / 'preregistration.json')
        self.assertFalse(prereg['inference_authorized'])
        self.assertFalse(prereg['inference_performed'])
        self.assertEqual(a.sha(report / 'evidence.tar.gz'), prereg['evidence_archive_sha256'])
        payload = a.g.archive_files(report / 'evidence.tar.gz')
        manifest = a.read(report / 'evidence-files.json')
        self.assertEqual({n: hashlib.sha256(raw).hexdigest() for n, raw in payload.items()}, manifest['files'])
        frozen = json.loads(payload['freeze/freeze.json'])
        for name, digest in frozen['input_sha256'].items():
            self.assertEqual(hashlib.sha256(payload['source/' + name]).hexdigest(), digest)
            if name == 'tools/native_one_hop.py':
                original = subprocess.check_output(['git', 'show', prereg['source_commit'] + ':' + name], cwd=a.ROOT)
                self.assertEqual(hashlib.sha256(original).hexdigest(), digest)
            else:
                self.assertEqual(a.sha(a.ROOT / name), digest)
        self.assertEqual(hashlib.sha256(payload['freeze/checksums.json']).hexdigest(), prereg['freeze_sha256'])
        for name, digest in a.read(report / 'historical-sha256.json').items():
            self.assertEqual(a.sha(a.ROOT / name), digest, name)
        review = report / 'blind-review'
        questions = a.read(review / 'questions.json')
        self.assertEqual(len(questions), 17)
        mapping = a.read(report / 'review-coordinator.json')
        self.assertEqual(set(mapping), {q['review_id'] for q in questions})
        self.assertTrue(all(q['reviewer'] is None and q['findings'] is None for q in questions))
        for q in questions:
            self.assertEqual(set(q), {'review_id', 'question', 'language', 'reviewer', 'findings'})
        self.assertEqual((review / 'source.nq').read_bytes(), (a.t.STUDY / 'snapshot.nq').read_bytes())
        table = a.read(review / 'vocabulary.json')
        self.assertEqual(set(table), {'snapshot_id', 'graphs', 'entities', 'predicates'})
        self.assertEqual(a.read(review / 'checksums.json'), a.v.inventory(review))
        decision = a.read(report / 'decision.json')
        for key in ['qwen35', 'gemma4']:
            rows = decision['models'][key]['cases']
            self.assertEqual(len(rows), 36)
            self.assertTrue(all(r['status'] == 'unattempted' and r['raw_output'] is None for r in rows))


if __name__ == '__main__':
    unittest.main()
