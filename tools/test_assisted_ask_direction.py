"""Assisted Ask v1 explicit-direction API and browser checks; no inference."""
import http.client
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
