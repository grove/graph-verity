#!/usr/bin/env python3
"""Local, document-only Ask UI over the existing BM25 and grounding contracts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat

import document_rag as documents
import grounded_rag as evidence
import local_cited_generation as generation
import local_find as find

ROOT = find.ROOT
ASSETS = Path(__file__).with_name("local_document_ask_ui")
PREFIX = "/api/document-ask/"
LANGUAGES = {"en", "nb"}
RESULT_LIMIT = 3
MAX_RESULT_BYTES = 1024 * 1024
MAX_RECEIPT_BYTES = 2 * 1024 * 1024


def _private_json(path: Path, limit: int) -> dict:
    """Read only operator-selected, owner-only regular files without following links."""
    require(path.is_absolute() and path.resolve(strict=True) == path,
            "Private result path must be absolute and canonical")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                and before.st_nlink == 1 and stat.S_IMODE(before.st_mode) in (0o400, 0o600)
                and 0 < before.st_size <= limit,
                "Private result file is not owner-only or exceeds its limit")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        require(len(raw) == before.st_size and len(raw) <= limit and
                all(getattr(before, key) == getattr(after, key) == getattr(current, key)
                    for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")),
                "Private result changed while reading")
    finally:
        os.close(fd)
    value = json.loads(raw)
    require(type(value) is dict, "Private result must be a JSON object")
    return value


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Bundle:
    """Fixed operator paths; browser requests cannot choose files or commands."""

    def __init__(self, manifest: Path, index: Path, scope: str,
                 runtime_registration: Path | None = None,
                 checked_result: Path | None = None,
                 checked_receipt: Path | None = None):
        self.manifest = manifest
        self.index = index
        self.scope = scope
        self.runtime_registration = runtime_registration
        self.checked_result = checked_result
        self.checked_receipt = checked_receipt
        self.pending = None  # Required by the shared local Find request handler.
        require(checked_result is not None or checked_receipt is None,
                "A native receipt requires its matching result")
        # Fail startup on an invalid or stale operator bundle; no passages are cached.
        documents.load_index(self.manifest, self.index, self.scope)

    def packet(self, request: dict) -> dict:
        require(type(request) is dict and set(request) == {"question", "language"},
                "Invalid Ask request")
        question, language = request["question"], request["language"]
        require(type(question) is str and question.strip() and
                len(question.encode("utf-8")) <= documents.MAX_QUERY and
                language in LANGUAGES, "Question or language is invalid")
        return evidence.retrieve(self.manifest, self.index, self.scope,
                                 question, language, RESULT_LIMIT)

    @staticmethod
    def source_only(packet: dict, reason: str, risk: dict | None = None) -> dict:
        view = evidence.fallback(packet, reason=reason)
        if risk is not None:
            view["grounding_risk"] = risk
        return {"packet": packet, "view": view, "execution": "none"}

    @staticmethod
    def unavailable(reason: str) -> dict:
        message = ("Source changed; passages and saved answers were withheld."
                   if reason == "source_changed" else
                   "The selected source could not be verified; no passage was returned.")
        return {"packet": None, "execution": "none", "view": {
            "status": "source_unavailable", "reason": reason, "answer": None,
            "model_invoked": False, "evidence": [], "message": message,
        }}

    def _native_or_saved_view(self, packet: dict) -> tuple[dict | None, str | None]:
        if self.checked_result is None:
            return None, None
        try:
            saved = _private_json(self.checked_result, MAX_RESULT_BYTES)
            require(set(saved) == {"packet", "view"}, "Invalid saved answer")
            if saved["packet"] != packet:
                return None, None
            view = saved["view"]
            require(type(view) is dict, "Invalid saved answer view")
            if view.get("status") == "checked_saved_output_only" and view.get("model_invoked") is False:
                candidate = {
                    "version": generation.VERSION, "status": "answer",
                    "language": packet["language"], "answer": view.get("answer"),
                    "citation_id": view.get("citation_id"),
                }
                checked = generation.check_answer(packet, candidate, actual_model=False)
                require(checked["status"] == "checked_saved_output_only",
                        "Saved replay did not pass source checks")
                return {"packet": packet, "view": checked, "execution": "saved_replay"}, None

            require(view.get("status") == "generated_checked_extractive" and
                    view.get("model_invoked") is True and
                    view.get("model_request_attempted") is True and
                    isinstance(view.get("run_authorization_id"), str) and
                    view.get("actual_model_attestation") ==
                    "separate_disk_process_endpoint_observations_only" and
                    self.checked_receipt is not None,
                    "Saved output is not a checked native result")
            receipt = _private_json(self.checked_receipt, MAX_RECEIPT_BYTES)
            validation = receipt.get("candidate_validation")
            require(receipt.get("version") == 2 and
                    receipt.get("transport_kind") == "native_http" and
                    receipt.get("model_request_attempted") is True and
                    receipt.get("request_send_attempted") is True and
                    receipt.get("sources_still_current") is True and
                    receipt.get("citation_check") == "exact_quote_and_citation_only" and
                    type(validation) is dict and
                    validation.get("complete_validator") == "passed" and
                    receipt.get("final_view") == view,
                    "Private receipt does not attest a checked native response")
            candidate = {
                "version": generation.VERSION, "status": "answer",
                "language": packet["language"], "answer": view.get("answer"),
                "citation_id": view.get("citation_id"),
            }
            checked = generation.check_answer(packet, candidate, actual_model=True)
            require(checked["status"] == "generated_checked_extractive",
                    "Native answer did not pass current source checks")
            return {"packet": packet, "view": checked, "execution": "native_authorized_cli"}, None
        except (OSError, ValueError, TypeError, KeyError, UnicodeError,
                json.JSONDecodeError):
            # No stale or unverifiable saved passage is returned to the browser.
            return None, "invalid_model_response"

    def api(self, route: str, request: dict, tab=None) -> dict:
        if route not in (PREFIX + "ask", PREFIX + "prepare"):
            raise ValueError("Route")
        try:
            packet = self.packet(request)
        except ValueError as error:
            if str(error) in ("Invalid Ask request", "Question or language is invalid"):
                raise
            return self.unavailable("source_changed" if "Source changed" in str(error)
                                    else "source_unavailable")
        except (OSError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
            return self.unavailable("source_unavailable")
        risk = evidence.assess_grounding_risk(packet)
        if not packet["document_evidence"]:
            return self.source_only(packet, "no_document_evidence", risk)
        if risk["classification"] != "CLEAR_SUPPORTED_CASE":
            return self.source_only(packet, risk["reason"], risk)

        if route.endswith("/prepare"):
            if self.runtime_registration is None:
                output = self.source_only(packet, "generation_not_authorized", risk)
                output["preparation"] = {"status": "unavailable",
                                         "reason": "model_registration_unavailable"}
                return output
            try:
                registration = generation.load_registration(self.runtime_registration)
                messages = generation.build_messages(packet)
                raw_request = generation.request_payload(registration, messages)
                host = generation.host_observation(registration)
                try:
                    generation.admit_host(registration, host)
                    host_status = {"status": "admitted"}
                except (ValueError, OSError, TypeError, KeyError):
                    host_status = {"status": "rejected",
                                   "reason": "host_preflight_not_satisfied"}
                result = {
                    "status": "prepared", "question": packet["question"],
                    "language": packet["language"], "document_scope": packet["document_scope"],
                    "packet_sha256": generation.fingerprint(packet),
                    "question_sha256": documents.sha(packet["question"].encode("utf-8")),
                    "request_sha256": documents.sha(raw_request),
                    "request": json.loads(raw_request),
                    "registration": {
                        "sha256": generation.fingerprint(registration),
                        "backend": registration["backend"],
                        "model_name": registration["model_name"],
                        "model_revision": registration["model_revision"],
                        "model_sha256": registration["model_sha256"],
                        "runtime_revision": registration["runtime_revision"],
                        "runtime_sha256": registration["runtime_sha256"],
                    },
                    "host_admission": host_status,
                    "authorization": {
                        "owner_approval_required": True, "owner_approved": False,
                        "single_use": True, "consumed": False,
                        "max_expiry_seconds": 86400, "recommended_expiry_seconds": 600,
                    },
                    "limits": {
                        "context_tokens": registration["context_tokens"],
                        "max_output_tokens": registration["max_output_tokens"],
                        "timeout_seconds": registration["timeout_seconds"],
                        "cpu_threads": registration["cpu_threads"],
                        "gpu_layers": registration["gpu_layers"],
                        "document_passages": len(packet["document_evidence"]),
                    },
                    "model_invoked": False,
                    "message": "Prepared only. No approval was created and no model request was sent.",
                }
                view = evidence.fallback(packet, reason="generation_not_authorized")
                view["grounding_risk"] = risk
                return {"packet": packet, "view": view,
                    "execution": "none", "preparation": result}
            except (OSError, ValueError, TypeError, KeyError, UnicodeError,
                    json.JSONDecodeError):
                output = self.source_only(packet, "model_unavailable", risk)
                output["preparation"] = {"status": "unavailable",
                                         "reason": "runtime_registration_unavailable"}
                return output

        if risk["classification"] == "CLEAR_SUPPORTED_CASE":
            checked, invalid_reason = self._native_or_saved_view(packet)
            if checked is not None:
                # Re-read source bytes immediately before returning any generated quote.
                try:
                    current = evidence.retrieve(self.manifest, self.index, self.scope,
                                                packet["question"], packet["language"],
                                                RESULT_LIMIT)
                except (OSError, ValueError, TypeError, KeyError, UnicodeError,
                        json.JSONDecodeError):
                    return self.unavailable("source_changed")
                if current != packet:
                    return self.unavailable("source_changed")
                return checked
            if invalid_reason:
                return self.source_only(packet, invalid_reason, risk)
        return self.source_only(packet, "generation_not_authorized", risk)


class Server(find.Server):
    def __init__(self, bundle: Bundle, host="127.0.0.1", port=0):
        super().__init__(bundle, host, port)
        self.assets = {route: ((ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ("/", "index.html", "text/html"),
            ("/app.js", "app.js", "text/javascript"),
            ("/style.css", "style.css", "text/css"),
        )}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Operator-selected document manifest")
    parser.add_argument("--index", type=Path, required=True,
                        help="Verified BM25 index for the selected manifest")
    parser.add_argument("--scope", required=True)
    parser.add_argument("--runtime-registration", type=Path,
                        help="Optional existing private local model registration; used only for request preparation")
    parser.add_argument("--checked-result", type=Path,
                        help="Optional private output from the existing local cited-generation CLI")
    parser.add_argument("--checked-receipt", type=Path,
                        help="Matching private CLI receipt; required with --checked-result for native status")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        bundle = Bundle(args.manifest, args.index, args.scope,
                        args.runtime_registration, args.checked_result,
                        args.checked_receipt)
        with Server(bundle, args.host, args.port) as server:
            print("Local document Ask; source-only by default. No model starts from this interface.", flush=True)
            print("Private session URL; stop with Ctrl-C.\n" + server.url, flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            json.JSONDecodeError):
        print("Cannot start document Ask. Check the selected manifest/index/scope and loopback bind.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
