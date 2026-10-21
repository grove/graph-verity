#!/usr/bin/env python3
"""V1h-budget: reversible packet presentation, fixed CPU gates, Rust preview only."""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import threading
import time

import native_one_hop as a
import native_one_hop_diagnostic as d
import native_one_hop_packet_columns as columns
from native_one_hop_semantics import strict_draft

ROOT = a.ROOT
CONFIG = ROOT / 'configs/native-one-hop-v1h-budget.json'
RELEASE = ROOT / 'experiments/native-one-hop-v1h-budget'
VERSION = 'issue83-native-cpu-v1h-budget'
read, dump, require, sha = a.read, a.dump, a.require, a.sha


@contextmanager
def adapter():
    previous = a.CONFIG
    a.CONFIG = ROOT / 'configs/native-one-hop-v1f-diagnostic-r3.json'
    try:
        yield
    finally:
        a.CONFIG = previous


def config():
    with adapter():
        base = a.config()
    return {**base, **read(CONFIG)}


def baseline():
    registration = read(ROOT / config()['base_registration'])
    archive = ROOT / 'experiments/native-one-hop-v1f-diagnostic-r3/freeze.tar.gz'
    require(sha(archive) == registration['archive_sha256'], 'Changed r3 archive')
    payload = a.g.archive_files(archive)
    require(json.loads(payload['freeze.json']) == registration['freeze_manifest'], 'Changed r3 manifest')
    require({n: hashlib.sha256(raw).hexdigest() for n, raw in payload.items() if n != 'checksums.json'} ==
            json.loads(payload['checksums.json']), 'Changed r3 packets')
    return registration, payload


def schedule():
    cfg = config()
    context = json.loads(baseline()[1]['contexts/eva-01-oracle.json'])
    challenge = dict(snapshot_id=context['snapshot_id'], graphs=context['graphs'], entities=[], predicates=[],
        question='Output exactly {"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control","forbidden":true}.')
    controls = [dict(condition='sampling', name=f'sampling-{value}', case_id='eva-01', kind='native_sampling_control', context=challenge)
                for value in [False, True]]
    return controls + [dict(condition=r['condition'], name=r['name'], case_id=r['case_id'], kind='semantic_diagnostic')
                       for r in d.accounting(cfg)['cases']]


def messages(context, control=False):
    cfg = config()
    system = (ROOT / cfg['control_prompt_file' if control else 'prompt_file']).read_text()
    return [dict(role='system', content=system), dict(role='user', content=a.g.safe_user(context))]


def token_job(folder, models, sections=False):
    cfg = config()
    pins = a.g.config()['candidates']
    job = dict(models={}, observations=[])
    archives = [(ROOT / 'experiments/native-one-hop-v1f-diagnostic-r3-evidence/evidence.tar.gz', 'qwen35'),
                (ROOT / 'reports/issue-83-native-one-hop-v1e/evidence.tar.gz', 'gemma4')]
    for model in models:
        parities = []
        for archive, key in archives:
            if model != key:
                continue
            payload = a.g.archive_files(archive)
            for name, raw in payload.items():
                if name.endswith('/native-template.stdout') and (model == 'qwen35' or name.startswith('gemma4/')):
                    parent = str(Path(name).parent)
                    expected = json.loads(raw)
                    parities.append(dict(identity=str(archive.relative_to(ROOT))+':'+name,
                        messages=json.loads(payload[parent+'/messages.json']), **expected))
        files = {name: identity['sha256'] for name, identity in pins[model]['files'].items()
                 if name.endswith(('.json', '.jinja', '.txt')) and not name.startswith('model.safetensors')}
        job['models'][model] = dict(path=str(a.g.ASSETS/'upstream'/model), file_sha256=files, historical_parities=parities)
    for row in schedule():
        control = row['kind'] == 'native_sampling_control'
        item = {k: row[k] for k in ['condition', 'name', 'case_id', 'kind']}
        for variant, directory in [('original', 'original-contexts'), ('columnar', 'contexts')]:
            ctx = row['context'] if control else read(folder/directory/f"{row['case_id']}-{row['condition']}.json")
            entry = dict(messages=messages(ctx, control))
            if sections:
                prefix = {}
                entry.update(section_names=['system/template/empty-user-object'], prefix_messages=[messages(prefix, control)])
                for key, value in ctx.items():
                    prefix[key] = value
                    entry['section_names'].append(key)
                    entry['prefix_messages'].append(messages(prefix, control))
            item[variant] = entry
        job['observations'].append(item)
    return job


