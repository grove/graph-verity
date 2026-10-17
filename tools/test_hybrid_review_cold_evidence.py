"""Verify recorded cold-start evidence without executing model workers."""
import json
import unittest

import hybrid_review_cold as cold


class ColdEvidence(unittest.TestCase):
    def test_all_preregistered_samples_and_timings_are_retained(self):
        base = cold.REPORT / 'cold-start'
        plan = json.loads((base / 'protocol.json').read_text())
        result = json.loads((base / 'results.json').read_text())
        self.assertEqual(plan['code_sha256'], cold.code_hashes())
        self.assertEqual(plan['protocol_id'], cold.review.verify()[2])
        self.assertEqual(result['public_protocol_sha256'], cold.review.forms.sha(base / 'protocol.json'))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual([{k: row[k] for k in ('repetition', 'task_id', 'system')} for row in result['samples']], cold.schedule())
        self.assertTrue(result['all_saved_ranks_preserved'])
        self.assertEqual((result['human_reviewers'], result['human_judgments']), (0, 0))
        self.assertEqual(result['recommendation'], 'defer')
        for row in result['samples']:
            self.assertGreater(row['first_result_ms'], 0)
            self.assertGreaterEqual(row['process_exit_ms'], row['first_result_ms'])
        for method in cold.review.METHODS:
            for metric in ('first_result_ms', 'process_exit_ms'):
                values = [row[metric] for row in result['samples'] if row['system'] == method]
                self.assertEqual(len(values), 15)
                self.assertEqual(result['summary'][method][metric], cold.review.hybrid.percentiles(values))
