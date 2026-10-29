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

    def test_feature_preflight_is_21_gb_and_training_remains_24_gib(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            available = run.FEATURE_MIN_AVAILABLE + 100 * 1024**2
            receipt = {"version": "rgcn-compgcn-readonly-preflight-v5",
                       "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                       "target_hardware_match": True, "machine": "arm64",
                       "ram_total_bytes": 32 * 1024**3,
                       "available_memory_snapshot_bytes": available,
                       "feature_admission_threshold_bytes": run.FEATURE_MIN_AVAILABLE,
                       "training_admission_threshold_bytes": run.MAX_RSS,
                       "available_memory_exceeds_registered_rss_ceiling": False,
                       "training_resource_preflight_passed": False,
                       "feature_resource_preflight_passed": True, "status": "pass"}
            path.write_text(json.dumps(receipt))
            self.assertEqual(run.require_passing_preflight(path), receipt)
            with self.assertRaisesRegex(ValueError, "24 GiB"):
                run.require_passing_preflight(path, training=True)

            receipt["available_memory_snapshot_bytes"] = run.FEATURE_MIN_AVAILABLE - 1
            receipt["feature_resource_preflight_passed"] = False
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "21 GB"):
                run.require_passing_preflight(path)

            receipt["available_memory_snapshot_bytes"] = available
            receipt["feature_resource_preflight_passed"] = True
            receipt["captured_at_utc"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "21 GB"):
                run.require_passing_preflight(path)


if __name__ == "__main__":
    unittest.main()
