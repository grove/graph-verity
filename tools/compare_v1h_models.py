#!/usr/bin/env python3
"""Reproduce the retained Qwen/Gemma comparison without models, processes or RDF queries."""
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

from rdflib import Dataset

import analyze_v1f as a
import analyze_v1h_qwen as q
from compact_ab import archive_files

REPORT = a.ROOT / 'experiments/native-one-hop-v1h-budget-gemma4-swap2048-evidence'
VARIANT = a.ROOT / 'experiments/native-one-hop-v1h-budget-swap2048/registration.json'
COMMAND = ('.venv/bin/python tools/native_one_hop_v1h_swap2048.py run \\\n'
           '  --freeze artifacts/v1h-budget \\\n'
           '  --allow-inference \\\n'
           '  --out artifacts/issue83-v1h-budget-gemma4-swap2048-first\n')


def annotation(saved, row, context):
    if saved is None:
        return dict(note=row.get('investigator_note') or 'No additional source-bound annotation; unrestricted rationale correctness is unassessed.', findings=[])
    a.require(saved['raw_sha256'] == row['raw_sha256'], 'Source note/raw mismatch')
    a.require(saved['context_sha256'] == a.digest(json.dumps(context, ensure_ascii=False, indent=2).encode() + b'\n'),
              'Source note/context mismatch')
    for finding in saved['findings']:
        value = context
        for key in finding['source_path']:
            value = value[key]
        a.require(value == finding['source_value'] and value != finding['asserted_value'], 'Source finding/witness mismatch')
        a.require(finding['excerpt'] in (row.get('rationale_text') or ''), 'Source finding/excerpt mismatch')
    return saved


def retain_missing_semantics(row):
    fields = ['exact_exposed_reference_agreement', 'accepted_exposed_reference_agreement', 'wrong_but_executable',
              'correct_model_clarification', 'AI_source_audit_clarification_agreement', 'incorrect_guess', 'field_agreement']
    row['raw_output_reference_diagnostic'] = {key: row[key] for key in fields} if not row['completed'] else None
    if not row['completed']:
        for key in fields:
            row[key] = None
    return row


def native_integrity(run, state, budgets):
    requests = sorted(run.rglob('completion-request.json'))
    a.require(state['generation_attempts'] == len(requests) <= 38, 'Request accounting mismatch')
    streams = []
    for request in requests:
        dest = request.parent
        condition = 'sampling' if dest.parent.name == 'controls' else dest.parent.name
        expected = next(b['columnar'] for b in budgets if (b['condition'], b['name']) == (condition, dest.name))
        native, parity = a.read(dest / 'native-template.stdout'), a.read(dest / 'parity.json')
        a.require(parity['token_ids_equal'] and parity['prompt_bytes_equal'], 'Retained native parity failure')
        a.require(native['tokens'] == a.read(request)['prompt'] == expected['tokens']
                  and (dest / 'prompt.txt').read_bytes() == native['prompt'].encode() == expected['prompt'].encode(),
                  'Registered native prompt/token mismatch')
        a.require(a.read(dest / 'parity-tokens.http.json')['tokens'] == native['tokens']
                  and parity['restored_bos'] + a.read(dest / 'parity-template.http.json')['prompt'] == native['prompt'],
                  'Native HTTP parity mismatch')
        stream, proposal = dest / 'completion.http.sse', dest / 'proposal.txt'
        events, error = [], None
        try:
            if stream.exists():
                events = [json.loads(line[5:].strip()) for line in stream.read_bytes().splitlines() if line.startswith(b'data:')]
        except (ValueError, UnicodeDecodeError) as failure:
            error = type(failure).__name__ + ': ' + str(failure)
        if error is None and proposal.exists():
            a.require(b''.join(e.get('content', '').encode() for e in events) == proposal.read_bytes(), 'SSE/raw mismatch')
        streams.append(dict(path=str(dest.relative_to(run)), terminal=bool(events and events[-1].get('stop') is True),
            stream_present=stream.exists(), stream_error=error, proposal_present=proposal.exists(),
            raw_sha256=a.digest(proposal.read_bytes()) if proposal.exists() else None))
    a.require(sum(s['terminal'] for s in streams) == state['generation_completed'], 'Terminal stream accounting mismatch')
    return dict(generation_attempts=state['generation_attempts'], generation_completed=state['generation_completed'],
                sampling_controls=state['checks'], grammar_controls=a.read(run / 'grammar-controls/controls.json'), streams=streams)