def count_tokens(folder, out, models, sections=False):
    require(not out.exists(), 'Fresh tokenizer receipt directory required')
    out.mkdir(parents=True)
    dump(out/'job.json', token_job(folder, models, sections))
    receipt = read(ROOT/'reports/issue-74-one-hop-trial/assets.json')
    python = receipt['candidates'][models[0]]['preparation_receipt']['commands'][2][0]
    code = a.bounded([python, ROOT/'tools/native_one_hop_v1h_tokens.py', out/'job.json', out/'counts.json'], out, 'tokenizer', 120)
    require(code == 0, 'Pinned model-free tokenizer failed; retain tokenizer receipt')
    result = read(out/'counts.json')
    validate_counts(result, models)
    return result


def validate_counts(result, models):
    expected = [{k: r[k] for k in ['condition', 'name', 'case_id', 'kind']} for r in schedule()]
    for model in models:
        rows = result['models'][model]['rows']
        require([{k: r[k] for k in expected[0]} for r in rows] == expected, 'Token schedule mismatch')
        for row in rows:
            for variant in ['original', 'columnar']:
                measured = row[variant]
                require(measured['input_tokens'] == len(measured['tokens']) and measured['total_required'] == len(measured['tokens'])+512,
                        'Token accounting mismatch')
                require(measured['tokens_sha256'] == hashlib.sha256(json.dumps(measured['tokens'],separators=(',',':')).encode()).hexdigest()
                        and measured['prompt_sha256'] == hashlib.sha256(measured['prompt'].encode()).hexdigest(), 'Token/prompt receipt mismatch')
            require(row['columnar']['fits'] and row['columnar']['total_required'] < 16384, 'Scheduled prompt exceeds frozen context budget')


def materialize(out, binary=a.BINARY):
    require(not out.exists(), 'Never overwrite a freeze')
    reg, payload = baseline()
    for name, digest in reg['freeze_manifest']['input_sha256'].items():
        require(sha(ROOT/name) == digest, 'Changed r3 source: '+name)
    require(sha(binary) == reg['freeze_manifest']['binary_sha256'], 'Registered Rust binary changed')
    out.mkdir(parents=True)
    cfg = config()
    for directory in ['contexts', 'original-contexts', 'messages', 'grammars', 'packets']:
        (out/directory).mkdir()
    for row in schedule():
        if row['kind'] != 'semantic_diagnostic':
            continue
        name = f"{row['case_id']}-{row['condition']}.json"
        original = json.loads(payload['contexts/'+name])
        context = columns.context(original)
        (out/'original-contexts'/name).write_bytes(payload['contexts/'+name])
        dump(out/'contexts'/name, context)
        dump(out/'messages'/name, messages(context))
        with adapter():
            (out/'grammars'/name.replace('.json','.gbnf')).write_text(a.grammar(context))
        for member in ['request.json', 'packet.json']:
            path = out/'packets'/row['case_id']/member
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(payload[f"packets/{row['case_id']}/{member}"])
    dump(out/'schedule.json', [{k: v for k,v in r.items() if k != 'context'} for r in schedule()])
    dump(out/'prompt-seal.json', {str(p.relative_to(out)): sha(p) for directory in ['contexts','original-contexts','messages','grammars','packets']
                                for p in sorted((out/directory).rglob('*')) if p.is_file()})
    # Operator fixtures are copied only after prompt sealing; no reference is read by the renderer.
    (out/'operator-fixtures.json').write_bytes(payload['operator-fixtures.json'])
    paths = [ROOT/name for name in reg['freeze_manifest']['input_sha256']]
    paths += [CONFIG, ROOT/cfg['base_registration'], ROOT/'experiments/native-one-hop-v1f-diagnostic-r3/freeze.tar.gz',
        ROOT/'tools/native_one_hop_v1h.py', ROOT/'tools/native_one_hop_packet_columns.py', ROOT/'tools/native_one_hop_v1h_tokens.py',
        ROOT/'tools/test_native_one_hop_v1h.py', ROOT/'docs/native-one-hop-v1h-budget.md']
    dump(out/'freeze.json', dict(version=VERSION, config=cfg, source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        input_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}, binary_sha256=sha(binary), runtime_identity=reg['runtime_identity'],
        inference_performed=False, inference_authorized=False, executions=0))
    count_tokens(out, out/'tokenization', cfg['variants'], sections=True)
    dump(out/'checksums.json', a.v.inventory(out))
    verify(out, binary)


