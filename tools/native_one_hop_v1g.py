#!/usr/bin/env python3
"""V1g executable diagnostic: frozen membership, common renderer, preview only."""
import argparse
import base64
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import gzip
import json
from importlib.metadata import version as package_version
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys

import tempfile
import tarfile
import threading
import time

from rdflib import Dataset

import analyze_v1f as analysis
import native_one_hop as a
import native_one_hop_context as presentation
import native_one_hop_diagnostic as diagnostic
from native_one_hop_semantics import PLAN_FIELDS, repeatability, strict_draft

ROOT, STUDY = a.ROOT, a.t.STUDY
DESIGN = ROOT / 'experiments/native-one-hop-v1g'
CAPTURE = ROOT / 'reports/issue-82-neighborhood/capture'
HISTORICAL = a.t.REPORT / 'freeze'
BRIDGE = ROOT / 'target/debug/examples/v1g_preview'
VERSION = 'native-one-hop-v1g-execution-v1'
CONDITIONS = ['oracle', 'BM25-v1', 'neighborhood-v2']
read, dump, require, sha = a.read, a.dump, a.require, a.sha


def inventory(folder):
    return {k: v for k, v in analysis.inventory(folder).items() if k != 'execution-registration.json'}


def runtime_identity():
    return {**read(a.t.REPORT / 'assets.json'), 'runtime_source_tree_verified': True,
            'original_licenses_verified': True}


@contextmanager
def adapter():
    """Scope delegation to the unchanged v1f CPU/host/grammar implementation."""
    previous = a.CONFIG
    a.CONFIG = ROOT / 'configs/native-one-hop-v1f-diagnostic.json'
    try:
        yield
    finally:
        a.CONFIG = previous


def config():
    with adapter():
        cfg = a.config()
    return {**cfg, 'version': VERSION, 'stages': CONDITIONS,
            'fixture_file': None, 'maximum_completion_requests_per_model': 94}


def schedule(questions):
    return ([dict(condition='oracle', name=f'repeat-{i}', case_id='eva-01') for i in range(2)] +
            [dict(condition=c, name=q['id'], case_id=q['id']) for c in CONDITIONS for q in questions])


def accounting(questions):
    return dict(cases=[dict(**s, status='unattempted', generation_attempted=False, raw_output=None,
                           raw_base64=None, raw_sha256=None, rust_preview=None, gbnf_valid=None,
                           latency_ms=None, runtime=None, resources=None) for s in schedule(questions)],
                repeatability=None, diagnostic_only=True, semantic_go=False)


def source_data():
    return a.t.n.parse_rdf(Dataset(), STUDY / 'snapshot.nq', format='nquads')


def render(oracle, data, discovery, packet=None):
    context = copy.deepcopy(oracle)
    context.pop('packet', None)
    context['source_provenance'] = discovery['graphs']
    if packet is not None:
        graphs = {r['id']: r['iri'] for r in oracle['graphs']}
        for collection in ['entities', 'predicates']:
            retained = {(r['graph'], r['iri']) for r in packet[collection]['candidates']}
            context[collection] = [r for r in oracle[collection] if (graphs[r['graph']], r['iri']) in retained]
            require({(graphs[r['graph']], r['iri']) for r in context[collection]} == retained,
                    'Every retained graph/IRI/role must have an original numeric ID')
    return presentation.language_view(presentation.enrich(context, oracle, data))


def binding(context, condition, request, budget, packet, fixture):
    selection = {k: context[k] for k in ['snapshot_id', 'graphs']}
    for collection in ['entities', 'predicates']:
        selection[collection] = [{k: r[k] for k in ['id', 'graph', 'iri']} for r in context[collection]]
    available = {r['id'] for r in selection['entities']}
    selection.update(resolved_start=fixture['resolved_start'] if fixture['resolved_start'] in available else None,
                     blocked=fixture['blocked'], limit=100)
    return dict(condition=condition, request=request, budget=budget,
                saved_packet_id=packet['packet_id'] if packet else None, selection=selection)


