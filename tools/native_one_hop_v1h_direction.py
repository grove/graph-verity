#!/usr/bin/env python3
"""Direction-only successor using the unchanged status-precedence freeze/runner."""
from contextlib import contextmanager

import native_one_hop_v1h_status_precedence as p

h = p.h
ROOT = h.ROOT
NAME = 'native-one-hop-v1h-qwen-direction-only'
CONFIG = ROOT / 'configs' / (NAME + '.json')
RELEASE = ROOT / 'experiments' / NAME
PARENT = p.RELEASE
STATUS_VERIFY = p.verify
SOURCES = [
    'tools/native_one_hop_v1h_direction.py',
    'tools/test_native_one_hop_v1h_direction.py',
    'tools/audit_v1h_predicates.py',
    'tools/native_one_hop_v1h_status_precedence.py',
    'tools/test_native_one_hop_v1h_status_precedence.py',
    'configs/native-one-hop-v1h-qwen-status-precedence.json',
    'configs/native-one-hop-v1h-qwen-status-precedence.prompt.txt',
    *h.read(RELEASE / 'provenance-audit.json')['input_sha256'],
    *[str((RELEASE / name).relative_to(ROOT)) for name in
      ['README.md', 'prompt.diff', 'provenance-audit.json', 'synthetic-drafts.json']],
]
OLD = 'Reverse follows that same stored predicate from object to subject; do not invent an inverse property.'
NEW = ('For reverse traversal, start from the original object and follow the same original predicate to matching subjects; '
       'do not invent an inverse property. Keep the original named graph and use its graph-qualified numeric entity, '
       'predicate and graph IDs. Return matching subjects through the existing values projection. '
       'Plural wording does not require multiple matches, counting or additional hops.')


def verify(folder, binary=h.a.BINARY):
    frozen = STATUS_VERIFY(folder, binary)
    old = h.read(PARENT / 'registration.json')['freeze_manifest']['config']
    current = h.config()
    allowed = {'version', 'hypothesis', 'comparison', 'prompt_file', 'parent_registration',
               'parent_registration_sha256', 'baseline_evidence', 'baseline_evidence_sha256',
               'proposed_output', 'primary_evaluation', 'reporting'}
    h.require({k: v for k, v in current.items() if k not in allowed} ==
              {k: v for k, v in old.items() if k not in allowed}, 'Changed non-direction configuration')
    before = (ROOT / old['prompt_file']).read_text()
    after = (ROOT / current['prompt_file']).read_text()
    h.require(before.count(OLD) == 1 and after == before.replace(OLD, NEW),
              'Only reverse construction wording may change')
    return frozen


@contextmanager
def experiment():
    names = ['CONFIG', 'RELEASE', 'VERSION', 'SOURCES', 'PARENT', 'verify']
    previous = {name: getattr(p, name) for name in names}
    for name, value in zip(names, [CONFIG, RELEASE, 'issue83-native-cpu-v1h-qwen-direction-only', SOURCES, PARENT, verify]):
        setattr(p, name, value)
    try:
        with p.experiment():
            yield
    finally:
        for name, value in previous.items():
            setattr(p, name, value)


if __name__ == '__main__':
    with experiment():
        p.main()
