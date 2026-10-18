"""The historical pilot is verified without updating its commitment or inputs."""
from hashlib import sha256
import unittest

import frozen_pilot as pilot


class FrozenPilotTests(unittest.TestCase):
    def test_export_is_exact_and_does_not_include_new_rust_sources(self):
        original = (pilot.ROOT / pilot.FREEZE).read_bytes()
        with pilot.source_snapshot() as source:
            self.assertEqual((source / pilot.FREEZE).read_bytes(), original)
            self.assertEqual(sha256(original).hexdigest(), pilot.FREEZE_SHA256)
            self.assertFalse((source / 'crates/verity_core/src/nl_ask.rs').exists())
            self.assertTrue((source / 'tools/test_pilot_study.py').is_file())
            self.assertTrue((source / 'data/wikidata/scope.json').is_file())
        self.assertEqual((pilot.ROOT / pilot.FREEZE).read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
