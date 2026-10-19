"""Inspect the committed execution release portably; never load registered binaries/models."""
import hashlib
import json
import unittest

import native_one_hop_v1g as v


class CommittedExecutionTests(unittest.TestCase):
    def test_committed_execution_and_separate_development_bytes(self):
        release = v.DESIGN / 'execution-v1'
        reg = v.read(release / 'freeze/execution-registration.json')
        self.assertFalse(reg['inference_authorized'])
        self.assertFalse(reg['inference_performed'])
        self.assertTrue(reg['model_free_replay_passed'])
        self.assertEqual(reg['decision'], 'INCONCLUSIVE_REVISE')
        archive = v.ROOT / reg['archive_path']
        self.assertEqual(v.sha(archive), reg['archive_sha256'])
        payload = v.a.g.archive_files(archive)
        manifest = json.loads(payload['checksums.json'])
        self.assertEqual({name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()
                          if name != 'checksums.json'}, manifest)
        self.assertEqual(payload['checksums.json'], (release / 'freeze/checksums.json').read_bytes())
        self.assertEqual(v.sha(release / 'freeze/checksums.json'), reg['freeze_sha256'])
        self.assertEqual(json.loads(payload['freeze.json']), reg['freeze_manifest'])
        for name, digest in reg['freeze_manifest']['input_sha256'].items():
            self.assertEqual(v.sha(v.ROOT / name), digest, name)
        self.assertEqual(v.sha(release / 'assets.json'), reg['fresh_assets_receipt_sha256'])
        self.assertEqual(v.read(release / 'assets.json'), reg['freeze_manifest']['runtime_identity'])
        self.assertEqual(len(json.loads(payload['questions.json'])), 30)
        self.assertEqual(len([name for name in payload if name.startswith('contexts/')]), 90)
        for name, raw in payload.items():
            if name.startswith('contexts/'):
                self.assertNotIn('packet', json.loads(raw))
        score = v.read(release / 'unattempted-score.json')
        self.assertFalse(score['semantic_go'])
        self.assertEqual(len(score['cases']),184)
        self.assertTrue(all(r['exact_exposed_reference_agreement'] is None for r in score['cases']))
        panel = v.a.g.archive_files(release / 'explicit-predicate-development.tar.gz')
        self.assertFalse(json.loads(panel['panel.json'])['v1g_denominator_member'])
        self.assertFalse(json.loads(panel['panel.json'])['inference_performed'])
        for name, digest in json.loads(panel['checksums.json']).items():
            self.assertEqual(hashlib.sha256(panel[name]).hexdigest(), digest)
        development = v.read(release / 'development-registration.json')
        self.assertEqual(development['archive_sha256'], v.sha(release / 'explicit-predicate-development.tar.gz'))
        self.assertFalse(development['native_inference_authorized'])
        self.assertEqual(development['v1g_denominator_contribution'],0)
