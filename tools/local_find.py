#!/usr/bin/env python3
"""Operator-started, offline Find pilot. Python standard library + the Rust CLI only."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import socketserver
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "tools" / "local_find_ui"
MAX_REQUEST = 16 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
ROLES = ("entity", "predicate", "class")
SESSION_SECONDS = 15 * 60
REVIEW_SECONDS = 2 * 60
XSD = "http://www.w3.org/2001/XMLSchema#"
LITERAL_TYPES = {XSD + t for t in ("string", "boolean", "integer", "decimal", "double", "date", "dateTime")}
LITERAL_TYPES.add("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString")
ERROR = {"error": "Request unavailable. Check selection or restart with a valid operator bundle."}


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    with path.open("rb") as file:
        return "sha256:" + hashlib.file_digest(file, "sha256").hexdigest()


def read(path: Path, limit: int) -> bytes:
    with path.open("rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Input limit")
    return data


class Bundle:
    """Freeze trusted inputs; never use browser-supplied filenames or commands."""

    def __init__(self, binary: Path, rdf: Path, fmt: str, policy: Path, scope: Path,
                 config: Path, index: Path | None = None, roles: tuple = ROLES):
        self.temp = tempfile.TemporaryDirectory(prefix="verity-find-")
        self.directory = Path(self.temp.name)
        self.tab = None
        self.pending = None
        self.selection = None
        self.find_entities = set()
        try:
            if not roles or len(set(roles)) != len(roles) or any(r not in ROLES for r in roles):
                raise ValueError("Roles")
            self.roles = roles
            self.binary = binary.resolve(strict=True)
            self.originals = {}
            paths = []
            for i, (path, limit) in enumerate([(rdf, 16 * 1024 * 1024), (policy, MAX_REQUEST),
                                              (scope, MAX_REQUEST), (config, 2 * 1024 * 1024)]
                                             + ([(index, 64 * 1024 * 1024)] if index else [])):
                path = path.resolve(strict=True)
                data = read(path, limit)
                self.originals[path] = (digest(data), limit)
                copy = self.directory / str(i)
                copy.write_bytes(data)
                copy.chmod(0o600)
                paths.append(str(copy))
            self.common = [paths[0], fmt, *paths[1:4]]
            self.index = paths[4:]
            self.scope = json.loads(Path(paths[2]).read_bytes())
            self.policy = json.loads(Path(paths[1]).read_bytes())
            # Existing core validates scope, policy, config, snapshot and any persisted index.
            built = self.invoke("index-inspect" if index else "index-build", self.index,
                                limit=64 * 1024 * 1024)
            self.snapshot = built["manifest"]["snapshot_id"]
            self.resource_roles = {g: {iri: doc["roles"] for iri, doc in value["documents"].items()}
                                   for g, value in built["graphs"].items()}
            self.documents = {g: value["documents"] for g, value in built["graphs"].items()}
            self.catalogs = {}
            for graph in self.scope:
                with tempfile.NamedTemporaryFile(dir=self.directory) as file:
                    file.write(json.dumps([graph]).encode())
                    file.flush()
                    self.catalogs[graph] = self.invoke("catalog", [file.name])
            self.page_limit = min(50, self.policy["max_rows"], self.policy["max_evidence"])
            if not self.page_limit:
                raise ValueError("Evidence policy")
            self.receipt = {
                "version": 1, "transport": "loopback-http-v1", "backend": "bm25-only",
                "snapshot_id": self.snapshot,
                "policy_hash": built["manifest"]["policy_hash"],
                "config_hash": built["manifest"]["config_hash"],
                "index_revision": built["manifest"]["index_revision"],
                "binary_sha256": file_digest(self.binary),
                "adapter_sha256": digest(Path(__file__).read_bytes()),
                "assets": {p.name: digest(p.read_bytes()) for p in sorted(ASSETS.iterdir())},
            }
        except Exception:
            self.close()
            raise

    def close(self):
        self.temp.cleanup()

    def current(self):
        # Changes revoke the session; requests always execute against private frozen copies.
        if any(digest(read(p, limit)) != expected
               for p, (expected, limit) in self.originals.items()):
            self.tab = self.pending = None
            raise ValueError("Stale operator bundle")
        if file_digest(self.binary) != self.receipt["binary_sha256"]:
            self.tab = self.pending = None
            raise ValueError("Stale executable")

    def invoke(self, command: str, tail: list, limit: int = MAX_RESPONSE, approval=None):
        common = self.common[:3] if command in ("catalog", "ask-preview", "ask") else self.common
        with tempfile.TemporaryFile(dir=self.directory) as output:
            subprocess.run([str(self.binary), command, *common, *tail],
                           input=(f"approve {approval}\n" if approval else "").encode(),
                           stdout=output, stderr=subprocess.DEVNULL,
                           check=True, timeout=45)
            output.seek(0)
            data = output.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Output limit")
        if command == "ask":
            # The existing CLI emits a fresh preview then an outcome; preserve both.
            decoder = json.JSONDecoder()
            preview, end = decoder.raw_decode(data.decode())
            return preview, json.loads(data.decode()[end:])
        return json.loads(data)

    def ask(self, request, approval=None):
        with tempfile.NamedTemporaryFile(dir=self.directory) as file:
            file.write(json.dumps(request, ensure_ascii=True).encode())
            file.flush()
            return self.invoke("ask" if approval else "ask-preview", [file.name], approval=approval)

    def choices(self):
        choices = []
        for graph, catalog in self.catalogs.items():
            for predicate, profile in catalog["profiles"].get(graph, {}).items():
                choices.append({"graph": graph, "predicate": predicate,
                                "labels": catalog["entries"][predicate]["labels"],
                                "document": self.documents[graph].get(predicate),
                                "object_types": profile["object_types"], "ill_typed": profile["ill_typed"]})
        return choices

    def api(self, route: str, request: dict, tab=None):
        self.current()
        if route == "/api/session" and request == {}:
            self.tab = secrets.token_hex(32)
            self.expires = time.monotonic() + SESSION_SECONDS
            self.pending = self.selection = None
            self.find_entities.clear()
            return {"scope": self.scope, "roles": self.roles, "snapshot_id": self.snapshot,
                    "page_limit": self.page_limit, "receipt": self.receipt, "tab": self.tab,
                    "session_seconds": SESSION_SECONDS}
        if (not isinstance(tab, str) or not self.tab or not hmac.compare_digest(tab, self.tab)
                or time.monotonic() >= self.expires):
            self.pending = None
            raise ValueError("Expired or stale tab")
        if not isinstance(request, dict):
            raise ValueError("Object required")
        if route == "/api/ask-confirm":
            pending, self.pending = self.pending, None  # Consume before any validation or execution.
            if (set(request) != {"token", "decision"} or not pending
                    or not isinstance(request["token"], str)
                    or not hmac.compare_digest(request["token"], pending["token"])
                    or time.monotonic() >= pending["expires"]):
                raise ValueError("Decision")
            if request["decision"] == "cancel":
                return {"status": "cancelled"}
            if request["decision"] != "approve":
                raise ValueError("Approval required")
            # Rust independently rebuilds/authorizes now, then again inside execute_confirmed_ask.
            if self.ask(pending["request"]) != pending["preview"]:
                raise ValueError("Changed plan")
            self.current()
            if time.monotonic() >= min(self.expires, pending["expires"]):
                raise ValueError("Expired decision")
            fresh, outcome = self.ask(pending["request"], pending["preview"]["approval_id"])
            self.current()
            if fresh != pending["preview"] or outcome["status"] != "executed":
                raise ValueError("Changed plan")
            return {"outcome": outcome, "sources": pending["sources"]}
        self.pending = None
        if route == "/api/ask-cancel" and request == {}:
            return {"status": "cancelled"}
        if route == "/api/ask-catalog" and request == {}:
            if not self.selection or not {"entity", "predicate"}.issubset(self.roles):
                raise ValueError("Select a Find entity")
            return {"selection": self.selection, "choices": self.choices(),
                    "max_rows": self.policy["max_rows"], "max_evidence": self.policy["max_evidence"],
                    "timeout_ms": self.policy["timeout_ms"], "snapshot_id": self.snapshot}
        if route == "/api/ask-preview":
            template = request["template"]
            if (not self.selection or not {"entity", "predicate"}.issubset(self.roles)
                    or template["start"] != self.selection["iri"]
                    or template["steps"][0]["graph"] != self.selection["graph"]):
                raise ValueError("Select a Find entity")
            for step in template["steps"]:
                if (step["graph"] not in self.scope
                        or step["predicate"] not in self.catalogs[step["graph"]]["profiles"][step["graph"]]):
                    raise ValueError("Predicate")
            if template.get("filter") is not None:
                step = template["steps"][-1]
                datatype = template["filter"]["value"]["datatype"]
                if (step["direction"] != "forward" or datatype not in LITERAL_TYPES
                        or datatype not in self.catalogs[step["graph"]]["profiles"][step["graph"]][step["predicate"]]["object_types"]):
                    raise ValueError("Exact observed datatype required")
            preview = self.ask(request)
            self.current()
            if time.monotonic() >= self.expires:
                raise ValueError("Expired session")
            token = secrets.token_hex(32)
            sources = {g: json.loads(Path(self.common[4]).read_bytes())["graphs"][g]
                       for g in request["scope"]}
            self.pending = {"token": token, "expires": time.monotonic() + REVIEW_SECONDS,
                            "request": json.loads(json.dumps(request)), "preview": preview, "sources": sources}
            return {"preview": preview, "token": token, "review_seconds": REVIEW_SECONDS,
                    "sources": sources}
        scope = request.get("scope")
        if (not isinstance(scope, list) or not scope or any(g not in self.scope for g in scope)
                or len(set(scope)) != len(scope)):
            raise ValueError("Scope")
        if route == "/api/find":
            self.selection = None
            self.find_entities.clear()
            if set(request) != {"query", "scope", "role", "limit"}:
                raise ValueError("Fields")
            if request["role"] not in self.roles:
                raise ValueError("Role")
            command = "find"
        elif route == "/api/entity":
            self.selection = None
            if set(request) != {"snapshot_id", "scope", "iri", "direction", "offset", "limit"}:
                raise ValueError("Fields")
            # Every navigation remains graph-qualified, including deliberate edge selections.
            if len(scope) != 1:
                raise ValueError("Select one graph")
            iri = request["iri"]
            if not isinstance(iri, str):
                raise ValueError("IRI")
            known_roles = self.resource_roles[scope[0]].get(iri, [])
            if not any(role in self.roles for role in known_roles):
                # Reuse core's no-match result, without echoing unknown/denied identifiers.
                request = dict(request, iri="urn:verity:unavailable:" + secrets.token_hex(32))
            command = "entity"
        else:
            raise ValueError("Route")
        with tempfile.NamedTemporaryFile(dir=self.directory) as file:
            file.write(json.dumps(request, ensure_ascii=True).encode())
            file.flush()
            result = self.invoke(command, [file.name, *self.index])
        # A concurrent edit revokes even the result of an already-running request.
        self.current()
        if route == "/api/find" and request["role"] == "entity":
            self.find_entities = {(hit["iri"], hit["graph"]) for hit in result["hits"]}
        if (route == "/api/entity" and result["iri"]
                and (result["iri"], scope[0]) in self.find_entities):
            self.selection = {"iri": result["iri"], "graph": scope[0]}
        return result


class Handler(socketserver.BaseRequestHandler):
    """One bounded HTTP/1.1 request per connection; no uploads, proxying or keepalive."""

    def handle(self):
        try:
            self.deadline = time.monotonic() + 5
            data = bytearray()
            while b"\r\n\r\n" not in data:
                data.extend(self.receive(1))
                if len(data) > MAX_REQUEST:
                    raise ValueError("Headers too large")
            lines = data[:-4].decode("ascii").split("\r\n")
            method, route, version = lines[0].split(" ")
            if version != "HTTP/1.1":
                raise ValueError("HTTP version")
            headers = {}
            for line in lines[1:]:
                name, value = line.split(":", 1)
                name = name.lower()
                if name in headers or not name or any(c not in "abcdefghijklmnopqrstuvwxyz-" for c in name):
                    raise ValueError("Header")
                headers[name] = value.strip()
            if (headers.get("host") != self.server.authority or "transfer-encoding" in headers
                    or headers.get("sec-fetch-site", "none") not in ("none", "same-origin")):
                raise ValueError("Origin")
            origin = headers.get("origin")
            if origin is not None and origin != self.server.origin:
                raise ValueError("Origin")
            length = headers.get("content-length", "0")
            if not length.isascii() or not length.isdecimal() or int(length) > MAX_REQUEST:
                raise ValueError("Content length")
            length = int(length)
            if method == "GET" and length == 0 and route in self.server.assets:
                body, mime = self.server.assets[route]
                self.respond(200, body, mime)
                return
            if (method != "POST" or origin != self.server.origin
                    or headers.get("content-type") != "application/json"
                    or not hmac.compare_digest(headers.get("authorization", ""),
                                               "Bearer " + self.server.credential)):
                raise ValueError("Authentication")
            body = bytearray()
            while len(body) < length:
                body.extend(self.receive(length - len(body)))
            request = json.loads(body)
            result = self.server.bundle.api(route, request, headers.get("x-verity-tab"))
            encoded = json.dumps(result, ensure_ascii=True, allow_nan=False).encode()
            if len(encoded) > MAX_RESPONSE:
                raise ValueError("Output limit")
            self.respond(200, encoded, "application/json")
        except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError, subprocess.SubprocessError):
            self.server.bundle.pending = None
            self.respond(400, json.dumps(ERROR).encode(), "application/json")

    def receive(self, size):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Deadline")
        self.request.settimeout(remaining)
        data = self.request.recv(size)
        if not data:
            raise ValueError("Disconnected")
        return data

    def respond(self, status, body, mime):
        headers = (
            f"HTTP/1.1 {status} {'OK' if status == 200 else 'Bad Request'}\r\n"
            f"Content-Type: {mime}; charset=utf-8\r\nContent-Length: {len(body)}\r\n"
            "Connection: close\r\nCache-Control: no-store\r\nReferrer-Policy: no-referrer\r\n"
            "X-Content-Type-Options: nosniff\r\nX-Frame-Options: DENY\r\n"
            "Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'\r\n\r\n"
        ).encode()
        try:
            self.request.sendall(headers + body)
        except OSError:
            pass


class Server(socketserver.TCPServer):
    allow_reuse_address = False

    def __init__(self, bundle: Bundle, host: str = "127.0.0.1", port: int = 0):
        # Reject names, wildcards and other 127/8 aliases: only these deliberate binds.
        if host not in ("127.0.0.1", "::1") or not ipaddress.ip_address(host).is_loopback:
            raise ValueError("Only 127.0.0.1 and ::1 binds are allowed")
        self.address_family = socket.AF_INET6 if host == "::1" else socket.AF_INET
        self.bundle = bundle
        self.credential = secrets.token_hex(32)
        self.assets = {route: ((ASSETS / name).read_bytes(), mime) for route, name, mime in (
            ("/", "index.html", "text/html"), ("/app.js", "app.js", "text/javascript"),
            ("/style.css", "style.css", "text/css"))}
        super().__init__((host, port), Handler)
        address = f"[{host}]" if host == "::1" else host
        self.authority = f"{address}:{self.server_address[1]}"
        self.origin = "http://" + self.authority

    @property
    def url(self):
        return self.origin + "/#" + self.credential


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/debug/verity")
    parser.add_argument("--rdf", type=Path, default=ROOT / "data/wikidata/snapshot.nq")
    parser.add_argument("--format", choices=("nquads", "trig", "turtle"), default="nquads")
    for name in ("policy", "scope", "config"):
        default = "discovery" if name == "config" else name
        parser.add_argument("--" + name, type=Path, default=ROOT / f"data/wikidata/{default}.json")
    parser.add_argument("--index", type=Path)
    parser.add_argument("--roles", nargs="+", choices=ROLES, default=ROLES)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    bundle = None
    try:
        bundle = Bundle(args.binary, args.rdf, args.format, args.policy, args.scope,
                        args.config, args.index, tuple(args.roles))
        with Server(bundle, args.host, args.port) as server:
            print("Local Find pilot; keep this session URL private. Stop with Ctrl-C.", flush=True)
            print(server.url, flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("Cannot start Find. Build the CLI and check the trusted operator bundle/bind.")
        return 1
    finally:
        if bundle:
            bundle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
