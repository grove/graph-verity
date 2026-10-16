#!/usr/bin/env python3
"""Verify an external, sequestered holdout candidate without disclosing its gold.

Never run this tool in public CI with a real private bundle. Only the
cryptographic commitment, never the questions/answers, belongs in Git.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[1]
COMMITMENT = ROOT / "configs" / "locked-holdout-commitment.json"
FILES = {"holdout.json", "manifest.json", "reviews.json", "README.txt"}

def verify(path: Path) -> dict:
    conf = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    if conf["status"] != "SEALED_AI_AUTHORED_CANDIDATE_NOT_INDEPENDENTLY_EXPERT_APPROVED":
        raise ValueError("Unsupported holdout integrity commitment status")
    if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Missing or unexpectedly large private holdout bundle")
    digest = sha256(path.read_bytes()).hexdigest()
    if digest != conf["bundle_sha256"]:
        raise ValueError("Private bundle has changed relative to public commitment")
    with ZipFile(path) as archive:
        members = archive.namelist()
        if len(members) != len(FILES) or set(members) != FILES:
            raise ValueError("Unexpected private bundle files")
        if archive.testzip() is not None:
            raise ValueError("Corrupted ZIP member")
        if sum(item.file_size for item in archive.infolist()) > 4 * 1024 * 1024:
            raise ValueError("Unbounded ZIP contents")
        gold_raw = archive.read("holdout.json")
        meta = json.loads(archive.read("manifest.json"))
        ledger = json.loads(archive.read("reviews.json"))
        gold = json.loads(gold_raw)
    if (sha256(gold_raw).hexdigest() != conf["benchmark_sha256"]
            or meta["frozen_benchmark_sha256"] != conf["benchmark_sha256"]
            or meta["snapshot_id"] != conf["snapshot_id"]
            or gold["snapshot_id"] != conf["snapshot_id"]
            or gold["version"] != 1
            or len(gold["cases"]) != conf["cases"]
            or len({c["id"] for c in gold["cases"]}) != conf["cases"]
            or any(c["split"] != conf["split"] for c in gold["cases"])):
        raise ValueError("Incorrect split or frozen benchmark identity")
    executable = [c for c in gold["cases"] if c["expected_status"] == "executed"]
    abstain = [c for c in gold["cases"] if c["expected_status"] in
               {"needs_clarification", "unsupported", "parsing_error"}]
    if (len(executable) != conf["executable"]
            or len(abstain) != conf["expected_abstentions_not_tested"]):
        raise ValueError("Holdout denominator mismatch")
    if (any(any(c[k] is None for k in
                 ("gold", "reference_sparql", "expected_bindings")) for c in executable)
            or any(any(c[k] is not None for k in
                       ("gold", "reference_sparql", "expected_bindings")) for c in abstain)):
        raise ValueError("Expected-status/gold mismatch")
    if ledger["records"]:
        raise ValueError("This commitment covers an unreviewed AI candidate, not approved gold")
    return {"integrity": "verified_against_public_commitment",
            "cases": len(gold["cases"]), "executable": len(executable),
            "recorded_abstentions_not_model_tested": len(abstain),
            "human_expert_review": "pending", "model_invoked": False,
            "locked_holdout_evaluated": False,
            "source_snapshot": conf["snapshot_id"]}

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path, help="External private ZIP, never commit into public repo")
    args = p.parse_args()
    # Prints *only metadata*, never private questions or expected bindings.
    print(json.dumps(verify(args.bundle), indent=2))

if __name__ == "__main__":
    main()
