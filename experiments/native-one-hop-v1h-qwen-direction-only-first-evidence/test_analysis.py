"""Portable evidence reproduction and archive-integrity checks; no models."""
import importlib.util
import io
import json
import tarfile
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

REPORT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('direction_only_analysis', REPORT / 'analyze.py')
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

    def test_resealed_false_review_excerpt_is_rejected(self):
        payload = v.archive_files(REPORT / 'evidence.tar.gz')
        name = 'operator/source-audit-notes.json'
        notes = json.loads(payload[name])
        notes['oracle/multi_hop']['contradictions'][0]['raw_excerpt'] = 'Invented review quote absent from raw response'
        payload[name] = json.dumps(notes).encode()
        with tempfile.TemporaryDirectory(prefix='direction-review-tamper-') as temp:
            report = Path(temp)
            archive = report / 'evidence.tar.gz'
            with tarfile.open(archive, 'w:gz') as bundle:
                for member_name, raw in sorted(payload.items()):
                    member = tarfile.TarInfo(member_name)
                    member.size = len(raw)
                    bundle.addfile(member, io.BytesIO(raw))
            manifest = dict(archive_sha256=v.a.digest(archive.read_bytes()),
                files={n: v.a.digest(raw) for n, raw in payload.items()})
            (report / 'evidence-files.json').write_text(json.dumps(manifest))
            with patch.object(v, 'REPORT', report), patch('subprocess.Popen', side_effect=AssertionError('No processes allowed')):
                with self.assertRaisesRegex(ValueError, 'Review excerpt absent from original rationale'):
                    v.analyze()

    def test_archive_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='qwen-status-tamper-') as temp:
            report = Path(temp)
            (report / 'evidence.tar.gz').write_bytes((REPORT / 'evidence.tar.gz').read_bytes() + b'changed')
            (report / 'evidence-files.json').write_bytes((REPORT / 'evidence-files.json').read_bytes())
            with patch.object(v, 'REPORT', report), self.assertRaisesRegex(ValueError, 'Changed evidence archive'):
                v.analyze()


if __name__ == '__main__':
    unittest.main()
