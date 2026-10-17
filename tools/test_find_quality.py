import gzip
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import find_quality as q
import retrieval as r


REPORT = r.ROOT / 'reports/issue-46-find-quality'


class FindQualityTests(unittest.TestCase):
    def test_fresh_comparison_preserves_denominators_and_original_failures(self):
        comparison = q.compare(r.ROOT / 'reports/issue-37-bm25/run', REPORT / 'run')
        self.assertEqual(comparison, r.read(REPORT / 'comparison.json'))
        for split in comparison['splits'].values():
            self.assertEqual(split['baseline']['metrics']['family/predicate']['recall@10']['mean'], 0)
            self.assertEqual(split['revised']['metrics']['family/predicate']['recall@10']['mean'], 1)
            self.assertEqual(split['revised']['metrics']['overall']['recall@10']['n'], 60)
            self.assertEqual(split['outcomes']['all']['n'], 80)
            self.assertEqual(split['outcomes']['status/no_match']['states'], {'no_match': 10})
            for family in ['identifier', 'entity', 'alias', 'description']:
                self.assertEqual(split['baseline']['metrics']['family/' + family],
                                 split['revised']['metrics']['family/' + family])
        self.assertTrue(all(comparison['budgets'].values()))
        release = r.read(REPORT / 'release.json')
        self.assertEqual(release['binary_sha256'], r.read(REPORT / 'run/environment.json')['binary_sha256'])
        for name, expected in release['sha256'].items():
            self.assertEqual(r.sha(REPORT / name), expected)

    def test_development_only_fusion_is_verified_without_model_runtime(self):
        import embedding_experiment as e
        path = REPORT / 'fusion-development'
        with patch.object(e, 'cpu_runtime', side_effect=AssertionError('CI must not invoke a model')):
            q.verify_fusion_dev(path)
        summary = r.read(path / 'summary.json')
        self.assertEqual(summary['systems']['bm25']['metrics']['overall']['mrr@10']['mean'], 1)
        for method in ['embedding', 'fusion']:
            self.assertEqual(summary['systems'][method]['behavior']['no_match/all']['returned_candidates'], 10)
            self.assertLess(summary['systems'][method]['metrics']['overall']['mrr@10']['mean'], 1)
        self.assertIn('defer fusion', summary['decision'])
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / 'trial'
            shutil.copytree(path, copied)
            rows = q.ranks(copied)
            rows[0]['split'] = 'evaluation'
            with gzip.open(copied / 'ranks.jsonl.gz', 'wt', encoding='utf-8') as stream:
                stream.writelines(json.dumps(row) + '\n' for row in rows)
            inventory = r.read(copied / 'artifacts.json')
            inventory['ranks.jsonl.gz'] = r.sha(copied / 'ranks.jsonl.gz')
            r.write(copied / 'artifacts.json', inventory)
            with self.assertRaisesRegex(ValueError, 'judgment/formulation changed'):
                q.verify_fusion_dev(copied)

    def test_conservative_states_do_not_hide_candidates_or_error_denominators(self):
        rows = [dict(language='no', family='no_match', status='no_match', result_status=state,
                     hits=hits) for state, hits in [('ambiguous_candidates', [1, 2]),
                                                  ('low_confidence', [1]), ('no_match', [])]]
        rows.append(dict(rows[-1], result_status=None, error='failed'))
        summary = q.outcomes(rows)['status/no_match']
        self.assertEqual(summary['n'], 4)
        self.assertEqual(summary['errors'], 1)
        self.assertEqual(summary['returned_candidates']['mean'], .5)
        self.assertEqual(summary['states'], dict(ambiguous_candidates=1, low_confidence=1, no_match=1, error=1))


if __name__ == '__main__':
    unittest.main()
