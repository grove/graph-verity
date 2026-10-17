#!/usr/bin/env python3
"""Frozen public retrieval scoring and single-process CPU measurements; no models or Ask data."""
import argparse
from collections import Counter
import hashlib
import gzip
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'benchmarks/retrieval/manifest.json'
FAMILIES = {'identifier', 'entity', 'alias', 'predicate', 'description', 'multi_relevant', 'ambiguous', 'no_match'}
KS = (1, 5, 10, 50)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify():
    manifest = read(MANIFEST)
    for path, expected in manifest['sha256'].items():
        require(sha(ROOT / path) == expected, f'Frozen retrieval input changed: {path}')
    cases = read(ROOT / manifest['judgments'])['cases']
    ids = [c['id'] for c in cases]
    require(len(set(ids)) == len(ids) == 80, 'Expected 80 distinct judgments')
    require(Counter(c['language'] for c in cases) == {'no': 40, 'en': 40}, 'Language imbalance')
    require(Counter(c['family'] for c in cases) == dict.fromkeys(FAMILIES, 10), 'Family imbalance')
    for c in cases:
        require(c['status'] in {'relevant', 'ambiguous', 'no_match'}, 'Unknown judgment status')
        require(bool(c['relevant']) == (c['status'] != 'no_match'), 'Invalid relevance denominator')
        require(len({(r['graph'], r['iri']) for r in c['relevant']}) == len(c['relevant']), 'Duplicate judgment')
        require(bool(c['lineage']), 'Missing judgment lineage')
    formulations = []
    for key in ['development', 'evaluation']:
        queries = read(ROOT / manifest[key])['queries']
        require(len(queries) == 80 and {q['id'] for q in queries} == set(ids), 'Formulation IDs differ')
        require(all(0 < len(q['query'].encode()) <= 4096 for q in queries), 'Unbounded query')
        formulations.append({q['id']: q['query'] for q in queries})
    require(all(formulations[0][id] != formulations[1][id] for id in ids), 'Reused formulation')
    require(manifest['parameters'] == {'k1': 1.2, 'b': 0.75, 'limit': 50}, 'Unreviewed parameter change')
    return manifest, cases


def percentile(values, p):
    values = sorted(values)
    return values[max(0, math.ceil(p * len(values)) - 1)] if values else None


def interval(values):
    """Descriptive query-level percentile bootstrap; not an independent-population CI."""
    if not values:
        return {'n': 0, 'mean': None, 'descriptive_95': [None, None]}
    rng = random.Random(37)
    means = [sum(rng.choices(values, k=len(values))) / len(values) for _ in range(2000)]
    return {'n': len(values), 'mean': sum(values) / len(values),
            'descriptive_95': [percentile(means, .025), percentile(means, .975)]}


def score(case, result):
    relevant = {(r['graph'], r['iri']) for r in case['relevant']}
    ranked = [(h['graph'], h['iri']) for h in result.get('hits', [])]
    require(len(ranked) == len(set(ranked)), 'Duplicate graph-qualified result')
    metrics = {f'recall@{k}': len(set(ranked[:k]) & relevant) / len(relevant) for k in KS} if relevant else {}
    metrics['mrr@10'] = next((1 / (i + 1) for i, r in enumerate(ranked[:10]) if r in relevant), 0.0) if relevant else None
    return metrics


