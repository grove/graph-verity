"""Model-free retained-draft scoring. Rust preview only; never execute a draft."""
import argparse
from collections import Counter
import copy
import gzip
import json
import math
import statistics
from pathlib import Path
import subprocess

import ask_alpha_benchmark as b
from local_nl_ask import table
from native_one_hop_semantics import PLAN_FIELDS, strict_draft

ROOT, BENCH = b.ROOT, b.DEST


def verify():
    for name, digest in b.read(BENCH / 'manifest.json')['input_sha256'].items():
        if b.sha(ROOT / name) != digest:
            raise ValueError('Changed benchmark input: ' + name)


def packets():
    return json.loads(gzip.decompress((BENCH / 'packets.json.gz').read_bytes()))


def prepare_packets():
    """Question-only #82 discovery; references are never read by this renderer."""
    source_definitions = {r['predicate']: r for r in b.definitions()}
    result = {}
    adapter = b.bundle()
    try:
        for q in b.read(BENCH / 'questions.json')['cases']:
            packet = adapter.packet(q['question'], q['language'])
            selection = table(packet, 20)
            context = {k: selection[k] for k in ['snapshot_id', 'graphs', 'entities', 'predicates']}
            context.update(question=q['question'], language=q['language'], context_trust=packet['context_trust'])
            for role in ['entities', 'predicates']:
                for row, candidate in zip(context[role], packet[role]['candidates']):
                    row.update(texts=candidate['texts'], usage=candidate['usage'])
                    if role == 'predicates':
                        row['source_definition'] = source_definitions.get(row['iri']) if candidate['graph'] == b.W else None
            # Restore a minimal immutable Rust selection after enriching copies of its rows.
            selection = table(packet, 20)
            result[q['id']] = dict(packet=packet, selection=selection, context=context)
    finally:
        adapter.close()
    return result


def numeric(plan, selection):
    if plan is None:
        return None
    graph = next((r['id'] for r in selection['graphs'] if r['iri'] == plan['graph']), None)
    fields = dict(graph=graph, direction=plan['direction'], output=plan['output'])
    for field, role in [('start', 'entities'), ('predicate', 'predicates')]:
        fields[field] = next((r['id'] for r in selection[role] if r['iri'] == plan[field] and r['graph'] == graph), None)
    return fields


def resolved(draft, selection):
    if not draft or draft['status'] != 'candidate':
        return None
    graph = next((r['iri'] for r in selection['graphs'] if r['id'] == draft['graph']), None)
    result = dict(graph=graph, direction=draft['direction'], output=draft['output'])
    for field, role in [('start', 'entities'), ('predicate', 'predicates')]:
        result[field] = next((r['iri'] for r in selection[role]
                              if r['id'] == draft[field] and r['graph'] == draft['graph']), None)
    return result


def assemble(choice, selection):
    """Architecture B feasibility only: graph comes from authorized role bindings."""
    if set(choice) != {'start', 'predicate', 'direction'} or choice['direction'] not in {'forward', 'reverse'}:
        raise ValueError('Expected three constrained choices')
    if any(type(choice[k]) is not int for k in ['start', 'predicate']):
        raise ValueError('Numeric authorized choices required')
    entity = next((r for r in selection['entities'] if r['id'] == choice['start']), None)
    predicate = next((r for r in selection['predicates'] if r['id'] == choice['predicate']), None)
    if not entity or not predicate or entity['graph'] != predicate['graph']:
        raise ValueError('Missing or cross-graph choices')
    return dict(version='nl-ask-draft-v1', status='candidate', start=choice['start'],
                predicate=choice['predicate'], graph=entity['graph'], direction=choice['direction'],
                output='values', rationale='Synthetic deterministic assembly feasibility control')


