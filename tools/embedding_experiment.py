#!/usr/bin/env python3
"""Pinned CPU EmbeddingGemma 2 retrieval experiment; no Find integration or Ask data."""
import argparse
import hashlib
import json
import math
import gzip
import importlib.metadata
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time
import urllib.request

import retrieval as r

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'benchmarks/embeddinggemma/manifest.json'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def verify():
    manifest = r.read(MANIFEST)
    r.verify()
    r.require(manifest['status'] == 'preregistered', 'Unexpected experiment status')
    for path, expected in manifest['sha256'].items():
        r.require(digest(ROOT / path) == expected, f'Embedding prerequisite changed: {path}')
    upstream = r.read(ROOT / manifest['upstream'])
    r.require(upstream['id'] == manifest['model'] == 'google/embeddinggemma-2', 'Wrong model generation')
    r.require(upstream['sha'] == manifest['revision'] == '914f7f89142e33e77833254d9c9b90c3cef7303b',
              'Wrong upstream revision')
    return manifest, upstream


def assets(directory):
    """Check upstream Git blobs and LFS content, streaming the large weight files."""
    _, upstream = verify()
    failures = []
    checked = {}
    for entry in upstream['siblings']:
        name = entry['rfilename']
        if name in {'.gitattributes', 'notebook.ipynb'}:
            continue
        path = Path(directory) / name
        if not path.is_file():
            failures.append(dict(file=name, reason='missing'))
            continue
        if path.stat().st_size != entry['size']:
            failures.append(dict(file=name, reason='size mismatch'))
            continue
        sha256 = digest(path)
        if 'lfs' in entry:
            valid = sha256 == entry['lfs']['sha256']
        else:
            blob = hashlib.sha1(f"blob {entry['size']}\0".encode())
            with path.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    blob.update(chunk)
            valid = blob.hexdigest() == entry['blobId']
        if valid:
            checked[name] = sha256
        else:
            failures.append(dict(file=name, reason='upstream content mismatch'))
    return dict(model=upstream['id'], revision=upstream['sha'], sha256=checked, failures=failures,
                valid=not failures)


def parity_inputs():
    manifest, _ = verify()
    fixtures = r.read(ROOT / manifest['parity_fixtures'])
    return [dict(id=case['id'], kind=case['kind'],
                 input=manifest['prefixes'][case['kind']] + case['text'] * case.get('repeat', 1))
            for case in fixtures['cases']]


def compare_parity(reference, runtime):
    """Compare separately produced reference/runtime traces; never fabricate a reference."""
    manifest, _ = verify()
    for trace in [reference, runtime]:
        r.require(trace['model'] == manifest['model'] and trace['revision'] == manifest['revision'],
                  'Parity model/revision mismatch')
        r.require(len(trace['cases']) == len(parity_inputs()), 'Missing parity cases')
    rows = []
    for fixture, left, right in zip(parity_inputs(), reference['cases'], runtime['cases']):
        for case in [left, right]:
            r.require(case['id'] == fixture['id'], 'Parity case order/identity mismatch')
            r.require(case['input_sha256'] == hashlib.sha256(fixture['input'].encode()).hexdigest(),
                      'Parity prefix/text mismatch')
            tokens = case['token_ids']
            r.require(tokens and len(tokens) <= manifest['max_tokens'] and
                      all(type(t) is int and t >= 0 for t in tokens), 'Invalid token trace')
            r.require(type(case['untruncated_tokens']) is int and
                      case['untruncated_tokens'] >= len(tokens), 'Invalid truncation trace')
            r.require(len(tokens) == min(case['untruncated_tokens'], manifest['max_tokens']),
                      'Truncation length mismatch')
            if fixture['id'].startswith('truncation'):
                r.require(case['untruncated_tokens'] > manifest['max_tokens'], 'Truncation not exercised')
            vector = case['vector']
            r.require(len(vector) == manifest['dimensions'] and
                      all(type(v) in (int, float) and math.isfinite(v) for v in vector),
                      'Invalid embedding vector')
            r.require(abs(math.sqrt(sum(v * v for v in vector)) - 1) <= 1e-5, 'Vector not L2 normalized')
        r.require(left['token_ids'] == right['token_ids'] and
                  left['untruncated_tokens'] == right['untruncated_tokens'], 'Tokenizer parity failed')
        error = max(abs(a - b) for a, b in zip(left['vector'], right['vector']))
        cosine = sum(a * b for a, b in zip(left['vector'], right['vector'])) / math.sqrt(
            sum(a*a for a in left['vector']) * sum(b*b for b in right['vector']))
        r.require(error <= 1e-5 and cosine >= 1 - 1e-6, 'Vector parity failed')
        rows.append(dict(id=fixture['id'], max_absolute_error=error, cosine=cosine))
    return rows


