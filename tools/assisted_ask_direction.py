#!/usr/bin/env python3
"""Assisted Ask v1 direction extension: explicit choices; no inference."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

import assisted_ask as ask
import local_find as find
import local_nl_ask as bridge

ASSETS = Path(__file__).with_name('assisted_ask_direction_ui')
PREFIX = '/api/assisted-ask-v1-direction/'
SHAPE_GUIDANCE_BINARY = ask.ROOT / 'target/debug/shape_guidance'
SHAPE_FILE = ask.ROOT / 'examples/assisted-ask-direction/demo-shapes/shapes.trig'
SHAPE_CONFIG = ask.ROOT / 'examples/assisted-ask-direction/demo-shapes/config.json'


class Bundle(ask.Bundle):
    def __init__(self, *args, shape_guidance_binary=SHAPE_GUIDANCE_BINARY,
                 shape_file=SHAPE_FILE, shape_config=SHAPE_CONFIG, **kwargs):
        binary = Path(shape_guidance_binary)
        self.shape_guidance_binary = binary.resolve(strict=True) if binary.is_file() else None
        self.shape_guidance_binary_sha256 = (
            find.file_digest(self.shape_guidance_binary) if self.shape_guidance_binary else None)
        super().__init__(*args, **kwargs)
        try:
            for index, (source, limit) in enumerate(((shape_file, 16 * 1024 * 1024),
                                                     (shape_config, find.MAX_REQUEST))):
                source = Path(source).resolve(strict=True)
                data = find.read(source, limit)
                self.originals[source] = (find.digest(data), limit)
                frozen = self.directory / f'shape-{index}.input'
                frozen.write_bytes(data)
                frozen.chmod(0o600)
                if index == 0:
                    self.shape_file = frozen
                    self.shape_sha256 = find.digest(data)
                else:
                    self.shape_config_file = frozen
                    self.shape_metadata = json.loads(data)
            if (not isinstance(self.shape_metadata, dict)
                    or self.shape_metadata.get('version') != 1
                    or self.shape_metadata.get('origin') not in ('operator_authored_demo', 'source_published')
                    or self.shape_metadata.get('data_graph') != ask.GRAPH
                    or self.shape_metadata.get('data_snapshot_id') != ask.SNAPSHOT):
                raise ValueError('Shape guidance must map a supported origin to this authorized data snapshot')
        except Exception:
            self.close()
            raise

    def current(self):
        super().current()
        if self.shape_guidance_binary:
            try:
                current = find.file_digest(self.shape_guidance_binary)
            except OSError as error:
                self.tab = self.pending = None
                raise ValueError('Stale shape-guidance executable') from error
            if current != self.shape_guidance_binary_sha256:
                self.tab = self.pending = None
                raise ValueError('Stale shape-guidance executable')

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

    def shape_suggestions(self, question, language):
        if not self.shape_guidance_binary:
            raise ValueError('Build the separate shape-guidance executable first')
        request_path = self.directory / 'shape-request.json'
        budget_path = self.directory / 'shape-budget.json'
        request_path.write_text(json.dumps(dict(question=question, language=language, snapshot_id=self.snapshot,
                                                index_revision=self.receipt['index_revision'], scope=[ask.GRAPH])))
        budget_path.write_text(json.dumps(self.budget))
        request_path.chmod(0o600)
        budget_path.chmod(0o600)
        command = [str(self.shape_guidance_binary), *self.common, str(self.shape_file), 'trig',
                   str(self.shape_config_file), str(request_path), str(budget_path)]
        try:
            with tempfile.TemporaryFile(dir=self.directory) as output, tempfile.TemporaryFile(dir=self.directory) as errors:
                result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output, stderr=errors, timeout=45)
                output.seek(0)
                errors.seek(0)
                data = output.read(find.MAX_RESPONSE + 1)
                error = errors.read(find.MAX_REQUEST + 1)
            if result.returncode or len(data) > find.MAX_RESPONSE or len(error) > find.MAX_REQUEST:
                raise ValueError('Shape suggestion failed')
            response = json.loads(data)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
            raise ValueError('Shape suggestion failed') from error
        self.current()
        return response

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
        if route == PREFIX + 'suggestions':
            bridge.Bundle.api(self, bridge.PREFIX + 'unreview', {}, tab)
            self.proposal = None
            if (not isinstance(request, dict) or set(request) != {'question', 'language'}
                    or not isinstance(request['question'], str) or not request['question'].strip()
                    or len(request['question'].encode()) > 4096
                    or request['language'] not in ('en', 'nb')):
                raise ValueError('A non-empty question and supported language are required')
            return self.shape_suggestions(request['question'], request['language'])
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
            ui_version='assisted-ask-v1-direction-shape-neighborhood-entities',
            backend='manual-structured-selection-explicit-direction',
            adapter_sha256=find.file_digest(Path(__file__)),
            shape_guidance_binary_sha256=self.bundle.shape_guidance_binary_sha256,
            shape_guidance=dict(origin=self.bundle.shape_metadata['origin'],
                                source=self.bundle.shape_metadata['source']['source'],
                                license=self.bundle.shape_metadata['source']['license'],
                                shape_snapshot_id=self.bundle.shape_metadata['shape_snapshot_id'],
                                shape_sha256=self.bundle.shape_sha256,
                                data_graph=self.bundle.shape_metadata['data_graph']),
            assets={route: find.digest(body) for route, (body, _) in self.assets.items()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ask.ROOT / 'target/debug/verity')
    parser.add_argument('--shape-guidance-binary', type=Path, default=SHAPE_GUIDANCE_BINARY)
    parser.add_argument('--shape-file', type=Path, default=SHAPE_FILE,
                        help='operator-selected local TriG shape source')
    parser.add_argument('--shape-config', type=Path, default=SHAPE_CONFIG,
                        help='operator-supplied shape source, license, and graph mapping manifest')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args(argv)
    bundle = None
    try:
        bundle = Bundle(args.binary, ask.DATA / 'snapshot.nq', 'nquads', ask.DATA / 'policy.json',
                        ask.DATA / 'scope.json', ask.DATA / 'discovery.json',
                        shape_guidance_binary=args.shape_guidance_binary,
                        shape_file=args.shape_file, shape_config=args.shape_config)
        if not bundle.shape_guidance_binary:
            raise ValueError('Build shape_guidance before launch')
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
