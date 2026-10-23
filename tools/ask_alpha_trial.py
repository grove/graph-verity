"""Append-only, operator-only local Ask preview trial. Never executes generated RDF."""
import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import threading
import time

import ask_alpha_evaluation as e
import native_one_hop_v1h as h
import predicate_diagnostics_native as n

b, a = e.b, n.a
ROOT = b.ROOT
RELEASE = ROOT / 'docs/ask-alpha-v1'
FREEZE = ROOT / 'artifacts/ask-alpha-v1/freeze'
OUTPUT = ROOT / 'artifacts/ask-alpha-v1/run'
LEDGER = ROOT / 'artifacts/ask-alpha-v1/attempt.json'
REG = RELEASE / 'registration.json'
ARCHIVE = RELEASE / 'freeze.tar.gz'
COMMAND = ['.venv/bin/python', 'tools/ask_alpha_trial.py', 'run', '--allow-inference']


def require(value, message):
    if not value:
        raise ValueError(message)


def inventory(folder):
    return {str(p.relative_to(folder)): b.sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p != folder / 'checksums.json'}


def prepare():
    e.verify()
    require(not FREEZE.exists() and not REG.exists() and not ARCHIVE.exists(), 'New freeze/registration only')
    FREEZE.mkdir(parents=True)
    prior = b.read(ROOT / 'experiments/predicate-diagnostics-v1-execution-v1/registration.json')
    cfg = dict(prior['runtime_config'], variants=['qwen35'])
    inputs = {str(p.relative_to(ROOT)): b.sha(p) for p in [
        *sorted((ROOT / 'tools').glob('*.py')), *sorted((ROOT / 'tools').glob('*.mjs')),
        *sorted((ROOT / 'crates').rglob('*.rs')), *sorted((ROOT / 'crates').rglob('Cargo.toml')),
        *sorted((ROOT / 'configs').glob('native-one-hop-*')), ROOT / 'configs/one-hop-trial-v1.json',
        ROOT / 'configs/grounded-models-v1.json', ROOT / 'Cargo.lock', ROOT / 'Cargo.toml',
        ROOT / 'rust-toolchain.toml', *sorted(b.DEST.iterdir()),
        *[ROOT / p for p in b.read(b.DEST / 'manifest.json')['input_sha256']],
        ROOT / 'experiments/predicate-diagnostics-v1-execution-v1/registration.json'] if p.is_file()}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    n.committed(inputs, revision)
    packet_rows = e.packets()
    questions = b.read(b.DEST / 'questions.json')['cases']
    # Round robin categories prevents a late timeout from hiding every reverse/control case.
    refs = {r['id']: r for r in b.read(b.DEST / 'references.json')['cases']}
    groups = {}
    for q in questions:
        groups.setdefault(refs[q['id']]['category'], []).append(q['id'])
    order = []
    while any(groups.values()):
        for group in groups.values():
            if group:
                order.append(group.pop(0))
    # Scheduling reads category metadata only; the context renderer never sees reference plans.
    control = dict(snapshot_id=b.read(b.DEST / 'source.json')['snapshot_id'], graphs=[], entities=[], predicates=[],
        question='Output exactly {"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control","forbidden":true}.')
    contexts = {'sampling-unconstrained': control, 'sampling-constrained': control}
    contexts.update({f'repeat-{i}': packet_rows['alpha-01']['context'] for i in range(2)})
    contexts.update({key: packet_rows[key]['context'] for key in order})
    schedule, observations = [], []
    with n.native_config(cfg):
        for key, context in contexts.items():
            control_row = key.startswith('sampling-')
            repeat_row = key.startswith('repeat-')
            prompt = (ROOT / cfg['control_prompt_file' if control_row else 'prompt_file']).read_text()
            messages = [dict(role='system', content=prompt), dict(role='user', content=a.g.safe_user(context))]
            b.write(FREEZE / 'contexts' / (key + '.json'), context)
            b.write(FREEZE / 'messages' / (key + '.json'), messages)
            grammar = FREEZE / 'grammars' / (key + '.gbnf')
            grammar.parent.mkdir(exist_ok=True)
            grammar.write_text(a.grammar(context))
            schedule.append(dict(id=key, kind='native_control' if control_row else 'repeat' if repeat_row else 'semantic',
                                 constrained=key != 'sampling-unconstrained'))
            observations.append(dict(condition='neighborhood_v2_definitions', name=key, case_id=key,
                kind='native_control' if control_row else 'repeat' if repeat_row else 'semantic',
                original=dict(messages=messages), columnar=dict(messages=messages)))
    pins = prior['runtime_identity']['candidates']['qwen35']['upstream']['files']
    spec = dict(path=str(a.g.ASSETS / 'upstream/qwen35'),
                file_sha256={name: record['sha256'] for name, record in pins.items()
                             if name in ['tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja', 'merges.txt', 'vocab.json', 'config.json']},
                historical_parities=[])
    b.write(FREEZE / 'token-job.json', dict(models=dict(qwen35=spec), observations=observations))
    python = prior['runtime_identity']['candidates']['qwen35']['preparation_receipt']['commands'][2][0]
    # Tokenizer only: no weights, model class, native server, generation or asset acquisition.
    code = a.bounded([python, ROOT / 'tools/native_one_hop_v1h_tokens.py', FREEZE / 'token-job.json',
                      FREEZE / 'token-counts.json'], FREEZE, 'tokenizer', 120)
    require(code == 0, 'Model-free tokenizer failed; retain preparation logs')
    tokens = b.read(FREEZE / 'token-counts.json')['models']['qwen35']['rows']
    require(all(r['columnar']['fits'] and r['columnar']['total_required'] < 16384 for r in tokens), 'Prompt budget overflow')
    b.write(FREEZE / 'schedule.json', schedule)
    b.write(FREEZE / 'operator/references.json', b.read(b.DEST / 'references.json'))
    b.write(FREEZE / 'freeze.json', dict(version='ask-alpha-preview-v1', inputs=inputs,
        source_commit=revision,
        runtime_config=cfg, runtime_identity=prior['runtime_identity'], binary_sha256=b.sha(ROOT / 'target/debug/verity')))
    b.write(FREEZE / 'checksums.json', inventory(FREEZE))
    RELEASE.mkdir(exist_ok=True)
    with ARCHIVE.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for path in sorted(FREEZE.rglob('*')):
                    if path.is_file():
                        archive.add(path, arcname=str(path.relative_to(FREEZE)), recursive=False)
    b.write(REG, dict(version='ask-alpha-preview-v1', archive_sha256=b.sha(ARCHIVE),
        checksums_sha256=b.sha(FREEZE / 'checksums.json'), source_commit=b.read(FREEZE / 'freeze.json')['source_commit'],
        command=COMMAND, completion_requests=64, semantic_cases=60, model='qwen35', retries=0,
        output=str(OUTPUT.relative_to(ROOT)), ledger=str(LEDGER.relative_to(ROOT)),
        inference_authorized=False, inference_performed=False, executions=0, decision='INCONCLUSIVE_REVISE',
        human_comprehension='unmeasured', issue75_integration='disabled', issue83='keep_open'))
    return verify()


