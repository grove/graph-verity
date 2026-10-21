"""Portable evidence reproduction and archive-integrity checks; no models."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

REPORT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('status_precedence_analysis', REPORT / 'analyze.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class EvidenceTests(unittest.TestCase):
    def test_exact_reproduction_without_processes_and_preserved_denominators(self):
        with patch('subprocess.Popen', side_effect=AssertionError('No processes allowed')):
            result = v.analyze()
        self.assertEqual(result, json.loads((REPORT / 'analysis.json').read_bytes()))
        self.assertEqual(len(result['cases']), 36)
        self.assertEqual([result['conditions'][c]['scheduled'] for c in ['oracle', 'retrieval']], [19, 17])
        for condition in result['conditions'].values():
            self.assertEqual(condition['unsupported']['scheduled'], 6)
            self.assertEqual(condition['genuine_clarification']['scheduled'], 3)
        self.assertLessEqual(result['generation_attempts'], 38)
        self.assertEqual(result['model_generated_rdf_executions'], 0)
        self.assertEqual(result['independent_human_review'], 'pending')
        for row in result['cases']:
            self.assertIsNone(row['independent_human_judgment'])
            if not row['completed']:
                self.assertIsNone(row['exact_exposed_reference_agreement'])
                self.assertIsNone(row['field_agreement'])

    def test_archive_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='qwen-status-tamper-') as temp:
            report = Path(temp)
            (report / 'evidence.tar.gz').write_bytes((REPORT / 'evidence.tar.gz').read_bytes() + b'changed')
            (report / 'evidence-files.json').write_bytes((REPORT / 'evidence-files.json').read_bytes())
            with patch.object(v, 'REPORT', report), self.assertRaisesRegex(ValueError, 'Changed evidence archive'):
                v.analyze()


if __name__ == '__main__':
    unittest.main()
