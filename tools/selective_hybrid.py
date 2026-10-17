#!/usr/bin/env python3
"""Issue 53: opt-in lexical-first retrieval; frozen, model-free evidence replay."""
import argparse
import gzip
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import time

import embedding_experiment as e
import hybrid_retrieval as h
import retrieval as r
from local_parser import Memory

SPEC = r.ROOT/'benchmarks/selective-hybrid/protocol.json'
HISTORY = r.ROOT/'reports/issue-50-real-rdf-hybrid'
SYSTEMS = (*h.SYSTEMS, 'selective')


def verify_protocol():
    spec = r.read(SPEC)
    h.verify_protocol()
    for path, digest in spec['sha256'].items():
        r.require(e.digest(r.ROOT/path) == digest, 'Selective frozen input changed: ' + path)
    cases = r.read(r.ROOT/spec['cases'])
    old = r.read(r.ROOT/'benchmarks/hybrid/cases.json')
    regressions = [dict(c, split='regression', original_split=c['split']) for c in old]
    r.require(cases[:len(old)] == regressions, 'Exposed cases must remain unchanged regressions')
    new = cases[len(old):]
    r.require(new and all(c['split'] == 'evaluation' for c in new), 'Missing new evaluation')
    r.require(len({c['id'] for c in cases}) == len(cases), 'Duplicate case')
    old_lineages = {g for c in old for g in c['group_lineage']}
    r.require(not old_lineages & {g for c in new for g in c['group_lineage']}, 'Exposed evaluation lineage')
    source = set((r.ROOT/spec['corpus']['rdf']).read_text().splitlines())
    payload = e.load_gzip(HISTORY/'freeze/bm25-46-documents.json.gz')
    allowed = {(d['graph'], d['iri']): d for d in payload['documents']}
    for c in cases:
        r.require(c['language'] in {'no', 'en'} and c['role'] in {'entity', 'predicate', 'class'}, 'Invalid role/language')
        r.require(0 < len(c['query'].encode()) <= 4096, 'Invalid query')
        r.require(c['status'] in {'relevant', 'ambiguous', 'no_match'} and
                  bool(c['relevant']) == (c['status'] != 'no_match'), 'Invalid judgment')
        r.require(c['review_status'] == 'AI_reference_only', 'Review misrepresented')
        r.require(len(c['witnesses']) == len(c['relevant']) and
                  all(w['source_quads'] and set(w['source_quads']) <= source for w in c['witnesses']), 'Missing source witness')
        r.require(len({(x['graph'], x['iri']) for x in c['relevant']}) == len(c['relevant']) and
                  all((x['graph'], x['iri']) in allowed and c['role'] in allowed[x['graph'], x['iri']]['document']['roles']
                      for x in c['relevant']), 'Judgment escaped authorized role/scope')
        r.require(all(w['graph'] == x['graph'] and w['iri'] == x['iri'] and
                      all('<'+x['iri']+'>' in q for q in w['source_quads'])
                      for x,w in zip(c['relevant'], c['witnesses'])), 'Witness identity changed')
    r.require(spec['model'] == e.verify()[0]['model'] and spec['revision'] == e.verify()[0]['revision'], 'Changed model')
    r.require(spec['selective'] == dict(dense_min_score=.73, lexical_head=3, limit=50), 'Unregistered strategy')
    return spec, cases


def exact(document, query):
    query = query.strip()
    return document['iri'] == query or any(t['field'] != 'description' and
        t['value']['text'].lower() == query.lower() for t in document['document']['texts'])