def unpack():
    require(not FREEZE.exists(), 'Fresh extraction destination required')
    require(b.sha(ARCHIVE) == b.read(REG)['archive_sha256'], 'Archive drift')
    FREEZE.mkdir(parents=True)
    with tarfile.open(ARCHIVE) as archive:
        archive.extractall(FREEZE, filter='data')


def verify():
    reg = b.read(REG)
    require(reg['command'] == COMMAND and reg['completion_requests'] == 64 and reg['retries'] == 0
            and reg['executions'] == 0 and reg['inference_authorized'] is False
            and reg['decision'] == 'INCONCLUSIVE_REVISE', 'Changed authority boundaries')
    require(b.sha(ARCHIVE) == reg['archive_sha256'] and b.sha(FREEZE / 'checksums.json') == reg['checksums_sha256'], 'Changed freeze')
    require(inventory(FREEZE) == b.read(FREEZE / 'checksums.json'), 'Changed frozen payload')
    frozen = b.read(FREEZE / 'freeze.json')
    for name, digest in frozen['inputs'].items():
        require(b.sha(ROOT / name) == digest, 'Changed registered source: ' + name)
    require(b.sha(ROOT / 'target/debug/verity') == frozen['binary_sha256'], 'Changed Rust binary')
    require(len(b.read(FREEZE / 'schedule.json')) == 64, 'Changed schedule')
    return frozen


