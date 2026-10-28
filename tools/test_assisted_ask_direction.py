"""Assisted Ask v1 explicit-direction API and browser checks; no inference."""
import http.client
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
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

    def test_cli_passes_operator_selected_shape_files(self):
        with tempfile.TemporaryDirectory() as directory:
            shape_file = Path(directory) / 'selected-shapes.trig'
            shape_config = Path(directory) / 'selected-config.json'
            shutil.copyfile(ask.SHAPE_FILE, shape_file)
            shutil.copyfile(ask.SHAPE_CONFIG, shape_config)
            created = []
            real_bundle = ask.Bundle

            def create_bundle(*args, **kwargs):
                bundle = real_bundle(*args, **kwargs)
                created.append(bundle)
                return bundle

            with patch.object(ask, 'Bundle', side_effect=create_bundle) as bundle, \
                    patch.object(ask, 'Server') as server:
                server.return_value.__enter__.return_value.url = 'http://127.0.0.1/'
                self.assertEqual(ask.main(['--shape-file', str(shape_file), '--shape-config', str(shape_config)]), 0)
            self.assertEqual(bundle.call_args.kwargs['shape_file'], shape_file)
            self.assertEqual(bundle.call_args.kwargs['shape_config'], shape_config)
            self.assertTrue(created[0].shape_sha256.endswith(hashlib.sha256(shape_file.read_bytes()).hexdigest()))

    def test_selected_shape_manifest_cannot_change_data_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            config = json.loads(ask.SHAPE_CONFIG.read_text())
            config['data_graph'] = 'urn:unapproved:graph'
            selected_config = Path(directory) / 'shape-config.json'
            selected_config.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'authorized data snapshot'):
                ask.Bundle(v1.ROOT / 'target/debug/verity', v1.DATA / 'snapshot.nq', 'nquads',
                           v1.DATA / 'policy.json', v1.DATA / 'scope.json', v1.DATA / 'discovery.json',
                           shape_file=ask.SHAPE_FILE, shape_config=selected_config)

    def test_session_and_api_require_a_direction(self):
        session = self.result('/api/session', {})
        self.assertEqual(session['version'], 'assisted-ask-v1-direction-catalog')
        self.assertEqual(session['directions'], ['forward', 'reverse'])
        self.assertEqual(session['candidate_selection'], 'explicit_authorized_graph_roles')
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
            self.assertEqual(result['provenance']['proposal_origin'], 'manual_graph_catalog_selection_v1_explicit_direction')
            shape = result['provenance']['shape_guidance_context']
            self.assertEqual(shape['availability'], 'optional_guidance_only_not_query_evidence')
            self.assertEqual(shape['provenance_status'], 'operator_declared_not_independently_verified')
            self.assertEqual(shape['origin'], 'operator_authored_demo')
            self.assertEqual(shape['source']['license'], 'Apache-2.0')
            self.assertEqual(shape['shape_sha256'], self.bundle.shape_sha256)
            self.assertEqual(shape['data_snapshot_id'], v1.SNAPSHOT)
            self.assertTrue(all(not call.args[1:] for call in preview.call_args_list))
            self.result(ask.PREFIX + 'cancel', {})

    def test_changing_direction_revokes_the_pending_review(self):
        preview = self.result(ask.PREFIX + 'preview', self.choices(direction='reverse'))
        self.bundle.pending['proposal']['direction'] = 'forward'
        with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as call:
            status, _ = self.call(ask.PREFIX + 'confirm', {'token': preview['token'], 'decision': 'approve'})
        self.assertEqual(status, 400)
        self.assertTrue(all(not entry.args[1:] for entry in call.call_args_list))

    def test_catalog_candidates_can_be_previewed_but_unobserved_iris_cannot(self):
        country = 'http://www.wikidata.org/entity/Q20'
        country_property = 'http://www.wikidata.org/prop/direct/P17'
        with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as preview:
            result = self.result(ask.PREFIX + 'preview', self.choices(
                entity=country, predicate=country_property, direction='reverse'))
            request = result['resolved']['request']
            self.assertEqual(request['template']['start'], country)
            self.assertEqual(request['template']['steps'][0]['predicate'], country_property)
            self.assertEqual(request['template']['steps'][0]['direction'], 'reverse')
            self.assertEqual(preview.call_count, 1)
            self.result(ask.PREFIX + 'cancel', {})
            for invalid in (self.choices(entity='urn:unobserved:entity'),
                            self.choices(predicate='urn:unobserved:predicate')):
                self.assertEqual(self.call(ask.PREFIX + 'preview', invalid)[0], 400)
            self.assertEqual(preview.call_count, 1)

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
            self.assertEqual(result['version'], 'assisted-ask-shape-neighborhood-metadata-suggestions-v4')
            self.assertIs(type(result['entity_candidates_clipped']), bool)
            self.assertIs(type(result['predicate_candidates_clipped']), bool)
            self.assertIs(type(result['property_metadata']['clipped']), bool)
            self.assertEqual(result['candidate_selection_version'], 'authorized-graph-role-v1')
            self.assertEqual(result['neighborhood']['version'], 'question-vocabulary-packet-v2-neighborhood')
            metadata = result['property_metadata']
            self.assertEqual(metadata['source_file'], 'studies/nl-ask-v1/sources/Q279724.ttl')
            self.assertEqual(metadata['license'], 'CC0-1.0')
            self.assertEqual(metadata['data_graph'], v1.GRAPH)
            self.assertRegex(metadata['source_sha256'], r'^sha256:[0-9a-f]{64}$')
            self.assertIn('en', metadata['text_languages'])
            self.assertFalse({'no', 'nb', 'nn'} & set(metadata['text_languages']))
            for item in metadata['candidates']:
                self.assertEqual(item['candidate']['graph'], v1.GRAPH)
                self.assertIn(item['candidate']['iri'], item['metadata']['direct_claim_statement'])
                self.assertTrue(item['metadata']['source_statements'])
                self.assertNotIn('usage', item['candidate'])
            guidance = result['shape_guidance']
            self.assertEqual(guidance['origin'], 'operator_authored_demo')
            self.assertEqual(guidance['source']['license'], 'Apache-2.0')
            self.assertEqual(guidance['data_snapshot_id'], v1.SNAPSHOT)
            self.assertEqual(guidance['shape_sha256'], shape_hash)

        for result in results[:2]:
            self.assertEqual(result['candidates'], [])
            self.assertTrue(result['entity_candidates'])
            self.assertTrue(result['neighborhood']['clipped'])
            candidate = result['entity_candidates'][0]['candidate']
            self.assertEqual(candidate['iri'], v1.ENTITY)
            self.assertEqual(candidate['graph'], v1.GRAPH)
            self.assertGreater(candidate['ranking_score'], 0)
            labels = [text['value'] for text in candidate['texts'] if text['field'] == 'label']
            self.assertIn('en', {label['language'] for label in labels})
            self.assertIn('nb', {label['language'] for label in labels})
            self.assertTrue(any('</script><script>' in label['text'] for label in labels))
            neighborhood_iris = [item['candidate']['iri'] for item in result['neighborhood_candidates']]
            self.assertIn(v1.PREDICATES['P1448'], neighborhood_iris)
            self.assertIn(v1.PREDICATES['P856'], neighborhood_iris)
            self.assertIn('http://www.wikidata.org/prop/direct/P17', neighborhood_iris)
            neighborhood_by_iri = {item['candidate']['iri']: item for item in result['neighborhood_candidates']}
            self.assertTrue(neighborhood_by_iri['http://www.wikidata.org/prop/direct/P17']['selectable'])
            self.assertEqual(neighborhood_by_iri[v1.PREDICATES['P1448']]['neighborhood_rank'], 4)
            self.assertEqual(neighborhood_by_iri[v1.PREDICATES['P856']]['neighborhood_rank'], 7)
            for item in result['neighborhood_candidates']:
                candidate = item['candidate']
                self.assertEqual(candidate['graph'], v1.GRAPH)
                self.assertEqual(candidate['ranking_score'], 0)
                self.assertEqual(item['witness']['entity']['iri'], v1.ENTITY)
                self.assertEqual(item['witness']['direction'], 'outgoing')
                statement = item['witness']['statement']
                self.assertEqual(statement['source_graph']['value'], v1.GRAPH)
                self.assertEqual(statement['subject']['value'], v1.ENTITY)
                self.assertEqual(statement['predicate']['value'], candidate['iri'])
                if item['shape_properties']:
                    self.assertEqual(item['shape_properties'][0]['predicate_iri'], candidate['iri'])
            self.assertEqual(neighborhood_by_iri['http://www.wikidata.org/prop/direct/P17']['shape_properties'], [])
            neighbor = next(item for item in result['neighborhood_entity_candidates']
                            if item['candidate']['iri'] == 'http://www.wikidata.org/entity/Q20')
            self.assertTrue(neighbor['selectable'])
            self.assertEqual(neighbor['candidate']['graph'], v1.GRAPH)
            self.assertEqual(neighbor['witness']['entity']['iri'], v1.ENTITY)
            self.assertEqual(neighbor['witness']['entity']['rank'], 1)
            self.assertEqual(neighbor['witness']['direction'], 'outgoing')
            witness = neighbor['witness']['statement']
            self.assertEqual(witness['source_graph']['value'], v1.GRAPH)
            self.assertEqual(witness['subject']['value'], v1.ENTITY)
            self.assertEqual(witness['predicate']['value'], 'http://www.wikidata.org/prop/direct/P17')
            self.assertEqual(witness['object']['value'], 'http://www.wikidata.org/entity/Q20')
            self.assertLessEqual(len(result['neighborhood_entity_candidates']), 20)
            self.assertEqual(result['two_hop_candidates'], [])
            self.assertFalse(result['two_hop_candidates_clipped'])

        for result, code in zip(results[2:], ('P856', 'P1448')):
            self.assertEqual(result['entity_candidates'], [])
            self.assertEqual(result['neighborhood_entity_candidates'], [])
            self.assertEqual(result['two_hop_candidates'], [])
            self.assertEqual(result['neighborhood_candidates'], [])
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
        self.assertEqual(results[2]['property_metadata']['candidates'][0]['candidate']['iri'],
                         v1.PREDICATES['P856'])
        self.assertIn('description', {text['field'] for text in results[2]['property_metadata']['candidates'][0]['candidate']['texts']})
        self.assertEqual(results[3]['property_metadata']['candidates'][0]['candidate']['iri'],
                         v1.PREDICATES['P1448'])
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