def export_corpus(binary, corpus, role=None):
    """The Rust builder authorizes scope before any text reaches this process."""
    r.require(role in {None, 'entity', 'predicate', 'class'}, 'Invalid role')
    paths = [str(ROOT / corpus[k]) if k != 'format' else corpus[k]
             for k in ['rdf', 'format', 'policy', 'scope', 'config']]
    proc = subprocess.run([str(Path(binary).resolve()), 'index-build', *paths],
                          cwd=ROOT, capture_output=True, text=True, timeout=180)
    r.require(proc.returncode == 0, f'Authorized index build failed: {proc.stderr.strip()}')
    index = json.loads(proc.stdout)
    scope = r.read(ROOT / corpus['scope'])
    r.require(set(index['graphs']) == set(index['manifest']['scope']) == set(scope), 'Scope mismatch')
    rows = []
    for graph, data in sorted(index['graphs'].items()):
        for iri, document in sorted(data['documents'].items()):
            if role is None or role in document['roles']:
                rows.append(dict(graph=graph, iri=iri, document=document,
                                 input='title: none | text: ' + '\n'.join(
                                     [iri] + [t['value']['text'] for t in document['texts']])))
    r.require(len(rows) <= 10000, 'Pilot exceeds 10000 graph-qualified resources')
    return dict(manifest=index['manifest'], role=role, documents=rows)


def save_gzip(path, value):
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False)


