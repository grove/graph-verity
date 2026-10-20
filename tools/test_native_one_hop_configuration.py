"""CLI/module identity and frozen-input regressions; no native model assets."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import native_one_hop as a
import native_one_hop_diagnostic as d

VARIANT = 'v1f-diagnostic-r3'
CONFIG = a.ROOT / f'configs/native-one-hop-{VARIANT}.json'


class ConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.freeze = cls.root / 'freeze'
        subprocess.run([sys.executable, str(a.ROOT / 'tools/native_one_hop.py'),
                        '--variant', VARIANT, 'freeze', '--out', str(cls.freeze)],
                       cwd=a.ROOT, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_direct_script_freeze_and_explicit_configuration(self):
        with patch.object(a, 'CONFIG', CONFIG):
            frozen = a.verify_freeze(self.freeze)
            self.assertEqual(frozen['version'], 'issue83-native-cpu-' + VARIANT)
            self.assertEqual(d.a.config(), frozen['config'])
        old = a.read(a.ROOT / 'configs/native-one-hop-v1f-diagnostic.json')
        corrected = a.read(CONFIG)
        self.assertEqual({**old, 'version': corrected['version']}, corrected)

    def test_direct_and_imported_cli_reach_helper_with_selected_configuration(self):
        original_freeze = a.freeze
        for direct in [True, False]:
            with self.subTest(direct=direct):
                out = self.root / f'probe-{direct}'
                out.mkdir()
                state = dict(diagnostic=d.accounting(a.read(CONFIG)))
                state['diagnostic']['cases'] = state['diagnostic']['cases'][:1]

                class ModelFreeStop(Exception):
                    pass

                class Runtime:
                    generation_attempts = 0

                    def generate(self, *args):
                        raise ModelFreeStop('Stopped at fake transport; no model')

                def probe(*args):
                    self.assertIs(d.a, a)
                    self.assertEqual(a.CONFIG, CONFIG)
                    a.verify_freeze(self.freeze)
                    with self.assertRaises(ModelFreeStop):
                        d.observe(self.freeze, out, state, Runtime(),
                                  dict(samples=1, error=None, peak_kib=100), a.BINARY)
                    row = state['diagnostic']['cases'][0]
                    self.assertEqual(row['status'], 'fatal_failure')
                    self.assertFalse(row['generation_attempted'])

                argv = ['native_one_hop.py', '--variant', VARIANT, 'freeze', '--out', str(out)]
                with patch.object(sys, 'argv', argv), patch.object(a, 'freeze', side_effect=probe) as called, \
                     patch.object(a, 'CONFIG', a.CONFIG), patch.object(a, 'assets') as assets, \
                     patch.object(a, 'Runtime') as runtime:
                    if direct:
                        runpy.run_path(str(a.ROOT / 'tools/native_one_hop.py'), run_name='__main__')
                    else:
                        a.main()
                    called.assert_called_once()
                    assets.assert_not_called()
                    runtime.assert_not_called()
                self.assertIs(a.freeze, original_freeze)

    def test_mismatched_configuration_and_historical_freeze_rejected(self):
        for variant in ['v1c', 'v1d', 'v1e', 'v1f-diagnostic']:
            with patch.object(a, 'CONFIG', a.ROOT / f'configs/native-one-hop-{variant}.json'):
                self.assertEqual(a.config()['version'], 'issue83-native-cpu-' + variant)
                with self.assertRaisesRegex(ValueError, 'Adapter configuration changed'):
                    a.verify_freeze(self.freeze)
        historical = a.read(a.REPORT.parent / 'issue-83-native-one-hop-v1f-diagnostic/preregistration.json')
        self.assertNotEqual(a.sha(a.ROOT / 'tools/native_one_hop.py'),
                            historical['freeze_manifest']['input_sha256']['tools/native_one_hop.py'])

    def test_historical_cli_variants_keep_explicit_selection(self):
        for variant in ['v1c', 'v1d', 'v1e', 'v1f-diagnostic']:
            for direct in [True, False]:
                with self.subTest(variant=variant, direct=direct):
                    def probe(*args):
                        self.assertEqual(a.config()['version'], 'issue83-native-cpu-' + variant)
                        self.assertEqual(d.a.CONFIG, a.CONFIG)
                    argv = ['native_one_hop.py', '--variant', variant, 'freeze', '--out', str(self.root)]
                    with patch.object(sys, 'argv', argv), patch.object(a, 'CONFIG', a.CONFIG), \
                         patch.object(a, 'freeze', side_effect=probe) as called:
                        if direct:
                            runpy.run_path(str(a.ROOT / 'tools/native_one_hop.py'), run_name='__main__')
                        else:
                            a.main()
                        called.assert_called_once()

    def test_modified_source_packet_and_binary_rejected(self):
        with patch.object(a, 'CONFIG', CONFIG):
            frozen = a.verify_freeze(self.freeze)
        copied = self.root / 'changed-source'
        for name in frozen['input_sha256']:
            path = copied / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(a.ROOT / name, path)
        source = copied / 'tools/native_one_hop.py'
        source.write_bytes(source.read_bytes() + b'\n# changed\n')
        copied_config = copied / CONFIG.relative_to(a.ROOT)
        with patch.object(a, 'ROOT', copied), patch.object(a, 'CONFIG', copied_config):
            with self.assertRaisesRegex(ValueError, 'Changed frozen input: tools/native_one_hop.py'):
                a.verify_freeze(self.freeze)
        packet = self.root / 'changed-packet'
        shutil.copytree(self.freeze, packet)
        context = packet / 'contexts/eva-01-oracle.json'
        context.write_bytes(context.read_bytes() + b' ')
        with patch.object(a, 'CONFIG', CONFIG):
            with self.assertRaisesRegex(ValueError, 'Changed new freeze'):
                a.verify_freeze(packet)
            binary = self.root / 'changed-binary'
            binary.write_bytes(b'not the registered binary')
            with self.assertRaisesRegex(ValueError, 'Rust binary changed'):
                a.verify_freeze(self.freeze, binary)

    def test_original_model_free_reproduction_against_archived_source(self):
        report = a.REPORT.parent / 'issue-83-native-one-hop-v1f-diagnostic'
        payload = a.g.archive_files(report / 'evidence.tar.gz')
        root = self.root / 'historical'
        for name, raw in payload.items():
            if name.startswith(('source/', 'freeze/')):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        path = root / 'source/tools/native_one_hop.py'
        spec = importlib.util.spec_from_file_location('v1f_cli_probe', path)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        cli.ROOT = root / 'source'
        cli.CONFIG = cli.ROOT / 'configs/native-one-hop-v1f-diagnostic.json'
        frozen = cli.read(root / 'freeze/freeze.json')
        # Other hosts must still reach and enforce the original binary guard.
        if a.sha(a.BINARY) == frozen['binary_sha256']:
            cli.verify_freeze(root / 'freeze')
        else:
            with self.assertRaisesRegex(ValueError, 'Rust binary changed'):
                cli.verify_freeze(root / 'freeze')
        self.assertIsNot(cli, d.a)
        with patch.object(a, 'CONFIG', a.ROOT / 'configs/native-one-hop-v1c.json'):
            with self.assertRaisesRegex(ValueError, '^Adapter configuration changed$'):
                d.a.verify_freeze(root / 'freeze')
        with patch.object(a, 'CONFIG', a.ROOT / 'configs/native-one-hop-v1f-diagnostic.json'):
            with self.assertRaisesRegex(ValueError, 'Changed frozen input: tools/native_one_hop.py'):
                a.verify_freeze(root / 'freeze')
        for name, digest in frozen['input_sha256'].items():
            self.assertEqual(hashlib.sha256(payload['source/' + name]).hexdigest(), digest)

    def test_successor_has_zero_execution_authority_and_requires_opt_in(self):
        with patch.object(a, 'CONFIG', CONFIG), patch.object(a, 'assets') as assets, \
             patch.object(a, 'Runtime') as runtime:
            for allow, ci, message in [(False, {}, 'allow-inference'), (True, {'CI': '1'}, 'forbidden in CI')]:
                with patch.dict(os.environ, ci, clear=True), self.assertRaisesRegex(ValueError, message):
                    a.run(self.freeze, self.root / 'never-attempted', 'qwen35', allow)
            assets.assert_not_called()
            runtime.assert_not_called()
        self.assertFalse((self.root / 'never-attempted').exists())
        frozen = a.read(self.freeze / 'freeze.json')
        self.assertEqual(frozen['executions'], 0)
        self.assertFalse(frozen['inference_performed'])
        state = dict(diagnostic=d.accounting(frozen['config']), status='unattempted')
        d.finish(state)
        self.assertEqual(state['decision'], 'INCONCLUSIVE_REVISE')
        self.assertFalse(state['diagnostic']['semantic_go'])

    def test_registered_successor_binds_sources_settings_and_preserves_history(self):
        release = a.ROOT / 'experiments/native-one-hop-v1f-diagnostic-r3'
        reg = a.read(release / 'registration.json')
        self.assertFalse(reg['inference_authorized'])
        self.assertFalse(reg['inference_performed'])
        self.assertEqual(reg['executions'], 0)
        self.assertEqual(reg['decision'], 'INCONCLUSIVE_REVISE')
        self.assertEqual(a.sha(release / 'freeze.tar.gz'), reg['archive_sha256'])
        payload = a.g.archive_files(release / 'freeze.tar.gz')
        self.assertEqual({n: hashlib.sha256(b).hexdigest() for n, b in payload.items()
                          if n != 'checksums.json'}, json.loads(payload['checksums.json']))
        self.assertEqual(hashlib.sha256(payload['checksums.json']).hexdigest(), reg['freeze_sha256'])
        self.assertEqual(json.loads(payload['freeze.json']), reg['freeze_manifest'])
        for name, digest in {**reg['freeze_manifest']['input_sha256'], **reg['source_sha256']}.items():
            self.assertEqual(a.sha(a.ROOT / name), digest, name)
        assets = reg['native_assets_reference']
        self.assertEqual(a.sha(a.ROOT / assets['path']), assets['sha256'])
        self.assertEqual(a.read(a.ROOT / assets['path']), reg['runtime_identity'])
        self.assertEqual(reg['freeze_manifest']['config']['version'], 'issue83-native-cpu-' + VARIANT)
        self.assertEqual(reg['diagnostic_observations_per_model'], 36)
        self.assertEqual(reg['maximum_completion_requests_per_model'], 38)
        historical = a.ROOT / 'reports/issue-83-native-one-hop-v1f-diagnostic'
        for name, digest in a.read(historical / 'historical-sha256.json').items():
            self.assertEqual(a.sha(a.ROOT / name), digest, name)
        changed = subprocess.check_output(['git', 'diff', '--exit-code', reg['base_commit'], '--',
            'reports', 'studies', 'experiments/native-one-hop-v1g',
            'configs/native-one-hop-v1f-diagnostic.json', 'configs/native-one-hop-v1f-diagnostic.audit.json',
            'tools/native_one_hop_diagnostic.py', 'tools/native_one_hop_v1g.py'], cwd=a.ROOT)
        self.assertEqual(changed, b'')

        import native_one_hop_v1g as v1g
        old = a.ROOT / 'experiments/native-one-hop-v1g/execution-v1'
        directory = self.root / 'registered-v1g'
        for name, raw in a.g.archive_files(old / 'freeze.tar.gz').items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'Changed frozen input: tools/native_one_hop.py'):
            v1g.verify(directory)


if __name__ == '__main__':
    unittest.main()
