"""Synthetic interruption checks: temporary paths, no native/model/RDF execution."""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import ask_alpha_trial_observable_r2 as t
import ask_alpha_register_observable_r2 as registration


class InterruptedAttempt(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)
            freeze, output = root/'freeze', root/'run'
            (root/'artifacts').mkdir()
            reg = root/'registration.json'
            t.b.write(reg, {'synthetic': True})
            schedule = [dict(id=key, kind='native_control', constrained=True) for key in ['sampling-0', 'sampling-1']]
            counts = dict(models=dict(qwen35=dict(rows=[])))
            t.b.write(freeze/'schedule.json', schedule)
            t.b.write(freeze/'token-counts.json', counts)
            t.b.write(freeze/'contexts/alpha-01.json', {})
            for row in schedule:
                t.b.write(freeze/'contexts'/(row['id']+'.json'), {})
                t.b.write(freeze/'messages'/(row['id']+'.json'), [dict(content='synthetic')])
            frozen = dict(runtime_config=dict(host_max_age_seconds=60), runtime_identity=dict(synthetic='identity'))
            assets = dict(synthetic='identity', candidates=dict(qwen35=dict(preparation_receipt=dict(commands=[[], [], ['synthetic-python']]))))
            runtime = MagicMock()
            runtime.generation_attempts = runtime.generation_completed = runtime.candidate_bytes_received = 0
            runtime.startup_ms = 0
            runtime.generate.side_effect = KeyboardInterrupt('before dispatch')
            def tokenizer(args, directory, *unused):
                t.b.write(directory/'token-counts.json', counts)
                return 0
            def samples(directory, done, rss):
                rss['samples'] = 1
            patches = [
                patch.multiple(t, ROOT=root, FREEZE=freeze, OUTPUT=output, REG=reg,
                               LEDGER=root/'attempt.json', JOURNAL=root/'stages.jsonl', DIAGNOSTICS=root/'diagnostics.json'),
                patch.object(t, 'verify', return_value=frozen),
                patch.object(t.subprocess, 'check_output', return_value=reg.read_bytes()),
                patch.object(t.a, 'assets', return_value=assets),
                patch.object(t.a, 'bounded', side_effect=tokenizer),
                patch.object(t.a, 'grammar_controls'),
                patch.object(t.a, 'preflight', return_value=dict(captured_at=datetime.now(timezone.utc).isoformat(), blockers=[])),
                patch.object(t.a, 'sample_rss', side_effect=samples),
                patch.object(t.h.d, 'resource_guard'),
                patch.object(t.b, 'bundle'),
                patch.object(t, 'Runtime', return_value=runtime),
                patch.object(t.e, 'packets', return_value={}),
                patch.object(t.e, 'rust_preview', side_effect=AssertionError('No RDF preview in interruption fixture')),
                patch.object(t.e, 'score', return_value={'synthetic': True}),
                patch.object(t.e, 'markdown', return_value='Synthetic report'),
                patch.dict(os.environ, CI='', GITHUB_ACTIONS=''),
            ]
            mocks = [stack.enter_context(p) for p in patches]
            yield root, runtime, mocks

    def assert_consumed(self, root, runtime, error, stage, counters_unknown=True):
        with self.assertRaises(type(error)) as caught:
            t.run(True)
        self.assertIs(caught.exception, error)
        before = (root/'attempt.json').read_bytes()
        state = t.b.read(root/'diagnostics.json')
        self.assertEqual(state['exception']['exception_class'], type(error).__qualname__)
        self.assertEqual(state['exception']['message'], str(error))
        self.assertIn('Traceback', state['exception']['traceback'])
        self.assertEqual(state['failure_last_entered_stage'], stage)
        self.assertEqual(state['status'], 'blocked_or_failed')
        self.assertEqual(len(state['remaining_scheduled_requests']), 2)
        self.assertEqual(state['executions'], 0)
        if counters_unknown:
            for field in ['generation_attempts', 'generation_completed', 'candidate_bytes_received', 'inference_performed']:
                self.assertIsNone(state[field], field)
            runtime.generate.assert_not_called()
        records = [json.loads(line) for line in (root/'stages.jsonl').read_text().splitlines()]
        entries = [row for row in records if row['stage'] == stage and row['status'] == 'entered']
        self.assertEqual(len(entries), 1)
        self.assertTrue(all(row['utc'].endswith('+00:00') and row['elapsed_seconds'] >= 0 for row in records))
        with self.assertRaisesRegex(ValueError, 'Consumed registration'):
            t.run(True)
        self.assertEqual((root/'attempt.json').read_bytes(), before)
        self.assertEqual(sum(row['stage'] == 'attempt_ledger_creation' and row['status'] == 'completed' for row in records), 1)
        return state

    def test_interruptions_before_and_during_preload(self):
        for target, stage in [('ledger_completed', 'attempt_ledger_creation'),
                              ('output_entered', 'output_directory_initialization'),
                              ('asset_entered', 'asset_verification'),
                              ('assets', 'asset_verification'), ('bounded', 'tokenizer_recount'),
                              ('preflight', 'host_admission')]:
            for error_type in [KeyboardInterrupt, SystemExit, RuntimeError]:
                with self.subTest(target=target, error=error_type.__name__), self.fixture() as (root, runtime, mocks):
                    error = error_type('synthetic '+target)
                    if target in ['assets', 'bounded', 'preflight']:
                        def interrupt(*args, **kwargs):
                            t.b.write(root/'run/partial.json', {'retained': True})
                            raise error
                        extra = patch.object(getattr(t.a, target), 'side_effect', interrupt)
                    else:
                        original_record = t.Stages.record
                        selected, status = {'ledger_completed': ('attempt_ledger_creation', 'completed'),
                                            'output_entered': ('output_directory_initialization', 'entered'),
                                            'asset_entered': ('asset_verification', 'entered')}[target]
                        def interrupt(stages, current, event, *args, **kwargs):
                            original_record(stages, current, event, *args, **kwargs)
                            if (current, event) == (selected, status):
                                raise error
                        extra = patch.object(t.Stages, 'record', interrupt)
                    with extra:
                        state = self.assert_consumed(root, runtime, error, stage)
                    if target in ['assets', 'bounded', 'preflight']:
                        self.assertTrue(t.b.read(root/'run/partial.json')['retained'])
                        self.assertIn('partial.json', t.b.read(root/'run/checksums.json'))
                    self.assertEqual(state['evidence_finalization'], 'completed')
                    t.e.rust_preview.assert_not_called()

    def test_startup_and_before_first_request_preserve_measured_zeros(self):
        for target, stage in [('startup', 'model_startup'), ('generate', 'request')]:
            with self.subTest(target=target), self.fixture() as (root, runtime, mocks):
                error = KeyboardInterrupt('synthetic '+target)
                if target == 'startup':
                    runtime.__enter__.side_effect = error
                else:
                    runtime.generate.side_effect = error
                state = self.assert_consumed(root, runtime, error, stage, counters_unknown=False)
                self.assertEqual(state['generation_attempts'], 0)
                self.assertEqual(state['generation_completed'], 0)
                self.assertEqual(state['model_startup_confirmed'], target != 'startup')
                if target == 'startup':
                    runtime.generate.assert_not_called()
                runtime.__exit__.assert_called_once()

    def test_cleanup_and_scoring_do_not_replace_original_interrupt(self):
        with self.fixture() as (root, runtime, mocks):
            original = KeyboardInterrupt('original cause')
            runtime.generate.side_effect = original
            runtime.__exit__.side_effect = RuntimeError('cleanup cause')
            t.e.score.side_effect = SystemExit('finalization cause')
            state = self.assert_consumed(root, runtime, original, 'request', counters_unknown=False)
            self.assertEqual(state['evidence_finalization'], 'failed')
            self.assertEqual([r['message'] for r in state['secondary_errors']], ['cleanup cause', 'finalization cause'])
            self.assertTrue((root/'run/checksums.json').exists())

    def test_finalization_failure_is_fatal_even_after_completed_schedule(self):
        with self.fixture() as (root, runtime, mocks):
            t.b.write(root/'freeze/schedule.json', [])
            error = SystemExit('finalization only')
            t.e.score.side_effect = error
            with self.assertRaises(SystemExit) as caught:
                t.run(True)
            self.assertIs(caught.exception, error)
            state = t.b.read(root/'diagnostics.json')
            self.assertEqual(state['status'], 'blocked_or_failed')
            self.assertEqual(state['exception']['message'], str(error))
            self.assertEqual(state['evidence_finalization'], 'failed')

    def test_verification_and_lock_failures_are_also_single_invocations(self):
        for target in ['verify', 'lock']:
            with self.subTest(target=target), self.fixture() as (root, runtime, mocks):
                error = RuntimeError('synthetic '+target)
                extra = patch.object(t, 'verify', side_effect=error) if target == 'verify' else patch.object(t.fcntl, 'flock', side_effect=error)
                with extra, self.assertRaises(RuntimeError):
                    t.run(True)
                runtime.generate.assert_not_called()
                state = t.b.read(root/'diagnostics.json')
                self.assertIsNone(state['generation_attempts'])
                with self.assertRaisesRegex(ValueError, 'Consumed registration'):
                    t.run(True)

    def test_historical_ledger_bytes_rejected_in_isolated_copy(self):
        with self.fixture() as (root, runtime, mocks):
            # Copy the published evidence, never open the actual consumed ledger for writing.
            consumed = (t.original.ROOT/'experiments/ask-alpha-v1-interruption-evidence/raw/attempt.json').read_bytes()
            (root/'attempt.json').write_bytes(consumed)
            with self.assertRaisesRegex(ValueError, 'Consumed registration'):
                t.run(True)
            self.assertEqual((root/'attempt.json').read_bytes(), consumed)
            self.assertFalse((root/'stages.jsonl').exists())
            runtime.generate.assert_not_called()

    def test_completion_dispatch_stage_and_partial_stream_survive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (root/'stages.jsonl').open('x') as stream:
                stages = t.Stages(stream)
                runtime = t.Runtime({}, root, 'qwen35', root)
                runtime.stages, runtime.dispatched = stages, []
                error = KeyboardInterrupt('transport interruption')
                def transport(*args):
                    (root/'partial.sse').write_bytes(b'data: {')
                    raise error
                with patch.object(t.h.Runtime, 'post', side_effect=transport), self.assertRaises(KeyboardInterrupt):
                    runtime.post('completion', {}, root/'request-0/completion')
                self.assertEqual(stages.last_entered, 'first_request_dispatch')
                self.assertEqual(runtime.dispatched, ['request-0'])
                self.assertEqual((root/'partial.sse').read_bytes(), b'data: {')
                with patch.object(t.h.Runtime, 'post', return_value={}) as post:
                    runtime.post('completion', {'unchanged': True}, root/'request-1/completion')
                    post.assert_called_once_with('completion', {'unchanged': True}, root/'request-1/completion')
                self.assertEqual(stages.last_completed, 'request_dispatch')

    def test_inherited_startup_cleanup_preserves_active_exception(self):
        runtime = t.Runtime({}, Path('.'), 'qwen35', Path('.'))
        runtime.stages = t.Stages(io.StringIO())
        with patch.object(t.h.Runtime, '__exit__', side_effect=RuntimeError('cleanup')):
            try:
                raise KeyboardInterrupt('startup')
            except KeyboardInterrupt:
                runtime.__exit__()
        self.assertEqual(runtime.stages.secondary_errors[0]['message'], 'cleanup')

    def test_request_receipt_failure_does_not_replace_original(self):
        with self.fixture() as (root, runtime, mocks):
            original = KeyboardInterrupt('primary request cause')
            runtime.generate.side_effect = original
            write = t.durable_write
            failed = False
            def once(path, value):
                nonlocal failed
                if path == root/'run/run.json' and value['controls'] and not failed:
                    failed = True
                    raise OSError('receipt write failure')
                return write(path, value)
            with patch.object(t, 'durable_write', side_effect=once):
                state = self.assert_consumed(root, runtime, original, 'request', counters_unknown=False)
            self.assertEqual(state['secondary_errors'][0]['message'], 'receipt write failure')

    def test_archive_is_canonical_and_semantic_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'freeze.tar.gz'
            files = {'z': b'last', 'a': b'first'}
            raw = registration.archive_bytes(files)
            self.assertEqual(raw, registration.archive_bytes(dict(reversed(list(files.items())))))
            path.write_bytes(raw)
            self.assertEqual(registration.archive_files(path), files)
        old_files = registration.archive_files(t.original.ARCHIVE)
        frozen = json.loads(old_files['freeze.json'])
        for name in ['schedule.json', 'contexts/alpha-01.json', 'messages/alpha-01.json',
                     'grammars/alpha-01.gbnf', 'token-counts.json', 'operator/references.json']:
            changed = dict(old_files)
            changed[name] += b' '
            with self.subTest(name=name), patch.object(registration, 'baseline', return_value=(old_files, frozen)), \
                 patch.object(registration, 'archive_files', return_value=changed), \
                 patch.object(t.b, 'read', return_value={}), self.assertRaisesRegex(ValueError, 'Semantic payload mismatch'):
                registration.comparison()

    def test_authorization_guards_do_not_claim_attempt(self):
        with self.fixture() as (root, runtime, mocks):
            with self.assertRaises(ValueError):
                t.run(False)
            with patch.dict(os.environ, CI='1'), self.assertRaises(ValueError):
                t.run(True)
            self.assertFalse((root/'stages.jsonl').exists())
            runtime.generate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
