"""Original r3 bytes, portable analysis, no model runtime or native assets."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import analyze_v1f_r3 as r3


class R3AnalysisTests(unittest.TestCase):
    def test_original_evidence_reproduces_without_processes_and_excludes_missing_cases(self):
        with patch('subprocess.Popen', side_effect=AssertionError('Analysis must not start a process')):
            result = r3.analyze()
        self.assertEqual(result, r3.a.read(r3.REPORT / 'analysis.json'))
        qwen = result['summary']['model_condition']['qwen35']
        self.assertEqual([(s['scheduled'], s['attempted'], s['completed'], s['unattempted']) for s in qwen.values()],
                         [(19, 19, 19, 0), (17, 14, 14, 3)])
        missing = [r for r in result['cases'] if not r['generation_attempted']]
        self.assertEqual(len(missing), 39)
        self.assertTrue(all(r['exact_exposed_reference_agreement'] is None and r['gbnf_valid'] is None for r in missing))
        self.assertEqual(result['summary']['model_condition']['gemma4']['oracle']['metrics']['rust_accepted'],
                         dict(numerator=None, denominator=0))
        self.assertEqual(result['native_integrity']['streams_verified'], 35)
        self.assertEqual(result['stop']['input_tokens'], 18926)
        self.assertFalse(result['authorization']['retroactive_authorization_claim'])
        self.assertFalse(result['semantic_go'])

    def test_changed_archive_fails_before_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            raw = (r3.REPORT / 'evidence.tar.gz').read_bytes()
            (report / 'evidence.tar.gz').write_bytes(raw + b'changed')
            (report / 'evidence-files.json').write_bytes((r3.REPORT / 'evidence-files.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'Changed evidence archive'):
                r3.analyze(report)

    def test_outer_inventory_cannot_override_registered_source(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            manifest = r3.a.read(r3.REPORT / 'evidence-files.json')
            archive = report / 'evidence.tar.gz'
            with tarfile.open(r3.REPORT / 'evidence.tar.gz') as original, tarfile.open(archive, 'w:gz') as changed:
                for member in original:
                    raw = original.extractfile(member).read()
                    if member.name == 'source/configs/native-one-hop-v1e.prompt.txt':
                        raw += b'changed'
                        member.size = len(raw)
                        manifest['files'][member.name] = r3.a.digest(raw)
                    changed.addfile(member, io.BytesIO(raw))
            manifest['archive_sha256'] = r3.a.digest(archive.read_bytes())
            (report / 'evidence-files.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Changed registered source'):
                r3.analyze(report)


if __name__ == '__main__':
    unittest.main()
