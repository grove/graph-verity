"""Model-free evidence checks: reproduction, missing outcomes, and tampering."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

REPORT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('predicate_evidence_analysis', REPORT / 'analyze.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class EvidenceTests(unittest.TestCase):
    def test_reproduction_without_processes_and_missing_outcomes(self):
        with patch('subprocess.Popen', side_effect=AssertionError('No subprocesses')):
            result = v.analyze()
        self.assertEqual(result, json.loads((REPORT / 'analysis.json').read_bytes()))
        self.assertEqual(len(result['rows']), 126)
        self.assertEqual(result['construction']['scheduled'], 60)
        self.assertEqual([result['metadata'][arm]['scheduled'] for arm in ['no_metadata', 'metadata']], [31, 31])
        self.assertEqual(len(result['pairs']), 31)
        for row in result['rows']:
            if row['measurement']:
                self.assertIsNone(row['measurement']['independent_human_correctness'])
                if not row['completed']:
                    self.assertIsNone(row['measurement']['reference_agreement'])
                    self.assertIsNone(row['measurement']['field_agreement'])

    def test_archive_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            (report / 'evidence.tar.gz').write_bytes((REPORT / 'evidence.tar.gz').read_bytes() + b'changed')
            (report / 'evidence-files.json').write_bytes((REPORT / 'evidence-files.json').read_bytes())
            with patch.object(v, 'REPORT', report), self.assertRaisesRegex(ValueError, 'Changed evidence archive'):
                v.analyze()

    def test_resealed_false_investigator_quote_is_rejected(self):
        payload = v.archive_files(REPORT / 'evidence.tar.gz')
        name = 'operator/source-audit-notes.json'
        notes = json.loads(payload[name])
        next(iter(notes['observations'].values()))['rationale_exact'] = 'Invented rationale absent from the original response'
        payload[name] = json.dumps(notes).encode()
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            archive = report / 'evidence.tar.gz'
            with tarfile.open(archive, 'w:gz') as bundle:
                for member_name, raw in sorted(payload.items()):
                    member = tarfile.TarInfo(member_name)
                    member.size = len(raw)
                    bundle.addfile(member, io.BytesIO(raw))
            (report / 'evidence-files.json').write_text(json.dumps(dict(archive_sha256=v.digest(archive.read_bytes()),
                files={n: v.digest(raw) for n, raw in payload.items()})))
            with patch.object(v, 'REPORT', report), self.assertRaisesRegex(ValueError, 'Unbound investigator note'):
                v.analyze()


if __name__ == '__main__':
    unittest.main()
