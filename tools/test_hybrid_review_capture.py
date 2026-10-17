"""Replay the actual post-preregistration capture without loading a model."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import hybrid_review as review
import hybrid_review_ai as ai


class SavedCapture(unittest.TestCase):
    def test_actual_capture_remains_model_free_and_human_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.json'
            with gzip.open(review.ROOT / 'reports/issue-58-human-review/saved-results.json.gz', 'rb') as source:
                path.write_bytes(source.read())
            study = review.Review(demo=False, results=path)
            self.assertEqual(len(study.tasks), 20)
            self.assertEqual(len(study.capture['samples']), 60)
            self.assertIsNone(study.capture['memory']['sampling_error'])
            report = review.summarize([], study)
            self.assertEqual(report['recommendation'], 'defer')
            self.assertEqual(report['counts'], dict(independent=0, owner=0, rehearsal=0))
            self.assertEqual(report['paired'], [])
            decision = json.loads((review.ROOT / 'reports/issue-58-human-review/decision.json').read_text())
            self.assertEqual(decision['protocol_id'], study.protocol_id)
            self.assertEqual(decision['counts']['new_query_inference_runs'], 1)

    def test_ai_scores_replay_without_human_attribution(self):
        actual = ai.analyze()
        expected = json.loads((review.ROOT / 'reports/issue-58-human-review/ai-analysis.json').read_text())
        self.assertEqual(actual, expected)
        self.assertEqual(actual['human_reviewers'], 0)
        self.assertEqual(actual['human_judgments'], 0)
        self.assertEqual(len(actual['new_anchor_recall10_wins']), 6)
        self.assertEqual(actual['both_methods_miss_at10'], ['HR-03', 'HR-06', 'HR-20'])
        self.assertEqual(actual['summaries']['overall']['exact_first'], dict(probes=4, preserved=4))
        self.assertEqual(actual['summaries']['overall']['no_match_false_candidate_rate']['selective']['mean'], 1)
        self.assertEqual(actual['recommendation'], 'defer')
