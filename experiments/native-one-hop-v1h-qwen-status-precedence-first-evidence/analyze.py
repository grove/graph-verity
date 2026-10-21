"""Model-free comparison of the single authorized status-precedence attempt."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_v1h_qwen as baseline
from compact_ab import archive_files
from rdflib import Dataset

a = baseline.a
REPORT = Path(__file__).resolve().parent
RELEASE = ROOT / 'experiments/native-one-hop-v1h-qwen-status-precedence'


def analyze():
    manifest = a.read(REPORT / 'evidence-files.json')
    a.require(a.digest((REPORT / 'evidence.tar.gz').read_bytes()) == manifest['archive_sha256'], 'Changed evidence archive')
    payload = archive_files(REPORT / 'evidence.tar.gz')
    a.require({n: a.digest(raw) for n, raw in payload.items()} == manifest['files'], 'Changed evidence inventory')
    read = lambda name: json.loads(payload[name])
    registration = read('registration.json')
    frozen = registration['freeze_manifest']
    a.require(payload['registration.json'] == (RELEASE / 'registration.json').read_bytes(), 'Changed registration')
    a.require(read('freeze/freeze.json') == frozen, 'Changed freeze manifest')
    a.require(a.digest(payload['freeze/checksums.json']) == registration['freeze_sha256'], 'Changed freeze identity')
    a.require({n.removeprefix('freeze/'): a.digest(raw) for n, raw in payload.items()
        if n.startswith('freeze/') and n != 'freeze/checksums.json'} == read('freeze/checksums.json'), 'Changed freeze bytes')
    a.require(all(a.digest(payload['source/' + n]) == h for n, h in frozen['input_sha256'].items()), 'Changed registered source')
    pr = read('operator/pr97-verification.json')
    a.require(pr['headRefOid'] == 'e540f90e7624ef63cc031128a0704b1222450082'
        and pr['statusCheckRollup'] and all(c['conclusion'] == 'SUCCESS' for c in pr['statusCheckRollup']), 'Authorized PR/CI mismatch')
    for name in ['tools/analyze_v1f.py', 'tools/analyze_v1f_r3.py', 'tools/analyze_v1h_qwen.py']:
        a.require(payload['analysis-source/' + name] == (ROOT / name).read_bytes(), 'Changed analysis source: ' + name)
    auth = read('operator/execution-authorization.json')
    a.require(auth['authorized_pr_commit'] == 'e540f90e7624ef63cc031128a0704b1222450082'
        and auth['original_owner_message_exact'] == 'PR #97 passed. I authorize it.'
        and auth['followup_exact'] == 'Try now' and auth['model'] == 'qwen35' and auth['retries'] == 0
        and auth['registration_sha256'] == a.digest(payload['registration.json'])
        and auth['freeze_sha256'] == registration['freeze_sha256']
        and auth['maximum_completion_requests'] == 38
        and auth['freeze_archive_sha256'] == registration['archive_sha256']
        and auth['command'] == '.venv/bin/python tools/native_one_hop_v1h_status_precedence.py run --freeze artifacts/v1h-qwen-status-precedence --model qwen35 --allow-inference --out artifacts/issue83-v1h-qwen-status-precedence-first', 'Authorization mismatch')
    old = baseline.analyze()
    a.require(old == a.read(baseline.REPORT / 'analysis.json'), 'Baseline analysis drift')
    notes = read('operator/source-audit-notes.json')
    with tempfile.TemporaryDirectory(prefix='qwen-status-evidence-') as temp:
        directory = Path(temp)
        for name, raw in payload.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        run = directory / 'run'
        state = a.read(run / 'run.json')
        a.require(a.inventory(run) == a.read(run / 'checksums.json'), 'Changed original run')
        a.require(state['version'] == registration['version'] and state['model'] == 'qwen35'
            and state['freeze_sha256'] == registration['freeze_sha256'] and state['executions'] == 0
            and not state['integration_authorized'] and not state['holdout_accessed'], 'Changed run authority')
        ledger = read('operator/attempt-ledger.json')
        a.require(ledger == ['qwen35'], 'No-retry ledger mismatch')
        assets = a.read(run / 'assets.json')
        a.require(all(assets[k] == v for k, v in frozen['runtime_identity'].items()), 'Changed pinned assets')
        budgets = read('freeze/tokenization/counts.json')['models']['qwen35']['rows']
        recount = a.read(run / 'preload-token-budget/counts.json')
        saved_counts = read('freeze/tokenization/counts.json')
        a.require(all(recount[k] == saved_counts[k] for k in ['packages', 'python']), 'Tokenizer environment changed')
        for new, saved in zip(recount['models']['qwen35']['rows'], budgets):
            a.require(all(new[k] == saved[k] for k in ['condition', 'name', 'case_id', 'kind']), 'Changed token schedule')
            for variant in ['original', 'columnar']:
                a.require(all(new[variant][k] == saved[variant][k] for k in
                    ['prompt', 'tokens', 'prompt_sha256', 'tokens_sha256', 'input_tokens', 'output_reserve', 'total_required', 'fits']), 'Changed prompt/token budget')
            a.require(new['columnar']['total_required'] == len(new['columnar']['tokens']) + 512 < 16384, 'Context overflow')
        a.require(len(recount['models']['qwen35']['rows']) == len(budgets) == 38, 'Missing token receipts')
        host = a.read(run / 'host.json')
        a.require(not host['blockers'] and host['swap_used_mib'] <= 1024, 'Original host gate failed')
        grammar_controls = a.read(run / 'grammar-controls/controls.json')
        a.require(grammar_controls['accepted'] == grammar_controls['expected'] and len(grammar_controls['accepted']) == 12, 'Native grammar control failure')
        samples = [json.loads(line) for line in payload.get('run/rss.jsonl', b'').splitlines()]
        a.require(len(samples) == state['process_tree_rss']['samples']
            and (not samples or max(s['total_kib'] for s in samples) == state['process_tree_rss']['peak_kib'])
            and all(s['total_kib'] == sum(row[2] for row in s['tree_pid_ppid_rss_kib']) for s in samples), 'RSS receipt mismatch')
        if state['model_loaded']:
            a.require(samples and 0 <= (datetime.fromisoformat(samples[0]['at']) - datetime.fromisoformat(host['captured_at'])).total_seconds() <= 60, 'Missing fresh pre-load host evidence')
        if state['status'] == 'completed_diagnostic':
            a.require(all(c.get('passed') is True for c in state['checks'].values()), 'Native sampling controls did not pass')
            a.require(state['process_tree_rss']['samples'] > 0 and not state['process_tree_rss']['error']
                and state['process_tree_rss']['peak_kib'] <= 24 * 2**20, 'Final RSS gate failed')
        requests = sorted(run.rglob('completion-request.json'))
        a.require(len(requests) == state['generation_attempts'] <= 38, 'Request limit/count mismatch')
        streams = []
        for request in requests:
            dest = request.parent
            events, stream_error = [], None
            try:
                events = [json.loads(line[5:].strip()) for line in (dest / 'completion.http.sse').read_bytes().splitlines()
                          if line.startswith(b'data:')]
            except (OSError, ValueError, UnicodeDecodeError) as error:
                stream_error = type(error).__name__ + ': ' + str(error)
            raw = b''.join(e.get('content', '').encode() for e in events)
            proposal = dest / 'proposal.txt'
            a.require(stream_error is not None or not proposal.exists() or raw == proposal.read_bytes(), 'SSE/raw drift')
            parity = a.read(dest / 'parity.json')
            a.require(parity['token_ids_equal'] and parity['prompt_bytes_equal'], 'Native parity failure')
            condition = 'sampling' if dest.parent.name == 'controls' else dest.parent.name
            budget = next(b['columnar'] for b in budgets if b['condition'] == condition and b['name'] == dest.name)
            native = a.read(dest / 'native-template.stdout')
            a.require(native['tokens'] == a.read(request)['prompt'] == budget['tokens']
                and (dest / 'prompt.txt').read_bytes() == native['prompt'].encode() == budget['prompt'].encode(), 'Preload/native/request mismatch')
            a.require(a.read(dest / 'parity-tokens.http.json')['tokens'] == native['tokens']
                and a.read(dest / 'parity-template.http.json')['prompt'] == native['prompt'], 'HTTP native parity mismatch')
            streams.append(dict(path=str(dest.relative_to(run)), terminal=bool(events and events[-1].get('stop') is True),
                stream_error=stream_error, raw_sha256=a.digest(proposal.read_bytes()) if proposal.exists() else None))
        a.require(sum(s['terminal'] for s in streams) == state['generation_completed'], 'Terminal stream count mismatch')
        cases = {c['id']: c for c in read('source/studies/nl-ask-v1/cases.json') if c['split'] == 'evaluation'}
        cases.update({c['id']: c for c in read('source/' + frozen['config']['fixture_file'])})
        audit = read('source/configs/native-one-hop-v1f-diagnostic.audit.json')['cases']
        data = Dataset()
        data.parse(directory / 'source/studies/nl-ask-v1/evaluation/snapshot.nq', format='nquads')
        table = read('source/studies/nl-ask-v1/evaluation/catalog.json')
        rows = []
        expected = a.schedule(frozen['config'])
        saved_rows = state['diagnostic']['cases']
        a.require([{k:r[k] for k in ['condition','name','case_id']} for r in saved_rows] == expected, 'Changed observation schedule')
        for saved, prior in zip(saved_rows, old['cases']):
            case = cases[saved['case_id']]
            context_path = 'freeze/contexts/' + case['id'] + '-' + saved['condition'] + '.json'
            context = read(context_path)
            row = a.analyze_row(saved, case, context, a.source_facts(case, context, data, table), audit[case['id']], run)
            row['raw_evidence_path'] = 'run/diagnostic/' + row['condition'] + '/' + row['name']
            row['independent_human_judgment'] = None
            if not row['completed']:
                for key in ['exact_exposed_reference_agreement', 'accepted_exposed_reference_agreement',
                    'correct_model_clarification', 'AI_source_audit_clarification_agreement', 'incorrect_guess',
                    'wrong_but_executable', 'field_agreement']:
                    row[key] = None
            if row['rust_accepted'] is None:
                row['rust_rejection'] = None
            if row['raw_sha256']:
                note = notes[row['condition'] + '/' + row['name']]
                a.require(note['raw_sha256'] == row['raw_sha256'] and note['context_sha256'] == a.digest(payload[context_path]), 'Unbound source inspection')
                row['source_investigator_review'] = note
            else:
                row['source_investigator_review'] = None
            row['baseline'] = {k: prior[k] for k in ['completed', 'model_origin_status', 'reference_status',
                'accepted_exposed_reference_agreement', 'field_agreement', 'raw_sha256', 'rationale', 'investigator_note']}
            a.require(all(row[k] == prior[k] for k in ['condition', 'name', 'case_id']), 'Changed paired identity')
            rows.append(row)
        a.require(state['diagnostic']['attempted'] == sum(r['generation_attempted'] for r in rows)
            and state['diagnostic']['completed'] == sum(r['completed'] for r in rows), 'Diagnostic count mismatch')
        conditions = {}
        for condition in ['oracle', 'retrieval']:
            selected = [r for r in rows if r['condition'] == condition]
            forbidden = [r for r in selected if r['reference_status'] == 'unsupported']
            clarify = [r for r in selected if r['reference_status'] == 'needs_clarification']
            score = lambda group, status: dict(scheduled=len(group), completed=sum(r['completed'] for r in group),
                correct=sum(r['model_origin_status'] == status for r in group if r['completed']) if any(r['completed'] for r in group) else None,
                baseline_correct=sum(r['baseline']['model_origin_status'] == status for r in group),
                identities=[dict(name=r['name'], baseline=r['baseline']['model_origin_status'], new=r['model_origin_status'], completed=r['completed']) for r in group])
            candidates = [r for r in selected if r['reference_status'] == 'candidate']
            conditions[condition] = dict(scheduled=len(selected), attempted=sum(r['generation_attempted'] for r in selected),
                completed=sum(r['completed'] for r in selected), fatal_failed=sum(r['status']=='fatal_failure' for r in selected),
                unattempted=sum(not r['generation_attempted'] for r in selected), statuses=dict(Counter(r['model_origin_status'] for r in selected)),
                unsupported=score(forbidden, 'unsupported'), genuine_clarification=score(clarify, 'needs_clarification'),
                paired_completed=sum(r['completed'] and r['baseline']['completed'] for r in selected),
                candidate_abstentions=[r['name'] for r in candidates if r['completed'] and r['model_origin_status'] in ['unsupported','needs_clarification']],
                lost_baseline_valid_candidates=[r['name'] for r in candidates if r['completed'] and r['baseline']['accepted_exposed_reference_agreement'] is True and r['accepted_exposed_reference_agreement'] is not True],
                baseline_valid_candidates_not_completed=[r['name'] for r in candidates if not r['completed'] and r['baseline']['accepted_exposed_reference_agreement'] is True],
                five_fields={k:a.rate([r['field_agreement'][k] if r['field_agreement'] else None for r in candidates]) for k in a.PLAN_FIELDS},
                directions={direction:dict(scheduled=sum(r['reference_direction']==direction for r in candidates),
                    failures=[r['name'] for r in candidates if r['reference_direction']==direction and r['completed'] and r['exact_exposed_reference_agreement'] is False],
                    unmeasured=[r['name'] for r in candidates if r['reference_direction']==direction and not r['completed']]) for direction in ['forward','reverse']})
        return dict(version='qwen-status-precedence-first-run-analysis-v1', decision='INCONCLUSIVE_REVISE',
            independent_human_review='pending', issue83='open', issue75_integration='disabled',
            semantic_correctness=None, model_superiority=None, product_readiness=None,
            analyzer_invokes_models=False, model_generated_rdf_executions=0,
            authorization=auth, status=state['status'], error=state.get('error'),
            generation_attempts=state['generation_attempts'], generation_completed=state['generation_completed'],
            diagnostic_attempted=state['diagnostic']['attempted'], diagnostic_completed=state['diagnostic']['completed'],
            diagnostic_unattempted=sum(not r['generation_attempted'] for r in rows),
            diagnostic_fatal_failed=sum(r['status']=='fatal_failure' for r in rows),
            native_controls=state['checks'], native_grammar_controls=grammar_controls, native_streams=streams, conditions=conditions,
            resources=dict(model_loaded=state['model_loaded'], startup_ms=state.get('startup_ms'),
                host_captured_at=host['captured_at'], host_swap_used_mib=host['swap_used_mib'], host_blockers=host['blockers'],
                process_tree_rss=state['process_tree_rss'], first_rss_sample=samples[0] if samples else None),
            cases=rows, rationale_review_origin='Every retained semantic response inspected by coding agent against supplied context; not independent human review. Narrow automatic checks retained separately.',
            source_table_rationale_contradiction_witnesses=[dict(condition=r['condition'],name=r['name'],
                raw_sha256=r['raw_sha256'],**w) for r in rows if r['source_investigator_review']
                for w in r['source_investigator_review']['contradictions']],
            input_identity=dict(evidence_archive_sha256=manifest['archive_sha256'],
                registration_sha256=a.digest(payload['registration.json']), freeze_sha256=registration['freeze_sha256'],
                baseline_archive_sha256=old['input_identity']['archive_sha256'], scorer_sha256=a.digest(Path(a.__file__).read_bytes()),
                analyzer_sha256=a.digest(Path(__file__).read_bytes())))


def markdown(result):
    lines = ['# Full scheduled status-precedence comparison', '',
        '**INCONCLUSIVE_REVISE; independent human review pending.**', '',
        'BM25-v1 is stored as `retrieval`. Missing outcomes remain null. '
        'Reference agreement and Rust acceptance do not establish semantic correctness.', '',
        '| Condition | Scheduled | Attempted | Completed | Fatal failures | Unattempted | Unsupported: baseline → new / 6 scheduled | Clarification: baseline → new / 3 scheduled |',
        '|---|---:|---:|---:|---:|---:|---|---|']
    number = lambda n: 'null' if n is None else str(n)
    for condition, c in result['conditions'].items():
        u, q = c['unsupported'], c['genuine_clarification']
        lines.append(f"| {condition} | {c['scheduled']} | {c['attempted']} | {c['completed']} | {c['fatal_failed']} | {c['unattempted']} | {u['baseline_correct']} → {number(u['correct'])}; {u['completed']}/6 completed | {q['baseline_correct']} → {number(q['correct'])}; {q['completed']}/3 completed |")
    lines += ['', 'Field order: start / predicate / graph / direction / output (values projection). '
        'T/F records exposed-reference agreement, including completed abstentions. '
        'Missing comparisons are null.', '',
        '| Condition / observation | Reference / direction | Baseline model status | New state / model status | Rust accepted | Baseline five fields | New five fields |',
        '|---|---|---|---|---|---|---|']
    for r in result['cases']:
        display = lambda fields: '/'.join('T' if fields[k] else 'F' for k in a.PLAN_FIELDS) if fields else 'null'
        lines.append(f"| {r['condition']} / {r['name']} | {r['reference_status']} / {r['reference_direction'] or 'n/a'} | {r['baseline']['model_origin_status']} | {r['status']} / {r['model_origin_status'] or 'null'} | {r['rust_accepted']} | {display(r['baseline']['field_agreement'])} | {display(r['field_agreement'])} |")
    lines += ['', 'All original references and the separate four-case AI ambiguity audit remain unchanged. '
        'Every retained response has a hash-bound source-inspection note in `analysis.json`; '
        'explicit contradiction witnesses are separate from five-field plan agreement.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    with patch('subprocess.Popen', side_effect=AssertionError('Model-free analysis cannot start subprocesses')):
        result = analyze()
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if sys.argv[1:] == ['--check']:
        a.require((REPORT / 'analysis.json').read_text() == rendered, 'Analysis reproduction drift')
        a.require((REPORT / 'comparison.md').read_text() == markdown(result), 'Comparison reproduction drift')
        print('PASS: exact model-free analysis reproduction; no subprocesses or models')
    else:
        a.require(not sys.argv[1:], 'Only --check supported')
        (REPORT / 'analysis.json').write_text(rendered)
        (REPORT / 'comparison.md').write_text(markdown(result))
