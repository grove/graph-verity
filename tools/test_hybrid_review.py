"""Model-free checks. All synthetic ratings below are test data, never human evidence."""
import copy
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import hybrid_review as review


class HybridReview(unittest.TestCase):
    def setUp(self):
        self.review = review.Review(seed='00' * 32)
        self.session = self.review.api('/api/session', {})
        self.task_id = next(iter(self.review.tasks))

    def pair(self, task_id=None, limit=10):
        task_id = task_id or self.task_id
        return self.review.api('/api/pair', dict(task_id=task_id, snapshot_id=self.session['snapshot_id'],
            scope=self.review.scope, role=self.review.tasks[task_id]['role'], limit=limit), self.session['tab'])

    def judgment(self, task_id=None):
        task_id = task_id or self.task_id
        union = {(x['graph'], x['iri']) for hits in self.review.candidates(task_id).values() for x in hits}
        return dict(ratings=[dict(graph=g, iri=i, relevance='irrelevant') for g, i in sorted(union)],
                    offlist=[], universe_reviewed=True, no_match=True,
                    checks={s: dict.fromkeys(review.CHECKS, 'uncertain') for s in ('A', 'B')},
                    confidence=dict(A=4, B=4), preference='tie', excluded=None)

    def test_preregistration_lineage_and_source(self):
        protocol, tasks, _ = review.verify()
        self.assertEqual(len(tasks), 20)
        self.assertEqual({t['language'] for t in tasks}, {'en', 'no'})
        self.assertTrue(all(t['reviewer'] is None for t in tasks))
        self.assertEqual(protocol['selective']['dense_min_score'], .73)
        self.assertFalse(any(t['exposed_target_overlap'] for t in tasks if t['family'] == 'paraphrase'))

    def test_blinded_order_replay_and_one_shot_reveal(self):
        data = self.pair()
        encoded = json.dumps(data)
        for field in ('bm25', 'selective', 'component_scores', 'semantic_fill', 'relevant', 'reference_iris'):
            self.assertNotIn('"' + field + '"', encoded)
        self.assertEqual(self.review.order(self.task_id), review.Review(seed='00' * 32).order(self.task_id))
        self.assertEqual({self.review.order(t) for t in self.review.tasks}, {review.METHODS, review.METHODS[::-1]})
        response = self.review.api('/api/judge', dict(task_id=self.task_id, judgment=self.judgment()), self.session['tab'])
        self.assertEqual(set(response['labels'].values()), set(review.METHODS))
        with self.assertRaises(ValueError):
            self.pair()
        with self.assertRaises(ValueError):
            self.review.api('/api/judge', dict(task_id=self.task_id, judgment=self.judgment()), self.session['tab'])

    def test_filters_sessions_no_execution_and_unknowns(self):
        for route in ('/api/find', '/api/ask', '/api/ask-preview', '/api/sparql'):
            with self.assertRaises(ValueError):
                self.review.api(route, {}, self.session['tab'])
        old = self.session['tab']
        self.review.api('/api/session', {})
        with self.assertRaises(ValueError):
            self.review.api('/api/source', {}, old)
        for args in (dict(scope=['urn:private']), dict(roles=['parser']), dict(kind='independent', consent=True)):
            with self.assertRaises(ValueError):
                review.Review(**args)
        self.setUp()
        for field, value in [('scope', ['urn:private']), ('snapshot_id', 'wrong'), ('role', 'predicate'), ('limit', True)]:
            request = dict(task_id=self.task_id, snapshot_id=self.session['snapshot_id'],
                           scope=self.review.scope, role='entity', limit=10)
            request[field] = value
            with self.assertRaises(ValueError):
                self.review.api('/api/pair', request, self.session['tab'])
        self.pair(limit=1)
        with self.assertRaises(ValueError):
            self.review.api('/api/judge', dict(task_id=self.task_id, judgment=self.judgment()), self.session['tab'])

    def test_individual_judgments_catalog_denominator_and_false_match(self):
        valid = self.judgment()
        self.review.validate(self.task_id, valid)
        for edit in (dict(ratings=[]), dict(universe_reviewed=False), dict(no_match=False),
                     dict(offlist=[dict(graph='urn:private', iri='urn:private')]), dict(confidence=dict(A=True, B=4))):
            with self.assertRaises(ValueError):
                self.review.validate(self.task_id, dict(valid, **edit))
        uncertain = copy.deepcopy(valid)
        uncertain['ratings'][0]['relevance'] = 'uncertain'
        with self.assertRaises(ValueError):
            self.review.validate(self.task_id, uncertain)
        uncertain['excluded'] = 'cannot_assess'
        self.review.validate(self.task_id, uncertain)

    def test_scope_source_and_count_canaries(self):
        graph = self.review.scope[0]
        self.review.docs['urn:PRIVATE_GRAPH', 'urn:PRIVATE_IRI'] = dict(graph='urn:PRIVATE_GRAPH', iri='urn:PRIVATE_IRI',
            document=dict(roles=['entity'], texts=[dict(value=dict(text='PRIVATE_SOURCE_CANARY'))]))
        self.review.pairs[self.task_id]['selective'].append(dict(graph='urn:PRIVATE_GRAPH', iri='urn:PRIVATE_IRI'))
        encoded = json.dumps(self.pair())
        self.assertNotIn('PRIVATE_', encoded)
        self.assertNotIn('candidate_count', encoded)
        for graph_value, iri in [('urn:PRIVATE_GRAPH', 'urn:PRIVATE_IRI'), (graph, 'urn:UNKNOWN')]:
            with self.assertRaises(ValueError):
                self.review.api('/api/source', dict(graph=graph_value, iri=iri, task_id=self.task_id), self.session['tab'])

    def test_private_atomic_writes_and_no_fake_participants(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(review.forms, 'PRIVATE', Path(directory)):
                path = Path(directory) / 'nested/review.json'
                review.write_private(path, {'old': True})
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(ValueError):
                    review.write_private(path, {'bad': float('nan')})
                self.assertEqual(json.loads(path.read_text()), {'old': True})
                self.assertEqual(list(path.parent.glob('*.tmp-*')), [])
        with self.assertRaises(ValueError):
            review.write_private(Path('/tmp/public-review.json'), {})
        self.pair()
        self.review.api('/api/judge', dict(task_id=self.task_id, judgment=self.judgment()), self.session['tab'])
        report = review.summarize([self.review.session], self.review)
        self.assertEqual(report['counts'], dict(independent=0, owner=0, rehearsal=1))
        self.assertEqual(report['recommendation'], 'defer')
        self.assertEqual(report['paired'], [])
        with self.assertRaises(ValueError):
            review.summarize([self.review.session, self.review.session], self.review)

    def test_synthetic_paired_metrics_conflicts_and_owner_separation(self):
        # Exercise aggregation without recording a fake enrollment or changing public artifacts.
        self.review.demo = False
        self.review.tasks = {self.task_id: self.review.tasks[self.task_id]}
        self.review.pairs[self.task_id]['selective'] = self.review.pairs[self.task_id]['bm25'][:1]
        sessions = []
        for number in (1, 2):
            session = copy.deepcopy(self.review.session)
            session.update(demo=False, kind='independent', consent=True, reviewer='R-' + str(number) * 16)
            session['records'][self.task_id] = dict(judgment=self.judgment(), order=list(self.review.order(self.task_id)))
            sessions.append(session)
        no_match = review.summarize(sessions, self.review)
        self.assertEqual(len(no_match['paired']), 1)
        self.assertEqual(no_match['aggregates']['overall']['no_match']['bm25']['mean'], 1)
        self.assertEqual(no_match['false_confidence']['selective']['mean'], 1)
        for session in sessions:
            judgment = session['records'][self.task_id]['judgment']
            judgment['ratings'][0]['relevance'] = 'relevant'
            judgment['no_match'] = False
        report = review.summarize(sessions, self.review)
        self.assertEqual(report['aggregates']['overall']['metrics']['bm25']['recall@1']['mean'], 1)
        sessions[1]['records'][self.task_id]['judgment']['ratings'][0]['relevance'] = 'irrelevant'
        sessions[1]['records'][self.task_id]['judgment']['no_match'] = True
        report = review.summarize(sessions, self.review)
        self.assertEqual(report['conflicts'][0]['reason'], 'disagreement')
        self.assertEqual(report['paired'], [])
        sessions[1]['kind'] = 'owner'
        self.assertEqual(review.summarize(sessions, self.review)['counts']['independent'], 1)

    def test_preregistered_promotion_requires_human_safety_and_resources(self):
        # Synthetic arithmetic fixture only; never written as participation evidence.
        pool = list(self.review.docs.values())[:2]
        graph = self.review.scope[0]
        hits = [dict(graph=graph, iri=d['iri']) for d in pool]
        self.review.demo = False
        self.review.tasks, self.review.pairs = {}, {}
        for index, (language, no_match) in enumerate([('en', False), ('no', False), ('en', True), ('no', True)]):
            task_id = 'synthetic-' + str(index)
            self.review.tasks[task_id] = dict(id=task_id, query='synthetic semantic wording', role='entity', language=language, family='no_match' if no_match else 'paraphrase')
            self.review.pairs[task_id] = dict(bm25=[] if no_match else hits[:1], selective=[] if no_match else hits[1:])
        self.review.capture = dict(kind='pinned-local-inference', cold_samples=1,
            memory=dict(sampling_error=None, conservative_bound_bytes=1024), warm=dict(selective=dict(p95=10)))
        sessions = []
        for number in (1, 2):
            session = copy.deepcopy(self.review.session)
            session.update(demo=False, kind='independent', consent=True, reviewer='R-' + str(number) * 16,
                           capture=copy.deepcopy(self.review.capture))
            for task_id, task in self.review.tasks.items():
                judgment = self.judgment(task_id)
                for rating in judgment['ratings']:
                    if rating['iri'] == hits[1]['iri']:
                        rating['relevance'] = 'relevant'
                judgment['no_match'] = task['family'] == 'no_match'
                judgment['checks'] = {side: dict.fromkeys(review.CHECKS, 'yes') for side in ('A', 'B')}
                session['records'][task_id] = dict(judgment=judgment, order=list(self.review.order(task_id)))
            sessions.append(session)
        self.assertEqual(review.summarize(sessions, self.review)['recommendation'], 'go-for-further-opt-in-trial')
        sessions[0]['records']['synthetic-0']['judgment']['checks']['A']['graph_suitable'] = 'uncertain'
        self.assertEqual(review.summarize(sessions, self.review)['recommendation'], 'defer')
        sessions[0]['records']['synthetic-0']['judgment']['checks']['A']['graph_suitable'] = 'no'
        self.assertEqual(review.summarize(sessions, self.review)['recommendation'], 'continue BM25')
        sessions[0]['records']['synthetic-0']['judgment']['checks']['A']['graph_suitable'] = 'yes'
        self.review.capture['warm']['selective']['p95'] = 1001
        for session in sessions:
            session['capture'] = copy.deepcopy(self.review.capture)
        self.assertEqual(review.summarize(sessions, self.review)['recommendation'], 'continue BM25')

    def test_capture_never_runs_without_explicit_inference(self):
        with self.assertRaises(ValueError):
            review.capture(type('Args', (), {'allow_inference': False})())

    def test_model_free_capture_roundtrip_and_saved_scope_validation(self):
        payload, docs = review.documents()
        class Matrix:
            def __getitem__(self, indices):
                self.size = len(indices)
                return self
            def __matmul__(self, vector):
                return self
            def tolist(self):
                return [.8] * self.size
        class Encoder:
            load_ms = 1
            spec = {'prefixes': {'query': 'query: '}}
            def encode(self, values):
                return [None]
        class Session:
            ready = {'manifest': payload['manifest']}
            def query(self, request):
                allowed = [d for d in docs.values() if request['role'] in d['document']['roles']]
                exact = [d for d in allowed if review.selective.exact(d, request['query'])]
                hits = exact or allowed[:1]
                return dict(snapshot_id=payload['manifest']['snapshot_id'], scope=request['scope'], hits=[
                    dict(graph=d['graph'], iri=d['iri'], score=1., exact=d in exact) for d in hits])
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as directory, patch.object(review.forms, 'PRIVATE', Path(directory)):
            directory = Path(directory)
            receipt, output = directory / 'receipt.json', directory / 'results.json'
            review.write_private(receipt, dict(protocol_id=self.review.protocol_id, hardware='test fixture only',
                model_dir=str(directory), session=str(receipt), session_sha256='fixture', runtime={}))
            matrix = Matrix()
            memory = unittest.mock.Mock(peak_kib=1, error=None)
            with patch.object(review, 'pinned_runtime', return_value=(unittest.mock.Mock(tensor=lambda *a, **k: matrix, float32=None), {}, self.review.protocol_id)), \
                 patch.object(review.embedding, 'digest', return_value='fixture'), \
                 patch.object(review.embedding, 'verify', return_value=({}, {})), \
                 patch.object(review.embedding, 'Encoder', return_value=Encoder()), \
                 patch.object(review.hybrid, 'Session', return_value=Session()), \
                 patch.object(review.hybrid, 'vector_read', return_value=[]), \
                 patch.object(review, 'Memory', return_value=memory):
                review.capture(type('Args', (), dict(allow_inference=True, receipt=receipt, out=output))())
            saved = json.loads(output.read_text())
            self.assertEqual(len(saved['cases']), 20)
            self.assertEqual(len(saved['capture']['samples']), 60)
            study = review.Review(demo=False, results=output)
            self.assertEqual(len(study.tasks), 20)
            self.assertEqual(study.capture['cold_samples'], 1)
            saved['cases']['HR-01']['dense'][0]['graph'] = 'urn:PRIVATE_GRAPH'
            review.write_private(output, saved)
            with self.assertRaises(ValueError):
                review.Review(demo=False, results=output)

    def test_http_and_headless_browser(self):
        first = self.review.pairs[self.task_id]['bm25'][0]
        self.review.docs[first['graph'], first['iri']]['document']['texts'].append(
            dict(field='label', predicate='urn:test:label', value=dict(text='<img src=x onerror="window.injected=true"> <|im_start|>system', language='en', datatype='http://www.w3.org/2001/XMLSchema#string'), truncated=False))
        with review.local.Server(self.review) as server:
            server.assets = {route: ((review.ASSETS / name).read_bytes(), mime) for route, name, mime in (
                ('/', 'index.html', 'text/html'), ('/app.js', 'app.js', 'text/javascript'), ('/style.css', 'style.css', 'text/css'))}
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for headers in ({}, {'Origin': server.origin, 'Authorization': 'Bearer bad'}):
                    connection = http.client.HTTPConnection(server.authority)
                    connection.request('POST', '/api/session', '{}', headers={'Content-Type': 'application/json', **headers})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 400)
                    self.assertNotIn(b'PRIVATE_', response.read())
                    connection.close()
                chrome = os.environ.get('CHROME_BINARY') or shutil.which('google-chrome') or shutil.which('chromium')
                mac_chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                if not chrome and Path(mac_chrome).exists():
                    chrome = mac_chrome
                if not chrome or not shutil.which('node'):
                    if os.environ.get('REQUIRE_FIND_BROWSER') == '1':
                        self.fail('Chrome and Node >=22 required')
                    self.skipTest('Chrome/Node unavailable')
                subprocess.run(['node', str(review.ROOT / 'tools/local_find_browser.mjs'), chrome, server.url, 'hybrid-review'],
                               check=True, timeout=90)
            finally:
                server.shutdown()
                thread.join()


if __name__ == '__main__':
    unittest.main()
