"""Operator-only execution of the immutable #103 diagnostic freeze; preview only."""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

import predicate_diagnostics as d
import native_one_hop_v1h as h

ROOT, a = d.ROOT, d.v.a
read, dump, require, sha = d.read, d.dump, d.require, d.sha
RELEASE = ROOT / 'experiments/predicate-diagnostics-v1-execution-v1'
REGISTRATION = RELEASE / 'registration.json'
FREEZE = ROOT / 'artifacts/predicate-diagnostics-v1-execution-v1/freeze'
OUTPUT = ROOT / 'artifacts/predicate-diagnostics-v1-execution-v1/run'
LEDGER = ROOT / 'artifacts/predicate-diagnostics-v1-execution-v1/attempt.json'
VERSION = 'predicate-diagnostics-native-execution-v1'


@contextmanager
def native_config(cfg):
    # Native helpers read module configuration; use the exact inherited frozen limits.
    previous = a.config
    a.config = lambda: cfg
    try:
        yield
    finally:
        a.config = previous


def unpack(folder):
    require(not folder.exists(), 'Fresh freeze destination required')
    reg = read(d.RELEASE / 'registration.json')
    require(sha(d.RELEASE / 'freeze.tar.gz') == reg['archive_sha256'], 'Changed #103 archive')
    for name, raw in a.g.archive_files(d.RELEASE / 'freeze.tar.gz').items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    d.verify_registration(folder)


def committed(pins, revision):
    for name, digest in pins.items():
        require(sha(ROOT / name) == digest, 'Changed execution source: ' + name)
        raw = subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
        require(d.m.digest(raw) == digest, 'Commit execution inputs first: ' + name)


def identities(folder):
    tokens = read(folder / 'token-counts.json')['models']['qwen35']['rows']
    schedule = read(folder / 'schedule.json')
    require(len(schedule) == len(tokens) == 126, '126-request schedule required')
    result = []
    for row, token in zip(schedule, tokens):
        key = row['id']
        require(token['name'] == key and token['columnar']['fits'] and
                token['columnar']['total_required'] < 16384, 'Token schedule mismatch/overflow')
        result.append(dict(**row, packet_id=read(folder / 'context-packets' / (key + '.json'))['packet_id'],
            files={name: sha(folder / name) for name in [
                'messages/' + key + '.json', 'contexts/' + key + '.json',
                'grammars/' + key + '.gbnf', 'context-packets/' + key + '.json']},
            prompt_sha256=token['columnar']['prompt_sha256'], tokens_sha256=token['columnar']['tokens_sha256']))
    return result


def register(folder):
    frozen = d.verify_registration(folder)
    require(folder == FREEZE and not REGISTRATION.exists(), 'Append-only fixed execution registration')
    pins = {str(p.relative_to(ROOT)): sha(p) for p in [
        Path(__file__), ROOT / 'tools/test_predicate_diagnostics_native.py', RELEASE / 'README.md',
        d.RELEASE / 'registration.json', d.RELEASE / 'freeze.tar.gz',
        d.RELEASE / 'model-free-notes.md', d.RELEASE / 'model-free-replay.json',
        d.RELEASE / 'preservation.json', d.RELEASE / 'verify.py']}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    committed(pins, revision)
    record = dict(version=VERSION, source_commit=revision, input_sha256=pins,
        original_registration_sha256=sha(d.RELEASE / 'registration.json'),
        original_archive_sha256=sha(d.RELEASE / 'freeze.tar.gz'),
        checksums_sha256=sha(folder / 'checksums.json'), schedule=identities(folder),
        runtime_config=frozen['runtime_config'], runtime_identity=frozen['runtime_identity'],
        binary_sha256=frozen['binary_sha256'], bridge_sha256=frozen['bridge_sha256'],
        scorer_sha256=sha(ROOT / 'tools/predicate_diagnostics.py'),
        destinations=dict(freeze=str(FREEZE.relative_to(ROOT)), output=str(OUTPUT.relative_to(ROOT)),
                          ledger=str(LEDGER.relative_to(ROOT))),
        maximum_completion_requests=126, retries=0, model='qwen35',
        command=['.venv/bin/python', 'tools/predicate_diagnostics_native.py', 'run', '--allow-inference'],
        inference_authorized=False, inference_performed=False, executions=0,
        issue83='keep_open', issue75_integration='disabled', independent_human_review='deferred',
        decision='INCONCLUSIVE_REVISE')
    with REGISTRATION.open('x') as stream:
        stream.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    return record