def preview(bound, packet_path, raw_path, out, bridge=BRIDGE):
    dump(out / 'binding.json', bound)
    args = [bridge, STUDY / 'snapshot.nq', STUDY / 'policy.json', STUDY / 'scope.json',
            STUDY / 'discovery.json', out / 'binding.json', packet_path, raw_path]
    code = a.bounded(args, out, 'rust-preview', 30)
    result = dict(returncode=code, stdout=(out / 'rust-preview.stdout').read_text(),
                  stderr=(out / 'rust-preview.stderr').read_text())
    dump(out / 'rust.json', result)
    return result


def packet_path(folder, cid, condition):
    return folder / 'packets' / cid / {'oracle': 'oracle.bin', 'BM25-v1': 'v1.json', 'neighborhood-v2': 'v2.json'}[condition]


def materialize(out, binary=a.BINARY, bridge=BRIDGE):
    require(not out.exists(), 'Never overwrite an execution freeze')
    for name, digest in read(DESIGN / 'registration.json')['input_sha256'].items():
        require(sha(ROOT / name) == digest, 'Changed design input: ' + name)
    require(read(CAPTURE / 'checksums.json') == a.v.inventory(CAPTURE), 'Changed #82 capture')
    require(read(HISTORICAL / 'checksums.json') == a.v.inventory(HISTORICAL), 'Changed #74 freeze')
    questions = read(HISTORICAL / 'questions.json')['questions']
    require([q['id'] for q in questions] == [f'eva-{i:02}' for i in range(1, 31)], 'Frozen 30-case order changed')
    out.mkdir(parents=True)
    for directory in ['contexts', 'packets', 'bindings', 'messages', 'grammars']:
        (out / directory).mkdir()
    dump(out / 'questions.json', questions)
    budget = read(CAPTURE / 'budget.json')
    discovery = read(STUDY / 'discovery.json')
    data = source_data()
    system = (ROOT / config()['prompt_file']).read_text()
    for q in questions:
        cid = q['id']
        dest = out / 'packets' / cid
        dest.mkdir()
        for name in ['request.json', 'v1.json', 'v2.json']:
            (dest / name).write_bytes((CAPTURE / cid / name).read_bytes())
        (dest / 'oracle.bin').write_bytes(b'')
        require((dest / 'v1.json').read_bytes() == (HISTORICAL / 'retrieval' / cid / 'packet.json').read_bytes(),
                'BM25-v1 must be byte identical to #74')
        request = read(dest / 'request.json')
        require((request['question'], request['language']) == (q['question'], q['language']), 'Question binding changed')
        oracle = read(HISTORICAL / 'contexts' / f'{cid}-oracle.json')
        for condition in CONDITIONS:
            packet = None if condition == 'oracle' else read(packet_path(out, cid, condition))
            context = render(oracle, data, discovery, packet)
            dump(out / 'contexts' / f'{cid}-{condition}.json', context)
            dump(out / 'messages' / f'{cid}-{condition}.json', [dict(role='system', content=system),
                                                              dict(role='user', content=a.g.safe_user(context))])
            with adapter():
                (out / 'grammars' / f'{cid}-{condition}.gbnf').write_text(a.grammar(context))
    # Prompts are sealed before references/operator fixtures are read. They never affect membership.
    dump(out / 'prompt-seal.json', {str(p.relative_to(out)): sha(p) for directory in ['contexts', 'messages', 'grammars', 'packets']
                                  for p in sorted((out / directory).rglob('*')) if p.is_file()})
    cases = a.t.cases()
    dump(out / 'references.json', cases)
    fixtures = {c['id']: dict(resolved_start=c['resolved_start'], blocked=c['preflight_blocked'],
                             origin='AI-authored frozen operator fixture; not model output') for c in cases}
    dump(out / 'operator-fixtures.json', fixtures)
    with tempfile.TemporaryDirectory(prefix='v1g-preflight-') as temp:
        check = Path(temp)
        raw = check / 'proposal.txt'
        raw.write_bytes(b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"trusted preflight"}')
        for q in questions:
            cid = q['id']
            for condition in CONDITIONS:
                context = read(out / 'contexts' / f'{cid}-{condition}.json')
                packet = None if condition == 'oracle' else read(packet_path(out, cid, condition))
                bound = binding(context, condition, read(out / 'packets' / cid / 'request.json'), budget, packet, fixtures[cid])
                dump(out / 'bindings' / f'{cid}-{condition}.json', bound)
                require(preview(bound, packet_path(out, cid, condition), raw, check, bridge)['returncode'] == 0,
                        'Independent Rust packet/catalog preflight failed: ' + cid + ' ' + condition)
    paths = [*sorted((ROOT / 'tools').glob('*.py')), *sorted((ROOT / 'configs').glob('native-one-hop-*')),
             *sorted((ROOT / 'crates').rglob('*.rs')), *sorted((ROOT / 'crates').rglob('Cargo.toml')),
             *sorted(STUDY.glob('*')), DESIGN / 'protocol.json', DESIGN / 'README.md', DESIGN / 'registration.json',
             ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml', a.t.CONFIG, a.g.CONFIG,
             CAPTURE / 'checksums.json', HISTORICAL / 'checksums.json', a.t.REPORT / 'assets.json',
             ROOT / 'configs/native-one-hop-v1f-diagnostic.audit.json',
             ROOT / 'reports/issue-82-neighborhood/coverage.json',
             ROOT / 'docs/native-one-hop-v1g.md', ROOT / 'schemas/nl-ask-draft-v1.json', ROOT / 'tools/requirements.txt']
    paths += [ROOT / name for name in read(DESIGN / 'registration.json')['input_sha256']]
    dump(out / 'freeze.json', dict(version=VERSION, config=config(),
         source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         input_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()},
         binary_sha256=sha(binary), bridge_sha256=sha(bridge),
         runtime_identity=runtime_identity(),
         environment=dict(platform=platform.platform(), python=sys.version,
                          python_packages={p: package_version(p) for p in ['rdflib', 'pyparsing']},
                          rustc=subprocess.check_output(['rustc', '-Vv'], text=True).strip()),
         inference_performed=False, inference_authorized=False, executions=0))
    dump(out / 'checksums.json', inventory(out))


