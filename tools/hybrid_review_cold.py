#!/usr/bin/env python3
"""Opt-in, fresh-process first-result timings; never alter frozen review rankings."""
import argparse
import gzip
import json
import os
from pathlib import Path
import queue
import random
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import time

import hybrid_review as review

CASES = ('HR-01', 'HR-02', 'HR-09', 'HR-19', 'HR-20')
REPEATS = 3
SEED = 58
ROOT = review.ROOT
REPORT = ROOT / 'reports/issue-58-human-review'
SCRIPT = Path(__file__).resolve()


def schedule():
    rng, rows = random.Random(SEED), []
    for repetition in range(REPEATS):
        cases = list(CASES)
        rng.shuffle(cases)
        for case in cases:
            methods = list(review.METHODS)
            rng.shuffle(methods)
            rows.extend(dict(repetition=repetition, task_id=case, system=method) for method in methods)
    return rows


def code_hashes():
    return {name: review.forms.sha(ROOT / 'tools' / name) for name in (
        'hybrid_review_cold.py', 'test_hybrid_review_cold.py')}


def prepare(args):
    receipt = review.forms.load(review.forms.private_path(args.receipt))
    _, runtime, protocol_id = review.pinned_runtime(receipt['model_dir'], receipt['session'])
    review.require(receipt['protocol_id'] == protocol_id and receipt['runtime'] == runtime,
                   'Original pinned capture receipt changed')
    review.require(not args.out.exists(), 'Refusing to overwrite a measurement plan')
    plan = dict(version=1, protocol_id=protocol_id, code_sha256=code_hashes(),
        implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        receipt_path=str(review.forms.private_path(args.receipt)), receipt_sha256=review.forms.sha(args.receipt),
        saved_results_sha256=review.forms.sha(REPORT / 'saved-results.json.gz'),
        python=runtime['python'], platform=runtime['platform'], hardware=receipt['hardware'],
        schedule=schedule(), seed=SEED, repetitions=REPEATS,
        timing='Parent monotonic clock immediately before fresh Python Popen through receipt and validation of the first serialized top-10 result; teardown measured separately',
        included=['interpreter startup', 'Python imports', 'frozen input and binary verification',
                  'checkpoint verification and Torch/runtime initialization for selective',
                  'model load for selective', 'lexical index construction', 'vector load for selective',
                  'first query, serialization, IPC and parent result validation'],
        conditions='Sequential workers, no overlapping model owners; CPU-only 4/1 threads; native scheduler; process-cold with OS caches retained; no cache eviction; concurrent desktop workload uncontrolled',
        limitations=['15 observations per method across 5 exposed query probes; descriptive timing percentiles, not population estimates.',
                     'Not storage-cold, reboot-cold or shipping CLI startup; this measures the pinned research worker with input validation.',
                     'Historical document vectors reused; no document-vector rebuild or new relevance judgments.',
                     'No cold-latency promotion threshold is introduced; the original warm/RSS and human gates remain unchanged.'])
    review.write_private(args.out, plan)


def check_plan(path):
    plan = review.forms.load(review.forms.private_path(path))
    protocol, tasks, protocol_id = review.verify()
    review.require(plan['protocol_id'] == protocol_id and plan['code_sha256'] == code_hashes()
                   and plan['schedule'] == schedule() and plan['python'] == sys.version
                   and plan['saved_results_sha256'] == review.forms.sha(REPORT / 'saved-results.json.gz'),
                   'Measurement differs from the frozen plan')
    receipt_path = review.forms.private_path(Path(plan['receipt_path']))
    review.require(review.forms.sha(receipt_path) == plan['receipt_sha256'], 'Capture receipt changed')
    return plan, review.forms.load(receipt_path), protocol, {t['id']: t for t in tasks}


def worker(args):
    review.require(args.allow_inference, 'Worker requires --allow-inference')
    plan, receipt, protocol, tasks = check_plan(args.plan)
    payload, docs = review.documents()
    if args.system == 'selective':
        torch, runtime, _ = review.pinned_runtime(receipt['model_dir'], receipt['session'])
        review.require(runtime == receipt['runtime'], 'Runtime changed')
        encoder = review.embedding.Encoder(receipt['model_dir'], torch, review.embedding.verify()[0])
        vectors = torch.tensor(review.hybrid.vector_read(review.HISTORY / 'run/bm25-46-vectors.f32.gz', len(docs)), dtype=torch.float32)
    else:
        review.require(review.embedding.digest(receipt['session']) == receipt['session_sha256'], 'Lexical binary changed')
    session = review.hybrid.Session(receipt['session'], protocol['manifest_to_corpus'])
    try:
        review.require(session.ready['manifest'] == payload['manifest'], 'Index representation changed')
        task = tasks[args.task_id]
        request = dict(query=task['query'], role=task['role'], scope=payload['manifest']['scope'], limit=50)
        lexical = session.query(request)
        hits = lexical['hits']
        if args.system == 'selective':
            vector = encoder.encode([encoder.spec['prefixes']['query'] + task['query']])[0]
            documents = payload['documents']
            indices = [i for i, d in enumerate(documents) if task['role'] in d['document']['roles']]
            scores = (vectors[indices] @ vector).tolist()
            dense = [dict(graph=documents[i]['graph'], iri=documents[i]['iri'], score=score)
                     for i, score in sorted(zip(indices, scores), key=lambda p: (-p[1], documents[p[0]]['iri'], documents[p[0]]['graph']))[:50]]
            hits = review.selective.select(payload, request, lexical, dense, protocol['selective'])['hits']
        result = dict(snapshot_id=payload['manifest']['snapshot_id'],
                      hits=[dict(graph=h['graph'], iri=h['iri']) for h in hits[:10]])
        unit = 1 if sys.platform == 'darwin' else 1024
        print(json.dumps(dict(result=result, worker_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit)), flush=True)
    finally:
        session.close()


