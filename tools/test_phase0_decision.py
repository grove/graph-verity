"""Check the published decision against saved public evidence; no inference or network."""
import hashlib
import json
import re
import unittest
from pathlib import Path

from phase0 import rate

ROOT = Path(__file__).resolve().parents[1]


class Phase0DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / 'docs/phase-0-decision.json').read_text())
        cls.document = (ROOT / 'docs/phase-0-decision.md').read_text()
        cls.facts = {f['name']: f['value'] for f in cls.record['facts']}

    def test_copied_facts_have_exact_public_sources_and_valid_intervals(self):
        def intervals(value):
            if isinstance(value, dict):
                if value.get('status') == 'measured' and 'wilson_95' in value:
                    expected = rate(value['numerator'], value['denominator'])
                    self.assertEqual(value['value'], expected['value'])
                    self.assertEqual(value['wilson_95'], expected['wilson_95'])
                for item in value.values():
                    intervals(item)
            elif isinstance(value, list):
                for item in value:
                    intervals(item)

        self.assertEqual(len(self.facts), len(self.record['facts']))
        for fact in self.record['facts']:
            with self.subTest(fact=fact['name']):
                path = Path(fact['source'])
                self.assertFalse(path.is_absolute())
                self.assertNotIn('..', path.parts)
                self.assertIn(path.parts[0], ['reports', 'configs'])
                self.assertNotIn('holdout', str(path))
                raw = (ROOT / path).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), fact['source_sha256'])
                value = json.loads(raw)
                for key in fact['keys']:
                    value = value[key]
                self.assertEqual(value, fact['value'])
                intervals(value)

    def test_human_tables_match_adversarial_rates_and_intervals(self):
        labels = [('Valid JSON/contracts', 'contract_valid'), ('Invalid contracts', 'invalid_contract'),
                  ('Correct complete answers', 'strict_complete_exact'),
                  ('Correct model abstentions', 'correct_status_abstention'),
                  ('Executed proposals', 'execution'), ('Wrong-but-executable plans', 'wrong_executable_strict')]
        for label, key in labels:
            values = [self.facts[f'{route}.{key}'] for route in ['v1', 'v2']]
            cells = [f"{v['numerator']}/{v['denominator']}" for v in values]
            self.assertIn(f'| {label} | {cells[0]} | {cells[1]} |', self.document)
        for label, key in [('Contract valid / 30', 'contract_valid'),
                           ('Invalid contract / 30', 'invalid_contract'),
                           ('Complete answer / 24', 'strict_complete_exact'),
                           ('Correct abstention / 6', 'correct_status_abstention'),
                           ('Wrong execution / 30', 'wrong_executable_strict')]:
            cells = ['–'.join(f'{x * 100:.1f}' for x in self.facts[f'{r}.{key}']['wilson_95']) + '%'
                     for r in ['v1', 'v2']]
            self.assertIn(f'| {label} | {cells[0]} | {cells[1]} |', self.document)

    def test_development_latency_tokens_memory_and_hashes(self):
        dev = self.facts['development.performance']
        for label, key, denom in [('Valid contracts', 'contract_valid', 'questions'),
                                  ('Invalid contracts', 'invalid_contract', 'questions'),
                                  ('Strict structural IR agreement', 'structural_AI_reference_matches', 'supported'),
                                  ('Exact answer-binding agreement', 'exact_answer_AI_reference_matches', 'supported'),
                                  ('Correct expected-status abstentions', 'correct_status_abstentions', 'expected_abstentions')]:
            cells = [f"{v[key]}/{v[denom]}" for v in dev.values()]
            self.assertIn(f'| {label} | {cells[0]} | {cells[1]} |', self.document)
        runs = [('Original dev', dev), ('Repeat dev', self.facts['repeat.performance'])]
        for name, values in runs:
            for dataset, label in [('wikidata', 'Wikidata'), ('worldcities-transfer', 'real transfer')]:
                v = values[dataset]
                times = [v['warm_end_to_end_ms'][p] for p in ['p50', 'p95', 'p99']]
                times.append(v['cold_first_answer_ms_page_cache_not_evicted'])
                row = ' | '.join(f'{x / 1000:.2f}' for x in times)
                self.assertIn(f'| {name} / {label} | {row} |', self.document)
        for v in dev.values():
            generation = '/'.join(f'{v['generation_ms'][p] / 1000:.2f}' for p in ['p50', 'p95', 'p99'])
            self.assertIn(generation, self.document)
        comparison = json.loads((ROOT / 'reports/issue-32-compact-ab/comparison.json').read_text())
        for route in ['v1', 'v2']:
            for dataset, label in [('adversarial', 'source'), ('adversarial-transfer', 'transfer')]:
                v = self.facts[f'{route}.performance']['datasets'][dataset]
                times = [v['warm_end_to_end_ms'][p] for p in ['p50', 'p95', 'p99']]
                times.append(v['cold_first_answer_ms_page_cache_not_evicted'])
                row = ' | '.join(f'{x / 1000:.2f}' for x in times)
                self.assertIn(f'| Adversarial {route} / {label} | {row} |', self.document)
                generation = '/'.join(f'{v['generation_ms'][p] / 1000:.2f}' for p in ['p50', 'p95', 'p99'])
                self.assertIn(generation, self.document)
            for key in ['input_tokens', 'output_tokens']:
                self.assertIn(f"{self.facts[f'{route}.{key}']:,}", self.document)
        for dataset, label in [('adversarial', 'Source'), ('adversarial-transfer', 'Transfer')]:
            cells = [f"{comparison['datasets'][dataset][r]['input_tokens']:,} / "
                     f"{comparison['datasets'][dataset][r]['output_tokens']:,}" for r in ['v1', 'v2']]
            self.assertIn(f'| {label} | {cells[0]} | {cells[1]} |', self.document)
        for run in ['development', 'repeat', 'adversarial-v1']:
            for key in ['sampled_aggregate_peak_rss_kib', 'child_lifetime_peak_rss_kib']:
                self.assertIn(f"{int(self.facts[f'{run}.{key}']):,}", self.document)
        freeze = self.facts['v2.freeze']
        for key in ['sampled_aggregate_peak_rss_kib', 'child_lifetime_peak_rss_kib']:
            self.assertIn(f"{int(self.facts['v2.performance'][key]):,}", self.document)
        for config in [freeze['v1_config'], freeze['v2_config']]:
            for key in ['model_sha256', 'runtime_revision', 'prompt_sha256', 'grammar_sha256', 'schema_sha256']:
                self.assertIn(config[key], self.document)
        for dataset in ['wikidata', 'worldcities-transfer', 'adversarial', 'adversarial-transfer']:
            hashes = (self.facts['development.artifact_sha256'] if dataset in dev else freeze['input_sha256'])
            for path in [f'benchmarks/{dataset}.json', f'data/{dataset}/snapshot.nq']:
                self.assertIn(hashes[path], self.document)
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), hashes[path])

    def test_decision_limits_and_local_links(self):
        self.assertEqual(self.record['decision'], {
            'unattended_free_form_ask': 'STOP_TESTED_CONFIGURATIONS',
            'product_direction': 'REVISE_FIND_FIRST', 'formal_phase0_gate': 'NOT READY',
            'evidence_class': 'public_development_AI_reference_agreement_only',
            'expert_gold_review_completed': False, 'sealed_holdout_evaluated': False,
            'sealed_holdout_independence_established': False, 'phase1_implemented': False})
        self.assertEqual(self.facts['owner_approval']['status'], 'owner_approved_pending_external_split_integrity')
        self.assertIsNone(self.facts['owner_approval']['experiment_identity']['split_integrity_evidence_sha256'])
        self.assertFalse(self.facts['v2.freeze']['protocol']['holdout_accessed'])
        for phrase in ['Human review was waived for exploratory engineering only',
                       'not a formally preregistered, expert-validated feasibility result',
                       'No private holdout material was accessed', 'no SHACL runtime scheduled']:
            self.assertIn(phrase, self.document)
        for url in self.record['phase1_issues'].values():
            self.assertRegex(url, r'^https://github.com/grove/graph-verity/issues/\d+$')
            self.assertIn(url, self.document)
        for path in ['README.md', 'docs/phase-0-decision.md', 'docs/phase-0-feasibility.md',
                     'docs/phase-0-evaluation.md', 'docs/implementation-plan.md']:
            for link in re.findall(r'\]\(([^)]+)\)', (ROOT / path).read_text()):
                if '://' not in link and not link.startswith('#'):
                    self.assertTrue((ROOT / path).parent.joinpath(link.split('#')[0]).exists(), (path, link))


if __name__ == '__main__':
    unittest.main()