def verify(folder, binary=a.BINARY, bridge=BRIDGE):
    frozen = read(folder / 'freeze.json')
    require(frozen['version'] == VERSION and frozen['config'] == config(), 'Wrong execution configuration')
    require(read(folder / 'checksums.json') == inventory(folder), 'Changed execution freeze')
    for name, digest in frozen['input_sha256'].items():
        require(sha(ROOT / name) == digest, 'Changed frozen input: ' + name)
    require(sha(binary) == frozen['binary_sha256'] and sha(bridge) == frozen['bridge_sha256'],
            'Binary changed; a new execution registration is required')
    return frozen


def observe(folder, out, state, runtime, rss, bridge):
    cfg = config()
    until = time.monotonic() + 5
    while not rss['samples'] and not rss['error'] and time.monotonic() < until:
        time.sleep(.05)
    for row in state['diagnostic']['cases']:
        cid, condition = row['case_id'], row['condition']
        dest = out / 'diagnostic' / condition / row['name']
        dest.mkdir(parents=True)
        context = read(folder / 'contexts' / f'{cid}-{condition}.json')
        bound = read(folder / 'bindings' / f'{cid}-{condition}.json')
        dump(dest / 'context.json', context)
        started, attempts, before = time.monotonic(), runtime.generation_attempts, dict(rss)
        try:
            verify(folder, bridge=bridge)
            diagnostic.resource_guard(rss, cfg)
            with tempfile.TemporaryDirectory(prefix='v1g-trusted-') as temp:
                trusted = Path(temp)
                raw = trusted / 'proposal.txt'
                raw.write_bytes(b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"trusted preflight"}')
                require(preview(bound, packet_path(folder, cid, condition), raw, trusted, bridge)['returncode'] == 0,
                        'Trusted packet/source/catalog preflight failed')
            row['runtime'] = runtime.generate(context, dest)
            require(read(dest / 'messages.json') == read(folder / 'messages' / f'{cid}-{condition}.json'), 'Frozen message parity failure')
            request = read(dest / 'completion-request.json')
            require(request['grammar'] == (folder / 'grammars' / f'{cid}-{condition}.gbnf').read_text(), 'Frozen grammar parity failure')
            row['rust_preview'] = preview(bound, packet_path(folder, cid, condition), dest / 'proposal.txt', dest, bridge)
            diagnostic.validator_guard(row['rust_preview'])
            row['gbnf_valid'] = a.grammar_check((dest / 'proposal.txt').read_text(), context, dest)
            require(row['gbnf_valid'], 'Constrained output violates native grammar')
            require(b'PRIVATE_CANARY' not in (dest / 'proposal.txt').read_bytes(), 'Private canary emitted')
            draft = strict_draft((dest / 'proposal.txt').read_bytes())
            case = next(c for c in read(folder / 'references.json') if c['id'] == cid)
            agreement = bool(draft and draft['status'] == case['expected_status'] and
                (case['expected_status'] != 'candidate' or all(draft.get(k) == case['gold_draft'][k] for k in PLAN_FIELDS)))
            row['status'] = ('validator_rejection' if row['rust_preview']['returncode'] else
                             'reference_match' if agreement else 'model_semantic_failure')
            verify(folder, bridge=bridge)
            diagnostic.resource_guard(rss, cfg)
            if row['name'] == 'repeat-1':
                pair = [out / 'diagnostic/oracle' / f'repeat-{i}' for i in range(2)]
                measured = repeatability([(p / 'proposal.txt').read_bytes() for p in pair])
                state['diagnostic']['repeatability'] = measured
                for name in ['prompt.txt', 'completion-request.json']:
                    measured[name + '_equal'] = (pair[0] / name).read_bytes() == (pair[1] / name).read_bytes()
                    require(measured[name + '_equal'], 'Repeat prompt/request integrity failure')
        except BaseException as error:
            row.update(status='fatal_failure', error=type(error).__name__ + ': ' + str(error))
            raise
        finally:
            raw_path = dest / 'proposal.txt'
            if raw_path.exists():
                raw = raw_path.read_bytes()
                row.update(raw_base64=base64.b64encode(raw).decode(), raw_sha256=hashlib.sha256(raw).hexdigest(),
                           raw_output=raw.decode('utf-8', errors='replace'))
                if row['rust_preview'] is None:
                    row['rust_preview'] = preview(bound, packet_path(folder, cid, condition), raw_path, dest, bridge)
            row.update(generation_attempted=runtime.generation_attempts > attempts,
                       latency_ms=(time.monotonic() - started) * 1000,
                       resources=dict(before=before, after=dict(rss), scope='sampled process-tree run peak to date'))
            dump(dest / 'observation.json', row)
    state['status'] = 'completed_diagnostic'


