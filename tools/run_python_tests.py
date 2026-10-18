#!/usr/bin/env python3
"""Test current code and replay #53/#57 against unchanged source fingerprints."""
import hashlib
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PILOT_COMMIT = "f12422a0b106faa84c2f1cd05c8ee99fea14c185"
VOCABULARY_COMMIT = "6d90bf8df3ce87c286d3ccd67097f817afdf16a3"


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


@contextmanager
def source_export(commit):
    with tempfile.TemporaryDirectory(prefix="verity-frozen-pilot-") as temp:
        directory = Path(temp)
        archive = directory / "source.tar"
        with archive.open("wb") as stream:
            subprocess.run(["git", "archive", "--format=tar", commit], cwd=ROOT, stdout=stream, check=True)
        source = directory / "source"
        source.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter="data")
        yield source, directory


def replay_frozen_studies():
    with source_export(PILOT_COMMIT) as (source, directory):
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


def replay_question_vocabulary():
    # #73 packets bind the original source/index identity, including lib.rs.
    report = Path("reports/issue-73-question-vocabulary")
    with source_export(VOCABULARY_COMMIT) as (source, _):
        frozen = json.loads((ROOT / report / "freeze/freeze.json").read_bytes())
        for name, digest in frozen["input_sha256"].items():
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digest, name
        for folder in [report, Path("benchmarks/question-vocabulary-v1")]:
            def hashes(root):
                return {p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in root.rglob("*") if p.is_file()}
            assert hashes(ROOT / folder) == hashes(source / folder), "Changed frozen vocabulary evidence"
        subprocess.run(["cargo", "build", "--locked", "--offline", "-q", "-p", "verity_cli"], cwd=source, check=True)
        subprocess.run([sys.executable, "tools/question_vocabulary.py", "verify",
                        "--binary", str(source / "target/debug/verity")], cwd=source, check=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["question-vocabulary"]:
        replay_question_vocabulary()
    elif not sys.argv[1:]:
        sys.exit(main())
    else:
        sys.exit("usage: run_python_tests.py [question-vocabulary]")
