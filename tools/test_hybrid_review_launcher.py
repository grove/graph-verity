"""Offline handoff regression fixtures only; no real participants or judgments."""
import copy
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import hybrid_review_launcher as launcher


def remove_readonly(path):
    path.chmod(0o700)
    for child in path.rglob('*'):
        if child.is_dir() and not child.is_symlink():
            child.chmod(0o700)
    shutil.rmtree(path)


class PortableReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = launcher.ROOT
        cls.spec = launcher.manifest()
        cls.export = Path(tempfile.mkdtemp())
        launcher.prepare_source(cls.export / 'source', cls.spec)

    @classmethod
    def tearDownClass(cls):
        remove_readonly(cls.export)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / 'tools').mkdir()
        self.script = self.root / 'tools/hybrid_review_launcher.py'
        shutil.copy2(self.original / 'tools/hybrid_review_launcher.py', self.script)
        destination = self.root / 'studies/hybrid-review-handoff'
        destination.mkdir(parents=True)
        shutil.copy2(self.original / 'studies/hybrid-review-handoff/manifest.json', destination)
        self.private = self.root / 'study-private/hybrid'
        launcher.private_directory(self.private.parent)
        launcher.private_directory(self.private)
        self.source = self.private / 'source'
        shutil.copytree(self.export / 'source', self.source)

    def tearDown(self):
        remove_readonly(self.root)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', '-S', '-B', str(self.script), *args],
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, 'PATH': '', 'PYTHONPATH': str(self.root / 'tools')})

    def prepare(self):
        result = self.run_cli('prepare')
        self.assertEqual(result.returncode, 0, result.stderr)

    def rewrite(self, relative, data):
        path = self.source / relative
        path.chmod(0o600)
        path.write_bytes(data)
        path.chmod(0o400)

    def launch_fixture(self, reviewer, kind):
        # Intercept only browser opening/serving; exercise real isolated saved-review enrollment.
        code = '''
import runpy, sys, webbrowser
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'study-private/hybrid/source/tools'))
import local_find
webbrowser.open = lambda url: True
local_find.Server.serve_forever = lambda self: None
sys.argv = [str(root / 'tools/hybrid_review_launcher.py'), 'launch',
            '--reviewer', sys.argv[2], '--kind', sys.argv[3], '--consent']
runpy.run_path(sys.argv[0], run_name='__main__')
'''
        return subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code,
                               str(self.root), reviewer, kind], capture_output=True, text=True, timeout=30)

    def test_offline_bundle_ignores_evolving_main_and_has_no_third_party_imports(self):
        (self.root / 'tools/hybrid_review.py').write_text("raise RuntimeError('EVOLVING MAIN')")
        code = '''
import runpy, sys
def audit(event, args):
    if event in ('socket.connect', 'socket.bind', 'subprocess.Popen'):
        raise RuntimeError('Network/process forbidden in verification')
    if event == 'import' and args[0].split('.')[0] in ('torch', 'numpy', 'transformers'):
        raise RuntimeError('Model import forbidden')
sys.addaudithook(audit)
sys.argv = [sys.argv[1], 'prepare']
runpy.run_path(sys.argv[0], run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code, str(self.script)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.private.glob('reviewer-*.json')), [])
        capture = self.private / 'results.json'
        self.assertEqual(capture.stat().st_mode & 0o777, 0o600)
        self.assertEqual(capture.read_bytes(), gzip.decompress((self.source / launcher.CAPTURE).read_bytes()))
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o500)
        self.prepare()  # Already exported kit needs neither Git nor the source checkout.

    def test_missing_changed_extra_or_writable_source_fails_before_session(self):
        target = 'tools/local_find.py'
        original = (self.source / target).read_bytes()
        for data in (b'# changed', b''):
            self.rewrite(target, data)
            self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.rewrite(target, original)
        (self.source / target).chmod(0o600)
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        (self.source / target).chmod(0o400)
        self.source.chmod(0o700)
        extra = self.source / 'unregistered.py'
        extra.write_text('')
        extra.chmod(0o400)
        self.source.chmod(0o500)
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.source.chmod(0o700)
        extra.unlink()
        (self.source / target).parent.chmod(0o700)
        (self.source / target).unlink()
        (self.source / target).parent.chmod(0o500)
        self.source.chmod(0o500)
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.assertFalse((self.private / 'results.json').exists())

    def test_wrong_protocol_unexpected_capture_and_missing_capture_fail_closed(self):
        data = json.loads(gzip.decompress((self.source / launcher.CAPTURE).read_bytes()))
        data['protocol_id'] = 'wrong'
        raw = json.dumps(data).encode()
        archive = gzip.compress(raw)
        self.rewrite(launcher.CAPTURE, archive)
        spec = copy.deepcopy(self.spec)
        spec.update(capture_sha256=launcher.digest(archive), results_sha256=launcher.digest(raw))
        with self.assertRaisesRegex(ValueError, 'protocol'):
            launcher.prepare_capture(self.private, self.source, spec)
        self.rewrite(launcher.CAPTURE, (self.export / 'source' / launcher.CAPTURE).read_bytes())
        self.prepare()
        capture = self.private / 'results.json'
        capture.write_text('{}')
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.assertEqual(capture.read_text(), '{}')
        capture.unlink()
        session = self.private / 'reviewer-rehearsal.json'
        session.write_text('{}')
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.assertFalse(capture.exists())

    def test_consent_kind_private_permissions_and_operator_lock(self):
        for args in (('launch', '--reviewer', '01', '--kind', 'independent'),
                     ('launch', '--reviewer', 'owner', '--kind', 'independent', '--consent')):
            self.assertNotEqual(self.run_cli(*args).returncode, 0)
        self.assertEqual(list(self.private.glob('reviewer-*.json')), [])
        self.private.chmod(0o755)
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.private.chmod(0o700)
        (self.private / '.operator-lock').write_text('')
        self.assertNotEqual(self.run_cli('prepare').returncode, 0)
        self.assertTrue((self.private / '.operator-lock').exists())

    def test_two_synthetic_sessions_fresh_seeds_no_replay_and_private_report(self):
        for reviewer in ('01', '02'):
            result = self.launch_fixture(reviewer, 'independent')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('http://', result.stdout + result.stderr)
        paths = [self.private / ('reviewer-' + number + '.json') for number in ('01', '02')]
        sessions = [json.loads(path.read_bytes()) for path in paths]
        self.assertNotEqual(sessions[0]['seed'], sessions[1]['seed'])
        self.assertNotEqual(sessions[0]['reviewer'], sessions[1]['reviewer'])
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in paths))
        before = paths[0].read_bytes()
        self.assertNotEqual(self.launch_fixture('01', 'independent').returncode, 0)
        self.assertEqual(before, paths[0].read_bytes())
        result = self.run_cli('report')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.private / 'report.json'
        self.assertEqual(report.stat().st_mode & 0o777, 0o600)
        summary = json.loads(report.read_bytes())
        self.assertEqual(summary['recommendation'], 'defer')
        self.assertEqual(summary['paired'], [])  # Blank synthetic fixtures never satisfy the gate.
        self.assertNotEqual(self.run_cli('report', paths[0].name, paths[0].name).returncode, 0)
        sessions[1]['reviewer'] = sessions[0]['reviewer']
        paths[1].write_text(json.dumps(sessions[1]))
        result = self.run_cli('report')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Duplicate reviewer', result.stdout)
        sessions[1]['reviewer'] = 'R-' + 'f' * 16
        sessions[1]['seed'] = sessions[0]['seed']
        paths[1].write_text(json.dumps(sessions[1]))
        self.assertNotEqual(self.run_cli('report').returncode, 0)
        self.assertEqual(json.loads(report.read_bytes()), summary)

    def test_saved_rehearsal_uses_existing_browser_security_walkthrough(self):
        self.prepare()
        code = '''