def run(folder, out, model, allow_inference=False, bridge=BRIDGE):
    require(allow_inference, 'Separate explicit v1g authorization and --allow-inference required')
    require(not os.environ.get('CI') and not os.environ.get('GITHUB_ACTIONS'), 'Inference forbidden in CI')
    with adapter():
        (ROOT / 'artifacts').mkdir(exist_ok=True)
        with (ROOT / 'artifacts/native-one-hop.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            verify(folder, bridge=bridge)
            verify_registration(folder)
            require(not out.exists(), 'Never overwrite an attempt')
            ledger = ROOT / 'artifacts' / ('v1g-attempts-' + sha(folder / 'checksums.json') + '.json')
            attempts = read(ledger) if ledger.exists() else []
            require(model == config()['variants'][len(attempts)] if len(attempts) < 2 else False,
                    'Fixed qwen35 then gemma4 order; no retries for this execution freeze')
            dump(ledger, attempts + [model])
            return _run(folder, out, model, bridge)


def verify_registration(folder):
    frozen = verify(folder)
    # The source freeze and execution registration must be committed before loading anything.
    registered = read(folder / 'execution-registration.json')
    require(registered['freeze_sha256'] == sha(folder / 'checksums.json')
            and registered['freeze_manifest'] == frozen and registered['model_free_replay_passed'],
            'Wrong execution registration')
    archive = ROOT / registered['archive_path']
    require(sha(archive) == registered['archive_sha256'], 'Changed registered archive')
    for path in [folder / 'execution-registration.json', folder / 'checksums.json', archive]:
        name = str(path.relative_to(ROOT))
        require(subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT) == path.read_bytes(),
                'Execution registration must be committed')