def verify(folder, committed_registration=False):
    frozen = d.verify_registration(folder)
    reg = read(REGISTRATION)
    require(reg['version'] == VERSION and reg['checksums_sha256'] == sha(folder / 'checksums.json') and
            reg['original_registration_sha256'] == sha(d.RELEASE / 'registration.json') and
            reg['original_archive_sha256'] == sha(d.RELEASE / 'freeze.tar.gz'), 'Execution registration mismatch')
    committed(reg['input_sha256'], reg['source_commit'])
    require(reg['schedule'] == identities(folder), 'Changed registered schedule/packets/prompts')
    for key in ['runtime_config', 'runtime_identity', 'binary_sha256', 'bridge_sha256']:
        require(reg[key] == frozen[key], 'Changed execution runtime/binary: ' + key)
    require(reg['scorer_sha256'] == sha(ROOT / 'tools/predicate_diagnostics.py'), 'Changed scorer')
    require(reg['destinations'] == dict(freeze=str(FREEZE.relative_to(ROOT)), output=str(OUTPUT.relative_to(ROOT)),
            ledger=str(LEDGER.relative_to(ROOT))) and reg['maximum_completion_requests'] == 126 and
            reg['retries'] == 0 and reg['model'] == 'qwen35' and reg['inference_authorized'] is False and
            reg['inference_performed'] is False and reg['executions'] == 0 and
            reg['command'] == ['.venv/bin/python', 'tools/predicate_diagnostics_native.py', 'run', '--allow-inference'] and
            reg['issue83'] == 'keep_open' and reg['issue75_integration'] == 'disabled' and
            reg['independent_human_review'] == 'deferred' and reg['decision'] == 'INCONCLUSIVE_REVISE',
            'Changed execution boundaries')
    if committed_registration:
        raw = subprocess.check_output(['git', 'show', 'HEAD:' + str(REGISTRATION.relative_to(ROOT))], cwd=ROOT)
        require(raw == REGISTRATION.read_bytes(), 'Execution registration must be committed')
    return frozen


def recount(folder, out):
    code = a.bounded([read(ROOT / 'reports/issue-74-one-hop-trial/assets.json')['candidates']['qwen35']
        ['preparation_receipt']['commands'][2][0], ROOT / 'tools/native_one_hop_v1h_tokens.py',
        folder / 'token-job.json', out / 'token-counts.json'], out, 'tokenizer', 120)
    require(code == 0, 'Pinned tokenizer failed')
    actual = read(out / 'token-counts.json')
    require(actual == read(folder / 'token-counts.json'), 'Fresh tokenizer receipt drift')
    return actual['models']['qwen35']['rows']


def preview(folder, key, raw, packet_id):
    if key.startswith('sampling-'):
        context = read(folder / 'contexts' / (key + '.json'))
        d.m.revalidate(read(folder / 'context-packets' / (key + '.json')), context, d.m.build(), packet_id)
        with tempfile.TemporaryDirectory(prefix='predicate-control-') as temp:
            dest = Path(temp)
            (dest / 'proposal.txt').write_bytes(raw)
            return a.preview_raw(context, dest / 'proposal.txt', dest,
                                 dict(resolved_start=None, blocked=False))
    return d.preview(folder, key, raw, packet_id)


def packet(folder, key):
    context = read(folder / 'contexts' / (key + '.json'))
    saved = read(folder / 'context-packets' / (key + '.json'))
    d.m.revalidate(saved, context, d.m.build(), saved['packet_id'])
    return context, saved['packet_id']


