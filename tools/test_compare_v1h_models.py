"""Portable comparison, complete denominators and source/annotation tamper checks."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import compare_v1h_models as v


class ComparisonTests(unittest.TestCase):
    def test_retained_reports_reproduce_without_processes(self):
        with patch('subprocess.Popen', side_effect=AssertionError('Comparison must not start processes')):
            result = v.analyze()
        self.assertEqual(result, v.a.read(v.REPORT / 'analysis.json'))
        self.assertEqual(v.markdown(result), (v.REPORT / 'comparison.md').read_text())
        self.assertEqual(v.failure_matrix(result), (v.REPORT / 'failure-matrix.md').read_text())
        self.assertEqual(len(result['cases']), 72)
        self.assertEqual(len(result['paired_observations']), 36)
        self.assertEqual(len(result['gemma_context_budgets']), 38)
        self.assertFalse(result['semantic_go'])
        self.assertIsNone(result['model_ranking'])
        self.assertTrue(all(r['independent_human_judgment'] is None for r in result['cases']))
        for row in result['cases']:
            if row['model'] == 'gemma4' and not row['completed']:
                self.assertIsNone(row['exact_exposed_reference_agreement'])
                self.assertIsNone(row['field_agreement'])
            if not row['generation_attempted']:
                self.assertIsNone(row['model_origin_status'])
                self.assertIsNone(row['exact_exposed_reference_agreement'])
        for conditions in result['summary'].values():
            for summary in conditions.values():
                self.assertEqual(summary['scheduled'], summary['attempted'] + summary['unattempted'])
                self.assertLessEqual(summary['completed'], summary['attempted'])
                self.assertEqual(summary['independent_human_judgments'], 0)
        for condition, paired in result['paired_completed_comparison'].items():
            expected = [p['name'] for p in result['paired_observations'] if p['condition'] == condition
                        and p['qwen35']['completed'] and p['gemma4']['completed']]
            self.assertEqual(paired['observations'], expected)
            for summary in paired['models'].values():
                self.assertEqual(summary['completed'], len(expected))
                self.assertEqual(summary['unattempted'], 0)

    def test_changed_archive_and_rebound_registered_source_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)
            manifest = v.a.read(v.REPORT / 'evidence-files.json')
            (report / 'evidence.tar.gz').write_bytes((v.REPORT / 'evidence.tar.gz').read_bytes() + b'changed')
            (report / 'evidence-files.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Changed Gemma evidence archive'):
                v.analyze(report)
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

    def test_annotation_requires_exact_raw_excerpt_and_source_value(self):
        context = dict(predicates=[dict(id=1004, graph=0, iri='source:P17')])
        row = dict(raw_sha256='raw-hash', rationale_text='Predicate 1004 is source:P1448.')
        note = dict(raw_sha256='raw-hash',
            context_sha256=hashlib.sha256((json.dumps(context, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest(),
            note='Coding-agent source-table contradiction; not independent human review.',
            findings=[dict(excerpt='Predicate 1004 is source:P1448.', source_path=['predicates', 0, 'iri'],
                           source_value='source:P17', asserted_value='source:P1448')])
        self.assertEqual(v.annotation(note, row, context), note)
        for key, value, message in [('raw_sha256', 'different', 'note/raw'), ('context_sha256', 'different', 'note/context')]:
            changed = {**note, key: value}
            with self.assertRaisesRegex(ValueError, message):
                v.annotation(changed, row, context)
        for key, value, message in [('source_value', 'source:P856', 'finding/witness'),
                                    ('asserted_value', 'source:P17', 'finding/witness'),
                                    ('excerpt', 'not actually said', 'finding/excerpt')]:
            changed = copy.deepcopy(note)
            changed['findings'][0][key] = value
            with self.assertRaisesRegex(ValueError, message):
                v.annotation(changed, row, context)

    def test_runtime_failure_has_no_measured_semantic_outcome(self):
        keys = ['exact_exposed_reference_agreement', 'accepted_exposed_reference_agreement', 'wrong_but_executable',
                'correct_model_clarification', 'AI_source_audit_clarification_agreement', 'incorrect_guess', 'field_agreement']
        row = dict(completed=False, **{key: False for key in keys})
        result = v.retain_missing_semantics(row)
        self.assertTrue(all(result[key] is None for key in keys))
        self.assertTrue(all(result['raw_output_reference_diagnostic'][key] is False for key in keys))


if __name__ == '__main__':
    unittest.main()