import runpy, sys, unittest
from pathlib import Path
root = Path(sys.argv[1])
private = root / 'study-private/hybrid'
sys.path.insert(0, str(private / 'source/tools'))
import hybrid_review as review
import test_hybrid_review as tests
review.forms.PRIVATE = private
class SavedBrowser(tests.HybridReview):
    def setUp(self):
        self.review = review.Review(demo=False, results=private / 'results.json',
                                   out=private / 'reviewer-rehearsal.json')
        self.session = self.review.api('/api/session', {})
        self.task_id = next(iter(self.review.tasks))
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
    SavedBrowser('test_http_and_headless_browser')]))
sys.exit(not result.wasSuccessful())
'''
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code, str(self.root)],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class SavedReviewSemantics(unittest.TestCase):
    def test_synthetic_offlist_no_match_incomplete_and_disagreement(self):
        import hybrid_review as review
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / 'results.json'
            results.write_bytes(gzip.decompress((launcher.ROOT / launcher.CAPTURE).read_bytes()))
            study = review.Review(demo=False, results=results)
        task_id = next(iter(study.tasks))
        union = {(hit['graph'], hit['iri']) for hits in study.candidates(task_id).values() for hit in hits}
        offlist = next(key for key in study.authorized(study.tasks[task_id]) if key not in union)
        judgment = dict(ratings=[dict(graph=g, iri=i, relevance='irrelevant') for g, i in sorted(union)],
                        offlist=[dict(graph=offlist[0], iri=offlist[1])], universe_reviewed=True, no_match=False,
                        checks={side: dict.fromkeys(review.CHECKS, 'uncertain') for side in ('A', 'B')},
                        confidence=dict(A=3, B=3), preference='uncertain', excluded=None)
        study.validate(task_id, judgment)
        for change in (dict(ratings=[]), dict(no_match=True), dict(universe_reviewed=False)):
            with self.assertRaises(ValueError):
                study.validate(task_id, dict(judgment, **change))
        sessions = []
        for number in ('1', '2'):
            session = copy.deepcopy(study.session)
            session.update(kind='independent', consent=True, reviewer='R-' + number * 16)
            session['records'][task_id] = dict(judgment=copy.deepcopy(judgment), order=list(study.order(task_id)))
            sessions.append(session)
        summary = review.summarize(sessions, study)
        self.assertEqual(summary['paired'][0]['relevant'], judgment['offlist'])
        sessions[1]['records'][task_id]['judgment'].update(offlist=[], no_match=True)
        summary = review.summarize(sessions, study)
        self.assertEqual(summary['paired'], [])
        self.assertTrue(any(row['reason'] == 'disagreement' for row in summary['conflicts']))
        self.assertEqual(summary['recommendation'], 'defer')


if __name__ == '__main__':
    unittest.main()
