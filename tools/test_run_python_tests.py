"""Keep current contract checks while replaying frozen source fingerprints independently."""
import unittest
from unittest.mock import patch

import run_python_tests as runner


class RunnerTests(unittest.TestCase):
    def test_shards_cover_every_current_module_once(self):
        expected = {path for path in (runner.ROOT / "tools").glob("test_*.py")
                    if path.name not in {"test_pilot_study.py", "test_nl_ask_evaluation.py"}}
        first, second = runner.current_modules(0), runner.current_modules(1)
        self.assertEqual(set(first) | set(second), expected)
        self.assertFalse(set(first) & set(second))
        self.assertEqual(runner.current_modules(), sorted(expected))

    def test_failed_shard_does_not_pass_or_replay_history(self):
        with patch.object(runner, "current_modules", return_value=[]), \
             patch.object(runner.unittest, "TextTestRunner") as execute, \
             patch.object(runner, "replay_frozen_studies") as replay:
            execute.return_value.run.return_value.wasSuccessful.return_value = False
            self.assertEqual(runner.main(0), 1)
            replay.assert_not_called()

    def test_default_runner_keeps_history_but_shards_leave_it_to_its_own_check(self):
        with patch.object(runner, "current_modules", return_value=[]), \
             patch.object(runner.unittest, "TextTestRunner") as execute, \
             patch.object(runner, "replay_frozen_studies") as replay:
            execute.return_value.run.return_value.wasSuccessful.return_value = True
            self.assertEqual(runner.main(0), 0)
            replay.assert_not_called()
            self.assertEqual(runner.main(), 0)
            replay.assert_called_once_with()

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
