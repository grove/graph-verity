#!/usr/bin/env python3
"""Assisted Ask v1 direction extension: explicit choices; no inference."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import time

import assisted_ask as ask
import local_find as find
import local_nl_ask as bridge

ASSETS = Path(__file__).with_name('assisted_ask_direction_ui')
PREFIX = '/api/assisted-ask-v1-direction/'


class Bundle(ask.Bundle):
    def assemble(self, entity, predicate, direction='forward'):
        if direction not in ('forward', 'reverse'):
            raise ValueError('Explicit supported direction required')
        request = super().assemble(entity, predicate)
        request['template']['steps'][0]['direction'] = direction
        return request

    def resolve(self, proposal, start):
        if type(start) is not int or start != 1:
            raise ValueError('Explicit supported entity required')
        request = self.assemble(proposal['entity'], proposal['predicate'], proposal['direction'])
        return dict(status='candidate', request=request, preview=self.ask(request))

    def provenance(self, proposal):
        return dict(proposal_origin='manual_structured_selection_v1_explicit_direction', inference_performed=False,
                    original_question=proposal['packet']['request']['question'],
                    original_question_status='unverified_user_intent_not_interpreted',
                    language=proposal['packet']['request']['language'],
                    selected_operation=self.assemble(proposal['entity'], proposal['predicate'], proposal['direction']),
                    answer_claim='selected_graph_operation_only; original_question_not_verified',
                    operator_confirmation=None)

    def api(self, route, request, tab=None):
        self.current()
        if route == '/api/session':
            result = super().api(route, request, tab)
            for predicate in ask.PREDICATES.values():
                for direction in ('forward', 'reverse'):
                    self.assemble(ask.ENTITY, predicate, direction)
            result.update(version='assisted-ask-v1-direction', directions=['forward', 'reverse'],
                          runtime='manual_structured_selection',
                          runtime_message='INCONCLUSIVE_REVISE. Structured choices only; no question interpretation.')
            return result
        if route == PREFIX + 'preview':
            bridge.Bundle.api(self, bridge.PREFIX + 'unreview', {}, tab)
            self.proposal = None
            if (not isinstance(request, dict)
                    or set(request) != {'entity', 'predicate', 'direction', 'question', 'language'}
                    or not isinstance(request['question'], str) or len(request['question'].encode()) > 4096
                    or request['language'] not in ('en', 'nb')
                    or request['direction'] not in ('forward', 'reverse')):
                raise ValueError('Explicit choices and optional unverified question required')
            self.assemble(request['entity'], request['predicate'], request['direction'])
            sources = json.loads(Path(self.common[4]).read_bytes())['graphs']
            proposal = dict(entity=request['entity'], predicate=request['predicate'], direction=request['direction'],
                            packet=dict(request={k: request[k] for k in ('question', 'language')},
                                        sources={ask.GRAPH: sources[ask.GRAPH]}))
            resolved = self.resolve(proposal, 1)
            provenance = self.provenance(proposal)
            self.current()
            if time.monotonic() >= self.expires:
                raise ValueError('Expired session')
            token = secrets.token_hex(32)
            self.pending = dict(token=token, expires=time.monotonic() + find.REVIEW_SECONDS,
                                proposal=proposal, start=1, resolved=resolved, provenance=provenance)
            return dict(status='awaiting_confirmation', resolved=resolved, token=token,
                        review_seconds=min(find.REVIEW_SECONDS, max(0, self.expires - time.monotonic())),
                        sources=proposal['packet']['sources'], provenance=provenance)
        if route in (PREFIX + 'confirm', PREFIX + 'cancel'):
            return bridge.Bundle.api(self, bridge.PREFIX + route[len(PREFIX):], request, tab)
        self.pending = self.proposal = None
        raise ValueError('Assisted Ask v1 direction route only')


class Server(ask.Server):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assets = {
            '/': ((ASSETS / 'index.html').read_bytes(), 'text/html'),
            '/assisted-ask-v1-direction.js': ((ASSETS / 'app.js').read_bytes(), 'text/javascript'),
            '/style.css': ((ask.ASSETS / 'style.css').read_bytes(), 'text/css'),
        }
        self.bundle.receipt.update(
            ui_version='assisted-ask-v1-direction',
            backend='manual-structured-selection-explicit-direction',
            adapter_sha256=find.file_digest(Path(__file__)),
            assets={route: find.digest(body) for route, (body, _) in self.assets.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ask.ROOT / 'target/debug/verity')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    bundle = None
    try:
        bundle = Bundle(args.binary, ask.DATA / 'snapshot.nq', 'nquads', ask.DATA / 'policy.json',
                        ask.DATA / 'scope.json', ask.DATA / 'discovery.json')
        for predicate in ask.PREDICATES.values():
            for direction in ('forward', 'reverse'):
                bundle.assemble(ask.ENTITY, predicate, direction)
        with Server(bundle, port=args.port) as server:
            print('Assisted Ask v1 with explicit direction — structured choices, no inference. INCONCLUSIVE_REVISE.', flush=True)
            print('Private single-tab URL; stop with Ctrl-C.\n' + server.url, flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print('Cannot start Assisted Ask. Check the Rust build and authorized development snapshot.')
        return 1
    finally:
        if bundle:
            bundle.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