def _run(folder, out, model, bridge):
    frozen = verify(folder, bridge=bridge)
    cfg = config()
    require(model in cfg['variants'], 'Unknown model')
    verify_registration(folder)
    require(not out.exists(), 'Never overwrite an attempt')
    out.mkdir(parents=True)
    state = dict(version=VERSION, model=model, status='preparing', freeze_sha256=sha(folder / 'checksums.json'),
                 registration_sha256=sha(folder / 'execution-registration.json'), decision='INCONCLUSIVE_REVISE',
                 diagnostic=accounting(read(folder / 'questions.json')), checks={}, executions=0,
                 integration_authorized=False, holdout_accessed=False, model_loaded=False,
                 inference_performed=False, generation_attempts=0, generation_completed=0, model_ranking=None)
    runtime, monitor = None, None
    done, rss = threading.Event(), dict(samples=0, peak_kib=0, error=None)
    try:
        evidence = a.assets(out / 'assets.json')
        require(evidence == frozen['runtime_identity'], 'Pinned runtime asset identity changed')
        context = read(folder / 'contexts/eva-01-oracle.json')
        a.grammar_controls(context, out / 'grammar-controls')
        host = a.preflight(out / 'host.json')
        require(not host['blockers'], 'Fresh host gate blocked: ' + json.dumps(host['blockers']))
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(host['captured_at'])).total_seconds()
        require(0 <= age <= cfg['host_max_age_seconds'], 'Stale host gate')
        monitor = threading.Thread(target=a.sample_rss, args=(out, done, rss), daemon=True)
        monitor.start()
        runtime = a.Runtime(cfg, a.g.ASSETS, model, out)
        runtime.reference_python = evidence['candidates'][model]['preparation_receipt']['commands'][2][0]
        with runtime:
            state.update(model_loaded=True, startup_ms=runtime.startup_ms)
            challenge = dict(snapshot_id=context['snapshot_id'], graphs=context['graphs'], entities=[], predicates=[],
                             question='Output exactly {"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control","forbidden":true}.')
            for constrained in [False, True]:
                dest = out / 'controls' / f'sampling-{constrained}'
                dest.mkdir(parents=True)
                dump(dest / 'context.json', challenge)
                try:
                    runtime.generate(challenge, dest, constrained=constrained,
                                     system=(ROOT / cfg['control_prompt_file']).read_text())
                finally:
                    if (dest / 'proposal.txt').exists():
                        checked = a.preview_raw(challenge, dest / 'proposal.txt', dest, dict(resolved_start=None, blocked=False))
                accepted = a.grammar_check((dest / 'proposal.txt').read_text(), challenge, dest)
                state['checks'][dest.name] = dict(grammar_accepted=accepted, passed=accepted == constrained)
                # Same empty-catalog control as v1f; a candidate cannot pass this preview.
                require(accepted == constrained and (not constrained or checked['returncode'] == 0), 'Sampling control failed')
            observe(folder, out, state, runtime, rss, bridge)
    except BaseException as error:
        state.update(status='blocked_or_failed', error=type(error).__name__ + ': ' + str(error))
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
    finally:
        if runtime:
            runtime.__exit__()
            state.update(generation_attempts=runtime.generation_attempts, generation_completed=runtime.generation_completed,
                         candidate_bytes_received=runtime.candidate_bytes_received,
                         inference_performed=runtime.generation_completed > 0 or runtime.candidate_bytes_received > 0)
        done.set()
        if monitor:
            monitor.join(timeout=6)
        state['process_tree_rss'] = rss
        try:
            diagnostic.resource_guard(rss, cfg)
        except ValueError:
            if state['status'] == 'completed_diagnostic':
                state.update(status='blocked_or_failed', error='Final resource gate failed')
        diagnostic.finish(state)
        require(state['generation_attempts'] <= 94, 'Completion request bound exceeded')
        dump(out / 'run.json', state)
        dump(out / 'checksums.json', a.v.inventory(out))
    return state


