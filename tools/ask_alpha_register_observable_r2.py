"""Append-only model-free registration and exact equivalence proof for observable r2."""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

import ask_alpha_trial_observable_r2 as t

OLD_REG_SHA = '55af85f8f5c15e45b46653d78e6e92cfe5c03a84fabfcf75be622e63c8386464'
OLD_ARCHIVE_SHA = '4c094d907b8debd770a0c4c9d564cc339deb91302c166ed90164f2ad34a3998a'
SOURCES = ['tools/ask_alpha_trial_observable_r2.py', 'tools/ask_alpha_register_observable_r2.py',
           'tools/test_ask_alpha_observable_r2.py']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_files(path):
    with tarfile.open(path) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}


def baseline():
    t.require(t.b.sha(t.original.REG) == OLD_REG_SHA and t.b.sha(t.original.ARCHIVE) == OLD_ARCHIVE_SHA,
              'Original registration/archive drift')
    files = archive_files(t.original.ARCHIVE)
    t.require({name: sha(raw) for name, raw in files.items() if name != 'checksums.json'} == json.loads(files['checksums.json']),
              'Original archive manifest drift')
    frozen = json.loads(files['freeze.json'])
    for name, digest in frozen['inputs'].items():
        t.require(t.b.sha(t.ROOT/name) == digest, 'Original source drift: '+name)
    t.require(t.b.sha(t.ROOT/'target/debug/verity') == frozen['binary_sha256'], 'Original Rust binary drift')
    return files, frozen


