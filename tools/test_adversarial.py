"""Model-free cross-engine fixture, grounding and reporting checks for issue #9."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from rdflib import Dataset

from adversarial import category
from local_parser import ADVERSARIAL_DATASETS, ROOT, chat, config, oracle_context
from verify_worldcities_benchmark import normalized, rows


class AdversarialTests(unittest.TestCase):
    def test_frozen_fixtures_in_both_query_engines_and_authorized_prompt(self):
        cli = ROOT / 'target/debug/verity'
        subprocess.run(['cargo', 'build', '--locked', '--offline', '-p', 'verity_cli'], cwd=ROOT, check=True,
                       capture_output=True)
        families = []
        for name, split in ADVERSARIAL_DATASETS:
            benchmark = json.loads((ROOT / f'benchmarks/{name}.json').read_text())
            data = ROOT / f'data/{name}/snapshot.nq'
            policy = ROOT / f'data/{name}/policy.json'
            store = Dataset()
            store.parse(data=data.read_bytes(), format='nquads')
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                subprocess.run([str(cli), 'evaluate', str(data), 'nquads', str(policy),
                                str(ROOT / f'benchmarks/{name}.json'), split, str(out)],
                               check=True, capture_output=True)
                report = json.loads((out / 'report.json').read_text())
                self.assertEqual(report['passed'], 15)
                for c in benchmark['cases']:
                    if c['gold']:
                        self.assertEqual(normalized(rows(store, c['reference_sparql'])), normalized(c['expected_bindings']), c['id'])
                    scope = out / 'scope.json'
                    scope.write_text(json.dumps(c['scope']))
                    catalog = json.loads(subprocess.check_output([str(cli), 'catalog', str(data), 'nquads', str(policy), str(scope)]))
                    request = dict(question=c['question'], catalog=catalog, context_trust='untrusted')
                    context = oracle_context(request, c)
                    prompt = chat(config(), context)
                    self.assertNotIn('PRIVATE_', json.dumps(request) + prompt)
                    self.assertNotIn('COMMENT_INJECTION_CANARY', json.dumps(request) + prompt)
                    self.assertEqual(prompt.count('<|im_start|>system'), 1)
                    if c['id'].startswith('injection-'):
                        self.assertEqual(len(context['vocabulary'][next(p['from']['iri'] for p in c['gold']['patterns'])]['labels']), 2)
                    if c['id'] == 'alias':
                        self.assertEqual(sum(any(l['text'] == 'Felles AS' for l in e['labels']) for e in context['vocabulary'].values()), 2)
                    question, response = out / 'question.txt', out / 'response.json'
                    question.write_text(c['question'])
                    proposal = ({'status': 'candidate', 'plan': c['gold']} if c['gold'] else
                                {'status': c['expected_status'], 'reason': 'Recorded expected behavior, not inference'})
                    response.write_text(json.dumps({'version': 1, 'proposal': proposal}))
                    replayed = json.loads(subprocess.check_output([str(cli), 'replay', str(data), 'nquads', str(policy),
                        str(scope), str(question), str(response)]))
                    self.assertEqual(replayed['status'], 'executed' if c['gold'] else 'abstained')
                    self.assertNotIn('PRIVATE_', json.dumps(replayed))
            families.append([(c['id'], c['family'], c['expected_status']) for c in benchmark['cases']])
        self.assertEqual(families[0], families[1])

    def test_false_positives_do_not_hide_abstentions_or_rejections(self):
        correct = dict(expected_status='executed', expected_abstention=False, actual_abstention=False,
                       proposal_status='candidate', exact_result_set=True, execution={'complete_within_scope': True})
        wrong = {**correct, 'exact_result_set': False}
        truncated = {**correct, 'execution': {'complete_within_scope': False}}
        abstained = {**correct, 'proposal_status': 'unsupported', 'actual_abstention': True, 'execution': None}
        unsafe_answer = {**correct, 'expected_status': 'needs_clarification', 'expected_abstention': True}
        rejected = {**unsafe_answer, 'execution': None}
        result = category([correct, wrong, truncated, abstained, unsafe_answer, rejected], True)
        self.assertEqual(result['false_positive']['numerator'], 3)
        self.assertEqual(result['false_positive']['denominator'], 6)
        self.assertEqual(result['false_abstention']['value'], .25)
        self.assertEqual(result['failure_to_abstain']['value'], 1)
        self.assertEqual(result['safe_abstention_on_ambiguous_or_unsupported']['value'], 0)
        self.assertNotIn('false_positive', category([correct], False))


if __name__ == '__main__':
    unittest.main()
