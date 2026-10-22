"""Reproduce the retained diagnostic summary without inference or subprocesses."""
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from compact_ab import archive_files
from native_one_hop_semantics import PLAN_FIELDS, strict_draft
from predicate_diagnostics import measure

REPORT = Path(__file__).resolve().parent
REGISTRATION_SHA256 = '6ff9ca9824d62dc5f7457e142b308039f7ff033480b9dc871c22573892319e65'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def summary(rows):
    completed = [r for r in rows if r['completed']]
    candidates = [r for r in completed if r['expected']['fields']]
    return dict(scheduled=len(rows), attempted=sum(r['attempted'] for r in rows),
        completed=len(completed), missing=len(rows) - len(completed),
        reference_matches=sum(r['measurement']['reference_agreement'] is True for r in completed),
        model_statuses=dict(Counter(r['measurement']['model_status'] for r in completed)),
        rust_accepted=sum(r['measurement']['rust_accepted'] is True for r in completed),
        candidate_references_completed=len(candidates),
        field_matches={k: sum(bool(r['measurement']['field_agreement'] and
            r['measurement']['field_agreement'][k]) for r in candidates) for k in PLAN_FIELDS})


def analyze():
    manifest = json.loads((REPORT / 'evidence-files.json').read_bytes())
    archive = REPORT / 'evidence.tar.gz'
    require(digest(archive.read_bytes()) == manifest['archive_sha256'], 'Changed evidence archive')
    payload = archive_files(archive)
    require({n: digest(raw) for n, raw in payload.items()} == manifest['files'], 'Changed evidence inventory')
    read = lambda name: json.loads(payload[name])
    require(digest(payload['registration.json']) == REGISTRATION_SHA256, 'Changed execution registration')
    registration = read('registration.json')
    require(digest(payload['registered-freeze.tar.gz']) == registration['original_archive_sha256'], 'Changed original archive')
    for name, expected in registration['input_sha256'].items():
        require(digest(payload['source/' + name]) == expected, 'Changed registered input: ' + name)
    checksums = read('run/checksums.json')
    require({n.removeprefix('run/'): digest(raw) for n, raw in payload.items()
        if n.startswith('run/') and Path(n).name != 'checksums.json'} == checksums, 'Changed run bytes')
    state, score = read('run/run.json'), read('run/score.json')
    notes = read('operator/source-audit-notes.json')['observations']
    require(state['registration_sha256'] == REGISTRATION_SHA256 and state['executions'] == 0 and
        not state['integration_authorized'] and not state['holdout_accessed'], 'Changed run authority')
    require(len(state['rows']) == len(score['rows']) == len(registration['schedule']) == 126, 'Changed denominator')
    rows = []
    for observed, scored, registered in zip(state['rows'], score['rows'], registration['schedule']):
        require(all(observed[k] == scored[k] == registered[k] for k in ['id', 'experiment', 'condition', 'case_id']),
            'Changed scheduled identity')
        raw = base64.b64decode(observed['raw_base64'], validate=True) if observed['raw_base64'] is not None else None
        if raw is not None:
            require(digest(raw) == observed['raw_sha256'] and
                raw == payload['run/requests/' + observed['id'] + '/proposal.txt'], 'Changed original response')
        complete = observed['status'] == 'completed'
        require(scored['completed'] == complete and scored['attempted'] == observed['attempted'], 'Changed completion accounting')
        expected = scored['expected']
        preview = observed.get('rust_preview')
        if expected:
            require(scored['measurement'] == measure(expected, raw if complete else None,
                preview['returncode'] == 0 if preview else None), 'Changed measurement')
        draft = strict_draft(raw) if raw is not None else None
        note = notes.get(observed['id'])
        if note:
            require(note['raw_sha256'] == observed['raw_sha256'] and draft is not None and
                note['rationale_exact'] == draft['rationale'] and note['supplied_fields'] == expected['fields'] and
                digest(payload[note['context_path']]) == registered['files'][note['context_path'].removeprefix('freeze/')],
                'Unbound investigator note')
        rows.append(dict(**scored, status=observed['status'], raw_measurement=observed.get('raw_measurement'),
            rationale=draft['rationale'] if draft else None,
            rationale_at_character_limit=len(draft['rationale']) == 512 if draft else None,
            source_investigator_note=note, latency_ms=observed.get('latency_ms')))
    requests = [n for n in payload if n.startswith('run/requests/') and n.endswith('/completion-request.json')]
    require(len(requests) == state.get('generation_attempts', 0) <= 126, 'Changed request accounting')
    streams = []
    for name in requests:
        prefix = name.removesuffix('completion-request.json')
        key = prefix.rstrip('/').split('/')[-1]
        registered = next(r for r in registration['schedule'] if r['id'] == key)
        native, body, parity = read(prefix + 'native-template.stdout'), read(name), read(prefix + 'parity.json')
        require(parity['token_ids_equal'] and parity['prompt_bytes_equal'] and
            digest(payload[prefix + 'prompt.txt']) == registered['prompt_sha256'] and
            payload[prefix + 'prompt.txt'] == native['prompt'].encode() and
            native['tokens'] == body['prompt'] and
            digest(json.dumps(native['tokens'], separators=(',', ':')).encode()) == registered['tokens_sha256'],
            'Changed native prompt/token parity')
        require(body['n_predict'] == 512 and body['temperature'] == 0 and body['seed'] == 7 and
            body.get('grammar') == (payload['freeze/grammars/' + key + '.gbnf'].decode()
                if key != 'sampling-unconstrained' else None), 'Changed generation configuration')
        events, error = [], None
        try:
            for line in payload.get(prefix + 'completion.http.sse', b'').splitlines():
                if line.startswith(b'data:'):
                    events.append(json.loads(line[5:]))
        except (ValueError, UnicodeDecodeError) as failure:
            error = str(failure)
        raw = payload.get(prefix + 'proposal.txt')
        require(error is not None or raw is None or raw == ''.join(e.get('content', '') for e in events).encode(),
            'Changed SSE/response bytes')
        streams.append(dict(id=key, terminal=bool(events and events[-1].get('stop') is True), stream_error=error))
    require(sum(s['terminal'] for s in streams) == state.get('generation_completed', 0), 'Changed terminal count')
    semantic = [r for r in rows if r['expected']]
    construction = [r for r in rows if r['experiment'] == 'explicit_iri_construction']
    metadata = [r for r in rows if r['experiment'] == 'natural_language_metadata']
    synthetic = read('source/experiments/predicate-diagnostics-v1/model-free-replay.json')
    incompatible = {r['id'] for r in synthetic['observations'] if r['rust_preview']['returncode'] != 0}
    require(len(incompatible) == 10, 'Changed known compiler incompatibilities')
    strata = {}
    for row in semantic:
        ref = row['expected']
        key = '/'.join([row['experiment'], row['condition'], ref['fields']['direction'] if ref['fields'] else ref['expected_status'],
            str(ref['kind']), 'target_metadata=' + str(ref['target_metadata_available'])])
        strata.setdefault(key, []).append(row)
    return dict(decision='INCONCLUSIVE_REVISE', independent_human_review='deferred',
        semantic_readiness=None, model_generated_rdf_executions=0, issue83='keep_open', issue75_integration='disabled',
        run_status=state['status'], failure=state.get('failure'), generation_attempts=state.get('generation_attempts', 0),
        generation_completed=state.get('generation_completed', 0), scheduled=126, completed=score['completed'],
        controls=[r for r in rows if r['experiment'] == 'native_sampling_control'],
        construction=summary(construction), metadata={arm: summary([r for r in metadata if r['condition'] == arm])
            for arm in ['no_metadata', 'metadata']}, strata={k: summary(v) for k, v in strata.items()},
        pairs=score['natural_language_pairs'], paired_completed=score['paired_completed'], repeatability=score['repeatability'],
        compiler_rejections=[r['id'] for r in semantic if r['completed'] and r['measurement']['rust_accepted'] is False],
        known_compiler_incompatibilities=[dict(id=r['id'], completed=r['completed'], measurement=r['measurement'])
            for r in construction if r['id'] in incompatible],
        reference_disagreements=[r['id'] for r in semantic if r['completed'] and r['measurement']['reference_agreement'] is False],
        incomplete=[r['id'] for r in rows if not r['completed']],
        streams=streams, process_tree_rss=state['process_tree_rss'], rows=rows)


if __name__ == '__main__':
    result = analyze()
    if '--check' in sys.argv:
        require(result == json.loads((REPORT / 'analysis.json').read_bytes()), 'Analysis drift')
        print('Evidence summary reproduced without inference or subprocesses.')
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