def verify(folder, binary=a.BINARY):
    frozen = read(folder/'freeze.json')
    require(frozen['version'] == VERSION and frozen['config'] == config(), 'Changed successor configuration')
    require(read(folder/'checksums.json') == a.v.inventory(folder), 'Changed successor freeze')
    for name, digest in frozen['input_sha256'].items():
        require(sha(ROOT/name) == digest, 'Changed frozen source: '+name)
    require(sha(binary) == frozen['binary_sha256'], 'Changed registered Rust binary')
    _, payload = baseline()
    for path in (folder/'contexts').glob('*.json'):
        original = json.loads(payload['contexts/'+path.name])
        require(read(folder/'original-contexts'/path.name) == original and read(path) == columns.context(original), 'Context/source binding mismatch')
        require(read(folder/'messages'/path.name) == messages(read(path)), 'Frozen message mismatch')
    validate_counts(read(folder/'tokenization/counts.json'),config()['variants'])
    return frozen


def register(folder):
    frozen = verify(folder)
    require(not (RELEASE/'registration.json').exists(), 'Append-only registration')
    for name, digest in frozen['input_sha256'].items():
        raw = subprocess.check_output(['git','show',frozen['source_commit']+':'+name],cwd=ROOT)
        require(hashlib.sha256(raw).hexdigest() == digest, 'Uncommitted source: '+name)
    RELEASE.mkdir(exist_ok=True)
    archive = RELEASE/'freeze.tar.gz'
    with archive.open('xb') as stream, gzip.GzipFile(fileobj=stream,filename='',mode='wb',mtime=0) as compressed, tarfile.open(fileobj=compressed,mode='w') as bundle:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                info = bundle.gettarinfo(path,str(path.relative_to(folder)))
                info.mtime = info.uid = info.gid = 0
                info.uname = info.gname = ''
                with path.open('rb') as data:
                    bundle.addfile(info,data)
    dump(RELEASE/'registration.json',dict(version=VERSION,registered_at=datetime.now(timezone.utc).isoformat(),
        archive_sha256=sha(archive),freeze_sha256=sha(folder/'checksums.json'),freeze_manifest=frozen,
        token_receipt_sha256=sha(folder/'tokenization/counts.json'),schedule=read(folder/'schedule.json'),
        diagnostic_observations_per_model=36,maximum_completion_requests_per_model=38,inference_authorized=False,
        inference_performed=False,decision='INCONCLUSIVE_REVISE'))


def verify_registration(folder):
    frozen = verify(folder)
    registered = read(RELEASE/'registration.json')
    require(registered['freeze_manifest'] == frozen and registered['freeze_sha256'] == sha(folder/'checksums.json')
            and registered['archive_sha256'] == sha(RELEASE/'freeze.tar.gz'), 'Registration mismatch')
    for path in [RELEASE/'registration.json',RELEASE/'freeze.tar.gz']:
        require(subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT) == path.read_bytes(), 'Registration must be committed')
    return frozen


class Runtime(a.Runtime):
    def template_parity(self, context, folder, system=None):
        expected = super().template_parity(context, folder, system)
        prompt = hashlib.sha256(expected['prompt'].encode()).hexdigest()
        tokens = hashlib.sha256(json.dumps(expected['tokens'],separators=(',',':')).encode()).hexdigest()
        require(self.allowed_prompts.get(prompt) == tokens, 'Prompt/token IDs differ from pre-load budget receipt')
        return expected