def select(payload, request, lexical, dense, policy):
    """Only the authorized immutable export can confer identity, exactness or metadata."""
    manifest = payload['manifest']
    r.require(set(request['scope']) <= set(manifest['scope']) and request['scope'], 'Unauthorized scope')
    r.require(request['role'] in {'entity', 'predicate', 'class'} and
              0 < len(request['query'].encode()) <= 4096 and 1 <= request['limit'] <= 50, 'Invalid request')
    r.require(lexical['snapshot_id'] == manifest['snapshot_id'] and
              set(lexical['scope']) == set(request['scope']), 'Lexical snapshot/scope mismatch')
    allowed = {(d['graph'], d['iri']): d for d in payload['documents']
               if d['graph'] in request['scope'] and request['role'] in d['document']['roles']}
    exact_ids = {key for key, d in allowed.items() if exact(d, request['query'])}
    components = {}
    for name, hits in [('bm25', lexical['hits']), ('embedding', dense)]:
        r.require(len(hits) <= 50 and len({(x['graph'], x['iri']) for x in hits}) == len(hits), 'Invalid candidate budget/duplicate')
        for hit in hits:
            key = hit['graph'], hit['iri']
            r.require(key in allowed and math.isfinite(hit['score']), 'Candidate escaped scope/role or invalid score')
            if name == 'bm25':
                r.require(hit['exact'] == (key in exact_ids), 'Untrusted exact flag')
            components.setdefault(key, {})[name] = hit['score']
    lexical_ids = [(x['graph'], x['iri']) for x in lexical['hits']]
    exact_hits = [key for key in lexical_ids if key in exact_ids]
    r.require(len(exact_hits) == min(len(exact_ids), 50), 'Missing exact candidates')
    head = [key for key in lexical_ids if key not in exact_ids][:policy['lexical_head']]
    semantic = [(x['graph'], x['iri']) for x in sorted(dense, key=lambda x: (-x['score'], x['iri'], x['graph']))
                if x['score'] >= policy['dense_min_score']]
    ranked, seen = [], set()
    for route, keys in [('exact', exact_hits), ('lexical', head), ('semantic_fill', semantic), ('lexical_tail', lexical_ids)]:
        for key in keys:
            if key not in seen:
                seen.add(key)
                d = allowed[key]
                ranked.append(dict(graph=key[0], iri=key[1], exact=key in exact_ids, route=route,
                                   component_scores=components[key], document=d['document']))
    status = ('ambiguous_exact' if len(exact_ids) > 1 else 'ranked' if exact_ids else h.state(len(ranked)))
    return dict(snapshot_id=manifest['snapshot_id'], manifest=manifest, status=status,
                exact_candidates=len(exact_ids), candidate_count=len(seen), truncated=len(seen) > request['limit'],
                requires_user_selection=True, interpretation_correctness='not_assessed',
                hits=ranked[:request['limit']])


def summarize(rows):
    result = {}
    for variant in h.VARIANTS:
        result[variant] = {}
        for split in ['regression', 'evaluation']:
            selected = [row for row in rows if row['variant'] == variant and row['split'] == split]
            base = {row['id']: row for row in selected if row['system'] == 'bm25'}
            methods = {}
            for system in SYSTEMS:
                current = [row for row in selected if row['system'] == system]
                paired = {key: {m: r.interval([row['metrics'][m] - base[row['id']]['metrics'][m] for row in group])
                                for m in h.METRICS} for key, group in
                          h.groups([row for row in current if row['status'] == 'relevant']).items()}
                methods[system] = dict(metrics=h.metrics(current), outcomes=h.outcomes(current), paired_delta=paired,
                    exact_rank_regressions=[row['id'] for row in current if base[row['id']]['hits'] and
                        base[row['id']]['hits'][0].get('exact') and
                        (not row['hits'] or (row['hits'][0]['graph'], row['hits'][0]['iri']) !=
                         (base[row['id']]['hits'][0]['graph'], base[row['id']]['hits'][0]['iri']))],
                    false_confident_retrieval=[row['id'] for row in current if row['status'] == 'no_match' and row['result_status'] == 'ranked'],
                    new_recall10_wins=[row['id'] for row in current if row['status'] == 'relevant' and
                        base[row['id']]['metrics']['recall@10'] == 0 and row['metrics']['recall@10'] > 0])
            result[variant][split] = methods
    return result


