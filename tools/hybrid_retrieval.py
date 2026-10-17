#!/usr/bin/env python3
"""Issue 50 opt-in retrieval experiment and model-free evidence replay; no Ask inputs."""
import argparse
from array import array
from collections import Counter
import gzip
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time

import embedding_experiment as e
import retrieval as r

ROOT = r.ROOT
SPEC = ROOT/'benchmarks/hybrid/protocol.json'
SYSTEMS = ('bm25', 'embedding', 'fusion')
VARIANTS = ('bm25-46', 'skos-definitions-v1')
METRICS = ('recall@1', 'recall@5', 'recall@10', 'recall@50', 'mrr@10')


def verify_protocol():
    spec = r.read(SPEC)
    for path, expected in spec['sha256'].items():
        r.require(r.sha(ROOT/path) == expected, 'Hybrid frozen input changed: ' + path)
    cases = r.read(ROOT/spec['cases'])
    r.require(len(cases) >= 120 and len({c['id'] for c in cases}) == len(cases), 'Retrieval query denominator changed')
    r.require({c['split'] for c in cases} == {'development', 'evaluation'}, 'Invalid retrieval split')
    r.require(spec['fusion'] == e.verify()[0]['fusion'], 'Unregistered fusion change')
    r.require(spec['parameters'] == dict(limit=50, k1=1.2, b=0.75, max_tokens=256), 'Unregistered ranking change')
    r.require(spec['model'] == e.verify()[0]['model'] and spec['revision'] == e.verify()[0]['revision'], 'Changed model')
    for c in cases:
        r.require(c['language'] in {'no', 'en'} and 0 < len(c['query'].encode()) <= 4096, 'Invalid language/query')
        r.require(c['role'] in {'entity', 'predicate', 'class'}, 'Invalid role')
        r.require(c['status'] in {'relevant', 'ambiguous', 'no_match'}, 'Invalid relevance state')
        r.require(bool(c['relevant']) == (c['status'] != 'no_match'), 'Invalid judgment denominator')
        r.require(c['review_status'] == 'AI_reference_only' and c['author'] and c['group_lineage'], 'Missing judgment origin')
        r.require(len(c['witnesses']) == len(c['relevant']), 'Missing original source witness')
    return spec, cases


def inventory(out):
    r.write(out/'artifacts.json', {p.name: e.digest(p) for p in sorted(out.iterdir())
                                  if p.is_file() and p.name != 'artifacts.json'})


def prepare(args):
    spec, cases = verify_protocol()
    checked = e.assets(args.model_dir)
    r.require(checked['valid'], 'Pinned model assets missing or changed')
    _, runtime = e.cpu_runtime()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    corpus = spec['corpus']
    exports = {}
    for variant, binary in zip(VARIANTS, [args.baseline_binary, args.binary]):
        payload = e.export_corpus(binary, corpus)
        e.save_gzip(out/f'{variant}-documents.json.gz', payload)
        exports[variant] = payload
        r.require(('including skos:definition' in payload['manifest']['rules']) == (variant == 'skos-definitions-v1'), 'Variant binary/representation swapped')
        allowed = {(d['graph'], d['iri']): d for d in payload['documents']}
        for c in cases:
            r.require(all((h['graph'], h['iri']) in allowed and c['role'] in
                          allowed[h['graph'], h['iri']]['document']['roles'] for h in c['relevant']),
                      'Judged resource not retrievable in authorized role/scope: ' + c['id'])
    for variant, session_binary in zip(VARIANTS, [args.baseline_session, args.session]):
        session = Session(str(Path(session_binary).resolve()), corpus)
        try:
            r.require(session.ready['manifest'] == exports[variant]['manifest'], 'Resident session/export manifest mismatch: ' + variant)
        finally:
            session.close()
    r.require([(d['graph'], d['iri'], d['document']['roles']) for d in exports[VARIANTS[0]]['documents']] ==
              [(d['graph'], d['iri'], d['document']['roles']) for d in exports[VARIANTS[1]]['documents']],
              'Variant candidate universes differ')
    paths = ['tools/hybrid_retrieval.py', 'tools/gemet.py', 'tools/embedding_experiment.py',
             'tools/retrieval.py', 'tools/embedding-requirements.txt', 'Cargo.lock', 'rust-toolchain.toml']
    paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'crates').rglob('*.rs'))]
    sessions = dict(zip(VARIANTS, map(lambda p: str(Path(p).resolve()), [args.baseline_session, args.session])))
    frozen = dict(version=1, protocol_sha256=r.sha(SPEC), frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        model=checked, model_dir=str(Path(args.model_dir).resolve()), runtime=runtime,
        sessions=sessions, session_sha256={v: e.digest(p) for v, p in sessions.items()},
        binary_sha256={v: e.digest(p) for v, p in zip(VARIANTS, [args.baseline_binary, args.binary])},
        code_sha256={p: r.sha(ROOT/p) for p in paths}, inputs_sha256=spec['sha256'],
        exports_sha256={p.name: r.sha(p) for p in out.iterdir()},
        baseline_revision=spec['baseline_revision'], cpu_description=args.cpu_description,
        scheduling='Native host scheduler; four Torch intra-op threads, one inter-op; no affinity or quota; OS caches retained',
        legal_sha256=r.read(ROOT/'reports/issue-38-embeddinggemma/freeze.json')['legal_sha256'],
        compiler=subprocess.check_output(['rustc', '-Vv'], text=True).strip(),
        no_tuning=True, holdout_accessed=False)
    r.write(out/'freeze.json', frozen)
    inventory(out)
    print('Frozen before parity, document inference or scoring: ' + r.sha(out/'freeze.json'), flush=True)


