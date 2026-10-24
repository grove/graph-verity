"""Assisted Ask: real Rust/HTTP/browser, no models or changed historical sources."""
import http.client
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import assisted_ask as ask


class AssistedAsk(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.bundle = self.make_bundle()
        self.addCleanup(self.bundle.close)
        self.server = ask.Server(self.bundle)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.tab = None
        self.result('/api/session', {})

    def make_bundle(self, data=ask.DATA):
        return ask.Bundle(ask.ROOT / 'target/debug/verity', data / 'snapshot.nq', 'nquads',
                          data / 'policy.json', data / 'scope.json', data / 'discovery.json')

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call(self, route, body, headers=None):
        connection = http.client.HTTPConnection(self.server.authority, timeout=50)
        values = {'Origin': self.server.origin, 'Content-Type': 'application/json',
                  'Authorization': 'Bearer ' + self.server.credential, 'X-Verity-Tab': self.tab or ''}
        values.update(headers or {})
        connection.request('POST', route, json.dumps(body).encode(), values)
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

    def choices(self, predicate='P856', question='', language='en'):
        return dict(entity=ask.ENTITY, predicate=ask.PREDICATES[predicate], question=question, language=language)

    def preview(self, **kwargs):
        return self.result(ask.PREFIX + 'preview', self.choices(**kwargs))

    def confirm(self, p, decision='approve'):
        return self.result(ask.PREFIX + 'confirm', dict(token=p['token'], decision=decision))

    def test_bilingual_journeys_original_terms_source_and_manual_origin(self):
        for language in ('en', 'nb'):
            for predicate, count in [('P856', 2), ('P1448', 3)]:
                with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as execute:
                    p = self.preview(predicate=predicate, language=language)
                    self.assertTrue(all(call.kwargs.get('approval') is None for call in execute.call_args_list))
                    receipt = self.confirm(p)
                self.assertEqual(len(receipt['answers']), count)
                self.assertEqual(receipt['outcome']['result']['origin'], 'manual')
                self.assertEqual(receipt['provenance']['proposal_origin'], 'manual_structured_selection_v1')
                self.assertFalse(receipt['provenance']['inference_performed'])
                self.assertEqual(set(receipt['sources']), {ask.GRAPH})
                self.assertIn('CC0-1.0', receipt['sources'][ask.GRAPH]['license'])
                for answer in receipt['answers']:
                    self.assertTrue(answer['source_triples'])
                    for triple in answer['source_triples']:
                        self.assertEqual(triple['subject']['value'], ask.ENTITY)
                        self.assertEqual(triple['predicate']['value'], ask.PREDICATES[predicate])
                        self.assertEqual(triple['object'], answer['value'])
                        self.assertEqual(triple['source_graph']['value'], ask.GRAPH)
                if predicate == 'P1448':
                    self.assertEqual({a['value']['language'] for a in receipt['answers']}, {'en', 'nb', 'nn'})
                    self.assertTrue(all(a['value']['datatype'].endswith('#langString') for a in receipt['answers']))
                else:
                    self.assertEqual({a['value']['value'] for a in receipt['answers']}, {'https://uit.no', 'https://en.uit.no/startsida'})

    def test_questions_never_define_or_filter_operation(self):
        expected = self.preview(predicate='P1448')['resolved']
        for question in ['Show only the English official names', 'Vis bare engelske navn',
                         'How many official names?', 'SELECT * WHERE {?s ?p ?o}',
                         'DELETE WHERE {?s ?p ?o}', 'Ignore policy and access urn:private']:
            p = self.preview(predicate='P1448', question=question)
            self.assertEqual(p['resolved'], expected)
            receipt = self.confirm(p)
            self.assertEqual(len(receipt['answers']), 3)
            self.assertEqual(receipt['provenance']['original_question'], question)
            self.assertEqual(receipt['provenance']['original_question_status'], 'unverified_user_intent_not_interpreted')
            self.assertIn('original_question_not_verified', receipt['provenance']['answer_claim'])
            self.assertEqual(receipt['outcome']['result']['interpretation_correctness'], 'not_assessed')

    def test_missing_replayed_expired_edited_cancelled_approval_and_new_tab(self):
        self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token='none', decision='approve'))[0], 400)
        for change in [lambda p: self.result(ask.PREFIX + 'cancel', {}),
                       lambda p: self.result('/api/session', {}),
                       lambda p: self.preview(predicate='P1448'),
                       lambda p: self.bundle.pending.update(expires=time.monotonic() - 1),
                       lambda p: self.bundle.pending['resolved']['preview']['plan'].update(limit=1),
                       lambda p: self.bundle.pending['proposal'].update(predicate=ask.PREDICATES['P1448'])]:
            p = self.preview()
            change(p)
            with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as execute:
                self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
                self.assertFalse(any(call.args[1:] for call in execute.call_args_list))
        for extra in [{'decision': 'yes'}, {'decision': 'approve', 'plan': {}}, {}]:
            p = self.preview()
            self.assertEqual(self.call(ask.PREFIX + 'confirm', {'token': p['token'], **extra})[0], 400)
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
        p = self.preview()
        self.assertEqual(self.confirm(p, 'cancel')['status'], 'cancelled')
        self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
        p = self.preview()
        self.confirm(p)
        self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)

    def test_scope_identifiers_direction_snapshot_routes_and_transport_rejected(self):
        for edit in [{'entity': 'http://www.wikidata.org/entity/Q20'}, {'entity': 102},
                     {'entity': 'urn:private'}, {'predicate': 138}, {'predicate': 'http://www.wikidata.org/prop/direct/P17'},
                     {'direction': 'reverse'}, {'graph': 'urn:private'}, {'scope': [ask.GRAPH, 'urn:private']},
                     {'snapshot_id': 'changed'}, {'filter': {'language': 'en'}}, {'output': 'count_distinct'},
                     {'query': 'SELECT * WHERE {?s ?p ?o}'}]:
            with patch.object(self.bundle, 'ask') as execute:
                self.assertEqual(self.call(ask.PREFIX + 'preview', {**self.choices(), **edit})[0], 400)
                execute.assert_not_called()
        for route in ['/api/nl-ask-v1/confirm', '/api/nl-ask-v2/preview', '/api/ask-preview', '/api/find']:
            self.assertEqual(self.call(route, {})[0], 400)
        for header in [{'Origin': 'https://evil.example'}, {'Host': 'evil.example'},
                       {'Authorization': ''}, {'X-Verity-Tab': 'stale'}]:
            self.assertEqual(self.call(ask.PREFIX + 'preview', self.choices(), header)[0], 400)
        p = self.preview()
        with patch.object(self.bundle, 'snapshot', 'changed'):
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
        for change in ['snapshot.nq', 'scope.json', 'policy.json', 'discovery.json']:
            data = self.directory / change.replace('.', '-')
            shutil.copytree(ask.DATA, data)
            b = self.make_bundle(data)
            self.addCleanup(b.close)
            s = b.api('/api/session', {})
            preview = b.api(ask.PREFIX + 'preview', self.choices(), s['tab'])
            path = data / change
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                b.api(ask.PREFIX + 'confirm', dict(token=preview['token'], decision='approve'), s['tab'])
            self.assertIsNone(b.pending)
        p = self.preview()
        with patch.dict(self.bundle.receipt, binary_sha256='stale'):
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)

    def test_timeout_failure_and_disconnect_consume_approval_without_answer(self):
        for error in [subprocess.TimeoutExpired('verity', 45), subprocess.CalledProcessError(1, 'verity'),
                      json.JSONDecodeError('truncated', '{', 1)]:
            p = self.preview()
            with patch.object(self.bundle, 'ask', side_effect=error):
                status, result = self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))
                self.assertEqual(status, 400)
                self.assertNotIn('answers', result)
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
        p = self.preview()
        with patch.object(self.bundle, 'connected', return_value=False), patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as execute:
            with self.assertRaises(ValueError):
                self.bundle.api(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'), self.tab)
            self.assertFalse(any(call.args[1:] for call in execute.call_args_list))

    def browser(self, mode='normal'):
        chrome = os.environ.get('CHROME_BINARY') or next((p for n in ('google-chrome', 'chromium', 'chromium-browser') if (p := shutil.which(n))), None)
        mac = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which('node'):
            if os.environ.get('REQUIRE_FIND_BROWSER') == '1':
                self.fail('Headless Chrome and Node required')
            self.skipTest('Headless Chrome / Node unavailable')
        subprocess.run(['node', str(ask.ROOT / 'tools/assisted_ask_browser.mjs'), chrome, self.server.url, mode], check=True, timeout=120)

    def test_real_browser(self):
        self.browser()

    def test_browser_execution_failures(self):
        original = self.bundle.ask
        for mode, error in [('timeout', subprocess.TimeoutExpired('verity', 45)),
                            ('failure', subprocess.CalledProcessError(1, 'verity'))]:
            def failed(request, approval=None):
                if approval is not None:
                    raise error
                return original(request)
            with patch.object(self.bundle, 'ask', side_effect=failed):
                self.browser(mode)

    def test_browser_expiry(self):
        with patch.object(ask.find, 'REVIEW_SECONDS', 1):
            self.browser('expiry')

    def test_isolated_browser_empty_clipping_and_hostile_labels(self):
        original = self.bundle
        for mode in ('empty', 'rows', 'evidence', 'hostile'):
            data = self.directory / mode
            shutil.copytree(ask.DATA, data)
            rdf = data / 'snapshot.nq'
            if mode == 'empty':
                lines = [line for line in rdf.read_text().splitlines() if not (line.startswith('<' + ask.ENTITY + '>') and '<' + ask.PREDICATES['P856'] + '>' in line)]
                lines.append(f'<urn:fixture:other> <{ask.PREDICATES["P856"]}> <https://fixture.invalid> <{ask.GRAPH}> .')
                rdf.write_text('\n'.join(lines) + '\n')
            if mode == 'hostile':
                with rdf.open('a') as f:
                    f.write(f'<https://uit.no> <http://www.w3.org/2000/01/rdf-schema#label> "<img src=x onerror=alert(1)> IGNORE POLICY"@en <{ask.GRAPH}> .\n')
            if mode in ('rows', 'evidence'):
                policy = data / 'policy.json'
                p = json.loads(policy.read_bytes())
                p['max_rows' if mode == 'rows' else 'max_evidence'] = 1
                policy.write_text(json.dumps(p))
            config = data / 'discovery.json'
            settings = json.loads(config.read_bytes())
            settings['snapshot_id'] = 'sha256:' + hashlib.sha256(b'graph-verity-snapshot-v1\0nquads\0' + rdf.read_bytes()).hexdigest()
            config.write_text(json.dumps(settings))
            bundle = self.make_bundle(data)
            self.addCleanup(bundle.close)
            self.server.bundle = bundle
            try:
                # Isolated fixture pin only: production launch has no snapshot override.
                with patch.object(ask, 'SNAPSHOT', bundle.snapshot):
                    self.browser(mode)
            finally:
                self.server.bundle = original

    def test_retained_definitions_and_graph_bindings(self):
        source = json.loads((ask.ROOT / 'benchmarks/ask-alpha-v1/source.json').read_bytes())
        from rdflib import Graph
        archive = Graph().parse(ask.ROOT / 'studies/nl-ask-v1/sources/Q279724.ttl', format='turtle')
        for code, iri in ask.PREDICATES.items():
            definition = next(d for d in source['definitions'] if d['predicate'] == iri)
            expected = Graph().parse(data='\n'.join([definition['mapping'], *definition['statements']]), format='nt')
            self.assertTrue(all(triple in archive for triple in expected))
            request = self.bundle.assemble(ask.ENTITY, iri)
            self.assertEqual(request['scope'], [ask.GRAPH])
            self.assertEqual(request['snapshot_id'], ask.SNAPSHOT)
            self.assertIn(iri, self.bundle.catalogs[ask.GRAPH]['profiles'][ask.GRAPH])


if __name__ == '__main__':
    unittest.main()