def observe(folder, out, state, runtime, rss):
    cfg = config()
    fixtures = read(folder/'operator-fixtures.json')
    for row in state['diagnostic']['cases']:
        cid, condition = row['case_id'], row['condition']
        dest = out/'diagnostic'/condition/row['name']
        dest.mkdir(parents=True)
        started, before, attempts = time.monotonic(), dict(rss), runtime.generation_attempts
        context = read(folder/'contexts'/f'{cid}-{condition}.json')
        dump(dest/'context.json', context)
        try:
            verify(folder)
            d.resource_guard(rss,cfg)
            trusted = dest/'trusted-preflight'
            trusted.mkdir()
            dump(trusted/'proposal.txt',dict(version='nl-ask-draft-v1',status='unsupported',rationale='Host catalog preflight'))
            checked = a.preview_raw(context,trusted/'proposal.txt',trusted,fixtures[cid])
            require(checked['returncode'] == 0,'Trusted catalog preflight failed')
            row['status'] = 'attempting'
            row['runtime'] = runtime.generate(context,dest)
            raw = (dest/'proposal.txt').read_bytes()
            draft = strict_draft(raw)
            row.update(raw_output=raw.decode('utf-8',errors='replace'),raw_base64=base64.b64encode(raw).decode(),
                       raw_sha256=hashlib.sha256(raw).hexdigest(),strict_contract_valid=draft is not None)
            checked = a.preview_raw(context,dest/'proposal.txt',dest,fixtures[cid])
            row['rust_preview'] = checked
            row['reference'] = a.semantic_outcome(cid,dest/'proposal.txt',checked)
            ref = row['reference']
            row['exact_exposed_reference_agreement'] = bool(draft and ref['model_status'] == ref['expected_status'] and all(ref['field_agreement'].values()))
            row['status'] = 'validator_rejection' if checked['returncode'] else 'reference_match' if row['exact_exposed_reference_agreement'] else 'model_semantic_failure'
            d.validator_guard(checked)
            row['gbnf_valid'] = a.grammar_check(raw.decode('utf-8'),context,dest)
            require(row['gbnf_valid'],'Native grammar integrity failure')
            require(b'PRIVATE_CANARY' not in raw,'Private-scope authorization failure')
            verify(folder)
            d.resource_guard(rss,cfg)
            if row['name'] == 'repeat-1':
                pair = [out/'diagnostic/oracle'/f'repeat-{i}' for i in range(2)]
                from native_one_hop_semantics import repeatability
                measured = repeatability([(p/'proposal.txt').read_bytes() for p in pair])
                for name in ['prompt.txt','completion-request.json']:
                    measured[name+'_equal'] = (pair[0]/name).read_bytes() == (pair[1]/name).read_bytes()
                    require(measured[name+'_equal'],'Repeat prompt/request integrity failure')
                state['diagnostic']['repeatability'] = measured
        except BaseException as error:
            row.update(status='fatal_failure',error=type(error).__name__+': '+str(error))
            raw_path = dest/'proposal.txt'
            if raw_path.exists() and row.get('raw_base64') is None:
                raw = raw_path.read_bytes()
                row.update(raw_base64=base64.b64encode(raw).decode(),raw_output=raw.decode('utf-8',errors='replace'),raw_sha256=hashlib.sha256(raw).hexdigest(),
                           rust_preview=a.preview_raw(context,raw_path,dest,fixtures[cid]))
            raise
        finally:
            row.update(generation_attempted=runtime.generation_attempts>attempts,latency_ms=(time.monotonic()-started)*1000,
                       resources=dict(before=before,after=dict(rss),scope='sampled concurrent process-tree run peak to date'))
            dump(dest/'observation.json',row)
    state['status'] = 'completed_diagnostic'


