"""Lossless source binding, retained native token budgets, and synthetic-only runner."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_one_hop_v1h as v


class BudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = v.a.g.archive_files(v.RELEASE/'freeze.tar.gz')
        cls.counts = json.loads(cls.payload['tokenization/counts.json'])

    def test_lossless_roundtrip_preserves_every_role_id_source_and_missing_predicate(self):
        _, baseline = v.baseline()
        for name, raw in self.payload.items():
            if not name.startswith('contexts/'):
                continue
            old = json.loads(baseline[name])
            current = json.loads(raw)
            self.assertEqual(current,v.columns.context(old))
            for key in old:
                if key != 'packet':
                    self.assertEqual(current[key],old[key],(name,key))
            if 'packet' in old:
                self.assertEqual(json.dumps(v.columns.unpack(current['packet']),ensure_ascii=False),json.dumps(old['packet'],ensure_ascii=False))
            if not old['predicates']:
                with v.adapter():
                    self.assertTrue(v.a.grammar(current).startswith('root ::= clarification | unsupported'))
        original = json.loads(baseline['contexts/eva-20-oracle.json'])
        self.assertEqual(v.columns.context(original)['identity_collisions'],original['identity_collisions'])
        source = {'a': 'x'*40, 'b': 'x'*40, 'collision':['S0']}
        with self.assertRaisesRegex(ValueError,'Reserved'):
            v.columns.pack(source)

    def test_actual_pinned_token_receipts_cover_schedule_and_preserve_overflow(self):
        v.validate_counts(self.counts,['qwen35','gemma4'])
        for model,data in self.counts['models'].items():
            self.assertEqual(len(data['rows']),38)
            self.assertEqual(sum(r['kind']=='semantic_diagnostic' for r in data['rows']),36)
            self.assertTrue(data['native_parities_reproduced'])
            self.assertTrue(all(r['columnar']['total_required'] < 16384 for r in data['rows']))
            failed = next(r for r in data['rows'] if r['condition']=='retrieval' and r['name']=='smoke-eva-08')
            self.assertFalse(failed['original']['fits'])
            for row in data['rows']:
                for variant in ['original','columnar']:
                    self.assertEqual(sum(row[variant]['section_contributions'].values()),row[variant]['input_tokens'])
            if model=='qwen35':
                self.assertEqual(failed['original']['input_tokens'],18926)
                self.assertEqual(len(data['native_parities_reproduced']),36)
        tampered = copy.deepcopy(self.counts)
        row = tampered['models']['qwen35']['rows'][0]['columnar']
        row.update(tokens=[0]*15872,input_tokens=15872,total_required=16384,fits=True)
        row['tokens_sha256'] = hashlib.sha256(json.dumps(row['tokens'],separators=(',',':')).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'exceeds'):
            v.validate_counts(tampered,['qwen35'])

    def test_original_sources_archives_and_registration_are_immutable(self):
        registered = v.read(v.RELEASE/'registration.json')
        self.assertFalse(registered['inference_authorized'])
        self.assertFalse(registered['inference_performed'])
        self.assertEqual(v.sha(v.RELEASE/'freeze.tar.gz'),registered['archive_sha256'])
        self.assertEqual({n:hashlib.sha256(raw).hexdigest() for n,raw in self.payload.items() if n!='checksums.json'},
                         json.loads(self.payload['checksums.json']))
        frozen = registered['freeze_manifest']
        for name,digest in frozen['input_sha256'].items():
            self.assertEqual(v.sha(v.ROOT/name),digest,name)
        for directory in ['experiments/native-one-hop-v1f-diagnostic-r3','experiments/native-one-hop-v1f-diagnostic-r3-evidence']:
            p = v.ROOT/directory
            self.assertEqual(v.read(p/'checksums.json'),v.a.v.inventory(p))
        history = v.read(v.ROOT/'reports/issue-83-native-one-hop-v1f-diagnostic/historical-sha256.json')
        for name,digest in history.items():
            self.assertEqual(v.sha(v.ROOT/name),digest,name)

    def test_prompt_seal_has_no_operator_reference_dependency_or_semantic_prompt_change(self):
        poison = AssertionError('References must not be consulted while rendering')
        with patch.object(v.a.t,'cases',side_effect=poison):
            for name,raw in self.payload.items():
                if name.startswith('original-contexts/'):
                    old = json.loads(raw)
                    current = v.columns.context(old)
                    self.assertEqual(v.messages(current),json.loads(self.payload[name.replace('original-contexts/','messages/')]))
        base = v.read(v.ROOT/'experiments/native-one-hop-v1f-diagnostic-r3/registration.json')['freeze_manifest']['config']
        cfg = v.config()
        for field in ['prompt_file','grammar_file','host_gates','hardware','context_tokens','max_output_tokens','cpu_threads','gpu_layers','concurrency','stages']:
            self.assertEqual(cfg[field],base[field],field)
        self.assertEqual(v.read(v.ROOT/'experiments/native-one-hop-v1g/registration.json')['inference_performed'],False)

    def test_opt_in_ci_and_preload_budget_failure_prevent_weight_loading(self):
        with patch.object(v.a,'assets') as assets,patch.object(v,'Runtime') as runtime:
            with self.assertRaisesRegex(ValueError,'allow-inference'):
                v.run(Path('missing'),Path('missing'),'qwen35')
            with patch.dict('os.environ',{'CI':'1'}),self.assertRaisesRegex(ValueError,'forbidden in CI'):
                v.run(Path('missing'),Path('missing'),'qwen35',True)
            assets.assert_not_called()
            runtime.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'artifacts').mkdir()
            folder = root/'freeze'
            folder.mkdir()
            (folder/'checksums.json').write_bytes(self.payload['checksums.json'])
            cfg = v.config()
            frozen = json.loads(self.payload['freeze.json'])
            with patch.object(v,'ROOT',root),patch.object(v,'config',return_value=cfg), \
                 patch.object(v,'verify_registration',return_value=frozen), \
                 patch.object(v.a,'assets',return_value=frozen['runtime_identity']), \
                 patch.object(v,'count_tokens',side_effect=ValueError('preload overflow')), \
                 patch.object(v,'Runtime') as runtime,patch.dict('os.environ',{},clear=True):
                state = v.run(folder,root/'run','qwen35',True)
                runtime.assert_not_called()
            self.assertIn('preload overflow',state['error'])
            self.assertFalse(state['model_loaded'])
            self.assertEqual(state['generation_attempts'],0)
            self.assertTrue(all(not r['generation_attempted'] for r in state['diagnostic']['cases']))

    def test_native_parity_cache_guard_is_before_completion(self):
        runtime = v.Runtime(v.config(),Path('unused'),'qwen35',Path('unused'))
        runtime.allowed_prompts = {}
        with patch.object(v.a.Runtime,'template_parity',return_value=dict(prompt='changed',tokens=[1])), \
             self.assertRaisesRegex(ValueError,'pre-load'):
            runtime.template_parity({},Path('unused'))

    def test_synthetic_full_schedule_and_private_failure_keep_zero_execution_authority(self):
        for private in [False,True]:
            with self.subTest(private=private),tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root/'artifacts').mkdir()
                folder = root/'freeze'
                folder.mkdir()
                for name,raw in self.payload.items():
                    path = folder/name
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(raw)
                cfg = v.config()
                jobs = v.schedule()
                frozen = json.loads(self.payload['freeze.json'])
                counts = {'models':{'qwen35':self.counts['models']['qwen35']}}
                class FakeRuntime:
                    startup_ms = 1
                    generation_attempts = generation_completed = candidate_bytes_received = 0
                    def __init__(self,*args):pass
                    def __enter__(self):return self
                    def __exit__(self,*args):pass
                    def generate(self,context,dest,constrained=True,system=None):
                        self.generation_attempts+=1
                        draft = dict(version='nl-ask-draft-v1',status='unsupported',rationale='PRIVATE_CANARY' if private and self.generation_attempts==3 else 'synthetic transport')
                        if not constrained:draft['forbidden']=True
                        raw = json.dumps(draft).encode()
                        (dest/'proposal.txt').write_bytes(raw)
                        v.dump(dest/'completion-request.json',{'synthetic_only':True})
                        (dest/'prompt.txt').write_text(v.a.g.safe_user(context))
                        (dest/'completion.http.sse').write_bytes(b'data: '+raw+b'\n')
                        self.generation_completed+=1
                        self.candidate_bytes_received+=len(raw)
                        return dict(elapsed_ms=1)
                def sample(out,done,rss):rss.update(samples=1,peak_kib=100)
                host = dict(blockers=[],captured_at=datetime.now(timezone.utc).isoformat())
                with patch.object(v,'ROOT',root),patch.object(v,'config',return_value=cfg), \
                     patch.object(v,'schedule',return_value=jobs), \
                     patch.object(v,'verify_registration',return_value=frozen),patch.object(v,'verify',return_value=frozen), \
                     patch.object(v.a,'assets',return_value=frozen['runtime_identity']),patch.object(v,'count_tokens',return_value=counts), \
                     patch.object(v.a,'grammar_controls'),patch.object(v.a,'preflight',return_value=host), \
                     patch.object(v.a,'sample_rss',side_effect=sample),patch.object(v,'Runtime',FakeRuntime), \
                     patch.object(v.a,'grammar_check',side_effect=lambda text,*args:'forbidden' not in text), \
                     patch.object(v.a,'semantic_outcome',return_value=dict(model_status='unsupported',expected_status='candidate',field_agreement={})), \
                     patch.dict('os.environ',{},clear=True):
                    # The pinned control prompt is outside this temporary synthetic root.
                    (root/'configs').mkdir()
                    (root/cfg['control_prompt_file']).write_bytes((v.a.ROOT/cfg['control_prompt_file']).read_bytes())
                    state = v.run(folder,root/'run','qwen35',True)
                self.assertEqual(state['executions'],0)
                self.assertFalse(state['integration_authorized'])
                self.assertEqual(state['decision'],'INCONCLUSIVE_REVISE')
                if private:
                    self.assertEqual(state['status'],'blocked_or_failed')
                    self.assertIn('Private-scope',state['error'])
                    self.assertEqual(state['generation_attempts'],3)
                    self.assertTrue((root/'run/diagnostic/oracle/repeat-0/proposal.txt').exists())
                else:
                    self.assertEqual(state['status'],'completed_diagnostic',state.get('error'))
                    self.assertEqual(state['generation_attempts'],38)
                    self.assertEqual(state['diagnostic']['completed'],36)
                for path in (root/'run').rglob('rust-preview-command.json'):
                    self.assertEqual(v.read(path)[1],'nl-ask-preview')


if __name__ == '__main__':
    unittest.main()
