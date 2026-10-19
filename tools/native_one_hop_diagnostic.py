"""V1f observation only. No query execution, prompt enrichment or semantic approval."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import time

import native_one_hop as a
from native_one_hop_semantics import PLAN_FIELDS, repeatability, strict_draft


def accounting(cfg):
    rows = []
    for condition in cfg["stages"]:
        cases = [("repeat-0", cfg["smoke_cases"][0]), ("repeat-1", cfg["smoke_cases"][0])] if condition == "oracle" else []
        cases += list(cfg["control_cases"].items()) + [("smoke-" + cid, cid) for cid in cfg["smoke_cases"]]
        for name, cid in cases:
            rows.append(dict(condition=condition, name=name, case_id=cid, status="unattempted", generation_attempted=False,
                             raw_output=None, raw_base64=None, raw_sha256=None, model_origin_status=None, json_valid=None,
                             strict_contract_valid=None, gbnf_valid=None, rust_preview=None,
                             plan={k: None for k in PLAN_FIELDS}, exact_exposed_reference_agreement=None,
                             semantic_ambiguity=None, source_evidence_sufficiency=None,
                             reference=None, latency_ms=None, runtime=None, resources=None))
    return dict(diagnostic_only=True, semantic_go=False, cases=rows, repeatability=None)


def resource_guard(rss, cfg):
    a.require(rss["samples"] > 0 and not rss["error"], "Diagnostic RSS monitor unavailable")
    a.require(rss["peak_kib"] <= cfg["engineering_gates_per_stage"]["sampled_concurrent_process_tree_rss_gib_max"] * 2**20,
              "Diagnostic host RSS resource limit exceeded")


def validator_guard(checked):
    """Only known draft rejections can continue after trusted catalog preflight."""
    if checked["returncode"] == 0:
        return
    try:
        error = json.loads(checked["stderr"])
    except (ValueError, TypeError):
        error = {}
    code = error.get("detail", "").split(":", 1)[0]
    a.require(checked["returncode"] == 1 and error.get("status") == "error" and code in {
        "invalid_json", "invalid_contract", "invalid_catalog_reference", "deterministic_preflight_block"
    }, "Unexpected Rust/runtime integrity failure")


def observe(folder, out, state, runtime, rss, binary):
    cfg = a.config()
    audit = a.read(a.ROOT / "configs/native-one-hop-v1f-diagnostic.audit.json")["cases"]
    # Wait only for the first bounded monitor sample, before any diagnostic generation.
    until = time.monotonic() + 5
    while not rss["samples"] and not rss["error"] and time.monotonic() < until:
        time.sleep(.05)
    fixtures = a.read(folder / "operator-fixtures.json")
    for row in state["diagnostic"]["cases"]:
        cid, condition = row["case_id"], row["condition"]
        dest = out / "diagnostic" / condition / row["name"]
        dest.mkdir(parents=True)
        row.update(semantic_ambiguity=audit[cid]["ambiguity"],
                   source_evidence_sufficiency=audit[cid]["source_evidence_sufficiency"],
                   review_origin="AI investigator preregistration; independent human review pending")
        started = time.monotonic()
        before = dict(rss)
        generations_before = runtime.generation_attempts
        try:
            a.verify_freeze(folder, binary)
            resource_guard(rss, cfg)
            context = a.read(folder / "contexts" / f"{cid}-{condition}.json")
            a.dump(dest / "context.json", context)
            # Validate trusted source/catalog separately so a source failure cannot masquerade as a draft rejection.
            trusted = dest / "trusted-preflight"
            trusted.mkdir()
            a.dump(trusted / "context.json", context)
            a.dump(trusted / "proposal.txt", dict(version="nl-ask-draft-v1", status="unsupported", rationale="Host catalog preflight"))
            checked = a.preview_raw(context, trusted / "proposal.txt", trusted, fixtures[cid], binary)
            a.require(checked["returncode"] == 0, "Trusted source/catalog preflight failed")
            row["status"] = "attempting"
            row["runtime"] = runtime.generate(context, dest)
            raw = (dest / "proposal.txt").read_bytes()
            draft = strict_draft(raw)
            try:
                parsed = json.loads(raw)
                row["json_valid"] = True
            except (ValueError, UnicodeDecodeError):
                parsed = None
                row["json_valid"] = False
            row.update(raw_output=raw.decode("utf-8", errors="replace"), raw_base64=base64.b64encode(raw).decode(),
                       raw_sha256=hashlib.sha256(raw).hexdigest(), strict_contract_valid=draft is not None,
                       model_origin_status=parsed.get("status") if isinstance(parsed, dict) else None,
                       plan={k: parsed.get(k) if isinstance(parsed, dict) else None for k in PLAN_FIELDS})
            checked = a.preview_raw(context, dest / "proposal.txt", dest, fixtures[cid], binary)
            row["rust_preview"] = checked
            row["reference"] = a.semantic_outcome(cid, dest / "proposal.txt", checked)
            ref = row["reference"]
            row["exact_exposed_reference_agreement"] = bool(draft and ref["model_status"] == ref["expected_status"] and all(ref["field_agreement"].values()))
            row["status"] = "validator_rejection" if checked["returncode"] else "reference_match" if row["exact_exposed_reference_agreement"] else "model_semantic_failure"
            validator_guard(checked)
            row["gbnf_valid"] = a.grammar_check(raw.decode("utf-8"), context, dest)
            a.require(row["gbnf_valid"], "Constrained output violates native grammar; runtime integrity failure")
            a.require("PRIVATE_CANARY" not in row["raw_output"], "Authorization violation: private canary emitted")
            a.verify_freeze(folder, binary)
            resource_guard(rss, cfg)
            if row["name"] == "repeat-1":
                pair = [out / "diagnostic/oracle" / f"repeat-{i}" for i in range(2)]
                measured = repeatability([(p / "proposal.txt").read_bytes() for p in pair])
                state["diagnostic"]["repeatability"] = measured
                for name in ["prompt.txt", "completion-request.json"]:
                    equal = (pair[0] / name).read_bytes() == (pair[1] / name).read_bytes()
                    measured[name + "_equal"] = equal
                    a.require(equal, "Diagnostic repeat prompt/request integrity mismatch")
        except BaseException as error:
            row.update(observation_before_abort=row["status"], status="fatal_failure", error=type(error).__name__ + ": " + str(error))
            # Preserve partial raw bytes and independently reject them, even on a runtime abort.
            raw_path = dest / "proposal.txt"
            if raw_path.exists() and row["raw_base64"] is None:
                raw = raw_path.read_bytes()
                row.update(raw_base64=base64.b64encode(raw).decode(), raw_output=raw.decode("utf-8", errors="replace"),
                           raw_sha256=hashlib.sha256(raw).hexdigest())
                row["rust_preview"] = a.preview_raw(context, raw_path, dest, fixtures[cid], binary)
            raise
        finally:
            row.update(generation_attempted=runtime.generation_attempts > generations_before,
                       latency_ms=(time.monotonic() - started) * 1000,
                       resources=dict(before=before, after=dict(rss), scope="sampled process-tree run peak to date; not a per-case peak"))
            a.dump(dest / "observation.json", row)
    state["status"] = "completed_diagnostic"


def finish(state):
    diag = state["diagnostic"]
    for row in diag["cases"]:
        if row["status"] == "unattempted":
            row["reason"] = state["status"]
    diag["attempted"] = sum(r["generation_attempted"] for r in diag["cases"])
    diag["completed"] = sum(r["status"] in {"reference_match", "model_semantic_failure", "validator_rejection"} for r in diag["cases"])
    diag["denominator"] = len(diag["cases"])
    diag["finished_at"] = datetime.now(timezone.utc).isoformat()
    state.update(decision="INCONCLUSIVE_REVISE", controls_passed=False, smoke_passed=False)
