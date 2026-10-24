#!/usr/bin/env python3
"""Assisted Ask v1: explicit local choices, Rust preview, separate exact approval."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import time

import local_find as find
import local_nl_ask as bridge

ROOT = find.ROOT
DATA = ROOT / 'studies/nl-ask-v1/development'
ASSETS = Path(__file__).with_name('assisted_ask_ui_v1')
PREFIX = '/api/assisted-ask-v1/'
SNAPSHOT = 'sha256:48f0c13ddab7ce2a7881509192be30c1fe08693b4e7df5991e68cb302c20561b'
GRAPH = 'urn:graph-verity:nl-ask-v1:development:wikidata'
ENTITY = 'http://www.wikidata.org/entity/Q279724'
PREDICATES = {code: 'http://www.wikidata.org/prop/direct/' + code for code in ('P856', 'P1448')}


class Bundle(bridge.Bundle):
    def assemble(self, entity, predicate):
        """Resolve only explicit supported IRIs against the current graph-local catalog."""
        self.current()
        if (entity != ENTITY or predicate not in PREDICATES.values()
                or self.snapshot != SNAPSHOT or GRAPH not in self.scope
                or 'entity' not in self.resource_roles.get(GRAPH, {}).get(entity, [])
                or predicate not in self.catalogs[GRAPH]['profiles'][GRAPH]):
            raise ValueError('Unsupported selection or stale authorized catalog')
        return dict(version=1, snapshot_id=self.snapshot, scope=[GRAPH],
                    limit=min(100, self.policy['max_rows']),
                    template=dict(kind='follow_path', start=entity, steps=[dict(
                        graph=GRAPH, predicate=predicate, direction='forward')], filter=None, output='values'))

    def resolve(self, proposal, start):
        if start != 1:
            raise ValueError('Explicit supported entity required')
        request = self.assemble(proposal['entity'], proposal['predicate'])
        return dict(status='candidate', request=request, preview=self.ask(request))

    def provenance(self, proposal):
        return dict(proposal_origin='manual_structured_selection_v1', inference_performed=False,
                    original_question=proposal['packet']['request']['question'],
                    original_question_status='unverified_user_intent_not_interpreted',
                    language=proposal['packet']['request']['language'],
                    selected_operation=self.assemble(proposal['entity'], proposal['predicate']),
                    answer_claim='selected_graph_operation_only; original_question_not_verified',
                    operator_confirmation=None)

    def api(self, route, request, tab=None):
        if route == '/api/session':
            result = super().api(route, request, tab)
            # Fail closed at startup/session entry, even before offering choices.
            for predicate in PREDICATES.values():
                self.assemble(ENTITY, predicate)
            result.update(version='assisted-ask-v1', runtime='manual_structured_selection',
                          scope=[GRAPH], entity=ENTITY, predicates=PREDICATES,
                          runtime_message='INCONCLUSIVE_REVISE. Structured choices only; no question interpretation.')
            return result
        if route == PREFIX + 'preview':
            super().api(bridge.PREFIX + 'unreview', {}, tab)
            self.proposal = None
            if (not isinstance(request, dict) or set(request) != {'entity', 'predicate', 'question', 'language'}
                    or not isinstance(request['question'], str) or len(request['question'].encode()) > 4096
                    or request['language'] not in ('en', 'nb')):
                raise ValueError('Explicit choices and optional unverified question required')
            self.assemble(request['entity'], request['predicate'])
            sources = json.loads(Path(self.common[4]).read_bytes())['graphs']
            proposal = dict(entity=request['entity'], predicate=request['predicate'],
                            packet=dict(request={k: request[k] for k in ('question', 'language')},
                                        sources={GRAPH: sources[GRAPH]}))
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
            return super().api(bridge.PREFIX + route[len(PREFIX):], request, tab)
        self.pending = self.proposal = None
        raise ValueError('Assisted Ask route only')


class Server(find.Server):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.RequestHandlerClass = bridge.Handler
        self.assets = {route: ((ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ('/', 'index.html', 'text/html'), ('/assisted-ask-v1.js', 'app.js', 'text/javascript'),
            ('/style.css', 'style.css', 'text/css'))}
        self.bundle.receipt.update(ui_version='assisted-ask-v1', backend='manual-structured-selection',
            adapter_sha256=find.file_digest(Path(__file__)),
            approval_adapter_sha256=find.file_digest(Path(bridge.__file__)),
            transport_adapter_sha256=find.file_digest(Path(find.__file__)),
            assets={route: find.digest(body) for route, (body, _) in self.assets.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/debug/verity')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    bundle = None
    try:
        bundle = Bundle(args.binary, DATA / 'snapshot.nq', 'nquads', DATA / 'policy.json',
                        DATA / 'scope.json', DATA / 'discovery.json')
        for predicate in PREDICATES.values():
            bundle.assemble(ENTITY, predicate)
        with Server(bundle, port=args.port) as server:
            print('Assisted Ask v1 — structured choices, no inference. INCONCLUSIVE_REVISE.', flush=True)
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