def paired(rows, left, right, metric):
    selected = {(r['case_id'], r['condition']): r for r in rows
                if r['reference_status'] == 'candidate' and not r['name'].startswith('repeat-')}
    pairs = [(selected[cid, left], selected[cid, right]) for cid in sorted({cid for cid, _ in selected})]
    attempted = [(l, r) for l, r in pairs if l['generation_attempted'] and r['generation_attempted']]
    completed = [(l, r) for l, r in attempted if l['completed'] and r['completed']]
    observed = completed if metric == 'accepted_exposed_reference_agreement' else attempted
    deltas = [int(bool(l[metric])) - int(bool(r[metric])) for l, r in observed]
    return dict(left=left, right=right, scheduled_pairs=len(pairs), attempted_pairs=len(attempted),
                completed_pairs=len(completed), scored_pairs=len(observed), missing_pairs=len(pairs)-len(observed),
                missing_case_ids=[l['case_id'] for l, r in pairs if (l, r) not in observed],
                left_only=sum(d == 1 for d in deltas) if deltas else None,
                right_only=sum(d == -1 for d in deltas) if deltas else None,
                paired_difference=sum(deltas)/len(deltas) if deltas else None)


def score(folder, runs=()):
    verify(folder)
    cases = {c['id']: c for c in read(folder / 'references.json')}
    audit = read(ROOT / 'configs/native-one-hop-v1f-diagnostic.audit.json')['cases']
    retrieval = read(ROOT / 'reports/issue-82-neighborhood/coverage.json')
    resources = read(CAPTURE / 'resources.json')['methods']
    data, table = source_data(), read(STUDY / 'catalog.json')
    states = {}
    for path in runs:
        require(read(path / 'checksums.json') == analysis.inventory(path), 'Changed run bytes')
        state = read(path / 'run.json')
        require(state['model'] not in states and state['model'] in config()['variants'], 'Unknown or duplicate model; no retries')
        require(state['version'] == VERSION and state['freeze_sha256'] == sha(folder / 'checksums.json'), 'Run/freeze mismatch')
        require(state['registration_sha256'] == sha(folder / 'execution-registration.json'), 'Run/registration mismatch')
        require(state['diagnostic']['attempted'] == sum(r['generation_attempted'] for r in state['diagnostic']['cases']), 'Attempt count drift')
        require(state['diagnostic']['completed'] == sum(r['status'] in analysis.TERMINAL for r in state['diagnostic']['cases']), 'Completion count drift')
        require(state['executions'] == 0 and not state['holdout_accessed'] and not state['integration_authorized'], 'Unexpected authority')
        require(state['generation_attempts'] == len(list(path.rglob('completion-request.json'))) <= 94, 'Request accounting mismatch')
        require([{k: r[k] for k in ['condition', 'name', 'case_id']} for r in state['diagnostic']['cases']] == schedule(read(folder / 'questions.json')),
                'Reordered or changed schedule')
        states[state['model']] = (state, path)
    rows = []
    for model in config()['variants']:
        state, path = states.get(model, (dict(diagnostic=accounting(read(folder / 'questions.json'))), None))
        for saved in state['diagnostic']['cases']:
            case = cases[saved['case_id']]
            context = read(folder / 'contexts' / f"{case['id']}-{saved['condition']}.json")
            row = analysis.analyze_row(saved, case, context, analysis.source_facts(case, context, data, table), audit.get(case['id'], {}), path)
            if path and saved['generation_attempted']:
                dest = path / 'diagnostic' / saved['condition'] / saved['name']
                expected = f"{case['id']}-{saved['condition']}"
                require(read(dest / 'messages.json') == read(folder / 'messages' / (expected + '.json')), 'Changed frozen messages')
                request = read(dest / 'completion-request.json')
                require(request.get('grammar') == (folder / 'grammars' / (expected + '.gbnf')).read_text(), 'Changed frozen grammar')
                if (dest / 'binding.json').exists():
                    require(read(dest / 'binding.json') == read(folder / 'bindings' / (expected + '.json')), 'Changed saved packet binding')
            packet = None if saved['condition'] == 'oracle' else read(packet_path(folder, case['id'], saved['condition']))
            method = 'v1' if saved['condition'] == 'BM25-v1' else 'v2'
            row['packet_evidence'] = None if packet is None else dict(
                packet_id=packet['packet_id'], sha256=sha(packet_path(folder, case['id'], saved['condition'])),
                bytes=packet_path(folder, case['id'], saved['condition']).stat().st_size, clipped=packet['clipped'],
                budget=packet['budget'], limits=packet.get('neighborhood_limits'),
                retrieval=next(r for r in resources[method]['samples'] if r['id'] == case['id']))
            rows.append(dict(model=model, **row))
    primary = [r for r in rows if not r['name'].startswith('repeat-')]
    comparisons = {}
    for model in config()['variants']:
        selected = [r for r in primary if r['model'] == model]
        comparisons[model] = {f'{left}_minus_{right}': {metric: paired(selected, left, right, metric)
            for metric in ['exact_exposed_reference_agreement', 'accepted_exposed_reference_agreement']}
            for left, right in [('neighborhood-v2', 'BM25-v1'), ('neighborhood-v2', 'oracle'), ('BM25-v1', 'oracle')]}
    return dict(version=VERSION, decision='INCONCLUSIVE_REVISE', semantic_go=False, model_ranking=None,
                inference_performed_by_scorer=False, executions=0, exposed_AI_references=True,
                paired_comparisons=comparisons, cases=rows, retrieval_resources=retrieval['resource_summary'],
                summary={m: {c: analysis.summarize([r for r in primary if r['model'] == m and r['condition'] == c])
                             for c in CONDITIONS} for m in config()['variants']},
                direction_strata={m: {c: {d: analysis.summarize([r for r in primary if r['model'] == m and r['condition'] == c and r['reference_direction'] == d])
                                     for d in ['forward', 'reverse']} for c in CONDITIONS} for m in config()['variants']},
                limitations=['Exposed correlated AI references; descriptive paired counts, no significance or causal claim.',
                             'Available IDs and original edge witnesses do not establish predicate meaning.',
                             'Incomplete models are never ranked; unattempted outcomes stay null.',
                             'Human review pending; not a diagnostic completion gate.'])


