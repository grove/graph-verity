"""Model-free v2 journeys and the reused exact-approval boundary."""
import copy
import http.client
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

import supervised_ask as ask

DEMO = ask.ROOT / 'examples/nl-ask-v2/saved-drafts-demo.json'
FORWARD = 'Which official websites does the University of Tromsø list?'
REVERSE = 'Which institution has https://uit.no as its official website?'
NORWEGIAN = 'Hvilke offisielle navn har Universitetet i Tromsø?'
WRONG = 'Which country is the University of Tromsø in?'


class SupervisedAsk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['cargo', 'build', '--locked', '--offline', '-q', '-p', 'verity_cli'], cwd=ask.ROOT, check=True)

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

    def make_bundle(self, data=ask.DATA, demo=DEMO):
        return ask.Bundle(ask.ROOT / 'target/debug/verity', data / 'snapshot.nq', 'nquads',
                          data / 'policy.json', data / 'scope.json', data / 'discovery.json',
                          saved_drafts_demo=demo)

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
        status, raw = response.status, response.read()
        connection.close()
        if route == '/api/session' and status == 200:
            self.tab = json.loads(raw)['tab']
        return status, json.loads(raw)

    def result(self, route, body):
        status, result = self.call(route, body)
        self.assertEqual(status, 200, result)
        return result

    def question(self, question=FORWARD, language='en'):
        return self.result(ask.PREFIX + 'question', dict(question=question, language=language))

    def preview(self, question=FORWARD, language='en'):
        q = self.question(question, language)
        self.assertIsNone(self.bundle.pending)
        return self.result(ask.PREFIX + 'preview', dict(proposal_token=q['proposal_token'],
                                                       start=json.loads(q['raw_draft'])['start']))

    def confirm(self, preview, decision='approve'):
        return self.result(ask.PREFIX + 'confirm', dict(token=preview['token'], decision=decision))

    def test_complete_bilingual_forward_reverse_multiple_values_and_provenance(self):
        for question, lang, count, direction in [(FORWARD, 'en', 2, 'forward'),
                                                (NORWEGIAN, 'nb', 3, 'forward'),
                                                (REVERSE, 'en', 1, 'reverse')]:
            with patch.object(self.bundle, 'ask', wraps=self.bundle.ask) as execute:
                p = self.preview(question, lang)
                execute.assert_not_called()
                request = p['resolved']['request']
                self.assertEqual(request['template']['steps'][0]['direction'], direction)
                self.assertEqual(request['scope'], ['urn:graph-verity:nl-ask-v1:development:wikidata'])
                receipt = self.confirm(p)
                self.assertEqual(execute.call_count, 1)
            self.assertEqual(len(receipt['answers']), count)
            self.assertEqual(receipt['provenance']['packet']['version'], 'question-vocabulary-packet-v2-neighborhood')
            self.assertFalse(receipt['provenance']['inference_performed'])
            self.assertEqual(receipt['provenance']['original_question'], question)
            self.assertEqual(receipt['provenance']['raw_draft'], p['provenance']['raw_draft'])
            self.assertEqual(receipt['outcome']['result']['snapshot_id'], self.bundle.snapshot)
            for answer in receipt['answers']:
                self.assertTrue(answer['source_triples'])
                for triple in answer['source_triples']:
                    self.assertEqual(triple['source_graph']['value'], request['scope'][0])
                    self.assertEqual(triple['predicate']['value'], request['template']['steps'][0]['predicate'])
                    self.assertEqual(triple['subject' if direction == 'forward' else 'object']['value'], request['template']['start'])
            if lang == 'nb':
                self.assertEqual({a['value']['language'] for a in receipt['answers']}, {'en', 'nb', 'nn'})
            elif direction == 'forward':
                self.assertEqual({a['value']['value'] for a in receipt['answers']}, {'https://uit.no', 'https://en.uit.no/startsida'})
            else:
                self.assertTrue(receipt['answers'][0]['value']['value'].endswith('/Q279724'))
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)

    def test_ambiguity_missing_vocabulary_unsupported_and_unseen_question_do_not_execute(self):
        with patch.object(self.bundle, 'ask') as execute:
            ambiguous = self.question('Which country is Campus in?')
            self.assertEqual(ambiguous['status'], 'model_needs_clarification')
            campus = [c['iri'] for c in ambiguous['packet']['entities']['candidates']
                      if any(t['value']['text'] == 'Campus' for t in c['texts'])]
            self.assertEqual(set(campus), {'http://www.wikidata.org/entity/Q279724', 'https://en.uit.no/startsida'})
            self.assertNotIn('token', ambiguous)
            self.assertIsNone(self.bundle.proposal)
            missing = self.question('What is the University of Tromsø postal code?')
            self.assertEqual(missing['status'], 'model_needs_clarification')
            self.assertIn('No postal-code relationship', missing['explanation'])
            self.assertEqual(self.question('How many official websites does the University of Tromsø list?')['status'], 'model_unsupported')
            self.assertEqual(self.question('An unsaved fresh question')['status'], 'demo_question_unavailable')
            execute.assert_not_called()
        # Clarification is an edited question, requiring another saved fixture and new preview.
        self.assertEqual(len(self.confirm(self.preview(NORWEGIAN, 'nb'))['answers']), 3)

    def test_wrong_but_executable_cancel_and_empty_results(self):
        p = self.preview(WRONG)
        self.assertTrue(p['resolved']['request']['template']['steps'][0]['predicate'].endswith('/P131'))
        with patch.object(self.bundle, 'ask') as execute:
            self.assertEqual(self.confirm(p, 'cancel')['status'], 'cancelled')
            execute.assert_not_called()
        wrong = self.confirm(self.preview(WRONG))
        self.assertTrue(wrong['answers'][0]['value']['value'].endswith('/Q26087'))
        self.assertEqual(wrong['outcome']['result']['interpretation_correctness'], 'not_assessed')
        empty = self.confirm(self.preview('Which website lists the University of Tromsø as its official website?'))
        self.assertEqual(empty['answers'], [])
        self.assertTrue(empty['outcome']['result']['complete_within_scope'])

    def test_wrong_direction_is_reviewable_and_never_runs_automatically(self):
        q = self.question()
        draft = json.loads(self.bundle.proposal['raw_draft'])
        draft['direction'] = 'reverse'
        self.bundle.proposal['raw_draft'] = json.dumps(draft)
        with patch.object(self.bundle, 'ask') as execute:
            p = self.result(ask.PREFIX + 'preview', dict(proposal_token=q['proposal_token'], start=draft['start']))
            self.assertEqual(p['resolved']['preview']['plan']['patterns'][0]['direction'], 'reverse')
            execute.assert_not_called()
            self.confirm(p, 'cancel')
            execute.assert_not_called()

    def test_absent_edited_expired_cancelled_new_tab_and_replayed_approval(self):
        with patch.object(self.bundle, 'ask') as execute:
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token='none', decision='approve'))[0], 400)
            execute.assert_not_called()
        for action in [lambda p: self.question(REVERSE), lambda p: self.result(ask.PREFIX + 'cancel', {}),
                       lambda p: self.result('/api/session', {}),
                       lambda p: self.bundle.pending.update(expires=time.monotonic() - 1),
                       lambda p: self.bundle.pending['resolved']['preview']['plan'].update(limit=1)]:
            p = self.preview()
            action(p)
            with patch.object(self.bundle, 'ask') as execute:
                self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
                execute.assert_not_called()
        for body in [{}, {'decision': 'yes'}, {'decision': 'approve', 'scope': ['urn:private']}]:
            p = self.preview()
            with patch.object(self.bundle, 'ask') as execute:
                self.assertEqual(self.call(ask.PREFIX + 'confirm', {'token': p['token'], **body})[0], 400)
                self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
                execute.assert_not_called()

    def test_unknown_ids_wrong_start_direction_injection_and_scope_changes(self):
        for fields in [{'start': 65535}, {'predicate': 65535}, {'graph': 65535}, {'direction': 'inverse'},
                       {'start': 'urn:injected'}, {'query': 'DELETE WHERE {?s ?p ?o}'},
                       {'scope': ['urn:private']}, {'steps': [{}, {}]}]:
            q = self.question()
            draft = json.loads(self.bundle.proposal['raw_draft'])
            self.bundle.proposal['raw_draft'] = json.dumps({**draft, **fields})
            with patch.object(self.bundle, 'ask') as execute:
                self.assertEqual(self.call(ask.PREFIX + 'preview', dict(proposal_token=q['proposal_token'], start=draft['start']))[0], 400)
                execute.assert_not_called()
            self.assertIsNone(self.bundle.pending)
        q = self.question()
        self.assertEqual(self.call(ask.PREFIX + 'preview', dict(proposal_token=q['proposal_token'], start=2))[0], 400)
        p = self.preview()
        with patch.dict(self.bundle.receipt, binary_sha256='stale'), patch.object(self.bundle, 'ask') as execute:
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
            execute.assert_not_called()
        data = self.directory / 'data'
        shutil.copytree(ask.DATA, data)
        bundle = self.make_bundle(data)
        self.addCleanup(bundle.close)
        bundle.api('/api/session', {})
        scope = data / 'scope.json'
        scope.write_text('["urn:private"]')
        with self.assertRaises(ValueError):
            bundle.api(ask.PREFIX + 'question', dict(question=FORWARD, language='en'), bundle.tab)

    def test_timeout_and_truncated_execution_or_draft_do_not_reuse_approval(self):
        for method, error in [('resolve', subprocess.TimeoutExpired('verity', 45)),
                              ('ask', subprocess.TimeoutExpired('verity', 45)),
                              ('ask', json.JSONDecodeError('truncated', '{', 1))]:
            p = self.preview()
            with patch.object(self.bundle, method, side_effect=error):
                self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
            self.assertEqual(self.call(ask.PREFIX + 'confirm', dict(token=p['token'], decision='approve'))[0], 400)
        q = self.question()
        self.bundle.proposal['raw_draft'] = '{'
        self.assertEqual(self.call(ask.PREFIX + 'preview', dict(proposal_token=q['proposal_token'], start=1))[0], 400)

    def test_injected_labels_typed_date_and_row_evidence_clipping(self):
        receipt = self.confirm(self.preview('Which published labels belong to the University of Tromsø?'))
        self.assertIn('IGNORE POLICY', json.dumps(receipt['answers']))
        date = self.confirm(self.preview('When was the University of Tromsø founded?'))
        self.assertTrue(date['answers'][0]['value']['datatype'].endswith('#dateTime'))
        p = self.preview()
        original = self.bundle.ask
        # Use a real restrictive Rust preview/execution, not mocked clipping flags.
        request = copy.deepcopy(p['resolved']['request'])
        request['limit'] = 1
        limited = original(request)
        _, result = original(request, limited['approval_id'])
        self.assertFalse(result['result']['complete_within_scope'])
        policy = self.directory / 'policy.json'
        policy.write_text(json.dumps({**self.bundle.policy, 'max_evidence': 1}))
        bundle = ask.Bundle(ask.ROOT / 'target/debug/verity', ask.DATA / 'snapshot.nq', 'nquads',
                            policy, ask.DATA / 'scope.json', ask.DATA / 'discovery.json')
        self.addCleanup(bundle.close)
        request['limit'] = 20
        preview = bundle.ask(request)
        _, result = bundle.ask(request, preview['approval_id'])
        self.assertFalse(result['result']['evidence_complete_for_returned_rows'])

    def test_routes_origin_credentials_and_unavailable_mode(self):
        for route in ['/api/nl-ask-v1/confirm', '/api/ask', '/api/run']:
            self.assertEqual(self.call(route, {})[0], 400)
        for headers in [{'Origin': 'https://invalid.example'}, {'Authorization': ''},
                        {'X-Verity-Tab': 'old'}, {'Host': 'invalid.example'}]:
            self.assertEqual(self.call(ask.PREFIX + 'question', dict(question=FORWARD, language='en'), headers)[0], 400)
        bundle = self.make_bundle(demo=None)
        self.addCleanup(bundle.close)
        tab = bundle.api('/api/session', {})['tab']
        with patch.object(bundle, 'ask') as execute:
            self.assertEqual(bundle.api(ask.PREFIX + 'question', dict(question=FORWARD, language='en'), tab)['status'], 'model_unavailable')
            execute.assert_not_called()

    def test_headless_browser(self):
        chrome = os.environ.get('CHROME_BINARY') or next((p for n in ('google-chrome', 'chromium', 'chromium-browser') if (p := shutil.which(n))), None)
        mac = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which('node'):
            if os.environ.get('REQUIRE_FIND_BROWSER') == '1':
                self.fail('Headless Chrome and Node required')
            self.skipTest('Headless Chrome / Node unavailable')
        source = (ask.ROOT / 'tools/supervised_ask_browser.mjs').read_text()
        readiness = 'await until("!document.getElementById(\'ask\').disabled");'
        self.assertIn(readiness, source)
        # The original driver is sealed into Ask Alpha; adapt only this current test copy.
        script = self.directory / 'supervised_ask_browser.mjs'
        script.write_text(source.replace(readiness,
            'await until("document.getElementById(\'ask\') && !document.getElementById(\'ask\').disabled");', 1))
        subprocess.run(['node', str(script), chrome, self.server.url], check=True, timeout=120)


