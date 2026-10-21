#!/usr/bin/env python3
"""Separately frozen Qwen status precedence; inherit v1h's preview-only runner."""
import argparse
from contextlib import contextmanager
import difflib
import json
from pathlib import Path
import signal
import sys

import native_one_hop_v1h as h

ROOT = h.ROOT
CONFIG = ROOT / 'configs/native-one-hop-v1h-qwen-status-precedence.json'
RELEASE = ROOT / 'experiments/native-one-hop-v1h-qwen-status-precedence'
VERSION = 'issue83-native-cpu-v1h-qwen-status-precedence'
SOURCES = ['tools/native_one_hop_v1h_status_precedence.py',
           'tools/test_native_one_hop_v1h_status_precedence.py',
           str((RELEASE / 'README.md').relative_to(ROOT)),
           str((RELEASE / 'prompt.diff').relative_to(ROOT))]
PARENT = h.RELEASE
BASE_VERIFY = h.verify


@contextmanager
def experiment():
    previous = h.CONFIG, h.RELEASE, h.VERSION, h.verify
    h.CONFIG, h.RELEASE, h.VERSION, h.verify = CONFIG, RELEASE, VERSION, verify
    try:
        yield
    finally:
        h.CONFIG, h.RELEASE, h.VERSION, h.verify = previous


def parent():
    cfg = h.config()
    h.require(h.sha(ROOT / cfg['parent_registration']) == cfg['parent_registration_sha256'],
              'Changed parent registration')
    h.require(h.sha(ROOT / cfg['baseline_evidence']) == cfg['baseline_evidence_sha256'],
              'Changed original Qwen evidence')
    registered = h.read(ROOT / cfg['parent_registration'])
    h.require(h.sha(PARENT / 'freeze.tar.gz') == registered['archive_sha256'], 'Changed parent archive')
    return registered, h.a.g.archive_files(PARENT / 'freeze.tar.gz')


def verify(folder, binary=h.a.BINARY):
    frozen = BASE_VERIFY(folder, binary)
    registered, payload = parent()
    cfg = h.config()
    old_cfg = registered['freeze_manifest']['config']
    changed = set(h.read(CONFIG)) - set(h.read(ROOT / 'configs/native-one-hop-v1h-budget.json'))
    changed |= {'version', 'prompt_file', 'variants', 'semantic_prompt_change', 'hypothesis', 'comparison'}
    h.require({k: v for k, v in cfg.items() if k not in changed} ==
              {k: v for k, v in old_cfg.items() if k not in changed}, 'Changed non-status configuration')
    h.require(cfg['variants'] == ['qwen35'] and cfg['host_gates']['swap_used_mib_max'] == 1024,
              'Original Qwen admission gate required')
    sources = SOURCES + [cfg['prompt_file'], cfg['parent_registration'], cfg['baseline_evidence']]
    h.require(all(frozen['input_sha256'].get(name) == h.sha(ROOT / name) for name in sources),
              'Missing status-ablation source binding')
    # Bind all source information, grammar and observation identities to v1h, byte for byte.
    for name, raw in payload.items():
        if name.startswith(('contexts/', 'original-contexts/', 'grammars/', 'packets/')) or name in ['schedule.json', 'operator-fixtures.json']:
            h.require((folder / name).read_bytes() == raw, 'Changed parent input: ' + name)
    before = (ROOT / old_cfg['prompt_file']).read_text()
    after = (ROOT / cfg['prompt_file']).read_text()
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                   fromfile=old_cfg['prompt_file'], tofile=cfg['prompt_file']))
    h.require((RELEASE / 'prompt.diff').read_text() == diff, 'Changed exact prompt diff')
    h.require(h.read(folder / 'tokenization/job.json') == h.token_job(folder, ['qwen35'], sections=True),
              'Changed tokenizer job/messages')
    counts = h.read(folder / 'tokenization/counts.json')
    original_counts = json.loads(payload['tokenization/counts.json'])
    h.require(set(counts['models']) == {'qwen35'} and counts['inference_performed'] is False
              and all(counts[k] == original_counts[k] for k in ['python', 'packages']),
              'Changed tokenizer environment or model')
    for row in counts['models']['qwen35']['rows']:
        for variant in ['original', 'columnar']:
            receipt = row[variant]
            h.require(receipt['output_reserve'] == 512 and receipt['fits'] == (receipt['total_required'] < 16384)
                      and sum(receipt['section_contributions'].values()) == receipt['input_tokens'],
                      'Changed exact token budget')
    return frozen


def freeze(out):
    # The inherited builder verifies before the successor's source bindings are added.
    h.verify = BASE_VERIFY
    try:
        h.materialize(out)
    finally:
        h.verify = verify
    frozen = h.read(out / 'freeze.json')
    cfg = h.config()
    sources = SOURCES + [cfg['prompt_file'], cfg['parent_registration'], cfg['baseline_evidence']]
    frozen['input_sha256'].update({name: h.sha(ROOT / name) for name in sources})
    h.dump(out / 'freeze.json', frozen)
    h.dump(out / 'checksums.json', h.a.v.inventory(out))
    verify(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'register', 'verify', 'budget', 'replay', 'run'])
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--model', choices=['qwen35'], default='qwen35')
    parser.add_argument('--run', type=Path)
    parser.add_argument('--allow-inference', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Operator cancelled'))
    with experiment():
        if args.command == 'freeze':
            h.require(args.out, 'Fresh --out required')
            freeze(args.out.resolve())
            return
        h.require(args.freeze, '--freeze required')
        folder = args.freeze.resolve()
        if args.command == 'register':
            h.register(folder)
        elif args.command == 'verify':
            h.verify_registration(folder)
        elif args.command == 'replay':
            print(json.dumps(h.replay(folder, args.run.resolve() if args.run else None)))
        elif args.command == 'budget':
            verify(folder)
            h.require(args.out, 'Fresh --out required')
            h.count_tokens(folder, args.out.resolve(), ['qwen35'])
        else:
            h.require(args.out and args.out.resolve() == ROOT / h.config()['proposed_output'],
                      'Run output must match the separately proposed command')
            state = h.run(folder, args.out.resolve(), 'qwen35', args.allow_inference)
            print(json.dumps(state, indent=2))
            raise SystemExit(0 if state['status'] == 'completed_diagnostic' else 1)


if __name__ == '__main__':
    main()
