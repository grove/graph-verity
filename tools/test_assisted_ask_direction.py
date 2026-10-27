"""Assisted Ask v1 explicit-direction API and browser checks; no inference."""
import http.client
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from unittest.mock import patch

import assisted_ask as v1
import assisted_ask_direction as ask


class ExplicitDirection(unittest.TestCase):
    def setUp(self):
        self.bundle = ask.Bundle(v1.ROOT / 'target/debug/verity', v1.DATA / 'snapshot.nq', 'nquads',
                                 v1.DATA / 'policy.json', v1.DATA / 'scope.json', v1.DATA / 'discovery.json')
        self.addCleanup(self.bundle.close)
        self.server = ask.Server(self.bundle)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.tab = None
        self.result('/api/session', {})

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call(self, route, body):
        connection = http.client.HTTPConnection(self.server.authority, timeout=50)
        headers = {'Origin': self.server.origin, 'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + self.server.credential, 'X-Verity-Tab': self.tab or ''}
        connection.request('POST', route, json.dumps(body).encode(), headers)
        response = connection.getresponse()
        status, result = response.status, json.loads(response.read())
        connection.close()
        if route == '/api/session' and status == 200:
            self.tab = result['tab']
        return status, result

    def result(self, route, body):
        status, result = self.call(route, body)
        self.assertEqual(status, 200, result)
        return result

    def choices(self, **changes):
        request = dict(entity=v1.ENTITY, predicate=v1.PREDICATES['P856'], direction='forward',
                       question='', language='en')
        request.update(changes)
        return request

    def test_session_and_api_require_a_direction(self):
        session = self.result('/api/session', {})
        self.assertEqual(session['version'], 'assisted-ask-v1-direction')
        self.assertEqual(session['directions'], ['forward', 'reverse'])
        with patch.object(self.bundle, 'ask') as preview:
            for request in [self.choices(direction=None), self.choices(direction='sideways'),
                            {k: v for k, v in self.choices().items() if k != 'direction'}]:
                self.assertEqual(self.call(ask.PREFIX + 'preview', request)[0], 400)
            preview.assert_not_called()

    def test_rust_preview_binds_each_selected_direction(self):
        for direction in ('forward', 'reverse'):
            with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as preview:
                result = self.result(ask.PREFIX + 'preview', self.choices(direction=direction))
            step = result['resolved']['request']['template']['steps'][0]
            self.assertEqual(step['direction'], direction)
            self.assertEqual(result['provenance']['selected_operation']['template']['steps'][0]['direction'], direction)
            self.assertEqual(result['provenance']['proposal_origin'], 'manual_structured_selection_v1_explicit_direction')
            self.assertTrue(all(not call.args[1:] for call in preview.call_args_list))
            self.result(ask.PREFIX + 'cancel', {})

    def test_changing_direction_revokes_the_pending_review(self):
        preview = self.result(ask.PREFIX + 'preview', self.choices(direction='reverse'))
        self.bundle.pending['proposal']['direction'] = 'forward'
        with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as call:
            status, _ = self.call(ask.PREFIX + 'confirm', {'token': preview['token'], 'decision': 'approve'})
        self.assertEqual(status, 400)
        self.assertTrue(all(not entry.args[1:] for entry in call.call_args_list))

    def test_shape_suggestions_are_scoped_and_do_not_execute_or_select(self):
        with patch.object(self.bundle, 'shape_suggestions', wraps=self.bundle.shape_suggestions) as suggest, \
                patch.object(self.bundle, 'ask') as run:
            for request in ({'question': ' ', 'language': 'en'},
                            {'question': 'P856', 'language': 'fr'}):
                self.assertEqual(self.call(ask.PREFIX + 'suggestions', request)[0], 400)
            results = [self.result(ask.PREFIX + 'suggestions', request) for request in (
                {'question': 'Which official websites does the University of Tromsø list?', 'language': 'en'},
                {'question': 'Hvilke offisielle navn har Universitetet i Tromsø?', 'language': 'nb'},
                {'question': 'P856', 'language': 'en'}, {'question': 'P1448', 'language': 'nb'})]
        self.assertEqual(suggest.call_count, 4)
        run.assert_not_called()
        shape_hash = hashlib.sha256(Path(self.bundle.shape_file).read_bytes()).hexdigest()
        for result in results:
            self.assertEqual(result['request']['scope'], [v1.GRAPH])
            self.assertIn('BM25', result['score_semantics'])
            guidance = result['shape_guidance']
            self.assertEqual(guidance['origin'], 'operator_authored_demo')
            self.assertEqual(guidance['source']['license'], 'Apache-2.0')
            self.assertEqual(guidance['data_snapshot_id'], v1.SNAPSHOT)
            self.assertEqual(guidance['shape_sha256'], shape_hash)

        for result in results[:2]:
            self.assertEqual(result['candidates'], [])
            self.assertTrue(result['entity_candidates'])
            candidate = result['entity_candidates'][0]['candidate']
            self.assertEqual(candidate['iri'], v1.ENTITY)
            self.assertEqual(candidate['graph'], v1.GRAPH)
            self.assertGreater(candidate['ranking_score'], 0)
            labels = [text['value'] for text in candidate['texts'] if text['field'] == 'label']
            self.assertIn('en', {label['language'] for label in labels})
            self.assertIn('nb', {label['language'] for label in labels})
            self.assertTrue(any('</script><script>' in label['text'] for label in labels))

        for result, code in zip(results[2:], ('P856', 'P1448')):
            self.assertEqual(result['entity_candidates'], [])
            self.assertEqual(len(result['candidates']), 1)
            candidate = result['candidates'][0]
            self.assertEqual(candidate['candidate']['iri'], v1.PREDICATES[code])
            self.assertEqual(candidate['candidate']['graph'], v1.GRAPH)
            self.assertEqual(candidate['candidate']['texts'], [])
            self.assertGreater(candidate['candidate']['ranking_score'], 0)
            self.assertTrue(candidate['candidate']['usage'])
            self.assertEqual(candidate['shape_properties'][0]['predicate_iri'], v1.PREDICATES[code])
        self.assertEqual(results[2]['candidates'][0]['shape_properties'][0]['node_kind'],
                         'http://www.w3.org/ns/shacl#IRI')
        self.assertEqual(results[3]['candidates'][0]['shape_properties'][0]['datatype'],
                         'http://www.w3.org/1999/02/22-rdf-syntax-ns#langString')
        self.assertIsNone(self.bundle.pending)

    def browser(self):
        chrome = os.environ.get('CHROME_BINARY') or next(
            (path for name in ('google-chrome', 'chromium', 'chromium-browser')
             if (path := shutil.which(name))), None)
        mac = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which('node'):
            if os.environ.get('REQUIRE_FIND_BROWSER') == '1':
                self.fail('Headless Chrome and Node required')
            self.skipTest('Headless Chrome / Node unavailable')
        subprocess.run(['node', str(v1.ROOT / 'tools/assisted_ask_direction_browser.mjs'), chrome,
                        self.server.url], check=True, timeout=120)

    def test_real_bilingual_browser_direction_choice(self):
        with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as preview:
            self.browser()
        self.assertGreaterEqual(preview.call_count, 2)
        self.assertTrue(all(not call.args[1:] for call in preview.call_args_list))


if __name__ == '__main__':
    unittest.main()