def load_gzip(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def cpu_runtime():
    spec, _ = verify()
    threads = str(spec['runtime']['threads'])
    os.environ.update(OMP_NUM_THREADS=threads, OPENBLAS_NUM_THREADS=threads,
                      TOKENIZERS_PARALLELISM='false', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    import torch
    torch.set_num_threads(int(threads))
    torch.set_num_interop_threads(1)
    torch.manual_seed(38)
    torch.use_deterministic_algorithms(True)
    packages = {}
    for dist in importlib.metadata.distributions():
        record = dist.read_text('RECORD') or ''
        packages[dist.metadata['Name']] = dict(version=dist.version,
            record_sha256=hashlib.sha256(record.encode()).hexdigest())
    return torch, dict(python=sys.version, platform=platform.platform(), machine=platform.machine(),
                      torch_build=torch.__config__.show(), torch_git=torch.version.git_version,
                      threads=torch.get_num_threads(), interop_threads=torch.get_num_interop_threads(),
                      packages=packages)


def prepare(args):
    spec, _ = verify()
    checked = assets(args.model_dir)
    r.require(checked['valid'], 'Missing or modified upstream assets: ' + str(checked['failures']))
    _, runtime = cpu_runtime()
    from transformers import AutoProcessor
    # Resolve the official processor's optional dependencies before freezing/inference.
    AutoProcessor.from_pretrained(args.model_dir, local_files_only=True, trust_remote_code=False)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    baseline, _ = r.verify()
    corpora = dict(baseline['corpora'])
    (out / 'scale').mkdir()
    corpora['scale'] = r.scale_corpus(out / 'scale')
    r.require(digest(corpora['scale']['rdf']) == baseline['scale']['rdf_sha256'], 'Scale corpus changed')
    corpus_files = {}
    for name, corpus in corpora.items():
        payload = export_corpus(args.binary, corpus)
        save_gzip(out / f'{name}-documents.json.gz', payload)
        corpus_files[name] = dict(inputs=corpus, documents=len(payload['documents']),
            input_sha256={k: digest(ROOT / corpus[k]) for k in ['rdf', 'policy', 'scope', 'config']},
            export_sha256=digest(out / f'{name}-documents.json.gz'))
    legal = {}
    for name in ['APACHE-2.0.txt', 'gemma-terms.html', 'prohibited-use-policy.html']:
        source = Path(args.legal_dir) / name
        shutil.copyfile(source, out / name)
        legal[name] = digest(out / name)
    files = ['tools/embedding_experiment.py', 'tools/retrieval.py', 'tools/embedding-requirements.txt',
             'benchmarks/embeddinggemma/manifest.json', 'Cargo.lock', 'rust-toolchain.toml']
    files.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT/'crates').rglob('*.rs')))
    freeze = dict(version=1, spec_sha256=digest(MANIFEST), model=checked,
        model_dir=str(Path(args.model_dir).resolve()), binary=str(Path(args.binary).resolve()),
        binary_sha256=digest(args.binary), runtime=runtime, cpu_description=args.cpu_description,
        scheduling='Host scheduler; no CPU affinity or isolated CPU quota on macOS',
        code_sha256={p: digest(ROOT / p) for p in files}, legal_sha256=legal,
        corpora=corpus_files, cold=args.cold, warm=args.warm,
        frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    r.write(out / 'freeze.json', freeze)
    print('Frozen before inference: ' + digest(out / 'freeze.json'), flush=True)


class Encoder:
    """Direct Transformers CPU path, checked against official Sentence Transformers."""
    def __init__(self, directory, torch, spec):
        started = time.perf_counter()
        from transformers import AutoConfig, AutoModel, AutoTokenizer
        self.torch, self.spec = torch, spec
        self.tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
        config = AutoConfig.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
        config.vision_config = config.audio_config = None
        self.model = AutoModel.from_pretrained(directory, config=config, dtype=torch.float32,
            attn_implementation='eager', local_files_only=True, trust_remote_code=False).eval().to('cpu')
        self.load_ms = (time.perf_counter() - started) * 1000

    def encode(self, texts):
        tokens = self.tokenizer(texts, padding=True, truncation=True,
                                max_length=self.spec['max_tokens'], return_tensors='pt')
        with self.torch.inference_mode():
            hidden = self.model(**tokens).last_hidden_state
            mask = tokens['attention_mask'].unsqueeze(-1)
            vectors = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
            vectors = self.torch.nn.functional.normalize(vectors, p=2, dim=1)
        r.require(vectors.shape == (len(texts), self.spec['dimensions']) and
                  bool(self.torch.isfinite(vectors).all()), 'Invalid runtime vectors')
        return vectors


def trace(encoder, inputs, vectors, spec):
    rows = []
    for fixture, vector in zip(inputs, vectors):
        text = fixture['input']
        full = encoder.tokenizer(text, truncation=False)['input_ids']
        tokens = encoder.tokenizer(text, truncation=True, max_length=spec['max_tokens'])['input_ids']
        rows.append(dict(id=fixture['id'], input_sha256=hashlib.sha256(text.encode()).hexdigest(),
                         untruncated_tokens=len(full), token_ids=tokens, vector=vector.tolist()))
    return dict(model=spec['model'], revision=spec['revision'], cases=rows)


def parity_run(directory, torch, spec, out):
    from sentence_transformers import SentenceTransformer
    import gc
    inputs = parity_inputs()
    reference = SentenceTransformer(directory, device='cpu', local_files_only=True, trust_remote_code=False,
        config_kwargs={'vision_config': None, 'audio_config': None},
        model_kwargs={'dtype': torch.float32, 'attn_implementation': 'eager'})
    reference.max_seq_length = spec['max_tokens']
    vectors = reference.encode([f['input'] for f in inputs], batch_size=1, prompt='',
                               normalize_embeddings=True, convert_to_tensor=True, show_progress_bar=False)
    # Use the actual reference tokenizer, rather than copying runtime token IDs.
    ref = trace(reference, inputs, vectors, spec)
    r.write(out / 'parity-reference.json', ref)
    del reference, vectors
    gc.collect()
    runtime = Encoder(directory, torch, spec)
    vectors = torch.cat([runtime.encode([f['input']]) for f in inputs])
    actual = trace(runtime, inputs, vectors, spec)
    r.write(out / 'parity-runtime.json', actual)
    r.write(out / 'parity.json', compare_parity(ref, actual))
    return runtime


def dense_rank(documents, vectors, query_vector, role, limit=50):
    # Role filtering precedes similarity, candidate counts and returned provenance.
    selected = [i for i, d in enumerate(documents) if role is None or role in d['document']['roles']]
    scores = (vectors[selected] @ query_vector).tolist() if selected else []
    ranked = sorted(zip(selected, scores), key=lambda pair: (-pair[1], documents[pair[0]]['iri'],
                                                            documents[pair[0]]['graph']))
    return [dict(graph=documents[i]['graph'], iri=documents[i]['iri'], score=score)
            for i, score in ranked[:limit]]


def fuse(lexical, semantic):
    scores = {}
    for hits in [lexical, semantic]:
        r.require(len({(h['graph'], h['iri']) for h in hits}) == len(hits), 'Duplicate fusion ID')
        for rank, hit in enumerate(hits, 1):
            key = hit['graph'], hit['iri']
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    return [dict(graph=key[0], iri=key[1], score=value)
            for key, value in sorted(scores.items(), key=lambda pair: (-pair[1], pair[0][1], pair[0][0]))[:50]]


def paired(rows, system):
    base = {r['id']: r for r in rows if r['system'] == 'bm25'}
    selected = [r for r in rows if r['system'] == system and r['status'] == 'relevant']
    groups = dict(overall=selected)
    for lang in ['no', 'en']:
        groups['language/' + lang] = [r for r in selected if r['language'] == lang]
    for family in sorted(r.FAMILIES - {'ambiguous', 'no_match'}):
        groups['family/' + family] = [r for r in selected if r['family'] == family]
    return {key: {metric: r.interval([row['metrics'][metric] - base[row['id']]['metrics'][metric]
                                     for row in group])
                  for metric in ['recall@1', 'recall@5', 'recall@10', 'recall@50', 'mrr@10']}
            for key, group in groups.items()}


def invoke(binary, command, corpus, request):
    paths = [str(ROOT / corpus[k]) if k != 'format' else corpus[k]
             for k in ['rdf', 'format', 'policy', 'scope', 'config']]
    proc = subprocess.run([binary, command, *paths, str(request)], cwd=ROOT,
                          capture_output=True, text=True, timeout=180)
    r.require(proc.returncode == 0, f'BM25 failed: {proc.stderr}')
    return json.loads(proc.stdout)


def query(encoder, payload, vectors, query_text, role):
    vector = encoder.encode([encoder.spec['prefixes']['query'] + query_text])[0]
    return dense_rank(payload['documents'], vectors, vector, role)


def run(args):
    spec, _ = verify()
    frozen = Path(args.freeze).resolve()
    freeze = r.read(frozen / 'freeze.json')
    torch, identity = cpu_runtime()
    r.require(identity == freeze['runtime'], 'CPU runtime/build changed after freeze')
    r.require(freeze['spec_sha256'] == digest(MANIFEST), 'Experiment spec changed')
    for path, expected in freeze['code_sha256'].items():
        r.require(digest(ROOT / path) == expected, 'Code changed after freeze: ' + path)
    directory = args.model_dir or freeze['model_dir']
    binary = str(Path(args.binary or freeze['binary']).resolve())
    r.require(assets(directory) == freeze['model'] and digest(binary) == freeze['binary_sha256'], 'Assets/binary changed')
    for name, corpus in freeze['corpora'].items():
        r.require(digest(frozen / f'{name}-documents.json.gz') == corpus['export_sha256'], 'Export changed')
        for key, expected in corpus['input_sha256'].items():
            r.require(digest(ROOT / corpus['inputs'][key]) == expected, 'Corpus/scope changed')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    r.write(out / 'run.json', dict(freeze_sha256=digest(frozen / 'freeze.json'), started_utc=time.strftime(
        '%Y-%m-%dT%H:%M:%SZ', time.gmtime()), status='running'))
    failures = []
    raw = gzip.open(out / 'ranks.jsonl.gz', 'wt', encoding='utf-8')
    try:
        encoder = parity_run(directory, torch, spec, out)
        baseline, cases = r.verify()
        indexes, builds = {}, {}
        for name, corpus in freeze['corpora'].items():
            print('Embedding corpus ' + name, flush=True)
            payload = load_gzip(frozen / f'{name}-documents.json.gz')
            texts = [d['input'] for d in payload['documents']]
            start = time.perf_counter()
            vectors = []
            for i in range(0, len(texts), spec['document_batch_size']):
                vectors.append(encoder.encode(texts[i:i + spec['document_batch_size']]))
                if i % 1000 == 0:
                    print(f'{name}: {i}/{len(texts)}', flush=True)
            matrix = torch.cat(vectors) if vectors else torch.empty((0, spec['dimensions']))
            builds[name] = dict(embedding_build_ms=(time.perf_counter() - start) * 1000,
                documents=len(texts), vector_bytes=matrix.numel() * matrix.element_size())
            torch.save(matrix, out / f'{name}-vectors.pt')
            builds[name]['vector_disk_bytes'] = (out / f'{name}-vectors.pt').stat().st_size
            indexes[name] = payload, matrix
        rows = []
        for split in ['development', 'evaluation']:
            formulations = {q['id']: q['query'] for q in r.read(ROOT / baseline[split])['queries']}
            for name, corpus in baseline['corpora'].items():
                selected = [c for c in cases if c['corpus'] == name]
                if not selected:
                    continue
                requests = [dict(query=formulations[c['id']], role=c['role'],
                                 scope=r.read(ROOT / corpus['scope']), limit=50) for c in selected]
                path = out / f'{split}-{name}-requests.json'
                r.write(path, requests)
                batch = invoke(binary, 'find-batch', corpus, path)
                r.require(len(batch['results']) == len(selected), 'Lost BM25 cases')
                for case, request, response in zip(selected, requests, batch['results']):
                    lexical = response.get('result', {}).get('hits', [])
                    lexical_error, semantic_error = response.get('error'), None
                    try:
                        semantic = query(encoder, *indexes[name], request['query'], case['role'])
                    except Exception as exc:
                        semantic, semantic_error = [], str(exc)
                    for system, hits in [('bm25', lexical), ('embedding', semantic), ('fusion', fuse(lexical, semantic))]:
                        error = (lexical_error if system == 'bm25' else semantic_error if system == 'embedding'
                                 else lexical_error or semantic_error)
                        row = dict(case, split=split, system=system, query=request['query'],
                            snapshot_id=indexes[name][0]['manifest']['snapshot_id'],
                            result_status=response.get('result', {}).get('status') if system == 'bm25' else 'ranked',
                            hits=[{k: h[k] for k in ['graph', 'iri', 'score']} for h in hits])
                        if error:
                            row['error'] = error
                            # Failed systems retain zero-score denominators, including fusion.
                            row['hits'] = []
                            failures.append(dict(split=split, id=case['id'], system=system, error=error))
                        row['metrics'] = r.score(case, row)
                        rows.append(row)
                        raw.write(json.dumps(row, ensure_ascii=False) + '\n'); raw.flush()
        performance = measure(encoder, binary, freeze, indexes, out, raw)
        builds['runtime'] = dict(load_ms=encoder.load_ms, loaded_parameters=sum(p.numel() for p in encoder.model.parameters()),
                                checkpoint_disk_bytes=sum((Path(directory)/p).stat().st_size for p in freeze['model']['sha256']))
        summary = summarize(rows, performance, builds)
        r.write(out / 'summary.json', summary)
        r.write(out / 'run.json', dict(freeze_sha256=digest(frozen / 'freeze.json'), status='complete'))
    except Exception as exc:
        failures.append(dict(stage='experiment', error=str(exc)))
        raise
    finally:
        raw.close()
        r.write(out / 'failures.json', failures)
        rss_unit = 1 if sys.platform == 'darwin' else 1024
        r.write(out / 'memory.json', dict(controller_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * rss_unit,
            child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * rss_unit,
            aggregate_upper_bound_bytes=(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss +
                                        resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * rss_unit))
        r.write(out / 'artifacts.json', {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    r.write(out / 'decision.json', decide(summary, r.read(out / 'memory.json'), failures))
    r.write(out / 'artifacts.json', {p.name: digest(p) for p in sorted(out.iterdir())
                                   if p.is_file() and p.name != 'artifacts.json'})
    return int(bool(failures))


def measure(encoder, binary, freeze, indexes, out, raw):
    performance = {}
    for name, corpus in freeze['corpora'].items():
        queries = (['Coastal station 00123', 'vannkvalitet', 'Water quality', '99997', 'urn:load:00042']
                   if name == 'scale' else ['Oslo', 'Bergen', 'Ålesund', 'population', 'nonexistentcanary'])
        requests = [dict(query=queries[i % len(queries)], role=None,
                         scope=r.read(ROOT / corpus['inputs']['scope']), limit=50) for i in range(freeze['warm'])]
        path = out / f'{name}-performance-requests.json'
        r.write(path, requests)
        start = time.perf_counter()
        batch = invoke(binary, 'find-batch', corpus['inputs'], path)
        batch_e2e = (time.perf_counter() - start) * 1000
        r.require(len(batch['results']) == len(requests) and
                  all('result' in result for result in batch['results']), 'BM25 timing failures')
        perf = dict(bm25_build_ms=batch['build_ms'], bm25_index_bytes=batch['index_bytes'],
                    bm25_batch_end_to_end_ms=batch_e2e, samples=[])
        for i, (request, response) in enumerate(zip(requests, batch['results'])):
            started = time.perf_counter()
            json.dumps(request, ensure_ascii=False)
            semantic = query(encoder, *indexes[name], request['query'], None)
            json.dumps(semantic, ensure_ascii=False)
            dense_ms = (time.perf_counter() - started) * 1000
            # A fresh lexical CLI includes import/build and IO: a conservative fusion latency bound.
            single = out / f'{name}-single-request.json'
            r.write(single, request)
            started = time.perf_counter()
            lexical = invoke(binary, 'find', corpus['inputs'], single)
            json.dumps(fuse(lexical['hits'], semantic), ensure_ascii=False)
            fusion_ms = dense_ms + (time.perf_counter() - started) * 1000
            sample = dict(iteration=i, query=request['query'], bm25_warm_ms=response['elapsed_ms'],
                          embedding_end_to_end_ms=dense_ms, fusion_end_to_end_upper_bound_ms=fusion_ms)
            perf['samples'].append(sample)
            raw.write(json.dumps(dict(split='performance', corpus=name, **sample)) + '\n'); raw.flush()
        for key in ['bm25_warm_ms', 'embedding_end_to_end_ms', 'fusion_end_to_end_upper_bound_ms']:
            values = [sample[key] for sample in perf['samples']]
            perf[key] = dict(n=len(values), p50=r.percentile(values, .5), p95=r.percentile(values, .95),
                             p99=r.percentile(values, .99))
        perf['cold_bm25_end_to_end_ms'] = []
        for _ in range(freeze['cold']):
            started = time.perf_counter()
            invoke(binary, 'find', corpus['inputs'], single)
            perf['cold_bm25_end_to_end_ms'].append((time.perf_counter() - started) * 1000)
        performance[name] = perf
    return performance


def summarize(rows, performance, builds):
    splits = {}
    for split in ['development', 'evaluation']:
        selected = [row for row in rows if row['split'] == split]
        splits[split] = dict(systems={system: r.summarize([row for row in selected if row['system'] == system])
                                     for system in ['bm25', 'embedding', 'fusion']},
                             paired_gain={system: paired(selected, system) for system in ['embedding', 'fusion']})
    return dict(splits=splits, performance=performance, builds=builds)


def decide(summary, memory, failures):
    spec, _ = verify()
    rule = spec['adoption_proposal']
    decisions = {}
    for system in ['embedding', 'fusion']:
        delta = summary['splits']['evaluation']['paired_gain'][system]
        overall = delta['overall']
        gain = (overall['recall@10']['mean'] >= rule['recall_at_10_gain'] - 1e-12 or
                overall['mrr@10']['mean'] >= rule['mrr_at_10_gain'] - 1e-12)
        languages = all(delta['language/' + lang][metric]['mean'] >= -rule['maximum_language_regression'] - 1e-12
                        for lang in ['no', 'en'] for metric in ['recall@10', 'mrr@10'])
        # Frozen uncertainty rule: a positive gain must also exclude zero in its paired interval.
        certain = any(overall[metric]['mean'] >= threshold - 1e-12 and
                      overall[metric]['descriptive_95'][0] > 0
                      for metric, threshold in [('recall@10', rule['recall_at_10_gain']),
                                                ('mrr@10', rule['mrr_at_10_gain'])])
        key = 'embedding_end_to_end_ms' if system == 'embedding' else 'fusion_end_to_end_upper_bound_ms'
        latency = all(p[key]['p95'] <= rule['warm_end_to_end_p95_ms'] for p in summary['performance'].values())
        ram = memory['aggregate_upper_bound_bytes'] <= rule['aggregate_peak_rss_bytes']
        eligible = gain and languages and certain and latency and ram and not failures
        decisions[system] = dict(gain=gain, language_non_regression=languages, positive_paired_interval=certain,
                                 latency=latency, memory=ram, no_failures=not failures,
                                 pilot_rule_pass=eligible)
    return dict(decision='candidate_for_review' if any(d['pilot_rule_pass'] for d in decisions.values()) else 'retain_bm25',
                systems=decisions, automatic_integration=False,
                interpretation='Exploratory AI judgments, correlated public formulations; not stakeholder quality or Phase 0 approval')


def verify_report(frozen, out):
    spec, _ = verify()
    freeze = r.read(frozen / 'freeze.json')
    r.require(freeze['spec_sha256'] == digest(MANIFEST), 'Report uses another spec')
    inventory = r.read(out / 'artifacts.json')
    r.require(set(inventory) == {p.name for p in out.iterdir() if p.is_file() and p.name != 'artifacts.json'},
              'Artifact inventory incomplete')
    for name, expected in inventory.items():
        r.require(digest(out / name) == expected, 'Artifact changed: ' + name)
    r.require(r.read(out / 'run.json') == dict(freeze_sha256=digest(frozen / 'freeze.json'), status='complete'),
              'Incomplete run or changed freeze')
    for name, expected in freeze['legal_sha256'].items():
        r.require(digest(frozen / name) == expected, 'License/policy changed')
    exports = {}
    for name, corpus in freeze['corpora'].items():
        path = frozen / f'{name}-documents.json.gz'
        r.require(digest(path) == corpus['export_sha256'], 'Frozen documents changed')
        exports[name] = load_gzip(path)
    parity = compare_parity(r.read(out / 'parity-reference.json'), r.read(out / 'parity-runtime.json'))
    r.require(parity == r.read(out / 'parity.json'), 'Parity summary changed')
    baseline, cases = r.verify()
    expected = {c['id']: c for c in cases}
    with gzip.open(out / 'ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
        raw = [json.loads(line) for line in stream]
    rows = [row for row in raw if row['split'] in ['development', 'evaluation']]
    summary = r.read(out / 'summary.json')
    for split in ['development', 'evaluation']:
        formulations = {q['id']: q['query'] for q in r.read(ROOT / baseline[split])['queries']}
        for system in ['bm25', 'embedding', 'fusion']:
            selected = [row for row in rows if row['split'] == split and row['system'] == system]
            r.require(len(selected) == 80 and {row['id'] for row in selected} == set(expected), 'Lost rank denominators')
            for row in selected:
                case = expected[row['id']]
                r.require(all(row[key] == case[key] for key in case), 'Changed judgment/denominator')
                r.require(row['query'] == formulations[row['id']], 'Changed formulation')
                payload = exports[case['corpus']]
                allowed = {(d['graph'], d['iri']) for d in payload['documents']
                           if case['role'] is None or case['role'] in d['document']['roles']}
                r.require(all((h['graph'], h['iri']) in allowed for h in row['hits']), 'Rank escaped scope/role')
                r.require(row['snapshot_id'] == payload['manifest']['snapshot_id'], 'Changed snapshot')
                r.require(row['metrics'] == r.score(case, row), 'Changed metrics')
    for name, perf in summary['performance'].items():
        samples = [{k: value for k, value in row.items() if k not in ['split', 'corpus']}
                   for row in raw if row['split'] == 'performance' and row['corpus'] == name]
        r.require(samples == perf['samples'] and len(samples) == freeze['warm'], 'Changed timing samples')
        for key in ['bm25_warm_ms', 'embedding_end_to_end_ms', 'fusion_end_to_end_upper_bound_ms']:
            values = [sample[key] for sample in samples]
            r.require(perf[key] == dict(n=len(values), p50=r.percentile(values,.5),
                p95=r.percentile(values,.95), p99=r.percentile(values,.99)), 'Changed timing percentiles')
    r.require(summary == summarize(rows, summary['performance'], summary['builds']), 'Summary differs from ranks')
    r.require(r.read(out / 'decision.json') == decide(summary, r.read(out / 'memory.json'), r.read(out / 'failures.json')),
              'Decision differs from evidence')
    print('Pinned inputs, parity, scope/roles, denominators, metrics, intervals, timing and decision verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify')
    download = sub.add_parser('download')
    download.add_argument('--out', required=True)
    check = sub.add_parser('assets')
    check.add_argument('directory')
    parity = sub.add_parser('parity')
    parity.add_argument('reference')
    parity.add_argument('runtime')
    export = sub.add_parser('export')
    export.add_argument('--binary', required=True)
    export.add_argument('--corpus', choices=['wikidata', 'cities', 'descriptions'], required=True)
    export.add_argument('--role', choices=['entity', 'predicate', 'class'])
    export.add_argument('--out', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--model-dir', required=True)
    prep.add_argument('--legal-dir', required=True)
    prep.add_argument('--binary', required=True)
    prep.add_argument('--out', required=True)
    prep.add_argument('--cpu-description', required=True)
    prep.add_argument('--cold', type=int, default=30)
    prep.add_argument('--warm', type=int, default=200)
    for command in ['run', 'verify-report']:
        runner = sub.add_parser(command)
        runner.add_argument('--freeze', required=True)
        runner.add_argument('--out', required=True)
        if command == 'run':
            runner.add_argument('--model-dir')
            runner.add_argument('--binary')
    args = parser.parse_args()
    manifest, _ = verify()
    if args.command == 'verify':
        print('Pinned EmbeddingGemma 2 experiment inputs verified; no inference performed.')
        return 0
    if args.command == 'download':
        _, upstream = verify()
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=False)
        for entry in upstream['siblings']:
            name = entry['rfilename']
            if name == '.gitattributes':
                continue
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(f"https://huggingface.co/{manifest['model']}/resolve/{manifest['revision']}/{name}",
                                        timeout=300) as source, target.open('xb') as stream:
                shutil.copyfileobj(source, stream)
        result = assets(out)
        r.require(result['valid'], 'Downloaded upstream content mismatch')
        return 0
    if args.command == 'prepare':
        r.require(args.cold >= 1 and 1 <= args.warm <= 1000, 'Invalid sample counts')
        prepare(args)
        return 0
    if args.command == 'run':
        return run(args)
    if args.command == 'verify-report':
        verify_report(Path(args.freeze), Path(args.out))
        return 0
    if args.command == 'assets':
        result = assets(args.directory)
        print(json.dumps(result, indent=2))
        return int(bool(result['failures']))
    if args.command == 'parity':
        print(json.dumps(compare_parity(r.read(args.reference), r.read(args.runtime)), indent=2))
        return 0
    baseline = r.read(ROOT / manifest['retrieval_manifest'])
    payload = export_corpus(args.binary, baseline['corpora'][args.corpus], args.role)
    # Exclusive creation prevents a preparation command from replacing frozen evidence.
    with Path(args.out).open('x') as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(documents=len(payload['documents']), sha256=digest(args.out))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
