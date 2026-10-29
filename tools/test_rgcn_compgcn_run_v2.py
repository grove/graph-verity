"""Feature-vector loader and data-alignment checks; no encoder or model is loaded."""
import tempfile
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

import rgcn_compgcn_run_v2 as run


class FeatureLoaderTests(unittest.TestCase):
    def test_query_candidate_pools_are_role_matched(self):
        self.assertEqual(run.role_candidate_ids("entity", 3, 2), [0, 1, 2])
        self.assertEqual(run.role_candidate_ids("entity", 3, 2, {1}), [0, 2])
        self.assertEqual(run.role_candidate_ids("predicate", 3, 2), [3, 4])
        with self.assertRaisesRegex(ValueError, "Unsupported retrieval role"):
            run.role_candidate_ids("graph", 3, 2)

    def test_synthetic_normalized_vectors_match_frozen_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            run.feature_tests_only(Path(directory))

    def test_feature_and_revised_training_preflight_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            feature_available = run.FEATURE_MIN_AVAILABLE + 100 * 1024**2
            receipt = {"version": "rgcn-compgcn-readonly-preflight-v5",
                       "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                       "target_hardware_match": True, "machine": "arm64",
                       "ram_total_bytes": 32 * 1024**3,
                       "available_memory_snapshot_bytes": feature_available,
                       "feature_admission_threshold_bytes": run.FEATURE_MIN_AVAILABLE,
                       "training_admission_threshold_bytes": run.MAX_RSS,
                       "available_memory_exceeds_registered_rss_ceiling": False,
                       "training_resource_preflight_passed": False,
                       "feature_resource_preflight_passed": True, "status": "pass"}
            path.write_text(json.dumps(receipt))
            self.assertEqual(run.require_passing_preflight(path), receipt)
            receipt["available_memory_snapshot_bytes"] = run.FEATURE_MIN_AVAILABLE - 1
            receipt["feature_resource_preflight_passed"] = False
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "21 GB"):
                run.require_passing_preflight(path)

            training = {"version": run.RESOURCE_PREFLIGHT_VERSION,
                        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                        "target_hardware_match": True, "machine": "arm64",
                        "ram_total_bytes": 32 * 1024**3,
                        "available_memory_snapshot_bytes": run.MAX_RSS,
                        "training_admission_threshold_bytes": run.MAX_RSS,
                        "process_tree_rss_ceiling_bytes": run.MAX_RSS,
                        "process_tree_rss_warning_bytes": run.RSS_WARNING,
                        "minimum_runtime_headroom_bytes": run.MIN_HEADROOM,
                        "maximum_swapout_growth_bytes": run.MAX_SWAPOUT_GROWTH,
                        "critical_memory_pressure_free_percent": run.CRITICAL_FREE_PERCENT,
                        "resource_sample_interval_seconds": run.RESOURCE_SAMPLE_SECONDS,
                        "training_resource_preflight_passed": True, "status": "pass",
                        "resource_metrics_valid": True, "memory_pressure_free_percent": 20,
                        "vm_stat": {"page_size_bytes": 16384, "swapouts_pages": 0},
                        "runtime_identity": {"valid": True}, "frozen_inputs_valid": True,
                        "fit_execution": {"count": 12, "concurrency": 1, "order": "sequential"}}
            path.write_text(json.dumps(training))
            self.assertEqual(run.require_passing_preflight(path, training=True), training)
            training["available_memory_snapshot_bytes"] = run.MAX_RSS - 1
            training["training_resource_preflight_passed"] = False
            path.write_text(json.dumps(training))
            with self.assertRaisesRegex(ValueError, "18 GiB"):
                run.require_passing_preflight(path, training=True)

            training["available_memory_snapshot_bytes"] = run.MAX_RSS
            training["training_resource_preflight_passed"] = True
            training["memory_pressure_free_percent"] = run.CRITICAL_FREE_PERCENT
            path.write_text(json.dumps(training))
            with self.assertRaisesRegex(ValueError, "18 GiB"):
                run.require_passing_preflight(path, training=True)

            receipt["available_memory_snapshot_bytes"] = feature_available
            receipt["feature_resource_preflight_passed"] = True
            receipt["captured_at_utc"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "21 GB"):
                run.require_passing_preflight(path)

    def test_runtime_safeguards_stop_at_each_registered_limit(self):
        page_size = 16 * 1024
        baseline = {"page_size_bytes": page_size, "swapouts_pages": 100}
        sample = {"process_tree_rss_bytes": run.RSS_WARNING,
                  "available_memory_bytes": run.MIN_HEADROOM,
                  "memory_pressure_free_percent": run.CRITICAL_FREE_PERCENT + 1,
                  "vm_stat": baseline}
        self.assertIsNone(run.resource_stop_reason(sample, baseline))

        for changed, phrase in (
            ({"process_tree_rss_bytes": run.MAX_RSS}, "RSS ceiling"),
            ({"available_memory_bytes": run.MIN_HEADROOM - 1}, "headroom"),
            ({"memory_pressure_free_percent": run.CRITICAL_FREE_PERCENT}, "critical"),
            ({"vm_stat": {"page_size_bytes": page_size,
                           "swapouts_pages": 100 + run.MAX_SWAPOUT_GROWTH // page_size}}, "swapout growth"),
        ):
            with self.subTest(phrase=phrase):
                unsafe = {**sample, **changed}
                self.assertIn(phrase, run.resource_stop_reason(unsafe, baseline))

    def test_resource_revision_preserves_original_freeze_and_evaluation_criteria(self):
        source_path = run.EXP / "experiment-manifest-final.json"
        source = run.read(source_path)
        source_hash = run.sha_file(source_path)
        with tempfile.TemporaryDirectory(dir=run.EXP) as directory:
            preflight = Path(directory) / "preflight.json"
            out = Path(directory) / "revised.json"
            run.write(preflight, {"version": run.RESOURCE_PREFLIGHT_VERSION,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "target_hardware_match": True, "machine": "arm64",
                "ram_total_bytes": 32 * 1024**3,
                "available_memory_snapshot_bytes": run.MAX_RSS,
                "training_admission_threshold_bytes": run.MAX_RSS,
                "process_tree_rss_ceiling_bytes": run.MAX_RSS,
                "process_tree_rss_warning_bytes": run.RSS_WARNING,
                "minimum_runtime_headroom_bytes": run.MIN_HEADROOM,
                "maximum_swapout_growth_bytes": run.MAX_SWAPOUT_GROWTH,
                "critical_memory_pressure_free_percent": run.CRITICAL_FREE_PERCENT,
                "resource_sample_interval_seconds": run.RESOURCE_SAMPLE_SECONDS,
                "training_resource_preflight_passed": True, "status": "pass",
                "resource_metrics_valid": True, "memory_pressure_free_percent": 100,
                "vm_stat": {"page_size_bytes": 16384, "swapouts_pages": 10},
                "runtime_identity": {"valid": True}, "frozen_inputs_valid": True,
                "fit_execution": {"count": 12, "concurrency": 1, "order": "sequential"},
                "frozen_inputs": {"source_manifest_sha256": source_hash,
                                  "feature_binding": source["features"]["binding"]}})
            run.revise_resource_manifest(source_path, preflight, out)
            revised = run.read(out)
            self.assertEqual(run.sha_file(source_path), run.PREVIOUS_FINAL_MANIFEST_SHA256)
            self.assertEqual(revised["resource_revision"]["source_manifest_sha256"], source_hash)
            self.assertEqual(revised["comparison"], source["comparison"])
            self.assertEqual(revised["architectures"], source["architectures"])
            self.assertEqual(revised["features"]["binding"], source["features"]["binding"])
            self.assertEqual(revised["training"]["resource_ceiling"]["process_tree_rss_bytes"], run.MAX_RSS)
            self.assertEqual(revised["training"]["resource_ceiling"]["total_training_seconds"], run.MAX_SECONDS)
            self.assertEqual(revised["training"]["fit_execution"]["concurrency"], 1)


if __name__ == "__main__":
    unittest.main()
