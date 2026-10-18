#!/usr/bin/env python3
"""Replay frozen study checks from pinned Rust sources without amending evidence."""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'f12422a0b106faa84c2f1cd05c8ee99fea14c185'
FREEZE = 'studies/pilot-v1/freeze.json'
FREEZE_SHA256 = '5398f886ec1812ac23a427134b9008ca092c559669991fdfa0b919f8d6c38353'
EXTRA_FILES = {'data/wikidata/scope.json': '4815891ffd7325fbb7be1ac24b835160164c3b418c8e1647e59cb23572c82aee'}


@contextmanager
def source_snapshot():
    def blob(name):
        return subprocess.check_output(['git', 'cat-file', 'blob', COMMIT + ':' + name], cwd=ROOT)

    raw = blob(FREEZE)
    if sha256(raw).hexdigest() != FREEZE_SHA256:
        raise ValueError('Historical pilot freeze identity mismatch')
    with tempfile.TemporaryDirectory(prefix='verity-frozen-pilot-') as temp:
        source = Path(temp)
        for name, expected in {**json.loads(raw)['files'], **EXTRA_FILES, FREEZE: FREEZE_SHA256}.items():
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


def current_selective_lexical():
    import selective_hybrid as study
    spec, cases = study.verify_protocol()
    session = study.h.Session(str(ROOT / 'target/debug/examples/retrieval_session'), spec['corpus'])
    current_revision = session.ready['manifest']['index_revision']
    recorded_revisions = set()
    try:
        with gzip.open(ROOT / 'reports/issue-53-selective-hybrid/run/skos-definitions-v1-resident-scores.jsonl.gz', 'rt') as stream:
            pools = [json.loads(line) for line in stream]
        study.r.require(len(pools) == len(cases), 'Selective lexical denominator changed')
        for case, pool in zip(cases, pools):
            study.r.require(pool['id'] == case['id'], 'Selective lexical case changed')
            actual = session.query(study.h.request(case, spec))
            expected = pool['lexical']
            study.r.require(actual.pop('index_revision') == current_revision, 'Inconsistent current index revision')
            recorded_revisions.add(expected.pop('index_revision'))
            study.r.require(len(actual['hits']) == len(expected['hits']), 'Selective lexical hit count changed')
            for left, right in zip(actual['hits'], expected['hits']):
                study.r.require(math.isclose(left['score'], right['score'], rel_tol=1e-12, abs_tol=1e-12), 'Selective lexical score changed')
                left['score'] = right['score']
            study.r.require(actual == expected, 'Current selective lexical behavior changed')
    finally:
        session.close()
    print(json.dumps(dict(current_index_revision=current_revision, recorded_index_revisions=sorted(recorded_revisions),
                          current_lexical_cases_verified=len(cases), model_invoked=False)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['test-all', 'verify', 'rehearse', 'selective-replay'])
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.command == 'test-all':
        if not unittest.TextTestRunner(verbosity=2).run(current_tests()).wasSuccessful():
            return 1
    with source_snapshot() as source:
        if args.command == 'selective-replay':
            subprocess.run(['cargo', 'build', '--locked', '--offline', '--quiet', '-p', 'verity_cli',
                            '--example', 'retrieval_session'], cwd=ROOT, check=True)
            current_selective_lexical()
            subprocess.run(['cargo', 'build', '--locked', '--offline', '--quiet', '-p', 'verity_cli',
                            '--example', 'retrieval_session'], cwd=source, check=True)
            command = [sys.executable, str(ROOT / 'tools/selective_hybrid.py'), 'verify-report',
                       '--freeze', str(ROOT / 'reports/issue-53-selective-hybrid/freeze'),
                       '--out', str(ROOT / 'reports/issue-53-selective-hybrid/run'),
                       '--binary', str(source / 'target/debug/examples/retrieval_session')]
        elif args.command == 'test-all':
            command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(source / 'tools'),
                       '-p', 'test_pilot_study.py', '-v']
        else:
            command = [sys.executable, str(source / 'tools/pilot_study.py'), args.command]
            if args.out:
                command += ['--out', str(args.out.resolve())]
        return subprocess.run(command, cwd=source).returncode


if __name__ == '__main__':
    raise SystemExit(main())