def rust_preview(adapter, selection, raw):
    selection = copy.deepcopy(selection)
    draft = strict_draft(raw)
    # This is validation of the proposed binding, not human identity resolution or approval.
    selection['resolved_start'] = draft['start'] if draft and draft['status'] == 'candidate' else None
    paths = [adapter.directory / 'alpha-selection.json', adapter.directory / 'alpha-raw.txt']
    b.write(paths[0], selection)
    paths[1].write_text(raw)
    try:
        r = subprocess.run([str(adapter.binary), 'nl-ask-preview', *adapter.common, *map(str, paths)],
                           capture_output=True, text=True, timeout=45)
        body = json.loads(r.stdout) if r.returncode == 0 else None
        return dict(accepted=r.returncode == 0, candidate=bool(body and body['status'] == 'candidate'),
                    returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
    except subprocess.TimeoutExpired as error:
        return dict(accepted=None, candidate=False, returncode=None, failure='rust_timeout',
                    stdout=(error.stdout or b'').decode(), stderr=(error.stderr or b'').decode())


def measure(ref, observation, selection, rust):
    completed = observation['outcome'] == 'completed'
    draft = strict_draft(observation.get('raw_draft', '')) if completed else None
    plan = resolved(draft, selection)
    fields = {k: plan[k] == ref['expected_plan'][k] if plan and ref['expected_plan'] else None for k in PLAN_FIELDS}
    match = all(fields.values()) if plan and ref['expected_plan'] else None
    required = numeric(ref['expected_plan'], selection)
    missing = [k for k in ['start', 'predicate', 'graph'] if required[k] is None] if required else None
    correct_status = draft['status'] == ref['expected_status'] if draft else None
    wrong = bool(rust and rust['candidate'] and ref['semantically_determinate'] and
                 (ref['expected_status'] != 'candidate' or match is False)) if completed else None
    unsupported_meaning = bool(plan and (None in plan.values() or not ref['semantically_determinate'] or
                               (ref['expected_plan'] and plan['predicate'] != ref['expected_plan']['predicate']))) if completed else None
    # Optional retained answer comparison is legitimate only for matching determinate plans.
    answer = observation.get('answer_evidence')
    answer_match = None
    if answer is not None and match is True and ref['semantically_determinate']:
        answer_match = (sorted(answer['terms']) == ref['answer_terms'] and
                        sorted(answer['source_witnesses']) == ref['source_witnesses'] and
                        answer['snapshot_id'] == b.read(BENCH / 'source.json')['snapshot_id'] and
                        answer['complete_rows'] is True and answer['complete_evidence'] is True)
    return dict(id=ref['id'], language=ref['language'], category=ref['category'], reason=ref['reason'],
        direction=ref['expected_plan']['direction'] if ref['expected_plan'] else None,
        expected_status=ref['expected_status'], determinate=ref['semantically_determinate'],
        outcome=observation['outcome'], completed=completed, raw_draft=observation.get('raw_draft'),
        failure=observation.get('failure'), latency_ms=observation.get('latency_ms'), strict_valid=draft is not None if completed else None,
        model_status=draft['status'] if draft else None, resolved_plan=plan, field_agreement=fields,
        five_field_agreement=match, status_agreement=correct_status,
        missing_numeric_vocabulary=missing, retrieval_covered=not missing if required else None,
        wrong_but_executable=wrong, unjustified_relationship_selection=unsupported_meaning,
        unresolved_candidate=bool(plan and not ref['semantically_determinate']) if completed else None,
        rust=rust, source_evidence_agreement=answer_match,
        independent_semantic_correctness=None, rationale_meaning_audit='not_automatically_proven')


def fraction(rows, predicate, success):
    subset = [r for r in rows if predicate(r)]
    return dict(numerator=sum(success(r) is True for r in subset), denominator=len(subset))


def summary(rows):
    latencies = sorted(r['latency_ms'] for r in rows if r['completed']
                       and type(r.get('latency_ms')) in (int, float) and math.isfinite(r['latency_ms']) and r['latency_ms'] >= 0)
    latency = dict(samples=len(latencies), p50_ms=statistics.median(latencies) if latencies else None,
                   p95_ms=latencies[math.ceil(.95*len(latencies))-1] if latencies else None,
                   p99_ms=latencies[math.ceil(.99*len(latencies))-1] if latencies else None)
    supported = lambda r: r['expected_status'] == 'candidate'
    return dict(scheduled=len(rows), completed_latency=latency, outcomes=dict(Counter(r['outcome'] for r in rows)),
        five_field_scheduled=fraction(rows, supported, lambda r: r['five_field_agreement']),
        five_field_completed=fraction(rows, lambda r: supported(r) and r['completed'], lambda r: r['five_field_agreement']),
        fields={k: fraction(rows, supported, lambda r: r['field_agreement'][k]) for k in PLAN_FIELDS},
        clarification=fraction(rows, lambda r: r['expected_status'] == 'needs_clarification', lambda r: r['status_agreement']),
        unsupported=fraction(rows, lambda r: r['expected_status'] == 'unsupported', lambda r: r['status_agreement']),
        false_clarification=sum(r['model_status'] == 'needs_clarification' and supported(r) for r in rows),
        false_unsupported=sum(r['model_status'] == 'unsupported' and r['expected_status'] != 'unsupported' for r in rows),
        wrong_but_executable=fraction(rows, lambda r: bool(r['rust'] and r['rust']['candidate']), lambda r: r['wrong_but_executable']),
        wrong_but_executable_scheduled=fraction(rows, lambda r: True, lambda r: r['wrong_but_executable']),
        unresolved_candidates=sum(r['unresolved_candidate'] is True for r in rows),
        unjustified_relationship_selections=sum(r['unjustified_relationship_selection'] is True for r in rows),
        retrieval=fraction(rows, supported, lambda r: r['retrieval_covered']),
        rust=dict(Counter('not_measured' if r['rust'] is None or r['rust']['accepted'] is None else
                          'accepted' if r['rust']['accepted'] else 'rejected' for r in rows)),
        source_evidence=fraction(rows, lambda r: r['source_evidence_agreement'] is not None, lambda r: r['source_evidence_agreement']))


def score(retained, packet_rows=None):
    verify()
    packet_rows = packet_rows or packets()
    refs = b.read(BENCH / 'references.json')['cases']
    if retained['origin'] not in ['synthetic_fixture', 'retained_local_model']:
        raise ValueError('Explicit evidence origin required')
    conditions = retained['conditions']
    if not conditions or len(set(conditions)) != len(conditions):
        raise ValueError('Distinct scheduled conditions required')
    observations = {}
    for r in retained['rows']:
        key = (r['condition'], r['id'])
        if key in observations or key[0] not in conditions or key[1] not in {r['id'] for r in refs}:
            raise ValueError('Duplicate or unscheduled observation')
        if r['outcome'] not in ['completed', 'failed', 'timed_out', 'unattempted']:
            raise ValueError('Unknown outcome')
        if r['outcome'] == 'completed' and not isinstance(r.get('raw_draft'), str):
            raise ValueError('Completed requires untouched UTF-8 draft')
        observations[key] = r
    adapter = b.bundle()
    arms = {}
    try:
        for condition in conditions:
            rows = []
            for ref in refs:
                observation = observations.get((condition, ref['id']), dict(outcome='unattempted'))
                selection = packet_rows[ref['id']]['selection']
                rust = rust_preview(adapter, selection, observation['raw_draft']) if observation['outcome'] == 'completed' else None
                rows.append(measure(ref, observation, selection, rust))
            arms[condition] = dict(summary=summary(rows), rows=rows,
                strata={field: {str(value): summary([r for r in rows if r[field] == value])
                               for value in sorted({r[field] for r in rows}, key=str)}
                        for field in ['language', 'direction', 'category']})
    finally:
        adapter.close()
    paired = {}
    if len(conditions) == 2:
        left, right = (arms[c]['rows'] for c in conditions)
        ids = [a['id'] for a, z in zip(left, right) if a['completed'] and z['completed']]
        paired = dict(scheduled_pairs=len(refs), completed_pairs=len(ids), ids=ids,
                      conditions={c: summary([r for r in arms[c]['rows'] if r['id'] in ids]) for c in conditions})
    return dict(version='ask-alpha-score-v1', origin=retained['origin'], decision='INCONCLUSIVE_REVISE',
                executions=0, inference_performed=False, human_observations=0,
                semantic_claim='agent_prepared_source_reference_agreement_not_independent_correctness',
                conditions=arms, paired=paired, runtime=dict(startup_ms=retained.get('startup_ms'),
                process_tree_rss=retained.get('process_tree_rss'), latency_definition='whole_observation_including_preview_and_parity_not_isolated_generation'))


def markdown(report):
    lines = ['# Retained Ask draft evaluation', '', f"Origin: **{report['origin']}**. INCONCLUSIVE_REVISE.",
             'No model invoked; no draft executed. Human comprehension unmeasured.', '']
    for condition, arm in report['conditions'].items():
        lines += [f'## {condition}', '', '```json', json.dumps(arm['summary'], indent=2), '```', '',
                  '| Case | Outcome | Problem |', '|---|---|---|']
        for r in arm['rows']:
            problems = []
            if not r['completed']:
                problems.append(r['outcome'])
            if r['five_field_agreement'] is False:
                problems.append('fields: ' + ', '.join(k for k, v in r['field_agreement'].items() if v is False))
            if r['status_agreement'] is False:
                problems.append('unexpected model status')
            if r['completed'] and not r['strict_valid']:
                problems.append('invalid draft')
            if r['wrong_but_executable']:
                problems.append('WRONG BUT EXECUTABLE')
            if r['unresolved_candidate']:
                problems.append('guess on unresolved intent')
            if r['missing_numeric_vocabulary']:
                problems.append('missing numeric ' + ', '.join(r['missing_numeric_vocabulary']))
            if r['rust'] and r['rust']['accepted'] is False:
                problems.append('Rust rejected')
            if r['source_evidence_agreement'] is False:
                problems.append('source evidence mismatch')
            if problems:
                lines.append(f"| {r['id']} | {r['outcome']} | {'; '.join(problems)} |")
    lines += ['', 'Full row JSON retains raw drafts, resolved fields and exact Rust rejection text.',
              'Unresolved dispositions are automation targets, not definitive semantic gold. Rationale claims require source audit.',
              'Source-evidence agreement is snapshot-only; schema validity and Rust acceptance do not prove interpretation.', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['packets', 'score'])
    p.add_argument('--retained', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    if args.command == 'packets':
        (BENCH / 'packets.json.gz').write_bytes(gzip.compress(
            json.dumps(prepare_packets(), ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    else:
        if args.out.exists():
            raise ValueError('Fresh output directory required')
        report = score(b.read(args.retained))
        b.write(args.out / 'score.json', report)
        (args.out / 'failures.md').write_text(markdown(report))


if __name__ == '__main__':
    main()
