import tempfile
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch
import retrieval as r


class RetrievalTests(unittest.TestCase):
    def test_find_mvp_release_preserves_frozen_ranks_and_walkthrough_provenance(self):
        report = r.ROOT / 'reports/issue-39-find-mvp'
        r.verify_report(report / 'run')
        def ranks(path):
            with gzip.open(path / 'ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
                return [{k: row[k] for k in ['id', 'split', 'hits', 'metrics', 'result_status']}
                        for row in map(json.loads, stream)
                        if row['split'] in {'development', 'evaluation'}]
        self.assertEqual(ranks(report / 'run'), ranks(r.ROOT / 'reports/issue-37-bm25/run'))
        release = r.read(report / 'release.json')
        self.assertEqual(r.sha(report / 'smoke.json'), release['smoke_sha256'])
        smoke = r.read(report / 'smoke.json')
        self.assertFalse(smoke['network_used'])
        self.assertFalse(smoke['model_used'])
        no, en, country, city = [s['result'] for s in smoke['steps']]
        self.assertEqual(no['hits'][0]['iri'], country['iri'])
        self.assertEqual(no['hits'][0]['iri'], en['hits'][0]['iri'])
        self.assertEqual(len({s['result']['snapshot_id'] for s in smoke['steps']}), 1)
        edge = next(e for e in country['evidence']
                    if e['predicate']['value'] == 'http://www.wikidata.org/prop/direct/P36')
        self.assertEqual(edge['object']['value'], city['iri'])
        self.assertIn(edge, city['evidence'])
        self.assertEqual(r.read(report / 'run/environment.json')['binary_sha256'], release['binary_sha256'])

    def test_frozen_inputs_and_scale_recipe(self):
        manifest, cases = r.verify()
        self.assertEqual(len(cases), 80)
        with tempfile.TemporaryDirectory() as directory:
            corpus = r.scale_corpus(Path(directory))
            self.assertEqual(r.sha(corpus['rdf']), manifest['scale']['rdf_sha256'])
        with patch.object(r, 'sha', return_value='modified'):
            with self.assertRaisesRegex(ValueError, 'Frozen retrieval input changed'):
                r.verify()

    def test_retained_report_and_original_scale_failure(self):
        report = r.ROOT / 'reports/issue-37-bm25/run'
        r.verify_report(report)
        failure = r.read(report.parent / 'initial-scale-failure.json')
        archive = report.parent / failure['source']
        self.assertEqual(r.sha(archive), failure['archive_sha256'])
        with gzip.open(archive, 'rb') as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), failure['superseded_rdf_sha256'])
        self.assertIn('index_limit:', failure['failures'][0]['stderr'])
        self.assertEqual(failure['failures'][0]['stdout'], '')
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / 'run'
            shutil.copytree(report, copied)
            ranks = copied / 'ranks.jsonl.gz'
            with gzip.open(ranks, 'rt', encoding='utf-8') as f:
                rows = [json.loads(line) for line in f]
            rows[0]['status'] = 'no_match'
            with gzip.open(ranks, 'wt', encoding='utf-8') as f:
                f.write(''.join(json.dumps(row) + '\n' for row in rows))
            inventory = r.read(copied / 'artifacts.json')
            inventory[ranks.name] = r.sha(ranks)
            r.write(copied / 'artifacts.json', inventory)
            with self.assertRaisesRegex(ValueError, 'Rank judgment or denominator changed'):
                r.verify_report(copied)

    def test_recall_is_fraction_of_relevant_graph_qualified_ids(self):
        case = {'relevant': [{'iri': 'x', 'graph': 'a'}, {'iri': 'x', 'graph': 'b'}]}
        result = {'hits': [{'iri': 'wrong', 'graph': 'a'}, {'iri': 'x', 'graph': 'b'}]}
        metrics = r.score(case, result)
        self.assertEqual(metrics['recall@1'], 0)
        self.assertEqual(metrics['recall@5'], .5)
        self.assertEqual(metrics['mrr@10'], .5)
        self.assertEqual(r.score(case, {})['recall@50'], 0)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            r.score(case, {'hits': result['hits'] * 2})

    def test_separate_ambiguous_no_match_and_error_denominators(self):
        _, cases = r.verify()
        rows = []
        for case in cases:
            row = dict(case, metrics=r.score(case, {}), hits=[], result_status=None, error='test failure')
            rows.append(row)
        summary = r.summarize(rows)
        self.assertEqual(summary['metrics']['overall']['recall@10']['n'], 60)
        self.assertEqual(summary['metrics']['language/no']['mrr@10']['n'], 30)
        self.assertEqual(summary['metrics']['family/predicate']['recall@10']['mean'], 0)
        self.assertEqual(summary['behavior']['ambiguous/all']['n'], 10)
        self.assertEqual(summary['behavior']['no_match/all']['errors'], 10)
        self.assertEqual(summary['errors'], 80)
        self.assertFalse(any(summary['pilot_targets'].values()))
        self.assertEqual(r.interval([0, 1]), r.interval([0, 1]))
        self.assertEqual(r.interval([1, 1])['descriptive_95'], [1, 1])


if __name__ == '__main__':
    unittest.main()
