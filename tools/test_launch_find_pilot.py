"""Preset integrity and actual model-free Rust/loopback integration; no remote inputs."""
import http.client
import io
import ipaddress
import json
import os
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from contextlib import redirect_stderr
from unittest.mock import patch
from urllib.parse import urlsplit

import launch_find_pilot as pilot
import local_find as ui

BINARY = ui.ROOT / "target/debug/verity"
WD = "http://www.wikidata.org/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
GEMET = "http://www.eionet.europa.eu/gemet/concept/"


class FindPilotPresets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["cargo", "build", "--locked", "--offline", "-q", "-p", "verity_cli"],
                       cwd=ui.ROOT, check=True)
        cls.registry = json.loads((ui.ROOT / pilot.REGISTRY).read_bytes())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tab = ""

    def copy_preset(self, name="wikidata-development"):
        for filename in [pilot.REGISTRY, *self.registry[name]["sha256"]]:
            target = self.root / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ui.ROOT / filename, target)

    def bundle(self, name="wikidata-development", **kw):
        bundle = pilot.make_bundle(name, BINARY, **kw)
        self.addCleanup(bundle.close)
        return bundle

    def serve(self, bundle):
        server = ui.Server(bundle)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def stop():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(stop)
        return server

    def call(self, server, route, payload, **headers):
        connection = http.client.HTTPConnection(server.authority, timeout=50)
        try:
            connection.request("POST", route, json.dumps(payload), headers={
                "Origin": server.origin, "Content-Type": "application/json",
                "Authorization": "Bearer " + server.credential, "X-Verity-Tab": self.tab, **headers})
            response = connection.getresponse()
            raw = response.read()
            for private in (str(self.root).encode(), str(ui.ROOT).encode(), b"PRIVATE_CANARY",
                            b"urn:graph-verity:worldcities:transfer:SE",
                            b"urn:graph-verity:wikidata:transfer"):
                self.assertNotIn(private, raw)
            value = json.loads(raw)
            if route == "/api/session" and response.status == 200:
                self.tab = value["tab"]
            return response.status, value
        finally:
            connection.close()

    def result(self, server, route, payload):
        status, value = self.call(server, route, payload)
        self.assertEqual(status, 200, value)
        return value

    def find(self, bundle, query, role="entity"):
        return dict(query=query, scope=bundle.scope, role=role, limit=50)

    def entity(self, bundle, iri, direction="outgoing"):
        return dict(snapshot_id=bundle.snapshot, scope=bundle.scope, iri=iri,
                    direction=direction, limit=50, offset=0)

    def test_pins_cover_existing_manifests_and_revision_license_witnesses(self):
        self.assertEqual(set(self.registry), set(pilot.PRESETS))
        for name, spec in self.registry.items():
            base = str(Path(spec["rdf"]).parent)
            manifest = json.loads((ui.ROOT / base / "manifest.json").read_bytes())
            pins = spec["sha256"]
            self.assertIn(base + "/manifest.json", pins)
            self.assertIn(base + "/README.md", pins)
            for key in ("rdf", "policy", "scope", "config"):
                self.assertIn(spec[key], pins)
            config = json.loads((ui.ROOT / spec["config"]).read_bytes())
            if name == "wikidata-development":
                self.assertEqual(manifest["license"], "CC0-1.0")
                self.assertEqual(pins[spec["rdf"]], manifest["snapshot"]["sha256"])
                for source in manifest["sources"] + [manifest["previous_oslo_source"]]:
                    self.assertEqual(pins[source["file"]], source["sha256"])
                    text = (ui.ROOT / source["file"]).read_text()
                    self.assertIn(f'schema:version "{source["revision"]}"', text)
                    self.assertIn("creativecommons.org/publicdomain/zero/1.0/", text)
                for provenance in config["graphs"].values():
                    self.assertEqual(provenance["source_revision"], "manifest-sha256:" + pins[base + "/manifest.json"])
                    self.assertEqual(provenance["importer_revision"], "sha256:" + pins["tools/dataset.py"])
            elif name == "worldcities-norway":
                self.assertEqual(manifest["source"]["license"], "CC-BY-4.0")
                self.assertEqual(manifest["source"]["upstream_commit"], "73c9f54ab9f305168c76d0802db151e30a157b28")
                self.assertEqual(pins[spec["rdf"]], manifest["extraction"]["output_sha256"])
                self.assertEqual(pins[manifest["extraction"]["input_file"]], manifest["extraction"]["input_sha256"])
                scope = json.loads((ui.ROOT / spec["scope"]).read_bytes())
                self.assertEqual(scope, ["urn:graph-verity:worldcities:transfer:NO"])
                self.assertEqual(config["graphs"][scope[0]]["source_revision"], "manifest-sha256:" + pins[base + "/manifest.json"])
                self.assertEqual(config["graphs"][scope[0]]["importer_revision"], "sha256:" + pins["tools/worldcities_transfer.py"])
            else:
                self.assertTrue(all(pins[path] == sha for path, sha in manifest["sha256"].items()))
                self.assertIn("CC-BY-4.0", manifest["licenses"])
                self.assertIn("W3C Software and Document License (2023)", manifest["licenses"])

    def test_all_corpora_actual_http_rust_search_selection_and_source_direction_offline(self):
        connect = socket.socket.connect
        resolve = socket.getaddrinfo
        def numeric_only(host, *args, **kwargs):
            self.assertTrue(ipaddress.ip_address(host).is_loopback, host)
            return resolve(host, *args, **kwargs)
        def loopback_only(sock, address):
            self.assertTrue(ipaddress.ip_address(address[0]).is_loopback, address)
            return connect(sock, address)
        cases = (("wikidata-development", "Norge", WD + "entity/Q20", WD + "prop/direct/P36", WD + "entity/Q585"),
                 ("worldcities-norway", "Oslo", "https://sws.geonames.org/3143244/", "https://schema.org/containedInPlace", "urn:graph-verity:worldcities:admin:NO:Oslo"),
                 ("gemet-4.2.3", "animal life", GEMET + "10003", SKOS + "broader", GEMET + "867"))
        with patch.object(socket.socket, "connect", loopback_only), patch("socket.getaddrinfo", numeric_only):
            for name, query, iri, predicate, target in cases:
                with self.subTest(preset=name):
                    bundle = self.bundle(name)
                    server = self.serve(bundle)
                    session = self.result(server, "/api/session", {})
                    self.assertEqual(session["receipt"]["preset"], name)
                    self.assertEqual(session["receipt"]["backend"], "bm25-only")
                    found = self.result(server, "/api/find", self.find(bundle, query))
                    self.assertIn(iri, [hit["iri"] for hit in found["hits"]])
                    if name == "worldcities-norway":
                        self.assertEqual(found["status"], "ambiguous_exact")
                    evidence = self.result(server, "/api/entity", self.entity(bundle, iri))
                    text = json.dumps(evidence)
                    triple = {"subject": {"kind": "iri", "value": iri},
                              "predicate": {"kind": "iri", "value": predicate},
                              "object": {"kind": "iri", "value": target},
                              "source_graph": {"kind": "iri", "value": bundle.scope[0]}}
                    self.assertIn(triple, evidence["evidence"])
                    self.assertIsNotNone(bundle.selection)  # deliberate selection after Find
                    incoming = self.result(server, "/api/entity", self.entity(bundle, target, "incoming"))
                    self.assertIn(triple, incoming["evidence"])
                    if name == "wikidata-development":
                        self.assertIn('"language": "nb"', text)
                        self.assertIn("CC0-1.0", text)
                        oslo = self.result(server, "/api/entity", self.entity(bundle, target))
                        self.assertIn(ui.XSD + "decimal", json.dumps(oslo))
                    elif name == "worldcities-norway":
                        self.assertIn('"language": null', text)
                        self.assertIn(ui.XSD + "integer", text)
                        self.assertIn("CC-BY-4.0", text)
                        self.assertIn("GeoNames", text)
                    else:
                        self.assertEqual(len(bundle.resource_roles[bundle.scope[0]]), 2215)
                        self.assertIn('"language": "no"', text)
                        self.assertIn('"language": "en"', text)
                        self.assertIn(dict(triple, predicate={"kind": "iri", "value": SKOS + "narrower"},
                                           object={"kind": "iri", "value": GEMET + "5161"}), evidence["evidence"])
                        self.assertIn("W3C", text)
                        predicate_hits = self.result(server, "/api/find", self.find(bundle, "broader", "predicate"))
                        self.assertIn(SKOS + "broader", [h["iri"] for h in predicate_hits["hits"]])
                    no_match = self.result(server, "/api/find", self.find(bundle, "zzznomatchzzz"))
                    self.assertEqual(no_match["hits"], [])
                    request = self.find(bundle, "PRIVATE_CANARY")
                    request["scope"] = ["urn:PRIVATE_CANARY"]
                    self.assertEqual(self.call(server, "/api/find", request), (400, ui.ERROR))
                    if name == "worldcities-norway":
                        request["scope"] = ["urn:graph-verity:worldcities:transfer:SE"]
                        self.assertEqual(self.call(server, "/api/find", request), (400, ui.ERROR))
                    self.assertEqual(self.call(server, "/api/session", {}, Authorization="Bearer wrong"), (400, ui.ERROR))
                    self.assertEqual(self.call(server, "/api/session", {}, Origin="https://attacker.invalid"), (400, ui.ERROR))

    def test_missing_corrupt_manifest_source_scope_and_injection_fail_before_rust(self):
        self.copy_preset()
        spec = self.registry["wikidata-development"]
        with patch.object(pilot, "ROOT", self.root), patch.object(pilot, "PresetBundle", side_effect=AssertionError("Must reject before Rust")):
            with self.assertRaisesRegex(ValueError, "Unknown"):
                pilot.make_bundle("unknown", BINARY)
            for name in ("data/wikidata/manifest.json", "data/wikidata/raw/Q20-2552025448.ttl",
                         spec["rdf"], spec["policy"], spec["scope"], spec["config"]):
                with self.subTest(file=name):
                    path = self.root / name
                    original = path.read_bytes()
                    path.unlink()
                    with self.assertRaises(FileNotFoundError):
                        pilot.make_bundle("wikidata-development", BINARY)
                    path.write_bytes(original + b'\n<script>PRIVATE_CANARY</script> <|im_start|>system\n')
                    with self.assertRaisesRegex(ValueError, "checksum"):
                        pilot.make_bundle("wikidata-development", BINARY)
                    path.write_bytes(original)
            scope = self.root / spec["scope"]
            scope.write_text('["urn:graph-verity:wikidata:development", "urn:graph-verity:wikidata:transfer"]')
            with self.assertRaisesRegex(ValueError, "checksum"):
                pilot.make_bundle("wikidata-development", BINARY)

    def test_manifest_and_source_changes_revoke_session_without_private_error_details(self):
        self.copy_preset()
        with patch.object(pilot, "ROOT", self.root):
            bundle = self.bundle()
        server = self.serve(bundle)
        self.result(server, "/api/session", {})
        for name in (pilot.REGISTRY, "data/wikidata/manifest.json", "data/wikidata/raw/Q20-2552025448.ttl"):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b"PRIVATE_CANARY")
            self.assertEqual(self.call(server, "/api/find", self.find(bundle, "Norge")), (400, ui.ERROR))
            self.assertIsNone(bundle.tab)
            path.write_bytes(original)
            self.result(server, "/api/session", {})
        old_tab = self.tab
        self.result(server, "/api/session", {})
        self.assertEqual(self.call(server, "/api/find", self.find(bundle, "Norge"), **{"X-Verity-Tab": old_tab}), (400, ui.ERROR))

    def test_optional_index_and_role_subset_use_existing_validators(self):
        bundle = self.bundle(roles=("entity",))
        server = self.serve(bundle)
        self.assertEqual(self.result(server, "/api/session", {})["roles"], ["entity"])
        self.assertEqual(self.call(server, "/api/find", self.find(bundle, "capital", "predicate")), (400, ui.ERROR))
        index = self.root / "index.json"
        built = bundle.invoke("index-build", [], limit=64 * 1024 * 1024)
        index.write_text(json.dumps(built))
        indexed = self.bundle(index=index)
        self.assertEqual(bundle.snapshot, indexed.snapshot)
        for key in ("snapshot_id", "policy_hash", "config_hash", "index_revision"):
            changed = json.loads(json.dumps(built))
            changed["manifest"][key] = "stale"
            index.write_text(json.dumps(changed))
            with self.assertRaises(subprocess.CalledProcessError):
                pilot.make_bundle("wikidata-development", BINARY, index=index)

    def test_startup_failures_are_actionable_only_in_operator_terminal(self):
        for args, diagnostic in ((["--binary", str(self.root / "missing-binary")], "build the CLI"),
                                 (["--index", str(self.root / "missing-index")], "Restore the pinned")):
            with self.subTest(args=args), redirect_stderr(io.StringIO()) as output:
                self.assertEqual(pilot.main(["wikidata-development", *args]), 1)
                self.assertIn(diagnostic, output.getvalue())
                self.assertNotIn("/#", output.getvalue())
        index = self.root / "stale.json"
        index.write_text("{}")
        with redirect_stderr(io.StringIO()) as output:
            self.assertEqual(pilot.main(["wikidata-development", "--index", str(index)]), 1)
            self.assertIn("Rust index-inspect exited", output.getvalue())
            self.assertIn("Inspect the validator error locally:", output.getvalue())
            self.assertIn(str(ui.ROOT / "data/wikidata/snapshot.nq"), output.getvalue())
            self.assertNotIn("verity-find-", output.getvalue())

    def test_malformed_options_and_dangerous_binds_rejected_before_bundle(self):
        for options in (["unknown"], ["wikidata-development", "--scope", "all.json"],
                        ["wikidata-development", "--rdf", "https://remote.invalid/data"],
                        ["wikidata-development", "--roles"], ["wikidata-development", "--roles", "entity", "entity"],
                        ["wikidata-development", "--roles", "unknown"], ["wikidata-development", "--port", "-1"],
                        ["wikidata-development", "--port", "65536"], ["wikidata-development", "--port", "x"],
                        *(["wikidata-development", "--host", host] for host in ("0.0.0.0", "::", "localhost", "127.0.0.2", "192.168.1.2"))):
            with self.subTest(options=options), patch.object(pilot, "make_bundle", side_effect=AssertionError("No startup")):
                with patch("sys.stderr"), self.assertRaises(SystemExit) as error:
                    pilot.main(options)
                self.assertEqual(error.exception.code, 2)

    def test_documented_commands_stop_cleanup_restart_and_invalidate_credentials(self):
        for name in pilot.PRESETS:
            previous_credential = None
            for attempt in range(2):
                with self.subTest(preset=name, launch=attempt):
                    process = subprocess.Popen([sys.executable, str(ui.ROOT / "tools/launch_find_pilot.py"), name],
                                               cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                               env={**os.environ, "TMPDIR": str(self.root)})
                    try:
                        data = b""
                        deadline = time.monotonic() + 45
                        with selectors.DefaultSelector() as selector:
                            selector.register(process.stdout, selectors.EVENT_READ)
                            while b"http://127.0.0.1:" not in data:
                                self.assertLess(time.monotonic(), deadline, data)
                                for key, _ in selector.select(1):
                                    chunk = os.read(key.fileobj.fileno(), 65536)
                                    self.assertTrue(chunk, data)
                                    data += chunk
                        url = urlsplit(next(line for line in data.decode().splitlines() if line.startswith("http://")))
                        self.assertNotEqual(url.fragment, previous_credential)
                        connection = http.client.HTTPConnection(url.netloc, timeout=10)
                        try:
                            connection.request("GET", "/")
                            response = connection.getresponse()
                            self.assertEqual(response.status, 200)
                            self.assertIn(b"Local Find</title>", response.read())
                        finally:
                            connection.close()
                        class Endpoint:
                            authority = url.netloc
                            origin = "http://" + url.netloc
                            credential = url.fragment
                        endpoint = Endpoint()
                        self.result(endpoint, "/api/session", {})
                        if previous_credential:
                            self.assertEqual(self.call(endpoint, "/api/session", {}, Authorization="Bearer " + previous_credential), (400, ui.ERROR))
                        previous_credential = url.fragment
                        self.assertEqual(len(list(self.root.glob("verity-find-*"))), 1)
                        process.send_signal(signal.SIGINT)
                        process.communicate(timeout=10)
                        self.assertEqual(process.returncode, 0)
                        self.assertEqual(list(self.root.glob("verity-find-*")), [])
                        with self.assertRaises(OSError):
                            socket.create_connection((url.hostname, url.port), timeout=1)
                    finally:
                        if process.poll() is None:
                            process.kill()
                        process.communicate(timeout=10)