def summarize(rows):
    result = a.summarize(rows)
    completed = [r for r in rows if r['completed']]
    result['completed_unsupported_classification'] = a.rate([r['model_origin_status'] == 'unsupported'
        for r in completed if r['reference_status'] == 'unsupported'])
    result['completed_model_clarification_on_reference_cases'] = a.rate([r['model_origin_status'] == 'needs_clarification'
        for r in completed if r['reference_status'] == 'needs_clarification'])
    result['completed_model_clarification_on_AI_ambiguity_cases'] = a.rate([r['model_origin_status'] == 'needs_clarification'
        for r in completed if r['AI_source_question_group'] == 'ambiguous'])
    result['completed_status_counts'] = dict(sorted(Counter(r['model_origin_status'] for r in completed).items()))
    result['source_bound_agent_findings'] = sum(len(r['source_annotation']['findings']) for r in rows)
    result['observations_with_source_bound_agent_findings'] = sum(bool(r['source_annotation']['findings']) for r in rows)
    result['distinct_response_hashes_with_source_bound_agent_findings'] = len({r['raw_sha256'] for r in rows
        if r['source_annotation']['findings']})
    result['independent_human_judgments'] = 0
    return result


def analyze(report=REPORT):
    manifest = a.read(report / 'evidence-files.json')
    a.require(a.digest((report / 'evidence.tar.gz').read_bytes()) == manifest['archive_sha256'], 'Changed Gemma evidence archive')
    payload = archive_files(report / 'evidence.tar.gz')
    a.require({n: a.digest(raw) for n, raw in payload.items()} == manifest['files'], 'Gemma archive inventory mismatch')
    parent, variant = json.loads(payload['registration.json']), json.loads(payload['variant-registration.json'])
    a.require(parent == a.read(q.REGISTRATION) and variant == a.read(VARIANT), 'Changed registered protocol')
    frozen = parent['freeze_manifest']
    cfg = frozen['config']
    a.require(variant['parent_registration_sha256'] == a.digest(payload['registration.json'])
              and variant['parent_freeze_sha256'] == parent['freeze_sha256']
              and variant['parent_freeze_archive_sha256'] == parent['archive_sha256']
              and variant['effective_config'] == {**cfg, 'host_gates': {**cfg['host_gates'], 'swap_used_mib_max': 2048}},
              'Variant exceeds the single registered host-gate change')
    a.require(a.digest(payload['registered-freeze.tar.gz']) == parent['archive_sha256'], 'Changed original freeze archive')
    for name, digest in {**frozen['input_sha256'], **variant['source_input_sha256']}.items():
        a.require(a.digest(payload['source/' + name]) == digest, 'Changed registered source: ' + name)
    for name in ['tools/compare_v1h_models.py', 'tools/analyze_v1f.py', 'tools/analyze_v1h_qwen.py']:
        a.require(payload['source/' + name] == (a.ROOT / name).read_bytes(), 'Analysis source differs: ' + name)
    auth = json.loads(payload['authorization.json'])
    a.require(auth['owner_message_exact'] == 'I authorize it' and auth['proposal_command_exact'] == COMMAND
              and auth['registration_sha256'] == a.digest(payload['variant-registration.json'])
              and auth['parent_registration_sha256'] == variant['parent_registration_sha256']
              and auth['freeze_checksums_sha256'] == parent['freeze_sha256']
              and auth['freeze_archive_sha256'] == parent['archive_sha256']
              and auth['registered_binary_sha256'] == frozen['binary_sha256']
              and auth['model'] == 'gemma4' and auth['maximum_requests'] == 38 and auth['retries'] == 0
              and auth['sampling_controls'] == 2 and auth['semantic_observations'] == 36 and auth['swap_ceiling_mib'] == 2048
              and auth['output_absent_at_receipt'] and 'gemma4' not in auth['prior_attempts'], 'Gemma authorization mismatch')
    qwen = q.analyze()
    a.require(qwen == a.read(q.REPORT / 'analysis.json'), 'Historical Qwen analysis drift')
    qwen_bytes = archive_files(q.REPORT / 'evidence.tar.gz')
    notes = json.loads(payload['operator/source-audit-notes.json'])
    with tempfile.TemporaryDirectory(prefix='v1h-model-comparison-') as temp:
        root = Path(temp)
        for name, raw in payload.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        freeze, outer, run = root / 'freeze', root / 'variant', root / 'variant/run'
        a.require(a.read(freeze / 'freeze.json') == frozen and a.inventory(freeze) == a.read(freeze / 'checksums.json')
                  and a.digest((freeze / 'checksums.json').read_bytes()) == parent['freeze_sha256'], 'Frozen input mismatch')
        a.require({str(p.relative_to(outer)): a.digest(p.read_bytes()) for p in outer.rglob('*')
                   if p.is_file() and p != outer / 'checksums.json'} == a.read(outer / 'checksums.json'), 'Variant inventory mismatch')
        a.require(a.read(outer / 'variant-registration.json') == variant, 'Outer registration mismatch')
        a.require(a.inventory(run) == a.read(run / 'checksums.json'), 'Inner run inventory mismatch')
        state, envelope = a.read(run / 'run.json'), a.read(outer / 'variant.json')
        a.require(envelope['version'] == variant['version'] and envelope['status'] == state['status']
                  and state['version'] == parent['version'] and state['model'] == 'gemma4'
                  and state['freeze_sha256'] == parent['freeze_sha256'] and state['executions'] == 0
                  and not state['integration_authorized'] and not state['holdout_accessed'], 'Run identity/authority mismatch')
        a.require(all(envelope[k] == state[k] for k in ['generation_attempts', 'generation_completed']), 'Outer/inner accounting mismatch')
        a.require(json.loads(payload['attempt-ledger.json']) == ['qwen35', 'gemma4'], 'Shared no-retry ledger mismatch')
        expected = a.schedule(cfg)
        saved = state['diagnostic']['cases']
        a.require([{k: r[k] for k in ('condition', 'name', 'case_id')} for r in saved] == expected,
                  'Changed diagnostic schedule')
        a.require(state['diagnostic']['attempted'] == sum(r['generation_attempted'] for r in saved)
                  and state['diagnostic']['completed'] == sum(r['status'] in a.TERMINAL for r in saved)
                  and state['diagnostic']['denominator'] == len(expected) == 36, 'Diagnostic accounting mismatch')
        tokens = a.read(freeze / 'tokenization/counts.json')
        budgets = tokens['models']['gemma4']['rows']
        preload = a.read(run / 'preload-token-budget/counts.json')
        a.require(all(preload[k] == tokens[k] for k in ['python', 'packages']), 'Tokenizer environment mismatch')
        fresh = preload['models']['gemma4']['rows']
        a.require(len(fresh) == len(budgets) == 38, 'Preload budget schedule mismatch')
        for old, new in zip(budgets, fresh):
            a.require(all(old[k] == new[k] for k in ['condition', 'name', 'case_id', 'kind'])
                      and all(old[v][k] == new[v][k] for v in ['original', 'columnar']
                              for k in ['tokens', 'prompt', 'tokens_sha256', 'prompt_sha256', 'input_tokens', 'output_reserve', 'total_required', 'fits'])
                      and new['columnar']['total_required'] == len(new['columnar']['tokens']) + 512 < 16384, 'Exact budget mismatch')
        assets = a.read(run / 'assets.json')
        a.require({k: assets[k] for k in frozen['runtime_identity']} == frozen['runtime_identity'], 'Native asset identity mismatch')
        host, original_host = a.read(run / 'host.json'), a.read(run / 'host-original-1024.json')
        a.require(host['host_gate_variant'] == variant['version'] and not host['blockers']
                  and host['effective_host_gates'] == variant['effective_config']['host_gates']
                  and host['original_blockers'] == original_host['blockers']
                  and all(host[k] == value for k, value in original_host.items() if k != 'blockers'), 'Host gate receipt mismatch')
        cases = {c['id']: c for c in a.read(root / 'source/studies/nl-ask-v1/cases.json') if c['split'] == 'evaluation'}
        cases.update({c['id']: c for c in a.read(root / 'source' / cfg['fixture_file'])})
        audit = a.read(root / 'source/configs/native-one-hop-v1f-diagnostic.audit.json')['cases']
        data = Dataset()
        data.parse(root / 'source/studies/nl-ask-v1/evaluation/snapshot.nq', format='nquads')
        table = a.read(root / 'source/studies/nl-ask-v1/evaluation/catalog.json')
        rows = []
        for observation in saved:
            case = cases[observation['case_id']]
            context = a.read(freeze / 'contexts' / f"{case['id']}-{observation['condition']}.json")
            row = retain_missing_semantics(a.analyze_row(observation, case, context,
                a.source_facts(case, context, data, table), audit[case['id']], run))
            row.update(model='gemma4', independent_human_judgment=None,
                       raw_evidence_path=f"variant/run/diagnostic/{row['condition']}/{row['name']}")
            proposal = run / 'diagnostic' / row['condition'] / row['name'] / 'proposal.txt'
            draft = a.strict_draft(proposal.read_bytes()) if proposal.exists() else None
            row['rationale_text'] = draft['rationale'] if draft else None
            row['source_annotation'] = annotation(notes['gemma4'].get(row['condition'] + '/' + row['name']), row, context)
            rows.append(row)
        for old in qwen['cases']:
            row = dict(old)
            context = a.read(freeze / 'contexts' / f"{row['case_id']}-{row['condition']}.json")
            key = row['condition'] + '/' + row['name']
            raw = qwen_bytes.get('run/diagnostic/' + key + '/proposal.txt')
            draft = a.strict_draft(raw) if raw is not None else None
            row['rationale_text'] = draft['rationale'] if draft else None
            row['source_annotation'] = annotation(notes['qwen35'].get(key), row, context)
            rows.append(row)
        integrity = native_integrity(run, state, budgets)
        resources = dict(startup_ms=state.get('startup_ms'), process_tree_rss=state['process_tree_rss'], host=host,
                         repeatability=state['diagnostic']['repeatability'])
    summaries = {model: {condition: summarize([r for r in rows if r['model'] == model and r['condition'] == condition])
                 for condition in cfg['stages']} for model in ['qwen35', 'gemma4']}
    strata = {model: {condition: {field: {str(value): summarize([r for r in rows if r['model'] == model
        and r['condition'] == condition and r[field] == value])
        for value in sorted({r[field] for r in rows if r['model'] == model and r['condition'] == condition}, key=str)}
        for field in ['reference_direction', 'reference_group', 'AI_source_question_group']}
        for condition in cfg['stages']} for model in ['qwen35', 'gemma4']}
    paired = []
    for left in [r for r in rows if r['model'] == 'qwen35']:
        right = next(r for r in rows if r['model'] == 'gemma4' and (r['condition'], r['name']) == (left['condition'], left['name']))
        fields = ['generation_attempted', 'completed', 'status', 'model_origin_status', 'exact_exposed_reference_agreement',
                  'rust_accepted', 'field_agreement', 'raw_sha256']
        paired.append(dict(condition=left['condition'], name=left['name'], case_id=left['case_id'],
                           reference_status=left['reference_status'], reference_direction=left['reference_direction'],
                           AI_source_question_group=left['AI_source_question_group'],
                           qwen35={k: left[k] for k in fields}, gemma4={k: right[k] for k in fields}))
    paired_completed = {}
    for condition in cfg['stages']:
        names = [p['name'] for p in paired if p['condition'] == condition
                 and p['qwen35']['completed'] and p['gemma4']['completed']]
        paired_completed[condition] = dict(observations=names, models={model: summarize([r for r in rows
            if r['model'] == model and r['condition'] == condition and r['name'] in names])
            for model in ['qwen35', 'gemma4']})
    return dict(version='v1h-qwen-gemma-comparison-v1', decision='INCONCLUSIVE_REVISE', semantic_go=False,
        independent_human_review='deferred', model_ranking=None, exact_answer_accuracy=None,
        inference_performed_by_analyzer=False, model_generated_rdf_executions=0,
        source_annotation_method=dict(origin='coding-agent source inspection; not independent human review',
            findings='Hard source-table mismatches only: exact raw excerpt plus an asserted value conflicting with an exact supplied source field.',
            notes='Also retain missing identity/meaning evidence and interpretation limits; those are not counted as hard table mismatches.'),
        input_identity=dict(gemma_archive_sha256=manifest['archive_sha256'], qwen_archive_sha256=qwen['input_identity']['archive_sha256'],
            parent_registration_sha256=variant['parent_registration_sha256'], variant_registration_sha256=a.digest(payload['variant-registration.json']),
            analyzer_sha256=a.digest(Path(__file__).read_bytes()), scorer_sha256=a.digest(Path(a.__file__).read_bytes())),
        authorization=auth, run_status=state['status'], error=state.get('error'), gemma_native_integrity=integrity,
        qwen_native_integrity=qwen['native_integrity'],
        gemma_resources=resources, qwen_resources=qwen['resources'],
        gemma_context_budgets=[{**{k: b[k] for k in ['condition', 'name', 'case_id', 'kind']},
            **{v: {k: b[v][k] for k in ['input_tokens', 'output_reserve', 'total_required', 'fits', 'prompt_sha256', 'tokens_sha256']}
               for v in ['original', 'columnar']}} for b in budgets],
        tokenizer_environment={k: tokens[k] for k in ['packages', 'python']}, summary=summaries, diagnostic_strata=strata,
        paired_observations=paired, paired_completed_comparison=paired_completed, cases=rows,
        limitations=['Gemma uses the separately registered 2048 MiB swap admission ceiling; Qwen used 1024 MiB. Frozen context information and schedules match between models within each condition; model/tokenizer identities differ as registered.',
            'Model timing and RSS differences are confounded by admission rules, host/cache state and tokenization; no causal model ranking.',
            'Exposed-reference agreement and Rust acceptance are not independently established semantic correctness or answer accuracy.',
            'Source-bound annotations are coding-agent observations tied to raw excerpts and exact supplied source values, not independent human judgments.',
            'Automatic rationale rules recognize narrow whole English ID assertions only; zero matches does not validate other prose.',
            'Completed classification rates exclude runtime failures and missing responses; all attempts, failures and unattempted schedules remain separate.',
            'Incomplete/fatal Gemma semantic fields stay null; any raw-output reference diagnostic is retained separately and excluded from primary semantic rates.',
            'Missing measurements remain null. Repeated observations are correlated, and references are exposed AI-authored fixtures.',
            'No model proposal is executed as RDF; retained source witnesses enumerate triples only.',
            'RSS is a sampled concurrent process-tree run peak, not a per-case isolated peak; sampling can miss peaks or double-count shared pages.'])