def decision(summary, performance, memory, failures, spec):
    decisions = {}
    for variant in h.VARIANTS:
        methods = summary[variant]['evaluation']
        selected = methods['selective']
        delta = selected['paired_delta']['overall']
        checks = dict(
            gain=any(delta[m]['mean'] >= threshold and delta[m]['descriptive_95'][0] > 0
                     for m, threshold in [('recall@10', .05), ('mrr@10', .03)]),
            language_nonregression=all(selected['paired_delta']['language/'+lang][m]['mean'] >= -.02
                                      for lang in ['no', 'en'] for m in ['recall@10', 'mrr@10']),
            exact_rank_one=all(not summary[variant][s]['selective']['exact_rank_regressions'] for s in ['regression', 'evaluation']),
            no_match_nonregression=selected['outcomes']['no_match']['returned_candidates']['mean'] <=
                                  methods['bm25']['outcomes']['no_match']['returned_candidates']['mean'],
            resident_p95=performance[variant]['selective']['p95'] <= spec['adoption']['warm_p95_ms'],
            conservative_memory=memory['aggregate_upper_bound_bytes'] <= spec['adoption']['rss_bytes'],
            no_failures=not failures)
        decisions[variant] = dict(checks=checks, continuation_screen_pass=all(checks.values()))
    return dict(recommendation='keep BM25; defer hybrid promotion', variants=decisions,
                evidence='AI-reference exploratory', independent_human_review=False,
                automatic_integration=False, retrieval_is_interpretation=False)


def prepare(args):
    spec, _ = verify_protocol()
    checked = e.assets(args.model_dir)
    r.require(checked['valid'], 'Pinned assets changed')
    _, runtime = e.cpu_runtime()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    sessions = dict(zip(h.VARIANTS, [str(Path(args.baseline_session).resolve()), str(Path(args.session).resolve())]))
    exports = {}
    for variant, session in sessions.items():
        # Reuse the exact authorized text of #50, never regenerate or enrich it.
        source = HISTORY/'freeze'/f'{variant}-documents.json.gz'
        (out/source.name).write_bytes(source.read_bytes())
        payload = e.load_gzip(source)
        lexical = h.Session(session, spec['corpus'])
        try:
            r.require(lexical.ready['manifest'] == payload['manifest'], 'Session representation changed')
        finally:
            lexical.close()
        exports[source.name] = e.digest(out/source.name)
    paths = ['tools/selective_hybrid.py', 'tools/hybrid_retrieval.py', 'tools/embedding_experiment.py',
             'tools/retrieval.py', 'tools/local_parser.py', 'tools/embedding-requirements.txt', 'Cargo.lock', 'rust-toolchain.toml']
    paths += [str(p.relative_to(r.ROOT)) for p in sorted((r.ROOT/'crates').rglob('*.rs'))]
    freeze = dict(protocol_sha256=e.digest(SPEC), frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  model=checked, model_dir=str(Path(args.model_dir).resolve()), runtime=runtime,
                  sessions=sessions, session_sha256={v: e.digest(p) for v, p in sessions.items()},
                  exports_sha256=exports, code_sha256={p: e.digest(r.ROOT/p) for p in paths},
                  compiler=subprocess.check_output(['rustc', '-Vv'], text=True).strip(),
                  cpu_description=args.cpu_description, holdout_accessed=False,
                  legal_sha256=r.read(HISTORY/'freeze/freeze.json')['legal_sha256'])
    r.write(out/'freeze.json', freeze)
    h.inventory(out)
    print('Frozen before new evaluation inference: ' + e.digest(out/'freeze.json'), flush=True)


def check_freeze(frozen):
    spec, cases = verify_protocol()
    freeze = r.read(frozen/'freeze.json')
    r.require(freeze['protocol_sha256'] == e.digest(SPEC), 'Protocol changed after freeze')
    for path, digest in freeze['code_sha256'].items():
        r.require(e.digest(r.ROOT/path) == digest, 'Code changed after freeze: ' + path)
    for name, digest in freeze['exports_sha256'].items():
        r.require(e.digest(frozen/name) == digest, 'Export changed after freeze')
    for variant, session in freeze['sessions'].items():
        r.require(e.digest(session) == freeze['session_sha256'][variant], 'Session changed after freeze')
    r.require(e.assets(freeze['model_dir']) == freeze['model'], 'Model changed after freeze')
    return spec, cases, freeze