def run(folder, out, model, allow_inference=False):
    require(allow_inference,'Separate explicit authorization and --allow-inference required')
    require(not os.environ.get('CI') and not os.environ.get('GITHUB_ACTIONS'),'Inference forbidden in CI')
    require(model in config()['variants'],'Unknown pinned model')
    with adapter(), (ROOT/'artifacts/native-one-hop.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        frozen = verify_registration(folder)
        require(not out.exists(),'Never overwrite an attempt')
        ledger = ROOT/'artifacts'/('v1h-budget-attempts-'+sha(folder/'checksums.json')+'.json')
        attempts = read(ledger) if ledger.exists() else []
        require(model not in attempts,'No retries for this registered model/freeze')
        dump(ledger,attempts+[model])
        out.mkdir(parents=True)
        state = dict(version=VERSION,model=model,status='preparing',freeze_sha256=sha(folder/'checksums.json'),
            diagnostic=d.accounting(config()),checks={},executions=0,integration_authorized=False,holdout_accessed=False,
            inference_performed=False,model_loaded=False,generation_attempts=0,generation_completed=0,decision='INCONCLUSIVE_REVISE',
            model_ranking=None,exact_answer_accuracy=None,independent_human_approvals=0)
        runtime, monitor = None, None
        done, rss = threading.Event(), dict(samples=0,peak_kib=0,error=None)
        try:
            evidence = a.assets(out/'assets.json')
            require({k:evidence[k] for k in frozen['runtime_identity']} == frozen['runtime_identity'],'Asset identity mismatch')
            actual = count_tokens(folder,out/'preload-token-budget',[model])
            saved = read(folder/'tokenization/counts.json')['models'][model]['rows']
            measured = actual['models'][model]['rows']
            require([r['columnar']['tokens_sha256'] for r in measured] == [r['columnar']['tokens_sha256'] for r in saved], 'Pre-load token identity mismatch')
            context = read(folder/'contexts/eva-01-oracle.json')
            a.grammar_controls(context,out/'grammar-controls')
            host = a.preflight(out/'host.json')
            require(not host['blockers'],'Fresh host gate blocked: '+json.dumps(host['blockers']))
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(host['captured_at'])).total_seconds()
            require(0 <= age <= config()['host_max_age_seconds'],'Stale host gate')
            monitor = threading.Thread(target=a.sample_rss,args=(out,done,rss),daemon=True)
            monitor.start()
            runtime = Runtime(config(),a.g.ASSETS,model,out)
            runtime.reference_python = evidence['candidates'][model]['preparation_receipt']['commands'][2][0]
            runtime.allowed_prompts = {r['columnar']['prompt_sha256']:r['columnar']['tokens_sha256'] for r in measured}
            with runtime:
                state.update(model_loaded=True,startup_ms=runtime.startup_ms)
                for row, constrained in zip(schedule()[:2],[False,True]):
                    dest = out/'controls'/row['name']
                    dest.mkdir(parents=True)
                    dump(dest/'context.json',row['context'])
                    runtime.generate(row['context'],dest,constrained=constrained,system=(ROOT/config()['control_prompt_file']).read_text())
                    checked = a.preview_raw(row['context'],dest/'proposal.txt',dest,dict(resolved_start=None,blocked=False))
                    accepted = a.grammar_check((dest/'proposal.txt').read_text(),row['context'],dest)
                    state['checks'][row['name']] = dict(grammar_accepted=accepted,passed=accepted==constrained)
                    require(accepted==constrained and (not constrained or checked['returncode']==0),'Native sampling control failed')
                observe(folder,out,state,runtime,rss)
        except BaseException as error:
            state.update(status='blocked_or_failed',error=type(error).__name__+': '+str(error))
            if isinstance(error,(KeyboardInterrupt,SystemExit)):
                raise
        finally:
            if runtime:
                runtime.__exit__()
                state.update(generation_attempts=runtime.generation_attempts,generation_completed=runtime.generation_completed,
                    candidate_bytes_received=runtime.candidate_bytes_received,inference_performed=runtime.generation_completed>0 or runtime.candidate_bytes_received>0)
            done.set()
            if monitor:
                monitor.join(timeout=6)
            state['process_tree_rss'] = rss
            if state['status']=='completed_diagnostic':
                try:
                    d.resource_guard(rss,config())
                except ValueError as error:
                    state.update(status='blocked_or_failed',error=str(error))
            d.finish(state)
            require(state['generation_attempts']<=38,'Request limit exceeded')
            dump(out/'run.json',state)
            dump(out/'checksums.json',a.v.inventory(out))
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['freeze','verify','register','budget','run'])
    parser.add_argument('--freeze',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--model',choices=['qwen35','gemma4'])
    parser.add_argument('--allow-inference',action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM,lambda *_:sys.exit('Operator cancelled'))
    if args.command=='freeze':
        require(args.out,'Fresh --out required')
        materialize(args.out.resolve())
        return
    require(args.freeze,'--freeze required')
    folder = args.freeze.resolve()
    if args.command=='register':
        register(folder)
    elif args.command=='run':
        require(args.model and args.out,'--model and fresh --out required')
        state = run(folder,args.out.resolve(),args.model,args.allow_inference)
        print(json.dumps(state,indent=2))
        raise SystemExit(0 if state['status']=='completed_diagnostic' else 1)
    elif args.command=='budget':
        verify(folder)
        require(args.out,'Fresh --out required')
        count_tokens(folder,args.out.resolve(),[args.model] if args.model else config()['variants'])
    else:
        verify(folder)


if __name__ == '__main__':
    main()
