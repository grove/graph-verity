#!/usr/bin/env python3
"""Model-free analysis of retained v1f bytes; never loads models or executes RDF queries."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile

from rdflib import Dataset, Literal, URIRef

from native_one_hop_semantics import PLAN_FIELDS, strict_draft

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/issue-83-native-one-hop-v1f-diagnostic'
VERSION = 'issue83-native-cpu-v1f-diagnostic'
TERMINAL = {'reference_match', 'model_semantic_failure', 'validator_rejection'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def inventory(folder):
    require(not any(p.is_symlink() for p in folder.rglob('*')), 'Symlink in retained evidence')
    return {str(p.relative_to(folder)): digest(p.read_bytes()) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.name != 'checksums.json'}


def schedule(cfg):
    rows = []
    for condition in cfg['stages']:
        names = [('repeat-0', cfg['smoke_cases'][0]), ('repeat-1', cfg['smoke_cases'][0])] if condition == 'oracle' else []
        names += list(cfg['control_cases'].items()) + [('smoke-' + c, c) for c in cfg['smoke_cases']]
        rows += [dict(condition=condition, name=n, case_id=c) for n, c in names]
    return rows


def load_freeze(report):
    prereg = read(report / 'preregistration.json')
    require(inventory(report) == read(report / 'checksums.json'), 'Changed registration report')
    archive = report / 'evidence.tar.gz'
    require(digest(archive.read_bytes()) == prereg['evidence_archive_sha256'], 'Changed evidence archive')
    payload = {}
    with tarfile.open(archive) as stream:
        for member in stream:
            require(member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts,
                    'Unsafe or non-file archive member')
            require(member.name not in payload, 'Duplicate archive member')
            payload[member.name] = stream.extractfile(member).read()
    require({n: digest(b) for n, b in payload.items()} == read(report / 'evidence-files.json')['files'],
            'Archive inventory mismatch')
    frozen = json.loads(payload['freeze/freeze.json'])
    require(frozen == prereg['freeze_manifest'] and frozen['version'] == VERSION, 'Wrong v1f registration')
    require(digest(payload['freeze/checksums.json']) == prereg['freeze_sha256'], 'Changed freeze identity')
    require({n.removeprefix('freeze/'): digest(b) for n, b in payload.items()
             if n.startswith('freeze/') and n != 'freeze/checksums.json'} == json.loads(payload['freeze/checksums.json']),
            'Changed frozen packets')
    for name, sha in frozen['input_sha256'].items():
        require(digest(payload['source/' + name]) == sha, 'Changed registered source: ' + name)
    cases = json.loads(payload['source/studies/nl-ask-v1/cases.json'])
    cases = [c for c in cases if c['split'] == 'evaluation']
    cases += json.loads(payload['source/' + frozen['config']['fixture_file']])
    audit = json.loads(payload['source/configs/native-one-hop-v1f-diagnostic.audit.json'])
    return prereg, payload, {c['id']: c for c in cases}, audit


def load_run(folder, frozen, expected):
    require(inventory(folder) == read(folder / 'checksums.json'), 'Changed run bytes')
    state = read(folder / 'run.json')
    require(state['version'] == VERSION and state['freeze_sha256'] == frozen['freeze_sha256'], 'Run/freeze mismatch')
    require(state['executions'] == 0 and not state['integration_authorized'] and not state['holdout_accessed'],
            'Unexpected execution/integration/holdout evidence')
    rows = state['diagnostic']['cases']
    require([{k: r[k] for k in ('condition', 'name', 'case_id')} for r in rows] == expected,
            'Missing, reordered or duplicate observations')
    require(state['generation_attempts'] <= 38 and state['generation_completed'] <= state['generation_attempts'],
            'Invalid completion accounting')
    require(state['diagnostic']['attempted'] == sum(r['generation_attempted'] for r in rows), 'Attempt count drift')
    require(state['diagnostic']['completed'] == sum(r['status'] in TERMINAL for r in rows), 'Completion count drift')
    require(state['diagnostic']['denominator'] == len(expected), 'Denominator drift')
    require(state['generation_attempts'] == len(list(folder.rglob('completion-request.json'))), 'Run request count drift')
    return state


def rationale_claims(text, context):
    """Only whole explicit identity assertions; unrestricted prose remains unassessed."""
    claims = []
    # shortcut: English declarative ID assertions only, extend with source-backed rules when new retained claims require it.
    pattern = r'(?im)^(predicate|entity) (\d+) (?:is|=|corresponds to) (https?://[^\s]+|[A-Za-z]+:[\w]+|P\d+)\.?$'
    prefixes = {'schema': 'https://schema.org/', 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'skos': 'http://www.w3.org/2004/02/skos/core#'}
    for match in re.finditer(pattern, text):
        role, identifier, value = match.groups()
        value = value.rstrip('.')
        iri = prefixes.get(value.split(':')[0], '') + value.split(':')[-1] if ':' in value and not value.startswith('http') else value
        if re.fullmatch(r'P\d+', value):
            iri = 'http://www.wikidata.org/prop/direct/' + value
        row = next((r for r in context['predicates' if role.lower() == 'predicate' else 'entities']
                    if r['id'] == int(identifier)), None)
        claims.append(dict(claim=match.group(), id=int(identifier), asserted_iri=iri, source_row=row,
                           contradicted=row['iri'] != iri if row and (iri.startswith('http://') or iri.startswith('https://')) else None))
    return dict(method='whole English ID identity assertions only; other prose unassessed', claims=claims,
                contradictions=sum(c['contradicted'] is True for c in claims),
                unrestricted_rationale_correctness=None)


def source_facts(case, context, data, table):
    gold = case['gold_draft']
    if case['expected_status'] != 'candidate':
        return dict(required_vocabulary=None, reference_edge_witnesses=None, predicate_metadata=None)
    required = {field: any(r['id'] == gold[field] and r['graph'] == gold['graph'] for r in context[collection])
                for field, collection in [('start', 'entities'), ('predicate', 'predicates')]}
    required['graph'] = any(r['id'] == gold['graph'] for r in context['graphs'])
    graph = next(r['iri'] for r in table['graphs'] if r['id'] == gold['graph'])
    start = next(r['iri'] for r in table['entities'] if r['id'] == gold['start'] and r['graph'] == gold['graph'])
    predicate = next(r['iri'] for r in table['predicates'] if r['id'] == gold['predicate'] and r['graph'] == gold['graph'])
    source = data.graph(URIRef(graph))
    # Enumerate retained triples only. No model plan, SPARQL or RDF query is executed.
    witnesses = sorted([s.n3(), p.n3(), o.n3(), URIRef(graph).n3()] for s, p, o in source
                       if str(p) == predicate and str(s if gold['direction'] == 'forward' else o) == start)
    metadata = sorted([s.n3(), p.n3(), o.n3(), URIRef(graph).n3()] for s, p, o in source
                      if str(s) == predicate and isinstance(o, Literal))
    return dict(required_vocabulary=required, reference_edge_witnesses=witnesses, predicate_metadata=metadata,
                predicate_meaning='not established merely by identity, local name, adjacency or reference agreement')


def analyze_row(saved, case, context, facts, audit, folder=None):
    row = {k: saved[k] for k in ('condition', 'name', 'case_id', 'status', 'generation_attempted')}
    attempted = saved['generation_attempted']
    require(type(attempted) is bool and saved['status'] in TERMINAL | {'unattempted', 'fatal_failure'}, 'Invalid observation state')
    completed = saved['status'] in TERMINAL
    raw, draft, parsed, preview = None, None, None, saved.get('rust_preview')
    json_valid = None
    if saved.get('raw_base64') is not None:
        raw = base64.b64decode(saved['raw_base64'], validate=True)
        require(digest(raw) == saved['raw_sha256'], 'Raw byte hash mismatch')
        draft = strict_draft(raw)
        try:
            parsed = json.loads(raw)
            json_valid = True
        except (ValueError, UnicodeDecodeError):
            json_valid = False
    if folder:
        dest = folder / 'diagnostic' / row['condition'] / row['name']
        require((dest / 'completion-request.json').exists() == attempted, 'Attempt/request mismatch')
        require(not attempted or (dest / 'context.json').exists(), 'Attempt missing context')
        require((dest / 'proposal.txt').exists() == (raw is not None), 'Missing retained raw bytes')
        if (dest / 'observation.json').exists():
            require(read(dest / 'observation.json') == saved, 'Observation/run mismatch')
        if (dest / 'context.json').exists():
            require(read(dest / 'context.json') == context, 'Run context differs from frozen context')
        if raw is not None:
            require((dest / 'proposal.txt').read_bytes() == raw, 'Raw proposal/base64 mismatch')
        if preview is not None:
            require(read(dest / 'rust.json') == preview, 'Retained Rust result mismatch')
    require(not completed or attempted and raw is not None and preview is not None, 'Completed without request/bytes/Rust')
    require(saved['status'] != 'unattempted' or not attempted and raw is None and preview is None,
            'Unattempted case contains measurements')
    fields = {k: draft.get(k) == case['gold_draft'].get(k) if draft else False for k in PLAN_FIELDS} if attempted and case['expected_status'] == 'candidate' else None
    status = parsed.get('status') if isinstance(parsed, dict) else None
    rust = preview['returncode'] == 0 if preview is not None else None
    agreement = bool(draft and status == case['expected_status'] and (fields is None or all(fields.values()))) if attempted else None
    usable = bool(agreement and rust and saved.get('gbnf_valid') is True and completed) if attempted else None
    present = facts['required_vocabulary']
    source_group = ('ambiguous' if audit.get('ambiguity') in {'unresolved label collision', 'relationship underdetermined', 'absent source identity'}
                    else 'unsupported' if case['expected_status'] == 'unsupported' else 'supported')
    mechanism = ('unattempted' if not attempted else 'runtime_or_integrity_failure' if not completed else
                 'reference_match' if usable else 'reference_failure_with_required_vocabulary_missing' if present and not all(present.values()) else
                 'reference_failure_with_vocabulary_available' if present else 'abstention_or_structural_failure')
    return dict(**row, completed=completed, reference_status=case['expected_status'],
                reference_group={'candidate': 'supported', 'needs_clarification': 'ambiguous', 'unsupported': 'unsupported'}[case['expected_status']],
                AI_source_question_group=source_group,
                reference_direction=case['gold_draft'].get('direction'), question=case['question'],
                raw_sha256=digest(raw) if raw is not None else None, model_origin_status=status,
                json_valid=json_valid,
                strict_contract_valid=draft is not None if raw is not None else None,
                gbnf_valid=saved.get('gbnf_valid'), rust_accepted=rust,
                rust_rejection=preview is not None and not rust, field_agreement=fields,
                exact_exposed_reference_agreement=agreement, accepted_exposed_reference_agreement=usable,
                wrong_but_executable=bool(status == 'candidate' and rust and not agreement) if attempted else None,
                correct_model_clarification=bool(status == 'needs_clarification' and usable) if attempted and case['expected_status'] == 'needs_clarification' else None,
                AI_source_audit_clarification_agreement=bool(draft and status == 'needs_clarification' and rust and saved.get('gbnf_valid') is True and completed) if attempted and source_group == 'ambiguous' else None,
                incorrect_guess=bool(status == 'candidate') if attempted and case['expected_status'] != 'candidate' else None,
                failure_stratum=mechanism, source=facts, preregistered_AI_audit=audit,
                rationale=rationale_claims(draft['rationale'], context) if draft else None,
                latency_ms=saved.get('latency_ms'), runtime=saved.get('runtime'), resources=saved.get('resources'),
                error=saved.get('error'), raw_evidence_path=str(folder / 'diagnostic' / row['condition'] / row['name']) if folder else None)


def rate(values):
    values = [v for v in values if v is not None]
    return dict(numerator=sum(v is True for v in values) if values else None, denominator=len(values))


def distribution(values):
    values = sorted(v for v in values if v is not None)
    return dict(samples=len(values), p50=values[(len(values)-1)//2] if values else None,
                p95=values[max(0, (95*len(values)+99)//100-1)] if values else None, maximum=max(values) if values else None)


def summarize(rows):
    metrics = {key: rate([r[key] for r in rows]) for key in ['json_valid', 'strict_contract_valid', 'gbnf_valid', 'rust_accepted',
               'exact_exposed_reference_agreement', 'accepted_exposed_reference_agreement', 'wrong_but_executable',
               'correct_model_clarification', 'AI_source_audit_clarification_agreement', 'incorrect_guess']}
    metrics['field_agreement'] = {k: rate([r['field_agreement'][k] if r['field_agreement'] is not None else None for r in rows]) for k in PLAN_FIELDS}
    return dict(scheduled=len(rows), attempted=sum(r['generation_attempted'] for r in rows),
                completed=sum(r['completed'] for r in rows), unattempted=sum(not r['generation_attempted'] for r in rows),
                rust_rejected=sum(r['rust_rejection'] for r in rows), metrics=metrics,
                failure_strata=dict(sorted(Counter(r['failure_stratum'] for r in rows).items())),
                observation_latency_ms=distribution([r['latency_ms'] for r in rows if r['generation_attempted']]),
                native_generation_latency_ms=distribution([(r['runtime'] or {}).get('elapsed_ms') for r in rows]),
                tokens_predicted=[(r['runtime'] or {}).get('tokens_predicted') for r in rows if r['generation_attempted']],
                sampled_run_peak_kib=distribution([(r['resources'] or {}).get('after', {}).get('peak_kib') for r in rows]),
                rationale_contradictions=sum(r['rationale']['contradictions'] for r in rows if r['rationale']))


def analyze(report=REPORT, runs=()):
    prereg, payload, cases, audit = load_freeze(report)
    cfg = prereg['freeze_manifest']['config']
    expected = schedule(cfg)
    baseline = read(report / 'decision.json')
    data = Dataset()
    data.parse(data=payload['source/studies/nl-ask-v1/evaluation/snapshot.nq'].decode(), format='nquads')
    table = json.loads(payload['freeze/catalog.json'])
    states, folders = {}, {}
    for folder in runs:
        state = load_run(folder, prereg, expected)
        key = state['model']
        require(key in cfg['variants'] and key not in states, 'Unknown or duplicate model run; no retries')
        states[key], folders[key] = state, folder
    rows, provenance = [], {}
    for model in cfg['variants']:
        state = states.get(model)
        saved_rows = state['diagnostic']['cases'] if state else baseline['models'][model]['cases']
        require([{k: r[k] for k in ('condition', 'name', 'case_id')} for r in saved_rows] == expected, 'Changed baseline schedule')
        require(state is not None or all(r['status'] == 'unattempted' for r in saved_rows), 'Native evidence requires --run')
        provenance[model] = dict(run_sha256=digest((folders[model] / 'run.json').read_bytes()) if state else None,
                                 checksums_sha256=digest((folders[model] / 'checksums.json').read_bytes()) if state else None,
                                 status=state['status'] if state else 'authorization_absent',
                                 reason=state.get('error') if state else baseline['unattempted_reason'],
                                 generation_attempts=state['generation_attempts'] if state else 0,
                                 generation_completed=state['generation_completed'] if state else 0,
                                 process_tree_rss=state.get('process_tree_rss') if state else None)
        for saved in saved_rows:
            case = cases[saved['case_id']]
            context = json.loads(payload[f"freeze/contexts/{case['id']}-{saved['condition']}.json"])
            row = analyze_row(saved, case, context, source_facts(case, context, data, table), audit['cases'][case['id']], folders.get(model))
            rows.append(dict(model=model, **row))
    groups = {'overall': summarize(rows)}
    for field in ['model', 'condition', 'reference_direction', 'reference_group', 'AI_source_question_group']:
        groups[field] = {str(value): summarize([r for r in rows if r[field] == value]) for value in sorted({r[field] for r in rows}, key=str)}
    groups['model_condition'] = {m: {c: summarize([r for r in rows if r['model'] == m and r['condition'] == c]) for c in cfg['stages']} for m in cfg['variants']}
    pairs = {}
    for comparison, field, left, right in [('oracle_vs_BM25_v1', 'condition', 'oracle', 'retrieval'), ('Qwen_vs_Gemma', 'model', 'qwen35', 'gemma4')]:
        other = 'model' if field == 'condition' else 'condition'
        index = {(r[other], r['name'], r[field]): r for r in rows}
        paired = [(r, index.get((r[other], r['name'], right))) for r in rows if r[field] == left]
        paired = [(l, r) for l, r in paired if r and l['generation_attempted'] and r['generation_attempted']]
        pairs[comparison] = dict(attempted_pairs=len(paired), left_only_reference_match=sum(bool(l['accepted_exposed_reference_agreement']) and not r['accepted_exposed_reference_agreement'] for l, r in paired) if paired else None,
                                 right_only_reference_match=sum(bool(r['accepted_exposed_reference_agreement']) and not l['accepted_exposed_reference_agreement'] for l, r in paired) if paired else None)
    return dict(version='v1f-retained-analysis-v1', decision='INCONCLUSIVE_REVISE', semantic_go=False,
                reference_origin='exposed AI-authored references; not independent validation', independent_human_review='pending; not a completion gate for this diagnostic',
                model_generated_rdf_executions=0, inference_performed_by_analyzer=False, model_ranking=None,
                input_identity=dict(preregistration_sha256=digest((report / 'preregistration.json').read_bytes()),
                                    archive_sha256=prereg['evidence_archive_sha256'], freeze_sha256=prereg['freeze_sha256'],
                                    registered_binary_sha256=prereg['freeze_manifest']['binary_sha256'],
                                    analyzer_sha256=digest(Path(__file__).read_bytes()), runs=provenance),
                limitations=['Vocabulary membership, explicit triple witnesses and predicate metadata are separate from semantic sufficiency.',
                             'Failure strata describe co-occurrence, not causal attribution. No model numerator for unattempted cases.',
                             'Rust receipts are read and hash-checked here; use the frozen replay command for independent byte replay.',
                             'Rationale rules cover explicit English ID identity assertions only. Other prose is unassessed, never validated.',
                             'RSS snapshots are sampled run peaks to date, not case peaks; OS cache is uncontrolled.',
                             'Repeated observations are correlated. No significance, generalization, human truth or readiness claim.'],
                summary=groups, paired_comparisons=pairs, cases=rows)


def markdown(result):
    s = result['summary']['overall']
    lines = ['# V1f retained diagnostic analysis', '', '**INCONCLUSIVE_REVISE. Human review pending; no semantic GO.**', '',
             f"{s['attempted']}/{s['scheduled']} observations attempted; {s['completed']} completed; {s['unattempted']} unattempted.",
             'Exposed AI-authored reference agreement is separate from Rust acceptance and source evidence sufficiency.', '',
             '| Model / condition | Attempts / scheduled | Complete | Rust accepted | Reference agreement |',
             '|---|---:|---:|---:|---:|']
    def fraction(metric):
        return 'unmeasured' if metric['numerator'] is None else f"{metric['numerator']}/{metric['denominator']}"
    for m, conditions in result['summary']['model_condition'].items():
        for c, summary in conditions.items():
            metrics = summary['metrics']
            lines.append(f"| {m} / {c} | {summary['attempted']}/{summary['scheduled']} | {summary['completed']} | {fraction(metrics['rust_accepted'])} | {fraction(metrics['accepted_exposed_reference_agreement'])} |")
    lines += ['', '## Failure matrix', '', 'Vocabulary is relative to exposed references. Missing IDs limit interpretation; available IDs do not define predicate meaning.', '',
              '| Condition / observation | Reference | Start / predicate in packet | Qwen | Gemma |', '|---|---|---|---|---|']
    for row in result['cases']:
        if row['model'] != 'qwen35':
            continue
        other = next(r for r in result['cases'] if r['model'] == 'gemma4' and r['condition'] == row['condition'] and r['name'] == row['name'])
        vocab = row['source']['required_vocabulary']
        coverage = f"{vocab['start']} / {vocab['predicate']}" if vocab else 'n/a'
        lines.append(f"| {row['condition']} / {row['name']} | {row['reference_status']} {row['reference_direction'] or ''} | {coverage} | {row['failure_stratum']} | {other['failure_stratum']} |")
    lines += ['', '## Measurement limits', ''] + ['- ' + line for line in result['limitations']]
    lines += ['', 'Machine report contains field agreement, source witnesses/metadata, statuses, rationale checks, latency, tokens and resource samples per observation and by model/condition/direction/question class.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=REPORT)
    parser.add_argument('--run', action='append', type=Path, default=[])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'Never overwrite an analysis')
    result = analyze(args.report, args.run)
    args.out.mkdir(parents=True)
    (args.out / 'analysis.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (args.out / 'README.md').write_text(markdown(result))


if __name__ == '__main__':
    main()
