"""Reproduce the blocked admission outcome without models or subprocesses."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from compact_ab import archive_files
import analyze_v1h_qwen as baseline

REPORT = Path(__file__).resolve().parent
REGISTRATION = ROOT / 'experiments/native-one-hop-v1h-qwen-status-precedence/registration.json'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def analyze():
    manifest = json.loads((REPORT / 'evidence-files.json').read_bytes())
    assert sha((REPORT / 'evidence.tar.gz').read_bytes()) == manifest['archive_sha256']
    payload = archive_files(REPORT / 'evidence.tar.gz')
    assert {name: sha(raw) for name, raw in payload.items()} == manifest['files']
    read = lambda name: json.loads(payload[name])
    registration = read('registration.json')
    assert payload['registration.json'] == REGISTRATION.read_bytes()
    assert read('freeze/freeze.json') == registration['freeze_manifest']
    assert sha(payload['freeze/checksums.json']) == registration['freeze_sha256']
    assert {name.removeprefix('freeze/'): sha(raw) for name, raw in payload.items()
            if name.startswith('freeze/') and name != 'freeze/checksums.json'} == read('freeze/checksums.json')
    assert all(sha(payload['source/' + name]) == digest
               for name, digest in registration['freeze_manifest']['input_sha256'].items())
    pr = read('operator/pr97-verification.json')
    assert pr['headRefOid'] == 'e540f90e7624ef63cc031128a0704b1222450082'
    assert pr['statusCheckRollup'] and all(c['conclusion'] == 'SUCCESS' for c in pr['statusCheckRollup'])
    gate, host = read('operator/gate-results.json'), read('operator/host.json')
    assert gate == dict(status='blocked', model_loaded=False, generation_attempts=0, retries=0, blockers=host['blockers'])
    assert host['blockers'] == [dict(metric='swap_used_mib', observed=2519.38, threshold=1024,
                                   reason='host_contention_or_resources')]
    assert registration['freeze_manifest']['config']['host_gates']['swap_used_mib_max'] == 1024
    assert read('operator/token-recount/counts.json') == read('freeze/tokenization/counts.json')
    assets = read('operator/assets.json')
    assert all(assets[k] == v for k, v in registration['freeze_manifest']['runtime_identity'].items())
    grammar = read('operator/grammar-controls/controls.json')
    assert grammar['accepted'] == grammar['expected'] and len(grammar['accepted']) == 12
    before, after = read('operator/before-attempt.json'), read('operator/after-attempt.json')
    assert not before['ledger_exists'] and not before['output_exists']
    assert not after['ledger_exists'] and not after['output_exists']
    assert not any(name.endswith(('completion-request.json', 'completion.http.sse', 'proposal.txt', 'run.json')) for name in payload)
    old = baseline.analyze()
    assert old == json.loads((baseline.REPORT / 'analysis.json').read_bytes())
    schedule = read('freeze/schedule.json')
    assert len(schedule) == 38 and schedule[:2] == registration['schedule'][:2]
    assert schedule == registration['schedule']
    comparisons = []
    for row, prior in zip(schedule[2:], old['cases']):
        assert all(row[k] == prior[k] for k in ['condition', 'name', 'case_id'])
        comparisons.append(dict(**row, status='unattempted', generation_attempted=False,
            model_origin_status=None, completed=False, reference_status=prior['reference_status'],
            reference_direction=prior['reference_direction'],
            field_agreement={k: None for k in baseline.a.PLAN_FIELDS},
            exact_exposed_reference_agreement=None, supported_candidate_regression=None,
            source_table_rationale_contradiction=None, independent_human_judgment=None,
            baseline={k: prior[k] for k in ['model_origin_status', 'reference_status', 'reference_direction',
                'field_agreement', 'exact_exposed_reference_agreement', 'accepted_exposed_reference_agreement',
                'rationale', 'raw_sha256', 'investigator_note']}))
    conditions = {}
    for condition, count in [('oracle', 19), ('retrieval', 17)]:
        rows = [r for r in comparisons if r['condition'] == condition]
        unsupported = [r for r in rows if r['reference_status'] == 'unsupported']
        clarification = [r for r in rows if r['reference_status'] == 'needs_clarification']
        assert len(rows) == count and len(unsupported) == 6 and len(clarification) == 3
        unsupported_hits = sum(r['baseline']['model_origin_status'] == 'unsupported' for r in unsupported)
        clarification_hits = sum(r['baseline']['model_origin_status'] == 'needs_clarification' for r in clarification)
        assert unsupported_hits == (2 if condition == 'oracle' else 4) and clarification_hits == 3
        conditions[condition] = dict(scheduled=count, completed=0, failed=0, unattempted=count, paired_completed=0,
            unsupported=dict(scheduled=6, baseline_correct=unsupported_hits, new_correct=None, new_measured=0),
            genuine_clarification=dict(scheduled=3, baseline_correct=3, new_correct=None, new_measured=0),
            supported_candidate_regressions=None,
            baseline_valid_candidates=[r['name'] for r in rows if r['reference_status'] == 'candidate'
                                       and r['baseline']['accepted_exposed_reference_agreement'] is True],
            directions={direction: dict(scheduled=sum(r['reference_direction'] == direction for r in rows),
                baseline_reference_failures=[r['name'] for r in rows if r['reference_direction'] == direction
                    and r['baseline']['exact_exposed_reference_agreement'] is False], new_failures=None)
                for direction in ['forward', 'reverse']})
    # A table contradiction remains a contradiction even when all five plan fields match.
    prior_bytes = archive_files(baseline.REPORT / 'evidence.tar.gz')
    path = 'run/diagnostic/retrieval/smoke-v1e-country-paraphrase-en/'
    raw = prior_bytes[path + 'proposal.txt']
    context = json.loads(prior_bytes[path + 'context.json'])
    supplied = next(p for p in context['predicates'] if p['id'] == 1004)
    assert sha(raw) == '8b39b1da0bbcda441d28d8b7a25a258cd099aef88a87b372eb02d2c545ad2202'
    assert supplied['source_iri_local_name'] == 'P17'
    assert supplied['observed_usage'] == [dict(subject=102, object=dict(kind='entity', id=101))]
    rationale = json.loads(raw)['rationale']
    assert 'predicate 1004 (P1448)' in rationale and "'Finland' as a literal string" in rationale
    return dict(version='qwen-status-precedence-blocked-analysis-v1', decision='INCONCLUSIVE_REVISE',
        status='blocked_before_inference_command', blocker=host['blockers'],
        authorized_pr_commit=pr['headRefOid'], registered_source_commit=registration['freeze_manifest']['source_commit'],
        generation_attempts=0, completed=0, failed=0, unattempted=38, retries=0, model_loaded=False,
        model_generated_rdf_executions=0, inference_performed=False, inference_command_issued=False,
        independent_human_review='pending', issue83='open', issue75_integration='disabled',
        semantic_correctness=None, model_superiority=None, product_readiness=None,
        native_controls=[dict(**r, status='unattempted', passed=None) for r in schedule[:2]],
        native_grammar_controls_passed=12, conditions=conditions, comparisons=comparisons,
        new_rationale_source_table_contradictions=None,
        baseline_rationale_source_table_witness=dict(condition='retrieval', name='smoke-v1e-country-paraphrase-en',
            raw_path=path+'proposal.txt', raw_sha256=sha(raw), raw_excerpt=raw.decode(),
            context_path=path+'context.json', source_context_sha256=sha(prior_bytes[path+'context.json']),
            supplied=supplied, asserted_predicate='P1448', asserted_object="literal string 'Finland'",
            five_plan_fields_match=True, independent_human_judgment=None,
            automatic_narrow_English_detector_contradictions=0),
        resources=dict(host_captured_at=host['captured_at'], swap_used_mib=host['swap_used_mib'],
            host_gate_passed=False, runtime_rss_samples=None, runtime_peak_rss_kib=None,
            load_timing_ms=None, completion_timing_ms=None),
        missing_evidence='No weight load, native template parity, completions, raw/SSE responses or model-output Rust previews exist because admission failed.',
        input_identity=dict(evidence_archive_sha256=manifest['archive_sha256'],
            registration_sha256=sha(payload['registration.json']), freeze_sha256=registration['freeze_sha256'],
            unchanged_baseline_archive_sha256=old['input_identity']['archive_sha256']))


if __name__ == '__main__':
    with patch('subprocess.Popen', side_effect=AssertionError('Model-free analyzer must not start processes')):
        result = analyze()
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    lines = ['# Full scheduled comparison', '',
        'All new outcomes are null: admission failed before any completion request. '
        'BM25-v1 is stored as `retrieval`. Independent human review is pending.', '',
        'Fields are start / predicate / graph / direction / output (values projection). '
        'T/F denotes baseline exposed-reference field agreement, including abstentions. '
        'It does not establish semantic correctness.', '',
        '| Condition / observation | Reference | Direction | Baseline status | Baseline five fields | New status | New five fields |',
        '|---|---|---|---|---|---|---|']
    for row in result['comparisons']:
        fields = row['baseline']['field_agreement']
        display = '/'.join('T' if fields[k] else 'F' for k in baseline.a.PLAN_FIELDS) if fields else 'n/a'
        lines.append(f"| {row['condition']} / {row['name']} | {row['reference_status']} | {row['reference_direction'] or 'n/a'} | {row['baseline']['model_origin_status']} | {display} | null | null/null/null/null/null |")
    matrix = '\n'.join(lines) + '\n'
    if sys.argv[1:] == ['--check']:
        assert (REPORT / 'analysis.json').read_text() == rendered
        assert (REPORT / 'comparison.md').read_text() == matrix
        assert all(v is None for r in result['comparisons'] for v in r['field_agreement'].values())
        print('PASS: exact analysis reproduction; 38 unattempted; missing outcomes null; no subprocesses')
    else:
        assert not sys.argv[1:]
        (REPORT / 'analysis.json').write_text(rendered)
        (REPORT / 'comparison.md').write_text(matrix)
