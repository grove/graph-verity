"""Model-free execution contracts; synthetic drafts are never model evidence."""
import base64
import copy
from functools import lru_cache
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import predicate_diagnostics_native as n


class FakeRuntime:
    def __init__(self, folder, fail=None, raw=None):
        self.folder, self.fail, self.raw = folder, fail, raw
        self.generation_attempts = self.generation_completed = self.candidate_bytes_received = 0
        self.calls = []

    def generate(self, context, dest, constrained=True, system=None):
        key = dest.name
        self.calls.append(key)
        self.generation_attempts += 1
        messages = n.read(self.folder / 'messages' / (key + '.json'))
        assert system == messages[0]['content']
        assert context == n.read(self.folder / 'contexts' / (key + '.json'))
        assert constrained == (key != 'sampling-unconstrained')
        n.dump(dest / 'messages.json', messages)
        # The repeat's prompt and completion bodies must be identical.
        (dest / 'prompt.txt').write_bytes(messages[1]['content'].encode())
        n.dump(dest / 'completion-request.json', dict(prompt=messages, constrained=constrained))
        refs = n.read(self.folder / 'expected.json')
        ref = refs.get(key)
        draft = dict(version='nl-ask-draft-v1', status=ref['expected_status'] if ref else 'unsupported', rationale='synthetic')
        if ref and ref['fields']:
            draft.update(ref['fields'])
        if key == 'sampling-unconstrained':
            draft['forbidden'] = True
        raw = self.raw if self.raw is not None and key == self.fail else json.dumps(draft).encode()
        (dest / 'proposal.txt').write_bytes(raw)
        (dest / 'completion.http.sse').write_bytes(b'data: ' + raw + b'\n\n')
        self.candidate_bytes_received += len(raw)
        if key == self.fail:
            raise TimeoutError('synthetic deadline')
        self.generation_completed += 1
        return dict(stopped_limit=False)


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='predicate-native-tests-')
        cls.folder = Path(cls.temp.name) / 'freeze'
        with patch.object(n.d, 'inputs', return_value={}):
            n.d.prepare(cls.folder)
        # Exact registered tokenizer receipt: no tokenizer or model is loaded by these tests.
        cls.original = n.a.g.archive_files(n.d.RELEASE / 'freeze.tar.gz')
        (cls.folder / 'token-counts.json').write_bytes(cls.original['token-counts.json'])
        n.dump(cls.folder / 'checksums.json', n.a.v.inventory(cls.folder))
        cls.cfg = n.read(cls.folder / 'freeze.json')['runtime_config']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def state(self):
        return dict(version=n.VERSION, registration_sha256='test', executions=0,
            integration_authorized=False, holdout_accessed=False,
            rows=[dict(**r, status='unattempted', attempted=False, failure=None, packet_id=None,
                       raw_base64=None, raw_sha256=None) for r in n.read(self.folder / 'schedule.json')])

    def execute(self, out, state, runtime):
        with patch.object(n, 'verify', return_value={}), n.native_config(self.cfg):
            n.observe(self.folder, out, state, runtime, dict(samples=1, peak_kib=1, error=None), self.cfg)

    def test_all_126_exact_requests_independent_scores_and_raw_replay(self):
        # Repeated scoring/replay uses identical Rust inputs; execute each distinct preview once.
        original = n.d.preview
        bounded = n.a.bounded
        def preview_only(args, *rest, **kwargs):
            self.assertTrue(Path(args[0]) == n.d.v.BRIDGE or
                            (Path(args[0]) == n.a.BINARY and args[1] == 'nl-ask-preview'))
            return bounded(args, *rest, **kwargs)
        with patch.object(n.d, 'preview', side_effect=lru_cache(maxsize=None)(original)), \
             patch.object(n.a, 'bounded', side_effect=preview_only):
            self.check_full_schedule()

    def check_full_schedule(self):
        with tempfile.TemporaryDirectory() as temp:
            out, state = Path(temp), self.state()
            runtime = FakeRuntime(self.folder)
            # Rust previews are real. Only the native character validator is replaced on CI.
            with patch.object(n.a, 'grammar_check', side_effect=lambda raw, ctx, dest: dest.name != 'sampling-unconstrained'):
                self.execute(out, state, runtime)
            expected = n.read(self.folder / 'schedule.json')
            self.assertEqual(runtime.calls, [r['id'] for r in expected])
            self.assertEqual(runtime.generation_attempts, 126)
            self.assertTrue(all(r['status'] == 'completed' and r['attempted'] for r in state['rows']))
            report = n.score(self.folder, state)
            self.assertEqual((report['scheduled'], report['completed'], report['paired_completed']), (126, 126, 31))
            self.assertEqual(report['model_generated_rdf_executions'], 0)
            explicit = [r for r in report['rows'] if r['experiment'] == 'explicit_iri_construction']
            self.assertEqual(len(explicit), 60)
            self.assertEqual(sum(r['measurement']['reference_agreement'] for r in explicit), 60)
            rejected = [r['id'] for r in explicit if not r['measurement']['rust_accepted']]
            self.assertEqual(rejected, ['explicit-' + i for i in ['003', '006', '013', '020', '028', '035', '038', '042', '049', '056']])
            self.assertTrue(all(r['measurement']['model_status'] == 'candidate' for r in explicit))
            self.assertTrue(all(p['reference_agreement_delta'] == 0 for p in report['natural_language_pairs']))
            # A Rust-compatible wrong direction fails construction fidelity without changing metadata scores.
            changed = copy.deepcopy(state)
            row = next(r for r in changed['rows'] if r['id'] == 'explicit-003')
            draft = json.loads(base64.b64decode(row['raw_base64']))
            draft['direction'] = 'forward'
            row['raw_base64'] = base64.b64encode(json.dumps(draft).encode()).decode()
            altered = n.score(self.folder, changed)
            scored = next(r for r in altered['rows'] if r['id'] == 'explicit-003')
            self.assertTrue(scored['measurement']['rust_accepted'])
            self.assertFalse(scored['measurement']['reference_agreement'])
            self.assertEqual(altered['natural_language_pairs'], report['natural_language_pairs'])
            n.dump(out / 'run.json', state)
            n.dump(out / 'score.json', report)
            n.dump(out / 'checksums.json', n.a.v.inventory(out))
            with patch.object(n, 'verify'), patch.object(n, 'sha', return_value='test'):
                self.assertEqual(n.replay(self.folder, out)['raw_previews'], 126)
                (out / 'requests/explicit-003/proposal.txt').write_bytes(b'changed')
                n.dump(out / 'checksums.json', n.a.v.inventory(out))
                with self.assertRaisesRegex(ValueError, 'original response bytes'):
                    n.replay(self.folder, out)

    def test_exact_original_messages_and_metadata_isolation(self):
        rows = n.identities(self.folder)
        self.assertEqual(len(rows), 126)
        for row in rows:
            key = row['id']
            self.assertEqual((self.folder / 'messages' / (key + '.json')).read_bytes(), self.original['messages/' + key + '.json'])
            self.assertEqual((self.folder / 'contexts' / (key + '.json')).read_bytes(), self.original['contexts/' + key + '.json'])
        pairs = rows[64:]
        self.assertEqual(len(pairs), 62)
        self.assertEqual(pairs[-1]['case_id'], 'v1e-label-explicit')
        for index in range(31):
            left, right = pairs[index * 2:index * 2 + 2]
            self.assertEqual([left['condition'], right['condition']],
                             ['no_metadata', 'metadata'] if index % 2 == 0 else ['metadata', 'no_metadata'])
            contexts = [n.read(self.folder / 'contexts' / (r['id'] + '.json')) for r in [left, right]]
            for context in contexts:
                for pred in context['predicates']:
                    pred['source_metadata'] = []
            self.assertEqual(*contexts)
            self.assertNotEqual(left['packet_id'], right['packet_id'])

    def test_fatal_timeout_keeps_invalid_original_bytes_and_all_missing_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            out, state = Path(temp), self.state()
            raw = b'\xff{"status":"candidate",'
            runtime = FakeRuntime(self.folder, fail='repeat-0', raw=raw)
            with patch.object(n.a, 'grammar_check', side_effect=lambda raw, ctx, dest: dest.name != 'sampling-unconstrained'):
                with self.assertRaisesRegex(TimeoutError, 'synthetic deadline'):
                    self.execute(out, state, runtime)
            self.assertEqual(runtime.calls, ['sampling-unconstrained', 'sampling-constrained', 'repeat-0'])
            failed = state['rows'][2]
            self.assertEqual(base64.b64decode(failed['raw_base64']), raw)
            self.assertEqual(failed['raw_sha256'], n.d.m.digest(raw))
            self.assertIsNotNone(failed['rust_preview'])
            self.assertEqual((out / 'requests/repeat-0/proposal.txt').read_bytes(), raw)
            report = n.score(self.folder, state)
            self.assertEqual(report['completed'], 2)
            self.assertEqual(report['paired_completed'], 0)
            self.assertTrue(all(r['measurement'] is None or r['measurement']['reference_agreement'] is None
                                for r in report['rows'][2:]))
            n.dump(out / 'run.json', state)
            n.dump(out / 'score.json', report)
            n.dump(out / 'checksums.json', n.a.v.inventory(out))
            with patch.object(n, 'verify'), patch.object(n, 'sha', return_value='test'):
                self.assertEqual(n.replay(self.folder, out)['raw_previews'], 3)

    def test_integrity_resource_private_grammar_and_validator_failures_stop_schedule(self):
        scenarios = [
            ('resource', patch.object(n.h.d, 'resource_guard', side_effect=ValueError('RSS unavailable')), 0),
            ('packet', patch.object(n, 'packet', side_effect=ValueError('Stale source')), 0),
            ('trusted', patch.object(n, 'preview', return_value=dict(returncode=2)), 0),
            ('validator', patch.object(n.h.d, 'validator_guard', side_effect=ValueError('Unexpected Rust/runtime integrity failure')), 1),
            ('grammar', patch.object(n.a, 'grammar_check', return_value=True), 1),
        ]
        for name, guard, attempts in scenarios:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp, guard:
                runtime, state = FakeRuntime(self.folder), self.state()
                with self.assertRaises(ValueError):
                    self.execute(Path(temp), state, runtime)
                self.assertEqual(runtime.generation_attempts, attempts)
                self.assertEqual(state['rows'][0]['status'], 'fatal_failure')
                self.assertTrue(all(r['status'] == 'unattempted' for r in state['rows'][1:]))

    def test_private_canary_and_repeat_request_mismatch_are_fatal(self):
        original = FakeRuntime.generate
        for target, change in [('sampling-unconstrained', 'private'), ('repeat-1', 'repeat')]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                runtime, state = FakeRuntime(self.folder), self.state()
                def generate(context, dest, **kwargs):
                    result = original(runtime, context, dest, **kwargs)
                    if dest.name == target:
                        if change == 'private':
                            (dest / 'proposal.txt').write_bytes(b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"PRIVATE_CANARY","forbidden":true}')
                        else:
                            (dest / 'completion-request.json').write_bytes(b'changed')
                    return result
                with patch.object(runtime, 'generate', side_effect=generate), \
                     patch.object(n.a, 'grammar_check', side_effect=lambda raw, ctx, dest: dest.name != 'sampling-unconstrained'):
                    with self.assertRaisesRegex(ValueError, 'authorization|Repeat prompt/request'):
                        self.execute(Path(temp), state, runtime)
                self.assertEqual(runtime.calls[-1], target)
                self.assertEqual(state['rows'][len(runtime.calls) - 1]['status'], 'fatal_failure')

    def test_stale_source_and_saved_packet_fail_before_rust(self):
        key = 'explicit-003'
        saved = n.read(self.folder / 'context-packets' / (key + '.json'))
        with patch.object(n.d.v, 'preview') as rust:
            with self.assertRaisesRegex(ValueError, 'Stale'):
                n.preview(self.folder, key, b'{}', 'stale')
            changed = {**n.d.m.build(), 'source_revision': 'stale'}
            with patch.object(n.d.m, 'build', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'Stale'):
                    n.preview(self.folder, key, b'{}', saved['packet_id'])
            rust.assert_not_called()

    def test_authority_ci_no_retry_and_registered_destinations(self):
        with patch.object(n, 'verify') as verify, patch.object(n.h, 'Runtime') as runtime:
            with self.assertRaisesRegex(ValueError, 'Separate explicit authorization'):
                n.run()
            verify.assert_not_called()
            runtime.assert_not_called()
            with patch.dict(n.os.environ, {'CI': '1'}):
                with self.assertRaisesRegex(ValueError, 'forbidden in CI'):
                    n.run(True)
            runtime.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for existing in ['ledger', 'output']:
                ledger, out = root / ('attempt-' + existing), root / ('run-' + existing)
                if existing == 'ledger':
                    ledger.write_text('consumed')
                else:
                    out.mkdir()
                with patch.object(n, 'LEDGER', ledger), patch.object(n, 'OUTPUT', out), \
                     patch.object(n, 'verify', return_value={'runtime_config': self.cfg}), \
                     patch.object(n.h, 'Runtime') as runtime, patch.dict(n.os.environ, {}, clear=True):
                    with self.assertRaisesRegex(ValueError, 'No overwrite or retry'):
                        n.run(True)
                    runtime.assert_not_called()

    def test_runtime_rejects_unregistered_parity_before_completion(self):
        runtime = n.h.Runtime(self.cfg, n.a.g.ASSETS, 'qwen35', Path(self.temp.name))
        runtime.allowed_prompts = {}
        with patch.object(n.a.Runtime, 'template_parity', return_value=dict(prompt='changed', tokens=[1])), \
             patch.object(runtime, 'post') as post:
            with self.assertRaisesRegex(ValueError, 'Prompt/token IDs differ'):
                runtime.generate({}, Path(self.temp.name))
            post.assert_not_called()
            self.assertEqual(runtime.generation_attempts, 0)

    def test_registration_append_only_and_rejects_rebound_inputs(self):
        with tempfile.TemporaryDirectory(dir=n.ROOT / 'artifacts') as temp:
            release = Path(temp)
            (release / 'README.md').write_bytes((n.RELEASE / 'README.md').read_bytes())
            local = release / 'freeze'
            shutil.copytree(self.folder, local)
            with patch.object(n, 'REGISTRATION', release / 'registration.json'), \
                 patch.object(n, 'RELEASE', release), patch.object(n, 'FREEZE', local), \
                 patch.object(n, 'committed'), patch.object(n.d, 'verify_registration',
                    return_value=n.read(self.folder / 'freeze.json')):
                n.register(local)
                n.verify(local)
                with self.assertRaisesRegex(ValueError, 'Append-only'):
                    n.register(local)
                reg = n.read(n.REGISTRATION)
                for field, value, message in [
                    ('scorer_sha256', 'stale', 'scorer'),
                    ('runtime_config', {}, 'runtime/binary'),
                    ('destinations', {}, 'boundaries'),
                    ('schedule', [], 'schedule/packets/prompts')]:
                    n.dump(n.REGISTRATION, {**reg, field: value})
                    with self.assertRaisesRegex(ValueError, message):
                        n.verify(local)
                n.dump(n.REGISTRATION, reg)

    def test_host_and_preload_failures_consume_attempt_without_loading_model(self):
        frozen = n.read(self.folder / 'freeze.json')
        host = dict(blockers=['synthetic host admission'], captured_at=n.datetime.now(n.timezone.utc).isoformat())
        for failure in ['assets', 'tokens', 'grammar', 'host', 'stale_host']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                evidence = copy.deepcopy(frozen['runtime_identity'])
                with patch.object(n, 'FREEZE', self.folder), patch.object(n, 'OUTPUT', root / 'run'), \
                     patch.object(n, 'LEDGER', root / 'attempt.json'), patch.object(n, 'sha', return_value='test'), \
                     patch.object(n, 'verify', return_value=frozen), patch.object(n.h, 'Runtime') as runtime, \
                     patch.object(n, 'recount', return_value=[], side_effect=ValueError('token failure') if failure == 'tokens' else None), \
                     patch.object(n.a, 'assets', return_value=evidence, side_effect=ValueError('asset failure') if failure == 'assets' else None), \
                     patch.object(n.a, 'grammar_controls', side_effect=ValueError('grammar failure') if failure == 'grammar' else None), \
                     patch.object(n.a, 'preflight', return_value=host if failure == 'host' else dict(blockers=[], captured_at='2000-01-01T00:00:00+00:00')), \
                     patch.dict(n.os.environ, {}, clear=True):
                    state = n.run(True)
                    runtime.assert_not_called()
                    self.assertTrue((root / 'attempt.json').exists())
                    self.assertEqual(state['status'], 'blocked_or_failed')
                    self.assertFalse(state['inference_performed'])
                    self.assertTrue(all(r['status'] == 'unattempted' for r in state['rows']))
                    self.assertEqual(n.read(root / 'run/score.json')['completed'], 0)
                    with self.assertRaisesRegex(ValueError, 'No overwrite or retry'):
                        n.run(True)


if __name__ == '__main__':
    unittest.main()
