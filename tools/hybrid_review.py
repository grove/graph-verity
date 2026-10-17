#!/usr/bin/env python3
"""Opt-in blinded offline review; saved ranks by default, never part of shipping Find."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import hmac
import json
import re
import resource
import sys
import secrets
import time
from pathlib import Path

import embedding_experiment as embedding
import hybrid_retrieval as hybrid
import local_find as local
import pilot_study as forms
import retrieval
import selective_hybrid as selective
from local_parser import Memory

ROOT = local.ROOT
KIT = ROOT / 'studies/hybrid-review-v1'
HISTORY = ROOT / 'reports/issue-53-selective-hybrid'
EXPORT = HISTORY / 'freeze/bm25-46-documents.json.gz'
ASSETS = ROOT / 'tools/hybrid_review_ui'
METHODS = ('bm25', 'selective')
CHECKS = ('exact_first', 'false_candidates', 'graph_suitable', 'direction_suitable',
          'ambiguity_clear', 'paraphrase_helpful')
OPTIONS = {'yes', 'no', 'not_applicable', 'uncertain'}
require = forms.require


def write_private(path, value):
    # Atomic replacement; a failed write never destroys the previous judgments.
    path = forms.private_path(Path(path))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.tmp-' + secrets.token_hex(8))
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            temporary.chmod(0o600)
            json.dump(value, stream, ensure_ascii=True, allow_nan=False, indent=2)
            stream.write('\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def frozen_files():
    paths = ['studies/hybrid-review-v1/README.md', 'tools/local_find_browser.mjs', 'tools/hybrid_review_browser.mjs', 'tools/hybrid_review.py', 'tools/test_hybrid_review.py',
             'studies/hybrid-review-v1/protocol.json', 'studies/hybrid-review-v1/tasks.json',
             'benchmarks/selective-hybrid/cases.json', 'benchmarks/selective-hybrid/protocol.json',
             'benchmarks/embeddinggemma/manifest.json', 'tools/embedding-requirements.txt',
             'data/gemet/snapshot.nq', 'data/gemet/discovery.json', 'data/gemet/policy.json',
             'data/gemet/scope.json', 'data/gemet/manifest.json', 'tools/local_find.py',
             'tools/selective_hybrid.py', 'tools/hybrid_retrieval.py', 'tools/embedding_experiment.py',
             'tools/pilot_study.py', 'tools/retrieval.py',
             'reports/issue-53-selective-hybrid/freeze/freeze.json',
             'reports/issue-53-selective-hybrid/freeze/bm25-46-documents.json.gz',
             'reports/issue-53-selective-hybrid/run/bm25-46-resident-ranks.jsonl.gz',
             'reports/issue-53-selective-hybrid/run/bm25-46-vectors.f32.gz',
             'tools/local_parser.py']
    paths += [str(p.relative_to(ROOT)) for p in sorted(ASSETS.iterdir())]
    return {p: forms.sha(ROOT / p) for p in paths}


def verify():
    frozen = forms.load(KIT / 'freeze.json')
    require(frozen['files'] == frozen_files(), 'Review kit changed; preregister a new version')
    protocol, tasks = forms.load(KIT / 'protocol.json'), forms.load(KIT / 'tasks.json')
    old = retrieval.read(ROOT / 'benchmarks/selective-hybrid/cases.json')
    exposed = {x['iri'] for c in old for x in c['relevant']}
    queries = {c['query'].casefold() for c in old}
    source = set((ROOT / 'data/gemet/snapshot.nq').read_text().splitlines())
    require(len({t['id'] for t in tasks}) == len(tasks) and tasks, 'Duplicate/empty tasks')
    for task in tasks:
        require(task['query'].casefold() not in queries, 'Exposed query in new tasks')
        overlap = sorted(set(task['reference_iris']) & exposed)
        require(task['exposed_target_overlap'] == overlap and task['reviewer'] is None,
                'Incorrect lineage or fabricated reviewer')
        require(task['source_quads'] and set(task['source_quads']) <= source, 'Missing source evidence')
    require(protocol['selective'] == dict(dense_min_score=.73, lexical_head=3, limit=50),
            'Unregistered selection policy')
    return protocol, tasks, forms.sha(KIT / 'freeze.json')


def documents():
    payload = embedding.load_gzip(EXPORT)
    return payload, {(d['graph'], d['iri']): d for d in payload['documents']}


def demo_rows():
    with gzip.open(HISTORY / 'run/bm25-46-resident-ranks.jsonl.gz', 'rt') as stream:
        rows = [json.loads(line) for line in stream]
    pairs, tasks = {}, []
    for row in rows:
        if row['system'] not in METHODS or row['family'] == 'authorization':
            continue
        pairs.setdefault(row['id'], {})[row['system']] = row['hits']
        if row['system'] == 'bm25':
            tasks.append({k: row[k] for k in ('id', 'query', 'language', 'role', 'family')})
    return tasks, pairs


def saved_rows(path, protocol_id, tasks, payload):
    saved = json.loads(local.read(path, 16 * 1024 * 1024), object_pairs_hook=forms.unique_object,
                       parse_constant=lambda _: require(False, 'Non-finite result'))
    require(saved['protocol_id'] == protocol_id and saved['snapshot_id'] == payload['manifest']['snapshot_id'],
            'Saved results do not match frozen review')
    require(set(saved['cases']) == {t['id'] for t in tasks}, 'Missing/extra saved case')
    pairs = {}
    for task in tasks:
        record = saved['cases'][task['id']]
        request = dict(query=task['query'], role=task['role'], scope=payload['manifest']['scope'], limit=50)
        selected = selective.select(payload, request, record['lexical'], record['dense'],
                                    forms.load(KIT / 'protocol.json')['selective'])
        pairs[task['id']] = dict(bm25=record['lexical']['hits'], selective=selected['hits'])
    require(saved['capture']['kind'] == 'pinned-local-inference', 'Unapproved result origin')
    return pairs, saved['capture']


class Review:
    def __init__(self, *, demo=True, results=None, scope=None, roles=local.ROLES,
                 seed=None, kind='rehearsal', consent=False, out=None):
        self.protocol, tasks, self.protocol_id = verify()
        self.payload, self.docs = documents()
        allowed = self.payload['manifest']['scope']
        self.scope = allowed if scope is None else scope
        require(self.scope and len(set(self.scope)) == len(self.scope)
                and set(self.scope) <= set(allowed), 'Unauthorized scope')
        require(roles and len(set(roles)) == len(roles) and set(roles) <= set(local.ROLES), 'Invalid roles')
        self.roles = list(roles)
        self.demo = demo
        self.capture = None
        if demo:
            tasks, self.pairs = demo_rows()
            require(kind == 'rehearsal', 'Exposed demo cannot count as a human study')
        else:
            require(results is not None, 'New study ranks pending; use demo or capture first')
            self.pairs, self.capture = saved_rows(results, self.protocol_id, tasks, self.payload)
        require(kind in {'rehearsal', 'owner', 'independent'} and (kind == 'rehearsal' or consent),
                'Actual reviewers must consent')
        self.tasks = {t['id']: t for t in tasks if t['role'] in roles}
        require(self.tasks, 'No tasks for selected roles')
        self.seed = seed or secrets.token_hex(32)
        require(isinstance(self.seed, str) and re.fullmatch(r'[0-9a-f]{64}', self.seed), 'Invalid seed')
        self.out = out
        require(kind == 'rehearsal' or out is not None, 'Human judgments need a private output')
        if out:
            forms.private_path(out)
            require(not Path(out).exists(), 'Refusing to overwrite a review')
        self.session = dict(version=1, protocol_id=self.protocol_id, demo=demo, kind=kind,
                            reviewer='R-' + secrets.token_hex(8), consent=consent,
                            seed=self.seed, scope=self.scope, roles=self.roles, capture=self.capture,
                            records={})
        self.tab = self.pending = None
        self.visible = None
        self.expires = 0
        # Restrict graph before examining or returning any source text.
        self.quads = [q for q in (ROOT / 'data/gemet/snapshot.nq').read_text().splitlines()
                      if any(q.endswith(' <' + g + '> .') for g in self.scope)]
        self.receipt = {'protocol_id': self.protocol_id, 'snapshot_id': self.payload['manifest']['snapshot_id']}
        if out:
            write_private(out, self.session)

    def order(self, task_id):
        bit = hmac.digest(bytes.fromhex(self.seed), task_id.encode(), 'sha256')[0] & 1
        return METHODS[::(-1 if bit else 1)]

    def authorized(self, task):
        return {key: d for key, d in self.docs.items()
                if key[0] in self.scope and task['role'] in d['document']['roles']}

    def candidates(self, task_id, limit=10):
        task = self.tasks[task_id]
        allowed = self.authorized(task)
        return {method: [hit for hit in self.pairs[task_id][method]
                         if (hit['graph'], hit['iri']) in allowed][:limit] for method in METHODS}

    def source(self, graph, iri):
        key = graph, iri
        require(key in self.docs and graph in self.scope, 'Unavailable resource')
        # Subject labels and predicate usage are original graph-qualified statements.
        quads = [q for q in self.quads if q.endswith(' <' + graph + '> .')
                 and (q.startswith('<' + iri + '> ') or (' <' + iri + '> ') in q)]
        return dict(graph=graph, iri=iri, document=self.docs[key]['document'],
                    source_quads=quads[:20], witnesses_clipped=len(quads) > 20,
                    provenance=self.payload['manifest']['sources'][graph])

    def public_task(self, task):
        return {k: task[k] for k in ('id', 'query', 'language', 'role', 'family')}

    def validate(self, task_id, judgment):
        forms.fields(judgment, 'ratings offlist universe_reviewed no_match checks confidence preference excluded')
        require(judgment['excluded'] in {None, 'cannot_assess', 'technical_failure', 'withdrawn'}, 'Invalid exclusion')
        task = self.tasks[task_id]
        allowed = self.authorized(task)
        union = {(x['graph'], x['iri']) for hits in self.candidates(task_id).values() for x in hits}
        require(type(judgment['ratings']) is list, 'Candidate ratings required')
        seen = set()
        for rating in judgment['ratings']:
            forms.fields(rating, 'graph iri relevance')
            key = rating['graph'], rating['iri']
            require(key in union and key not in seen and rating['relevance'] in {'relevant', 'irrelevant', 'uncertain'},
                    'Invalid candidate judgment')
            seen.add(key)
        require(seen == union, 'Judge every displayed candidate')
        require(type(judgment['offlist']) is list, 'Invalid missing relevant resources')
        missing = set()
        for item in judgment['offlist']:
            forms.fields(item, 'graph iri')
            key = item['graph'], item['iri']
            require(key in allowed and key not in union and key not in missing, 'Invalid missing resource')
            missing.add(key)
        require(type(judgment['universe_reviewed']) is bool and type(judgment['no_match']) is bool, 'Invalid scope judgment')
        relevant = missing | {(r['graph'], r['iri']) for r in judgment['ratings'] if r['relevance'] == 'relevant'}
        if judgment['excluded'] is None:
            require(judgment['universe_reviewed'] and all(r['relevance'] != 'uncertain' for r in judgment['ratings']),
                    'Complete relevance needs catalog review; otherwise exclude')
            require(judgment['no_match'] == (not relevant), 'No-match means no relevant retrievable resource in scope')
        forms.fields(judgment['checks'], 'A B')
        forms.fields(judgment['confidence'], 'A B')
        for side in ('A', 'B'):
            forms.fields(judgment['checks'][side], ' '.join(CHECKS))
            require(all(v in OPTIONS for v in judgment['checks'][side].values()), 'Incomplete rubric')
            require(type(judgment['confidence'][side]) is int and 1 <= judgment['confidence'][side] <= 5,
                    'Confidence must be 1–5')
        require(judgment['preference'] in {'A', 'B', 'tie', 'neither', 'uncertain'}, 'Invalid preference')

    def api(self, route, request, tab=None):
        require(type(request) is dict, 'Object required')
        if route == '/api/session' and request == {}:
            self.tab = secrets.token_hex(32)
            self.expires = time.monotonic() + local.SESSION_SECONDS
            self.visible = None
            return dict(tab=self.tab, demo=self.demo, reviewer=self.session['reviewer'],
                        tasks=[self.public_task(t) for t in self.tasks.values()],
                        scope=self.scope, roles=self.roles, **self.receipt)
        require(isinstance(tab, str) and self.tab and hmac.compare_digest(tab, self.tab)
                and time.monotonic() < self.expires, 'Expired/stale tab')
        if route == '/api/pair':
            forms.fields(request, 'task_id snapshot_id scope role limit')
            task = self.tasks[request['task_id']]
            require(request['snapshot_id'] == self.receipt['snapshot_id'] and request['scope'] == self.scope
                    and request['role'] == task['role'] and type(request['limit']) is int
                    and request['limit'] in {1, 5, 10}, 'Invalid filters')
            require(task['id'] not in self.session['records'], 'Already unblinded; start a new reviewer session')
            self.visible = (task['id'], request['limit'])
            candidates = self.candidates(task['id'], request['limit'])
            lists = {side: [self.source(x['graph'], x['iri']) for x in candidates[method]]
                     for side, method in zip(('A', 'B'), self.order(task['id']))}
            catalog = [dict(graph=g, iri=i, texts=d['document']['texts'])
                       for (g, i), d in self.authorized(task).items()]
            exact_count = sum(selective.exact(d, task['query']) for d in self.authorized(task).values())
            return dict(task=self.public_task(task), lists=lists, catalog=catalog,
                        exact_identities=exact_count, ambiguous_exact=exact_count > 1,
                        limit=request['limit'], scope=self.scope, **self.receipt)
        if route == '/api/source':
            forms.fields(request, 'graph iri task_id')
            task = self.tasks[request['task_id']]
            require((request['graph'], request['iri']) in self.authorized(task), 'Unavailable resource')
            return self.source(request['graph'], request['iri'])
        if route == '/api/judge':
            forms.fields(request, 'task_id judgment')
            task_id = request['task_id']
            require(self.visible == (task_id, 10) and task_id not in self.session['records'],
                    'Review top 10 before submitting once')
            self.validate(task_id, request['judgment'])
            record = dict(judgment=request['judgment'], order=list(self.order(task_id)))
            updated = dict(self.session, records={**self.session['records'], task_id: record})
            if self.out:
                write_private(self.out, updated)
            self.session = updated
            self.visible = None
            return dict(saved=bool(self.out), labels=dict(zip(('A', 'B'), self.order(task_id))))
        raise ValueError('Unavailable route')


def summarize(sessions, review):
    ids = [s['reviewer'] for s in sessions]
    require(len(set(ids)) == len(ids), 'Duplicate reviewer; do not double count')
    groups = {kind: [s['reviewer'] for s in sessions if s['kind'] == kind]
              for kind in ('independent', 'owner', 'rehearsal')}
    paired, conflicts, excluded = [], [], []
    judgments = {}
    for session in sessions:
        require(session['protocol_id'] == review.protocol_id and session['scope'] == review.scope
                and session['roles'] == review.roles and session['demo'] == review.demo, 'Incomparable session')
        require(session['kind'] in groups and re.fullmatch(r'R-[0-9a-f]{16}', session['reviewer'])
                and (session['kind'] == 'rehearsal' or session['consent'] is True), 'Invalid actual reviewer')
        require(not session['demo'] or session['kind'] == 'rehearsal', 'Demo cannot validate study')
        require(session['capture'] == review.capture, 'Results capture changed')
        for task_id, record in session['records'].items():
            review.validate(task_id, record['judgment'])
            expected = hmac.digest(bytes.fromhex(session['seed']), task_id.encode(), 'sha256')[0] & 1
            require(record['order'] == list(METHODS[::(-1 if expected else 1)]), 'Changed blinding order')
            if record['judgment']['excluded']:
                excluded.append(dict(task_id=task_id, reviewer=session['reviewer'], reason=record['judgment']['excluded']))
            elif session['kind'] == 'independent' and not session['demo']:
                judgments.setdefault(task_id, []).append((session['reviewer'], record))
    for task_id, ratings in judgments.items():
        sets = []
        for _, record in ratings:
            judgment = record['judgment']
            sets.append({(r['graph'], r['iri']) for r in judgment['ratings'] if r['relevance'] == 'relevant'} |
                        {(r['graph'], r['iri']) for r in judgment['offlist']})
        if len(ratings) < 2 or any(value != sets[0] for value in sets):
            conflicts.append(dict(task_id=task_id, reviewers=[r for r, _ in ratings],
                                  reason='disagreement' if len(ratings) >= 2 else 'second_review_pending'))
            continue
        relevant = sets[0]
        task = review.tasks[task_id]
        row = dict(task_id=task_id, language=task['language'], family=task['family'],
                   no_match=not relevant, reviewers=[r for r, _ in ratings],
                   relevant=[dict(graph=g, iri=i) for g, i in sorted(relevant)], systems={},
                   judgments=[dict(reviewer=r, **record) for r, record in ratings])
        for method, hits in review.candidates(task_id).items():
            metrics = retrieval.score(dict(relevant=row['relevant']), dict(hits=hits)) if relevant else {}
            row['systems'][method] = dict(metrics={k: metrics[k] for k in ('recall@1', 'recall@5', 'recall@10', 'mrr@10')} if relevant else {},
                false_candidate=bool(hits) if not relevant else None,
                hits=[dict(graph=h['graph'], iri=h['iri']) for h in hits])
        row['delta'] = {m: row['systems']['selective']['metrics'][m] - row['systems']['bm25']['metrics'][m]
                        for m in row['systems']['bm25']['metrics']}
        base = review.candidates(task_id)['bm25']
        row['exact_preserved'] = not base or not selective.exact(review.docs[base[0]['graph'], base[0]['iri']], task['query']) or (
            row['systems']['bm25']['hits'][:1] == row['systems']['selective']['hits'][:1])
        paired.append(row)
    aggregates = {}
    for name, rows in {'overall': paired, **{'language/' + lang: [r for r in paired if r['language'] == lang]
                                           for lang in ('en', 'no')},
                       **{'family/' + family: [r for r in paired if r['family'] == family]
                          for family in sorted({r['family'] for r in paired})}}.items():
        aggregates[name] = dict(n=len(rows),
            delta={m: retrieval.interval([r['delta'][m] for r in rows if not r['no_match']])
                   for m in ('recall@1', 'recall@5', 'recall@10', 'mrr@10')},
            metrics={method: {m: retrieval.interval([r['systems'][method]['metrics'][m] for r in rows if not r['no_match']])
                              for m in ('recall@1', 'recall@5', 'recall@10', 'mrr@10')} for method in METHODS},
            no_match={method: retrieval.interval([float(r['systems'][method]['false_candidate']) for r in rows if r['no_match']])
                      for method in METHODS})
    decisions = []
    false_confidence = {m: [] for m in METHODS}
    preferences = {m: 0 for m in (*METHODS, 'tie', 'neither', 'uncertain')}
    rubric_disagreements = []
    for row in paired:
        for record in row['judgments']:
            judgment = record['judgment']
            order = dict(zip(('A', 'B'), record['order']))
            preference = judgment['preference']
            preferences[order.get(preference, preference)] += 1
            for side, method in order.items():
                top = row['systems'][method]['hits'][:1]
                wrong = bool(top) and top[0] not in row['relevant']
                false_confidence[method].append(float(wrong and judgment['confidence'][side] >= 4))
        normalized = [{method: record['judgment']['checks'][side]
                       for side, method in zip(('A', 'B'), record['order'])} for record in row['judgments']]
        if any(value != normalized[0] for value in normalized):
            rubric_disagreements.append(row['task_id'])
    complete = len(groups['independent']) >= 2 and len(paired) == len(review.tasks) and not review.demo
    language_coverage = all(any(r['language'] == lang and r['no_match'] == no_match for r in paired)
                            for lang in ('en', 'no') for no_match in (True, False))
    safety_keys = ('exact_first', 'graph_suitable', 'direction_suitable', 'ambiguity_clear')
    safety = [record['judgment']['checks'][side][key] for row in paired for record in row['judgments']
              for side in ('A', 'B') for key in safety_keys]
    safety_complete = bool(safety) and 'uncertain' not in safety
    checks = dict(exact_rank_one=all(r['exact_preserved'] for r in paired),
                  human_scope_direction_ambiguity=bool(safety) and all(value in {'yes', 'not_applicable'} for value in safety))
    if language_coverage:
        overall = aggregates['overall']
        checks.update(no_match_nonregression=overall['no_match']['selective']['mean'] <= overall['no_match']['bm25']['mean'],
            meaningful_gain=any(overall['delta'][m]['mean'] >= threshold and overall['delta'][m]['descriptive_95'][0] > 0
                                for m, threshold in [('recall@10', .05), ('mrr@10', .03)]),
            both_languages=all(aggregates['language/' + lang]['delta']['recall@10']['mean'] > 0 and
                              aggregates['language/' + lang]['delta']['mrr@10']['mean'] >= -.02 for lang in ('en', 'no')))
    resource_ready = (review.capture is not None and review.capture.get('kind') == 'pinned-local-inference'
                      and review.capture.get('cold_samples', 0) >= 1
                      and review.capture.get('memory', {}).get('sampling_error') is None)
    if resource_ready:
        checks.update(warm_p95=review.capture['warm']['selective']['p95'] <= 1000,
                      conservative_rss=review.capture['memory']['conservative_bound_bytes'] <= 4 * 1024**3)
    recommendation = ('go-for-further-opt-in-trial' if all(checks.values()) else 'continue BM25') if (
        complete and language_coverage and resource_ready and safety_complete) else 'defer'
    if not complete:
        decisions.append('Full independent human consensus pending')
    if not safety_complete:
        decisions.append('Human exact/scope/direction/ambiguity rubric unresolved')
    if not resource_ready:
        decisions.append('New-query comparable resource evidence pending')
    return dict(recommendation=recommendation, issue_58='open; owner review required',
                protocol_id=review.protocol_id, reviewer_ids=groups,
                counts={k: len(v) for k, v in groups.items()},
                judgment_counts={kind: sum(len(s['records']) for s in sessions if s['kind'] == kind) for kind in groups},
                paired=paired, aggregates=aggregates,
                conflicts=conflicts, rubric_disagreements=rubric_disagreements, exclusions=excluded,
                preference_counts=preferences,
                false_confidence={m: retrieval.interval(v) for m, v in false_confidence.items()},
                missing_tasks=sorted(set(review.tasks) - {r['task_id'] for r in paired}),
                checks=checks, blockers=decisions, resource_evidence=review.capture,
                automatic_promotion=False, limitations=review.protocol['limitations'])


def pinned_runtime(model_dir, session):
    protocol, _, protocol_id = verify()
    require(embedding.assets(model_dir)['sha256'] == protocol['runtime']['checkpoint_sha256'],
            'Pinned checkpoint changed')
    historical = forms.load(HISTORY / 'freeze/freeze.json')
    require(embedding.digest(session) == historical['session_sha256']['bm25-46'],
            'Use the original pinned bm25-46 resident lexical binary')
    torch, runtime = embedding.cpu_runtime()
    installed = {re.sub(r'[-_.]+', '-', k).lower(): v['version'] for k, v in runtime['packages'].items()}
    for name, version in protocol['runtime']['package_versions'].items():
        require(installed.get(re.sub(r'[-_.]+', '-', name).lower()) == version, 'Pinned runtime changed: ' + name)
    return torch, runtime, protocol_id


def prepare(args):
    _, runtime, protocol_id = pinned_runtime(args.model_dir, args.session)
    require(args.hardware.strip(), 'Declare hardware before new inference')
    require(not args.out.exists(), 'Refusing to overwrite a capture preregistration')
    write_private(args.out, dict(protocol_id=protocol_id, hardware=args.hardware,
        model_dir=str(args.model_dir.resolve()), session=str(args.session.resolve()),
        session_sha256=embedding.digest(args.session), runtime=runtime,
        frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))


def capture(args):
    require(args.allow_inference, 'New model queries require --allow-inference')
    forms.private_path(args.out)
    receipt = forms.load(forms.private_path(args.receipt))
    require(not args.out.exists(), 'Refusing to overwrite results')
    torch, runtime, protocol_id = pinned_runtime(receipt['model_dir'], receipt['session'])
    require(receipt['protocol_id'] == protocol_id and receipt['runtime'] == runtime
            and receipt['session_sha256'] == embedding.digest(receipt['session']),
            'Capture differs from preregistered hardware/runtime/binary')
    protocol, tasks, _ = verify()
    payload, docs = documents()
    documents_list = payload['documents']
    memory = Memory()
    memory.worker.start()
    session = None
    samples, records = [], {}
    start = time.perf_counter()
    try:
        encoder = embedding.Encoder(receipt['model_dir'], torch, embedding.verify()[0])
        vectors = torch.tensor(hybrid.vector_read(HISTORY / 'run/bm25-46-vectors.f32.gz', len(docs)), dtype=torch.float32)
        session = hybrid.Session(receipt['session'], protocol['manifest_to_corpus'])
        require(session.ready['manifest'] == payload['manifest'], 'Lexical representation changed')
        # One cold pass, then three resident passes; identical queries, catalog and process.
        for repetition in range(4):
            for task in tasks:
                request = dict(query=task['query'], role=task['role'], scope=payload['manifest']['scope'], limit=50)
                query_start = time.perf_counter()
                lexical = session.query(request)
                bm25_ms = (time.perf_counter() - query_start) * 1000
                vector = encoder.encode([encoder.spec['prefixes']['query'] + task['query']])[0]
                indices = [i for i, d in enumerate(documents_list) if task['role'] in d['document']['roles']]
                scores = (vectors[indices] @ vector).tolist()
                dense = [dict(graph=documents_list[i]['graph'], iri=documents_list[i]['iri'], score=score)
                         for i, score in sorted(zip(indices, scores), key=lambda p: (-p[1], documents_list[p[0]]['iri'], documents_list[p[0]]['graph']))[:50]]
                selective.select(payload, request, lexical, dense, protocol['selective'])
                selective_ms = (time.perf_counter() - query_start) * 1000
                if repetition == 0:
                    records[task['id']] = dict(lexical={k: lexical[k] for k in ('snapshot_id', 'scope', 'hits')}, dense=dense)
                    # Rehydrate metadata from the immutable authorized export during replay.
                    for hit in records[task['id']]['lexical']['hits']:
                        hit.pop('document', None)
                    if task == tasks[0]:
                        cold_ms = (time.perf_counter() - start) * 1000
                else:
                    samples.append(dict(task_id=task['id'], bm25=bm25_ms, selective=selective_ms))
    finally:
        if session:
            session.close()
        memory.done.set()
        memory.worker.join(timeout=10)
    unit = 1 if sys.platform == 'darwin' else 1024
    rss = dict(process_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit,
               lexical_child_peak_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit,
               sampled_tree_peak_bytes=memory.peak_kib * 1024, sampling_error=memory.error)
    rss['conservative_bound_bytes'] = rss['process_peak_bytes'] + rss['lexical_child_peak_bytes']
    evidence = dict(kind='pinned-local-inference', receipt_sha256=forms.sha(args.receipt), hardware=receipt['hardware'],
                    cold_first_query_ms=cold_ms, cold_samples=1,
                    cold_limit='One cold startup, not a cold p95; historical vector build reused',
                    warm={m: hybrid.percentiles([r[m] for r in samples]) for m in METHODS},
                    samples=samples, memory=rss, model_load_ms=encoder.load_ms,
                    checkpoint_bytes=sum(p.stat().st_size for p in Path(receipt['model_dir']).rglob('*') if p.is_file()),
                    reused_vectors_sha256=forms.sha(HISTORY / 'run/bm25-46-vectors.f32.gz'))
    write_private(args.out, dict(protocol_id=protocol_id, snapshot_id=payload['manifest']['snapshot_id'],
                                 cases=records, capture=evidence))


def serve(args):
    review = Review(demo=args.demo, results=args.results, scope=args.scope, roles=args.roles,
                    seed=args.seed, kind=args.kind, consent=args.consent, out=args.out)
    with local.Server(review, args.host, args.port) as server:
        server.assets = {route: ((ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ('/', 'index.html', 'text/html'), ('/app.js', 'app.js', 'text/javascript'), ('/style.css', 'style.css', 'text/css'))}
        print('Reviewer-only offline replay. Keep this URL private; stop with Ctrl-C.', flush=True)
        print(server.url, flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify')
    preregister = commands.add_parser('prepare')
    preregister.add_argument('--model-dir', type=Path, required=True)
    preregister.add_argument('--session', type=Path, required=True)
    preregister.add_argument('--hardware', required=True)
    preregister.add_argument('--out', type=Path, required=True)
    inference = commands.add_parser('capture')
    inference.add_argument('--allow-inference', action='store_true')
    inference.add_argument('--receipt', type=Path, required=True)
    inference.add_argument('--out', type=Path, required=True)
    start = commands.add_parser('serve')
    mode = start.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--results', type=Path)
    start.add_argument('--kind', choices=('rehearsal', 'owner', 'independent'), default='rehearsal')
    start.add_argument('--consent', action='store_true')
    start.add_argument('--seed')
    start.add_argument('--scope', nargs='+')
    start.add_argument('--roles', nargs='+', choices=local.ROLES, default=local.ROLES)
    start.add_argument('--out', type=Path)
    start.add_argument('--host', default='127.0.0.1')
    start.add_argument('--port', type=int, default=0)
    report = commands.add_parser('report')
    report.add_argument('--results', type=Path)
    report.add_argument('--out', type=Path, required=True)
    report.add_argument('sessions', nargs='*', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'verify':
            verify()
            print('Frozen review verified; no inference or human judgments generated.')
        elif args.command == 'prepare':
            prepare(args)
        elif args.command == 'capture':
            capture(args)
        elif args.command == 'serve':
            serve(args)
        else:
            review = Review(demo=args.results is None, results=args.results)
            write_private(args.out, summarize([forms.load(p) for p in args.sessions], review))
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print('Review unavailable: ' + str(exc))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
