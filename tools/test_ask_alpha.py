"""Model-free benchmark, scorer, architecture and real browser regressions."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
import hashlib
import threading
import unittest
from unittest.mock import patch, MagicMock

from rdflib import Dataset
import ask_alpha_evaluation as e
import ask_alpha_trial as trial
import supervised_ask as ask


class Benchmark(unittest.TestCase):
    def test_source_and_authored_intent_are_separate_and_reproducible(self):
        e.verify()
        q, refs, source = e.b.build()
        for name, value in [('questions.json', q), ('references.json', refs), ('source.json', source)]:
            self.assertEqual(value, e.b.read(e.BENCH / name))
        self.assertEqual(len(q['cases']), 60)
        self.assertEqual(sum(r['language'] == 'nb' for r in q['cases']), 30)
        self.assertEqual(sum(r['expected_plan'] is not None for r in refs['cases']), 29)
        self.assertEqual(sum(r['semantically_determinate'] for r in refs['cases']), 42)
        self.assertFalse(any('expected' in key or 'answer' in key for row in q['cases'] for key in row))
        source_lines = (e.b.DATA / 'snapshot.nq').read_text().splitlines()
        self.assertEqual([f['nquad'] for f in source['facts']], source_lines)
        for ref in refs['cases']:
            if ref['expected_plan']:
                plan = ref['expected_plan']
                for key in ref['source_witnesses']:
                    line = next(f['nquad'] for f in source['facts'] if f['id'] == key)
                    dataset = Dataset()
                    dataset.parse(data=line, format='nquads')
                    s, p, o, g = next(iter(dataset.quads()))
                    self.assertEqual(str(g), plan['graph'])
                    self.assertEqual(str(p), plan['predicate'])
                    self.assertEqual(str(s if plan['direction'] == 'forward' else o), plan['start'])
                self.assertTrue(any(d['predicate'] == plan['predicate'] for d in source['definitions']))

    def test_question_only_packets_reproduce_without_references(self):
        original_read = e.b.read
        def no_refs(path):
            self.assertNotIn(path.name, ['references.json', 'retained-synthetic.json'])
            return original_read(path)
        with patch.object(e.b, 'read', side_effect=no_refs):
            self.assertEqual(e.prepare_packets(), e.packets())

    def test_deterministic_assembly_binds_graph_and_preserves_original_reverse_predicate(self):
        selection = e.packets()['alpha-01']['selection']
        fields = e.numeric(dict(start=e.b.Q+'Q279724', predicate=e.b.P+'P17', graph=e.b.W,
                                direction='reverse', output='values'), selection)
        choice = {k: fields[k] for k in ['start', 'predicate', 'direction']}
        draft = e.assemble(choice, selection)
        self.assertEqual({k: draft[k] for k in fields}, fields)
        for change in [dict(predicate=65535), dict(start=True), dict(direction='inverse'), dict(graph=1)]:
            with self.assertRaises(ValueError):
                e.assemble({**choice, **change}, selection)
        wrong_graph = copy.deepcopy(selection)
        next(r for r in wrong_graph['predicates'] if r['id'] == choice['predicate'])['graph'] = 1
        with self.assertRaises(ValueError):
            e.assemble(choice, wrong_graph)


class Scoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = e.b.read(e.BENCH / 'retained-synthetic.json')
        cls.report = e.score(cls.fixture)

    def test_scheduled_and_paired_denominators_and_missing_semantics(self):
        report = self.report
        self.assertEqual(report['paired']['completed_pairs'], 57)
        self.assertEqual(report['paired']['scheduled_pairs'], 60)
        arm = report['conditions']['synthetic_five_field']
        self.assertEqual(arm['summary']['scheduled'], 60)
        self.assertEqual(arm['summary']['five_field_scheduled'], dict(numerator=24, denominator=29))
        self.assertEqual(arm['summary']['five_field_completed'], dict(numerator=24, denominator=28))
        self.assertEqual(arm['summary']['retrieval'], dict(numerator=28, denominator=29))
        rows = {r['id']: r for r in arm['rows']}
        for key in ['alpha-02', 'alpha-04']:
            self.assertIsNone(rows[key]['five_field_agreement'])
            self.assertIsNone(rows[key]['model_status'])
        self.assertEqual(rows['alpha-08']['missing_numeric_vocabulary'], ['start'])
        self.assertEqual(rows['alpha-08']['model_status'], 'needs_clarification')
        self.assertTrue(rows['alpha-01']['wrong_but_executable'])
        self.assertTrue(rows['alpha-07']['wrong_but_executable'])
        self.assertFalse(rows['alpha-25']['rust']['accepted'])
        self.assertFalse(rows['alpha-05']['strict_valid'])
        self.assertFalse(rows['alpha-06']['strict_valid'])
        self.assertTrue(rows['alpha-47']['unresolved_candidate'])
        self.assertIsNone(rows['alpha-47']['five_field_agreement'])
        self.assertTrue(rows['alpha-26']['source_evidence_agreement'])
        text = e.markdown(report)
        self.assertIn('WRONG BUT EXECUTABLE', text)
        self.assertIn('missing numeric start', text)

    def test_duplicate_unknown_and_missing_observations(self):
        for row in [self.fixture['rows'][0], dict(id='not-scheduled', condition='synthetic_five_field', outcome='failed')]:
            with self.assertRaises(ValueError):
                e.score({**self.fixture, 'rows': self.fixture['rows'] + [row]})
        report = e.score(dict(origin='retained_local_model', conditions=['actual'], rows=[]))
        self.assertEqual(report['conditions']['actual']['summary']['outcomes'], {'unattempted': 60})

    def test_clipped_or_wrong_graph_answers_cannot_match_and_unresolved_is_not_gold(self):
        refs = {r['id']: r for r in e.b.read(e.BENCH / 'references.json')['cases']}
        measured = self.report['conditions']['synthetic_five_field']['rows'][25]
        observation = next(r for r in self.fixture['rows'] if r['id'] == 'alpha-26')
        for fields in [dict(complete_evidence=False), dict(snapshot_id='wrong'), dict(terms=[])]:
            row = copy.deepcopy(observation)
            row['answer_evidence'].update(fields)
            result = e.measure(refs['alpha-26'], row, e.packets()['alpha-26']['selection'], measured['rust'])
            self.assertFalse(result['source_evidence_agreement'])

    def test_runner_cannot_start_without_authorization_or_in_ci(self):
        with patch.object(trial.h, 'Runtime') as runtime:
            with self.assertRaises(ValueError):
                trial.run(False)
            with patch.dict(os.environ, CI='1'):
                with self.assertRaises(ValueError):
                    trial.run(True)
            runtime.assert_not_called()

    def test_fatal_runtime_timeout_stops_schedule_and_consumes_new_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            freeze, output, reg, ledger = root/'freeze', root/'run', root/'registration.json', root/'attempt.json'
            (root/'artifacts').mkdir()
            e.b.write(reg, dict(synthetic=True))
            cfg = dict(host_max_age_seconds=60)
            frozen = dict(runtime_config=cfg, runtime_identity=dict(synthetic='identity'))
            schedule = [dict(id=key, kind='semantic', constrained=True) for key in ['alpha-01', 'alpha-02']]
            e.b.write(freeze/'schedule.json', schedule)
            e.b.write(freeze/'token-counts.json', dict(models=dict(qwen35=dict(rows=[]))))
            for key in ['alpha-01', 'alpha-02']:
                e.b.write(freeze/'contexts'/(key+'.json'), e.packets()[key]['context'])
                e.b.write(freeze/'messages'/(key+'.json'), [dict(content='synthetic')])
            runtime = MagicMock()
            runtime.__enter__.return_value = runtime
            runtime.generation_attempts = runtime.generation_completed = runtime.candidate_bytes_received = 0
            runtime.startup_ms = 0
            def timeout(context, dest, **kwargs):
                runtime.generation_attempts += 1
                (dest/'proposal.txt').write_bytes(b'{"version":')
                raise TimeoutError('Synthetic 300-second failure; no model invoked')
            runtime.generate.side_effect = timeout
            def tokenizer(args, directory, *unused):
                e.b.write(directory/'token-counts.json', e.b.read(freeze/'token-counts.json'))
                return 0
            adapter = MagicMock()
            adapter.packet.side_effect = lambda question, language, saved: saved
            assets = dict(synthetic='identity', candidates=dict(qwen35=dict(preparation_receipt=dict(commands=[[], [], ['synthetic-python']]))))
            with patch.multiple(trial, ROOT=root, FREEZE=freeze, OUTPUT=output, REG=reg, LEDGER=ledger), \
                 patch.object(trial, 'verify', return_value=frozen), \
                 patch.object(trial.subprocess, 'check_output', return_value=reg.read_bytes()), \
                 patch.object(trial.a, 'assets', return_value=assets), \
                 patch.object(trial.a, 'bounded', side_effect=tokenizer), \
                 patch.object(trial.a, 'grammar_controls'), patch.object(trial.e, 'rust_preview', return_value=dict(accepted=True)), \
                 patch.object(trial.a, 'preflight', return_value=dict(captured_at=trial.datetime.now(trial.timezone.utc).isoformat(), blockers=[])), \
                 patch.object(trial.a, 'sample_rss'), patch.object(trial.h.d, 'resource_guard'), \
                 patch.object(trial.b, 'bundle', return_value=adapter), \
                 patch.object(trial.h, 'Runtime', return_value=runtime), \
                 patch.dict(os.environ, CI='', GITHUB_ACTIONS=''):
                state = trial.run(True)
                self.assertEqual(state['status'], 'blocked_or_failed')
                self.assertEqual([r['outcome'] for r in state['rows']], ['timed_out', 'unattempted'], state.get('failure'))
                self.assertTrue(state['rows'][0]['attempted'])
                self.assertEqual((output/'requests/alpha-01/proposal.txt').read_bytes(), b'{"version":')
                self.assertTrue((output/'checksums.json').exists())
                runtime.generate.assert_called_once()
                with self.assertRaises(ValueError):
                    trial.run(True)

    def test_frozen_trial_prompts_tokens_and_source_are_sealed_without_model_access(self):
        reg = e.b.read(trial.REG)
        self.assertEqual(e.b.sha(trial.ARCHIVE), reg['archive_sha256'])
        with tarfile.open(trial.ARCHIVE) as archive:
            files = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
        self.assertEqual({n: hashlib.sha256(raw).hexdigest() for n, raw in files.items() if n != 'checksums.json'},
                         json.loads(files['checksums.json']))
        frozen = json.loads(files['freeze.json'])
        self.assertEqual(frozen['source_commit'], reg['source_commit'])
        for name, digest in frozen['inputs'].items():
            original = subprocess.check_output(['git', 'show', frozen['source_commit'] + ':' + name], cwd=e.ROOT)
            self.assertEqual(hashlib.sha256(original).hexdigest(), digest, name)
        schedule = json.loads(files['schedule.json'])
        self.assertEqual(len(schedule), 64)
        self.assertEqual(len({r['id'] for r in schedule}), 64)
        counts = json.loads(files['token-counts.json'])['models']['qwen35']['rows']
        for request, receipt in zip(schedule, counts):
            self.assertEqual(request['id'], receipt['name'])
            row = receipt['columnar']
            self.assertEqual(len(row['tokens']), row['input_tokens'])
            self.assertEqual(hashlib.sha256(row['prompt'].encode()).hexdigest(), row['prompt_sha256'])
            self.assertLess(row['total_required'], 16384)
            context = json.loads(files['contexts/'+request['id']+'.json'])
            self.assertFalse({'expected_plan', 'answer_terms', 'source_witnesses'} & set(context))
        self.assertFalse(reg['inference_authorized'])
        self.assertEqual(reg['executions'], 0)


class Browser(unittest.TestCase):
    def test_saved_journey_expiry_transport_failure_and_real_rust_clipping(self):
        chrome = os.environ.get('CHROME_BINARY') or next((p for n in ('google-chrome', 'chromium', 'chromium-browser') if (p := shutil.which(n))), None)
        mac = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which('node'):
            if os.environ.get('REQUIRE_FIND_BROWSER') == '1':
                self.fail('Headless Chrome and Node required')
            self.skipTest('Headless Chrome / Node unavailable')
        servers, bundles, threads = [], [], []
        with tempfile.TemporaryDirectory() as temp, patch.object(ask.find, 'REVIEW_SECONDS', 2):
            directory = Path(temp)
            def make(policy, demo):
                bundle = ask.Bundle(e.ROOT/'target/debug/verity', ask.DATA/'snapshot.nq', 'nquads', policy,
                                    ask.DATA/'scope.json', ask.DATA/'discovery.json', saved_drafts_demo=demo)
                bundles.append(bundle)
                return bundle
            policy = directory / 'policy.json'
            e.b.write(policy, {**e.b.read(ask.DATA/'policy.json'), 'max_evidence': 1})
            demo = directory / 'saved-fixtures.json'
            adapter = make(policy, None)
            fixtures = []
            for question, language, predicate in [
                ('Which official websites does the University of Tromsø list?', 'en', 'P856'),
                ('Hvilke offisielle navn har Universitetet i Tromsø?', 'nb', 'P1448')]:
                packet = adapter.packet(question, language)
                fields = e.numeric(dict(start=e.b.Q+'Q279724', predicate=e.b.P+predicate, graph=e.b.W,
                                        direction='forward', output='values'), ask.replay.table(packet, 20))
                fixtures.append(dict(question=question, language=language, packet_id=packet['packet_id'],
                    raw_draft=json.dumps(dict(version='nl-ask-draft-v1', status='candidate', **fields,
                                               rationale='Synthetic restrictive-policy browser fixture'))))
            e.b.write(demo, dict(version='nl-ask-demo-v1', cases=fixtures))
            clipped = make(policy, demo)
            original_resolve = clipped.resolve
            def limit(proposal, start):
                result = original_resolve(proposal, start)
                if result and result['status'] == 'candidate' and proposal['packet']['request']['language'] == 'en':
                    result['request']['limit'] = 1
                    result['preview'] = clipped.ask(result['request'])
                return result
            clipped.resolve = limit
            main = make(ask.DATA/'policy.json', e.ROOT/'examples/nl-ask-v2/saved-drafts-demo.json')
            try:
                for bundle in [main, clipped]:
                    server = ask.Server(bundle)
                    servers.append(server)
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    threads.append(thread)
                    thread.start()
                subprocess.run(['node', str(e.ROOT/'tools/supervised_ask_browser.mjs'), chrome, servers[0].url],
                    check=True, timeout=120, env={**os.environ, 'ASK_ALPHA_BROWSER': '1', 'ASK_ALPHA_CLIPPED_URL': servers[1].url})
            finally:
                for server in servers:
                    server.shutdown()
                    server.server_close()
                for thread in threads:
                    thread.join()
                for bundle in bundles:
                    bundle.close()


if __name__ == '__main__':
    unittest.main()
