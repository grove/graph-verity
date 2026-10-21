#!/usr/bin/env python3
"""Model-free, hash-bound comparison of the single v1h Qwen attempt with r3."""
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

from rdflib import Dataset

import analyze_v1f as a
import analyze_v1f_r3 as r3
from compact_ab import archive_files

REPORT = a.ROOT / 'experiments/native-one-hop-v1h-budget-qwen35-evidence'
REGISTRATION = a.ROOT / 'experiments/native-one-hop-v1h-budget/registration.json'


def analyze(report=REPORT):
    manifest = a.read(report / 'evidence-files.json')
    a.require(a.digest((report / 'evidence.tar.gz').read_bytes()) == manifest['archive_sha256'], 'Changed evidence archive')
    payload = archive_files(report / 'evidence.tar.gz')
    a.require({n: a.digest(raw) for n, raw in payload.items()} == manifest['files'], 'Archive inventory mismatch')
    registration = json.loads(payload['registration.json'])
    a.require(registration == a.read(REGISTRATION), 'Changed registered revision')
    frozen = registration['freeze_manifest']
    a.require(json.loads(payload['freeze/freeze.json']) == frozen, 'Freeze/registration mismatch')
    a.require(a.digest(payload['freeze/checksums.json']) == registration['freeze_sha256'], 'Changed freeze identity')
    a.require({n.removeprefix('freeze/'): a.digest(raw) for n, raw in payload.items()
               if n.startswith('freeze/') and n != 'freeze/checksums.json'} == json.loads(payload['freeze/checksums.json']),
              'Changed frozen packets')
    for name, digest in frozen['input_sha256'].items():
        a.require(a.digest(payload['source/' + name]) == digest, 'Changed registered source: ' + name)
    authorization = json.loads(payload['authorization.json'])
    command = ('.venv/bin/python tools/native_one_hop_v1h.py run \\\n'
               '  --freeze artifacts/v1h-budget \\\n'
               '  --model qwen35 \\\n'
               '  --allow-inference \\\n'
               '  --out artifacts/issue83-v1h-budget-qwen35-first\n')
    a.require(authorization['owner_message_exact'] == 'I authorize it.'
              and authorization['proposal_command_exact'] == command
              and authorization['registration_sha256'] == a.digest(payload['registration.json'])
              and authorization['freeze_checksums_sha256'] == registration['freeze_sha256']
              and authorization['freeze_archive_sha256'] == registration['archive_sha256']
              and authorization['model'] == 'qwen35' and authorization['retries'] == 0,
              'Authorization identity mismatch')
    historical = r3.analyze()
    historical_bytes = archive_files(r3.REPORT / 'evidence.tar.gz')
    old_rows = [r for r in historical['cases'] if r['model'] == 'qwen35']
    notes = json.loads(payload['operator/source-audit-notes.json'])
    prior_notes = {(r['condition'], r['observation']): r for r in json.loads(payload['operator/prior-source-investigation.json'])['cases']}
    with tempfile.TemporaryDirectory(prefix='v1h-evidence-analysis-') as temp:
        root = Path(temp)
        for name, raw in payload.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        run = root / 'run'
        state = a.read(run / 'run.json')
        cfg = frozen['config']
        a.require(a.inventory(run) == a.read(run / 'checksums.json'), 'Changed run bytes')
        a.require(state['version'] == registration['version'] and state['model'] == 'qwen35'
                  and state['freeze_sha256'] == registration['freeze_sha256']
                  and state['executions'] == 0 and not state['integration_authorized'] and not state['holdout_accessed'],
                  'Run identity/authority mismatch')
        expected = a.schedule(cfg)
        saved = state['diagnostic']['cases']
        a.require([{k: r[k] for k in ('condition', 'name', 'case_id')} for r in saved] == expected
                  == [{k: r[k] for k in ('condition', 'name', 'case_id')} for r in old_rows], 'Changed comparison schedule')
        a.require(state['diagnostic']['attempted'] == sum(r['generation_attempted'] for r in saved)
                  and state['diagnostic']['completed'] == sum(r['status'] in a.TERMINAL for r in saved)
                  and state['diagnostic']['denominator'] == 36, 'Diagnostic accounting mismatch')
        requests = sorted(run.rglob('completion-request.json'))
        a.require(state['generation_attempts'] == len(requests) <= 38
                  and state['generation_completed'] <= len(requests), 'Request accounting mismatch')
        token_receipt = a.read(root / 'freeze/tokenization/counts.json')
        budgets = token_receipt['models']['qwen35']['rows']
        preload_receipt = a.read(run / 'preload-token-budget/counts.json') if (run / 'preload-token-budget/counts.json').exists() else None
        preload = preload_receipt['models']['qwen35']['rows'] if preload_receipt else []
        a.require(not state['model_loaded'] or len(preload) == len(budgets) == 38, 'Missing pre-load budget')
        a.require(not preload_receipt or all(preload_receipt[k] == token_receipt[k] for k in ['packages', 'python']),
                  'Pinned tokenizer environment mismatch')
        for old, new in zip(budgets, preload):
            a.require(all(old[k] == new[k] for k in ['condition', 'name', 'case_id', 'kind'])
                      and old['columnar']['tokens'] == new['columnar']['tokens']
                      and old['columnar']['prompt'] == new['columnar']['prompt']
                      and new['columnar']['total_required'] == len(new['columnar']['tokens']) + 512 < 16384,
                      'Pre-load token budget mismatch')
        if (run / 'assets.json').exists():
            assets = a.read(run / 'assets.json')
            a.require({k: assets[k] for k in frozen['runtime_identity']} == frozen['runtime_identity'], 'Asset identity mismatch')
        cases = a.read(root / 'source/studies/nl-ask-v1/cases.json')
        cases = {c['id']: c for c in cases if c['split'] == 'evaluation'}
        cases.update({c['id']: c for c in a.read(root / 'source' / cfg['fixture_file'])})
        audit = a.read(root / 'source/configs/native-one-hop-v1f-diagnostic.audit.json')['cases']
        data = Dataset()
        data.parse(root / 'source/studies/nl-ask-v1/evaluation/snapshot.nq', format='nquads')
        table = a.read(root / 'source/studies/nl-ask-v1/evaluation/catalog.json')
        rows, comparisons, streams = [], [], []
        for observation, old in zip(saved, old_rows):
            case = cases[observation['case_id']]
            context = a.read(root / 'freeze/contexts' / f"{case['id']}-{observation['condition']}.json")
            row = a.analyze_row(observation, case, context, a.source_facts(case, context, data, table), audit[case['id']], run)
            row['raw_evidence_path'] = f"run/diagnostic/{row['condition']}/{row['name']}"
            row['independent_human_judgment'] = None
            key = row['condition'] + '/' + row['name']
            if key in notes:
                a.require(notes[key]['raw_sha256'] == row['raw_sha256'], 'Investigator note/raw mismatch')
                row['investigator_note'] = notes[key]['note']
            elif row['raw_sha256']:
                prior = prior_notes[(row['condition'], row['name'])]
                a.require(prior['raw_sha256'] == row['raw_sha256'], 'Changed response needs a fresh source note')
                row['investigator_note'] = prior['investigator_note']
            else:
                row['investigator_note'] = 'No retained model response; no semantic outcome is inferred.'
            rows.append(dict(model='qwen35', **row))
            identity = f"diagnostic/{row['condition']}/{row['name']}"
            prompt = run / identity / 'prompt.txt'
            old_prompt = historical_bytes.get('run/' + identity + '/prompt.txt')
            prompt_equal = prompt.read_bytes() == old_prompt if prompt.exists() and old_prompt is not None else None
            a.require(row['condition'] != 'oracle' or prompt_equal is not False, 'Changed oracle prompt bytes')
            comparisons.append(dict(condition=row['condition'], name=row['name'], case_id=row['case_id'],
                r3={k: old[k] for k in ['completed', 'generation_attempted', 'model_origin_status', 'exact_exposed_reference_agreement', 'raw_sha256', 'latency_ms']},
                v1h={k: row[k] for k in ['completed', 'generation_attempted', 'model_origin_status', 'exact_exposed_reference_agreement', 'raw_sha256', 'latency_ms']},
                identical_prompt_bytes=prompt_equal,
                identical_response_bytes=row['raw_sha256'] == old['raw_sha256'] if row['raw_sha256'] and old['raw_sha256'] else None))
        for request in requests:
            dest = request.parent
            stream, proposal = dest / 'completion.http.sse', dest / 'proposal.txt'
            events, stream_error = [], None
            try:
                if stream.exists():
                    events = [json.loads(line[5:].strip()) for line in stream.read_bytes().splitlines() if line.startswith(b'data:')]
            except (ValueError, UnicodeDecodeError) as error:
                stream_error = type(error).__name__ + ': ' + str(error)
            terminal = bool(events and events[-1].get('stop') is True)
            raw = b''.join(e.get('content', '').encode() for e in events)
            a.require(stream_error is not None or not proposal.exists() or raw == proposal.read_bytes(), 'SSE/raw mismatch')
            parity = a.read(dest / 'parity.json')
            a.require(parity['token_ids_equal'] and parity['prompt_bytes_equal'], 'Native parity mismatch')
            condition = 'sampling' if dest.parent.name == 'controls' else dest.parent.name
            budget = next(b['columnar'] for b in budgets if b['condition'] == condition and b['name'] == dest.name)
            native = a.read(dest / 'native-template.stdout')
            a.require(native['tokens'] == a.read(request)['prompt'] == budget['tokens']
                      and (dest / 'prompt.txt').read_bytes() == native['prompt'].encode() == budget['prompt'].encode(),
                      'Registered prompt/token parity mismatch')
            a.require(a.read(dest / 'parity-tokens.http.json')['tokens'] == native['tokens']
                      and a.read(dest / 'parity-template.http.json')['prompt'] == native['prompt'], 'Native HTTP parity mismatch')
            streams.append(dict(path=str(dest.relative_to(run)), terminal=terminal, stream_present=stream.exists(),
                proposal_present=proposal.exists(), stream_error=stream_error,
                bytes=proposal.stat().st_size if proposal.exists() else None,
                raw_sha256=a.digest(proposal.read_bytes()) if proposal.exists() else None))
        a.require(sum(s['terminal'] for s in streams) == state['generation_completed'], 'Terminal stream count mismatch')
        summary = {c: a.summarize([r for r in rows if r['condition'] == c]) for c in cfg['stages']}
        strata = {}
        for revision, observations in [('r3', old_rows), ('v1h', rows)]:
            strata[revision] = {condition: {field: {str(value): a.summarize([r for r in observations
                if r['condition'] == condition and r[field] == value])
                for value in sorted({r[field] for r in observations if r['condition'] == condition}, key=str)}
                for field in ['reference_direction', 'reference_group', 'AI_source_question_group']}
                for condition in cfg['stages']}
        paired = {}
        for condition in cfg['stages']:
            pairs = [p for p in comparisons if p['condition'] == condition and p['r3']['completed'] and p['v1h']['completed']]
            paired[condition] = dict(completed_pairs=len(pairs), identical_response_bytes=sum(p['identical_response_bytes'] is True for p in pairs),
                r3_reference_agreement=sum(p['r3']['exact_exposed_reference_agreement'] is True for p in pairs),
                v1h_reference_agreement=sum(p['v1h']['exact_exposed_reference_agreement'] is True for p in pairs),
                r3_observation_latency_ms=a.distribution([p['r3']['latency_ms'] for p in pairs]),
                v1h_observation_latency_ms=a.distribution([p['v1h']['latency_ms'] for p in pairs]))
        return dict(version='v1h-qwen-retained-analysis-v1', decision='INCONCLUSIVE_REVISE', semantic_go=False,
            independent_human_review='pending', model_ranking=None, exact_answer_accuracy=None,
            investigator_note_origin='Source-grounded coding-agent notes, including prior notes for identical responses with preserved source information; not independent human review.',
            inference_performed_by_analyzer=False, model_generated_rdf_executions=0,
            input_identity=dict(archive_sha256=manifest['archive_sha256'], registration_sha256=a.digest(payload['registration.json']),
                registered_source_commit=frozen['source_commit'], registered_binary_sha256=frozen['binary_sha256'],
                run_sha256=a.digest(payload['run/run.json']), historical_archive_sha256=historical['input_identity']['archive_sha256'],
                scorer_sha256=a.digest(Path(a.__file__).read_bytes()), analyzer_sha256=a.digest(Path(__file__).read_bytes())),
            authorization=authorization, run_status=state['status'], error=state.get('error'),
            native_integrity=dict(sampling_controls=state['checks'], streams=streams,
                generation_attempts=state['generation_attempts'], generation_completed=state['generation_completed'],
                grammar_controls=a.read(run / 'grammar-controls/controls.json') if (run / 'grammar-controls/controls.json').exists() else None),
            resources=dict(startup_ms=state.get('startup_ms'), process_tree_rss=state['process_tree_rss'],
                host=a.read(run / 'host.json') if (run / 'host.json').exists() else None),
            context_budgets=[{**{k: b[k] for k in ['condition', 'name', 'case_id', 'kind']},
                **{v: {k: b[v][k] for k in ['input_tokens', 'output_reserve', 'total_required', 'fits', 'prompt_sha256', 'tokens_sha256']}
                   for v in ['original', 'columnar']}} for b in budgets],
            tokenizer_environment={k: token_receipt[k] for k in ['packages', 'python']},
            summary=summary, historical_summary=historical['summary']['model_condition']['qwen35'],
            diagnostic_strata=strata, observation_states={c: dict(Counter(r['status'] for r in rows if r['condition'] == c)) for c in cfg['stages']},
            paired_completed_comparison=paired, comparisons=comparisons, cases=rows,
            limitations=['Oracle messages are unchanged; BM25-v1 packet presentation changes while information and membership are preserved.',
                'Token reduction and representation effects are confounded; r3 is incomplete, exposed historical evidence.',
                'Exposed-reference agreement, grammar validity and Rust acceptance are not independent semantic correctness.',
                'Wrong-but-executable means disagreement with exposed references, not independently established semantic error.',
                'No draft is executed; source witnesses enumerate retained triples only. Missing vocabulary is not restored.',
                'Rationale identity rules recognize narrow English assertions; unrestricted rationale correctness is unassessed.',
                'The unchanged grammar bounds rationales to 512 characters; some retained explanations end mid-sentence.',
                'Repeated observations are correlated; no randomized baseline, causal attribution or readiness claim.',
                'RSS is a sampled concurrent process-tree peak; sampling can miss peaks and double-count shared pages.'])


