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

    def test_preflight_must_be_fresh_and_meet_registered_memory_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            receipt = {"version": "rgcn-compgcn-readonly-preflight-v3",
                       "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                       "target_hardware_match": True, "machine": "arm64",
                       "ram_total_bytes": 32 * 1024**3,
                       "available_memory_snapshot_bytes": run.MAX_RSS,
                       "available_memory_exceeds_registered_rss_ceiling": True,
                       "resource_preflight_passed": True, "status": "pass"}
            path.write_text(json.dumps(receipt))
            self.assertEqual(run.require_passing_preflight(path), receipt)

            receipt["available_memory_snapshot_bytes"] = run.MAX_RSS - 1
            receipt["resource_preflight_passed"] = False
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "24 GiB"):
                run.require_passing_preflight(path)

            receipt["available_memory_snapshot_bytes"] = run.MAX_RSS
            receipt["resource_preflight_passed"] = True
            receipt["captured_at_utc"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "24 GiB"):
                run.require_passing_preflight(path)


if __name__ == "__main__":
    unittest.main()
