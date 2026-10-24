"""Check retained native evidence using the standard library only."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(path.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def members(path):
    with tarfile.open(path) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}


def main():
    checks = read(HERE / 'checksums.json')
    assert {str(p.relative_to(HERE)): sha(p.read_bytes()) for p in HERE.rglob('*')
            if p.is_file() and p.name != 'checksums.json'} == checks
    logs = read(HERE / 'validation-log-files.json')
    assert sha((HERE / 'validation-logs.tar.gz').read_bytes()) == logs['archive_sha256']
    assert {name: sha(body) for name, body in members(HERE / 'validation-logs.tar.gz').items()} == {
        name: row['published_sha256'] for name, row in logs['entries'].items()}
    protocol = read(HERE / 'protocol.json')
    release = ROOT / 'docs/ask-alpha-preview-v1-observable-r2'
    assert sha((release / 'registration.json').read_bytes()) == protocol['registration_sha256']
    assert sha((release / 'freeze.tar.gz').read_bytes()) == protocol['archive_sha256']
    frozen_files = members(release / 'freeze.tar.gz')
    frozen = json.loads(frozen_files['freeze.json'])
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in frozen['inputs'].items())
    schedule = json.loads(frozen_files['schedule.json'])
    tokens = {r['name']: r['columnar'] for r in json.loads(frozen_files['token-counts.json'])['models']['qwen35']['rows']}
    raw = members(HERE / 'raw-evidence.tar.gz')
    index = read(HERE / 'raw-files.json')['files']
    assert set(raw) == set(index)
    assert all(sha(body) == index[name]['sha256'] and len(body) == index[name]['bytes'] for name, body in raw.items())
    ledger = json.loads(raw['attempt.json'])
    assert ledger['registration_sha256'] == protocol['registration_sha256']
    assert ledger['consumed_before_model_load'] is True
    run = json.loads(raw['run/run.json'])
    diagnostics = json.loads(raw['diagnostics.json'])
    assert run == diagnostics
    assert run['executions'] == 0 and run['decision'] == 'INCONCLUSIVE_REVISE'
    assert run['model_startup_confirmed'] is True
    assert run['inference_performed'] is True
    assert json.loads(raw['run/host.json'])['blockers'] == []
    assets = json.loads(raw['run/assets.json'])['candidates']['qwen35']['verified_retained_files']
    assert assets['qwen35-Q4_K_M.gguf']['sha256'] == protocol['model_sha256']
    assert assets['build/bin/llama-server']['sha256'] == protocol['native_server_sha256']
    server = json.loads(raw['run/server-command.json'])
    for flag, value in [('--threads', '4'), ('--threads-batch', '4'), ('--n-gpu-layers', '0'),
                        ('--parallel', '1'), ('--ctx-size', '16384')]:
        assert server[server.index(flag) + 1] == value
    assert '--offline' in server
    events = [json.loads(line) for line in raw['stages.jsonl'].splitlines()]
    assert len(events) <= 512
    dispatches = [e['identity']['request_id'] for e in events
                  if e['stage'] in ['first_request_dispatch', 'request_dispatch'] and e['status'] == 'entered']
    attempts = run['generation_attempts']
    assert 0 < attempts <= 64 and attempts == len(dispatches)
    assert dispatches == [r['id'] for r in schedule[:attempts]]
    assert 0 <= run['generation_completed'] <= attempts
    assert len(run['rows']) == 60 and len(run['controls']) == 4
    assert all(r['outcome'] == 'completed' for r in run['controls'])
    assert {r['id'] for r in run['rows']} == {r['id'] for r in schedule if r['kind'] == 'semantic'}
    assert run['process_tree_rss']['peak_kib'] <= 24 * 1024 * 1024
    assert run['process_tree_rss']['error'] is None
    manifest = json.loads(raw['run/checksums.json'])
    assert {n[4:]: sha(body) for n, body in raw.items() if n.startswith('run/') and n != 'run/checksums.json'} == manifest
    observations = {r['id']: r for r in run['controls'] + run['rows']}
    received = 0
    for request in schedule[:attempts]:
        key = request['id']
        prefix = 'run/requests/' + key + '/'
        assert sha(raw[prefix + 'prompt.txt']) == tokens[key]['prompt_sha256']
        body = json.loads(raw[prefix + 'completion-request.json'])
        assert body['prompt'] == tokens[key]['tokens']
        assert body['n_predict'] == 512 and body['temperature'] == 0 and body['seed'] == 7
        assert len(body['prompt']) + 512 < 16384
        if request['constrained']:
            assert body['grammar'].encode() == frozen_files['grammars/' + key + '.gbnf']
        else:
            assert 'grammar' not in body
        assert json.loads(raw[prefix + 'messages.json']) == json.loads(frozen_files['messages/' + key + '.json'])
        parity = json.loads(raw[prefix + 'parity.json'])
        assert parity['token_ids_equal'] and parity['prompt_bytes_equal']
        stream = raw[prefix + 'completion.http.sse']
        assert len(stream) <= 2 * 1024 * 1024
        pieces, terminal = [], False
        for line in stream.splitlines():
            if not line.startswith(b'data:'):
                continue
            try:
                event = json.loads(line[5:].strip())
            except ValueError:
                assert observations[key]['outcome'] != 'completed'
                break
            pieces.append(event.get('content', '').encode())
            if event.get('stop') is True:
                terminal = True
                break
        proposal = raw[prefix + 'proposal.txt']
        assert b''.join(pieces) == proposal
        received += len(proposal)
        if observations[key]['outcome'] == 'completed':
            assert terminal
    assert received == run['candidate_bytes_received']
    score = read(HERE / 'score.json')
    assert score == json.loads(raw['run/score.json'])
    arm = score['conditions']['neighborhood_v2_definitions']
    assessment = read(HERE / 'assessment.json')
    assert assessment['registered_summary'] == arm['summary']
    assert assessment['native']['attempted'] == run['generation_attempts']
    assert assessment['native']['completed'] == run['generation_completed']
    assert assessment['native']['candidate_bytes_received'] == received
    core = assessment['minimum_scope']
    assert core['ids'] == ['alpha-11', 'alpha-12', 'alpha-31', 'alpha-32', 'alpha-33',
                           'alpha-34', 'alpha-45', 'alpha-46']
    assert core['five_field_matches'] == sum(r['five_field_agreement'] is True
                                            for r in arm['rows'] if r['id'] in core['ids'])
    replay = read(HERE / 'replay.json')
    assert replay['registered_score_reproduced'] is True
    completed = {r['id'] for r in run['rows'] if r['outcome'] == 'completed'}
    assert {r['id'] for r in replay['rows'] if r['completed']} == completed
    assert all(r['matches_original_preview'] is True for r in replay['rows'] if r['completed'])
    assert {r['id'] for r in read(HERE / 'rationale-audit.json')['rows']} == completed
    assert read(HERE / 'preservation.json')['all_baseline_bytes_unchanged'] is True
    assert read(HERE / 'preservation.json')['native_evidence_unchanged_after_checks'] is True
    assert read(HERE / 'validation.json')['pipeline']['status'] == 'passed'
    print('PASS: raw bytes, registration, source pins, accounting, prompt/token parity, replay, scoring, audits and preservation')


if __name__ == '__main__':
    main()