def summarize(rows):
    scored = [r for r in rows if r['status'] == 'relevant']
    groups = {'overall': scored}
    for lang in ['no', 'en']:
        groups['language/' + lang] = [r for r in scored if r['language'] == lang]
    for family in sorted(FAMILIES - {'ambiguous', 'no_match'}):
        groups['family/' + family] = [r for r in scored if r['family'] == family]
        for lang in ['no', 'en']:
            groups[f'language-family/{lang}/{family}'] = [r for r in scored if r['language'] == lang and r['family'] == family]
    summary = {key: {metric: interval([r['metrics'][metric] for r in group])
                     for metric in ['recall@1', 'recall@5', 'recall@10', 'recall@50', 'mrr@10']}
               for key, group in groups.items()}
    behavior = {}
    for status in ['ambiguous', 'no_match']:
        for language in ['all', 'no', 'en']:
            group = [r for r in rows if r['status'] == status and (language == 'all' or r['language'] == language)]
            behavior[f'{status}/{language}'] = dict(n=len(group), errors=sum('error' in r for r in group),
                returned_candidates=sum(bool(r['hits']) for r in group),
                exact_ambiguity_flags=sum(r['result_status'] == 'ambiguous_exact' for r in group),
                all_relevant_at_50=sum(r['metrics'].get('recall@50') == 1 for r in group),
                mean_candidates=sum(len(r['hits']) for r in group) / len(group) if group else None,
                candidate_return_rate=interval([float(bool(r['hits'])) for r in group]),
                exact_ambiguity_rate=interval([float(r['result_status'] == 'ambiguous_exact') for r in group]),
                all_relevant_at_50_rate=interval([float(r['metrics'].get('recall@50') == 1) for r in group]) if status == 'ambiguous' else None)
    targets = {'overall': (.90, .75), 'language/no': (.80, .65), 'language/en': (.80, .65)}
    return dict(metrics=summary, behavior=behavior, errors=sum('error' in r for r in rows),
                pilot_targets={k: summary[k]['recall@10']['mean'] >= recall and summary[k]['mrr@10']['mean'] >= mrr
                               for k, (recall, mrr) in targets.items()},
                interpretation='AI-judged exploratory agreement, not stakeholder quality or Phase 0 approval')


def scale_corpus(out):
    """Frozen synthetic load, exactly 10,000 resources including its two predicates."""
    graph = 'urn:retrieval:scale'
    rdf = out / 'scale.nq'
    with rdf.open('w') as f:
        for i in range(9998):
            for p, text in [('http://www.w3.org/2000/01/rdf-schema#label', f'Coastal station Kyststasjon {i:05d}'),
                            ('https://schema.org/description', f'Water quality vannkvalitet')]:
                f.write(f'<urn:load:{i:05d}> <{p}> "{text}" <{graph}> .\n')
    snapshot = 'sha256:' + hashlib.sha256(b'graph-verity-snapshot-v1\0nquads\0' + rdf.read_bytes()).hexdigest()
    write(out / 'scale-policy.json', dict(version=1, graphs=[graph], max_rows=1000, max_evidence=100, timeout_ms=10000))
    write(out / 'scale-scope.json', [graph])
    write(out / 'scale-config.json', dict(version=1, snapshot_id=snapshot, graphs={graph: dict(source='Synthetic load, not relevance evidence', license='Apache-2.0', source_revision='sha256:' + sha(rdf), importer_revision='retrieval-scale-v1')}))
    return dict(rdf=str(rdf), format='nquads', policy=str(out / 'scale-policy.json'), scope=str(out / 'scale-scope.json'), config=str(out / 'scale-config.json'))