def observe(folder, out, state, runtime, rss, cfg):
    refs = read(folder / 'expected.json')
    for index, row in enumerate(state['rows']):
        key = row['id']
        dest = out / 'requests' / key
        dest.mkdir(parents=True)
        before, started, attempts = dict(rss), time.monotonic(), runtime.generation_attempts
        try:
            verify(folder)
            h.d.resource_guard(rss, cfg)
            context, row['packet_id'] = packet(folder, key)
            messages = read(folder / 'messages' / (key + '.json'))
            with d.v.adapter():
                require(a.grammar(context) == (folder / 'grammars' / (key + '.gbnf')).read_text(), 'Grammar drift')
            trusted = preview(folder, key, b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"Host preflight"}', row['packet_id'])
            require(trusted['returncode'] == 0, 'Trusted source/catalog preflight failed')
            dump(dest / 'trusted-preflight.json', trusted)
            require(attempts == index and attempts < 126, 'No retries; request cap/order mismatch')
            row['status'] = 'attempting'
            row['runtime'] = runtime.generate(context, dest, constrained=key != 'sampling-unconstrained',
                                               system=messages[0]['content'])
            require(read(dest / 'messages.json') == messages, 'Exact frozen message mismatch')
            raw = (dest / 'proposal.txt').read_bytes()
            row['rust_preview'] = preview(folder, key, raw, row['packet_id'])
            h.d.validator_guard(row['rust_preview'])
            row['gbnf_valid'] = a.grammar_check(raw.decode('utf-8'), context, dest)
            if key.startswith('sampling-'):
                require(row['gbnf_valid'] == (key == 'sampling-constrained') and
                        (key != 'sampling-constrained' or row['rust_preview']['returncode'] == 0), 'Native sampling control failed')
            else:
                require(row['gbnf_valid'], 'Native grammar integrity failure')
            require(b'PRIVATE_CANARY' not in raw, 'Private-scope authorization failure')
            if key == 'repeat-1':
                for name in ['prompt.txt', 'completion-request.json']:
                    require((out / 'requests/repeat-0' / name).read_bytes() == (dest / name).read_bytes(),
                            'Repeat prompt/request integrity failure')
            verify(folder)
            h.d.resource_guard(rss, cfg)
            row['status'] = 'completed'
        except BaseException as error:
            row.update(status='fatal_failure', failure=type(error).__name__ + ': ' + str(error))
            raise
        finally:
            row['attempted'] = runtime.generation_attempts > attempts
            row.update(latency_ms=(time.monotonic() - started) * 1000, resources=dict(before=before, after=dict(rss)))
            raw_path = dest / 'proposal.txt'
            if raw_path.exists():
                raw = raw_path.read_bytes()
                row.update(raw_base64=base64.b64encode(raw).decode(), raw_sha256=d.m.digest(raw))
                if row.get('rust_preview') is None:
                    try:
                        row['rust_preview'] = preview(folder, key, raw, row['packet_id'])
                    except Exception as error:
                        row['preview_failure'] = str(error)
                if key in refs:
                    row['raw_measurement'] = d.measure(refs[key], raw,
                        row['rust_preview']['returncode'] == 0 if row.get('rust_preview') else None)
            dump(dest / 'observation.json', row)
            dump(out / 'run.json', state)


def score(folder, state):
    observations = {}
    for row in state['rows']:
        raw = base64.b64decode(row['raw_base64'], validate=True) if row['raw_base64'] is not None else None
        try:
            text = raw.decode('utf-8') if raw is not None else None
        except UnicodeDecodeError:
            text = None
        observations[row['id']] = dict(attempted=row['attempted'], packet_id=row['packet_id'], raw_utf8=text,
            failure=row['failure'] or (None if row['status'] == 'completed' else row['status']))
    # The frozen scorer supplies independent construction/metadata groups and null missing outcomes.
    return d.score(folder, observations)