class Session:
    def __init__(self, binary, corpus):
        self.process = subprocess.Popen([binary, *[str(ROOT/corpus[k]) for k in ['rdf', 'policy', 'scope', 'config']]],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.ready = self._read()
        r.require(self.ready['ready'], 'Resident lexical index did not start')

    def _read(self):
        # A failed child closes stdout; its error is retained by the parent run.
        line = self.process.stdout.readline()
        if not line:
            raise ValueError('Resident lexical process failed: ' + self.process.stderr.read())
        return json.loads(line)

    def query(self, request):
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + '\n')
        self.process.stdin.flush()
        return self._read()

    def close(self):
        self.process.stdin.close()
        code = self.process.wait(timeout=30)
        error = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        r.require(code == 0, 'Resident lexical process failed: ' + error)


def request(case, spec):
    return dict(query=case['query'], role=case['role'], scope=r.read(ROOT/spec['corpus']['scope']), limit=50)


def vector_write(path, matrix):
    with gzip.open(path, 'wb') as stream:
        stream.write(matrix.detach().cpu().numpy().astype('<f4').tobytes())


def vector_read(path, rows):
    with gzip.open(path, 'rb') as stream:
        raw = stream.read(rows * 768 * 4 + 1)
    r.require(len(raw) == rows * 768 * 4, 'Malformed vector dimensions')
    values = array('f')
    values.frombytes(raw)
    if sys.byteorder != 'little':
        values.byteswap()
    r.require(all(math.isfinite(v) for v in values), 'Nonfinite vector')
    matrix = [values[i:i+768] for i in range(0, len(values), 768)]
    r.require(all(abs(sum(v*v for v in row) - 1) <= 2e-5 for row in matrix), 'Unnormalized vector')
    return matrix


def state(count):
    return 'ambiguous_candidates' if count > 1 else 'low_confidence' if count else 'no_match'


def groups(rows):
    result = {'overall': rows}
    for key in ['language', 'family', 'role', 'corpus', 'authorized_scope']:
        for value in sorted({row[key] for row in rows}):
            result[f'{key}/{value}'] = [row for row in rows if row[key] == value]
    return result


def metrics(rows):
    return {key: {metric: r.interval([row['metrics'][metric] for row in group]) for metric in METRICS}
            for key, group in groups([row for row in rows if row['status'] == 'relevant']).items()}


