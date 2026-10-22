#!/usr/bin/env python3
"""Reproduce the ten public #105 compiler incompatibilities, preview only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def assess():
    history = ROOT / 'experiments/predicate-diagnostics-v1/model-free-replay.json'
    archive = ROOT / 'experiments/native-one-hop-v1g/execution-v1/explicit-predicate-development.tar.gz'
    catalog_path = ROOT / 'studies/nl-ask-v1/evaluation/catalog.json'
    catalog = json.loads(catalog_path.read_bytes())
    with tarfile.open(archive) as stream:
        questions = {r['id']: r for r in json.load(stream.extractfile('questions.json'))}
    observations = json.loads(history.read_bytes())['observations']
    rejected = [r for r in observations if r['rust_preview']['returncode'] != 0]
    assert [r['id'] for r in rejected] == ['explicit-' + n for n in
        ['003', '006', '013', '020', '028', '035', '038', '042', '049', '056']]
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        request_path = Path(directory) / 'request.json'
        for row in rejected:
            draft = row['expected']
            graph = next(g['iri'] for g in catalog['graphs'] if g['id'] == draft['graph'])
            entity = next(e['iri'] for e in catalog['entities'] if e['id'] == draft['start'] and e['graph'] == draft['graph'])
            predicate = next(p['iri'] for p in catalog['predicates'] if p['id'] == draft['predicate'] and p['graph'] == draft['graph'])
            request = dict(version=1, snapshot_id=catalog['snapshot_id'], scope=[graph], limit=100,
                template=dict(kind='follow_path', start=entity, steps=[dict(graph=graph,
                    predicate=predicate, direction='reverse')], filter=None, output='values'))
            plan = dict(version=1, snapshot_id=catalog['snapshot_id'], scope=[graph], limit=100,
                patterns=[dict(graph=graph, predicate=predicate, direction='reverse',
                    **{'from': dict(kind='iri', iri=entity), 'to': dict(kind='variable', name='step1')})],
                filters=[], projection=[dict(kind='variable', name='step1')], group_by=[], having=[])
            request_path.write_text(json.dumps(request))
            args = ['target/debug/verity', 'ask-preview', 'studies/nl-ask-v1/evaluation/snapshot.nq',
                    'nquads', 'studies/nl-ask-v1/evaluation/policy.json', str(request_path)]
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=45)
            assert result.returncode != 0
            assert json.loads(result.stderr)['detail'] in (
                'datatype: IRI object is incompatible with the scoped predicate range',
                'class: Type object is not an observed class'), (row['id'], result.stderr)
            assert row['kind'] == 'empty_path' and draft['direction'] == 'reverse'
            rows.append(dict(id=row['id'], question=questions[row['id']]['question'], numeric_draft=draft,
                constructed_request=request, constructed_plan=plan,
                original_nl_rejection=row['rust_preview'], current_core_rejection=dict(
                    command=[*args[:-1], '<temporary request.json containing constructed_request>'],
                    returncode=result.returncode, stdout=result.stdout, stderr=result.stderr),
                typed_contract_requires_rejection=True, future_correction='revise_mechanical_probe_generator',
                compiler_change_justified=False, historical_reference_edit_permitted=False))
    return dict(version='supervised-ask-v2-compiler-assessment', mode='preview_only_no_RDF_execution',
        inputs_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (history, archive, catalog_path, ROOT / 'crates/verity_core/src/compiler.rs',
                                 ROOT / 'crates/verity_core/src/ask.rs')}, cases=rows)


if __name__ == '__main__':
    # stdout allows the operator to choose a new receipt path without modifying historical records.
    json.dump(assess(), sys.stdout, ensure_ascii=False, indent=2)
    print()
