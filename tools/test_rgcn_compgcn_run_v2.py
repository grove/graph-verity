"""Feature-vector loader and data-alignment checks; no encoder or model is loaded."""
import tempfile
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


if __name__ == "__main__":
    unittest.main()