def run(allow_inference=False):
    require(allow_inference, 'Separate owner authorization and --allow-inference required')
    require(not os.environ.get('CI') and not os.environ.get('GITHUB_ACTIONS'), 'Inference forbidden in CI')
    frozen = verify()
    raw = subprocess.check_output(['git', 'show', 'HEAD:' + str(REG.relative_to(ROOT))], cwd=ROOT)
    require(raw == REG.read_bytes(), 'Commit the reviewed registration first')
    with (ROOT / 'artifacts/native-one-hop.lock').open('a') as lock, n.native_config(frozen['runtime_config']):
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not OUTPUT.exists() and not LEDGER.exists(), 'Consumed registration; zero retries')
        with LEDGER.open('x') as stream:
            json.dump(dict(registration_sha256=b.sha(REG), consumed_before_model_load=True), stream)
        OUTPUT.mkdir(parents=True)
        cfg = frozen['runtime_config']
        state = dict(origin='retained_local_model', conditions=['neighborhood_v2_definitions'],
            rows=[dict(condition='neighborhood_v2_definitions', id=r['id'], outcome='unattempted')
                  for r in b.read(FREEZE / 'schedule.json') if r['kind'] == 'semantic'],
            controls=[], executions=0, inference_performed=False, decision='INCONCLUSIVE_REVISE')
        runtime, monitor, adapter = None, None, None
        done, rss = threading.Event(), dict(samples=0, peak_kib=0, error=None)
        try:
            evidence = a.assets(OUTPUT / 'assets.json')
            require({k: evidence[k] for k in frozen['runtime_identity']} == frozen['runtime_identity'], 'Native asset drift')
            code = a.bounded([evidence['candidates']['qwen35']['preparation_receipt']['commands'][2][0],
                ROOT / 'tools/native_one_hop_v1h_tokens.py', FREEZE / 'token-job.json', OUTPUT / 'token-counts.json'], OUTPUT, 'tokenizer', 120)
            require(code == 0 and b.read(OUTPUT / 'token-counts.json') == b.read(FREEZE / 'token-counts.json'), 'Pre-load tokenizer drift')
            tokens = b.read(FREEZE / 'token-counts.json')['models']['qwen35']['rows']
            a.grammar_controls(b.read(FREEZE / 'contexts/alpha-01.json'), OUTPUT / 'grammar-controls')
            host = a.preflight(OUTPUT / 'host.json')
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(host['captured_at'])).total_seconds()
            require(not host['blockers'] and 0 <= age <= cfg['host_max_age_seconds'], 'Fresh operator host gate blocked')
            monitor = threading.Thread(target=a.sample_rss, args=(OUTPUT, done, rss), daemon=True)
            monitor.start()
            adapter = b.bundle()
            runtime = h.Runtime(cfg, a.g.ASSETS, 'qwen35', OUTPUT)
            runtime.reference_python = evidence['candidates']['qwen35']['preparation_receipt']['commands'][2][0]
            runtime.allowed_prompts = {r['columnar']['prompt_sha256']: r['columnar']['tokens_sha256'] for r in tokens}
            rows = {r['id']: r for r in state['rows']}
            packet_rows = e.packets()
            with runtime:
                state['startup_ms'] = runtime.startup_ms
                until = time.monotonic() + 5
                while not rss['samples'] and not rss['error'] and time.monotonic() < until:
                    time.sleep(.05)
                for i, request in enumerate(b.read(FREEZE / 'schedule.json')):
                    key = request['id']
                    dest = OUTPUT / 'requests' / key
                    dest.mkdir(parents=True)
                    row = rows.get(key, dict(id=key, outcome='unattempted'))
                    if request['kind'] != 'semantic':
                        state['controls'].append(row)
                    started = time.monotonic()
                    before_attempts = runtime.generation_attempts
                    try:
                        verify()
                        h.d.resource_guard(rss, cfg)
                        require(runtime.generation_attempts == i and i < 64, 'Request cap/order violated')
                        context = b.read(FREEZE / 'contexts' / (key + '.json'))
                        if request['kind'] == 'semantic':
                            packet = packet_rows[key]['packet']
                            require(adapter.packet(context['question'], context['language'], packet) == packet, 'Source packet drift')
                            trusted = e.rust_preview(adapter, packet_rows[key]['selection'],
                                '{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"Trusted source preflight"}')
                            require(trusted['accepted'], 'Trusted Rust source/catalog preflight failed')
                            b.write(dest / 'trusted-preflight.json', trusted)
                        row['outcome'] = 'failed'
                        runtime.generate(context, dest, constrained=request['constrained'],
                                         system=b.read(FREEZE / 'messages' / (key + '.json'))[0]['content'])
                        require(b.read(dest / 'messages.json') == b.read(FREEZE / 'messages' / (key + '.json')), 'Message drift')
                        raw = (dest / 'proposal.txt').read_text()
                        grammar_ok = a.grammar_check(raw, context, dest)
                        require(grammar_ok == request['constrained'], 'Native grammar control/integrity failed')
                        if key == 'repeat-1':
                            for name in ['prompt.txt', 'completion-request.json']:
                                require((OUTPUT / 'requests/repeat-0' / name).read_bytes() == (dest / name).read_bytes(), 'Repeat prompt/request drift')
                            from native_one_hop_semantics import repeatability
                            state['repeatability'] = repeatability([(OUTPUT / 'requests/repeat-0/proposal.txt').read_bytes(), (dest / 'proposal.txt').read_bytes()])
                        if request['kind'] == 'semantic':
                            row['rust'] = e.rust_preview(adapter, packet_rows[key]['selection'], raw)
                            h.d.validator_guard(row['rust'])
                            row['raw_draft'] = raw
                        h.d.resource_guard(rss, cfg)
                        verify()
                        row['outcome'] = 'completed'
                    except BaseException as error:
                        row.update(outcome='timed_out' if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else 'failed',
                                   failure=type(error).__name__ + ': ' + str(error))
                        raise
                    finally:
                        row['attempted'] = runtime.generation_attempts > before_attempts
                        row['latency_ms'] = (time.monotonic() - started) * 1000
                        if (dest / 'proposal.txt').exists():
                            row['raw_sha256'] = b.sha(dest / 'proposal.txt')
                        b.write(OUTPUT / 'run.json', state)
            state['status'] = 'completed'
        except BaseException as error:
            state.update(status='blocked_or_failed', failure=type(error).__name__ + ': ' + str(error))
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
        finally:
            if runtime:
                runtime.__exit__()
                state.update(generation_attempts=runtime.generation_attempts, generation_completed=runtime.generation_completed,
                    inference_performed=runtime.generation_attempts > 0, candidate_bytes_received=runtime.candidate_bytes_received)
            done.set()
            if monitor:
                monitor.join(timeout=6)
            if adapter:
                adapter.close()
            state['process_tree_rss'] = rss
            b.write(OUTPUT / 'run.json', state)
            try:
                report = e.score(state)
                b.write(OUTPUT / 'score.json', report)
                (OUTPUT / 'failures.md').write_text(e.markdown(report))
            except Exception as error:
                state.update(status='blocked_or_failed', scoring_failure=str(error))
                b.write(OUTPUT / 'run.json', state)
            finally:
                b.write(OUTPUT / 'checksums.json', inventory(OUTPUT))
        return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'unpack', 'verify', 'run'])
    p.add_argument('--allow-inference', action='store_true')
    args = p.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Operator cancelled'))
    if args.command == 'prepare':
        prepare()
    elif args.command == 'unpack':
        unpack()
    elif args.command == 'verify':
        verify()
    else:
        return 0 if run(args.allow_inference)['status'] == 'completed' else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
