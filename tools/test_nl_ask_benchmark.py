"""Model-free regression tests for the #72 frozen contract and saved-outcome scorer."""
import copy
import json
import subprocess
import unittest

import nl_ask_benchmark as n


class NarrowAskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['cargo', 'build', '--quiet', '--locked', '--offline', '-p', 'verity_cli'],
                       cwd=n.ROOT, check=True)
        cls.binary = n.ROOT / 'target/debug/verity'
        cls.cases = n.read(n.STUDY / 'cases.json')

    def record(self, case, raw=None, **extra):
        return dict(id=case['id'], runtime_status='completed',
                    raw_response=json.dumps(case['gold_draft']) if raw is None else raw, **extra)

    def test_schema_matches_rust_and_all_frozen_references_preview_without_execution(self):
        schema = json.loads(subprocess.check_output([self.binary, 'schema-nl-ask'], text=True))
        self.assertEqual(schema, n.read(n.ROOT / 'schemas/nl-ask-draft-v1.json'))
        for case in self.cases:
            with self.subTest(case=case['id']):
                classification, value = n.rust_preview(case, json.dumps(case['gold_draft']), self.binary)
                expected = case['expected_status']
                self.assertEqual(classification['status'], 'candidate' if expected == 'candidate' else 'model_' + expected)
                self.assertNotIn('result', value)
                if expected == 'candidate':
                    self.assertEqual(value['request'], case['gold_request'])
                    self.assertEqual(value['interpretation_correctness'], 'not_assessed')
                else:
                    self.assertNotIn('request', value)

    def test_invalid_categories_preflight_and_model_origin_are_distinct(self):
        case = self.cases[0]
        valid = case['gold_draft']
        tests = [('{', 'invalid_json'),
                 (json.dumps(dict(valid, extra=True)), 'invalid_contract'),
                 (json.dumps(dict(valid, predicate=65535)), 'invalid_catalog_reference')]
        for raw, category in tests:
            self.assertEqual(n.score_case(case, self.record(case, raw), self.binary)['category'], category)
        cross_graph = dict(valid, graph=1)
        self.assertEqual(n.score_case(case, self.record(case, json.dumps(cross_graph)), self.binary)['category'], 'invalid_catalog_reference')
        ambiguous = next(c for c in self.cases if c['task_family'] == 'identical_alias_collision')
        result = n.score_case(ambiguous, self.record(ambiguous, json.dumps(valid)), self.binary)
        self.assertEqual(result['category'], 'deterministic_preflight_block')
        self.assertTrue(result['false_positive'])
        self.assertFalse(result['model_abstention_correct'])
        abstained = n.score_case(ambiguous, self.record(ambiguous), self.binary)
        self.assertTrue(abstained['model_abstention_correct'])
        timed_out = n.score_case(ambiguous, dict(id=ambiguous['id'], runtime_status='timeout', raw_response='partial'), self.binary)
        self.assertEqual(timed_out['category'], 'runtime_timeout')
        self.assertFalse(timed_out['model_abstention_correct'])
        cancelled = n.score_case(ambiguous, dict(id=ambiguous['id'], runtime_status='cancelled'), self.binary)
        self.assertEqual(cancelled['category'], 'user_cancelled')
        self.assertFalse(cancelled['model_abstention_correct'])
        wrong_status = dict(version=n.VERSION, status='unsupported', rationale='Unknown meaning')
        self.assertFalse(n.score_case(ambiguous, self.record(ambiguous, json.dumps(wrong_status)), self.binary)['model_abstention_correct'])

    def test_answer_agreement_cannot_rescue_a_wrong_plan_and_cancellation_is_not_abstention(self):
        case = next(c for c in self.cases if c['task_family'] == 'explicit_no_match')
        table = n.read(n.STUDY / case['split'] / 'catalog.json')
        type_id = next(r['id'] for r in table['predicates'] if r['graph'] == 0 and r['iri'] == 'http://www.wikidata.org/prop/direct/P17')
        wrong = dict(case['gold_draft'], predicate=type_id)
        alternative = copy.deepcopy(case)
        alternative['gold_request']['template']['steps'][0]['predicate'] = 'http://www.wikidata.org/prop/direct/P17'
        dataset = n.Dataset()
        dataset.parse(n.STUDY / case['split'] / 'snapshot.nq', format='nquads')
        self.assertEqual(n.rows_and_witnesses(alternative, dataset)[0], case['full_bindings'])
        _, proposal = n.rust_preview(case, json.dumps(wrong), self.binary)
        # These distinct source paths both return the empty set. Structural
        # disagreement must remain visible independently of answer agreement.
        execution = dict(status='executed', plan=proposal['preview']['plan'],
                         snapshot_id=proposal['request']['snapshot_id'], scope=proposal['request']['scope'],
                         complete_within_scope=True, evidence_complete_for_returned_rows=True,
                         bindings=case['full_bindings'])
        saved = self.record(case, json.dumps(wrong), decision='approved',
                            approval_id=proposal['preview']['approval_id'], execution=execution)
        result = n.score_case(case, saved, self.binary)
        self.assertEqual(result['category'], 'valid_draft_semantically_wrong')
        self.assertFalse(result['structural_faithfulness'])
        self.assertTrue(result['exact_answer_set'])
        # No execution is performed by this test or scorer: result provenance is a saved-record claim.
        saved['execution']['complete_within_scope'] = False
        saved['execution']['evidence_complete_for_returned_rows'] = False
        clipped = n.score_case(case, saved, self.binary)
        self.assertFalse(clipped['exact_answer_set'])
        self.assertTrue(clipped['rows_truncated'])
        self.assertTrue(clipped['evidence_truncated'])
        cancelled = n.score_case(case, self.record(case, decision='cancelled'), self.binary)
        self.assertIsNone(cancelled['exact_answer_set'])
        self.assertFalse(cancelled['model_abstention_correct'])
        saved['decision'] = 'cancelled'
        with self.assertRaises(ValueError):
            n.score_case(case, saved, self.binary)

    def test_named_constant_direction_and_wrong_identifier_regressions(self):
        case = self.cases[0]
        missing = copy.deepcopy(case['gold_draft']); missing.pop('start')
        self.assertEqual(n.score_case(case, self.record(case, json.dumps(missing)), self.binary)['category'], 'invalid_contract')
        for change in [dict(direction='reverse'), dict(predicate=1000)]:
            draft = dict(case['gold_draft'], **change)
            result = n.score_case(case, self.record(case, json.dumps(draft)), self.binary)
            self.assertIn(result['category'], {'valid_draft_semantically_wrong', 'invalid_catalog_reference'})
        outcomes = [n.score_case(case, self.record(case, decision='cancelled'), self.binary)]
        summary = n.summarize(outcomes)
        self.assertEqual(summary['strict_answer_agreement'], dict(numerator=0, denominator=1, unmeasured=1))
        self.assertEqual(summary['cancellations'], 1)

    def test_no_match_injection_and_full_literal_types_are_retained(self):
        for split in ['development', 'evaluation']:
            selected = [c for c in self.cases if c['split'] == split]
            empty = next(c for c in selected if c['task_family'] == 'explicit_no_match')
            self.assertEqual(empty['full_bindings'], [])
            label = next(c for c in selected if c['task_family'] == 'malicious_label')
            self.assertTrue(any('DELETE WHERE' in r['step1']['value'] for r in label['full_bindings']))
            number = next(c for c in selected if c['task_family'] == 'city_identifier')
            self.assertEqual(number['full_bindings'][0]['step1']['datatype'], str(n.rdflib.XSD.integer))
            date = next(c for c in selected if c['task_family'] == 'inception')
            self.assertEqual(date['full_bindings'][0]['step1']['datatype'], str(n.rdflib.XSD.dateTime))

    def test_frozen_sources_splits_and_manifest(self):
        self.assertTrue(n.verify()['verified'])


if __name__ == '__main__':
    unittest.main()
