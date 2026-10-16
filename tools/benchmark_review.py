"""Read-only review and split checks; reviewer assertions are not authentication."""
from collections import Counter
from datetime import date
import hashlib
import json


SPLITS = {"dev", "review_candidate", "transfer_candidate", "locked_holdout", "transfer_test"}
TEST_SPLITS = {"locked_holdout", "transfer_test"}


def case_sha256(case: dict, snapshot_id: str) -> str:
    """Bind a review to the complete case and its graph snapshot."""
    return hashlib.sha256(json.dumps({"case": case, "snapshot_id": snapshot_id}, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def partition(groups: dict, ids: set[str], label: str) -> dict[str, str]:
    if not isinstance(groups, dict):
        raise ValueError(f"{label} groups must be an object")
    owners = {}
    for group, members in groups.items():
        if not group.strip() or not isinstance(members, list) or not members:
            raise ValueError(f"{label} groups require nonempty ID lists")
        for case_id in members:
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"Invalid {label} member")
            if case_id in owners:
                raise ValueError(f"Duplicate {label} member: {case_id}")
            owners[case_id] = group
    if set(owners) != ids:
        raise ValueError(f"{label} must cover exactly the benchmark case IDs")
    return owners


def review_summary(benchmark: dict, manifest: dict, reviews: dict) -> dict:
    if benchmark["version"] != 1 or manifest["version"] != 1 or reviews["version"] != 1:
        raise ValueError("Unsupported benchmark, split or review version")
    cases = {case["id"]: case for case in benchmark["cases"]}
    if len(cases) != len(benchmark["cases"]):
        raise ValueError("Duplicate question ID")
    if not cases or not set(manifest["splits"]) <= SPLITS:
        raise ValueError("Empty benchmark or unknown split")
    splits = partition(manifest["splits"], set(cases), "Split")
    partition(manifest["groups"], set(cases), "Lineage")
    exposed = manifest["exposed_groups"]
    if (not isinstance(exposed, list) or len(exposed) != len(set(exposed))
            or not set(exposed) <= set(manifest["groups"])):
        raise ValueError("Exposed groups must name distinct known lineage groups")
    for case_id, case in cases.items():
        if splits[case_id] != case["split"]:
            raise ValueError(f"Case/manifest split mismatch: {case_id}")
        if not all(isinstance(case[field], str) and case[field].strip() for field in
                   ("question", "interpretation", "family", "provenance", "review_status")):
            raise ValueError(f"Missing question/review metadata: {case_id}")
        if case["expected_status"] not in {"executed", "needs_clarification", "unsupported", "parsing_error"}:
            raise ValueError(f"Unknown expected status: {case_id}")
        answerable = case["expected_status"] == "executed"
        if any((case[field] is not None) != answerable for field in
               ("gold", "reference_sparql", "expected_bindings")):
            raise ValueError(f"Expected status/gold mismatch: {case_id}")
        if not case["scope"] or (answerable and
                (case["gold"]["snapshot_id"] != benchmark["snapshot_id"] or
                 case["gold"]["scope"] != case["scope"])):
            raise ValueError(f"Gold snapshot/scope mismatch: {case_id}")
    for group, members in manifest["groups"].items():
        member_splits = {splits[case_id] for case_id in members}
        if member_splits & TEST_SPLITS and len(member_splits) != 1:
            raise ValueError("Related templates/paraphrases cross a locked test boundary")
        if member_splits & TEST_SPLITS and group in exposed:
            raise ValueError("Previously exposed material cannot become an independent test")

    # Append-only history may retain old hashes; only the latest decision can approve current gold.
    latest = {}
    fields = {"case_id", "case_sha256", "reviewer", "reviewed_at", "decision", "rationale"}
    for record in reviews["records"]:
        if set(record) != fields or not all(isinstance(v, str) and v.strip() for v in record.values()):
            raise ValueError("Review records require identity, date, hash, decision and rationale")
        case_id = record["case_id"]
        if case_id not in cases or record["decision"] not in {"approved", "excluded", "disputed"}:
            raise ValueError("Unknown reviewed case or decision")
        digest = record["case_sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid review case hash")
        reviewed_at = date.fromisoformat(record["reviewed_at"])
        if reviewed_at.isoformat() != record["reviewed_at"] or reviewed_at > date.today():
            raise ValueError("Review date must be YYYY-MM-DD and not in the future")
        if case_id in latest and record["reviewed_at"] < latest[case_id]["reviewed_at"]:
            raise ValueError("Review history must be chronological for each case")
        latest[case_id] = record

    hashes = {case_id: case_sha256(case, benchmark["snapshot_id"]) for case_id, case in cases.items()}
    decisions = {}
    for case_id, digest in hashes.items():
        record = latest.get(case_id)
        if record is None:
            decisions[case_id] = "pending"
        elif record["case_sha256"] != digest:
            decisions[case_id] = "stale"
        else:
            decisions[case_id] = record["decision"]
    approved = Counter(splits[case_id] for case_id, decision in decisions.items() if decision == "approved")
    eligible = [case_id for case_id in cases if splits[case_id] in {"dev", *TEST_SPLITS}]
    initial_ready = approved["dev"] >= 30
    final_ready = (initial_ready and 100 <= len(eligible) <= 200
                   and all(decisions[case_id] == "approved" for case_id in eligible)
                   and all(approved[split] > 0 for split in TEST_SPLITS))
    return {"version": 1, "decisions": dict(Counter(decisions.values())),
            "approved_by_split": dict(approved), "initial_ready": initial_ready,
            "final_ready": final_ready, "case_sha256": hashes}
