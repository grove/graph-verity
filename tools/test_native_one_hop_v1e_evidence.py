"""Immutable v1e source/raw-byte replay. Never access model assets or infer."""
import hashlib
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_one_hop as a
from native_one_hop_semantics import repeatability


class EvidenceTests(unittest.TestCase):
    def test_retained_v1e_evidence_and_rationale_coverage_replay_without_models(self):
        report = a.ROOT / 'reports/issue-83-native-one-hop-v1e'
        self.assertEqual(a.read(report / 'checksums.json'), a.v.inventory(report))
        manifest = a.read(report / 'evidence-files.json')
        archive = report / 'evidence.tar.gz'
        self.assertEqual(a.sha(archive), manifest['archive_sha256'])
        payload = a.g.archive_files(archive)
        self.assertEqual({n: hashlib.sha256(raw).hexdigest() for n,raw in payload.items()}, manifest['files'])
        prereg = a.read(report / 'preregistration.json')
        # Preregistration sealed in 8c66aa7 before inference; no Git ancestry requirement after squash.
        self.assertEqual(a.sha(report / 'preregistration.json'),
                         '6eb1eb6bf61d5153dabd99a71c978bda96612152ae2e8a42b0f08fd18f12c4bf')
        reviews = a.read(report / 'rationale-review.json')['responses']
        self.assertEqual(len(reviews), len({r['response'] for r in reviews}))
        reviews = {r['response']: r for r in reviews}
        with tempfile.TemporaryDirectory() as temp, patch.object(a, 'CONFIG', a.ROOT / 'configs/native-one-hop-v1e.json'):
            root = Path(temp)
            for name,raw in payload.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            for name in ['preregistration.json', 'failure-audit.json', 'native-environment.json', 'rationale-review.json']:
                self.assertEqual((root / name).read_bytes(), (report / name).read_bytes())
            self.assertEqual(a.sha(root / 'freeze/checksums.json'), prereg['freeze_sha256'])
            frozen = a.read(root / 'freeze/freeze.json')
            self.assertEqual(frozen, prereg['freeze_manifest'])
            self.assertEqual(a.read(root / 'freeze/checksums.json'), a.v.inventory(root / 'freeze'))
            for name,digest in frozen['input_sha256'].items():
                self.assertEqual(a.sha(root / 'source' / name), digest, name)
                if name == 'tools/native_one_hop.py':
                    original = subprocess.check_output(['git', 'show', 'f212b00d03ffe970885fcdbce0e01faeaf784a69:' + name], cwd=a.ROOT)
                    self.assertEqual(hashlib.sha256(original).hexdigest(), digest, name)
                else:
                    self.assertEqual(a.sha(a.ROOT / name), digest, name)
            covered = set()
            for key in frozen['config']['variants']:
                run = root / key
                state = a.read(run / 'run.json')
                self.assertEqual(a.read(run / 'checksums.json'), a.v.inventory(run))
                self.assertEqual(state['freeze_sha256'], prereg['freeze_sha256'])
                self.assertEqual(state['executions'], 0)
                self.assertEqual(state['independent_human_approvals'], 0)
                self.assertFalse(state['integration_authorized'])
                self.assertFalse(state['holdout_accessed'])
                repeats = sorted((run / 'controls').glob('repeat-*/proposal.txt'))
                expected = repeatability([p.read_bytes() for p in repeats])
                for field,value in expected.items():
                    if field != 'gate_passed':
                        self.assertEqual(state['repeatability'][field], value)
                for saved in run.rglob('rust.json'):
                    folder = saved.parent
                    with tempfile.TemporaryDirectory() as preview:
                        actual = a.preview_raw(a.read(folder / 'context.json'), folder / 'proposal.txt',
                                               Path(preview), a.read(folder / 'catalog.json'))
                    self.assertEqual(actual, a.read(saved))
                    if (folder / 'semantic.json').exists():
                        name = 'smoke-' + folder.name if folder.parent.name == 'smoke' else folder.name
                        cid = state['checks'][name]['case_id']
                        self.assertEqual(a.semantic_outcome(cid, folder / 'proposal.txt', actual), a.read(folder / 'semantic.json'))
                    stream = folder / 'completion.http.sse'
                    if stream.exists():
                        content = [json.loads(line[5:]).get('content', '') for line in stream.read_bytes().splitlines()
                                   if line.startswith(b'data:')]
                        self.assertEqual(''.join(content).encode(), (folder / 'proposal.txt').read_bytes())
                    if not folder.name.startswith('sampling-'):
                        name = str((folder / 'proposal.txt').relative_to(root))
                        covered.add(name)
                        review = reviews[name]
                        raw = (folder / 'proposal.txt').read_bytes()
                        self.assertEqual(review['response_sha256'], hashlib.sha256(raw).hexdigest())
                        self.assertEqual(review['rationale'], json.loads(raw)['rationale'])
                        self.assertEqual(review['reviewer'], 'AI investigator; not independent human validation')
                        self.assertTrue(all(c['classification'] in {'supported', 'unsupported', 'unverifiable'}
                                            and c['evidence'] for c in review['assertions']))
                for name,check in state['checks'].items():
                    if check['status'] == 'unattempted':
                        dest = run / 'smoke' / name[6:] if name.startswith('smoke-') else run / 'controls' / name
                        self.assertFalse((dest / 'completion-request.json').exists())
            self.assertEqual(covered, set(reviews))


if __name__ == '__main__':
    unittest.main()
