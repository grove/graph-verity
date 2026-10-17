"""V2 presentation plus the unchanged adapter's security/approval regression suite."""
import http.client
import json
import os
import shutil
import subprocess
import sys
import threading
from urllib.parse import urlsplit
from pathlib import Path
from unittest.mock import patch

import local_find as v1
import local_find_v2 as v2
import test_local_find as original


class LocalFindV2(original.LocalFind):
    def setUp(self):
        patcher = patch.object(v1, "Server", v2.Server)
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def make_bundle(self, **kw):
        if not getattr(self, "v2_fixture", False):
            self.v2_fixture = True
            with self.rdf.open("a") as file:
                file.write('''
ex:a {
 ex:child skos:prefLabel "Child"@en ; skos:broader ex:parent .
 ex:parent skos:prefLabel "Forelder"@nb ; skos:narrower ex:child .
 ex:aliasIri skos:altLabel "urn:discovery:missing"@en .
 ex:property rdfs:label "capital"@en, "hovedstad"@nb ;
   <http://wikiba.se/ontology#directClaim> ex:capital .
 ex:start ex:capital ex:child .
 ex:long skos:definition "''' + "bounded source text " * 100 + '''"@en .
}
ex:b { ex:outside rdfs:label "Outside selected graph"@en . }
''')
            config = json.loads(self.config.read_text())
            config["snapshot_id"] = json.loads(subprocess.check_output([
                str(v1.ROOT / "target/debug/verity"), "inspect", str(self.rdf), "trig"]))["snapshot_id"]
            self.config.write_text(json.dumps(config))
        return super().make_bundle(**kw)

    def test_both_operator_launchers_serve_their_own_ui(self):
        for launcher, version in (("local_find.py", b"Local Find</title>"),
                                  ("local_find_v2.py", b"Local Find v2 prototype</title>")):
            process = subprocess.Popen([
                sys.executable,
                str(v1.ROOT / "tools" / launcher), "--rdf", str(self.rdf), "--format", "trig",
                "--policy", str(self.policy), "--scope", str(self.scope), "--config", str(self.config)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                self.assertIn(b"Local Find pilot", process.stdout.readline())
                url = urlsplit(process.stdout.readline().decode().strip())
                self.assertEqual(url.hostname, "127.0.0.1")
                connection = http.client.HTTPConnection(url.netloc, timeout=10)
                try:
                    connection.request("GET", "/")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertIn(version, response.read())
                finally:
                    connection.close()
            finally:
                process.terminate()
                process.communicate(timeout=10)

    def test_v2_assets_receipt_and_unchanged_find_payloads(self):
        receipt = self.result("/api/session", {})["receipt"]
        self.assertEqual(receipt["ui_version"], "local-find-v2-prototype")
        for route, expected in self.server.assets.items():
            status, data, headers = self.call(route, method="GET")
            self.assertEqual(status, 200)
            self.assertEqual(data, expected[0])
            self.assertEqual(receipt["assets"][route], v1.digest(data))
            self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        # Independent v1 Bundle, identical trusted inputs: all ranks, scores and witnesses agree.
        old = super().make_bundle()
        self.addCleanup(old.close)
        tab = old.api("/api/session", {})["tab"]
        for query in ("urn:discovery:missing", "urn:discovery:outside", "urn:discovery:shared",
                      "Felles alias", "capital of Norway", "Atlantis capital", "bounded"):
            request = self.find(query)
            self.assertEqual(self.result("/api/find", request), old.api("/api/find", request, tab))
        result = self.result("/api/find", self.find("urn:discovery:missing"))
        self.assertGreater(result["matches"], 0)
        self.assertTrue(any(hit["exact"] for hit in result["hits"]))  # alias text is not IRI identity
        self.assertFalse(any(hit["explanation"]["exact_iri"] for hit in result["hits"]))
        result = self.result("/api/find", dict(self.find("Felles alias"), limit=1))
        self.assertEqual(result["exact_candidates"], 2)
        self.assertTrue(result["truncated"])

    def test_preclipping_exact_counts_keep_graph_and_role_identity(self):
        self.scope.write_text('["urn:discovery:a", "urn:discovery:b"]')
        config = json.loads(self.config.read_text())
        config["graphs"]["urn:discovery:b"] = config["graphs"]["urn:discovery:a"]
        self.config.write_text(json.dumps(config))
        bundle = self.make_bundle(roles=("entity",))
        self.addCleanup(bundle.close)
        with v2.Server(bundle) as server:
            session = bundle.api("/api/session", {})
            self.assertEqual(session["roles"], ("entity",))
            self.assertEqual(session["receipt"]["ui_version"], "local-find-v2-prototype")
            query = dict(self.find("urn:discovery:shared"), scope=session["scope"], limit=1)
            result = bundle.api("/api/find", query, session["tab"])
            self.assertEqual((result["exact_candidates"], result["exact_ids"]), (2, 1))
            self.assertTrue(result["truncated"])
            self.assertEqual(result["hits"][0]["iri"], "urn:discovery:shared")
            self.assertIn(result["hits"][0]["graph"], session["scope"])
            query["scope"] = ["urn:discovery:b"]
            result = bundle.api("/api/find", query, session["tab"])
            self.assertEqual(result["exact_candidates"], 1)
            self.assertEqual(result["hits"][0]["graph"], "urn:discovery:b")

    def test_bind_validation_ipv6_and_headless_browser(self):
        chrome = os.environ.get("CHROME_BINARY") or next((p for name in (
            "google-chrome", "chromium", "chromium-browser") if (p := shutil.which(name))), None)
        mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which("node"):
            if os.environ.get("REQUIRE_FIND_BROWSER") == "1":
                self.fail("Headless Chrome and Node >=22 required")
            self.skipTest("Headless Chrome / Node unavailable")
        subprocess.run(["node", str(v1.ROOT / "tools/local_find_v2_browser.mjs"), chrome, self.server.url],
                       check=True, timeout=120)
        # Also exercise the public real-data mapping, English/Norwegian and capital role/path case.
        bundle = v1.Bundle(v1.ROOT / "target/debug/verity", v1.ROOT / "data/wikidata/snapshot.nq", "nquads",
                           v1.ROOT / "data/wikidata/policy.json", v1.ROOT / "data/wikidata/scope.json",
                           v1.ROOT / "data/wikidata/discovery.json")
        self.addCleanup(bundle.close)
        with v2.Server(bundle) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                subprocess.run(["node", str(v1.ROOT / "tools/local_find_v2_browser.mjs"), chrome,
                                server.url, "wikidata"], check=True, timeout=120)
            finally:
                server.shutdown()
                thread.join()
