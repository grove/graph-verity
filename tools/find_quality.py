#!/usr/bin/env python3
"""Issue 46 comparison and explicitly opt-in, offline development-only fusion trial."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import resource
import sys
import time

import retrieval as r


def ranks(path):
    with gzip.open(Path(path) / 'ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def outcomes(rows):
    groups = {'all': rows}
    for key in ['language', 'family', 'status']:
        for value in sorted({row[key] for row in rows}):
            groups[f'{key}/{value}'] = [row for row in rows if row[key] == value]
    return {key: dict(n=len(group), states=dict(sorted(Counter(row['result_status'] or 'error' for row in group).items())),
                     errors=sum('error' in row for row in group),
                     returned_candidates=r.interval([float(bool(row['hits'])) for row in group]))
            for key, group in groups.items()}


def compare(baseline, revised):
    for path in [baseline, revised]:
        r.verify_report(path)
    old, new = ranks(baseline), ranks(revised)
    splits = {}
    for split in ['development', 'evaluation']:
        left = {row['id']: row for row in old if row['split'] == split}
        right = [row for row in new if row['split'] == split]
        groups = {'overall': [row for row in right if row['status'] == 'relevant']}
        for key in ['language', 'family']:
            for value in sorted({row[key] for row in right}):
                groups[f'{key}/{value}'] = [row for row in right if row['status'] == 'relevant' and row[key] == value]
        splits[split] = dict(baseline=r.summarize(list(left.values())), revised=r.summarize(right),
            outcomes=outcomes(right), paired_gain={key: {
                metric: r.interval([row['metrics'][metric] - left[row['id']]['metrics'][metric] for row in group])
                for metric in ['recall@1', 'recall@5', 'recall@10', 'recall@50', 'mrr@10']}
                for key, group in groups.items()})
    summary = r.read(Path(revised) / 'summary.json')
    return dict(baseline_artifacts_sha256=r.sha(Path(baseline) / 'artifacts.json'),
                revised_artifacts_sha256=r.sha(Path(revised) / 'artifacts.json'), splits=splits,
                budgets=dict(warm_p95_under_500ms=all(p['warm_ms']['p95'] <= 500 for p in summary['performance'].values()),
                             aggregate_rss_under_4gib=summary['aggregate_peak_rss_bytes'] <= 4 * 1024**3),
                fusion_decision='defer; separate development-only trial; independent relevance review unavailable')


def fusion_dev(binary, model_dir, out):
    # Importing this module never imports Torch or downloads assets.
    import embedding_experiment as e
    spec, _ = e.verify()
    manifest, cases = r.verify()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    checked = e.assets(model_dir)
    r.require(checked['valid'], 'Pinned offline model assets missing or changed')
    torch, runtime = e.cpu_runtime()
    binary = str(Path(binary).resolve())
    payloads, requests = {}, {}
    queries = {q['id']: q['query'] for q in r.read(r.ROOT / manifest['development'])['queries']}
    for name, corpus in manifest['corpora'].items():
        selected = [case for case in cases if case['corpus'] == name]
        if not selected:
            continue
        payloads[name] = e.export_corpus(binary, corpus)
        e.save_gzip(out / f'{name}-documents.json.gz', payloads[name])
        requests[name] = [dict(query=queries[c['id']], role=c['role'], scope=r.read(r.ROOT / corpus['scope']), limit=50)
                          for c in selected]
        r.write(out / f'{name}-requests.json', requests[name])
    paths = ['tools/find_quality.py', 'tools/embedding_experiment.py', 'tools/retrieval.py',
             'benchmarks/embeddinggemma/manifest.json', 'benchmarks/retrieval/manifest.json',
             'Cargo.lock', 'rust-toolchain.toml'] + [str(p.relative_to(r.ROOT)) for p in sorted((r.ROOT / 'crates').rglob('*.rs'))]
    freeze = dict(frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), model=checked,
                  runtime=runtime, binary_sha256=e.digest(binary), code_sha256={p: r.sha(r.ROOT / p) for p in paths},
                  inputs_sha256={p: r.sha(r.ROOT / p) for p in manifest['sha256']},
                  exports_sha256={p.name: r.sha(p) for p in out.iterdir()},
                  split='development_only', policy='dense/fusion have no exact tier; >1 hits ambiguous_candidates; 1 low_confidence; 0 no_match; no score cutoff',
                  fusion=spec['fusion'], selection='fixed #38 method; no tuning; no evaluation or scale inference',
                  review='AI-authored judgments; no independent relevance reviewer; integration deferred')
    r.write(out / 'freeze.json', freeze)
    print('Frozen development-only trial: ' + r.sha(out / 'freeze.json'), flush=True)
    rows, failures = [], []
    try:
        encoder = e.parity_run(model_dir, torch, spec, out)
        for name, payload in payloads.items():
            texts = [d['input'] for d in payload['documents']]
            vectors = torch.cat([encoder.encode(texts[i:i + spec['document_batch_size']])
                                 for i in range(0, len(texts), spec['document_batch_size'])])
            e.save_gzip(out / f'{name}-vectors.json.gz', vectors.tolist())
            batch = e.invoke(binary, 'find-batch', manifest['corpora'][name], out / f'{name}-requests.json')
            selected = [case for case in cases if case['corpus'] == name]
            r.require(len(batch['results']) == len(selected), 'Lost development cases')
            for case, request, response in zip(selected, requests[name], batch['results']):
                r.require('result' in response, 'Lexical development query failed')
                lexical = response['result']['hits']
                semantic = e.query(encoder, payload, vectors, request['query'], case['role'])
                for system, hits in [('bm25', lexical), ('embedding', semantic), ('fusion', e.fuse(lexical, semantic))]:
                    state = response['result']['status'] if system == 'bm25' else (
                        'ambiguous_candidates' if len(hits) > 1 else 'low_confidence' if hits else 'no_match')
                    row = dict(case, split='development', system=system, query=request['query'],
                               snapshot_id=payload['manifest']['snapshot_id'], result_status=state,
                               hits=[{k: h[k] for k in ['graph', 'iri', 'score']} for h in hits])
                    row['metrics'] = r.score(case, row)
                    rows.append(row)
        with gzip.open(out / 'ranks.jsonl.gz', 'wt', encoding='utf-8') as stream:
            stream.writelines(json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
        r.write(out / 'summary.json', fusion_summary(rows))
    except Exception as exc:
        failures.append(dict(error=str(exc)))
        raise
    finally:
        r.write(out / 'failures.json', failures)
        unit = 1 if sys.platform == 'darwin' else 1024
        r.write(out / 'memory.json', dict(aggregate_upper_bound_bytes=unit * (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss + resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)))
        r.write(out / 'artifacts.json', {p.name: e.digest(p) for p in sorted(out.iterdir()) if p.is_file()})


def fusion_summary(rows):
    import embedding_experiment as e
    return dict(systems={system: r.summarize([row for row in rows if row['system'] == system])
                for system in ['bm25', 'embedding', 'fusion']},
                outcomes={system: outcomes([row for row in rows if row['system'] == system])
                          for system in ['bm25', 'embedding', 'fusion']},
                paired_gain={system: e.paired(rows, system) for system in ['embedding', 'fusion']},
                decision='defer fusion; no independent relevance review; development-only, no rollout or performance claim')


def verify_fusion_dev(out):
    import embedding_experiment as e
    out = Path(out)
    for name, expected in r.read(out / 'artifacts.json').items():
        r.require(r.sha(out / name) == expected, 'Fusion development artifact changed: ' + name)
    freeze = r.read(out / 'freeze.json')
    spec, _ = e.verify()
    manifest, cases = r.verify()
    r.require(freeze['split'] == 'development_only' and freeze['fusion'] == spec['fusion'], 'Trial protocol changed')
    r.require(freeze['model']['valid'] and freeze['model']['model'] == spec['model']
              and freeze['model']['revision'] == spec['revision'], 'Trial model changed')
    for name, expected in freeze['exports_sha256'].items():
        r.require(r.sha(out / name) == expected, 'Frozen trial export changed')
    e.compare_parity(r.read(out / 'parity-reference.json'), r.read(out / 'parity-runtime.json'))
    rows = ranks(out)
    formulations = {q['id']: q['query'] for q in r.read(r.ROOT / manifest['development'])['queries']}
    judgments = {case['id']: case for case in cases}
    for system in ['bm25', 'embedding', 'fusion']:
        selected = [row for row in rows if row['system'] == system]
        r.require(len(selected) == 80 and {row['id'] for row in selected} == set(judgments), 'Trial denominators changed')
        for row in selected:
            case = judgments[row['id']]
            r.require(all(row[k] == case[k] for k in case) and row['split'] == 'development'
                      and row['query'] == formulations[row['id']], 'Trial judgment/formulation changed')
            corpus = manifest['corpora'][case['corpus']]
            payload = e.load_gzip(out / (case['corpus'] + '-documents.json.gz'))
            eligible = {(d['graph'], d['iri']) for d in payload['documents']
                        if case['role'] is None or case['role'] in d['document']['roles']}
            r.require(all((h['graph'], h['iri']) in eligible for h in row['hits']), 'Trial role/scope escaped')
            r.require(row['snapshot_id'] == r.read(r.ROOT / corpus['config'])['snapshot_id'], 'Trial snapshot changed')
            r.require(row['metrics'] == r.score(case, row), 'Trial metrics changed')
    r.require(len(rows) == 240 and not r.read(out / 'failures.json'), 'Unexpected trial rows/failures')
    r.require(r.read(out / 'summary.json') == fusion_summary(rows), 'Trial summary changed')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['compare', 'fusion-dev', 'verify-fusion-dev'])
    parser.add_argument('--baseline', default='reports/issue-37-bm25/run')
    parser.add_argument('--out', required=True)
    parser.add_argument('--binary', default='target/release/verity')
    parser.add_argument('--model-dir')
    args = parser.parse_args()
    if args.command == 'compare':
        r.write(Path(args.out) / 'comparison.json', compare(args.baseline, Path(args.out) / 'run'))
    elif args.command == 'verify-fusion-dev':
        verify_fusion_dev(args.out)
    else:
        r.require(args.model_dir, 'fusion-dev requires explicit --model-dir; no automatic download')
        fusion_dev(args.binary, args.model_dir, args.out)


if __name__ == '__main__':
    main()
