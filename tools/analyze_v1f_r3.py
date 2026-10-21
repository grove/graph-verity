#!/usr/bin/env python3
"""Replay retained r3 evidence through the existing model-free v1f scorer."""
import argparse
import io
import json
from pathlib import Path
import tarfile
import tempfile

from rdflib import Dataset

import analyze_v1f as a

REPORT = a.ROOT / 'experiments/native-one-hop-v1f-diagnostic-r3-evidence'
REGISTRATION = a.ROOT / 'experiments/native-one-hop-v1f-diagnostic-r3/registration.json'


def analyze(report=REPORT):
    manifest = a.read(report / 'evidence-files.json')
    archive = (report / 'evidence.tar.gz').read_bytes()
    a.require(a.digest(archive) == manifest['archive_sha256'], 'Changed evidence archive')
    with tempfile.TemporaryDirectory(prefix='v1f-r3-analysis-') as temp:
        root = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            members = stream.getmembers()
            names = [m.name for m in members]
            a.require(len(set(names)) == len(names), 'Duplicate archive member')
            a.require(all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                          for m in members), 'Unsafe archive member')
            stream.extractall(root, filter='data')
        actual = {n: a.digest((root / n).read_bytes()) for n in names}
        a.require(actual == manifest['files'], 'Archive inventory mismatch')
        registration = a.read(root / 'registration.json')
        a.require(registration == a.read(REGISTRATION), 'Changed registered revision')
        frozen = registration['freeze_manifest']
        cfg = frozen['config']
        freeze = root / 'freeze'
        a.require(a.read(freeze / 'freeze.json') == frozen, 'Freeze/registration mismatch')
        a.require(a.digest((freeze / 'checksums.json').read_bytes()) == registration['freeze_sha256'], 'Changed freeze identity')
        a.require(a.inventory(freeze) == a.read(freeze / 'checksums.json'), 'Changed frozen packets')
        for name, digest in {**frozen['input_sha256'], **registration['source_sha256']}.items():
            a.require(a.digest((root / 'source' / name).read_bytes()) == digest, 'Changed registered source: ' + name)
        run = root / 'run'
        a.require(a.inventory(run) == a.read(run / 'checksums.json'), 'Changed run bytes')
        state = a.read(run / 'run.json')
        a.require(state['version'] == frozen['version'] and state['freeze_sha256'] == registration['freeze_sha256'], 'Run/freeze mismatch')
        a.require(state['model'] == 'qwen35' and state['executions'] == 0 and not state['integration_authorized']
                  and not state['holdout_accessed'], 'Unexpected model or authority')
        expected = a.schedule(cfg)
        saved = state['diagnostic']['cases']
        a.require([{k: r[k] for k in ('condition', 'name', 'case_id')} for r in saved] == expected, 'Changed schedule')
        a.require(state['diagnostic']['attempted'] == sum(r['generation_attempted'] for r in saved)
                  and state['diagnostic']['completed'] == sum(r['status'] in a.TERMINAL for r in saved)
                  and state['diagnostic']['denominator'] == len(expected), 'Diagnostic accounting mismatch')
        requests = list(run.rglob('completion-request.json'))
        a.require(state['generation_attempts'] == len(requests) <= registration['maximum_completion_requests_per_model']
                  and state['generation_completed'] <= len(requests), 'Request accounting mismatch')
        assets = a.read(run / 'assets.json')
        a.require({k: assets[k] for k in registration['runtime_identity']} == registration['runtime_identity'], 'Asset receipt mismatch')
        cases = a.read(root / 'source/studies/nl-ask-v1/cases.json')
        cases = {c['id']: c for c in cases if c['split'] == 'evaluation'}
        cases.update({c['id']: c for c in a.read(root / 'source' / cfg['fixture_file'])})
        audit = a.read(root / 'source/configs/native-one-hop-v1f-diagnostic.audit.json')['cases']
        data = Dataset()
        data.parse(root / 'source/studies/nl-ask-v1/evaluation/snapshot.nq', format='nquads')
        table = a.read(freeze / 'catalog.json')
        rows = []
        for model in cfg['variants']:
            observations = saved if model == 'qwen35' else [dict(**r, status='unattempted', generation_attempted=False) for r in expected]
            for observation in observations:
                case = cases[observation['case_id']]
                context = a.read(freeze / 'contexts' / f"{case['id']}-{observation['condition']}.json")
                row = a.analyze_row(observation, case, context, a.source_facts(case, context, data, table), audit[case['id']],
                                    run if model == 'qwen35' else None)
                row['raw_evidence_path'] = f"run/diagnostic/{row['condition']}/{row['name']}" if model == 'qwen35' else None
                rows.append(dict(model=model, **row))
        streams = []
        for request in requests:
            folder = request.parent
            events = [json.loads(line[5:].strip()) for line in (folder / 'completion.http.sse').read_bytes().splitlines() if line.startswith(b'data:')]
            raw = b''.join(e.get('content', '').encode() for e in events)
            a.require(events and events[-1].get('stop') is True and raw == (folder / 'proposal.txt').read_bytes(), 'SSE/raw mismatch')
            parity = a.read(folder / 'parity.json')
            a.require(parity['token_ids_equal'] and parity['prompt_bytes_equal'], 'Native parity mismatch')
            streams.append(str(folder.relative_to(run)))
        failed = run / 'diagnostic/retrieval/smoke-eva-08'
        tokens = len(a.read(failed / 'native-template.stdout')['tokens'])
        parity = a.read(failed / 'parity.json')
        a.require(parity['token_ids_equal'] and parity['prompt_bytes_equal'], 'Stopped-case parity mismatch')
        a.require(tokens + cfg['max_output_tokens'] >= cfg['context_tokens'] and not (failed / 'completion-request.json').exists(), 'Context blocker mismatch')
        groups = dict(overall=a.summarize(rows), model_condition={m: {c: a.summarize([r for r in rows if r['model'] == m and r['condition'] == c])
                      for c in cfg['stages']} for m in cfg['variants']})
        return dict(version='v1f-r3-retained-analysis-v1', decision='INCONCLUSIVE_REVISE', semantic_go=False,
                    inference_performed_by_analyzer=False, model_generated_rdf_executions=0, model_ranking=None,
                    input_identity=dict(registration_sha256=a.digest((root / 'registration.json').read_bytes()),
                        archive_sha256=manifest['archive_sha256'], freeze_sha256=registration['freeze_sha256'],
                        registered_source_commit=registration['source_commit'], registered_binary_sha256=frozen['binary_sha256'],
                        run_sha256=a.digest((run / 'run.json').read_bytes()), run_checksums_sha256=a.digest((run / 'checksums.json').read_bytes()),
                        scorer_sha256=a.digest(Path(a.__file__).read_bytes()), analyzer_sha256=a.digest(Path(__file__).read_bytes())),
                    native_integrity=dict(streams_verified=len(streams), sampling_controls=state['checks'],
                        completed_prompt_tokenizer_parities=len(streams), grammar_controls=a.read(run / 'grammar-controls/controls.json'),
                        stopped_case_prompt_tokenizer_parity=True, generation_attempts=state['generation_attempts'],
                        generation_completed=state['generation_completed'], startup_ms=state['startup_ms'],
                        process_tree_rss=state['process_tree_rss'], resource_gates_passed=state['resource_gates_passed'],
                        original_host_blockers=a.read(run / 'host.json')['blockers']),
                    stop=dict(status=state['status'], error=state['error'], observation='retrieval/smoke-eva-08',
                        input_tokens=tokens, output_reserve=cfg['max_output_tokens'], context_limit=cfg['context_tokens'], generation_attempted=False),
                    repeatability=state['diagnostic']['repeatability'],
                    authorization=a.read(root / 'review-authorization.json'),
                    limitations=['Original inference authorization provenance is unresolved; present approval does not retroactively establish it.',
                        'All reference agreement is against exposed AI-authored plans; independent semantic review is pending.',
                        'Missing observations have null outcomes and never enter measured denominators. Gemma was not run by this review.',
                        'Rust acceptance is distinct from model-origin clarification. Replay uses original bytes and does not execute RDF queries.',
                        'Predicate IDs, adjacency and IRI local names do not independently establish predicate meaning.',
                        'Rationale checks cover explicit English ID assertions only; other prose remains unassessed.',
                        'RSS is a sampled concurrent process-tree run peak; sampling may miss peaks or double-count shared pages.',
                        'No causal, model-ranking, exact-answer-accuracy or product-readiness claim.'], summary=groups, cases=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=REPORT)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    a.require(not args.out.exists(), 'Never overwrite an analysis')
    result = analyze(args.report)
    args.out.mkdir(parents=True)
    (args.out / 'analysis.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (args.out / 'failure-matrix.md').write_text(a.markdown(result).replace('# V1f retained diagnostic analysis', '# V1f r3 retained diagnostic analysis', 1))


if __name__ == '__main__':
    main()
