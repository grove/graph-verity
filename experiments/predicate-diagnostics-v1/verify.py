"""Reproduce registered model-free receipts, including compiler-only rejections."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import predicate_diagnostics as d


def main():
    registration = d.read(d.RELEASE / 'registration.json')
    archive = d.RELEASE / 'freeze.tar.gz'
    assert d.sha(archive) == registration['archive_sha256']
    with tempfile.TemporaryDirectory(prefix='predicate-replay-') as temp:
        folder = Path(temp)
        for name, raw in d.v.a.g.archive_files(archive).items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        d.verify_registration(folder)
        assert d.score(folder, {}) == d.read(d.RELEASE / 'unattempted-score.json')
        report = d.read(d.RELEASE / 'model-free-replay.json')
        refs = d.read(folder / 'expected.json')
        rejected = []
        for row in report['observations']:
            raw = row['raw_utf8'].encode()
            assert d.m.digest(raw) == row['raw_sha256']
            result = d.preview(folder, row['id'], raw, row['packet_id'])
            assert result == row['rust_preview']
            metric = d.measure(refs[row['id']], raw, result['returncode'] == 0)
            assert metric == row['measurement'] and metric['reference_agreement'] is True
            if result['returncode']:
                rejected.append(row['id'])
                ref = refs[row['id']]
                assert ref['kind'] == 'empty_path' and ref['fields']['direction'] == 'reverse'
                assert 'deterministic_preflight_block' in result['stderr']
        assert len(report['observations']) == 124 and report['accepted'] == 114
        assert len(rejected) == 10
        # Rust acceptance and explicit request fidelity must stay independently measurable.
        key = 'explicit-003'
        ref = refs[key]
        raw = json.dumps(dict(version='nl-ask-draft-v1', status='candidate', rationale='synthetic', **ref['fields'])).encode()
        assert d.measure(ref, raw, False)['reference_agreement'] is True
        changed = json.loads(raw)
        changed['direction'] = 'forward'
        assert d.measure(ref, json.dumps(changed).encode(), True)['reference_agreement'] is False
    print('Registered bytes, zero-outcome report and 124 Rust previews reproduced; 10 compiler-only rejections retained.')


if __name__ == '__main__':
    main()
