"""Retained-byte analysis regressions: fake transport, real Rust, no native assets."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze_v1f as a
import native_one_hop as native
import test_native_one_hop_diagnostic as run_tests


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.prereg, payload, cls.cases, cls.audit = a.load_freeze(a.REPORT)
        cls.freeze = cls.root / 'freeze'
        for name, raw in payload.items():
            if name.startswith('freeze/'):
                path = cls.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        cls.context = json.loads(payload['freeze/contexts/eva-01-oracle.json'])
        harness = run_tests.DiagnosticTests()
        harness.root, harness.frozen = cls.root, cls.freeze
        with patch.object(native, 'CONFIG', native.ROOT / 'configs/native-one-hop-v1f-diagnostic.json'):
            _, cls.run_dir = harness.run_mock()
            _, cls.failed = harness.run_mock('template', key='gemma4')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_unattempted_is_not_zero_accuracy_and_deterministic(self):
        result = a.analyze()
        self.assertEqual(result, a.analyze())
        self.assertEqual(a.markdown(result), a.markdown(a.analyze()))
        summary = result['summary']['overall']
        self.assertEqual((summary['scheduled'], summary['attempted'], summary['unattempted']), (72, 0, 72))
        self.assertEqual(summary['metrics']['accepted_exposed_reference_agreement'], dict(numerator=None, denominator=0))
        self.assertEqual(result['paired_comparisons']['oracle_vs_BM25_v1']['attempted_pairs'], 0)
        self.assertEqual(result['summary']['reference_direction']['reverse']['scheduled'], 8)
        country = next(r for r in result['cases'] if r['case_id'] == 'eva-01')
        self.assertEqual(len(country['source']['reference_edge_witnesses']), 1)
        self.assertEqual(country['source']['predicate_metadata'], [])
        reverse = next(r for r in result['cases'] if r['case_id'] == 'eva-07' and r['condition'] == 'retrieval')
        self.assertFalse(reverse['source']['required_vocabulary']['predicate'])
        self.assertEqual(len(reverse['source']['reference_edge_witnesses']), 1)
        self.assertFalse(result['semantic_go'])

    def test_committed_analysis_and_separate_v1g_design_hashes(self):
        report = a.ROOT / 'reports/issue-83-v1f-analysis'
        result = a.analyze()
        self.assertEqual(a.read(report / 'analysis.json'), result)
        self.assertEqual((report / 'failure-matrix.md').read_text(), a.markdown(result))
        registration = a.read(a.ROOT / 'experiments/native-one-hop-v1g/registration.json')
        self.assertFalse(registration['inference_authorized'])
        self.assertFalse(registration['execution_freeze_complete'])
        for name, sha in registration['input_sha256'].items():
            self.assertEqual(a.digest((a.ROOT / name).read_bytes()), sha, name)
        protocol = a.read(a.ROOT / 'experiments/native-one-hop-v1g/protocol.json')
        self.assertEqual(protocol['diagnostic_observations_per_model'], 3 * 30 + 2)
        self.assertEqual(protocol['maximum_completion_requests_per_model'], 3 * 30 + 4)

    def test_saved_mock_runs_rejections_guesses_missing_vocabulary_and_partial_stop(self):
        result = a.analyze(runs=[self.run_dir, self.failed])
        rows = result['cases']
        repeat = next(r for r in rows if r['model'] == 'qwen35' and r['name'] == 'repeat-1')
        self.assertTrue(repeat['wrong_but_executable'])
        self.assertFalse(repeat['accepted_exposed_reference_agreement'])
        self.assertFalse(repeat['field_agreement']['predicate'])
        for condition in ['oracle', 'retrieval']:
            guess = next(r for r in rows if r['model'] == 'qwen35' and r['name'] == 'ambiguous_start' and r['condition'] == condition)
            self.assertTrue(guess['incorrect_guess'])
            self.assertTrue(guess['rust_rejection'])
            self.assertFalse(guess['correct_model_clarification'])
        missing = next(r for r in rows if r['model'] == 'qwen35' and r['case_id'] == 'eva-07' and r['condition'] == 'retrieval')
        self.assertEqual(missing['failure_stratum'], 'reference_failure_with_required_vocabulary_missing')
        self.assertFalse(missing['rust_accepted'])
        partial = next(r for r in rows if r['model'] == 'gemma4' and r['status'] == 'fatal_failure')
        self.assertFalse(partial['generation_attempted'])
        self.assertIsNone(partial['exact_exposed_reference_agreement'])
        self.assertEqual(result['summary']['model']['qwen35']['completed'], 36)
        self.assertEqual(result['paired_comparisons']['oracle_vs_BM25_v1']['attempted_pairs'], 17)
        self.assertEqual(result['summary']['model_condition']['gemma4']['retrieval']['attempted'], 0)
        self.assertIsNone(result['summary']['model_condition']['gemma4']['retrieval']['metrics']['rust_accepted']['numerator'])

    def test_hash_context_request_and_raw_byte_tampering_fail_closed(self):
        original = self.run_dir / 'diagnostic/oracle/repeat-0/proposal.txt'
        raw = original.read_bytes()
        try:
            original.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, 'Changed run bytes'):
                a.analyze(runs=[self.run_dir])
            # Even resealing the outer inventory cannot make changed proposal bytes match the retained observation.
            (self.run_dir / 'checksums.json').write_text(json.dumps(a.inventory(self.run_dir)))
            with self.assertRaisesRegex(ValueError, 'proposal/base64'):
                a.analyze(runs=[self.run_dir])
        finally:
            original.write_bytes(raw)
            (self.run_dir / 'checksums.json').write_text(json.dumps(a.inventory(self.run_dir)))
        request = self.run_dir / 'diagnostic/oracle/repeat-0/completion-request.json'
        raw = request.read_bytes()
        try:
            request.unlink()
            (self.run_dir / 'checksums.json').write_text(json.dumps(a.inventory(self.run_dir)))
            with self.assertRaisesRegex(ValueError, 'Attempt/request|request count'):
                a.analyze(runs=[self.run_dir])
        finally:
            request.write_bytes(raw)
            (self.run_dir / 'checksums.json').write_text(json.dumps(a.inventory(self.run_dir)))
        context = self.run_dir / 'diagnostic/oracle/repeat-0/context.json'
        raw = context.read_bytes()
        try:
            changed = json.loads(raw)
            changed['predicates'] = []
            context.write_text(json.dumps(changed))
            (self.run_dir / 'checksums.json').write_text(json.dumps(a.inventory(self.run_dir)))
            with self.assertRaisesRegex(ValueError, 'frozen context'):
                a.analyze(runs=[self.run_dir])
        finally:
            context.write_bytes(raw)
            (self.run_dir / 'checksums.json').write_text(json.dumps(a.inventory(self.run_dir)))
        with self.assertRaisesRegex(ValueError, 'duplicate model'):
            a.analyze(runs=[self.run_dir, self.run_dir])

    def test_duplicate_json_partial_bytes_and_narrow_rationale_claims(self):
        row = copy.deepcopy(a.read(self.run_dir / 'run.json')['diagnostic']['cases'][0])
        raw = b'{"version":"nl-ask-draft-v1","status":"candidate","status":"unsupported","rationale":"control"}'
        row.update(raw_base64=base64.b64encode(raw).decode(), raw_sha256=a.digest(raw), gbnf_valid=False)
        result = a.analyze_row(row, self.cases['eva-01'], self.context, dict(required_vocabulary={'start': True, 'predicate': True}), {})
        self.assertTrue(result['json_valid'])
        self.assertFalse(result['strict_contract_valid'])
        self.assertFalse(result['accepted_exposed_reference_agreement'])
        row.update(status='fatal_failure', raw_base64=base64.b64encode(b'\xff{').decode(), raw_sha256=a.digest(b'\xff{'))
        result = a.analyze_row(row, self.cases['eva-01'], self.context, dict(required_vocabulary=None), {})
        self.assertFalse(result['json_valid'])
        self.assertFalse(result['completed'])
        claims = a.rationale_claims('Predicate 1004 is P1448.\nPredicate 1004 is P17.\nI do not claim predicate 1004 is P131.', self.context)
        self.assertEqual(len(claims['claims']), 2)
        self.assertEqual(claims['contradictions'], 1)
        self.assertIsNone(claims['unrestricted_rationale_correctness'])
        self.assertEqual(a.rationale_claims('Predicate 9999 is P17.', self.context)['claims'][0]['contradicted'], None)

    def test_source_ambiguity_does_not_rewrite_exposed_reference(self):
        row = copy.deepcopy(next(r for r in a.read(self.run_dir / 'run.json')['diagnostic']['cases']
                                 if r['case_id'] == 'eva-06' and r['condition'] == 'oracle'))
        raw = b'{"version":"nl-ask-draft-v1","status":"needs_clarification","rationale":"Which label relation?"}'
        row.update(raw_base64=base64.b64encode(raw).decode(), raw_sha256=a.digest(raw))
        result = a.analyze_row(row, self.cases['eva-06'], self.context,
                               dict(required_vocabulary={'start': True, 'predicate': True}), self.audit['cases']['eva-06'])
        self.assertFalse(result['exact_exposed_reference_agreement'])
        self.assertTrue(result['AI_source_audit_clarification_agreement'])
        self.assertEqual((result['reference_group'], result['AI_source_question_group']), ('supported', 'ambiguous'))


if __name__ == '__main__':
    unittest.main()
