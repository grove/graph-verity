import hashlib
import gzip
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import tempfile
import tarfile
import unittest
from unittest.mock import patch

import gemet
import hybrid_retrieval as h
import retrieval as r

REPORT = r.ROOT/'reports/issue-50-real-rdf-hybrid'


class HybridTests(unittest.TestCase):
    def test_frozen_retrieval_cases_source_witnesses_and_disclosed_lineages(self):
        spec, cases = h.verify_protocol()
        self.assertEqual(len(cases), 122)
        self.assertEqual(spec['counts']['split'], {'development': 40, 'evaluation': 82})
        source = set((r.ROOT/'data/gemet/snapshot.nq').read_text().splitlines())
        for c in cases:
            self.assertTrue(all(q in source for witness in c['witnesses'] for q in witness['source_quads']))
        groups = {s: {g for c in cases if c['split'] == s for g in c['group_lineage']}
                  for s in ['development', 'evaluation']}
        self.assertEqual(sorted(groups['development'] & groups['evaluation']), spec['shared_resource_lineages'])
        self.assertEqual(len(spec['shared_resource_lineages']), 5)
        with patch.object(r, 'sha', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'frozen input changed'):
                h.verify_protocol()

    def test_real_source_license_and_byte_reproduction(self):
        manifest = gemet.verify()
        self.assertEqual(manifest['selected_concepts'], 2200)
        with tempfile.TemporaryDirectory() as directory:
            gemet.build(2200, Path(directory))
            for name in ['snapshot.nq', 'policy.json', 'scope.json', 'discovery.json', 'stats.json']:
                self.assertEqual((Path(directory)/name).read_bytes(), (gemet.DATA/name).read_bytes())
        with patch.object(r, 'sha', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'frozen source/import changed'):
                gemet.verify()

    def test_no_inference_without_explicit_opt_in_and_no_import_in_ci(self):
        with patch.object(h.e, 'cpu_runtime', side_effect=AssertionError('no inference')):
            with self.assertRaisesRegex(ValueError, '--allow-inference'):
                h.run(SimpleNamespace(allow_inference=False))
            with self.assertRaisesRegex(ValueError, '--allow-inference'):
                h.cold(SimpleNamespace(allow_inference=False))
            h.verify_protocol()

    def test_bounded_normalized_vectors_and_candidate_states(self):
        from array import array
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'vectors.gz'
            for values, message in [([1.], 'dimensions'), ([float('nan')]*768, 'Nonfinite'), ([0.]*768, 'Unnormalized')]:
                with gzip.open(path, 'wb') as stream:
                    stream.write(array('f', values).tobytes())
                with self.assertRaisesRegex(ValueError, message):
                    h.vector_read(path, 1)
        self.assertEqual([h.state(n) for n in [0, 1, 2, 500]],
                         ['no_match', 'low_confidence', 'ambiguous_candidates', 'ambiguous_candidates'])

    def test_resident_transport_bounds_frames_and_keeps_scope_authorization(self):
        subprocess.run(['cargo', 'build', '--locked', '--offline', '-p', 'verity_cli',
                        '--example', 'retrieval_session'], cwd=r.ROOT, check=True,
                       capture_output=True, text=True, timeout=300)
        spec, _ = h.verify_protocol()
        corpus = spec['corpus']
        argv = [str(r.ROOT/'target/debug/examples/retrieval_session'),
                *[str(r.ROOT/corpus[k]) for k in ['rdf', 'policy', 'scope', 'config']]]
        request = dict(query='water pollution', scope=r.read(r.ROOT/corpus['scope']), role='entity', limit=1)
        good = subprocess.run(argv, input=(json.dumps(request) + '\n') * 2,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(good.returncode, 0, good.stderr)
        ready, first, second = map(json.loads, good.stdout.splitlines())
        self.assertTrue(ready['ready'])
        self.assertEqual(first, second)
        self.assertEqual(first['snapshot_id'], ready['manifest']['snapshot_id'])
        for frame in ['x' * 65537 + '\n', '{}',
                      json.dumps(dict(request, scope=['urn:PRIVATE_SCOPE_CANARY'])) + '\n']:
            bad = subprocess.run(argv, input=frame, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(bad.returncode, 0)
            self.assertEqual(len(bad.stdout.splitlines()), 1)  # Authorized ready metadata only.
            self.assertNotIn('CANARY', bad.stdout)

    def test_retained_evidence_replays_without_model_runtime(self):
        # Full vector-dot replay is the normal model-free CI path, not synthetic parity.
        with patch.object(h.e, 'cpu_runtime', side_effect=AssertionError('CI must remain model-free')):
            h.verify_report(REPORT/'freeze', REPORT/'run')
        self.assertFalse(r.read(REPORT/'run/decision.json')['automatic_integration'])
        self.assertTrue(r.read(REPORT/'scope-canary.json')['document_roles_text_counts_unchanged'])

    def test_report_inventories_original_attempts_and_real_scale_block(self):
        checksums = r.read(REPORT/'checksums.json')
        self.assertEqual(set(checksums), {str(p.relative_to(REPORT)) for p in REPORT.rglob('*')
                                        if p.is_file() and p.name != 'checksums.json'})
        for name, expected in checksums.items():
            self.assertEqual(r.sha(REPORT/name), expected, name)
        limits = r.read(REPORT/'limits.json')
        with gzip.open(REPORT/'full-source-attempt.nq.gz', 'rb') as stream:
            self.assertEqual(hashlib.sha256(stream.read()).hexdigest(), limits['full_source_rdf_sha256'])
        self.assertEqual(limits['full_source_definition_variant_stdout'], '')
        self.assertIn('index_limit', limits['full_source_definition_variant_stderr'])
        self.assertIn('fewer concepts', limits['requested_10000_stderr'])
        self.assertEqual(limits['full_source_baseline_documents'], 5588)
        self.assertFalse(limits['limits_raised'])
        self.assertFalse(limits['synthetic_resources_added'])
        baseline = r.read(REPORT/'baseline-source.json')
        self.assertTrue(baseline['exact_find_and_discovery_source_matches_frozen_issue46'])
        with tarfile.open(REPORT/'run-1.tar.gz', 'r:gz') as archive:
            previous_freeze = json.load(archive.extractfile('freeze/freeze.json'))
            for directory in ['freeze', 'run']:
                inv = json.load(archive.extractfile(directory+'/artifacts.json'))
                for name, expected in inv.items():
                    self.assertEqual(hashlib.sha256(archive.extractfile(directory+'/'+name).read()).hexdigest(), expected)
            self.assertEqual(json.load(archive.extractfile('run/summary.json')), r.read(REPORT/'run/summary.json'))
        for filename, freeze in [('frozen-code.tar.gz', r.read(REPORT/'freeze/freeze.json')),
                                 ('frozen-code-v1.tar.gz', previous_freeze)]:
            with tarfile.open(REPORT/filename, 'r:gz') as archive:
                for prefix, mapping in [('measured/', freeze['code_sha256']), ('baseline/', baseline['sha256'])]:
                    for path, expected in mapping.items():
                        self.assertEqual(hashlib.sha256(archive.extractfile(prefix+path).read()).hexdigest(), expected)
        self.assertTrue(r.read(REPORT/'repeat-comparison.json')['identical_all_hits_scores_metrics_and_summaries'])
        self.assertEqual(r.read(REPORT/'historical-controls.json')['total_rank_lists'], 320)
        decision = r.read(REPORT/'run/decision.json')
        for variant in decision['variants'].values():
            self.assertTrue(variant['checks']['positive_paired_gain'])
            self.assertFalse(variant['checks']['exact_nonregression'])
            self.assertFalse(variant['checks']['no_match_nonregression'])
            self.assertFalse(variant['checks']['memory'])
            self.assertFalse(variant['engineering_rule_pass'])

    def test_resealed_rank_tampering_cannot_change_judgments_or_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'run'
            shutil.copytree(REPORT/'run', out)
            with gzip.open(out/'ranks.jsonl.gz', 'rt', encoding='utf-8') as stream:
                rows = [json.loads(line) for line in stream]
            rows[0]['split'] = 'evaluation'
            with gzip.open(out/'ranks.jsonl.gz', 'wt', encoding='utf-8') as stream:
                stream.writelines(json.dumps(row) + '\n' for row in rows)
            h.inventory(out)
            with self.assertRaisesRegex(ValueError, 'Changed judgment'):
                h.verify_report(REPORT/'freeze', out, replay_vectors=False)


if __name__ == '__main__':
    unittest.main()