def measure(command, expected, timeout=120):
    """Time the actual parent-observed result; exclude subsequent child teardown."""
    received = queue.Queue(maxsize=1)
    with tempfile.TemporaryFile() as errors:
        start = time.monotonic_ns()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True, start_new_session=True, cwd=ROOT)
        reader = threading.Thread(target=lambda: received.put(process.stdout.readline(review.local.MAX_RESPONSE + 1)), daemon=True)
        reader.start()
        try:
            line = received.get(timeout=timeout)
            review.require(len(line.encode()) <= review.local.MAX_RESPONSE, 'Worker output limit')
            value = json.loads(line)
            review.forms.fields(value, 'result worker_peak_bytes')
            review.require(value['result'] == expected and type(value['worker_peak_bytes']) is int
                           and value['worker_peak_bytes'] > 0, 'Worker result does not match saved authorized ranks')
            first_result_ms = (time.monotonic_ns() - start) / 1e6
            review.require(process.wait(timeout=30) == 0, 'Worker failed after result')
            total_ms = (time.monotonic_ns() - start) / 1e6
            return dict(first_result_ms=first_result_ms, process_exit_ms=total_ms,
                        worker_peak_bytes=value['worker_peak_bytes'])
        finally:
            # Each worker has its own process group, including the nested lexical child.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            reader.join(timeout=5)
            process.stdout.close()


def run(args):
    review.require(args.allow_inference, 'Measurement requires --allow-inference')
    plan, receipt, protocol, tasks = check_plan(args.plan)
    review.forms.private_path(args.out)
    review.require(not args.out.exists(), 'Refusing to overwrite measurement results')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'saved.json'
        with gzip.open(REPORT / 'saved-results.json.gz', 'rb') as stream:
            path.write_bytes(stream.read(review.local.MAX_RESPONSE + 1))
        study = review.Review(demo=False, results=path)
    samples = []
    try:
        for item in plan['schedule']:
            expected = dict(snapshot_id=protocol['manifest']['snapshot_id'], hits=[dict(graph=h['graph'], iri=h['iri'])
                for h in study.candidates(item['task_id'])[item['system']]])
            measured = measure([sys.executable, str(SCRIPT), 'worker', '--allow-inference', '--plan', str(args.plan.resolve()),
                                '--system', item['system'], '--task-id', item['task_id']], expected)
            samples.append(dict(item, **measured))
            print(f"{len(samples)}/{len(plan['schedule'])}: {item['system']} {item['task_id']}", flush=True)
    except Exception:
        review.write_private(args.out, dict(status='failed', plan_sha256=review.forms.sha(args.plan), samples=samples))
        raise
    summary = {method: {metric: review.hybrid.percentiles([s[metric] for s in samples if s['system'] == method])
                        for metric in ('first_result_ms', 'process_exit_ms')} for method in review.METHODS}
    review.write_private(args.out, dict(status='complete', plan_sha256=review.forms.sha(args.plan), protocol_id=plan['protocol_id'],
        samples=samples, summary=summary, all_saved_ranks_preserved=True, human_reviewers=0, human_judgments=0,
        recommendation='defer', limitations=plan['limitations']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--receipt', type=Path, required=True)
    prepare_parser.add_argument('--out', type=Path, required=True)
    for name in ('run', 'worker'):
        command = commands.add_parser(name)
        command.add_argument('--allow-inference', action='store_true')
        command.add_argument('--plan', type=Path, required=True)
        if name == 'run':
            command.add_argument('--out', type=Path, required=True)
        else:
            command.add_argument('--system', choices=review.METHODS, required=True)
            command.add_argument('--task-id', choices=CASES, required=True)
    args = parser.parse_args()
    try:
        {'prepare': prepare, 'run': run, 'worker': worker}[args.command](args)
    except (OSError, ValueError, KeyError, TypeError, queue.Empty, subprocess.SubprocessError) as error:
        print('Cold-start measurement failed: ' + type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
