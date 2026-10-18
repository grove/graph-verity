#!/usr/bin/env python3
"""Replay pilot-v1.1 checks from their pinned source without amending historic evidence."""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'f12422a0b106faa84c2f1cd05c8ee99fea14c185'
FREEZE = 'studies/pilot-v1/freeze.json'
FREEZE_SHA256 = '5398f886ec1812ac23a427134b9008ca092c559669991fdfa0b919f8d6c38353'


@contextmanager
def source_snapshot():
    def blob(name):
        return subprocess.check_output(['git', 'cat-file', 'blob', COMMIT + ':' + name], cwd=ROOT)

    raw = blob(FREEZE)
    if sha256(raw).hexdigest() != FREEZE_SHA256:
        raise ValueError('Historical pilot freeze identity mismatch')
    with tempfile.TemporaryDirectory(prefix='verity-frozen-pilot-') as temp:
        source = Path(temp)
        for name, expected in {**json.loads(raw)['files'], FREEZE: FREEZE_SHA256}.items():
            path = source / name
            data = blob(name)
            if sha256(data).hexdigest() != expected:
                raise ValueError('Historical pilot source mismatch: ' + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        yield source


def current_tests():
    def cases(suite):
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from cases(item)
            else:
                yield item
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tools'), pattern='test_*.py')
    # These exact original tests run below against the source bytes their freeze pins.
    return unittest.TestSuite(c for c in cases(suite) if c.__class__.__module__ != 'test_pilot_study')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['test-all', 'verify', 'rehearse'])
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.command == 'test-all':
        if not unittest.TextTestRunner(verbosity=2).run(current_tests()).wasSuccessful():
            return 1
    with source_snapshot() as source:
        if args.command == 'test-all':
            command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(source / 'tools'),
                       '-p', 'test_pilot_study.py', '-v']
        else:
            command = [sys.executable, str(source / 'tools/pilot_study.py'), args.command]
            if args.out:
                command += ['--out', str(args.out.resolve())]
        return subprocess.run(command, cwd=source).returncode


if __name__ == '__main__':
    raise SystemExit(main())