def outcomes(rows):
    return {key: dict(n=len(group), states=dict(sorted(Counter(row['result_status'] for row in group).items())),
                     returned_candidates=r.interval([float(bool(row['hits'])) for row in group]),
                     zero_hits=sum(not row['hits'] for row in group), errors=sum('error' in row for row in group))
            for key, group in {'all': rows, **{s: [row for row in rows if row['status'] == s]
                for s in ['relevant', 'ambiguous', 'no_match']},
                'hard_negative': [row for row in rows if row['family'] == 'hard_negative']}.items()}


def summarize(rows):
    result = {}
    for variant in VARIANTS:
        result[variant] = {}
        for split in ['development', 'evaluation']:
            selected = [row for row in rows if row['variant'] == variant and row['split'] == split]
            base = {row['id']: row for row in selected if row['system'] == 'bm25'}
            methods = {}
            for system in SYSTEMS:
                current = [row for row in selected if row['system'] == system]
                paired = {key: {metric: r.interval([row['metrics'][metric] - base[row['id']]['metrics'][metric]
                                                  for row in group]) for metric in METRICS}
                          for key, group in groups([row for row in current if row['status'] == 'relevant']).items()}
                methods[system] = dict(metrics=metrics(current), outcomes=outcomes(current), paired_delta=paired,
                    new_recall10_wins=[row['id'] for row in current if row['status'] == 'relevant'
                                      and base[row['id']]['metrics']['recall@10'] == 0 and row['metrics']['recall@10'] > 0],
                    mrr10_regressions=[row['id'] for row in current if row['status'] == 'relevant'
                                      and row['metrics']['mrr@10'] < base[row['id']]['metrics']['mrr@10']],
                    new_false_candidate_returns=[row['id'] for row in current if row['status'] == 'no_match'
                                                 and row['hits'] and not base[row['id']]['hits']],
                    exact_rank_regressions=[row['id'] for row in current if row['status'] == 'relevant'
                        and base[row['id']]['hits'] and base[row['id']]['hits'][0].get('exact')
                        and row['metrics']['mrr@10'] < base[row['id']]['metrics']['mrr@10']])
            result[variant][split] = methods
    return result


def percentiles(samples):
    return dict(n=len(samples), p50=r.percentile(samples, .50), p95=r.percentile(samples, .95), p99=r.percentile(samples, .99))


def decision(summary, performance, memory, failures, spec):
    rule = spec['adoption']
    decisions = {}
    for variant in VARIANTS:
        methods = summary[variant]['evaluation']
        current = methods['fusion']
        delta = current['paired_delta']['overall']
        gain = any(delta[m]['mean'] >= threshold and delta[m]['descriptive_95'][0] > 0
                   for m, threshold in [('recall@10', rule['recall10_gain']), ('mrr@10', rule['mrr10_gain'])])
        languages = all(current['paired_delta']['language/'+lang][m]['mean'] >= -rule['max_language_regression']
                        for lang in ['no', 'en'] for m in ['recall@10', 'mrr@10'])
        false_delta = current['outcomes']['no_match']['returned_candidates']['mean'] - methods['bm25']['outcomes']['no_match']['returned_candidates']['mean']
        checks = dict(positive_paired_gain=gain, language_nonregression=languages,
            exact_nonregression=not current['exact_rank_regressions'],
            no_match_nonregression=false_delta <= rule['max_no_match_return_increase'],
            warm_p95=performance[variant]['fusion']['p95'] <= rule['warm_p95_ms'],
            memory=memory['aggregate_upper_bound_bytes'] <= rule['rss_bytes'], no_failures=not failures)
        decisions[variant] = dict(checks=checks, engineering_rule_pass=all(checks.values()), no_match_return_delta=false_delta)
    return dict(recommendation='keep_bm25; defer hybrid pending owner decision and independent relevance/usability review',
                variants=decisions, automatic_integration=False, human_review_available=False,
                phase_0_gate=False, retrieval_is_interpretation=False)


