"""Verify published admission evidence without project imports or inference."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RELEASE = ROOT / 'docs/ask-alpha-preview-v1-observable-r2'


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = read(HERE / 'checksums.json')
    assert {str(p.relative_to(HERE)): digest(p) for p in HERE.rglob('*')
            if p.is_file() and p.name != 'checksums.json'} == checks
    logs = read(HERE / 'validation-log-files.json')
    assert digest(HERE / 'validation-logs.tar.gz') == logs['archive_sha256']
    with tarfile.open(HERE / 'validation-logs.tar.gz') as archive:
        published = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                     for m in archive if m.isfile()}
    assert published == {name: row['published_sha256'] for name, row in logs['entries'].items()}
    report = read(HERE / 'assessment.json')
    assert digest(RELEASE / 'registration.json') == report['registration_sha256']
    assert digest(RELEASE / 'freeze.tar.gz') == report['archive_sha256']
    registration = read(RELEASE / 'registration.json')
    with tarfile.open(RELEASE / 'freeze.tar.gz') as archive:
        files = {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}
    assert {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()
            if name != 'checksums.json'} == json.loads(files['checksums.json'])
    frozen = json.loads(files['freeze.json'])
    assert frozen['source_commit'] == registration['source_commit'] == report['registered_source_commit']
    assert all(digest(ROOT / name) == expected for name, expected in frozen['inputs'].items())
    host = read(HERE / 'host-before-invocation.json')
    gates = frozen['runtime_config']['host_gates']
    assert host['blockers'] == [dict(metric='swap_used_mib', observed=host['swap_used_mib'],
                                    threshold=gates['swap_used_mib_max'], reason='host_contention_or_resources')]
    assert host['swap_used_mib'] == 2448.94 > gates['swap_used_mib_max'] == 1024
    assert report['status'] == 'blocked_before_invocation'
    assert report['run_invocations'] == 0 and report['registration_consumed'] is False
    assert report['inference_performed'] is False and report['executions'] == 0
    assert report['decision'] == 'INCONCLUSIVE_REVISE'
    schedule = json.loads(files['schedule.json'])
    rows = report['rows']
    assert [dict((key, row[key]) for key in request) for row, request in zip(rows, schedule)] == schedule
    assert len(rows) == len(schedule) == 64
    assert Counter(row['kind'] for row in rows) == dict(native_control=2, repeat=2, semantic=60)
    assert all(row['outcome'] == 'unattempted' and row['attempted'] is False for row in rows)
    assert all(row['raw_response'] is None and row['five_field_agreement'] is None
               and row['wrong_but_executable'] is None and row['latency_ms'] is None for row in rows)
    refs = json.loads(files['operator/references.json'])['cases']
    assert len(refs) == 60
    assert Counter(row['language'] for row in refs) == dict(nb=30, en=30)
    assert Counter((row['expected_status'], row['semantically_determinate']) for row in refs) == {
        ('candidate', True): 29, ('unsupported', True): 8,
        ('needs_clarification', True): 5, ('needs_clarification', False): 18}
    minimum = [row['id'] for row in refs if row['expected_plan']
               and row['expected_plan']['start'] == 'http://www.wikidata.org/entity/Q279724'
               and row['expected_plan']['predicate'] in ['http://www.wikidata.org/prop/direct/P856',
                                                        'http://www.wikidata.org/prop/direct/P1448']
               and row['expected_plan']['direction'] == 'forward']
    assert report['minimum_alpha_scope']['ids'] == minimum and len(minimum) == 8
    assert report['minimum_alpha_scope']['result'] == 'not_established_host_admission_failed'
    assert all(value is None for value in report['runtime'].values())
    assert report['native_runtime_counters'] == dict(generation_attempts=None, generation_completed=None,
                                                    candidate_bytes_received=None)
    preservation = read(HERE / 'preservation.json')
    assert preservation['all_baseline_bytes_unchanged'] is True
    assert preservation['historical_attempt_metadata_unchanged'] is True
    assert set(preservation['successor_execution_paths_absent']) == {
        'attempt.json', 'stages.jsonl', 'diagnostics.json', 'run'}
    assert read(HERE / 'validation.json')['pipeline']['status'] == 'passed'
    print('PASS: published checksums, immutable sources, host blocker, 64 unattempted identities, null outcomes and preservation receipts')


if __name__ == '__main__':
    main()
