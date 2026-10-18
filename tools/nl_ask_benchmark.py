#!/usr/bin/env python3
"""Offline #72 freeze verification, gold-only reference baseline and saved-outcome scoring.

No inference, downloads, gold refresh, approval, or proposal execution. The Rust
boundary only previews saved drafts; answers must come from a separately approved run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import rdflib
from rdflib import Dataset, Graph, Literal, RDF, RDFS, SKOS, URIRef

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'studies/nl-ask-v1'
VERSION = 'nl-ask-draft-v1'


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def snapshot_id(raw):
    return 'sha256:' + sha256(b'graph-verity-snapshot-v1\0nquads\0' + raw).hexdigest()


def term(value):
    if isinstance(value, URIRef):
        return dict(kind='iri', value=str(value))
    require(isinstance(value, Literal), 'Blank nodes are outside this benchmark')
    return dict(kind='literal', value=str(value),
                datatype=str(value.datatype or (RDF.langString if value.language else rdflib.XSD.string)),
                language=value.language)


def n3(value):
    if isinstance(value, Literal):
        suffix = '@' + value.language if value.language else '^^<' + str(value.datatype) + '>' if value.datatype else ''
        return json.dumps(str(value), ensure_ascii=False) + suffix
    return value.n3()


def serialize(quads):
    return ''.join(sorted(' '.join(n3(t) for t in q) + ' .\n' for q in quads)).encode()


def parse_rdf(store, *args, **kwargs):
    # Preserve publisher lexical forms without changing other tools' parser defaults.
    previous = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        store.parse(*args, **kwargs)
    finally:
        rdflib.NORMALIZE_LITERALS = previous
    return store


def source_quads(recipe, gemet_graph):
    """The complete, pinned extraction recipe; no model or question-dependent retrieval."""
    quads = set()
    wiki = parse_rdf(Graph(), STUDY / 'sources' / (recipe['wikidata'] + '.ttl'), format='turtle')
    start = URIRef('http://www.wikidata.org/entity/' + recipe['wikidata'])
    graph = URIRef(recipe['graphs'][0])
    fields = {URIRef('http://www.wikidata.org/prop/direct/' + p)
              for p in ['P17', 'P131', 'P571', 'P856', 'P1448']}
    selected = {(s, p, o) for s, p, o in wiki if s == start and
                (p in fields or p == RDFS.label and isinstance(o, Literal) and o.language in {'en', 'nb', 'nn'})}
    quads.update((*t, graph) for t in selected)
    # CSV-to-Schema.org assertions preserve the existing attributed importer exactly.
    import worldcities_transfer as world
    rows = [r for r in world.read_rows() if r['geonameid'] in recipe['geonames']]
    require(len(rows) == len(recipe['geonames']), 'Missing GeoNames source rows')
    original = parse_rdf(Dataset(), data=world.build(rows)[0], format='nquads')
    quads.update((s, p, o, URIRef(recipe['graphs'][1])) for s, p, o, _ in original.quads())
    root = URIRef('http://www.eionet.europa.eu/gemet/concept/' + recipe['gemet'])
    fields = {SKOS.prefLabel, SKOS.definition, RDF.type, SKOS.broader, SKOS.narrower, SKOS.related}
    # All outgoing root fields and all explicit incoming semantic relations.
    triples = {(s, p, o) for s, p, o in gemet_graph if
               (s == root and p in fields and (not isinstance(o, Literal) or o.language in {'en', 'no', None}))
               or (o == root and p in {SKOS.broader, SKOS.narrower, SKOS.related})}
    quads.update((*t, URIRef(recipe['graphs'][2])) for t in triples)
    overlay = parse_rdf(Dataset(), STUDY / recipe['split'] / 'overlay.nq', format='nquads')
    quads.update(overlay.quads())
    return quads


def rows_and_witnesses(case, dataset):
    request = case['gold_request']
    step = request['template']['steps'][0]
    start = URIRef(request['template']['start'])
    predicate = URIRef(step['predicate'])
    graph = dataset.graph(URIRef(step['graph']))
    triples = list(graph.triples((start, predicate, None) if step['direction'] == 'forward'
                                 else (None, predicate, start)))
    rows = [{'step1': term(o if step['direction'] == 'forward' else s)} for s, _, o in triples]
    witnesses = [dict(subject=term(s), predicate=term(p), object=term(o),
                      source_graph=term(URIRef(step['graph']))) for s, p, o in triples]
    return canonical(rows), canonical(witnesses)


def canonical(values):
    return [json.loads(v) for v in sorted({json.dumps(v, sort_keys=True, ensure_ascii=False) for v in values})]


def verify():
    freeze = read(STUDY / 'freeze.json')
    payload = freeze['payload_commit']
    require(isinstance(payload, str) and len(payload) == 40 and all(c in '0123456789abcdef' for c in payload), 'Missing exact payload commit')
    for name, expected in freeze['sha256'].items():
        require(digest(ROOT / name) == expected, 'Frozen file changed: ' + name)
        committed = subprocess.check_output(['git', 'show', payload + ':' + name], cwd=ROOT)
        require(sha256(committed).hexdigest() == expected, 'Payload commit mismatch: ' + name)
    require(subprocess.check_output(['git', 'cat-file', '-t', freeze['source_base_commit']], cwd=ROOT,
                                    text=True).strip() == 'commit', 'Missing source-base commit')
    cases = read(STUDY / 'cases.json')
    manifest = read(STUDY / 'manifest.json')
    require(len(cases) == 60 and len({c['id'] for c in cases}) == 60, 'Expected 60 unique cases')
    from gemet import sources
    gemet_graph, _ = sources()
    lineages = {}
    for recipe in manifest['recipes']:
        split = recipe['split']
        folder = STUDY / split
        raw = (folder / 'snapshot.nq').read_bytes()
        require(serialize(source_quads(recipe, gemet_graph)) == raw, 'Source extraction mismatch: ' + split)
        dataset = parse_rdf(Dataset(), data=raw, format='nquads')
        scope, policy, config = (read(folder / f'{n}.json') for n in ['scope', 'policy', 'discovery'])
        require(scope == recipe['graphs'] == policy['graphs'] == list(config['graphs']), 'Graph/source boundary mismatch')
        require(config['snapshot_id'] == snapshot_id(raw), 'Snapshot identity mismatch')
        selected = [c for c in cases if c['split'] == split]
        require(len(selected) == 30 and Counter(c['language'] for c in selected) == {'nb': 15, 'en': 15}, 'Bilingual split mismatch')
        require(Counter(c['expected_status'] for c in selected) == {'candidate': 18, 'needs_clarification': 6, 'unsupported': 6}, 'Case balance mismatch')
        require(all(c['provenance']['independent_reviewer_status'] == 'pending' for c in selected), 'Review status changed without new freeze')
        lineages[split] = {c['intent_lineage'] for c in selected}
        for case in selected:
            require(case['source_witnesses'], 'Every case needs grounding witnesses: ' + case['id'])
            for witness in case['source_witnesses']:
                require(witness in [list(map(n3, q)) for q in dataset.quads()], 'Unobserved witness')
            if case['expected_status'] == 'candidate':
                rows, evidence = rows_and_witnesses(case, dataset)
                require(rows == case['full_bindings'] and evidence == case['full_evidence'], 'Gold source mismatch: ' + case['id'])
                require(len(rows) <= policy['max_rows'] and len(evidence) <= policy['max_evidence'], 'Clipped reference')
            else:
                require(case['gold_request'] is None and case['full_bindings'] is None, 'Abstention must not have executable gold')
    require(not lineages['development'] & lineages['evaluation'], 'Intent lineage crosses split')
    require(not set(manifest['recipes'][0]['focal_resources']) & set(manifest['recipes'][1]['focal_resources']), 'Focal resource crosses split')
    require(freeze['model_runs_before_freeze'] == 0 and freeze['independent_human_reviews'] == 0, 'Invalid preregistration claims')
    return dict(verified=True, cases=60, model_runs=0, independent_human_reviews=0,
                interpretation='AI-authored source-audited references; independent human review pending')


def rust_preview(case, raw, binary):
    folder = STUDY / case['split']
    if len(raw.encode()) > 16_384:
        return dict(status='invalid_contract'), None
    table = read(folder / 'catalog.json')
    table.update(resolved_start=case['resolved_start'], blocked=case['preflight_blocked'])
    with tempfile.TemporaryDirectory(prefix='nl-ask-') as temp:
        temp = Path(temp)
        (temp / 'catalog.json').write_text(json.dumps(table))
        (temp / 'draft.json').write_text(raw)
        args = [str(binary), 'nl-ask-preview', str(folder / 'snapshot.nq'), 'nquads',
                str(folder / 'policy.json'), str(folder / 'scope.json'), str(folder / 'discovery.json'),
                str(temp / 'catalog.json'), str(temp / 'draft.json')]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return dict(status='runtime_timeout'), None
    if result.returncode:
        code = json.loads(result.stderr)['detail'].split(':', 1)[0]
        require(code in {'invalid_json', 'invalid_contract', 'invalid_catalog_reference', 'deterministic_preflight_block'},
                'Unexpected Rust boundary failure: ' + result.stderr)
        return dict(status=code), None
    value = json.loads(result.stdout)
    return dict(status=value['status']), value


def score_case(case, record, binary):
    require(record['id'] == case['id'], 'Case ID mismatch')
    runtime = record['runtime_status']
    require(runtime in {'completed', 'timeout', 'error', 'cancelled'}, 'Unknown runtime status')
    require(record.get('decision') in {None, 'cancelled', 'approved'}, 'Unknown user decision')
    outcome = dict(id=case['id'], split=case['split'], language=case['language'], raw_record=record,
                   expected_status=case['expected_status'], raw_response=record.get('raw_response'),
                   runtime_status=runtime, decision=record.get('decision'),
                   structural_faithfulness=None, exact_answer_set=None, model_abstention_correct=False,
                   false_positive=False, rows_truncated=False, evidence_truncated=False,
                   interpretation_correctness='not_assessed_by_compiler',
                   gold_provenance=case['provenance'])
    proposal = None
    if runtime != 'completed':
        require(record.get('execution') is None, 'Runtime failure cannot carry execution')
        outcome['category'] = {'timeout': 'runtime_timeout', 'error': 'runtime_error', 'cancelled': 'user_cancelled'}[runtime]
        if runtime == 'cancelled':
            outcome['decision'] = 'cancelled'
        return outcome
    require(isinstance(record.get('raw_response'), str), 'Completed outcome needs original raw text')
    classification, proposal = rust_preview(case, record['raw_response'], binary)
    category = classification['status']
    expected = case['expected_status']
    if category in {'model_needs_clarification', 'model_unsupported'}:
        outcome['model_abstention_correct'] = category == 'model_' + expected
    if category in {'candidate', 'deterministic_preflight_block', 'invalid_catalog_reference'}:
        outcome['false_positive'] = expected != 'candidate'
    if category == 'candidate':
        faithful = expected == 'candidate' and proposal['request'] == case['gold_request']
        outcome['structural_faithfulness'] = faithful
        category = 'valid_draft' if faithful else 'valid_draft_semantically_wrong'
    outcome['category'] = category
    # Saved results only: this scorer never approves or executes a proposal.
    execution = record.get('execution')
    if execution is not None:
        require(proposal is not None and proposal['status'] == 'candidate' and record.get('decision') == 'approved', 'Execution without an approved candidate')
        require(record.get('approval_id') == proposal['preview']['approval_id'], 'Approval mismatch')
        require(execution['plan'] == proposal['preview']['plan'] and execution['snapshot_id'] == proposal['request']['snapshot_id']
                and execution['scope'] == proposal['request']['scope'] and execution['status'] == 'executed', 'Saved execution identity mismatch')
        require(type(execution['complete_within_scope']) is bool and type(execution['evidence_complete_for_returned_rows']) is bool, 'Execution completeness flags must be booleans')
        outcome['rows_truncated'] = not execution['complete_within_scope']
        outcome['evidence_truncated'] = not execution['evidence_complete_for_returned_rows']
        if expected == 'candidate':
            outcome['exact_answer_set'] = (not outcome['rows_truncated'] and
                                           canonical(execution['bindings']) == case['full_bindings'])
    return outcome


def summarize(outcomes):
    supported = [o for o in outcomes if o['expected_status'] == 'candidate']
    abstentions = [o for o in outcomes if o['expected_status'] != 'candidate']
    return dict(total=len(outcomes), categories=dict(Counter(o['category'] for o in outcomes)),
                structural_faithfulness=dict(numerator=sum(o['structural_faithfulness'] is True for o in supported), denominator=len(supported)),
                strict_answer_agreement=dict(numerator=sum(o['exact_answer_set'] is True for o in supported), denominator=len(supported),
                                             unmeasured=sum(o['exact_answer_set'] is None for o in supported)),
                model_abstention=dict(numerator=sum(o['model_abstention_correct'] for o in abstentions), denominator=len(abstentions)),
                model_statuses={status: dict(numerator=sum(o['model_abstention_correct'] for o in outcomes if o['expected_status'] == status),
                                             denominator=sum(o['expected_status'] == status for o in outcomes))
                                for status in ['needs_clarification', 'unsupported']},
                false_positives=sum(o['false_positive'] for o in outcomes),
                cancellations=sum(o['decision'] == 'cancelled' for o in outcomes),
                timeouts=sum(o['category'] == 'runtime_timeout' for o in outcomes),
                rows_truncated=sum(o['rows_truncated'] for o in outcomes),
                evidence_truncated=sum(o['evidence_truncated'] for o in outcomes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify', 'baseline', 'score'])
    parser.add_argument('--records', type=Path)
    parser.add_argument('--split', choices=['development', 'evaluation'], default='development')
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/debug/verity')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    verification = verify()
    cases = [c for c in read(STUDY / 'cases.json') if c['split'] == args.split]
    if args.command == 'verify':
        report = verification
    elif args.command == 'baseline':
        # Explicit reference-only traversal; not a saved/model proposal replay.
        dataset = parse_rdf(Dataset(), STUDY / args.split / 'snapshot.nq', format='nquads')
        checks = []
        for case in cases:
            if case['expected_status'] == 'candidate':
                rows, witnesses = rows_and_witnesses(case, dataset)
                checks.append(dict(id=case['id'], status='gold_reference_only', full_bindings=rows, full_evidence=witnesses))
            else:
                checks.append(dict(id=case['id'], status='fixture_status_only_not_model_abstention'))
        report = dict(mode='gold_reference_no_model', model_accuracy=None, cases=checks)
    else:
        require(args.records is not None, 'score needs --records JSONL')
        records = [json.loads(line) for line in args.records.read_text().splitlines()]
        require(len(records) == len(cases) and len({r['id'] for r in records}) == len(records)
                and {r['id'] for r in records} == {c['id'] for c in cases}, 'Exactly one record per frozen split case required')
        records = {r['id']: r for r in records}
        outcomes = [score_case(c, records[c['id']], args.binary.resolve()) for c in cases]
        report = dict(mode='saved_outcomes_no_execution', freeze_sha256=digest(STUDY / 'freeze.json'),
                      records_sha256=digest(args.records), summary=summarize(outcomes), cases=outcomes)
    text = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.out:
        require(args.out.resolve() != STUDY and STUDY not in args.out.resolve().parents, 'Do not overwrite frozen study files')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Preserve earlier outcomes rather than silently overwriting evidence.
        with args.out.open('x') as stream:
            stream.write(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