def cold(args):
    r.require(args.allow_inference, 'Cold inference requires --allow-inference')
    frozen = Path(args.freeze)
    freeze = r.read(frozen/'freeze.json')
    spec, cases = verify_protocol()
    torch, _ = e.cpu_runtime()
    encoder = e.Encoder(freeze['model_dir'], torch, e.verify()[0])
    payload = e.load_gzip(frozen/f'{args.variant}-documents.json.gz')
    vectors = vector_read(Path(args.vectors), len(payload['documents']))
    matrix = torch.tensor(vectors, dtype=torch.float32)
    session = Session(freeze['sessions'][args.variant], spec['corpus'])
    r.require(session.ready['manifest'] == payload['manifest'], 'Cold session/export manifest mismatch')
    case = cases[args.case]
    lexical = session.query(request(case, spec))
    dense = e.query(encoder, payload, matrix, case['query'], case['role'])
    json.dumps(e.fuse(lexical['hits'], dense), ensure_ascii=False)
    session.close()
    unit = 1 if sys.platform == 'darwin' else 1024
    print(json.dumps(dict(model_load_ms=encoder.load_ms, query_id=case['id'], lexical_hits=len(lexical['hits']), dense_hits=len(dense),
        worker_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit,
        nested_child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit)))


def run(args):
    r.require(args.allow_inference, 'New inference requires explicit --allow-inference on a capable local host')
    spec, cases = verify_protocol()
    frozen = Path(args.freeze).resolve()
    freeze = r.read(frozen/'freeze.json')
    r.require(freeze['protocol_sha256'] == r.sha(SPEC), 'Protocol changed after freeze')
    for path, expected in freeze['code_sha256'].items():
        r.require(r.sha(ROOT/path) == expected, 'Code changed after freeze: ' + path)
    for path, expected in freeze['exports_sha256'].items():
        r.require(r.sha(frozen/path) == expected, 'Export changed after freeze')
    for v, path in freeze['sessions'].items():
        r.require(e.digest(path) == freeze['session_sha256'][v], 'Resident binary changed after freeze')
    r.require(e.assets(freeze['model_dir']) == freeze['model'], 'Model changed after freeze')
    torch, runtime = e.cpu_runtime()
    r.require(runtime == freeze['runtime'], 'Runtime changed after freeze')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    r.write(out/'run.json', dict(status='running', freeze_sha256=r.sha(frozen/'freeze.json'), started_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
    rows, samples, builds, performance, failures = [], [], {}, {}, []
    rank_file = gzip.open(out/'ranks.jsonl.gz', 'wt', encoding='utf-8')
    context = dict(stage='parity')
    try:
        encoder = e.parity_run(freeze['model_dir'], torch, e.verify()[0], out)
        for variant in VARIANTS:
            context = dict(stage='document_embeddings', variant=variant)
            print('Embedding ' + variant, flush=True)
            payload = e.load_gzip(frozen/f'{variant}-documents.json.gz')
            documents = payload['documents']
            start = time.perf_counter()
            chunks = []
            for i in range(0, len(documents), 8):
                chunks.append(encoder.encode([d['input'] for d in documents[i:i+8]]))
                if i % 400 == 0:
                    print(f'{variant}: {i}/{len(documents)}', flush=True)
            matrix = torch.cat(chunks)
            vector_build_ms = (time.perf_counter() - start) * 1000
            vector_write(out/f'{variant}-vectors.f32.gz', matrix)
            session = Session(freeze['sessions'][variant], spec['corpus'])
            r.require(session.ready['manifest'] == payload['manifest'], 'Resident session/export manifest mismatch')
            builds[variant] = dict(documents=len(documents), embedding_build_ms=vector_build_ms,
                vector_bytes=matrix.numel() * 4, vector_disk_bytes=(out/f'{variant}-vectors.f32.gz').stat().st_size,
                lexical_build=session.ready, input_characters=percentiles([len(d['input']) for d in documents]),
                truncated_token_inputs=sum(len(encoder.tokenizer(d['input'], truncation=False)['input_ids']) > 256 for d in documents))
            qvectors = []
            with gzip.open(out/f'{variant}-scores.jsonl.gz', 'wt', encoding='utf-8') as score_file:
                for case in cases:
                    context = dict(stage='retrieval', variant=variant, id=case['id'])
                    start = time.perf_counter()
                    response = session.query(request(case, spec))
                    lexical_ms = (time.perf_counter() - start) * 1000
                    start = time.perf_counter()
                    json.dumps(request(case, spec), ensure_ascii=False)
                    vector = encoder.encode([encoder.spec['prefixes']['query'] + case['query']])[0]
                    qvectors.append(vector)
                    selected = [i for i, d in enumerate(documents) if case['role'] in d['document']['roles']]
                    scores = (matrix[selected] @ vector).tolist()
                    r.require(all(math.isfinite(s) for s in scores), 'Nonfinite similarity')
                    hits = [dict(graph=documents[i]['graph'], iri=documents[i]['iri'], score=s)
                        for i, s in sorted(zip(selected, scores), key=lambda pair: (-pair[1], documents[pair[0]]['iri'], documents[pair[0]]['graph']))[:50]]
                    json.dumps(hits, ensure_ascii=False)
                    dense_ms = (time.perf_counter() - start) * 1000
                    start = time.perf_counter()
                    fusion = e.fuse(response['hits'], hits)
                    json.dumps(fusion, ensure_ascii=False)
                    fusion_ms = lexical_ms + dense_ms + (time.perf_counter() - start) * 1000
                    samples.append(dict(variant=variant, id=case['id'], bm25=lexical_ms, embedding=dense_ms, fusion=fusion_ms))
                    score_file.write(json.dumps(dict(id=case['id'], indices=selected, scores=scores)) + '\n')
                    for system, ranked in [('bm25', response['hits']), ('embedding', hits), ('fusion', fusion)]:
                        row = dict(case, variant=variant, system=system, snapshot_id=payload['manifest']['snapshot_id'],
                            result_status=response['status'] if system == 'bm25' else state(len(selected) if system == 'embedding' else len(fusion)),
                            hits=[{k: h[k] for k in ['graph', 'iri', 'score', 'exact'] if k in h} for h in ranked])
                        row['metrics'] = r.score(case, row)
                        rows.append(row)
                        rank_file.write(json.dumps(row, ensure_ascii=False) + '\n')
                        rank_file.flush()
            session.close()
            vector_write(out/f'{variant}-queries.f32.gz', torch.stack(qvectors))
            cold_samples = []
            for i, case_index in enumerate(spec['cold_case_indices']):
                context = dict(stage='cold_measurement', variant=variant, id=cases[case_index]['id'])
                start = time.perf_counter()
                proc = subprocess.run([sys.executable, __file__, 'cold', '--allow-inference', '--freeze', str(frozen), '--variant', variant,
                    '--vectors', str(out/f'{variant}-vectors.f32.gz'), '--case', str(case_index)],
                    capture_output=True, text=True, timeout=180)
                elapsed_ms = (time.perf_counter() - start) * 1000
                (out/f'{variant}-cold-{i}.stderr.txt').write_text(proc.stderr)
                r.require(proc.returncode == 0, 'Cold worker failed: ' + proc.stderr)
                cold_samples.append(dict(elapsed_ms=elapsed_ms, **json.loads(proc.stdout)))
            performance[variant] = {system: percentiles([s[system] for s in samples if s['variant'] == variant]) for system in SYSTEMS}
            performance[variant]['cold_samples'] = cold_samples
            performance[variant]['cold_fusion_end_to_end'] = percentiles([s['elapsed_ms'] for s in cold_samples])
        r.write(out/'summary.json', summarize(rows))
        r.write(out/'run.json', dict(status='complete', freeze_sha256=r.sha(frozen/'freeze.json')))
    except Exception as exc:
        failures.append(dict(context, error=str(exc)))
        r.write(out/'run.json', dict(status='failed', freeze_sha256=r.sha(frozen/'freeze.json')))
        raise
    finally:
        rank_file.close()
        unit = 1 if sys.platform == 'darwin' else 1024
        memory = dict(controller_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit,
                      child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit)
        memory['nested_child_peak_rss_bytes'] = max((sample['nested_child_peak_rss_bytes']
            for perf in performance.values() for sample in perf['cold_samples']), default=0)
        memory['aggregate_upper_bound_bytes'] = sum(memory.values())
        r.write(out/'memory.json', memory)
        r.write(out/'failures.json', failures)
        r.write(out/'performance.json', performance)
        r.write(out/'samples.json', samples)
        r.write(out/'builds.json', dict(corpora=builds, model_load_ms=encoder.load_ms if 'encoder' in locals() else None,
            model_asset_bytes=sum((Path(freeze['model_dir'])/p).stat().st_size for p in freeze['model']['sha256']),
            platform=platform.platform(), cpu_description=freeze['cpu_description']))
        if (out/'summary.json').exists():
            r.write(out/'decision.json', decision(r.read(out/'summary.json'), performance, memory, failures, spec))
        inventory(out)


def verify_report(frozen, out, *, replay_vectors=True):
    spec, cases = verify_protocol()
    frozen, out = Path(frozen), Path(out)
    freeze = r.read(frozen/'freeze.json')
    r.require(freeze['protocol_sha256'] == r.sha(SPEC), 'Changed protocol')
    r.require(r.read(out/'run.json') == dict(status='complete', freeze_sha256=r.sha(frozen/'freeze.json')), 'Run incomplete or freeze changed')
    for directory in [frozen, out]:
        inv = r.read(directory/'artifacts.json')
        r.require(set(inv) == {p.name for p in directory.iterdir() if p.is_file() and p.name != 'artifacts.json'}, 'Incomplete artifact inventory')
        for name, expected in inv.items():
            r.require(e.digest(directory/name) == expected, 'Changed evidence artifact: ' + name)
    parity = e.compare_parity(r.read(out/'parity-reference.json'), r.read(out/'parity-runtime.json'))
    r.require(parity == r.read(out/'parity.json'), 'Changed parity summary')
    with gzip.open(out/'ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    r.require(len(rows) == len(cases) * len(VARIANTS) * len(SYSTEMS), 'Lost rank denominators')
    ranked = {(row['variant'], row['system'], row['id']): row for row in rows}
    r.require(len(ranked) == len(rows), 'Duplicate rank identity')
    for variant in VARIANTS:
        path = f'{variant}-documents.json.gz'
        r.require(e.digest(frozen/path) == freeze['exports_sha256'][path], 'Changed authorized export')
        payload = e.load_gzip(frozen/path)
        docs = payload['documents']
        matrix = vector_read(out/f'{variant}-vectors.f32.gz', len(docs))
        qvectors = vector_read(out/f'{variant}-queries.f32.gz', len(cases))
        with gzip.open(out/f'{variant}-scores.jsonl.gz', 'rt', encoding='utf-8') as stream:
            scores = [json.loads(line) for line in stream]
        r.require(len(scores) == len(cases), 'Lost dense candidate pools')
        for case, query_vector, pool in zip(cases, qvectors, scores):
            selected = [i for i, d in enumerate(docs) if case['role'] in d['document']['roles']]
            r.require(pool['id'] == case['id'] and pool['indices'] == selected and len(pool['scores']) == len(selected), 'Changed role-filtered candidate pool')
            r.require(all(math.isfinite(s) and -1.00001 <= s <= 1.00001 for s in pool['scores']), 'Malformed similarity')
            if replay_vectors:
                for i, actual in zip(selected, pool['scores']):
                    expected = sum(a*b for a, b in zip(matrix[i], query_vector))
                    r.require(abs(expected - actual) <= 1e-6, 'Similarity does not replay from saved vectors')
            dense = [dict(graph=docs[i]['graph'], iri=docs[i]['iri'], score=s)
                for i, s in sorted(zip(selected, pool['scores']), key=lambda pair: (-pair[1], docs[pair[0]]['iri'], docs[pair[0]]['graph']))[:50]]
            base = ranked[variant, 'bm25', case['id']]
            r.require(ranked[variant, 'embedding', case['id']]['hits'] == dense, 'Dense ranks do not replay')
            r.require(ranked[variant, 'fusion', case['id']]['hits'] == e.fuse(base['hits'], dense), 'Fusion ranks do not replay')
            allowed = {(docs[i]['graph'], docs[i]['iri']) for i in selected}
            for system in SYSTEMS:
                row = ranked[variant, system, case['id']]
                r.require(all(row[k] == case[k] for k in case), 'Changed judgment, split, lineage or query')
                r.require(row['snapshot_id'] == payload['manifest']['snapshot_id'], 'Changed snapshot')
                r.require(len(row['hits']) <= 50 and all((h['graph'], h['iri']) in allowed for h in row['hits']), 'Rank escaped authorized scope/role')
                r.require(row['metrics'] == r.score(case, row), 'Changed metrics')
                if system != 'bm25':
                    r.require(row['result_status'] == state(len(selected) if system == 'embedding' else len(row['hits'])), 'Changed candidate state')
    summary = r.read(out/'summary.json')
    r.require(summary == summarize(rows), 'Summary does not replay')
    perf = r.read(out/'performance.json')
    samples = r.read(out/'samples.json')
    for variant in VARIANTS:
        selected = [s for s in samples if s['variant'] == variant]
        r.require([s['id'] for s in selected] == [c['id'] for c in cases], 'Timing query distribution changed')
        for system in SYSTEMS:
            r.require(perf[variant][system] == percentiles([s[system] for s in selected]), 'Changed warm percentiles')
        r.require([s['query_id'] for s in perf[variant]['cold_samples']] == [cases[i]['id'] for i in spec['cold_case_indices']], 'Cold queries changed')
        r.require(perf[variant]['cold_fusion_end_to_end'] == percentiles([s['elapsed_ms'] for s in perf[variant]['cold_samples']]), 'Changed cold percentiles')
    memory = r.read(out/'memory.json')
    nested = max(s['nested_child_peak_rss_bytes'] for p in perf.values() for s in p['cold_samples'])
    r.require(memory['nested_child_peak_rss_bytes'] == nested and memory['aggregate_upper_bound_bytes'] ==
              sum(memory[k] for k in ['controller_peak_rss_bytes', 'child_peak_rss_bytes', 'nested_child_peak_rss_bytes']),
              'Incomplete process-tree RSS accounting')
    r.require(r.read(out/'decision.json') == decision(summary, perf, memory, r.read(out/'failures.json'), spec), 'Decision does not replay')
    return summary


def verify_lexical(binary, report):
    spec, cases = verify_protocol()
    with gzip.open(Path(report)/'ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
        saved = {row['id']: row for row in map(json.loads, stream)
                 if row['variant'] == 'skos-definitions-v1' and row['system'] == 'bm25'}
    with tempfile.TemporaryDirectory(prefix='hybrid-lexical-') as directory:
        path = Path(directory)/'requests.json'
        r.write(path, [request(c, spec) for c in cases])
        batch = e.invoke(str(Path(binary).resolve()), 'find-batch', spec['corpus'], path)
    r.require(len(batch['results']) == len(cases), 'Native lexical replay lost cases')
    for case, actual in zip(cases, batch['results']):
        r.require('result' in actual, 'Native lexical replay failed')
        actual, expected = actual['result'], saved[case['id']]
        r.require(actual['snapshot_id'] == expected['snapshot_id'] and actual['status'] == expected['result_status'], 'Native lexical status/snapshot changed')
        r.require([(h['graph'], h['iri'], h['exact']) for h in actual['hits']] ==
                  [(h['graph'], h['iri'], h['exact']) for h in expected['hits']], 'Native lexical ranks changed')
        r.require(all(math.isclose(a['score'], b['score'], rel_tol=1e-12, abs_tol=1e-12)
                      for a, b in zip(actual['hits'], expected['hits'])), 'Native lexical scores changed')
        r.require(r.score(case, actual) == expected['metrics'], 'Native lexical metrics changed')
    return dict(queries=len(cases), variant='skos-definitions-v1', native_lexical_replay=True, model_invoked=False)


def scope_canary(binary):
    spec, _ = verify_protocol()
    original = e.export_corpus(binary, spec['corpus'])
    with tempfile.TemporaryDirectory(prefix='hybrid-canary-') as directory:
        directory = Path(directory)
        raw = (ROOT/spec['corpus']['rdf']).read_bytes()
        private = b''.join(f'<urn:PRIVATE_ID_CANARY:{i}> <http://www.w3.org/2004/02/skos/core#definition> "PRIVATE_TEXT_COUNT_CANARY"@en <urn:PRIVATE_GRAPH_CANARY> .\n'.encode() for i in range(31))
        private += b'<http://www.eionet.europa.eu/gemet/concept/1001> <http://www.w3.org/2004/02/skos/core#prefLabel> "PRIVATE_LABEL_CANARY"@no <urn:PRIVATE_GRAPH_CANARY> .\n'
        (directory/'snapshot.nq').write_bytes(raw + private)
        config = r.read(ROOT/spec['corpus']['config'])
        import hashlib
        config['snapshot_id'] = 'sha256:' + hashlib.sha256(b'graph-verity-snapshot-v1\0nquads\0' + raw + private).hexdigest()
        config['graphs']['urn:PRIVATE_GRAPH_CANARY'] = dict(source='PRIVATE_SOURCE_CANARY', license='private canary', source_revision='canary', importer_revision='canary')
        r.write(directory/'config.json', config)
        corpus = dict(spec['corpus'], rdf=str(directory/'snapshot.nq'), config=str(directory/'config.json'))
        changed = e.export_corpus(binary, corpus)
        r.require(original['documents'] == changed['documents'], 'Private ID/text/count changed authorized documents')
        r.require('CANARY' not in json.dumps(changed, ensure_ascii=False), 'Private metadata escaped authorized export')
        r.write(directory/'scope.json', ['urn:PRIVATE_GRAPH_CANARY'])
        paths = [str(ROOT/corpus[k]) if k != 'format' else corpus[k] for k in ['rdf', 'format', 'policy', 'scope', 'config']]
        paths[3] = str(directory/'scope.json')
        result = subprocess.run([str(Path(binary).resolve()), 'index-build', *paths], capture_output=True, text=True, timeout=180)
        r.require(result.returncode != 0 and not result.stdout and 'scope' in result.stderr, 'Unauthorized scope produced an index')
    return dict(authorized_documents=len(original['documents']), private_resources_added=31,
                document_roles_text_counts_unchanged=True, metadata_canary_absent=True, unauthorized_scope_denied=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify')
    canary = sub.add_parser('scope-canary')
    canary.add_argument('--binary', required=True)
    lexical = sub.add_parser('verify-lexical')
    lexical.add_argument('--binary', required=True)
    lexical.add_argument('--out', required=True)
    prep = sub.add_parser('prepare')
    for name in ['model-dir', 'binary', 'baseline-binary', 'session', 'baseline-session', 'out', 'cpu-description']:
        prep.add_argument('--'+name, required=True)
    infer = sub.add_parser('run')
    infer.add_argument('--allow-inference', action='store_true')
    infer.add_argument('--freeze', required=True)
    infer.add_argument('--out', required=True)
    replay = sub.add_parser('verify-report')
    replay.add_argument('--freeze', required=True)
    replay.add_argument('--out', required=True)
    worker = sub.add_parser('cold')
    worker.add_argument('--allow-inference', action='store_true')
    worker.add_argument('--freeze', required=True)
    worker.add_argument('--variant', choices=VARIANTS, required=True)
    worker.add_argument('--vectors', required=True)
    worker.add_argument('--case', type=int, required=True)
    args = parser.parse_args()
    if args.command == 'verify-lexical':
        print(json.dumps(verify_lexical(args.binary, args.out)))
    elif args.command == 'scope-canary':
        print(json.dumps(scope_canary(args.binary)))
    elif args.command == 'prepare':
        prepare(args)
    elif args.command == 'run':
        run(args)
    elif args.command == 'cold':
        cold(args)
    elif args.command == 'verify-report':
        verify_report(args.freeze, args.out)
        print('Model-free replay verified.')
    else:
        verify_protocol()


if __name__ == '__main__':
    main()
