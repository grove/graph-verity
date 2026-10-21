"""Portable retained-evidence reproduction and fail-closed source binding."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import analyze_v1h_qwen as v


class V1hEvidenceTests(unittest.TestCase):
    def test_analysis_reproduces_without_processes_and_keeps_denominators(self):
        with patch('subprocess.Popen', side_effect=AssertionError('Analysis must not start processes')):
            result = v.analyze()
        self.assertEqual(result, v.a.read(v.REPORT / 'analysis.json'))
        self.assertEqual(v.markdown(result), (v.REPORT / 'comparison.md').read_text())
        self.assertEqual(v.failure_matrix(result), (v.REPORT / 'failure-matrix.md').read_text())
        self.assertEqual(len(result['cases']), 36)
        self.assertEqual(len(result['comparisons']), 36)
        self.assertEqual(len(result['context_budgets']), 38)
        self.assertTrue(all(b['columnar']['total_required'] < 16384 for b in result['context_budgets']))
        self.assertEqual(result['authorization']['owner_message_exact'], 'I authorize it.')
        self.assertFalse(result['semantic_go'])
        self.assertEqual(result['independent_human_review'], 'pending')
        self.assertTrue(all(r['independent_human_judgment'] is None for r in result['cases']))
        for row in result['cases']:
            if not row['generation_attempted']:
                self.assertIsNone(row['exact_exposed_reference_agreement'])
                self.assertIsNone(row['model_origin_status'])
        for summary in result['summary'].values():
            self.assertEqual(summary['scheduled'], summary['attempted'] + summary['unattempted'])
            self.assertLessEqual(summary['completed'], summary['attempted'])

    def test_archive_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            (report / 'evidence.tar.gz').write_bytes((v.REPORT / 'evidence.tar.gz').read_bytes() + b'changed')
            (report / 'evidence-files.json').write_bytes((v.REPORT / 'evidence-files.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'Changed evidence archive'):
                v.analyze(report)

    def test_outer_inventory_cannot_rebind_registered_source(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            manifest = v.a.read(v.REPORT / 'evidence-files.json')
            archive = report / 'evidence.tar.gz'
            with tarfile.open(v.REPORT / 'evidence.tar.gz') as original, tarfile.open(archive, 'w:gz') as changed:
                for member in original:
                    raw = original.extractfile(member).read()
                    if member.name == 'source/configs/native-one-hop-v1e.prompt.txt':
                        raw += b'changed'
                        member.size = len(raw)
                        manifest['files'][member.name] = v.a.digest(raw)
                    changed.addfile(member, io.BytesIO(raw))
            manifest['archive_sha256'] = v.a.digest(archive.read_bytes())
            (report / 'evidence-files.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Changed registered source'):
                v.analyze(report)


if __name__ == '__main__':
    unittest.main()
