#!/usr/bin/env python3
"""Prepare and run the checksummed #58 saved review, offline and model-free."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PIN = 'ba9e57f8574ebf2c28797a98004dd6fbda61abfe'
PROTOCOL = '6223e88dbca50cbc9e09b3eb8c0fa4034fe4f55ba8405e66318b37a633c84354'
MANIFEST = '1a415f85d63f5e68ebe85eccba11a1a59603e45b55f29cb7f9743a6f378beab8'
CAPTURE = 'reports/issue-58-human-review/saved-results.json.gz'
SESSIONS = {'01': 'independent', '02': 'independent', 'owner': 'owner', 'rehearsal': 'rehearsal'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    data = (ROOT / 'studies/hybrid-review-handoff/manifest.json').read_bytes()
    require(digest(data) == MANIFEST, 'Handoff manifest changed; stop, do not repair frozen inputs')
    result = json.loads(data)
    require(result['source_commit'] == PIN and result['protocol_id'] == PROTOCOL, 'Wrong study')
    return result


def private_directory(path):
    require(not path.is_symlink(), 'Private directory cannot be a symlink')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(path.is_dir() and path.stat().st_mode & 0o777 == 0o700,
            'Private directory must have mode 0700; inspect it before changing permissions')


def check_source(source, spec):
    require(source.is_dir() and not source.is_symlink(), 'Missing isolated study source')
    require(source.stat().st_mode & 0o222 == 0, 'Study source must be read-only')
    files = set()
    for path in source.rglob('*'):
        require(not path.is_symlink(), 'Symlink in isolated study source')
        require(path.stat().st_mode & 0o222 == 0, 'Study source must be read-only')
        if path.is_file():
            name = path.relative_to(source).as_posix()
            files.add(name)
            require(name in spec['files'] and digest(path.read_bytes()) == spec['files'][name]['sha256'],
                    'Study source hash mismatch: ' + name)
        else:
            require(path.is_dir(), 'Unexpected study source entry')
    require(files == set(spec['files']), 'Missing/unexpected study source files; do not repair in place')


def prepare_source(source, spec):
    if source.exists() or source.is_symlink():
        check_source(source, spec)
        return
    staging = source.with_name('.source-' + secrets.token_hex(8))
    staging.mkdir(mode=0o700)
    try:
        for name, expected in spec['files'].items():
            result = subprocess.run(['git', '-C', str(ROOT), 'cat-file', 'blob', PIN + ':' + name],
                                    capture_output=True, check=False)
            require(result.returncode == 0, 'Pinned Git objects unavailable; obtain the documented offline kit')
            require(digest(result.stdout) == expected['sha256'], 'Pinned source mismatch: ' + name)
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(result.stdout)
        for path in staging.rglob('*'):
            path.chmod(0o500 if path.is_dir() else 0o400)
        staging.chmod(0o500)
        check_source(staging, spec)
        staging.rename(source)
    finally:
        if staging.exists():
            staging.chmod(0o700)
            for path in staging.rglob('*'):
                if path.is_dir():
                    path.chmod(0o700)
            shutil.rmtree(staging)


def prepare_capture(private, source, spec, *, allow_create=True):
    archive = (source / CAPTURE).read_bytes()
    require(digest(archive) == spec['capture_sha256'], 'Archived capture identity mismatch')
    data = gzip.decompress(archive)
    require(digest(data) == spec['results_sha256'], 'Decompressed capture identity mismatch')
    require(json.loads(data)['protocol_id'] == PROTOCOL, 'Wrong capture protocol')
    path = private / 'results.json'
    if path.exists() or path.is_symlink():
        require(not path.is_symlink() and path.is_file()
                and path.stat().st_mode & 0o777 == 0o600, 'Capture must be a private regular file')
        require(digest(path.read_bytes()) == spec['results_sha256'],
                'Existing capture differs; refusing to replace it')
    else:
        require(allow_create and not any(private.glob('reviewer-*.json')),
                'Missing capture for an existing session/report; stop and investigate')
        # Exclusive creation never replaces a capture, including a concurrent writer's.
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
            stream.write(data)
    return path


def worker(args, private):
    spec = manifest()
    source = private / 'source'
    check_source(source, spec)
    results = prepare_capture(private, source, spec, allow_create=args.command != 'report')
    # -I -S -B excludes evolving main, site packages, PYTHONPATH and bytecode.
    sys.path.insert(0, str(source / 'tools'))
    import hybrid_review as review
    require(review.verify()[2] == PROTOCOL, 'Wrong frozen protocol')
    review.forms.PRIVATE = private
    study = review.Review(demo=False, results=results)
    if args.command == 'prepare':
        print('Verified pinned source, protocol, catalog and saved ranks. No reviewer created.')
        return 0
    if args.command == 'report':
        output = private / 'report.json'
        require(not output.is_symlink() and (not output.exists() or
                (output.is_file() and output.stat().st_mode & 0o777 == 0o600)),
                'Report must be a private regular file')
        paths = [private / name for name in args.sessions]
        for path in paths:
            require(path.name in {'reviewer-' + key + '.json' for key in SESSIONS}
                    and path.parent == private and path.is_file() and not path.is_symlink()
                    and path.stat().st_mode & 0o777 == 0o600, 'Invalid/private session required')
        sessions = [review.forms.load(path) for path in paths]
        seeds = [s['seed'] for s in sessions]
        require(len(set(seeds)) == len(seeds), 'Replayed reviewer seed')
        require(all(not s['demo'] for s in sessions), 'Exposed demo session is not this saved review')
        sys.argv = ['hybrid_review.py', 'report', '--results', str(results),
                    '--out', str(output), *map(str, paths)]
        return review.main()
    path = private / ('reviewer-' + args.reviewer + '.json')
    require(not path.exists() and not path.is_symlink(), 'Reviewer file already exists; refusing replay/overwrite')
    study = review.Review(demo=False, results=results, kind=args.kind, consent=args.consent, out=path)
    with review.local.Server(study, '127.0.0.1', 0) as server:
        server.assets = {route: ((review.ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ('/', 'index.html', 'text/html'), ('/app.js', 'app.js', 'text/javascript'),
            ('/style.css', 'style.css', 'text/css'))}
        require(webbrowser.open(server.url), 'Browser unavailable; keep the session file and resolve locally')
        print('Private localhost review opened in your browser. Stop with Ctrl-C. Do not share the address.', flush=True)
        server.serve_forever()
    return 0


def main():
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        os.execv(sys.executable, [sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('prepare', help='Verify/create the offline source and capture; no enrollment')
    launch = commands.add_parser('launch', help='One fresh session for one consenting person')
    launch.add_argument('--reviewer', required=True, choices=SESSIONS)
    launch.add_argument('--kind', required=True, choices=set(SESSIONS.values()))
    launch.add_argument('--consent', action='store_true')
    report = commands.add_parser('report', help='Write only study-private/hybrid/report.json')
    report.add_argument('sessions', nargs='*', default=['reviewer-01.json', 'reviewer-02.json'])
    args = parser.parse_args()
    try:
        require(sys.version_info >= (3, 11) and os.name == 'posix', 'Requires Python 3.11+ on macOS/Linux')
        if args.command == 'launch':
            require(SESSIONS[args.reviewer] == args.kind, 'Reviewer filename/kind mismatch')
            require(args.kind == 'rehearsal' or args.consent, 'Obtain actual informed consent before launch')
        private = ROOT / 'study-private'
        private_directory(private)
        private /= 'hybrid'
        private_directory(private)
        lock = private / '.operator-lock'
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.close(descriptor)
            prepare_source(private / 'source', manifest())
            return worker(args, private)
        finally:
            lock.unlink()
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Review unavailable: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
