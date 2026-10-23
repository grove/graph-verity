"""Observable successor of the consumed Ask Alpha trial. Preview only, zero retries."""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
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
import traceback

import ask_alpha_trial as original

b, a, e, h, n = original.b, original.a, original.e, original.h, original.n
require, inventory = original.require, original.inventory
ROOT = original.ROOT
VERSION = 'ask-alpha-preview-v1-observable-r2'
RELEASE = ROOT / 'docs' / VERSION
FREEZE = ROOT / 'artifacts' / VERSION / 'freeze'
OUTPUT = FREEZE.parent / 'run'
LEDGER = FREEZE.parent / 'attempt.json'
JOURNAL = FREEZE.parent / 'stages.jsonl'
DIAGNOSTICS = FREEZE.parent / 'diagnostics.json'
REG = RELEASE / 'registration.json'
ARCHIVE = RELEASE / 'freeze.tar.gz'
COMMAND = ['.venv/bin/python', 'tools/ask_alpha_trial_observable_r2.py', 'run', '--allow-inference']


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_write(path, value):
    # Atomic replacement preserves the last complete receipt if writing is interrupted.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def exception_record(error):
    return dict(exception_class=type(error).__qualname__, exception_module=type(error).__module__,
                message=str(error), traceback=''.join(traceback.format_exception(type(error), error, error.__traceback__)))


