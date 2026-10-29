"""Regression checks for aligned-v2's model-free CPU runtime path."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import rgcn_compgcn_aligned_run_v1 as aligned

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''import hashlib, importlib.metadata, json
from pathlib import Path
import torch
import embedding_experiment as embedding
import rgcn_compgcn_aligned_run_v1 as aligned

requirements = {}
for line in Path("tools/embedding-requirements.txt").read_text().splitlines():
    if line and not line.startswith("#"):
        name, version = line.split("==", 1)
        requirements[name] = version
real_version = importlib.metadata.version
def pinned_version(name):
    return requirements[name] if name in requirements else real_version(name)
importlib.metadata.version = pinned_version
spec = {"model": "google/embeddinggemma-2",
        "revision": "914f7f89142e33e77833254d9c9b90c3cef7303b",
        "dimensions": 768, "terms": {"license": "Apache-2.0"},
        "runtime": {"threads": 4}}
upstream = {"cardData": {"license": "apache-2.0"}}
embedding.verify = lambda: (spec, upstream)
asset_hashes = {"fixture": "a" * 64}
embedding.assets = lambda _path: {"valid": True, "failures": [], "sha256": asset_hashes}
interop_calls = []
real_set_interop = torch.set_num_interop_threads
def counted_set_interop(threads):
    interop_calls.append(threads)
    return real_set_interop(threads)
torch.set_num_interop_threads = counted_set_interop
cpu_calls = []
real_cpu_runtime = embedding.cpu_runtime
def counted_cpu_runtime():
    cpu_calls.append(True)
    return real_cpu_runtime()
embedding.cpu_runtime = counted_cpu_runtime
encoder_calls = []
class MustNotLoadWeights:
    def __init__(self, *args, **kwargs):
        encoder_calls.append(True)
        raise AssertionError("model construction is forbidden in this probe")
embedding.Encoder = MustNotLoadWeights

one = aligned.embedding_runtime_identity(Path("/no-model-load"))
two = aligned.embedding_runtime_identity(Path("/no-model-load"))
runtime_torch, runtime = aligned.reusable_feature_runtime(embedding, two)
runtime_hash = hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest()
conflict = None
try:
    embedding._initialize_cpu_runtime(torch, 2, 1)
except RuntimeError as error:
    conflict = str(error)

print(json.dumps({
    "identity_1": one,
    "identity_2": two,
    "feature_runtime_same_torch_module": runtime_torch is torch,
    "feature_runtime_hash_matches_identity": runtime_hash == two["runtime_sha256"],
    "runtime_threads": [torch.get_num_threads(), torch.get_num_interop_threads()],
    "interop_setter_calls": interop_calls,
    "cpu_runtime_calls": len(cpu_calls),
    "conflicting_config_error": conflict,
    "encoder_constructor_calls": len(encoder_calls),
}, sort_keys=True))
'''

class AlignedCpuRuntimeRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PYTHONPATH="tools")
        proc = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=90)
        if proc.returncode:
            raise AssertionError(f"runtime probe failed:\n{proc.stdout}\n{proc.stderr}")
        cls.result = json.loads(proc.stdout)

    def test_repeated_runtime_identity_checks_initialize_interop_once(self):
        self.assertEqual(self.result["identity_1"], self.result["identity_2"])
        self.assertEqual(self.result["cpu_runtime_calls"], 3)
        self.assertLessEqual(len(self.result["interop_setter_calls"]), 1)

    def test_feature_generation_reuses_initialized_runtime(self):
        self.assertTrue(self.result["feature_runtime_same_torch_module"])
        self.assertTrue(self.result["feature_runtime_hash_matches_identity"])
        self.assertEqual(self.result["runtime_threads"], [4, 1])

    def test_conflicting_runtime_configuration_fails_explicitly(self):
        self.assertIn("already initialized", self.result["conflicting_config_error"])
        self.assertIn("requested (2, 1)", self.result["conflicting_config_error"])

    def test_model_and_runtime_identity_fields_are_preserved(self):
        identity = self.result["identity_1"]
        self.assertEqual(identity["model"], "google/embeddinggemma-2")
        self.assertEqual(identity["revision"], "914f7f89142e33e77833254d9c9b90c3cef7303b")
        self.assertEqual(identity["license"], "Apache-2.0")
        self.assertEqual(identity["upstream_license"], "apache-2.0")
        self.assertEqual(identity["locked_package_versions"]["torch"], requirements_version("torch"))
        self.assertEqual(identity["runtime_sha256"], self.result["identity_2"]["runtime_sha256"])

    def test_model_free_runtime_probe_does_not_construct_model(self):
        self.assertEqual(self.result["encoder_constructor_calls"], 0)
        self.assertFalse(self.result["identity_1"]["model_weights_loaded"])
        self.assertFalse(self.result["identity_1"]["inference_performed"])

    def test_registered_feature_output_must_match_frozen_workspace_path(self):
        path = "experiments/example/runtime-fix/directional-relation-features.npz"
        manifest = {"features": {"new_relation_feature_output": path}}
        self.assertEqual(aligned.registered_feature_output(manifest, aligned.ROOT / path), path)
        with self.assertRaisesRegex(ValueError, "differs from the frozen path"):
            aligned.registered_feature_output(manifest, aligned.ROOT / "experiments/other/features.npz")

    def test_registered_feature_output_cannot_escape_workspace(self):
        manifest = {"features": {"new_relation_feature_output": "outside.npz"}}
        with self.assertRaisesRegex(ValueError, "inside the repository workspace"):
            aligned.registered_feature_output(manifest, Path("/private/tmp/features.npz"))


def requirements_version(package):
    for line in (ROOT / "tools/embedding-requirements.txt").read_text().splitlines():
        if line.startswith(package + "=="):
            return line.split("==", 1)[1]
    raise AssertionError(f"Missing pinned package: {package}")

if __name__ == "__main__":
    unittest.main()