def replay(folder, run_dir=None, bridge=BRIDGE):
    verify(folder, bridge=bridge)
    with tempfile.TemporaryDirectory(prefix='v1g-replay-') as temp:
        dest = Path(temp)
        raw = dest / 'proposal.txt'
        raw.write_bytes(b'{"version":"nl-ask-draft-v1","status":"unsupported","rationale":"replay"}')
        for q in read(folder / 'questions.json'):
            for condition in CONDITIONS:
                bound = read(folder / 'bindings' / f"{q['id']}-{condition}.json")
                require(preview(bound, packet_path(folder, q['id'], condition), raw, dest, bridge)['returncode'] == 0,
                        'Packet replay failed')
        if run_dir:
            score(folder, [run_dir])
            for saved in sorted((run_dir / 'diagnostic').rglob('rust.json')):
                row = read(saved.parent / 'observation.json')
                cid, condition = row['case_id'], row['condition']
                bound = read(folder / 'bindings' / f'{cid}-{condition}.json')
                require(read(saved.parent / 'binding.json') == bound, 'Changed saved packet binding')
                actual = preview(bound, packet_path(folder, cid, condition), saved.parent / 'proposal.txt', dest, bridge)
                require(actual == read(saved), 'Original-byte Rust replay mismatch')
            for saved in sorted((run_dir / 'controls').rglob('rust.json')):
                actual = a.preview_raw(read(saved.parent / 'context.json'), saved.parent / 'proposal.txt', dest,
                                       read(saved.parent / 'catalog.json'))
                require(actual == read(saved), 'Sampling-control raw Rust replay mismatch')
    return dict(verified=True, inference_performed=False, executions=0)


