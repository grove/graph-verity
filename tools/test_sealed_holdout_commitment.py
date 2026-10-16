"""Public CI checks only holdout commitment metadata, never the confidential gold."""
from pathlib import Path
import json
import tempfile
import unittest

from verify_sealed_holdout import verify

ROOT = Path(__file__).resolve().parents[1]

class SealedHoldoutContractTests(unittest.TestCase):
    def test_only_sha_and_counts_are_public(self):
        doc = json.loads((ROOT / "configs/locked-holdout-commitment.json").read_text())
        self.assertEqual(doc["version"], 1)
        self.assertEqual(doc["split"], "locked_holdout")
        self.assertEqual(doc["cases"], 60)
        self.assertEqual(doc["executable"], 50)
        self.assertEqual(doc["expected_abstentions_not_tested"], 10)
        self.assertTrue(doc["status"].startswith("SEALED_AI_AUTHORED_CANDIDATE"))
        for field in ("bundle_sha256", "benchmark_sha256"):
            self.assertRegex(doc[field], r"^[0-9a-f]{64}$")
        for path in (
            ROOT / "benchmarks" / "locked_holdout.json",
            ROOT / "benchmarks" / "holdout.json",
            ROOT / "graph-verity-sealed-holdout-candidate.zip",
        ):
            self.assertFalse(path.exists(), f"Private holdout leaked into public worktree: {path}")

    def test_bad_bundle_is_rejected_without_logging_gold(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.zip"
            path.write_bytes(b"not a real sealed bundle")
            with self.assertRaisesRegex(ValueError, "Private bundle has changed"):
                verify(path)

if __name__ == "__main__":
    unittest.main()
