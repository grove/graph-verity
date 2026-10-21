#!/usr/bin/env python3
"""Separately registered Gemma v1h host-gate variant; Rust preview only."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import native_one_hop_v1h as h

ROOT = h.ROOT
VERSION = 'issue83-native-cpu-v1h-budget-swap2048'
RELEASE = ROOT / 'experiments/native-one-hop-v1h-budget-swap2048'
PARENT_SHA256 = 'beb4e84519294d9f6b870236573c3728f4ccc028465db73c0cb97ab36a414bc7'
SOURCES = ['tools/native_one_hop_v1h_swap2048.py', 'tools/test_native_one_hop_v1h_swap2048.py',
           'experiments/native-one-hop-v1h-budget-swap2048/README.md']


def definition():
    parent = h.RELEASE / 'registration.json'
    h.require(h.sha(parent) == PARENT_SHA256, 'Changed parent registration')
    registered = h.read(parent)
    cfg = h.config()
    h.require(cfg['host_gates']['swap_used_mib_max'] == 1024, 'Changed parent swap ceiling')
    return dict(version=VERSION, parent_registration_sha256=PARENT_SHA256,
        change=dict(field='host_gates.swap_used_mib_max', previous=1024, proposed=2048,
                    owner_request_exact='Can we change the ceiling to be 2048MiB instead?'),
        parent_freeze_archive_sha256=registered['archive_sha256'],
        parent_freeze_sha256=registered['freeze_sha256'],
        registered_binary_sha256=registered['freeze_manifest']['binary_sha256'],
        source_input_sha256={name: h.sha(ROOT / name) for name in SOURCES},
        effective_config={**cfg, 'host_gates': {**cfg['host_gates'], 'swap_used_mib_max': 2048}},
        model='gemma4', sampling_controls=2, semantic_observations=36, maximum_requests=38, retries=0,
        attempt_ledger='Shared parent freeze/model ledger; original and variant are not separate retry allowances.',
        registration_resealed=False, inference_authorized=False, inference_performed=False,
        model_generated_rdf_executions=0, integration_authorized=False,
        independent_human_review='deferred', decision='INCONCLUSIVE_REVISE')


def verify(folder, committed=True):
    h.verify_registration(folder)
    registered = h.read(RELEASE / 'registration.json')
    h.require(registered == definition(), 'Changed swap2048 registration or source')
    if committed:
        for name in [*SOURCES, str((RELEASE / 'registration.json').relative_to(ROOT))]:
            original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
            h.require(original == (ROOT / name).read_bytes(), 'Variant must be committed: ' + name)
    return registered


@contextmanager
def host_gate():
    original = h.a.preflight

    def preflight(out):
        host = original(out.with_name(out.stem + '-original-1024.json'))
        cfg = definition()['effective_config']
        changed = h.a.t.host_blockers(host, cfg)
        amended = {**host, 'host_gate_variant': VERSION,
            'effective_host_gates': cfg['host_gates'], 'original_blockers': host['blockers'],
            'blockers': [b for b in host['blockers'] if b['metric'] != 'swap_used_mib']
                        + [b for b in changed if b['metric'] == 'swap_used_mib']}
        h.dump(out, amended)
        return amended

    # The frozen runner has no gate injection parameter; preserve its source and every other check.
    h.a.preflight = preflight
    try:
        yield
    finally:
        h.a.preflight = original


def run(folder, out, allow_inference=False):
    h.require(allow_inference, 'Separate exact-command authorization and --allow-inference required')
    h.require(not os.environ.get('CI') and not os.environ.get('GITHUB_ACTIONS'),
              'Inference forbidden in CI')
    registered = verify(folder)
    h.require(not out.exists(), 'Fresh variant output directory required')
    ledger = ROOT / 'artifacts' / ('v1h-budget-attempts-' + registered['parent_freeze_sha256'] + '.json')
    h.require(not ledger.exists() or 'gemma4' not in h.read(ledger), 'No retries across parent and variant')
    out.mkdir(parents=True)
    h.dump(out / 'variant-registration.json', registered)
    state = dict(version=VERSION, model='gemma4', status='preparing', decision='INCONCLUSIVE_REVISE')
    try:
        with host_gate():
            parent = h.run(folder, out / 'run', 'gemma4', allow_inference=True)
        state.update(status=parent['status'], parent_run='run/run.json',
                     generation_attempts=parent['generation_attempts'], generation_completed=parent['generation_completed'])
    except BaseException as error:
        state.update(status='blocked_or_failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        h.dump(out / 'variant.json', state)
        h.dump(out / 'checksums.json', {str(p.relative_to(out)): h.sha(p) for p in sorted(out.rglob('*'))
                                      if p.is_file() and p != out / 'checksums.json'})
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['register', 'verify', 'preflight', 'run'])
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--allow-inference', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Operator cancelled'))
    folder = args.freeze.resolve()
    if args.command == 'register':
        h.verify_registration(folder)
        h.require(not (RELEASE / 'registration.json').exists(), 'Append-only variant registration')
        h.dump(RELEASE / 'registration.json', definition())
    elif args.command == 'verify':
        verify(folder)
    else:
        h.require(args.out, 'Fresh --out required')
        if args.command == 'preflight':
            verify(folder)
            with h.adapter(), host_gate():
                result = h.a.preflight(args.out.resolve())
        else:
            result = run(folder, args.out.resolve(), args.allow_inference)
        print(json.dumps(result, indent=2))
        if args.command == 'run':
            raise SystemExit(0 if result['status'] == 'completed_diagnostic' else 1)


if __name__ == '__main__':
    main()