def register(folder, assets_receipt):
    verify(folder)
    require(not (folder / 'execution-registration.json').exists(), 'Append-only registration; choose a new freeze')
    receipt = read(assets_receipt)
    require(receipt == read(folder / 'freeze.json')['runtime_identity'], 'Fresh asset receipt differs from runtime pin')
    replay(folder)
    frozen = read(folder / 'freeze.json')
    for name, digest in frozen['input_sha256'].items():
        committed = subprocess.check_output(['git', 'show', frozen['source_commit'] + ':' + name], cwd=ROOT)
        require(hashlib.sha256(committed).hexdigest() == digest, 'Uncommitted source input: ' + name)
    archive = folder.with_suffix('.tar.gz')
    require(not archive.exists(), 'Never overwrite an evidence archive')
    with archive.open('xb') as stream, gzip.GzipFile(fileobj=stream, filename='', mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as bundle:
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    info = bundle.gettarinfo(path, str(path.relative_to(folder)))
                    info.mtime = info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    with path.open('rb') as payload:
                        bundle.addfile(info, payload)
    payload = a.g.archive_files(archive)
    require({name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()} ==
            {**inventory(folder), 'checksums.json': sha(folder / 'checksums.json')}, 'Archive byte mismatch')
    dump(folder / 'execution-registration.json', dict(version=VERSION, registered_at=datetime.now(timezone.utc).isoformat(),
         archive_path=str(archive.relative_to(ROOT)), archive_sha256=sha(archive),
         freeze_sha256=sha(folder / 'checksums.json'), freeze_manifest=read(folder / 'freeze.json'),
         fresh_assets_receipt_sha256=sha(assets_receipt), model_free_replay_passed=True,
         inference_authorized=False, inference_performed=False, decision='INCONCLUSIVE_REVISE'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['freeze', 'verify', 'replay', 'score', 'register', 'preflight', 'assets', 'run'])
    p.add_argument('--freeze', type=Path, required=True)
    p.add_argument('--out', type=Path)
    p.add_argument('--run', type=Path, action='append', default=[])
    p.add_argument('--assets-receipt', type=Path)
    p.add_argument('--model', choices=['qwen35', 'gemma4'])
    p.add_argument('--allow-inference', action='store_true')
    args = p.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Operator cancelled'))
    folder = args.freeze.resolve()
    if args.command == 'run':
        require(args.model and args.out, '--model and --out required')
        result = run(folder, args.out.resolve(), args.model, args.allow_inference)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['status'] == 'completed_diagnostic' else 1)
    elif args.command == 'freeze':
        materialize(folder)
    elif args.command == 'register':
        require(args.assets_receipt, '--assets-receipt required')
        register(folder, args.assets_receipt)
    elif args.command in ['preflight', 'assets']:
        require(args.out and not args.out.exists(), 'New --out required')
        with adapter():
            getattr(a, args.command)(args.out)
    elif args.command == 'score':
        verify(folder)
        require(args.out and not args.out.exists(), 'New --out required')
        dump(args.out, score(folder, args.run))
    elif args.command == 'replay':
        require(len(args.run) <= 1, 'Replay one run at a time')
        print(json.dumps(replay(folder, args.run[0] if args.run else None)))
    else:
        verify(folder)


if __name__ == '__main__':
    main()