def worker(args):
    r.require(args.allow_inference, 'Inference requires --allow-inference')
    frozen, out = Path(args.freeze), Path(args.out)
    spec, cases, freeze = check_freeze(frozen)
    torch, runtime = e.cpu_runtime()
    r.require(runtime == freeze['runtime'], 'Runtime changed after freeze')
    if args.cold_case is None:
        encoder = e.parity_run(freeze['model_dir'], torch, e.verify()[0], out)
    else:
        encoder = e.Encoder(freeze['model_dir'], torch, e.verify()[0])
    payload = e.load_gzip(frozen/f'{args.variant}-documents.json.gz')
    docs = payload['documents']
    start = time.perf_counter()
    if args.cold_case is None:
        matrix = torch.cat([encoder.encode([d['input'] for d in docs[i:i+8]]) for i in range(0, len(docs), 8)])
        h.vector_write(out/f'{args.variant}-vectors.f32.gz', matrix)
    else:
        matrix = torch.tensor(h.vector_read(out/f'{args.variant}-vectors.f32.gz', len(docs)), dtype=torch.float32)
    build_ms = (time.perf_counter() - start) * 1000
    session = h.Session(freeze['sessions'][args.variant], spec['corpus'])
    r.require(session.ready['manifest'] == payload['manifest'], 'Session/export manifest mismatch')
    samples, qvectors = [], []
    try:
        selected_cases = cases if args.cold_case is None else [cases[args.cold_case]]
        with gzip.open(out/f'{args.variant}-{args.tag}-ranks.jsonl.gz', 'wt', encoding='utf-8') as ranks, \
             gzip.open(out/f'{args.variant}-{args.tag}-scores.jsonl.gz', 'wt', encoding='utf-8') as scores_file:
            for case in selected_cases:
                request = h.request(case, spec)
                start = time.perf_counter()
                lexical = session.query(request)
                lexical_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                json.dumps(request)
                vector = encoder.encode([encoder.spec['prefixes']['query'] + case['query']])[0]
                qvectors.append(vector)
                indices = [i for i, d in enumerate(docs) if case['role'] in d['document']['roles']]
                scores = (matrix[indices] @ vector).tolist()
                dense = [dict(graph=docs[i]['graph'], iri=docs[i]['iri'], score=s) for i, s in
                    sorted(zip(indices, scores), key=lambda p: (-p[1], docs[p[0]]['iri'], docs[p[0]]['graph']))[:50]]
                json.dumps(dense)
                dense_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                fusion = e.fuse(lexical['hits'], dense)
                json.dumps(fusion)
                fusion_ms = lexical_ms + dense_ms + (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                selective = select(payload, request, lexical, dense, spec['selective'])
                json.dumps(selective, ensure_ascii=False)
                selective_ms = lexical_ms + dense_ms + (time.perf_counter() - start) * 1000
                samples.append(dict(id=case['id'], bm25=lexical_ms, embedding=dense_ms, fusion=fusion_ms, selective=selective_ms))
                scores_file.write(json.dumps(dict(id=case['id'], indices=indices, scores=scores, lexical=lexical)) + '\n')
                for system, hits, status in [('bm25', lexical['hits'], lexical['status']), ('embedding', dense, h.state(len(indices))),
                    ('fusion', fusion, h.state(len(fusion))), ('selective', selective['hits'], selective['status'])]:
                    row = dict(case, variant=args.variant, system=system, snapshot_id=payload['manifest']['snapshot_id'],
                               result_status=status, hits=hits,
                               selection={k: v for k, v in selective.items() if k != 'hits'} if system == 'selective' else None)
                    row['metrics'] = r.score(case, row)
                    ranks.write(json.dumps(row, ensure_ascii=False) + '\n')
                    ranks.flush()
        if args.cold_case is None:
            h.vector_write(out/f'{args.variant}-queries.f32.gz', torch.stack(qvectors))
    finally:
        session.close()
    unit = 1 if sys.platform == 'darwin' else 1024
    r.write(out/f'{args.variant}-{args.tag}.json', dict(samples=samples, model_load_ms=encoder.load_ms,
        vector_build_or_load_ms=build_ms, lexical_build=session.ready, vector_bytes=matrix.numel()*4,
        worker_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit,
        nested_child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit,
        token_truncated_documents=sum(len(encoder.tokenizer(d['input'], truncation=False)['input_ids']) > 256 for d in docs)))


def run(args):
    r.require(args.allow_inference, 'Inference requires --allow-inference')
    frozen, out = Path(args.freeze).resolve(), Path(args.out).resolve()
    spec, _, _ = check_freeze(frozen)
    out.mkdir(parents=True, exist_ok=False)
    r.write(out/'run.json', dict(status='running', freeze_sha256=e.digest(frozen/'freeze.json')))
    memory = Memory()
    memory.worker.start()
    performance, failures, workers, rows = {}, [], [], []
    try:
        # The controller never imports Torch or owns a model; cold and resident workers never overlap.
        for variant in h.VARIANTS:
            timings = []
            for tag, case in [('resident', None)] + [(f'cold-{i}', c) for i, c in enumerate(spec['cold_case_indices'])]:
                print(variant + ' ' + tag, flush=True)
                command = [sys.executable, __file__, 'worker', '--allow-inference', '--freeze', str(frozen),
                           '--out', str(out), '--variant', variant, '--tag', tag]
                if case is not None:
                    command += ['--cold-case', str(case)]
                start = time.perf_counter()
                result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
                elapsed = (time.perf_counter() - start) * 1000
                (out/f'{variant}-{tag}.stderr.txt').write_text(result.stderr)
                r.require(result.returncode == 0, 'Worker failed: ' + result.stderr)
                observed = r.read(out/f'{variant}-{tag}.json')
                workers.append(observed)
                if case is None:
                    performance[variant] = {s: h.percentiles([x[s] for x in observed['samples']]) for s in SYSTEMS}
                    with gzip.open(out/f'{variant}-resident-ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
                        rows.extend(json.loads(line) for line in stream)
                else:
                    timings.append(dict(elapsed_ms=elapsed, id=observed['samples'][0]['id'], model_load_ms=observed['model_load_ms']))
            performance[variant]['cold_samples'] = timings
            performance[variant]['cold_end_to_end'] = h.percentiles([x['elapsed_ms'] for x in timings])
        r.write(out/'summary.json', summarize(rows))
        r.write(out/'run.json', dict(status='complete', freeze_sha256=e.digest(frozen/'freeze.json')))
    except Exception as exc:
        failures.append(str(exc))
        r.write(out/'run.json', dict(status='failed', freeze_sha256=e.digest(frozen/'freeze.json')))
        raise
    finally:
        memory.done.set()
        memory.worker.join(timeout=10)
        unit = 1 if sys.platform == 'darwin' else 1024
        rss = dict(controller_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit,
                   child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit,
                   nested_child_peak_rss_bytes=max((x['nested_child_peak_rss_bytes'] for x in workers), default=0))
        rss['aggregate_upper_bound_bytes'] = sum(rss.values())
        rss.update(sampled_simultaneous_peak_bytes=memory.peak_kib*1024, samples=memory.samples,
                   sampling_error=memory.error, definition='controller HWM + maximum sequential direct child HWM + maximum nested Rust HWM; shared pages counted conservatively')
        r.write(out/'memory.json', rss)
        r.write(out/'performance.json', performance)
        r.write(out/'failures.json', failures)
        if (out/'summary.json').exists():
            r.write(out/'decision.json', decision(r.read(out/'summary.json'), performance, rss, failures, spec))
        h.inventory(out)


def verify_report(frozen, out, *, replay_vectors=True, binary=None, baseline_session=None):
    spec, cases = verify_protocol()
    frozen, out = Path(frozen), Path(out)
    freeze = r.read(frozen/'freeze.json')
    r.require(freeze['protocol_sha256'] == e.digest(SPEC), 'Changed protocol')
    r.require(r.read(out/'run.json') == dict(status='complete', freeze_sha256=e.digest(frozen/'freeze.json')), 'Incomplete run')
    for directory in [frozen, out]:
        inventory = r.read(directory/'artifacts.json')
        r.require(set(inventory) == {p.name for p in directory.iterdir() if p.is_file() and p.name != 'artifacts.json'}, 'Incomplete inventory')
        for name, digest in inventory.items():
            r.require(e.digest(directory/name) == digest, 'Changed artifact: ' + name)
    r.require(e.compare_parity(r.read(out/'parity-reference.json'), r.read(out/'parity-runtime.json')) == r.read(out/'parity.json'), 'Changed parity')
    rows, workers = [], []
    performance = r.read(out/'performance.json')
    for variant in h.VARIANTS:
        name = f'{variant}-documents.json.gz'
        r.require(e.digest(frozen/name) == freeze['exports_sha256'][name] == e.digest(HISTORY/'freeze'/name), 'Changed #50 text')
        payload = e.load_gzip(frozen/name)
        docs = payload['documents']
        vectors = h.vector_read(out/f'{variant}-vectors.f32.gz', len(docs))
        qvectors = h.vector_read(out/f'{variant}-queries.f32.gz', len(cases))
        with gzip.open(out/f'{variant}-resident-ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
            current = [json.loads(line) for line in stream]
        ranked = {(row['id'], row['system']): row for row in current}
        r.require(len(ranked) == len(current) == len(cases)*len(SYSTEMS), 'Rank denominator changed')
        with gzip.open(out/f'{variant}-resident-scores.jsonl.gz', 'rt', encoding='utf-8') as stream:
            pools = [json.loads(line) for line in stream]
        r.require(len(pools) == len(cases), 'Score denominator changed')
        session_path = binary if variant == 'skos-definitions-v1' else baseline_session
        session = h.Session(str(Path(session_path).resolve()), spec['corpus']) if session_path else None
        try:
            for case, vector, pool in zip(cases, qvectors, pools):
                indices = [i for i, d in enumerate(docs) if case['role'] in d['document']['roles']]
                r.require(pool['id'] == case['id'] and pool['indices'] == indices and len(pool['scores']) == len(indices), 'Changed role pool')
                r.require(all(math.isfinite(s) and -1.00001 <= s <= 1.00001 for s in pool['scores']), 'Invalid score')
                if replay_vectors:
                    r.require(all(abs(sum(a*b for a,b in zip(vectors[i], vector))-s) <= 1e-6
                                  for i,s in zip(indices, pool['scores'])), 'Vector score replay failed')
                dense = [dict(graph=docs[i]['graph'], iri=docs[i]['iri'], score=s) for i,s in
                         sorted(zip(indices, pool['scores']), key=lambda p: (-p[1], docs[p[0]]['iri'], docs[p[0]]['graph']))[:50]]
                lexical = pool['lexical']
                if session:
                    actual = session.query(h.request(case, spec))
                    r.require(len(actual['hits']) == len(lexical['hits']), 'Native lexical hit count changed')
                    for left, right in zip(actual['hits'], lexical['hits']):
                        r.require(math.isclose(left['score'], right['score'], rel_tol=1e-12, abs_tol=1e-12), 'Native lexical score changed')
                        left['score'] = right['score']
                    r.require(actual == lexical, 'Native lexical replay changed')
                selected = select(payload, h.request(case, spec), lexical, dense, spec['selective'])
                expected = dict(bm25=(lexical['hits'], lexical['status']), embedding=(dense, h.state(len(indices))),
                                fusion=(e.fuse(lexical['hits'], dense), h.state(len(e.fuse(lexical['hits'], dense)))),
                                selective=(selected['hits'], selected['status']))
                for system, (hits, status) in expected.items():
                    row = ranked[case['id'], system]
                    r.require(all(row[k] == case[k] for k in case) and row['variant'] == variant, 'Changed case/judgment')
                    r.require(row['snapshot_id'] == payload['manifest']['snapshot_id'] and row['hits'] == hits and
                              row['result_status'] == status and row['metrics'] == r.score(case, row), 'Rank/state/metric replay failed')
                    r.require(row['selection'] == ({k:v for k,v in selected.items() if k != 'hits'} if system == 'selective' else None), 'Changed provenance/selection')
        finally:
            if session:
                session.close()
        resident = r.read(out/f'{variant}-resident.json')
        workers.append(resident)
        r.require([x['id'] for x in resident['samples']] == [c['id'] for c in cases], 'Timing workload changed')
        for system in SYSTEMS:
            r.require(performance[variant][system] == h.percentiles([x[system] for x in resident['samples']]), 'Warm percentile changed')
        cold = performance[variant]['cold_samples']
        r.require([x['id'] for x in cold] == [cases[i]['id'] for i in spec['cold_case_indices']], 'Cold workload changed')
        r.require(performance[variant]['cold_end_to_end'] == h.percentiles([x['elapsed_ms'] for x in cold]), 'Cold percentiles changed')
        for i, timing in enumerate(cold):
            observed = r.read(out/f'{variant}-cold-{i}.json')
            r.require([x['id'] for x in observed['samples']] == [timing['id']] and
                      observed['model_load_ms'] == timing['model_load_ms'], 'Cold sample identity changed')
            with gzip.open(out/f'{variant}-cold-{i}-ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
                cold_rows = [json.loads(line) for line in stream]
            r.require(cold_rows == [ranked[timing['id'], s] for s in SYSTEMS], 'Cold/resident ranks differ')
            workers.append(observed)
        rows.extend(current)
    summary = summarize(rows)
    r.require(summary == r.read(out/'summary.json'), 'Summary replay failed')
    memory = r.read(out/'memory.json')
    r.require(memory['nested_child_peak_rss_bytes'] == max(w['nested_child_peak_rss_bytes'] for w in workers) and
              memory['child_peak_rss_bytes'] >= max(w['worker_peak_rss_bytes'] for w in workers) and
              memory['aggregate_upper_bound_bytes'] == sum(memory[k] for k in
                  ['controller_peak_rss_bytes', 'child_peak_rss_bytes', 'nested_child_peak_rss_bytes']), 'Incomplete process-tree accounting')
    r.require(memory['samples'] > 0 and not memory['sampling_error'], 'Missing simultaneous RSS samples')
    r.require(r.read(out/'decision.json') == decision(summary, performance, memory, r.read(out/'failures.json'), spec), 'Decision replay failed')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify')
    prep = sub.add_parser('prepare')
    for name in ['model-dir', 'baseline-session', 'session', 'out', 'cpu-description']:
        prep.add_argument('--'+name, required=True)
    for name in ['run', 'worker', 'verify-report']:
        command = sub.add_parser(name)
        command.add_argument('--freeze', required=True)
        command.add_argument('--out', required=True)
        if name == 'verify-report':
            command.add_argument('--binary')
            command.add_argument('--baseline-session')
        else:
            command.add_argument('--allow-inference', action='store_true')
        if name == 'worker':
            command.add_argument('--variant', choices=h.VARIANTS, required=True)
            command.add_argument('--tag', required=True)
            command.add_argument('--cold-case', type=int)
    args = parser.parse_args()
    if args.command == 'verify':
        verify_protocol()
    elif args.command == 'prepare':
        prepare(args)
    elif args.command == 'run':
        run(args)
    elif args.command == 'worker':
        worker(args)
    else:
        verify_report(args.freeze, args.out, binary=args.binary, baseline_session=args.baseline_session)
        print('Model-free selective hybrid replay verified.')


if __name__ == '__main__':
    main()
