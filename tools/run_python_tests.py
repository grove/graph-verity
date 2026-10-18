#!/usr/bin/env python3
"""Test current code and replay #53/#57 against unchanged source fingerprints."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PILOT_COMMIT = "f12422a0b106faa84c2f1cd05c8ee99fea14c185"


def main():
    sys.path.insert(0, str(ROOT / "tools"))
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for path in sorted((ROOT / "tools").glob("test_*.py")):
        # The original pilot hashes every Rust file; current-code coverage lives in
        # the other suites. Never refresh its source fingerprints to accept new code.
        if path.name != "test_pilot_study.py":
            suite.addTests(loader.loadTestsFromName(path.stem))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    replay_frozen_studies()
    return 0


def replay_frozen_studies():
    with tempfile.TemporaryDirectory(prefix="verity-frozen-pilot-") as temp:
        directory = Path(temp)
        archive = directory / "source.tar"
        with archive.open("wb") as stream:
            subprocess.run(["git", "archive", "--format=tar", PILOT_COMMIT], cwd=ROOT, stdout=stream, check=True)
        source = directory / "source"
        source.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter="data")
        frozen = json.loads((ROOT / "studies/pilot-v1/freeze.json").read_bytes())
        # Fail if the historical export differs from the committed original kit.
        assert (source / "studies/pilot-v1/freeze.json").read_bytes() == (ROOT / "studies/pilot-v1/freeze.json").read_bytes()
        for name, digest in frozen["files"].items():
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digest, name
        for args in [
            ["-m", "unittest", "discover", "-s", "tools", "-p", "test_pilot_study.py", "-v"],
            ["tools/pilot_study.py", "verify"],
            ["tools/pilot_study.py", "rehearse", "--out", str(directory / "rehearsal.json")],
        ]:
            subprocess.run([sys.executable, *args], cwd=source, check=True)
        # #53 also compares native source revisions, not just ranks. The current
        # lexical rank/score replay remains a separate verify_pre_llm check.
        original = json.loads((ROOT / "reports/issue-53-selective-hybrid/freeze/freeze.json").read_bytes())
        for name in ["crates/verity_core/src/catalog.rs", "crates/verity_core/src/discovery.rs", "crates/verity_core/src/lib.rs", "crates/verity_core/src/find.rs", "Cargo.lock", "rust-toolchain.toml"]:
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == original["code_sha256"][name], name
        subprocess.run(["cargo", "build", "--locked", "--offline", "-q", "-p", "verity_cli", "--example", "retrieval_session"], cwd=source, check=True)
        subprocess.run([sys.executable, "tools/selective_hybrid.py", "verify-report",
                        "--freeze", "reports/issue-53-selective-hybrid/freeze",
                        "--out", "reports/issue-53-selective-hybrid/run",
                        "--binary", str(source / "target/debug/examples/retrieval_session")], cwd=ROOT, check=True)


if __name__ == "__main__":
    sys.exit(main())
