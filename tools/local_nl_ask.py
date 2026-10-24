#!/usr/bin/env python3
"""Experimental loopback NL Ask boundary; live inference is blocked by #74.

Only --saved-drafts-demo enables fixture proposals, never natural-language inference.
"""
from __future__ import annotations

import argparse
import hmac
import json
from pathlib import Path
import secrets
import select
import subprocess
import tempfile
import time

import local_find as find

ROOT = find.ROOT
ASSETS = Path(__file__).with_name("local_nl_ask_ui_v1")
PREFIX = "/api/nl-ask-v1/"
BLOCKER = ("Live model unavailable: #74 stopped before inference and has no validated "
           "nl-ask-draft-v1 runtime. No model is loaded. Use Find expert mode if useful.")


def table(packet, limit):
    """Packet-local numeric aliases for #72; never resolve IDs against the full catalog."""
    graphs = [{"id": i, "iri": g} for i, g in enumerate(packet["request"]["scope"], 1)]
    graph_ids = {g["iri"]: g["id"] for g in graphs}
    result = dict(snapshot_id=packet["request"]["snapshot_id"], graphs=graphs,
                  resolved_start=None, blocked=False, limit=limit)
    for collection in ("entities", "predicates"):
        result[collection] = [{"id": i, "graph": graph_ids[c["graph"]], "iri": c["iri"]}
                              for i, c in enumerate(packet[collection]["candidates"], 1)]
    return result


