"""Synthetic contract checks and exact source/token preservation; no model scoring."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_v1h_predicates as audit
import native_one_hop_v1h_direction as v


class DirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = v.h.a.g.archive_files(v.PARENT / 'freeze.tar.gz')
        cls.fixtures = json.loads(cls.parent['operator-fixtures.json'])
        cls.drafts = v.h.read(v.RELEASE / 'synthetic-drafts.json')['cases']

    def preview(self, cid, condition, draft, *, context=None, fixture=None):
        context = context or json.loads(self.parent[f'contexts/{cid}-{condition}.json'])
        with tempfile.TemporaryDirectory() as temp, v.experiment():
            folder = Path(temp)
            raw = folder / 'draft.txt'
            raw.write_text(json.dumps(draft))
            result = v.h.a.preview_raw(context, raw, folder, fixture or self.fixtures[cid])
            self.assertEqual(v.h.read(folder / 'rust-preview-command.json')[1], 'nl-ask-preview')
            if result['returncode'] == 0:
                outcome = json.loads(result['stdout'])
                self.assertNotEqual(outcome['status'], 'executed')
                self.assertNotIn('bindings', outcome)
            return result

    def test_only_reverse_instruction_changes(self):
        before = (v.ROOT / 'configs/native-one-hop-v1h-qwen-status-precedence.prompt.txt').read_text()
        after = (v.ROOT / v.h.read(v.CONFIG)['prompt_file']).read_text()
        self.assertEqual(after, before.replace(v.OLD, v.NEW))
        self.assertEqual(before.count(v.OLD), 1)
        self.assertEqual(after.splitlines()[:6], before.splitlines()[:6])
        self.assertEqual(after.splitlines()[7:], before.splitlines()[7:])
        self.assertNotIn('P131', after)
        self.assertNotIn('P856', after)

    def test_saved_reverse_drafts_compile_original_object_predicate_graph_values(self):
        for row in self.drafts[:3]:
            cid, draft = row['case_id'], row['draft']
            for condition in ['oracle', 'retrieval']:
                result = self.preview(cid, condition, draft)
                if condition == 'retrieval' and cid in ['eva-07', 'eva-02']:
                    self.assertNotEqual(result['returncode'], 0)  # Missing numeric predicate stays missing.
                    continue
                self.assertEqual(result['returncode'], 0, result['stderr'])
                ctx = json.loads(self.parent[f'contexts/{cid}-{condition}.json'])
                request = json.loads(result['stdout'])['request']
                template = request['template']
                entity = next(r for r in ctx['entities'] if r['id'] == draft['start'])
                predicate = next(r for r in ctx['predicates'] if r['id'] == draft['predicate'])
                graph = next(r for r in ctx['graphs'] if r['id'] == draft['graph'])
                self.assertEqual(template['start'], entity['iri'])
                self.assertEqual(template['steps'], [dict(graph=graph['iri'], predicate=predicate['iri'], direction=draft['direction'])])
                self.assertEqual(template['output'], 'values')
                self.assertEqual(request['scope'], [graph['iri']])
                self.assertEqual(json.loads(result['stdout'])['preview']['status'], 'awaiting_confirmation')

    def test_missing_ids_wrong_start_graph_role_private_and_query_text_rejected(self):
        good = self.drafts[0]['draft']
        for changes in [dict(start=102), dict(start=65535), dict(predicate=65535), dict(graph=65535),
                        dict(graph=1), dict(predicate=100), dict(start=1002), dict(sparql='DELETE WHERE {?s ?p ?o}')]:
            with self.subTest(changes=changes):
                self.assertNotEqual(self.preview('eva-07', 'oracle', {**good, **changes})['returncode'], 0)
        original = json.loads(self.parent['contexts/eva-07-oracle.json'])
        for mutation in ['private', 'binding', 'missing']:
            ctx = copy.deepcopy(original)
            if mutation == 'private':
                ctx['graphs'][0]['iri'] = 'urn:private:unregistered'
            elif mutation == 'binding':
                next(r for r in ctx['predicates'] if r['id'] == 1002)['iri'] = 'urn:invented:inverse'
            else:
                ctx['predicates'] = [r for r in ctx['predicates'] if r['id'] != 1002]
            self.assertNotEqual(self.preview('eva-07', 'oracle', good, context=ctx)['returncode'], 0)
        # Rust checks scope and IDs, not natural-language direction correctness.
        wrong = self.preview('eva-07', 'oracle', {**good, 'direction': 'forward'})
        self.assertEqual(wrong['returncode'], 0)
        self.assertEqual(json.loads(wrong['stdout'])['interpretation_correctness'], 'not_assessed')

    def test_saved_unsupported_and_clarification_controls_are_model_origin_statuses(self):
        with v.experiment():
            for row in self.drafts[3:]:
                for condition in ['oracle', 'retrieval']:
                    result = self.preview(row['case_id'], condition, row['draft'])
                    self.assertEqual(result['returncode'], 0)
                    status = json.loads(result['stdout'])['status']
                    self.assertEqual(status, 'model_' + row['draft']['status'])
            for cid in ['eva-20', 'eva-19', 'eva-24']:
                result = self.preview(cid, 'oracle', self.drafts[0]['draft'])
                self.assertNotEqual(result['returncode'], 0)

    def test_archived_meanings_and_all_historical_hashes_reproduce(self):
        self.assertEqual(audit.build(), v.h.read(v.RELEASE / 'provenance-audit.json'))
        history = v.h.read(v.ROOT / 'reports/issue-83-native-one-hop-v1f-diagnostic/historical-sha256.json')
        self.assertEqual(len(history), 801)
        for name, digest in history.items():
            self.assertEqual(v.h.sha(v.ROOT / name), digest, name)
        for row in audit.build()['predicates']:
            self.assertEqual(row['languages'], ['en'])
            self.assertEqual(row['snapshot_property_subject_statements'], 0)
            self.assertEqual(row['predicate_binding'].get('texts', []), [])
            self.assertTrue(any('schema.org/description' in r['statement'] for r in row['property_metadata']))

    def test_final_freeze_tokens_membership_and_native_history(self):
        payload = v.h.a.g.archive_files(v.RELEASE / 'freeze.tar.gz')
        counts = json.loads(payload['tokenization/counts.json'])
        with v.experiment():
            v.h.validate_counts(counts, ['qwen35'])
            with patch.object(v.h.a.t, 'cases', side_effect=AssertionError('Gold accessed by renderer')):
                for name, raw in payload.items():
                    if name.startswith('contexts/'):
                        self.assertEqual(v.h.messages(json.loads(raw)), json.loads(payload[name.replace('contexts/', 'messages/')]))
        rows = counts['models']['qwen35']['rows']
        old_rows = json.loads(self.parent['tokenization/counts.json'])['models']['qwen35']['rows']
        self.assertEqual(len(rows), 38)
        self.assertEqual(sum(r['kind'] == 'semantic_diagnostic' for r in rows), 36)
        self.assertEqual(rows[:2], old_rows[:2])
        self.assertEqual(len(counts['models']['qwen35']['native_parities_reproduced']), 36)
        old_prompt = (v.ROOT / 'configs/native-one-hop-v1h-qwen-status-precedence.prompt.txt').read_text().rstrip()
        new_prompt = (v.ROOT / v.h.read(v.CONFIG)['prompt_file']).read_text().rstrip()
        for row, old in zip(rows[2:], old_rows[2:]):
            for variant in ['original', 'columnar']:
                receipt = row[variant]
                self.assertEqual(receipt['prompt'], old[variant]['prompt'].replace(old_prompt, new_prompt, 1))
                self.assertEqual(receipt['output_reserve'], 512)
                self.assertEqual(sum(receipt['section_contributions'].values()), receipt['input_tokens'])
        for name, raw in self.parent.items():
            if name.startswith(('contexts/', 'original-contexts/', 'grammars/', 'packets/')) or name in ['schedule.json', 'operator-fixtures.json']:
                self.assertEqual(payload[name], raw, name)
        frozen = json.loads(payload['freeze.json'])
        for name, digest in frozen['input_sha256'].items():
            self.assertEqual(v.h.sha(v.ROOT / name), digest, name)
        self.assertEqual(frozen['runtime_identity'], json.loads(self.parent['freeze.json'])['runtime_identity'])
        self.assertEqual(frozen['config']['host_gates']['swap_used_mib_max'], 1024)
        reg = v.h.read(v.RELEASE / 'registration.json')
        self.assertEqual(v.h.sha(v.RELEASE / 'freeze.tar.gz'), reg['archive_sha256'])
        self.assertEqual(hashlib.sha256(payload['tokenization/counts.json']).hexdigest(), reg['token_receipt_sha256'])
        self.assertFalse(reg['inference_authorized'])
        self.assertFalse(reg['inference_performed'])

    def test_opt_in_and_ci_guards_before_assets(self):
        with v.experiment(), patch.object(v.h.a, 'assets') as assets, patch.object(v.h, 'Runtime') as runtime:
            with self.assertRaisesRegex(ValueError, 'allow-inference'):
                v.h.run(Path('missing'), Path('missing'), 'qwen35')
            with patch.dict('os.environ', {'CI': '1'}), self.assertRaisesRegex(ValueError, 'forbidden in CI'):
                v.h.run(Path('missing'), Path('missing'), 'qwen35', True)
            assets.assert_not_called()
            runtime.assert_not_called()

    def test_synthetic_full_schedule_private_stop_and_fresh_ledger(self):
        from test_native_one_hop_v1h import BudgetTests
        payload = v.h.a.g.archive_files(v.RELEASE / 'freeze.tar.gz')
        self.payload = payload
        self.counts = json.loads(payload['tokenization/counts.json'])
        with v.experiment():
            BudgetTests.test_synthetic_full_schedule_and_private_failure_keep_zero_execution_authority(self)


if __name__ == '__main__':
    unittest.main()
