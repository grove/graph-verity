#!/usr/bin/env python3
"""Test current code and replay #53/#57 against unchanged source fingerprints."""
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PILOT_COMMIT = "f12422a0b106faa84c2f1cd05c8ee99fea14c185"
NL_ASK_COMMIT = "bba81fc68c3b7f6a63aa3c104baf3ea29d49e754"
VOCABULARY_COMMIT = "6d90bf8df3ce87c286d3ccd67097f817afdf16a3"
V1G_COMMIT = "e7d5dbfe3f2a80e14b08df7c2d10693fd2eb0ae9"


def current_tests(suite):
    # Only source-fingerprint checks move to the original export. Current contract tests remain.
    frozen_only = {
        "test_nl_ask_benchmark.NarrowAskTests.test_frozen_sources_splits_and_manifest",
        "test_one_hop_trial.OneHopTrialTests.test_committed_freeze_and_decision_replay_without_models",
        "test_native_one_hop_v1g_registration.CommittedExecutionTests.test_committed_execution_and_separate_development_bytes",
    }
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from current_tests(test)
        elif test.id() not in frozen_only:
            yield test


def current_modules(shard=None):
    paths = [path for path in sorted((ROOT / "tools").glob("test_*.py"))
             if path.name not in {"test_pilot_study.py", "test_nl_ask_evaluation.py"}]
    return paths if shard is None else paths[shard::2]


def main(shard=None):
    sys.path.insert(0, str(ROOT / "tools"))
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for path in current_modules(shard):
        # The original pilot hashes every Rust file; current-code coverage lives in
        # the other suites. Never refresh its source fingerprints to accept new code.
        suite.addTests(current_tests(loader.loadTestsFromName(path.stem)))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if shard is None:
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
    replay_v1g_history()


def replay_v1g_history():
    release = Path("experiments/native-one-hop-v1g/execution-v1")
    with source_export(V1G_COMMIT) as (source, _):
        def hashes(root):
            return {p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob("*") if p.is_file()}
        assert hashes(ROOT / release) == hashes(source / release), "Changed frozen v1g evidence"
        reg = json.loads((ROOT / release / "freeze/execution-registration.json").read_bytes())
        corrected_source = {
            "tools/native_one_hop.py", "tools/test_native_one_hop_diagnostic.py",
            "tools/test_native_one_hop_v1g_registration.py", "tools/run_python_tests.py",
            "tools/verify_pre_llm.py", "tools/test_run_python_tests.py", "tools/test_verify_pre_llm.py",
        }
        for name, digest in reg["freeze_manifest"]["input_sha256"].items():
            if name not in corrected_source:
                assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
        env = dict(os.environ, GIT_DIR=str(ROOT / ".git"), GIT_WORK_TREE=str(source))
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tools",
                        "-p", "test_native_one_hop_v1g_registration.py", "-v"],
                       cwd=source, env=env, check=True)


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


def replay_nl_ask_history():
    # Preserve #72–#76 source hashes and evidence; never reseal them for current code.
    with source_export(NL_ASK_COMMIT) as (source, _):
        for name in ["studies/nl-ask-v1", "reports/issue-74-one-hop-trial", "reports/issue-76-nl-ask-evaluation"]:
            def hashes(root):
                return {p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in root.rglob("*") if p.is_file()}
            assert hashes(ROOT / name) == hashes(source / name), "Changed frozen NL Ask evidence: " + name
        # The original #72 verifier inspects Git objects. Exported files stay separate,
        # while read-only object inspection uses the real repository's immutable history.
        env = dict(os.environ, GIT_DIR=str(ROOT / ".git"), GIT_WORK_TREE=str(source))
        subprocess.run(["cargo", "build", "--locked", "--offline", "-q", "-p", "verity_cli"], cwd=source, env=env, check=True)
        for name in ["test_nl_ask_benchmark.py", "test_one_hop_trial.py", "test_nl_ask_evaluation.py"]:
            subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tools", "-p", name, "-v"],
                           cwd=source, env=env, check=True)
        for args in [["verify"], ["baseline", "--split", "development"]]:
            subprocess.run([sys.executable, "tools/nl_ask_benchmark.py", *args], cwd=source, env=env, check=True)


if __name__ == "__main__":
    if sys.argv[1:] in (["current", "0"], ["current", "1"]):
        sys.exit(main(int(sys.argv[2])))
    elif sys.argv[1:] == ["frozen-history"]:
        replay_frozen_studies()
    elif sys.argv[1:] == ["question-vocabulary"]:
        replay_question_vocabulary()
    elif sys.argv[1:] == ["nl-ask-history"]:
        replay_nl_ask_history()
    elif not sys.argv[1:]:
        sys.exit(main())
    else:
        sys.exit("usage: run_python_tests.py [current 0|current 1|frozen-history|question-vocabulary|nl-ask-history]")