def serialized(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


def payload(revision):
    files, frozen = baseline()
    # Copy all model-visible and scoring bytes. Never regenerate or repair their content.
    pins = dict(frozen['inputs'], **{name: t.b.sha(t.ROOT/name) for name in SOURCES})
    t.n.committed(pins, revision)
    frozen.update(version=t.VERSION, source_commit=revision, inputs=pins)
    files['freeze.json'] = serialized(frozen)
    files['checksums.json'] = serialized({name: sha(raw) for name, raw in sorted(files.items()) if name != 'checksums.json'})
    return files


def archive_bytes(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, filename='', mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for name, raw in sorted(files.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(raw), 0o644
                archive.addfile(info, io.BytesIO(raw))
    return buffer.getvalue()


def comparison():
    old_files, old = baseline()
    new_files = archive_files(t.ARCHIVE)
    new = json.loads(new_files['freeze.json'])
    old_reg, new_reg = t.b.read(t.original.REG), t.b.read(t.REG)
    t.require(set(old_files) == set(new_files), 'Changed archive membership')
    differences = [name for name in old_files if old_files[name] != new_files[name]]
    t.require(sorted(differences) == ['checksums.json', 'freeze.json'], 'Semantic payload mismatch: '+repr(differences))
    t.require({k: v for k, v in old.items() if k not in ['version', 'source_commit', 'inputs']} ==
              {k: v for k, v in new.items() if k not in ['version', 'source_commit', 'inputs']}, 'Changed runtime/resource/preview contract')
    t.require(new['inputs'] == dict(old['inputs'], **{name: t.b.sha(t.ROOT/name) for name in SOURCES}), 'Changed original inputs')
    t.require(new_reg == dict(old_reg, version=t.VERSION, archive_sha256=t.b.sha(t.ARCHIVE),
        checksums_sha256=sha(new_files['checksums.json']), source_commit=new['source_commit'], command=t.COMMAND,
        output=str(t.OUTPUT.relative_to(t.ROOT)), ledger=str(t.LEDGER.relative_to(t.ROOT)),
        predecessor_registration_sha256=OLD_REG_SHA,
        observability=dict(journal=str(t.JOURNAL.relative_to(t.ROOT)), diagnostics=str(t.DIAGNOSTICS.relative_to(t.ROOT)))),
        'Unexpected registration change')
    schedule = json.loads(old_files['schedule.json'])
    tokens = json.loads(old_files['token-counts.json'])['models']['qwen35']['rows']
    t.require(len(schedule) == len(tokens) == 64, 'Schedule mismatch')
    requests = []
    languages = Counter()
    for request, token in zip(schedule, tokens):
        key = request['id']
        t.require(key == token['name'], 'Token order mismatch')
        context = json.loads(old_files['contexts/'+key+'.json'])
        if request['kind'] == 'semantic':
            languages[context['language']] += 1
        for variant in ['original', 'columnar']:
            row = token[variant]
            t.require(sha(row['prompt'].encode()) == row['prompt_sha256'] and
                      sha(json.dumps(row['tokens'], separators=(',', ':')).encode()) == row['tokens_sha256'] and
                      len(row['tokens']) == row['input_tokens'], 'Prompt/token integrity failure')
        requests.append(dict(**request, files_sha256={name: sha(old_files[name]) for name in
            ['contexts/'+key+'.json', 'messages/'+key+'.json', 'grammars/'+key+'.gbnf']},
            prompt_sha256=token['columnar']['prompt_sha256'], tokens_sha256=token['columnar']['tokens_sha256'],
            input_tokens=token['columnar']['input_tokens'], total_required=token['columnar']['total_required']))
    t.require(languages == dict(nb=30, en=30), 'Question language/count mismatch')
    rebuilt = archive_bytes(payload(new['source_commit']))
    t.require(rebuilt == t.ARCHIVE.read_bytes(), 'Non-deterministic freeze reproduction')
    changed_reg = {k: dict(old=old_reg.get(k), new=new_reg.get(k)) for k in sorted(set(old_reg) | set(new_reg)) if old_reg.get(k) != new_reg.get(k)}
    return dict(version='ask-alpha-observable-equivalence-v1', exact_semantic_equivalence=True,
        decision='INCONCLUSIVE_REVISE', original_registration_sha256=OLD_REG_SHA,
        successor_registration_sha256=t.b.sha(t.REG), original_archive_sha256=OLD_ARCHIVE_SHA,
        successor_archive_sha256=t.b.sha(t.ARCHIVE), source_commit=new['source_commit'],
        deterministic_archive_reproduction=True, scheduled_requests=64, semantic_cases=60, languages=dict(languages),
        equal_payload_sha256={name: sha(raw) for name, raw in sorted(old_files.items()) if name not in differences},
        equal_original_source_sha256=old['inputs'], instrumentation_source_sha256={name: new['inputs'][name] for name in SOURCES},
        equal_contracts=dict(runtime_config=old['runtime_config'], runtime_identity=old['runtime_identity'],
                             rust_binary_sha256=old['binary_sha256'], scoring_references_sha256=sha(old_files['operator/references.json']),
                             scoring_denominators='unchanged scorer and references: 60 scheduled, original completed-subset rules',
                             retrieval_packets_sha256=t.b.sha(t.e.BENCH/'packets.json.gz')),
        expected_changes=dict(registration=changed_reg, freeze_metadata=['version', 'source_commit', 'inputs: three added instrumentation/test files'],
                              archive_metadata='canonical tar/gzip headers; checksums.json and freeze.json only payload changes',
                              observability_receipts=['stages.jsonl', 'diagnostics.json', 'run.json stage/exception fields']),
        requests=requests, inference_performed=False, executions=0, independent_human_review=False)


def prepare():
    t.require(not any(path.exists() for path in [t.REG, t.ARCHIVE, t.FREEZE, t.OUTPUT, t.LEDGER, t.JOURNAL, t.DIAGNOSTICS]),
              'Append-only successor; fresh destinations required')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=t.ROOT, text=True).strip()
    files = payload(revision)
    t.FREEZE.mkdir(parents=True)
    for name, raw in files.items():
        path = t.FREEZE/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    t.RELEASE.mkdir(parents=True, exist_ok=True)
    with t.ARCHIVE.open('xb') as stream:
        stream.write(archive_bytes(files))
    reg = dict(t.b.read(t.original.REG), version=t.VERSION, archive_sha256=t.b.sha(t.ARCHIVE),
        checksums_sha256=sha(files['checksums.json']), source_commit=revision, command=t.COMMAND,
        output=str(t.OUTPUT.relative_to(t.ROOT)), ledger=str(t.LEDGER.relative_to(t.ROOT)),
        predecessor_registration_sha256=OLD_REG_SHA,
        observability=dict(journal=str(t.JOURNAL.relative_to(t.ROOT)), diagnostics=str(t.DIAGNOSTICS.relative_to(t.ROOT))))
    with t.REG.open('xb') as stream:
        stream.write(serialized(reg))
    t.verify()
    with (t.RELEASE/'equivalence.json').open('xb') as stream:
        stream.write(serialized(comparison()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'verify'])
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    else:
        t.verify()
        t.require(comparison() == t.b.read(t.RELEASE/'equivalence.json'), 'Changed equivalence report')


if __name__ == '__main__':
    main()
