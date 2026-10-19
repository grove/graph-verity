"""Post-generation v1e repeat diagnostics; no reference or prompt access."""
import json

PLAN_FIELDS = ("start", "predicate", "graph", "direction", "output")


def strict_draft(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate field")
            result[key] = value
        return result
    try:
        draft = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(draft, dict):
            return None
        status = draft.get("status")
        fields = {"version", "status", "rationale"} | (set(PLAN_FIELDS) if status == "candidate" else set())
        if (set(draft) != fields or draft["version"] != "nl-ask-draft-v1"
                or status not in {"candidate", "needs_clarification", "unsupported"}
                or not isinstance(draft["rationale"], str) or not 1 <= len(draft["rationale"]) <= 512):
            return None
        if status == "candidate" and (any(type(draft[k]) is not int or not 0 <= draft[k] <= 65535
                for k in PLAN_FIELDS[:3]) or draft["direction"] not in {"forward", "reverse"}
                or draft["output"] != "values"):
            return None
        return draft
    except (ValueError, UnicodeDecodeError, TypeError):
        return None


def repeatability(raws):
    """A stable abstention has no plan; a stable candidate may still be wrong."""
    drafts = [strict_draft(raw) for raw in raws]
    valid = len(drafts) >= 2 and all(d is not None for d in drafts)
    statuses = [d["status"] if d else None for d in drafts]
    status_equal = valid and len(set(statuses)) == 1
    plans = [{k: d[k] for k in PLAN_FIELDS} if d and d["status"] == "candidate" else None for d in drafts]
    plan_equal = all(p == plans[0] for p in plans) if valid and all(p is not None for p in plans) else None
    return dict(generations=len(raws), strict_drafts_valid=valid, model_statuses=statuses,
                status_equal=status_equal, structured_plans=plans, structured_plan_equal=plan_equal,
                complete_json_bytes_equal=len(raws) >= 2 and all(raw == raws[0] for raw in raws),
                rationale_text_equal=all(d["rationale"] == drafts[0]["rationale"] for d in drafts) if valid else None,
                semantic_correctness="separately_scored_against_exposed_references",
                gate_passed=status_equal and (statuses[0] != "candidate" or plan_equal is True))