class Bundle(find.Bundle):
    def __init__(self, *args, saved_drafts_demo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposal = None
        self.connected = lambda: False
        self.demo = saved_drafts_demo is not None
        self.replays = []
        try:
            if self.demo:
                path = saved_drafts_demo.resolve(strict=True)
                raw = find.read(path, 1024 * 1024)
                record = json.loads(raw)
                if set(record) != {"version", "cases"} or record["version"] != "nl-ask-demo-v1":
                    raise ValueError("Demo version")
                self.replays = record["cases"]
                if not isinstance(self.replays, list) or len(self.replays) > 100:
                    raise ValueError("Demo cases")
                identities = set()
                for case in self.replays:
                    if (set(case) != {"question", "language", "packet_id", "raw_draft"}
                            or any(not isinstance(v, str) for v in case.values())
                            or len(case["raw_draft"].encode()) > 16384):
                        raise ValueError("Demo case")
                    key = (case["question"], case["language"])
                    if key in identities:
                        raise ValueError("Duplicate demo question")
                    identities.add(key)
                self.originals[path] = (find.digest(raw), 1024 * 1024)
            self.budget = dict(per_role_top_k=min(20, self.policy["max_rows"]), max_packet_bytes=1024 * 1024,
                               texts_per_candidate=8, max_text_bytes=2048,
                               evidence_per_page=min(3, self.policy["max_evidence"]),
                               max_source_bytes=4096)
        except Exception:
            self.close()
            raise

    def packet(self, question, language, saved=None):
        request = dict(question=question, language=language, snapshot_id=self.snapshot,
                       index_revision=self.receipt["index_revision"], scope=self.scope)
        return self.json_call("vocabulary-replay" if saved else "vocabulary",
                              [request, self.budget] + ([saved] if saved else []))

    def json_call(self, command, values, unresolved=False):
        paths = []
        for i, value in enumerate(values):
            path = self.directory / f"nl-{i}.json"
            path.write_bytes(value.encode() if isinstance(value, str)
                             else json.dumps(value, ensure_ascii=True).encode())
            path.chmod(0o600)
            paths.append(str(path))
        if not unresolved:
            return self.invoke(command, paths)
        # Inspect only the bounded Rust error code; malformed drafts are not clarification.
        with tempfile.TemporaryFile(dir=self.directory) as output, tempfile.TemporaryFile(dir=self.directory) as errors:
            result = subprocess.run([str(self.binary), command, *self.common, *paths],
                                    stdin=subprocess.DEVNULL, stdout=output, stderr=errors, timeout=45)
            output.seek(0)
            errors.seek(0)
            data = output.read(find.MAX_RESPONSE + 1)
            error = errors.read(find.MAX_REQUEST + 1)
        if len(data) > find.MAX_RESPONSE or len(error) > find.MAX_REQUEST:
            raise ValueError("Rust output limit")
        if result.returncode:
            if json.loads(error).get("detail", "").startswith("deterministic_preflight_block:"):
                return None
            raise ValueError("Invalid draft or packet reference")
        return json.loads(data)

    def resolve(self, proposal, start):
        packet = proposal["packet"]
        if self.packet(packet["request"]["question"], packet["request"]["language"], packet) != packet:
            raise ValueError("Changed packet")
        selection = table(packet, min(20, self.policy["max_rows"]))
        if start is not None and (type(start) is not int
                                   or not any(r["id"] == start for r in selection["entities"])):
            raise ValueError("Choose an original packet entity")
        selection["resolved_start"] = start
        return self.json_call("nl-ask-preview", [selection, proposal["raw_draft"]], unresolved=start is None)

    def api(self, route, request, tab=None):
        self.current()
        if route == "/api/session":
            self.proposal = None
            result = super().api(route, request, tab)
            result.update(version="local-nl-ask-v1", runtime="saved_draft_demo" if self.demo else "unavailable",
                          runtime_message=BLOCKER, demo_cases=[{k: c[k] for k in ("question", "language")}
                                                               for c in self.replays])
            return result
        if (not isinstance(tab, str) or not self.tab or not hmac.compare_digest(tab, self.tab)
                or time.monotonic() >= self.expires):
            self.pending = self.proposal = None
            raise ValueError("Expired or stale tab")
        pending, self.pending = self.pending, None  # Every action invalidates approval.
        if not isinstance(request, dict):
            raise ValueError("Object required")
        if route == PREFIX + "unreview" and request == {}:
            return {"status": "review_cancelled"}
        if route == PREFIX + "confirm":
            self.proposal = None
            if (set(request) != {"token", "decision"} or not pending
                    or not isinstance(request["token"], str)
                    or not hmac.compare_digest(request["token"], pending["token"])
                    or time.monotonic() >= pending["expires"]):
                raise ValueError("Stale or consumed approval")
            if request["decision"] == "cancel":
                return {"status": "cancelled"}
            if request["decision"] != "approve":
                raise ValueError("Explicit approval required")
            # Revalidate #73 packet + #72 resolver + complete Rust preview before the only execute call.
            fresh = self.resolve(pending["proposal"], pending["start"])
            if fresh != pending["resolved"]:
                raise ValueError("Changed interpretation")
            self.current()
            if (time.monotonic() >= min(self.expires, pending["expires"])
                    or not self.connected()):
                raise ValueError("Expired or disconnected review")
            preview, outcome = self.ask(fresh["request"], fresh["preview"]["approval_id"])
            self.current()
            if preview != fresh["preview"] or outcome["status"] != "executed":
                raise ValueError("Changed plan")
            result = outcome["result"]
            step = fresh["request"]["template"]["steps"][0]
            answers = []
            for row in result["bindings"]:
                value = row["step1"]
                start_term = {"kind": "iri", "value": fresh["request"]["template"]["start"]}
                subject, obj = (start_term, value) if step["direction"] == "forward" else (value, start_term)
                witnesses = [s for s in result["evidence"] if s["subject"] == subject and s["object"] == obj
                             and s["predicate"] == {"kind": "iri", "value": step["predicate"]}
                             and s["source_graph"] == {"kind": "iri", "value": step["graph"]}]
                document = self.documents[step["graph"]].get(value["value"], {}) if value["kind"] == "iri" else {}
                labels = [t for t in document.get("texts", []) if t["field"] == "label"][:8]
                answers.append(dict(value=value, observed_labels=labels, source_triples=witnesses,
                                    evidence_complete=bool(witnesses)))
            return dict(status="executed", outcome=outcome, answers=answers,
                        provenance={**pending["provenance"], "operator_confirmation": {
                            "decision": "approve", "approval_id": preview["approval_id"],
                            "resolved_start": pending["start"], "single_use": True}},
                        sources=pending["proposal"]["packet"]["sources"])
        if route == PREFIX + "preview":
            proposal = self.proposal
            if (set(request) != {"proposal_token", "start"} or not proposal
                    or type(request["start"]) is not int
                    or not isinstance(request["proposal_token"], str)
                    or not hmac.compare_digest(request["proposal_token"], proposal["token"])
                    or time.monotonic() >= proposal["expires"]):
                self.proposal = None
                raise ValueError("Stale proposal")
            resolved = self.resolve(proposal, request["start"])
            if resolved["status"] != "candidate":
                return resolved
            self.current()
            if time.monotonic() >= min(self.expires, proposal["expires"]):
                raise ValueError("Expired preview")
            token = secrets.token_hex(32)
            provenance = dict(proposal_origin="saved_draft_demo", inference_performed=False,
                              original_question=proposal["packet"]["request"]["question"],
                              language=proposal["packet"]["request"]["language"],
                              packet=proposal["packet"], table=table(proposal["packet"], min(20, self.policy["max_rows"])),
                              draft_version="nl-ask-draft-v1", raw_draft=proposal["raw_draft"],
                              operator_confirmation=None)
            self.pending = dict(token=token, expires=time.monotonic() + find.REVIEW_SECONDS,
                                proposal=proposal, start=request["start"], resolved=resolved, provenance=provenance)
            return dict(status="awaiting_confirmation", resolved=resolved, token=token,
                        review_seconds=min(find.REVIEW_SECONDS, max(0, self.expires - time.monotonic())),
                        sources=proposal["packet"]["sources"], provenance=provenance)
        self.proposal = None
        if route == PREFIX + "cancel" and request == {}:
            return {"status": "cancelled"}
        if route == "/api/find":
            return super().api(route, request, tab)
        if route != PREFIX + "question" or set(request) != {"question", "language"}:
            raise ValueError("Route or fields")
        if (not isinstance(request["question"], str) or not request["question"].strip()
                or len(request["question"].encode()) > 4096
                or request["language"] not in ("en", "no", "nb", "nn")):
            raise ValueError("Question or language")
        if not self.demo:
            return dict(status="model_unavailable", message=BLOCKER)
        packet = self.packet(request["question"], request["language"])
        case = next((c for c in self.replays if c["question"] == request["question"]
                     and c["language"] == request["language"]), None)
        if case is None:
            return dict(status="demo_question_unavailable",
                        message="No saved draft for this exact question/language. This demo does not infer new questions.")
        if packet["packet_id"] != case["packet_id"]:
            raise ValueError("Demo packet binding")
        proposal = dict(packet=packet, raw_draft=case["raw_draft"], token=secrets.token_hex(32),
                        expires=time.monotonic() + find.REVIEW_SECONDS)
        # Rust strictly decodes even candidate drafts; unresolved candidates must fail preflight.
        outcome = self.resolve(proposal, None)
        self.current()
        if time.monotonic() >= self.expires:
            raise ValueError("Expired session")
        if outcome is not None:
            return dict(status=outcome["status"], explanation=outcome["display_rationale"],
                        proposal_origin="saved_draft_demo", inference_performed=False)
        self.proposal = proposal
        return dict(status="choose_exact_start", proposal_token=proposal["token"], packet=packet,
                    table=table(packet, min(20, self.policy["max_rows"])), raw_draft=case["raw_draft"],
                    proposal_origin="saved_draft_demo", inference_performed=False)


class Handler(find.Handler):
    def handle(self):
        # A closed/half-closed connection cannot redeem approval after resolver preflight.
        self.server.bundle.connected = lambda: not select.select([self.request], [], [], 0)[0]
        try:
            super().handle()
        finally:
            self.server.bundle.connected = lambda: False


class Server(find.Server):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.RequestHandlerClass = Handler
        self.assets = {route: ((ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ("/", "index.html", "text/html"), ("/nl-ask-v1.js", "app.js", "text/javascript"),
            ("/style.css", "style.css", "text/css"))}
        self.bundle.receipt.update(ui_version="local-nl-ask-v1", backend="saved-draft-demo" if self.bundle.demo else "unavailable",
                                   adapter_sha256=find.file_digest(Path(__file__)),
                                   transport_adapter_sha256=find.file_digest(Path(find.__file__)),
                                   assets={route: find.digest(body) for route, (body, _) in self.assets.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/debug/verity")
    parser.add_argument("--rdf", type=Path, default=ROOT / "data/wikidata/snapshot.nq")
    parser.add_argument("--format", choices=("nquads", "trig", "turtle"), default="nquads")
    for name in ("policy", "scope", "config"):
        parser.add_argument("--" + name, type=Path, default=ROOT / f"data/wikidata/{'discovery' if name == 'config' else name}.json")
    parser.add_argument("--saved-drafts-demo", type=Path, help="Explicit opt-in to model-free replay, never live inference")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    bundle = None
    try:
        bundle = Bundle(args.binary, args.rdf, args.format, args.policy, args.scope, args.config,
                        saved_drafts_demo=args.saved_drafts_demo)
        with Server(bundle, args.host, args.port) as server:
            print("Experimental NL Ask; " + ("SAVED-DRAFT DEMO, no inference." if bundle.demo else BLOCKER), flush=True)
            print("Private session URL; stop with Ctrl-C.\n" + server.url, flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("Cannot start NL Ask. Build Rust and check the operator bundle, demo and loopback bind.")
        return 1
    finally:
        if bundle:
            bundle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
