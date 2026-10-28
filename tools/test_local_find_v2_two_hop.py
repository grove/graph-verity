"""Real-graph browser coverage for Local Find v2's two-hop explorer."""
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest

import local_find as v1
import local_find_v2 as v2


class TwoHopBrowser(unittest.TestCase):
    def test_wikidata_path_witness_language_and_navigation(self):
        chrome = os.environ.get("CHROME_BINARY") or next((p for name in (
            "google-chrome", "chromium", "chromium-browser") if (p := shutil.which(name))), None)
        mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which("node"):
            if os.environ.get("REQUIRE_FIND_BROWSER") == "1":
                self.fail("Headless Chrome and Node >=22 required")
            self.skipTest("Headless Chrome / Node unavailable")

        root = v1.ROOT
        bundle = v1.Bundle(root / "target/debug/verity", root / "data/wikidata/snapshot.nq", "nquads",
                           root / "data/wikidata/policy.json", root / "data/wikidata/scope.json",
                           root / "data/wikidata/discovery.json")
        self.addCleanup(bundle.close)
        with v2.Server(bundle) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                subprocess.run(["node", str(root / "tools/local_find_v2_two_hop_browser.mjs"), chrome,
                                server.url], check=True, timeout=120)
            finally:
                server.shutdown()
                thread.join()