def run(args):
    manifest, cases = verify()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    binary = Path(args.binary).resolve()
    cpu = args.cpu
    if cpu is not None:
        require(hasattr(os, 'sched_setaffinity'), '--cpu requires Linux affinity support')
        os.sched_setaffinity(0, {cpu})
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', RAYON_NUM_THREADS='1')
    metadata = dict(platform=platform.platform(), machine=platform.machine(), python=sys.version,
                    cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
                    thread_budget=1, cpu_description=args.cpu_description,
                    binary_sha256=sha(binary), manifest_sha256=sha(MANIFEST),
                    code_sha256={str(p.relative_to(ROOT)): sha(p) for p in [ROOT / 'tools/retrieval.py', ROOT / 'crates/verity_core/src/find.rs', ROOT / 'crates/verity_core/src/discovery.rs', ROOT / 'crates/verity_core/src/compiler.rs', ROOT / 'crates/verity_core/src/navigation.rs', ROOT / 'crates/verity_cli/src/main.rs', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml']},
                    compiler=args.compiler, cold_repetitions=args.cold, warm_queries=args.warm,
                    cold_definition='fresh process + RDF import + index build + one query + JSON IO; OS page cache not evicted',
                    warm_definition='in-process find only, includes result construction; excludes JSON serialization/IO',
                    intervals='2000 query-level percentile bootstrap resamples, seed 37; descriptive only; correlated public formulations',
                    limitations=['AI judgments require human review before stakeholder claims', 'Public evaluation shares target intents with development; not independent holdout', 'Synthetic 10000-resource load does not establish real-domain scale', 'RSS sums process high-water marks, conservative aggregate upper bound; no child workers', 'No-match means no lexical candidates, not semantic absence; conservative outcome states do not calibrate confidence'])
    cpuinfo = Path('/proc/cpuinfo')
    if cpuinfo.exists():
        metadata['proc_cpuinfo'] = cpuinfo.read_text().split('\n\n')[0]
    write(out / 'environment.json', metadata)
    raw = gzip.open(out / 'ranks.jsonl.gz', 'wt', encoding='utf-8')
    failures = []

    def invoke(command, corpus, request_path=None):
        argv = [str(binary), command] + [str(ROOT / corpus[k]) if k != 'format' else corpus[k] for k in ['rdf', 'format', 'policy', 'scope', 'config']]
        if request_path:
            argv.append(str(request_path))
        start = time.perf_counter()
        proc = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
        elapsed = (time.perf_counter() - start) * 1000
        if proc.returncode:
            failure = dict(argv=argv, returncode=proc.returncode, stderr=proc.stderr, stdout=proc.stdout, elapsed_ms=elapsed)
            failures.append(failure)
            write(out / 'failures.json', failures)
            return {'error': proc.stderr}, elapsed
        return json.loads(proc.stdout), elapsed

    def compact(case, response, query, split):
        result = response.get('result', {})
        row = dict(id=case['id'], split=split, language=case['language'], family=case['family'], status=case['status'],
                   query=query, relevant=case['relevant'], result_status=result.get('status'),
                   elapsed_ms=response.get('elapsed_ms'), snapshot_id=result.get('snapshot_id'),
                   documents=result.get('documents'), matches=result.get('matches'), exact_ids=result.get('exact_ids'),
                   exact_candidates=result.get('exact_candidates'), outcome_policy=result.get('outcome_policy'),
                   hits=[{k: h[k] for k in ['iri', 'graph', 'score', 'exact']} for h in result.get('hits', [])])
        if 'error' in response:
            row['error'] = response['error']
        row['metrics'] = score(case, result)
        raw.write(json.dumps(row, ensure_ascii=False) + '\n'); raw.flush()
        return row

    corpora = dict(manifest['corpora'])
    corpora['scale'] = scale_corpus(out)
    # Pin generated load bytes and inputs before executing the binary on them.
    require(sha(corpora['scale']['rdf']) == manifest['scale']['rdf_sha256'], 'Frozen synthetic corpus changed')
    scale_paths = [corpora['scale'][k] for k in ['rdf', 'policy', 'scope', 'config']]
    write(out / 'scale-manifest.json', dict(resources=10000, quads=19996, synthetic=True, sha256={p: sha(p) for p in scale_paths}))
    summaries, performance = {}, {}
    built = {}
    for name, corpus in corpora.items():
        index, _ = invoke('index-build', corpus)
        require('error' not in index, f'{name}: index build failed; see failures.json')
        built[name] = index
        for c in cases:
            if c['corpus'] == name:
                require(all(r['iri'] in index['graphs'][r['graph']]['documents'] for r in c['relevant']), 'Judged resource missing')
        write(out / f'{name}-index-manifest.json', index['manifest'])
    for split in ['development', 'evaluation']:
        queries = {q['id']: q['query'] for q in read(ROOT / manifest[split])['queries']}
        rows = []
        for name, corpus in manifest['corpora'].items():
            selected = [c for c in cases if c['corpus'] == name]
            if not selected:
                continue
            scope = read(ROOT / corpus['scope'])
            requests = [dict(query=queries[c['id']], scope=scope, role=c['role'], limit=50) for c in selected]
            path = out / f'{split}-{name}-requests.json'; write(path, requests)
            batch, _ = invoke('find-batch', corpus, path)
            responses = batch.get('results', [{'error': batch.get('error', 'missing batch output')}] * len(selected))
            require(len(responses) == len(selected), 'Batch lost queries')
            rows.extend(compact(c, response, queries[c['id']], split) for c, response in zip(selected, responses))
        summaries[split] = summarize(rows)
    for name, corpus in corpora.items():
        scope = read(ROOT / corpus['scope'])
        queries = ([q['query'] for q in read(ROOT / manifest['evaluation'])['queries']
                    if next(c for c in cases if c['id'] == q['id'])['corpus'] == name]
                   if name not in {'cities', 'scale'} else
                   ['Oslo', 'Bergen', 'Trondheim', 'nonexistentcanary'] if name == 'cities' else
                   ['Coastal station 00123', 'vannkvalitet', 'Water quality', '99997', 'urn:load:00042'])
        requests = [dict(query=queries[i % len(queries)], scope=scope, role=None, limit=50) for i in range(args.warm)]
        warm_path = out / f'{name}-warm-requests.json'; write(warm_path, requests)
        warm, _ = invoke('find-batch', corpus, warm_path)
        require('results' in warm, f'{name}: warm batch failed')
        timings = [r['elapsed_ms'] for r in warm['results']]
        cold_times, cold_builds, cold_threads = [], [], []
        for i in range(args.cold):
            path = out / f'{name}-cold-request.json'; write(path, [requests[i % len(requests)]])
            cold, elapsed = invoke('find-batch', corpus, path)
            cold_times.append(elapsed); cold_builds.append(cold.get('build_ms')); cold_threads.append(cold.get('process_threads'))
            raw.write(json.dumps(dict(split='performance_cold', corpus=name, iteration=i, elapsed_ms=elapsed, response=cold)) + '\n')
        for i, response in enumerate(warm['results']):
            raw.write(json.dumps(dict(split='performance_warm', corpus=name, iteration=i, query=requests[i]['query'], response=response)) + '\n')
        index = built[name]
        docs = sum(len(g['documents']) for g in index['graphs'].values())
        if name == 'scale':
            require(docs == 10000, 'Synthetic resource cap changed')
        performance[name] = dict(documents=docs, unique_iris=len({iri for g in index['graphs'].values() for iri in g['documents']}),
            rdf_bytes=Path(ROOT / corpus['rdf']).stat().st_size, index_bytes=warm['index_bytes'], build_ms=warm['build_ms'],
            cold_build_ms=cold_builds, cold_process_threads=cold_threads, warm_process_threads=warm.get('process_threads'), cold_ms=dict(n=len(cold_times), p50=percentile(cold_times,.5), p95=percentile(cold_times,.95), p99=percentile(cold_times,.99)),
            warm_ms=dict(n=len(timings),p50=percentile(timings,.5),p95=percentile(timings,.95),p99=percentile(timings,.99)),
            cold_raw_ms=cold_times, warm_raw_ms=timings, warm_errors=sum('error' in r for r in warm['results']),
            coverage_statistics={g: data['statistics'] for g, data in index['graphs'].items()})
    raw.close()
    multiplier = 1 if sys.platform == 'darwin' else 1024
    metadata['cli_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * multiplier
    metadata['controller_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * multiplier
    metadata['aggregate_rss_upper_bound_bytes'] = metadata['cli_peak_rss_bytes'] + metadata['controller_peak_rss_bytes']
    write(out / 'environment.json', metadata)
    write(out / 'summary.json', dict(splits=summaries, performance=performance, aggregate_peak_rss_bytes=metadata['aggregate_rss_upper_bound_bytes']))
    write(out / 'failures.json', failures)
    # Archive the reproducible load without checking in 20,000 generated RDF lines.
    scale_rdf = Path(corpora['scale']['rdf'])
    with scale_rdf.open('rb') as source, gzip.open(out / 'scale.nq.gz', 'wb') as target:
        shutil.copyfileobj(source, target)
    scale_rdf.unlink()
    # Preserve a hash inventory, including raw ranks, requests and failure logs.
    write(out / 'artifacts.json', {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps({k: v['pilot_targets'] for k, v in summaries.items()}, indent=2))
    return int(bool(failures) or any(s['errors'] for s in summaries.values()) or any(p['warm_errors'] for p in performance.values()))


def verify_report(out):
    manifest, cases = verify()
    out = Path(out)
    for name, expected in read(out / 'artifacts.json').items():
        require(sha(out / name) == expected, f'Report artifact changed: {name}')
    environment = read(out / 'environment.json')
    require(environment['manifest_sha256'] == sha(MANIFEST), 'Report uses another freeze')
    with gzip.open(out / 'ranks.jsonl.gz', 'rt', encoding='utf-8') as f:
        rows = [json.loads(line) for line in f]
    expected = {c['id']: c for c in cases}
    summary = read(out / 'summary.json')
    for split in ['development', 'evaluation']:
        selected = [r for r in rows if r['split'] == split]
        require(len(selected) == 80 and {r['id'] for r in selected} == set(expected), 'Missing or duplicate ranked cases')
        queries = {q['id']: q['query'] for q in read(ROOT / manifest[split])['queries']}
        for row in selected:
            case = expected[row['id']]
            require(all(row[k] == case[k] for k in ['language', 'family', 'status', 'relevant']), 'Rank judgment or denominator changed')
            require(row['query'] == queries[row['id']], 'Rank formulation changed')
            corpus = manifest['corpora'][case['corpus']]
            scope = read(ROOT / corpus['scope'])
            require(all(h['graph'] in scope for h in row['hits']), 'Rank escaped corpus scope')
            if 'error' not in row:
                require(row['snapshot_id'] == read(ROOT / corpus['config'])['snapshot_id'], 'Rank snapshot changed')
            require(row['metrics'] == score(case, row), 'Rank metrics changed')
        require(summary['splits'][split] == summarize(selected), 'Summary differs from raw ranks')
    with gzip.open(out / 'scale.nq.gz', 'rb') as f:
        require(hashlib.sha256(f.read()).hexdigest() == manifest['scale']['rdf_sha256'], 'Archived scale corpus changed')
    require(set(summary['performance']) == set(manifest['corpora']) | {'scale'}, 'Missing performance corpus')
    for name, perf in summary['performance'].items():
        warm = [r['response']['elapsed_ms'] for r in rows if r['split'] == 'performance_warm' and r['corpus'] == name]
        cold = [r['elapsed_ms'] for r in rows if r['split'] == 'performance_cold' and r['corpus'] == name]
        require(len(warm) == environment['warm_queries'] and len(cold) == environment['cold_repetitions'], 'Missing timing samples')
        require(warm == perf['warm_raw_ms'] and cold == perf['cold_raw_ms'], 'Timing samples changed')
        for label, values in [('warm_ms', warm), ('cold_ms', cold)]:
            require(perf[label] == dict(n=len(values), p50=percentile(values,.5), p95=percentile(values,.95), p99=percentile(values,.99)), 'Timing percentiles changed')
    print('Report hashes, ranked denominators, metrics, descriptive intervals and timings verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify', 'verify-report', 'run'])
    parser.add_argument('--binary', default='target/release/verity')
    parser.add_argument('--out', default='artifacts/retrieval-run')
    parser.add_argument('--cpu', type=int)
    parser.add_argument('--cpu-description', default='unspecified; no target-device performance claim')
    parser.add_argument('--compiler', default='unspecified')
    parser.add_argument('--cold', type=int, default=30)
    parser.add_argument('--warm', type=int, default=200)
    args = parser.parse_args()
    if args.command == 'verify':
        verify(); print('Frozen retrieval inputs verified (80 dev + 80 evaluation formulations).'); return 0
    if args.command == 'verify-report':
        verify_report(args.out); return 0
    require(args.cold >= 1 and 1 <= args.warm <= 1000, 'Invalid repetition counts')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
