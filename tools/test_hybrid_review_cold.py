"""Fresh-process timing checks use only standard-library fake workers, never weights."""
from collections import Counter
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import time
import unittest

import hybrid_review_cold as cold


class ColdStartup(unittest.TestCase):
    def test_fixed_balanced_paired_schedule(self):
        schedule = cold.schedule()
        self.assertEqual(schedule, cold.schedule())
        self.assertEqual(len(schedule), 30)
        self.assertEqual(Counter((s['task_id'], s['system']) for s in schedule),
                         Counter({(case, method): 3 for case in cold.CASES for method in cold.review.METHODS}))
        for left, right in zip(schedule[::2], schedule[1::2]):
            self.assertEqual(left['task_id'], right['task_id'])
            self.assertEqual(left['repetition'], right['repetition'])
            self.assertNotEqual(left['system'], right['system'])

    def test_first_usable_result_includes_startup_but_excludes_teardown(self):
        expected = {'snapshot_id': 'synthetic', 'hits': []}
        program = "import json,time; time.sleep(.1); print(json.dumps({'result':{'snapshot_id':'synthetic','hits':[]},'worker_peak_bytes':1}),flush=True); time.sleep(.2)"
        result = cold.measure([sys.executable, '-c', program], expected)
        self.assertGreaterEqual(result['first_result_ms'], 100)
        self.assertGreater(result['process_exit_ms'] - result['first_result_ms'], 120)

    def test_invalid_result_and_timeout_terminate_worker_group(self):
        with self.assertRaises(ValueError):
            cold.measure([sys.executable, '-c', "print('{}',flush=True)"], {})
        start = time.monotonic()
        with self.assertRaises(queue.Empty):
            cold.measure([sys.executable, '-c', 'import time; time.sleep(10)'], {}, timeout=.1)
        self.assertLess(time.monotonic() - start, 3)

    def test_rejection_also_terminates_nested_child(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'leaked'
            child = "import time; time.sleep(.5); open(" + repr(str(marker)) + ",'w').write('leaked')"
            parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); print('{}',flush=True); time.sleep(10)"
            with self.assertRaises(ValueError):
                cold.measure([sys.executable, '-c', parent], {})
            time.sleep(.6)
            self.assertFalse(marker.exists())

    def test_failed_teardown_is_not_reported_as_success(self):
        program = "import json; print(json.dumps({'result':{},'worker_peak_bytes':1}),flush=True); raise SystemExit(1)"
        with self.assertRaises(ValueError):
            cold.measure([sys.executable, '-c', program], {})

    def test_no_run_without_inference_opt_in(self):
        for function in (cold.run, cold.worker):
            with self.assertRaises(ValueError):
                function(type('Args', (), {'allow_inference': False})())

    def test_cli_requires_explicit_inference_before_opening_inputs(self):
        result = subprocess.run([sys.executable, str(cold.SCRIPT), 'run', '--plan', 'PRIVATE_DO_NOT_OPEN',
                                 '--out', 'PRIVATE_DO_NOT_CREATE'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('ValueError', result.stderr)
        self.assertNotIn('PRIVATE_DO_NOT_OPEN', result.stderr)