class Stages:
    def __init__(self, stream):
        self.stream = stream
        self.started = time.monotonic()
        self.last_entered = self.last_completed = None
        self.events = 0
        self.secondary_errors = []

    def record(self, stage, status, identity=None, error=None):
        require(self.events < 512, 'Stage event bound exceeded')
        if status == 'entered':
            self.last_entered = stage
        elif status == 'completed':
            self.last_completed = stage
        row = dict(stage=stage, status=status, utc=datetime.now(timezone.utc).isoformat(),
                   elapsed_seconds=time.monotonic()-self.started, identity=identity,
                   failure_type=type(error).__qualname__ if error is not None else None)
        self.stream.write(json.dumps(row, separators=(',', ':'))+'\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.events += 1

    @contextmanager
    def stage(self, stage, identity=None):
        self.record(stage, 'entered', identity)
        try:
            yield
        except BaseException as error:
            try:
                self.record(stage, 'failed', identity, error)
            except BaseException as logging_error:
                self.secondary_errors.append(exception_record(logging_error))
            raise
        else:
            self.record(stage, 'completed', identity)


class Runtime(h.Runtime):
    def post(self, endpoint, body, name):
        if endpoint != 'completion':
            return super().post(endpoint, body, name)
        stage = 'first_request_dispatch' if not self.dispatched else 'request_dispatch'
        with self.stages.stage(stage, dict(request_id=name.parent.name)):
            self.dispatched.append(name.parent.name)
            return super().post(endpoint, body, name)

    def __exit__(self, *args):
        # The inherited startup handler calls __exit__ while its original error is active.
        active = sys.exc_info()[1]
        try:
            return super().__exit__(*args)
        except BaseException as error:
            if active is None:
                raise
            self.stages.secondary_errors.append(exception_record(error))


def verify():
    reg = b.read(REG)
    require(reg['version'] == VERSION and reg['command'] == COMMAND
            and reg['output'] == str(OUTPUT.relative_to(ROOT)) and reg['ledger'] == str(LEDGER.relative_to(ROOT))
            and reg['observability'] == dict(journal=str(JOURNAL.relative_to(ROOT)), diagnostics=str(DIAGNOSTICS.relative_to(ROOT)))
            and reg['completion_requests'] == 64 and reg['retries'] == 0 and reg['executions'] == 0
            and reg['inference_authorized'] is False and reg['decision'] == 'INCONCLUSIVE_REVISE', 'Changed authority boundaries')
    require(b.sha(ARCHIVE) == reg['archive_sha256'] and b.sha(FREEZE/'checksums.json') == reg['checksums_sha256'], 'Changed freeze')
    require(inventory(FREEZE) == b.read(FREEZE/'checksums.json'), 'Changed frozen payload')
    frozen = b.read(FREEZE/'freeze.json')
    require(frozen['version'] == VERSION and frozen['source_commit'] == reg['source_commit'], 'Changed freeze identity')
    for name, digest in frozen['inputs'].items():
        require(b.sha(ROOT/name) == digest, 'Changed registered source: '+name)
    require(b.sha(ROOT/'target/debug/verity') == frozen['binary_sha256'], 'Changed Rust binary')
    require(len(b.read(FREEZE/'schedule.json')) == 64, 'Changed schedule')
    return frozen


def unpack():
    require(not FREEZE.exists(), 'Fresh extraction destination required')
    require(b.sha(ARCHIVE) == b.read(REG)['archive_sha256'], 'Archive drift')
    FREEZE.mkdir(parents=True)
    with original.tarfile.open(ARCHIVE) as archive:
        archive.extractall(FREEZE, filter='data')


def run(allow_inference=False):
    require(allow_inference, 'Separate owner authorization and --allow-inference required')
    require(not os.environ.get('CI') and not os.environ.get('GITHUB_ACTIONS'), 'Inference forbidden in CI')
    require(not OUTPUT.exists() and not LEDGER.exists() and not JOURNAL.exists() and not DIAGNOSTICS.exists(),
            'Consumed registration; zero retries')
    # The exclusive journal is also an invocation claim: even verification/lock failure cannot be retried.
    with JOURNAL.open('x') as stream:
        os.chmod(JOURNAL, 0o600)
        sync_directory(JOURNAL.parent)
        stages = Stages(stream)
        state = dict(origin='retained_local_model', conditions=['neighborhood_v2_definitions'], rows=[], controls=[],
                     executions=0, inference_performed=None, model_startup_confirmed=False,
                     generation_attempts=None, generation_completed=None, candidate_bytes_received=None,
                     decision='INCONCLUSIVE_REVISE', status='blocked_or_failed', evidence_finalization='not_started')
        runtime, monitor, adapter, lock = None, None, None, None
        primary = None
        dispatched, schedule = [], None
        done, rss = threading.Event(), dict(samples=0, peak_kib=0, error=None)

        def snapshot():
            if runtime is not None:
                for field in ['generation_attempts', 'generation_completed', 'candidate_bytes_received']:
                    state[field] = getattr(runtime, field, None)
                attempts = state['generation_attempts']
                state['inference_performed'] = attempts > 0 if attempts is not None else None
            state.update(last_entered_stage=stages.last_entered, last_completed_stage=stages.last_completed,
                         remaining_scheduled_requests=[r['id'] for r in schedule if r['id'] not in dispatched] if schedule is not None else None,
                         process_tree_rss=rss, secondary_errors=stages.secondary_errors)
            durable_write(DIAGNOSTICS, state)
            if OUTPUT.is_dir():
                durable_write(OUTPUT/'run.json', state)

        def cleanup(stage, operation):
            nonlocal primary
            try:
                with stages.stage(stage):
                    operation()
            except BaseException as error:
                if primary is None:
                    primary = error
                    state.update(status='blocked_or_failed', exception=exception_record(error),
                                 failure=type(error).__name__+': '+str(error),
                                 failure_last_entered_stage=stages.last_entered,
                                 failure_last_completed_stage=stages.last_completed)
                else:
                    stages.secondary_errors.append(exception_record(error))

        try:
            with stages.stage('registration_verification', dict(registration=VERSION)):
                frozen = verify()
                raw = subprocess.check_output(['git', 'show', 'HEAD:'+str(REG.relative_to(ROOT))], cwd=ROOT)
                require(raw == REG.read_bytes(), 'Commit the reviewed registration first')
                schedule = b.read(FREEZE/'schedule.json')
                state['rows'] = [dict(condition='neighborhood_v2_definitions', id=r['id'], outcome='unattempted')
                                 for r in schedule if r['kind'] == 'semantic']
            with stages.stage('exclusive_lock_acquisition'):
                lock = (ROOT/'artifacts/native-one-hop.lock').open('a')
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with stages.stage('attempt_ledger_creation', dict(registration_sha256=b.sha(REG))):
                require(not OUTPUT.exists() and not LEDGER.exists(), 'Consumed registration; zero retries')
                with LEDGER.open('x') as ledger:
                    json.dump(dict(registration_sha256=b.sha(REG), consumed_before_model_load=True), ledger)
                    ledger.flush()
                    os.fsync(ledger.fileno())
                sync_directory(LEDGER.parent)
            with stages.stage('output_directory_initialization'):
                OUTPUT.mkdir(parents=True)
                sync_directory(OUTPUT.parent)
                snapshot()
            cfg = frozen['runtime_config']
            with n.native_config(cfg):
                with stages.stage('asset_verification', dict(model='qwen35')):
                    evidence = a.assets(OUTPUT / 'assets.json')
                    require({k: evidence[k] for k in frozen['runtime_identity']} == frozen['runtime_identity'], 'Native asset drift')
                with stages.stage('tokenizer_recount'):
                    code = a.bounded([evidence['candidates']['qwen35']['preparation_receipt']['commands'][2][0],
                        ROOT / 'tools/native_one_hop_v1h_tokens.py', FREEZE / 'token-job.json', OUTPUT / 'token-counts.json'], OUTPUT, 'tokenizer', 120)
                    require(code == 0 and b.read(OUTPUT / 'token-counts.json') == b.read(FREEZE / 'token-counts.json'), 'Pre-load tokenizer drift')
                    tokens = b.read(FREEZE / 'token-counts.json')['models']['qwen35']['rows']
                with stages.stage('grammar_controls'):
                    a.grammar_controls(b.read(FREEZE / 'contexts/alpha-01.json'), OUTPUT / 'grammar-controls')
                with stages.stage('host_admission'):
                    host = a.preflight(OUTPUT / 'host.json')
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(host['captured_at'])).total_seconds()
                    require(not host['blockers'] and 0 <= age <= cfg['host_max_age_seconds'], 'Fresh operator host gate blocked')
                with stages.stage('resource_monitor_initialization'):
                    monitor = threading.Thread(target=a.sample_rss, args=(OUTPUT, done, rss), daemon=True)
                    monitor.start()
                with stages.stage('runtime_initialization', dict(model='qwen35')):
                    adapter = b.bundle()
                    runtime = Runtime(cfg, a.g.ASSETS, 'qwen35', OUTPUT)
                    runtime.stages, runtime.dispatched = stages, dispatched
                    runtime.reference_python = evidence['candidates']['qwen35']['preparation_receipt']['commands'][2][0]
                    runtime.allowed_prompts = {r['columnar']['prompt_sha256']: r['columnar']['tokens_sha256'] for r in tokens}
                rows = {r['id']: r for r in state['rows']}
                packet_rows = e.packets()
                with stages.stage('model_startup', dict(model='qwen35')):
                    runtime.__enter__()
                    state['model_startup_confirmed'] = True
                    state['startup_ms'] = runtime.startup_ms
                until = time.monotonic() + 5
                while not rss['samples'] and not rss['error'] and time.monotonic() < until:
                    time.sleep(.05)
                for i, request in enumerate(b.read(FREEZE / 'schedule.json')):
                    key = request['id']
                    with stages.stage('request', dict(index=i, request_id=key)):
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
                            active = sys.exc_info()[1]
                            try:
                                row['attempted'] = runtime.generation_attempts > before_attempts
                                row['latency_ms'] = (time.monotonic() - started) * 1000
                                if (dest / 'proposal.txt').exists():
                                    row['raw_sha256'] = b.sha(dest / 'proposal.txt')
                                durable_write(OUTPUT / 'run.json', state)
                            except BaseException as receipt_error:
                                if active is None:
                                    raise
                                stages.secondary_errors.append(exception_record(receipt_error))
            state['status'] = 'completed'
        except BaseException as error:
            primary = error
            state.update(status='blocked_or_failed', exception=exception_record(error),
                         failure=type(error).__name__+': '+str(error))
            # Preserve the failure stage before shutdown transitions move the cursor.
            state['failure_last_entered_stage'] = stages.last_entered
            state['failure_last_completed_stage'] = stages.last_completed
        finally:
            cleanup('interruption_diagnostics', snapshot)
            if runtime is not None:
                cleanup('runtime_shutdown', runtime.__exit__)
            done.set()
            if monitor is not None and monitor.ident is not None:
                cleanup('resource_monitor_shutdown', lambda: monitor.join(timeout=6))
            if adapter is not None:
                cleanup('adapter_shutdown', adapter.close)

            def finalize():
                state['evidence_finalization'] = 'entered'
                snapshot()
                if OUTPUT.is_dir():
                    report = e.score(state)
                    durable_write(OUTPUT/'score.json', report)
                    (OUTPUT/'failures.md').write_text(e.markdown(report))
                state['evidence_finalization'] = 'completed'

            cleanup('evidence_finalization', finalize)
            if state['evidence_finalization'] != 'completed':
                state['evidence_finalization'] = 'failed'
            if lock is not None:
                cleanup('lock_release', lock.close)
            cleanup('final_diagnostics', snapshot)
            if OUTPUT.is_dir():
                cleanup('evidence_checksums', lambda: durable_write(OUTPUT/'checksums.json', inventory(OUTPUT)))
            if state.get('failure_last_entered_stage') == 'evidence_checksums':
                cleanup('checksum_failure_diagnostics', snapshot)
        if primary is not None:
            raise primary.with_traceback(primary.__traceback__)
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['unpack', 'verify', 'run'])
    parser.add_argument('--allow-inference', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Operator cancelled'))
    if args.command == 'unpack':
        unpack()
    elif args.command == 'verify':
        verify()
    else:
        run(args.allow_inference)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
