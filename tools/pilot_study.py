#!/usr/bin/env python3
"""Opt-in offline operator forms. No UI hooks, inference, network or raw text capture."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "studies" / "pilot-v1"
PRIVATE = ROOT / "study-private"
CHECKS = {"entity", "predicate", "scope", "direction", "two_hop", "filter", "count",
          "approval", "truncation", "unknown", "evidence_truth", "ambiguity", "provenance"}
STATUSES = {"not_attempted", "completed", "abandoned", "excluded"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected):
    require(type(value) is dict and set(value) == set(expected.split()), "Invalid fields")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def load(path):
    with Path(path).open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    require(len(raw) <= 1024 * 1024, "Form too large")
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda _: require(False, "Non-finite number"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_files():
    # Fixed public inputs only: never follow a manifest-supplied path or open a holdout.
    paths = ["tools/pilot_study.py", "tools/test_pilot_study.py", "tools/local_find.py",
             "Cargo.lock", "Cargo.toml", "rust-toolchain.toml"]
    paths += ["studies/pilot-v1/" + name for name in (
        "README.md", "consent.md", "protocol.json", "tasks.json", "snapshot.nq", "scope.json",
        "worldcities-scope.json", "policy.json", "clipped-policy.json", "discovery.json")]
    paths += ["crates/verity_core/Cargo.toml", "crates/verity_cli/Cargo.toml"]
    paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "crates").rglob("*.rs"))]
    paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "tools/local_find_ui").iterdir())]
    for dataset in ("wikidata", "worldcities-transfer"):
        paths += [f"data/{dataset}/{name}" for name in
                  ("snapshot.nq", "manifest.json", "discovery.json", "policy.json", "README.md")]
    return {path: sha(ROOT / path) for path in sorted(paths)}


def verify():
    freeze = load(KIT / "freeze.json")
    require(freeze["files"] == frozen_files(), "Frozen kit changed; preregister a new version")
    protocol, tasks = load(KIT / "protocol.json"), load(KIT / "tasks.json")
    require(protocol["version"] == 1 and len(tasks) > 0, "Protocol version/tasks")
    require(len({t["id"] for t in tasks}) == len(tasks), "Duplicate task")
    for task in tasks:
        require(set(task["checks"]) <= CHECKS and len(set(task["checks"])) == len(task["checks"])
                and task["checks"], "Invalid rubric")
        require(set(task["prompt"]) == {"en", "nb"}, "Missing task language")
        require(task["reviewer"] is None, "No human task reviewer has been registered in v1")
        require(task["snapshot"] in {"data/wikidata/snapshot.nq", "data/worldcities-transfer/snapshot.nq",
                                    "studies/pilot-v1/snapshot.nq"}, "Only public pilot snapshots allowed")
        for witness in task["witnesses"]:
            require(witness in (ROOT / task["snapshot"]).read_text().splitlines(), "Missing source witness")
    return protocol, tasks, sha(KIT / "freeze.json")


def form(tasks, protocol_id, language, experience, proficiency, kind="human"):
    return {"version": 1, "protocol_id": protocol_id, "kind": kind,
            "participant": "S-" + secrets.token_hex(8), "consent": True,
            "language": language, "experience": experience, "language_proficiency": proficiency,
            "assessor": None,
            "records": [{"task_id": t["id"], "status": "not_attempted", "seconds": None,
                         "assisted": None, "confidence": None, "relevance": None,
                         "decision": None, "explained_before_approval": None,
                         "checks": dict.fromkeys(t["checks"])} for t in tasks]}


def validate(session, tasks, protocol_id):
    fields(session, "version protocol_id kind participant consent language experience language_proficiency assessor records")
    require(type(session["version"]) is int and session["version"] == 1
            and session["protocol_id"] == protocol_id, "Protocol mismatch")
    require(session["kind"] in {"human", "rehearsal"} and session["consent"] is True, "Consent required")
    require(type(session["participant"]) is str and re.fullmatch(r"S-[0-9a-f]{16}", session["participant"]), "Anonymous ID required")
    require(session["language"] in {"en", "nb"} and session["experience"] in {"beginner", "experienced"}
            and session["language_proficiency"] in {"basic", "fluent"}, "Invalid participant categories")
    assessor = session["assessor"]
    if assessor is not None:
        fields(assessor, "id role")
        require(type(assessor["id"]) is str and re.fullmatch(r"R-[0-9a-f]{16}", assessor["id"])
                and assessor["role"] in {"owner", "independent"}, "Invalid actual assessor")
    require(type(session["records"]) is list, "Invalid records")
    task_map = {t["id"]: t for t in tasks}
    positions = []
    for row in session["records"]:
        fields(row, "task_id status seconds assisted confidence relevance decision explained_before_approval checks")
        require(row["task_id"] in task_map, "Unknown task")
        task = task_map[row["task_id"]]
        positions.append(tasks.index(task))
        require(row["status"] in STATUSES, "Invalid task status")
        require(type(row["checks"]) is dict and set(row["checks"]) == set(task["checks"]), "Rubric mismatch")
        require(all(v is None or type(v) is bool for v in row["checks"].values()), "Invalid rubric judgment")
        require(assessor is not None or all(v is None for v in row["checks"].values()), "Judgments need an actual assessor")
        for key in ("confidence", "relevance"):
            require(row[key] is None or type(row[key]) is int and 1 <= row[key] <= 5, "Invalid explicit user rating")
        require(task["kind"] == "find" or row["relevance"] is None, "Relevance applies to Find only")
        require(row["assisted"] is None or type(row["assisted"]) is bool, "Invalid assistance")
        require(row["seconds"] is None or type(row["seconds"]) is int and 0 <= row["seconds"] <= 7200, "Invalid elapsed time")
        require(row["explained_before_approval"] is None or type(row["explained_before_approval"]) is bool, "Invalid explanation timing")
        require(row["decision"] in {None, "approved", "cancelled", "no_approval"}, "Invalid decision")
        if task["kind"] == "find":
            require(row["decision"] is None and row["explained_before_approval"] is None, "Find has no approval")
        if row["status"] == "not_attempted":
            require(all(row[k] is None for k in ("seconds", "assisted", "confidence", "relevance", "decision", "explained_before_approval"))
                    and all(v is None for v in row["checks"].values()), "Unattempted task has observations")
        else:
            require(row["seconds"] is not None and row["assisted"] is not None, "Attempt needs elapsed time and assistance")
    require(positions == sorted(set(positions)), "Duplicate or out-of-order task")


def rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def observations(session, tasks):
    by_id = {r["task_id"]: r for r in session["records"]}
    for task in tasks:
        row = by_id.get(task["id"])
        attempted = row is not None and row["status"] != "not_attempted"
        checks = dict(row["checks"]) if row else dict.fromkeys(task["checks"])
        if attempted and task["kind"] == "ask":
            # Observe explanations before approval; later correct answers cannot repair this gate.
            if row["decision"] is not None and row["decision"] != task["decision"]:
                checks["approval"] = False
            if row["explained_before_approval"] is False:
                checks["approval"] = False
            if row["explained_before_approval"] is None or row["decision"] is None:
                if checks["approval"] is not False:
                    checks["approval"] = None
        assessed = attempted and session["assessor"] is not None and all(v is not None for v in checks.values())
        wrong = attempted and any(v is False for v in checks.values())
        comprehension = [v for k, v in checks.items() if k not in {"entity", "predicate"}]
        yield {"task": task, "row": row, "attempted": attempted, "assessed": assessed,
               "success": assessed and row["status"] == "completed" and all(checks.values()),
               "wrong": wrong, "checks": checks,
               "comprehension": all(comprehension) if attempted and comprehension and all(v is not None for v in comprehension) else None,
               "confident_wrong": wrong and row["confidence"] is not None and row["confidence"] >= 4}


def metrics(items):
    attempted = [x for x in items if x["attempted"]]
    assessed = [x for x in attempted if x["assessed"]]
    confidence = [x for x in attempted if x["row"]["confidence"] is not None]
    comprehension = [x for x in attempted if x["comprehension"] is not None]
    selection = [[v for k, v in x["checks"].items() if k in {"entity", "predicate"}] for x in attempted]
    selection = [values for values in selection if values and all(v is not None for v in values)]
    relevance = [x["row"]["relevance"] for x in attempted if x["row"]["relevance"] is not None]
    return {"planned": len(items), "attempted": len(attempted),
            "missing_records": sum(x["row"] is None for x in items),
            **{status: sum(x["row"] is not None and x["row"]["status"] == status for x in items) for status in sorted(STATUSES)},
            "assessed": len(assessed), "unassessed_attempts": len(attempted) - len(assessed),
            "assisted": sum(x["row"]["assisted"] for x in attempted),
            "success_per_planned": rate(sum(x["success"] for x in items), len(items)),
            "success_per_assessed": rate(sum(x["success"] for x in assessed), len(assessed)),
            "unassisted_success_per_planned": rate(sum(x["success"] and not x["row"]["assisted"] for x in items), len(items)),
            "incorrect_selection": rate(sum(not all(values) for values in selection), len(selection)),
            "misunderstanding": rate(sum(x["comprehension"] is False for x in comprehension), len(comprehension)),
            "confident_wrong": rate(sum(x["confident_wrong"] for x in confidence), len(confidence)),
            "confidence_unassessed": sum(not x["assessed"] for x in confidence),
            "low_relevance": rate(sum(v <= 2 for v in relevance), len(relevance)),
            "confidence_ratings": {str(v): sum(x["row"]["confidence"] == v for x in confidence) for v in range(1, 6)},
            "seconds_observed": sum(x["row"]["seconds"] for x in attempted),
            "decisions": {v: sum(x["row"]["decision"] == v for x in attempted) for v in ("approved", "cancelled", "no_approval")},
            "failures": {k: rate(sum(x["checks"].get(k) is False for x in attempted),
                                  sum(x["checks"].get(k) is not None for x in attempted)) for k in sorted(CHECKS)}}


def report(sessions, tasks, protocol_id, kind="human"):
    require(kind in {"human", "rehearsal"}, "Invalid report kind")
    seen, assessors, rows = set(), {}, []
    participant_observations = []
    for session in sessions:
        validate(session, tasks, protocol_id)
        require(session["kind"] == kind, "Cannot mix rehearsal and human evidence")
        require(session["participant"] not in seen, "Duplicate participant/session")
        seen.add(session["participant"])
        if session["assessor"]:
            a = session["assessor"]
            require(a["id"] not in assessors or assessors[a["id"]] == a["role"], "Inconsistent assessor role")
            assessors[a["id"]] = a["role"]
        observed = list(observations(session, tasks))
        participant_observations.append(observed)
        rows.extend((session, x) for x in observed)
    all_metrics = metrics([x for _, x in rows])
    human = len(sessions) if kind == "human" else 0
    hypotheses = load(KIT / "protocol.json")["product_readiness_hypotheses"]
    recommendations = ["Real volunteer pilot pending; issue #57 remains open"] if not human else ["Improve UX and vocabulary; inspect observed failure categories before another pilot"]
    if all_metrics["confident_wrong"]["numerator"]:
        recommendations.append("Stop proposed release pending investigation of confident wrong interpretations")
    if all_metrics["low_relevance"]["numerator"]:
        recommendations.append("Iterate on retrieval separately from plan comprehension")
    return {"protocol_id": protocol_id, "kind": kind, "human_participants": human,
            "synthetic_participants": len(sessions) if kind == "rehearsal" else 0,
            "human_task_attempts": all_metrics["attempted"] if kind == "human" else 0,
            "status": "blocked_pending_real_participants" if not human else "exploratory_observations_only",
            "independent_assessors": sum(v == "independent" for v in assessors.values()) if human else 0,
            "owner_assessors": sum(v == "owner" for v in assessors.values()) if human else 0,
            "participants": {"enrolled": len(sessions),
                "attempted": sum(any(x["attempted"] for x in p) for p in participant_observations),
                "completed_all": sum(all(x["success"] for x in p) for p in participant_observations),
                "with_observed_failure": sum(any(x["wrong"] for x in p) for p in participant_observations),
                "with_confident_wrong": sum(any(x["confident_wrong"] for x in p) for p in participant_observations),
                **{name: rate(sum(metrics(p)[name]["numerator"] > 0 for p in participant_observations),
                              sum(metrics(p)[name]["denominator"] > 0 for p in participant_observations))
                   for name in ("incorrect_selection", "misunderstanding", "confident_wrong")}},
            "tasks": all_metrics,
            "by_language": {v: metrics([x for s, x in rows if s["language"] == v]) for v in ("en", "nb")},
            "by_experience": {v: metrics([x for s, x in rows if s["experience"] == v]) for v in ("beginner", "experienced")},
            "by_language_proficiency": {v: metrics([x for s, x in rows if s["language_proficiency"] == v]) for v in ("basic", "fluent")},
            "by_task_type": {v: metrics([x for _, x in rows if x["task"]["type"] == v]) for v in sorted({t["type"] for t in tasks})},
            "recommendations": recommendations,
            "hypotheses_descriptive_only": {
                "sample_target_met": human >= hypotheses["min_participants"],
                "unassisted_task_target_met": all_metrics["unassisted_success_per_planned"]["rate"] >= hypotheses["unassisted_success_per_planned_at_least"] if rows else None,
                "comprehension_target_met": 1 - all_metrics["misunderstanding"]["rate"] >= hypotheses["assessed_comprehension_correct_at_least"] if all_metrics["misunderstanding"]["rate"] is not None else None,
                "stop_for_confident_wrong": all_metrics["confident_wrong"]["numerator"] >= hypotheses["confident_wrong_observations_stop_at"],
                "missing_or_unassessed": any(not x["assessed"] for _, x in rows)},
            "release_go": False, "model_invoked": False, "holdout_accessed": False,
            "limitations": ["AI-authored exposed tasks; no independent task gold review",
                            "Operator judgments are not model or automatic semantic validation",
                            "Convenience sample, fixed order, repeated tasks are correlated",
                            "No statistical safety inference or confidence intervals from task repetitions",
                            "Backend correctness, relevance, intent, confirmation, provenance and truth are separate"]}


def rehearsal(tasks, protocol_id):
    session = form(tasks, protocol_id, "nb", "beginner", "fluent", "rehearsal")
    session["participant"] = "S-0000000000000000"
    session["assessor"] = {"id": "R-0000000000000000", "role": "owner"}
    for task, row in zip(tasks[:3], session["records"]):
        row.update(status="completed", seconds=30, assisted=False, confidence=4, relevance=3,
                   checks=dict.fromkeys(task["checks"], True))
    session["records"][0]["checks"][tasks[0]["checks"][0]] = False
    session["records"][1].update(status="abandoned", assisted=True)
    session["records"].pop(2)
    result = report([session], tasks, protocol_id, "rehearsal")
    require(result["human_participants"] == result["human_task_attempts"] == 0
            and result["tasks"]["attempted"] == 2 and result["tasks"]["missing_records"] == 1
            and result["tasks"]["confident_wrong"]["numerator"] == 1, "Rehearsal arithmetic")
    return result


def private_path(path):
    path = path.resolve()
    require(path.is_relative_to(PRIVATE.resolve()), "Human forms/reports must remain under ignored study-private/")
    return path


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation avoids destroying observations or overwriting an unrelated file.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
        json.dump(value, file, indent=2, allow_nan=False)
        file.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    init = sub.add_parser("init", help="Create a blank private form only after informed consent")
    init.add_argument("--consent", action="store_true")
    init.add_argument("--language", choices=["en", "nb"], required=True)
    init.add_argument("--experience", choices=["beginner", "experienced"], required=True)
    init.add_argument("--language-proficiency", choices=["basic", "fluent"], required=True)
    init.add_argument("--out", type=Path, required=True)
    for command in ("report", "rehearse"):
        p = sub.add_parser(command)
        p.add_argument("--out", type=Path, required=True)
        if command == "report":
            p.add_argument("sessions", nargs="*", type=Path)
    args = parser.parse_args()
    try:
        _, tasks, protocol_id = verify()
        if args.command == "verify":
            print("Frozen pilot-v1 verified; participants and attempts remain unmeasured.")
        elif args.command == "init":
            require(args.consent, "Read consent.md and obtain voluntary consent first")
            write_new(private_path(args.out), form(tasks, protocol_id, args.language, args.experience, args.language_proficiency))
        elif args.command == "rehearse":
            write_new(args.out, rehearsal(tasks, protocol_id))
        else:
            write_new(private_path(args.out), report([load(private_path(p)) for p in args.sessions], tasks, protocol_id))
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Study command rejected: check frozen inputs, consent, private paths and form schema. No payload is logged.\n")


if __name__ == "__main__":
    main()
