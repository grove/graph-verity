"""Model-free prompt/budget, clarification and trust-boundary regressions."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_one_hop_v1h_status_precedence as v


class StatusPrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = v.h.a.g.archive_files(v.RELEASE / 'freeze.tar.gz')
        cls.parent = v.h.a.g.archive_files(v.PARENT / 'freeze.tar.gz')
        cls.counts = json.loads(cls.payload['tokenization/counts.json'])

    def test_exact_prompt_change_preserves_every_other_contract_line(self):
        before = (v.ROOT / 'configs/native-one-hop-v1e.prompt.txt').read_text().splitlines(True)
        cfg = v.h.read(v.CONFIG)
        after = (v.ROOT / cfg['prompt_file']).read_text().splitlines(True)
        self.assertEqual(after[:2], before[:2])
        self.assertEqual(after[2], before[6].rstrip() +
            ' A forbidden operation takes precedence over clarification or a partial candidate.'
            ' Missing authorized numeric vocabulary for an otherwise supported one-hop question requires clarification.\n')
        self.assertEqual(after[3], 'Otherwise, ' + before[5][0].lower() + before[5][1:])
        self.assertEqual(after[4], 'Otherwise, ' + before[2][0].lower() + before[2][1:])
        self.assertEqual(after[5:7], before[3:5])
        self.assertEqual(after[7:], before[7:])

    def test_exact_frozen_budgets_and_unchanged_sampling_controls(self):
        with v.experiment():
            v.h.validate_counts(self.counts, ['qwen35'])
        rows = self.counts['models']['qwen35']['rows']
        self.assertEqual(len(rows), 38)
        self.assertEqual(sum(r['kind'] == 'semantic_diagnostic' for r in rows), 36)
        original = json.loads(self.parent['tokenization/counts.json'])['models']['qwen35']['rows']
        self.assertEqual(rows[:2], original[:2])
        self.assertEqual(max(r['columnar']['input_tokens'] for r in rows), 14049)
        self.assertEqual(max(r['columnar']['total_required'] for r in rows), 14561)
        self.assertEqual(max(r['original']['input_tokens'] for r in rows), 18956)
        old_prompt = (v.ROOT / 'configs/native-one-hop-v1e.prompt.txt').read_text()
        new_prompt = (v.ROOT / v.h.read(v.CONFIG)['prompt_file']).read_text()
        for row, old in zip(rows[2:], original[2:]):
            for variant in ['original', 'columnar']:
                self.assertEqual(row[variant]['prompt'], old[variant]['prompt'].replace(old_prompt, new_prompt, 1))
                self.assertEqual(row[variant]['input_tokens'] - old[variant]['input_tokens'], 30)
        self.assertEqual(len(self.counts['models']['qwen35']['native_parities_reproduced']), 36)
        for row in rows:
            for variant in ['original', 'columnar']:
                r = row[variant]
                self.assertEqual(r['output_reserve'], 512)
                self.assertEqual(r['total_required'], len(r['tokens']) + 512)
                self.assertEqual(r['fits'], r['total_required'] < 16384)
                self.assertEqual(sum(r['section_contributions'].values()), len(r['tokens']))
        reg = v.h.read(v.RELEASE / 'registration.json')
        self.assertEqual(v.h.sha(v.RELEASE / 'freeze.tar.gz'), reg['archive_sha256'])
        self.assertEqual(hashlib.sha256(self.payload['tokenization/counts.json']).hexdigest(), reg['token_receipt_sha256'])
        self.assertFalse(reg['inference_performed'])
        self.assertFalse(reg['inference_authorized'])

    def test_frozen_inputs_grammar_scope_ids_and_gold_independence(self):
        for name, raw in self.parent.items():
            if name.startswith(('contexts/', 'original-contexts/', 'grammars/', 'packets/')) or name in ['schedule.json', 'operator-fixtures.json']:
                self.assertEqual(self.payload[name], raw, name)
        frozen = json.loads(self.payload['freeze.json'])
        for name, digest in frozen['input_sha256'].items():
            self.assertEqual(v.h.sha(v.ROOT / name), digest, name)
        self.assertEqual(frozen['runtime_identity'], json.loads(self.parent['freeze.json'])['runtime_identity'])
        with v.experiment(), patch.object(v.h.a.t, 'cases', side_effect=AssertionError('Gold accessed')):
            for name, raw in self.payload.items():
                if name.startswith('contexts/'):
                    context = json.loads(raw)
                    self.assertEqual(v.h.messages(context), json.loads(self.payload[name.replace('contexts/', 'messages/')]))
                    self.assertNotIn('PRIVATE_CANARY', json.dumps(context))
        self.assertEqual(frozen['config']['host_gates']['swap_used_mib_max'], 1024)
        self.assertEqual(frozen['config']['variants'], ['qwen35'])

    def test_genuine_clarification_and_ai_ambiguity_remain_distinct_from_rejection(self):
        fixtures = json.loads(self.payload['operator-fixtures.json'])
        with v.experiment():
            for condition in ['oracle', 'retrieval']:
                for cid in ['eva-20', 'eva-19', 'eva-24', 'eva-06']:
                    context = json.loads(self.payload[f'contexts/{cid}-{condition}.json'])
                    with tempfile.TemporaryDirectory() as temp:
                        folder = Path(temp)
                        raw = folder / 'draft'
                        raw.write_text(json.dumps(dict(version='nl-ask-draft-v1', status='needs_clarification', rationale='Unresolved input')))
                        result = v.h.a.preview_raw(context, raw, folder, fixtures[cid])
                        self.assertEqual(result['returncode'], 0)
                        outcome = v.h.a.semantic_outcome(cid, raw, result)
                        self.assertEqual(outcome['model_status'], 'needs_clarification')
                        self.assertEqual(outcome['semantic_correct'], cid != 'eva-06')
                        self.assertNotIn('executed', result['stdout'])

    def test_supported_candidate_regression_and_scope_private_write_rejections(self):
        context = json.loads(self.payload['contexts/eva-01-oracle.json'])
        fixtures = json.loads(self.payload['operator-fixtures.json'])
        good = v.h.a.t.cases()[0]['gold_draft']
        private = copy.deepcopy(context)
        private['graphs'][0]['iri'] = 'urn:private:unregistered'
        cases = [(context, good, fixtures['eva-01'], True),
                 (context, good, dict(resolved_start=None, blocked=False), False),
                 (context, good, dict(resolved_start=102, blocked=True), False),
                 (context, {**good, 'graph': 65535}, fixtures['eva-01'], False),
                 (context, {**good, 'predicate': 65535}, fixtures['eva-01'], False),
                 (context, {**good, 'sparql': 'DELETE WHERE {?s ?p ?o}'}, fixtures['eva-01'], False),
                 (private, good, fixtures['eva-01'], False)]
        with v.experiment():
            for ctx, draft, fixture, accepted in cases:
                with self.subTest(draft=draft, fixture=fixture), tempfile.TemporaryDirectory() as temp:
                    folder = Path(temp)
                    raw = folder / 'draft'
                    raw.write_text(json.dumps(draft))
                    result = v.h.a.preview_raw(ctx, raw, folder, fixture)
                    self.assertEqual(result['returncode'] == 0, accepted)
                    self.assertNotIn('executed', result['stdout'])
            with tempfile.TemporaryDirectory() as temp:
                raw = Path(temp) / 'draft'
                for status in ['unsupported', 'needs_clarification']:
                    raw.write_text(json.dumps(dict(version='nl-ask-draft-v1', status=status, rationale='Synthetic regression')))
                    outcome = v.h.a.semantic_outcome('eva-01', raw, dict(returncode=0))
                    self.assertFalse(outcome['semantic_correct'])
                    self.assertFalse(all(outcome['field_agreement'].values()))

    def test_opt_in_and_ci_guards_precede_assets_and_weight_loading(self):
        with v.experiment(), patch.object(v.h.a, 'assets') as assets, patch.object(v.h, 'Runtime') as runtime:
            with self.assertRaisesRegex(ValueError, 'allow-inference'):
                v.h.run(Path('missing'), Path('missing'), 'qwen35')
            with patch.dict('os.environ', {'CI': '1'}), self.assertRaisesRegex(ValueError, 'forbidden in CI'):
                v.h.run(Path('missing'), Path('missing'), 'qwen35', True)
            assets.assert_not_called()
            runtime.assert_not_called()

    def test_inherited_synthetic_schedule_and_private_canary_stop_with_new_prompt(self):
        from test_native_one_hop_v1h import BudgetTests
        with v.experiment():
            BudgetTests.test_synthetic_full_schedule_and_private_failure_keep_zero_execution_authority(self)


if __name__ == '__main__':
    unittest.main()
