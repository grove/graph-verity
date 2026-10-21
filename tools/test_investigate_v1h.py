"""Blinded review has no reference/outcome labels in the initial source view."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import investigate_v1h as i


class InvestigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.freeze = cls.root/'freeze'
        for name,raw in i.v.a.g.archive_files(i.v.RELEASE/'freeze.tar.gz').items():
            path = cls.freeze/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
        cls.out = cls.root/'generated'
        with patch('subprocess.Popen',side_effect=AssertionError('Investigation must not start processes')):
            i.build(cls.out,cls.freeze)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_byte_reproduction_and_all_missing_observations_retained(self):
        committed = i.v.ROOT/'experiments/native-one-hop-v1h-investigation/generated'
        self.assertEqual(i.analysis.inventory(self.out),i.analysis.inventory(committed))
        rows = i.v.read(self.out/'failure-by-failure.json')['cases']
        self.assertEqual(len(rows),36)
        self.assertEqual(sum(r['completed'] for r in rows),33)
        self.assertEqual(sum(not r['attempted'] for r in rows),3)
        self.assertTrue(all(r['exposed_reference_agreement'] is None for r in rows if not r['attempted']))
        self.assertTrue(all(r['independent_human_judgment'] is None for r in rows))

    def test_staged_review_is_identity_masked_source_bound_and_pending(self):
        payload = i.v.a.g.archive_files(self.out/'blind-review.tar.gz')
        self.assertFalse(any('coordinator' in n for n in payload))
        self.assertEqual(len([n for n in payload if n.endswith('/question.json')]),36)
        self.assertEqual(len([n for n in payload if n.endswith('/draft.txt')]),33)
        forbidden = {'gold_draft','gold_request','expected_status','resolved_start','preflight_blocked',
                     'exposed_reference_agreement','field_agreement','preregistered_AI_audit'}
        def inspect(value):
            if isinstance(value,dict):
                self.assertFalse(forbidden & value.keys())
                for child in value.values():inspect(child)
            elif isinstance(value,list):
                for child in value:inspect(child)
        for name,raw in payload.items():
            self.assertNotIn(b'qwen35',raw)
            self.assertNotIn(b'gemma4',raw)
            if name.startswith('phase1-source/') and name.endswith('.json'):
                inspect(json.loads(raw))
            if name.endswith('/review.json'):
                template = json.loads(raw)
                self.assertEqual(template['status'],'pending')
                self.assertIsNone(template['reviewer_id'])
                self.assertIsNone(template['reviewed_at'])
        original = i.v.a.g.archive_files(i.v.ROOT/'experiments/native-one-hop-v1f-diagnostic-r3-evidence/evidence.tar.gz')
        self.assertEqual(payload['phase1-source/source.nq'],original['source/studies/nl-ask-v1/evaluation/snapshot.nq'])
        for row in i.v.read(self.out/'coordinator/mapping.json'):
            name=f"run/diagnostic/{row['condition']}/{row['observation']}/proposal.txt"
            blind='phase2-drafts/'+row['review_id']+'/draft.txt'
            self.assertEqual(payload.get(blind),original.get(name))


if __name__ == '__main__':
    unittest.main()
