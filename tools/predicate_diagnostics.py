"""Prepare, verify and score two offline diagnostics. Deliberately no inference command."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

import native_one_hop_v1g as v
import native_one_hop_v1h_direction as direction
import source_predicate_metadata as m
from native_one_hop_semantics import PLAN_FIELDS, repeatability, strict_draft

ROOT = v.ROOT
RELEASE = ROOT / 'experiments/predicate-diagnostics-v1'
DEVELOPMENT = ROOT / 'experiments/native-one-hop-v1g/execution-v1'
VERSION = 'issue83-predicate-diagnostics-v1'
read, dump, require, sha = v.read, v.dump, v.require, v.sha


def development():
    registration = read(DEVELOPMENT / 'development-registration.json')
    archive = DEVELOPMENT / 'explicit-predicate-development.tar.gz'
    require(sha(archive) == registration['archive_sha256'], 'Changed development archive')
    payload = v.a.g.archive_files(archive)
    require({n: m.digest(b) for n, b in payload.items() if n != 'checksums.json'} ==
            json.loads(payload['checksums.json']), 'Changed development panel')
    return payload


def parent():
    reg = read(direction.RELEASE / 'registration.json')
    require(sha(direction.RELEASE / 'freeze.tar.gz') == reg['archive_sha256'], 'Changed parent archive')
    return reg, v.a.g.archive_files(direction.RELEASE / 'freeze.tar.gz')


def inputs():
    paths = [*sorted((ROOT / 'tools').glob('*.py')), *sorted((ROOT / 'crates').rglob('*.rs')),
             *sorted((ROOT / 'crates').rglob('Cargo.toml')), ROOT / 'Cargo.toml', ROOT / 'Cargo.lock',
             *sorted((ROOT / 'configs').glob('native-one-hop-*')),
             ROOT / 'rust-toolchain.toml', ROOT / 'tools/requirements.txt', m.CONFIG, RELEASE / 'protocol.json',
             RELEASE / 'README.md', direction.CONFIG, direction.RELEASE / 'registration.json',
             direction.RELEASE / 'freeze.tar.gz', DEVELOPMENT / 'development-registration.json',
             DEVELOPMENT / 'explicit-predicate-development.tar.gz', ROOT / 'configs/native-one-hop-v1.gbnf',
             ROOT / 'configs/native-one-hop-controls-v1.prompt.txt',
             ROOT / 'configs/native-one-hop-v1h-qwen-direction-only.prompt.txt',
             *[ROOT / n for n in m.build()['input_sha256']],
             *sorted(v.HISTORICAL.rglob('*')), v.a.t.REPORT / 'assets.json',
             ROOT / 'studies/nl-ask-v1/cases.json', ROOT / 'configs/grounded-models-v1.json',
             *sorted(v.STUDY.glob('*'))]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}


def generation_inputs(metadata, panel, prior):
    def item(key, experiment, condition, cid, context, control=False):
        return dict(id=key, experiment=experiment, condition=condition, case_id=cid), context, control
    catalog = read(v.STUDY / 'catalog.json')
    challenge = dict(snapshot_id=catalog['snapshot_id'], graphs=catalog['graphs'], entities=[], predicates=[],
        question='Output exactly {"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control","forbidden":true}.')
    for value in ['unconstrained', 'constrained']:
        yield item('sampling-' + value, 'native_sampling_control', value, 'sampling', challenge, True)
    first = json.loads(panel['contexts/explicit-001-oracle.json'])
    for i in range(2):
        yield item('repeat-' + str(i), 'repeatability', 'explicit', 'explicit-001', first)
    for q in json.loads(panel['questions.json']):
        yield item(q['id'], 'explicit_iri_construction', 'oracle_no_metadata', q['id'],
                   json.loads(panel['contexts/' + q['id'] + '-oracle.json']))
    natural = read(v.HISTORICAL / 'questions.json')['questions']
    data, discovery = v.source_data(), read(v.STUDY / 'discovery.json')
    for i, cid in enumerate([q['id'] for q in natural] + ['v1e-label-explicit']):
        base = (json.loads(prior['original-contexts/' + cid + '-oracle.json']) if cid == 'v1e-label-explicit' else
                v.render(read(v.HISTORICAL / 'contexts' / (cid + '-oracle.json')), data, discovery))
        for enabled in ([False, True] if i % 2 == 0 else [True, False]):
            arm = 'metadata' if enabled else 'no_metadata'
            yield item(cid + '-' + arm, 'natural_language_metadata', arm, cid, m.enrich(base, metadata, enabled))


def scoring_inputs(out, schedule, panel, prior):
    metadata = m.build()
    refs = {r['id']: dict(**r, expected_status='candidate') for r in json.loads(panel['references.json'])}
    with direction.experiment():
        with direction.h.adapter():
            refs.update({r['id']: r for r in v.a.experiment_cases()})
    fixtures = json.loads(prior['operator-fixtures.json'])
    expected, bindings = {}, {}
    for row in schedule:
        key, cid = row['id'], row['case_id']
        if cid == 'sampling':
            continue
        ref = refs[cid]
        expected[key] = dict(case_id=cid, expected_status=ref['expected_status'],
            fields={k: ref['gold_draft'][k] for k in PLAN_FIELDS} if ref['expected_status'] == 'candidate' else None,
            source_witnesses=ref.get('witnesses'), kind=ref.get('kind'), independent_human_correctness=None,
            reference_origin='mechanical_explicit_IRI' if cid.startswith('explicit-') else 'unchanged_exposed_AI_reference')
        fields = expected[key]['fields']
        expected[key]['target_metadata_available'] = (bool(next(r for r in metadata['predicates']
            if r['id'] == fields['predicate'] and r['graph'] == fields['graph'])['metadata']) if fields else None)
        expected[key]['historical_source_audit'] = read(ROOT / 'configs/native-one-hop-v1f-diagnostic.audit.json')['cases'].get(cid)
        context = read(out / 'contexts' / (key + '.json'))
        fixture = (dict(resolved_start=ref['gold_draft']['start'], blocked=False) if cid.startswith('explicit-')
                   else fixtures[cid])
        selection = {k: read(v.STUDY / 'catalog.json')[k] for k in ['snapshot_id', 'graphs', 'entities', 'predicates']}
        selection.update(resolved_start=fixture['resolved_start'], blocked=fixture['blocked'], limit=100)
        request = json.loads(prior['packets/eva-01/request.json'])
        request.update(question=context['question'], language=context.get('language', 'en'))
        bindings[key] = dict(condition='oracle', request=request,
            budget=read(v.CAPTURE / 'budget.json'), saved_packet_id=None, selection=selection)
    return expected, bindings


def prepare(out):
    require(not out.exists(), 'Never overwrite a diagnostic freeze')
    metadata, panel = m.build(), development()
    registration, prior = parent()
    cfg = registration['freeze_manifest']['config']
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    pins = inputs()
    for name, expected in pins.items():
        raw = subprocess.check_output(['git', 'show', source_commit + ':' + name], cwd=ROOT)
        require(m.digest(raw) == expected, 'Commit preparation inputs first: ' + name)
    out.mkdir(parents=True)
    dump(out / 'metadata.json', metadata)
    schedule = []
    for name in ['contexts', 'messages', 'grammars', 'context-packets', 'bindings']:
        (out / name).mkdir()
    def save(key, experiment, condition, cid, context, control=False):
        schedule.append(dict(id=key, experiment=experiment, condition=condition, case_id=cid))
        dump(out / 'contexts' / (key + '.json'), context)
        prompt = cfg['control_prompt_file' if control else 'prompt_file']
        dump(out / 'messages' / (key + '.json'), [dict(role='system', content=(ROOT / prompt).read_text()),
                                               dict(role='user', content=v.a.g.safe_user(context))])
        with v.adapter():
            (out / 'grammars' / (key + '.gbnf')).write_text(v.a.grammar(context))
        dump(out / 'context-packets' / (key + '.json'), m.packet(context, metadata))
    for row, context, control in generation_inputs(metadata, panel, prior):
        save(row['id'], row['experiment'], row['condition'], row['case_id'], context, control)
    dump(out / 'schedule.json', schedule)
    dump(out / 'prompt-seal.json', v.a.v.inventory(out))
    # Load scoring/operator material only after sealing all generation inputs.
    expected, bindings = scoring_inputs(out, schedule, panel, prior)
    dump(out / 'expected.json', expected)
    for key, bound in bindings.items():
        dump(out / 'bindings' / (key + '.json'), bound)
    dump(out / 'freeze.json', dict(version=VERSION, source_commit=source_commit, input_sha256=pins,
        runtime_config=cfg, runtime_identity=registration['freeze_manifest']['runtime_identity'],
        binary_sha256=sha(v.a.BINARY), bridge_sha256=sha(v.BRIDGE), inference_authorized=False,
        inference_performed=False, decision='INCONCLUSIVE_REVISE', protocol=read(RELEASE / 'protocol.json')))
    dump(out / 'checksums.json', v.a.v.inventory(out))
    verify(out)


def verify(folder):
    frozen = read(folder / 'freeze.json')
    require(frozen['version'] == VERSION and read(folder / 'checksums.json') == v.a.v.inventory(folder), 'Changed freeze')
    for name, expected in frozen['input_sha256'].items():
        require(sha(ROOT / name) == expected, 'Changed frozen input: ' + name)
    require(sha(v.a.BINARY) == frozen['binary_sha256'] and sha(v.BRIDGE) == frozen['bridge_sha256'], 'Changed binary')
    metadata = m.build()
    require(metadata == read(folder / 'metadata.json'), 'Changed metadata provenance')
    reg, prior = parent()
    require(frozen['runtime_config'] == reg['freeze_manifest']['config'] and
            frozen['runtime_identity'] == reg['freeze_manifest']['runtime_identity'] and
            frozen['protocol'] == read(RELEASE / 'protocol.json'), 'Changed runtime/protocol')
    generated = list(generation_inputs(metadata, development(), prior))
    require(read(folder / 'schedule.json') == [r for r, _, _ in generated], 'Changed diagnostic schedule')
    expected, bindings = scoring_inputs(folder, [r for r, _, _ in generated], development(), prior)
    require(read(folder / 'expected.json') == expected, 'Changed scoring references')
    for key, bound in bindings.items():
        require(read(folder / 'bindings' / (key + '.json')) == bound, 'Changed host binding')
    for name, expected in read(folder / 'prompt-seal.json').items():
        require(sha(folder / name) == expected, 'Changed sealed input')
    for row, expected_context, control in generated:
        key = row['id']
        ctx = read(folder / 'contexts' / (key + '.json'))
        require(ctx == expected_context, 'Changed source-derived context')
        prompt = frozen['runtime_config']['control_prompt_file' if control else 'prompt_file']
        require(read(folder / 'messages' / (key + '.json')) == [
            dict(role='system', content=(ROOT / prompt).read_text()), dict(role='user', content=v.a.g.safe_user(ctx))],
            'Changed messages')
        with v.adapter():
            require((folder / 'grammars' / (key + '.gbnf')).read_text() == v.a.grammar(ctx), 'Changed grammar')
        packet = read(folder / 'context-packets' / (key + '.json'))
        m.revalidate(packet, ctx, metadata, packet['packet_id'])
    return frozen


def preview(folder, key, raw, saved_packet_id):
    """Rebind the new metadata packet before invoking the unchanged Rust preview bridge."""
    metadata = m.build()
    ctx = read(folder / 'contexts' / (key + '.json'))
    saved = read(folder / 'context-packets' / (key + '.json'))
    m.revalidate(saved, ctx, metadata, saved_packet_id)
    with tempfile.TemporaryDirectory(prefix='predicate-preview-') as temp:
        out = Path(temp)
        (out / 'raw.txt').write_bytes(raw)
        (out / 'oracle.bin').write_bytes(b'')
        return v.preview(read(folder / 'bindings' / (key + '.json')), out / 'oracle.bin', out / 'raw.txt', out)


def verify_registration(folder):
    frozen = verify(folder)
    reg = read(RELEASE / 'registration.json')
    require(reg['freeze_manifest'] == frozen and sha(folder / 'checksums.json') == reg['checksums_sha256'] and
            sha(RELEASE / 'freeze.tar.gz') == reg['archive_sha256'], 'Changed registered archive identity')
    payload = v.a.g.archive_files(RELEASE / 'freeze.tar.gz')
    require({n: m.digest(b) for n, b in payload.items()} ==
            {**read(folder / 'checksums.json'), 'checksums.json': sha(folder / 'checksums.json')}, 'Changed registered bytes')
    return frozen


def measure(expected, raw, rust_accepted):
    draft = strict_draft(raw) if raw is not None else None
    candidate = draft is not None and draft['status'] == 'candidate'
    fields = {k: draft[k] == expected['fields'][k] for k in PLAN_FIELDS} if candidate and expected['fields'] else None
    return dict(model_status=draft['status'] if draft else None, strict_valid=draft is not None,
        actual_fields={k: draft[k] for k in PLAN_FIELDS} if candidate else None, field_agreement=fields,
        reference_agreement=(bool(draft and draft['status'] == expected['expected_status'] and
            (expected['fields'] is None or fields and all(fields.values()))) if raw is not None else None),
        rust_accepted=rust_accepted, independent_human_correctness=None)


def score(folder, observations):
    """Observations bind original responses to their saved host packet ID; missing outcomes stay null."""
    verify(folder)
    scheduled, refs = read(folder / 'schedule.json'), read(folder / 'expected.json')
    require(set(observations) <= {r['id'] for r in scheduled}, 'Unknown observation')
    rows = []
    for row in scheduled:
        key = row['id']
        obs = observations.get(key, dict(attempted=False, failure=None, raw_utf8=None, packet_id=None))
        require(set(obs) == {'attempted', 'failure', 'raw_utf8', 'packet_id'} and type(obs['attempted']) is bool and
                (obs['failure'] is None or isinstance(obs['failure'], str)) and
                (obs['raw_utf8'] is None or isinstance(obs['raw_utf8'], str)),
                'Malformed observation')
        require(not obs['attempted'] or obs['packet_id'] == read(folder / 'context-packets' / (key + '.json'))['packet_id'],
                'Stale observation packet ID')
        raw = obs['raw_utf8'].encode() if obs['raw_utf8'] is not None else None
        require(obs['attempted'] or raw is None, 'Unattempted response')
        complete = obs['attempted'] and obs['failure'] is None and raw is not None
        rust = preview(folder, key, raw, obs['packet_id']) if raw is not None and key in refs else None
        metric = measure(refs[key], raw if complete else None, rust['returncode'] == 0 if rust else None) if key in refs else None
        rows.append(dict(**row, **obs, completed=complete, raw_sha256=m.digest(raw) if raw is not None else None,
                         expected=refs.get(key), measurement=metric, rust_preview=rust))
    pairs = []
    for base in [r for r in rows if r['experiment'] == 'natural_language_metadata' and r['condition'] == 'no_metadata']:
        treatment = next(r for r in rows if r['case_id'] == base['case_id'] and r['condition'] == 'metadata')
        paired = base['completed'] and treatment['completed']
        pairs.append(dict(case_id=base['case_id'], paired_completed=paired,
            reference_agreement_delta=(int(treatment['measurement']['reference_agreement']) -
                                       int(base['measurement']['reference_agreement'])) if paired else None))
    groups = {}
    for row in rows:
        if row['experiment'] not in ['explicit_iri_construction', 'natural_language_metadata']:
            continue
        ref = row['expected']
        field = ref['fields']
        group = '/'.join([row['experiment'], row['condition'], field['direction'] if field else ref['expected_status'],
                          str(ref['kind']), 'target_metadata=' + str(ref['target_metadata_available'])])
        group_rows = groups.setdefault(group, dict(scheduled=0, completed=0, reference_matches=0))
        group_rows['scheduled'] += 1
        group_rows['completed'] += row['completed']
        group_rows['reference_matches'] += row['measurement']['reference_agreement'] is True
    repeats = [r for r in rows if r['experiment'] == 'repeatability']
    repeated = repeatability([r['raw_utf8'].encode() for r in repeats]) if all(r['completed'] for r in repeats) else None
    return dict(version=VERSION, decision='INCONCLUSIVE_REVISE', rows=rows, natural_language_pairs=pairs, groups=groups,
        repeatability=repeated,
        scheduled=len(rows), completed=sum(r['completed'] for r in rows),
        paired_completed=sum(p['paired_completed'] for p in pairs), model_generated_rdf_executions=0,
        independent_human_review='deferred', semantic_readiness=None)


def register(folder):
    frozen = verify(folder)
    require(not (RELEASE / 'registration.json').exists(), 'Append-only registration')
    require(not (folder / 'token-job.json').exists(), 'Fresh registration attempt required')
    native = frozen['runtime_identity']['candidates']['qwen35']['verified_retained_files']
    for name, record in native.items():
        require(sha(v.a.g.ASSETS / name) == record['sha256'], 'Changed retained native asset: ' + name)
    runtime_source = v.a.g.ASSETS / 'upstream' / ('llama.cpp-' + frozen['runtime_identity']['runtime_revision'])
    require(runtime_source.is_dir(), 'Retained runtime source missing')
    v.a.g.source_tree(v.a.g.config(), v.a.g.ASSETS)
    dump(folder / 'native-assets.json', dict(qwen35=native, runtime_source_tree_verified=True, model_loaded=False))
    with v.adapter():
        v.a.grammar_controls(read(folder / 'contexts/explicit-001.json'), folder / 'grammar-controls')
    # The existing local tokenizer worker loads no model and cannot download files.
    spec = json.loads(parent()[1]['tokenization/job.json'])['models']
    observations = []
    for row in read(folder / 'schedule.json'):
        messages = read(folder / 'messages' / (row['id'] + '.json'))
        observations.append(dict(condition=row['condition'], name=row['id'], case_id=row['case_id'],
            kind=row['experiment'], original=dict(messages=messages), columnar=dict(messages=messages)))
    dump(folder / 'token-job.json', dict(models=spec, observations=observations))
    python = read(ROOT / 'reports/issue-74-one-hop-trial/assets.json')['candidates']['qwen35']['preparation_receipt']['commands'][2][0]
    result = subprocess.run([python, ROOT / 'tools/native_one_hop_v1h_tokens.py', folder / 'token-job.json',
                             folder / 'token-counts.json'], cwd=ROOT, capture_output=True, timeout=120)
    (folder / 'tokenizer.stdout').write_bytes(result.stdout)
    (folder / 'tokenizer.stderr').write_bytes(result.stderr)
    require(result.returncode == 0, 'Pinned tokenizer failed')
    counts = read(folder / 'token-counts.json')['models']['qwen35']['rows']
    require(all(r['columnar']['fits'] and r['columnar']['total_required'] < 16384 for r in counts), 'Context overflow')
    dump(folder / 'checksums.json', v.a.v.inventory(folder))
    verify(folder)
    with (RELEASE / 'freeze.tar.gz').open('xb') as stream, gzip.GzipFile(fileobj=stream, filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as bundle:
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    info = bundle.gettarinfo(path, str(path.relative_to(folder)))
                    info.mtime = info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    with path.open('rb') as payload:
                        bundle.addfile(info, payload)
    dump(RELEASE / 'registration.json', dict(version=VERSION, freeze_manifest=frozen,
        archive_sha256=sha(RELEASE / 'freeze.tar.gz'), checksums_sha256=sha(folder / 'checksums.json'),
        maximum_completion_requests=126, inference_authorized=False, inference_performed=False,
        decision='INCONCLUSIVE_REVISE'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'verify', 'register', 'score'])
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--observations', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.freeze)
    elif args.command == 'verify':
        verify_registration(args.freeze)
    elif args.command == 'register':
        register(args.freeze)
    else:
        require(args.out and not args.out.exists(), 'Fresh --out required')
        verify_registration(args.freeze)
        dump(args.out, score(args.freeze, read(args.observations) if args.observations else {}))
