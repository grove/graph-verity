#!/usr/bin/env python3
"""Separately versioned Find UI v2; the frozen v1 adapter and Rust API are unchanged."""
from pathlib import Path
from unittest.mock import patch

import local_find as v1

ASSETS = Path(__file__).with_name("local_find_ui_v2")


class Server(v1.Server):
    def __init__(self, bundle, host="127.0.0.1", port=0):
        assets = {
            "/": ((ASSETS / "index.html").read_bytes(), "text/html"),
            "/v2.js": ((ASSETS / "v2.js").read_bytes(), "text/javascript"),
        }
        launcher_hash = v1.file_digest(Path(__file__))
        super().__init__(bundle, host, port)
        self.assets.update(assets)
        bundle.receipt.update({
            "ui_version": "local-find-v2-prototype",
            "launcher_sha256": launcher_hash,
            "assets": {route: v1.digest(body) for route, (body, _) in self.assets.items()},
        })


def main():
    # Reuse even the operator CLI; only the server's inert, same-origin assets differ.
    with patch.object(v1, "Server", Server):
        return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
