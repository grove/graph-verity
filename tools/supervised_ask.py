#!/usr/bin/env python3
"""Opt-in supervised Ask v2. Saved fixtures only; no live model adapter."""
import argparse
from pathlib import Path
import subprocess

import local_find as find
import local_nl_ask as replay

ROOT = replay.ROOT
PREFIX = '/api/nl-ask-v2/'
ASSETS = Path(__file__).with_name('local_nl_ask_ui_v2')
DATA = ROOT / 'studies/nl-ask-v1/development'


class Bundle(replay.Bundle):
    def packet(self, question, language, saved=None):
        # Reuse #82's source-witnessed discovery without changing frozen v1 retrieval.
        request = dict(question=question, language=language, snapshot_id=self.snapshot,
                       index_revision=self.receipt['index_revision'], scope=self.scope)
        packet = self.json_call('neighborhood', [request, self.budget])
        # Rebuild in Rust and compare the whole server-held packet; do not reserialize
        # Python JSON into the byte-canonical Rust neighborhood-replay interface.
        if saved is not None and packet != saved:
            raise ValueError('Changed neighborhood packet')
        return packet

    def api(self, route, request, tab=None):
        if route.startswith(PREFIX):
            route = replay.PREFIX + route[len(PREFIX):]
        elif route not in ('/api/session', '/api/find'):
            route = '/disabled-route'
        result = super().api(route, request, tab)
        if route == '/api/session':
            result.update(version='supervised-ask-v2', runtime_message=(
                'Live integration disabled. Saved synthetic interpretations only; '
                'new questions are not understood. Decision: INCONCLUSIVE_REVISE.'))
        if result.get('status') == 'model_unavailable':
            result['message'] = 'Live model integration disabled; no inference was performed.'
        if route == replay.PREFIX + 'question' and result['status'] == 'model_needs_clarification':
            result['packet'] = self.packet(request['question'], request['language'])
            self.current()
        return result


class Server(find.Server):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.RequestHandlerClass = replay.Handler
        self.assets = {route: ((ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ('/', 'index.html', 'text/html'), ('/nl-ask-v2.js', 'app.js', 'text/javascript'),
            ('/style.css', 'style.css', 'text/css'))}
        self.bundle.receipt.update(ui_version='supervised-ask-v2', backend='saved-draft-demo' if self.bundle.demo else 'unavailable',
            adapter_sha256=find.file_digest(Path(__file__)),
            approval_adapter_sha256=find.file_digest(Path(replay.__file__)),
            transport_adapter_sha256=find.file_digest(Path(find.__file__)),
            assets={route: find.digest(body) for route, (body, _) in self.assets.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saved-drafts-demo', type=Path, required=True,
                        help='Explicit model-free fixture opt-in; exact question matching only')
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/debug/verity')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    bundle = None
    try:
        bundle = Bundle(args.binary, DATA / 'snapshot.nq', 'nquads', DATA / 'policy.json',
                        DATA / 'scope.json', DATA / 'discovery.json', saved_drafts_demo=args.saved_drafts_demo)
        with Server(bundle, port=args.port) as server:
            print('EXPERIMENTAL supervised Ask v2 — SAVED FIXTURES, NO INFERENCE. Stop: Ctrl-C.', flush=True)
            print('Private single-tab session URL:\n' + server.url, flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print('Cannot start supervised Ask. Check the Rust build and pinned fixture bundle.')
        return 1
    finally:
        if bundle:
            bundle.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
