import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import embedding_experiment as e
import retrieval as r


class EmbeddingTests(unittest.TestCase):
    def test_pinned_model_and_retrieval_inputs(self):
        manifest, upstream = e.verify()
        self.assertEqual(upstream['cardData']['license'], 'apache-2.0')
        self.assertFalse(upstream['gated'])
        self.assertEqual(manifest['model'], 'google/embeddinggemma-2')
        self.assertIn('User explicitly replaced', manifest['model_selection'])
        with patch.object(e, 'digest', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'prerequisite changed'):
                e.verify()

    def test_streamed_upstream_git_and_lfs_checks(self):
        content = b'official bytes'
        blob = hashlib.sha1(b'blob 14\0' + content).hexdigest()
        upstream = dict(id='fixture', sha='revision', siblings=[
            dict(rfilename='config.json', size=len(content), blobId=blob),
            dict(rfilename='weights', size=len(content), lfs=dict(sha256=hashlib.sha256(content).hexdigest()))])
        with tempfile.TemporaryDirectory() as directory, patch.object(e, 'verify', return_value=({}, upstream)):
            self.assertEqual(len(e.assets(directory)['failures']), 2)
            for name in ['config.json', 'weights']:
                (Path(directory)/name).write_bytes(content)
            self.assertTrue(e.assets(directory)['valid'])
            (Path(directory)/'weights').write_bytes(b'x' * len(content))
            self.assertEqual(e.assets(directory)['failures'], [dict(file='weights', reason='upstream content mismatch')])

    def fixture_trace(self):
        manifest, _ = e.verify()
        cases = []
        for fixture in e.parity_inputs():
            length = 256 if fixture['id'].startswith('truncation') else 5
            cases.append(dict(id=fixture['id'], input_sha256=hashlib.sha256(fixture['input'].encode()).hexdigest(),
                              token_ids=[2] + [3] * (length - 2) + [1],
                              untruncated_tokens=10000 if length == 256 else length,
                              vector=[1.] + [0.] * 767))
        return dict(model=manifest['model'], revision=manifest['revision'], cases=cases)

    def test_model_free_parity_contract_rejects_corruption(self):
        reference = self.fixture_trace()  # Synthetic unit vectors, never reference-model evidence.
        self.assertEqual(len(e.compare_parity(reference, copy.deepcopy(reference))), 8)
        for key, value, message in [
            ('input_sha256', 'wrong', 'prefix/text'),
            ('token_ids', [1, 2, 3, 4, 5], 'Tokenizer parity'),
            ('vector', [float('nan')] + [0.] * 767, 'Invalid embedding'),
            ('vector', [2.] + [0.] * 767, 'not L2'),
            ('vector', [0., 1.] + [0.] * 766, 'Vector parity'),
            ('untruncated_tokens', 6, 'Truncation length')]:
            runtime = copy.deepcopy(reference)
            runtime['cases'][0][key] = value
            with self.subTest(key=key, value=str(value)[:30]), self.assertRaisesRegex(ValueError, message):
                e.compare_parity(reference, runtime)
        missing = copy.deepcopy(reference)
        missing['cases'].pop()
        with self.assertRaisesRegex(ValueError, 'Missing parity'):
            e.compare_parity(reference, missing)
        bad = copy.deepcopy(reference)
        bad['cases'][-1]['untruncated_tokens'] = 256
        with self.assertRaisesRegex(ValueError, 'Truncation not exercised'):
            e.compare_parity(reference, bad)

    def test_graph_qualified_fusion_and_stable_ties(self):
        a = dict(graph='a', iri='same')
        b = dict(graph='b', iri='same')
        self.assertEqual([(h['graph'], h['iri']) for h in e.fuse([b], [a])], [('a', 'same'), ('b', 'same')])
        self.assertGreater(e.fuse([a, b], [a])[0]['score'], 1/61)
        with self.assertRaisesRegex(ValueError, 'Duplicate fusion'):
            e.fuse([a, a], [])

    def test_role_filtered_before_similarity_and_counts(self):
        class Scores:
            def __getitem__(self, selected):
                self.selected = selected
                return self
            def __matmul__(self, query):
                return SimpleNamespace(tolist=lambda: [.5] * len(self.selected))
        vectors = Scores()
        docs = [dict(iri='z', graph='a', document=dict(roles=['predicate'])),
                dict(iri='a', graph='b', document=dict(roles=['entity'])),
                dict(iri='a', graph='a', document=dict(roles=['predicate']))]
        hits = e.dense_rank(docs, vectors, [], 'predicate')
        self.assertEqual(vectors.selected, [0, 2])
        self.assertEqual([(h['iri'], h['graph']) for h in hits], [('a', 'a'), ('z', 'a')])
        self.assertEqual(e.dense_rank(docs, vectors, [], 'class'), [])

    def test_adoption_rule_rejects_regression_uncertainty_latency_memory_and_errors(self):
        metrics = {'recall@10': dict(mean=.05, descriptive_95=[.01, .09]),
                   'mrr@10': dict(mean=.04, descriptive_95=[.01, .07])}
        delta = {'overall': metrics, 'language/no': copy.deepcopy(metrics), 'language/en': copy.deepcopy(metrics)}
        summary = dict(splits=dict(evaluation=dict(paired_gain={s: copy.deepcopy(delta) for s in ['embedding', 'fusion']})),
                       performance=dict(scale={k: dict(p95=999) for k in
                           ['embedding_end_to_end_ms', 'fusion_end_to_end_upper_bound_ms']}))
        memory = dict(aggregate_upper_bound_bytes=4*1024**3)
        self.assertEqual(e.decide(summary, memory, [])['decision'], 'candidate_for_review')
        self.assertEqual(e.decide(summary, dict(aggregate_upper_bound_bytes=4*1024**3+1), [])['decision'], 'retain_bm25')
        self.assertEqual(e.decide(summary, memory, ['failure'])['decision'], 'retain_bm25')
        for system in ['embedding', 'fusion']:
            summary['splits']['evaluation']['paired_gain'][system]['language/no']['mrr@10']['mean'] = -.021
        self.assertEqual(e.decide(summary, memory, [])['decision'], 'retain_bm25')
        for system in ['embedding', 'fusion']:
            summary['splits']['evaluation']['paired_gain'][system] = copy.deepcopy(delta)
            for metric in ['recall@10', 'mrr@10']:
                summary['splits']['evaluation']['paired_gain'][system]['overall'][metric]['descriptive_95'][0] = 0
        self.assertEqual(e.decide(summary, memory, [])['decision'], 'retain_bm25')
        for system in ['embedding', 'fusion']:
            summary['splits']['evaluation']['paired_gain'][system] = copy.deepcopy(delta)
        for values in summary['performance']['scale'].values():
            values['p95'] = 1001
        self.assertEqual(e.decide(summary, memory, [])['decision'], 'retain_bm25')

    def test_retained_report_and_changed_denominator(self):
        report = e.ROOT/'reports/issue-38-embeddinggemma'
        archive = report/'evidence.tar.gz'
        self.assertEqual(e.digest(archive), (report/'evidence.sha256').read_text().split()[0])
        with tempfile.TemporaryDirectory() as directory, tarfile.open(archive) as bundle:
            root = Path(directory)
            seen = set()
            for member in bundle:
                name = Path(member.name)
                self.assertFalse(name.is_absolute() or '..' in name.parts or member.issym() or member.islnk())
                self.assertTrue(member.isfile() or member.isdir())
                if member.isfile():
                    self.assertNotIn(member.name, seen)
                    seen.add(member.name)
                    self.assertLessEqual(member.size, 40*1024**2)
                    path = root/name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bundle.extractfile(member).read())
            for name in ['summary.json', 'decision.json', 'memory.json', 'parity.json']:
                self.assertEqual((report/name).read_bytes(), (root/'run'/name).read_bytes())
            self.assertEqual((report/'freeze.json').read_bytes(), (root/'freeze/freeze.json').read_bytes())
            inventory = r.read(root/'inventory.json')
            for name, expected in inventory.items():
                self.assertEqual(e.digest(root/name), expected)
            e.verify_report(root/'freeze', root/'run')
            ranks = root/'run/ranks.jsonl.gz'
            with e.gzip.open(ranks, 'rt', encoding='utf-8') as stream:
                rows = [json.loads(line) for line in stream]
            rows[0]['status'] = 'no_match'
            with e.gzip.open(ranks, 'wt', encoding='utf-8') as stream:
                stream.write(''.join(json.dumps(row) + '\n' for row in rows))
            inventory = r.read(root/'run/artifacts.json')
            inventory[ranks.name] = e.digest(ranks)
            r.write(root/'run/artifacts.json', inventory)
            with self.assertRaisesRegex(ValueError, 'Changed judgment/denominator'):
                e.verify_report(root/'freeze', root/'run')


class ExportScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['cargo', 'build', '--locked', '--offline', '--quiet', '-p', 'verity_cli'], cwd=e.ROOT, check=True)
        cls.binary = Path(os.environ.get('CARGO_TARGET_DIR', e.ROOT / 'target')) / 'debug/verity'

    def fixture(self, directory, scope):
        root = Path(directory)
        rdf = root/'snapshot.trig'
        rdf.write_bytes((e.ROOT/'tests/fixtures/discovery.trig').read_bytes())
        snapshot = 'sha256:' + hashlib.sha256(b'graph-verity-snapshot-v1\0trig\0' + rdf.read_bytes()).hexdigest()
        r.write(root/'policy.json', dict(version=1, graphs=['urn:discovery:a', 'urn:discovery:b'],
                                       max_rows=100, max_evidence=100, timeout_ms=1000))
        r.write(root/'scope.json', scope)
        r.write(root/'config.json', dict(version=1, snapshot_id=snapshot, graphs={g: dict(
            source='PRIVATE_SOURCE_CANARY' if g.endswith('private') else 'Apache-2.0 fixture',
            license='Apache-2.0', source_revision='fixture-v1', importer_revision='fixture-v1')
            for g in ['urn:discovery:a', 'urn:discovery:b', 'urn:discovery:private']}))
        return dict(rdf=str(rdf), format='trig', policy=str(root/'policy.json'),
                    scope=str(root/'scope.json'), config=str(root/'config.json'))

    def test_authorize_before_export_and_preserve_rdf_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = self.fixture(directory, ['urn:discovery:a'])
            payload = e.export_corpus(self.binary, corpus)
            text = json.dumps(payload)
            self.assertNotIn('PRIVATE_', text)
            self.assertNotIn('Only second graph', text)
            self.assertEqual(payload['manifest']['scope'], ['urn:discovery:a'])
            shared = next(d for d in payload['documents'] if d['iri'] == 'urn:discovery:shared')
            self.assertEqual(shared['graph'], 'urn:discovery:a')
            literals = [t['value'] for t in shared['document']['texts']]
            self.assertTrue(any(t['text'] == '0042' and t['datatype'].endswith('#string') for t in literals))
            self.assertTrue(any(t['text'] == '42' and t['datatype'].endswith('#integer') for t in literals))
            self.assertTrue(any(t['language'] == 'nb' and 'Ålesund' in t['text'] for t in literals))
            self.assertIn('SERVICE <https://invalid.example/> DELETE WHERE', text)
            predicates = e.export_corpus(self.binary, corpus, 'predicate')
            self.assertTrue(all('predicate' in d['document']['roles'] for d in predicates['documents']))
            r.write(Path(directory)/'scope.json', ['urn:discovery:private'])
            with self.assertRaisesRegex(ValueError, 'Scope is not authorized'):
                e.export_corpus(self.binary, corpus)
            r.write(Path(directory)/'scope.json', [])
            with self.assertRaisesRegex(ValueError, 'Scope is not authorized'):
                e.export_corpus(self.binary, corpus)


if __name__ == '__main__':
    unittest.main()