def run(allow_inference=False):
    require(allow_inference, 'Separate explicit authorization and --allow-inference required')
    require(not os.environ.get('CI') and not os.environ.get('GITHUB_ACTIONS'), 'Inference forbidden in CI')
    with (ROOT / 'artifacts/native-one-hop.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        frozen = verify(FREEZE, committed_registration=True)
        require(not OUTPUT.exists() and not LEDGER.exists(), 'No overwrite or retry for this registration')
        with LEDGER.open('x') as stream:
            json.dump(dict(registration_sha256=sha(REGISTRATION), output=str(OUTPUT), consumed_before_model_load=True), stream)
        OUTPUT.mkdir(parents=True)
        cfg = frozen['runtime_config']
        state = dict(version=VERSION, registration_sha256=sha(REGISTRATION), status='preparing',
            rows=[dict(**r, status='unattempted', attempted=False, failure=None, packet_id=None,
                       raw_base64=None, raw_sha256=None) for r in read(FREEZE / 'schedule.json')],
            executions=0, integration_authorized=False, holdout_accessed=False, decision='INCONCLUSIVE_REVISE',
            independent_human_review='deferred', model_loaded=False, inference_performed=False)
        runtime, monitor = None, None
        done, rss = threading.Event(), dict(samples=0, peak_kib=0, error=None)
        with native_config(cfg):
            try:
                evidence = a.assets(OUTPUT / 'assets.json')
                require({k: evidence[k] for k in frozen['runtime_identity']} == frozen['runtime_identity'], 'Asset identity mismatch')
                tokens = recount(FREEZE, OUTPUT)
                a.grammar_controls(read(FREEZE / 'contexts/explicit-001.json'), OUTPUT / 'grammar-controls')
                host = a.preflight(OUTPUT / 'host.json')
                require(not host['blockers'], 'Fresh host gate blocked: ' + json.dumps(host['blockers']))
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(host['captured_at'])).total_seconds()
                require(0 <= age <= cfg['host_max_age_seconds'], 'Stale host admission')
                monitor = threading.Thread(target=a.sample_rss, args=(OUTPUT, done, rss), daemon=True)
                monitor.start()
                runtime = h.Runtime(cfg, a.g.ASSETS, 'qwen35', OUTPUT)
                runtime.reference_python = evidence['candidates']['qwen35']['preparation_receipt']['commands'][2][0]
                runtime.allowed_prompts = {r['columnar']['prompt_sha256']: r['columnar']['tokens_sha256'] for r in tokens}
                with runtime:
                    state['model_loaded'] = True
                    until = time.monotonic() + 5
                    while not rss['samples'] and not rss['error'] and time.monotonic() < until:
                        time.sleep(.05)
                    observe(FREEZE, OUTPUT, state, runtime, rss, cfg)
                state['status'] = 'completed'
            except BaseException as error:
                state.update(status='blocked_or_failed', failure=type(error).__name__ + ': ' + str(error))
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise
            finally:
                if runtime:
                    runtime.__exit__()
                    state.update(generation_attempts=runtime.generation_attempts, generation_completed=runtime.generation_completed,
                        candidate_bytes_received=runtime.candidate_bytes_received,
                        inference_performed=runtime.generation_completed > 0 or runtime.candidate_bytes_received > 0)
                done.set()
                if monitor:
                    monitor.join(timeout=6)
                state['process_tree_rss'] = rss
                try:
                    h.d.resource_guard(rss, cfg)
                    verify(FREEZE)
                except Exception as error:
                    state.update(status='blocked_or_failed', failure=str(error))
                require(state.get('generation_attempts', 0) <= 126, 'Request cap exceeded')
                dump(OUTPUT / 'run.json', state)
                try:
                    dump(OUTPUT / 'score.json', score(FREEZE, state))
                except Exception as error:
                    state.update(status='blocked_or_failed', scoring_failure=str(error))
                    dump(OUTPUT / 'run.json', state)
                finally:
                    dump(OUTPUT / 'checksums.json', a.v.inventory(OUTPUT))
        return state


def replay(folder, output):
    verify(folder)
    require(read(output / 'checksums.json') == a.v.inventory(output), 'Changed run bytes')
    state = read(output / 'run.json')
    require(state['version'] == VERSION and state['registration_sha256'] == sha(REGISTRATION) and
            state['executions'] == 0 and not state['integration_authorized'] and not state['holdout_accessed'], 'Run identity/authority mismatch')
    require([{k: r[k] for k in ['id', 'experiment', 'condition', 'case_id']} for r in state['rows']] ==
            read(folder / 'schedule.json'), 'Run schedule mismatch')
    count = 0
    for row in state['rows']:
        if row['raw_base64'] is None:
            continue
        raw = base64.b64decode(row['raw_base64'], validate=True)
        require(d.m.digest(raw) == row['raw_sha256'] and
                raw == (output / 'requests' / row['id'] / 'proposal.txt').read_bytes(), 'Changed original response bytes')
        result = preview(folder, row['id'], raw, row['packet_id'])
        require(result == row.get('rust_preview'), 'Original-byte Rust preview drift')
        count += 1
    require(read(output / 'score.json') == score(folder, state), 'Independent score drift')
    return dict(verified=True, raw_previews=count, executions=0, inference_performed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['unpack', 'register', 'verify', 'replay', 'run'])
    parser.add_argument('--allow-inference', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Operator cancelled'))
    if args.command == 'unpack':
        unpack(FREEZE)
    elif args.command == 'register':
        register(FREEZE)
    elif args.command == 'verify':
        verify(FREEZE)
    elif args.command == 'replay':
        print(json.dumps(replay(FREEZE, OUTPUT)))
    else:
        state = run(args.allow_inference)
        raise SystemExit(0 if state['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()