def fraction(metric):
    return 'unmeasured' if metric['numerator'] is None else f"{metric['numerator']}/{metric['denominator']}"


def measured_seconds(distribution, percentile):
    value = distribution[percentile]
    return 'unmeasured' if value is None else f'{value / 1000:.2f}'


def markdown(result):
    lines = ['# Retained Qwen / Gemma v1h comparison', '',
        '**INCONCLUSIVE_REVISE. Independent human review deferred.**', '',
        'Qwen retains the original 1024 MiB swap gate; Gemma uses the separately registered 2048 MiB variant.',
        '`retrieval` denotes the unchanged frozen whole-question BM25-v1 condition.',
        'All reference agreement is against exposed AI-authored fixtures. No model ranking or exact-answer accuracy is inferred.', '',
        '| Model / condition | Attempted / scheduled | Completed | Unattempted | Reference agreement, completed | Unsupported classification, completed | Clarification on reference cases, completed |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for model, conditions in result['summary'].items():
        for condition, s in conditions.items():
            lines.append(f"| {model} / {condition} | {s['attempted']}/{s['scheduled']} | {s['completed']} | {s['unattempted']} | "
                f"{fraction(s['metrics']['exact_exposed_reference_agreement'])} | {fraction(s['completed_unsupported_classification'])} | "
                f"{fraction(s['completed_model_clarification_on_reference_cases'])} |")
    lines += ['', 'Paired-completed subsets below compare exactly the same completed observation identities. Full failures and missing observations remain in the schedules above.', '',
              '| Condition | Completed pairs | Qwen reference agreement | Gemma reference agreement |',
              '|---|---:|---:|---:|']
    for condition, paired in result['paired_completed_comparison'].items():
        left, right = paired['models']['qwen35'], paired['models']['gemma4']
        lines.append(f"| {condition} | {len(paired['observations'])} | {fraction(left['metrics']['exact_exposed_reference_agreement'])} | "
                     f"{fraction(right['metrics']['exact_exposed_reference_agreement'])} |")
    lines += ['', '| Model / condition | Forward candidate reference agreement | Reverse candidate reference agreement | AI ambiguity clarification, completed | Hard table-mismatch observations / distinct responses |',
              '|---|---:|---:|---:|---:|']
    for model, conditions in result['summary'].items():
        for condition, s in conditions.items():
            directions = result['diagnostic_strata'][model][condition]['reference_direction']
            forward = directions.get('forward', {}).get('metrics', {}).get('exact_exposed_reference_agreement', dict(numerator=None, denominator=0))
            reverse = directions.get('reverse', {}).get('metrics', {}).get('exact_exposed_reference_agreement', dict(numerator=None, denominator=0))
            lines.append(f"| {model} / {condition} | {fraction(forward)} | {fraction(reverse)} | "
                f"{fraction(s['completed_model_clarification_on_AI_ambiguity_cases'])} | {s['observations_with_source_bound_agent_findings']} / {s['distinct_response_hashes_with_source_bound_agent_findings']} |")
    lines += ['', '## Native controls, time and resources', '',
        'The two native sampling controls are outside the semantic denominator. Sampled RSS is a whole-run process-tree peak.', '',
        '| Model | Native requests / completed | Sampling controls measured / passed | Sampled peak GiB |',
        '|---|---:|---:|---:|']
    for model, native, resources in [('qwen35', result['qwen_native_integrity'], result['qwen_resources']),
                                     ('gemma4', result['gemma_native_integrity'], result['gemma_resources'])]:
        controls = list(native['sampling_controls'].values())
        measured = sum(c['status'] == 'measured' for c in controls)
        passed = sum(c.get('passed') is True for c in controls)
        peak = resources['process_tree_rss']['peak_kib'] / 2**20
        lines.append(f"| {model} | {native['generation_attempts']} / {native['generation_completed']} | {measured} / {passed} | {peak:.3f} |")
    lines += ['', '| Model / condition | Observation latency samples | p50 seconds | p95 seconds | Native-generation latency samples | Native p50 seconds | Native p95 seconds |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for model, conditions in result['summary'].items():
        for condition, s in conditions.items():
            total, native = s['observation_latency_ms'], s['native_generation_latency_ms']
            lines.append(f"| {model} / {condition} | {total['samples']} | {measured_seconds(total, 'p50')} | {measured_seconds(total, 'p95')} | "
                         f"{native['samples']} | {measured_seconds(native, 'p50')} | {measured_seconds(native, 'p95')} |")
    lines += ['', 'Runtime elapsed includes template/token parity and completion; native prompt/decode timings are retained separately in the machine report and raw streams.',
              'Different swap admission, tokenization, cache reuse and uncontrolled host state prevent causal timing/RSS comparisons.']
    lines += ['', '## Every paired semantic observation', '',
        '| Condition / observation | Exposed reference / AI source group | Qwen status | Gemma status | Qwen reference agreement | Gemma reference agreement |',
        '|---|---|---|---|---|---|']
    for p in result['paired_observations']:
        lines.append(f"| {p['condition']} / {p['name']} | {p['reference_status']} {p['reference_direction'] or ''} / {p['AI_source_question_group']} | "
                     f"{p['qwen35']['model_origin_status']} | {p['gemma4']['model_origin_status']} | "
                     f"{p['qwen35']['exact_exposed_reference_agreement']} | {p['gemma4']['exact_exposed_reference_agreement']} |")
    lines += ['', '## Measurement limits', ''] + ['- ' + limit for limit in result['limitations']]
    return '\n'.join(lines) + '\n'


def failure_matrix(result):
    lines = ['# Every retained semantic observation', '', '**INCONCLUSIVE_REVISE. Human judgments remain null.**', '',
        'Source annotations are source-bound coding-agent observations, not independent human review.', '',
        '| Model / condition / observation | Exposed reference | Attempted | Outcome | Model status | Rust accepted | Reference agreement | Source-bound note |',
        '|---|---|---|---|---|---|---|---|']
    for row in result['cases']:
        note = row['source_annotation']['note'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {row['model']} / {row['condition']} / {row['name']} | {row['reference_status']} {row['reference_direction'] or ''} | "
                     f"{row['generation_attempted']} | {row['status']} | "
                     f"{row['model_origin_status']} | {row['rust_accepted']} | {row['exact_exposed_reference_agreement']} | {note} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=REPORT)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    a.require(not args.out.exists(), 'Never overwrite an analysis')
    result = analyze(args.report)
    args.out.mkdir(parents=True)
    for name, content in [('analysis.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n'),
                          ('comparison.md', markdown(result)), ('failure-matrix.md', failure_matrix(result))]:
        (args.out / name).write_text(content)


if __name__ == '__main__':
    main()
