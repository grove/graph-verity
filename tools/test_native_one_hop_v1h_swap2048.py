"""Model-free admission boundaries, source binding and inherited runner authority."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_one_hop_v1h_swap2048 as v


class Swap2048Tests(unittest.TestCase):
    def host(self, swap):
        host = dict(commands=[], load_per_cpu=0.1, swap_used_mib=swap, memory_free_percent=78,
                    disk_free_gib=100, max_process_cpu_percent=10, competing_model_processes=[])
        host['blockers'] = v.h.a.t.host_blockers(host, v.h.config())
        return host

    def test_only_swap_ceiling_changes_and_original_receipt_is_retained(self):
        for swap in [1024, 1024.1, 1877.44, 2048, 2048.1, None]:
            with self.subTest(swap=swap), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                original = self.host(swap)
                original['blockers'].append(dict(metric='thermal', reason='test warning'))

                def preflight(out):
                    v.h.dump(out, original)
                    return copy.deepcopy(original)

                with patch.object(v.h.a, 'preflight', side_effect=preflight) as native:
                    with v.host_gate():
                        amended = v.h.a.preflight(root / 'host.json')
                    self.assertIs(v.h.a.preflight, native)
                self.assertEqual(v.h.read(root / 'host-original-1024.json'), original)
                self.assertEqual(amended['original_blockers'], original['blockers'])
                self.assertEqual([b for b in amended['blockers'] if b['metric'] != 'swap_used_mib'],
                                 [b for b in original['blockers'] if b['metric'] != 'swap_used_mib'])
                failed = [b for b in amended['blockers'] if b['metric'] == 'swap_used_mib']
                self.assertEqual(bool(failed), swap is None or swap > 2048)
                if failed:
                    self.assertEqual(failed[0]['threshold'], 2048)
                cfg = v.h.config()['host_gates']
                self.assertEqual(cfg['swap_used_mib_max'], 1024)
                self.assertEqual(amended['effective_host_gates'], {**cfg, 'swap_used_mib_max': 2048})

    def test_other_host_failures_and_preflight_exception_are_not_suppressed(self):
        original = self.host(1877.44)
        original.update(load_per_cpu=1, memory_free_percent=1, disk_free_gib=1,
                        max_process_cpu_percent=200, competing_model_processes=[dict(executable='llama-server')])
        original['blockers'] = v.h.a.t.host_blockers(original, v.h.config())
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(v.h.a, 'preflight', return_value=original) as native:
                with v.host_gate():
                    amended = v.h.a.preflight(Path(temp) / 'host.json')
                self.assertIs(v.h.a.preflight, native)
            self.assertEqual(amended['blockers'], [b for b in original['blockers'] if b['metric'] != 'swap_used_mib'])
        with patch.object(v.h.a, 'preflight', side_effect=ValueError('native failure')) as native:
            with self.assertRaisesRegex(ValueError, 'native failure'), v.host_gate():
                v.h.a.preflight(Path('unused.json'))
            self.assertIs(v.h.a.preflight, native)

    def test_definition_binds_parent_and_only_one_configuration_field_changes(self):
        registered = v.definition()
        cfg = v.h.config()
        self.assertEqual(registered['effective_config'],
                         {**cfg, 'host_gates': {**cfg['host_gates'], 'swap_used_mib_max': 2048}})
        self.assertEqual(registered['parent_registration_sha256'], v.PARENT_SHA256)
        self.assertEqual(registered['model'], 'gemma4')
        self.assertFalse(registered['inference_authorized'])
        self.assertEqual(registered['retries'], 0)
        self.assertEqual(registered['maximum_requests'], 38)
        self.assertEqual(set(registered['source_input_sha256']), set(v.SOURCES))
        with tempfile.TemporaryDirectory(dir=v.ROOT) as temp:
            release = Path(temp)
            v.h.dump(release / 'registration.json', registered)
            with patch.object(v, 'RELEASE', release), patch.object(v.h, 'verify_registration') as parent:
                self.assertEqual(v.verify(Path('freeze'), committed=False), registered)
                parent.assert_called_once_with(Path('freeze'))
                registered['effective_config']['host_gates']['swap_used_mib_max'] = 4096
                v.h.dump(release / 'registration.json', registered)
                with self.assertRaisesRegex(ValueError, 'Changed swap2048'):
                    v.verify(Path('freeze'), committed=False)
                registered = v.definition()
                registered['source_input_sha256'][v.SOURCES[0]] = '0' * 64
                v.h.dump(release / 'registration.json', registered)
                with self.assertRaisesRegex(ValueError, 'Changed swap2048'):
                    v.verify(Path('freeze'), committed=False)
                v.h.dump(release / 'registration.json', v.definition())
                with patch.object(v.subprocess, 'check_output', return_value=b'changed'):
                    with self.assertRaisesRegex(ValueError, 'Variant must be committed'):
                        v.verify(Path('freeze'))

    def test_run_requires_new_opt_in_and_preserves_inner_bytes_and_failure(self):
        with patch.object(v.h, 'run') as parent:
            with self.assertRaisesRegex(ValueError, 'Separate exact-command'):
                v.run(Path('missing'), Path('missing'))
            with patch.dict('os.environ', {'CI': '1'}), self.assertRaisesRegex(ValueError, 'forbidden in CI'):
                v.run(Path('missing'), Path('missing'), True)
            parent.assert_not_called()
        for fail in [False, True]:
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                registered = v.definition()
                out = root / 'attempt'
                native_preflight = v.h.a.preflight

                def parent(folder, dest, model, allow_inference):
                    self.assertEqual((folder, dest, model, allow_inference),
                                     (root / 'freeze', out / 'run', 'gemma4', True))
                    self.assertIsNot(v.h.a.preflight, native_preflight)
                    dest.mkdir()
                    (dest / 'raw.txt').write_bytes(b'original raw bytes\x00')
                    v.h.dump(dest / 'checksums.json', {'raw.txt': v.h.sha(dest / 'raw.txt')})
                    if fail:
                        raise ValueError('parent integrity stop')
                    return dict(status='completed_diagnostic', generation_attempts=38, generation_completed=38)

                with patch.object(v, 'ROOT', root), patch.object(v, 'verify', return_value=registered), \
                     patch.object(v.h, 'run', side_effect=parent), patch.dict('os.environ', {}, clear=True):
                    if fail:
                        with self.assertRaisesRegex(ValueError, 'parent integrity stop'):
                            v.run(root / 'freeze', out, True)
                    else:
                        result = v.run(root / 'freeze', out, True)
                        self.assertEqual(result['generation_attempts'], 38)
                    self.assertIs(v.h.a.preflight, native_preflight)
                    ledger = root / 'artifacts' / ('v1h-budget-attempts-' + registered['parent_freeze_sha256'] + '.json')
                    ledger.parent.mkdir()
                    v.h.dump(ledger, ['qwen35', 'gemma4'])
                    with self.assertRaisesRegex(ValueError, 'No retries across parent and variant'):
                        v.run(root / 'freeze', root / 'second-attempt', True)
                self.assertEqual((out / 'run/raw.txt').read_bytes(), b'original raw bytes\x00')
                inventory = v.h.read(out / 'checksums.json')
                self.assertEqual(inventory['run/checksums.json'], v.h.sha(out / 'run/checksums.json'))
                self.assertEqual(v.h.read(out / 'variant.json')['status'],
                                 'blocked_or_failed' if fail else 'completed_diagnostic')


if __name__ == '__main__':
    unittest.main()