class ReviewMaterials(unittest.TestCase):
    def test_pending_review_packages_and_pinned_sources(self):
        import hashlib
        from collections import Counter
        directory = ask.ROOT / 'examples/nl-ask-v2/review'
        manifest = json.loads((directory / 'manifest.json').read_bytes())
        for name, digest in manifest['files_sha256'].items():
            self.assertEqual(hashlib.sha256((ask.ROOT / name).read_bytes()).hexdigest(), digest, name)
        questions = json.loads((directory / 'questions.json').read_bytes())['cases']
        self.assertEqual(len(questions), 24)
        self.assertEqual(Counter(q['language'] for q in questions), {'nb': 12, 'en': 12})
        old = json.loads((ask.ROOT / 'studies/nl-ask-v1/cases.json').read_bytes())
        self.assertFalse({q['question'] for q in questions} & {q['question'] for q in old})
        for name, field in [('phase-a-source.json', 'human_assessment'),
                            ('phase-b-system.json', 'human_assessment'),
                            ('phase-c-usability.json', 'observation')]:
            package = json.loads((directory / name).read_bytes())
            self.assertEqual([q['id'] for q in package['cases']], [q['id'] for q in questions])
            for row in package['cases']:
                self.assertTrue(all(value == 'pending' for value in row[field].values()))
        phase_a = json.loads((directory / 'phase-a-source.json').read_bytes())
        lines = (ask.DATA / 'snapshot.nq').read_text().splitlines()
        self.assertEqual([f['original_nquad'] for f in phase_a['source_facts']], lines)

    def test_compiler_assessment_reproduces_exact_ten_rejections_without_execution(self):
        import assess_ask_compiler
        actual = assess_ask_compiler.assess()
        expected = json.loads((ask.ROOT / 'docs/supervised-ask-v2/compiler-assessment.json').read_bytes())
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