def markdown(result):
    lines = ['# Qwen v1h versus historical r3', '', '**INCONCLUSIVE_REVISE. Independent human review pending.**', '',
        '| Revision / condition | Scheduled | Attempted | Completed | Unattempted | Exposed-reference agreement |',
        '|---|---:|---:|---:|---:|---:|']
    for revision, summaries in [('r3', result['historical_summary']), ('v1h', result['summary'])]:
        for condition, s in summaries.items():
            m = s['metrics']['exact_exposed_reference_agreement']
            lines.append(f"| {revision} / {condition} | {s['scheduled']} | {s['attempted']} | {s['completed']} | {s['unattempted']} | {m['numerator']}/{m['denominator']} |")
    lines += ['', '| Condition / observation | r3 status | v1h status | r3 agreement | v1h agreement |', '|---|---|---|---|---|']
    for p in result['comparisons']:
        lines.append(f"| {p['condition']} / {p['name']} | {p['r3']['model_origin_status']} | {p['v1h']['model_origin_status']} | {p['r3']['exact_exposed_reference_agreement']} | {p['v1h']['exact_exposed_reference_agreement']} |")
    lines += ['', '## Limitations', ''] + ['- ' + line for line in result['limitations']]
    return '\n'.join(lines) + '\n'


def failure_matrix(result):
    lines = ['# Every Qwen semantic diagnostic observation', '', '**INCONCLUSIVE_REVISE. Independent human judgments remain pending.**', '',
        result['investigator_note_origin'], '',
        '| Condition / observation | Exposed reference | Model status | Rust accepted | Reference agreement | Source-bound investigator note |',
        '|---|---|---|---|---|---|']
    for row in result['cases']:
        note = row['investigator_note'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {row['condition']} / {row['name']} | {row['reference_status']} {row['reference_direction'] or ''} | {row['model_origin_status']} | {row['rust_accepted']} | {row['exact_exposed_reference_agreement']} | {note} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=REPORT)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    a.require(not args.out.exists(), 'Never overwrite an analysis')
    result = analyze(args.report)
    args.out.mkdir(parents=True)
    (args.out / 'analysis.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (args.out / 'comparison.md').write_text(markdown(result))
    (args.out / 'failure-matrix.md').write_text(failure_matrix(result))


if __name__ == '__main__':
    main()
