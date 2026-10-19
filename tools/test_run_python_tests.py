"""Keep current contract checks while replaying frozen source fingerprints independently."""
import unittest

import run_python_tests as runner


class RunnerTests(unittest.TestCase):
    def test_only_exact_frozen_fingerprint_tests_move_to_original_source(self):
        class NamedTest(unittest.TestCase):
            def __init__(self, name):
                super().__init__()
                self.name = name

            def id(self):
                return self.name
        source_check = NamedTest("test_nl_ask_benchmark.NarrowAskTests.test_frozen_sources_splits_and_manifest")
        trial_check = NamedTest("test_one_hop_trial.OneHopTrialTests.test_committed_freeze_and_decision_replay_without_models")
        contract = NamedTest("test_nl_ask_benchmark.NarrowAskTests.test_schema_matches_rust_and_all_frozen_references_preview_without_execution")
        error = unittest.loader._FailedTest("test_import_failure", ImportError("fixture"))
        suite = unittest.TestSuite([unittest.TestSuite([source_check, contract]), trial_check, error])
        self.assertEqual(list(runner.current_tests(suite)), [contract, error])
