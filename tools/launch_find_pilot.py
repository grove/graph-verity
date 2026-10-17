#!/usr/bin/env python3
"""Launch an allow-listed, hash-verified offline corpus in the existing Find UI."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

import local_find as ui

ROOT = ui.ROOT
PRESETS = ("wikidata-development", "worldcities-norway", "gemet-4.2.3")
REGISTRY = "tools/find_pilot_presets.json"


class PresetBundle(ui.Bundle):
    def current(self):
        try:
            super().current()
        except (OSError, ValueError):
            # Missing/growing witnesses must revoke leases just like checksum changes.
            self.tab = self.pending = self.selection = None
            self.find_entities.clear()
            raise


def make_bundle(preset: str, binary: Path, index: Path | None = None, roles=ui.ROLES):
    if preset not in PRESETS:
        raise ValueError("Unknown corpus preset")
    registry = ui.read(ROOT / REGISTRY, 64 * 1024)
    spec = json.loads(registry)[preset]
    originals = {ROOT / REGISTRY: (ui.digest(registry), 64 * 1024)}
    # Pins include the original manifests, source/license/revision witnesses and operator inputs.
    for name, expected in spec["sha256"].items():
        path = ROOT / name
        if not path.resolve(strict=True).is_relative_to(ROOT.resolve()):
            raise ValueError(f"Preset input escapes checkout: {name}")
        if ui.file_digest(path) != "sha256:" + expected:
            raise ValueError(f"Preset checksum mismatch: {name}; restore the retained file")
        originals[path] = ("sha256:" + expected, path.stat().st_size)
    paths = [ROOT / spec[key] for key in ("rdf", "policy", "scope", "config")]
    if any(path not in originals for path in paths):
        raise ValueError("Unpinned preset input")
    bundle = PresetBundle(binary, paths[0], spec["format"], *paths[1:], index, tuple(roles))
    try:
        bundle.originals.update(originals)
        bundle.current()  # Also reject changes made during validation/startup.
        bundle.receipt.update(preset=preset, preset_registry_sha256=ui.digest(registry),
                              preset_launcher_sha256=ui.file_digest(Path(__file__)))
        return bundle
    except Exception:
        bundle.close()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("preset", choices=PRESETS)
    parser.add_argument("--roles", nargs="+", choices=ui.ROLES, default=ui.ROLES)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/debug/verity")
    parser.add_argument("--index", type=Path, help="optional local index; Rust rebuilds and verifies it")
    parser.add_argument("--host", choices=("127.0.0.1", "::1"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("Python 3.11+ required; use python3.11/python3.12 or the project .venv/bin/python")
    if len(set(args.roles)) != len(args.roles):
        parser.error("--roles must be a nonempty subset without duplicates")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535 (0 chooses a private ephemeral port)")
    bundle = None
    try:
        bundle = make_bundle(args.preset, args.binary, args.index, args.roles)
        with ui.Server(bundle, args.host, args.port) as server:
            print(f"Local Find pilot: {args.preset}; BM25 only; frozen v1 interface.", flush=True)
            print(f"Snapshot: {bundle.snapshot}", flush=True)
            config = json.loads(Path(bundle.common[4]).read_bytes())
            for graph in bundle.scope:
                print(f"Authorized graph (importer-assigned): {graph}", flush=True)
                print(json.dumps(config["graphs"][graph], ensure_ascii=True), flush=True)
            print("Keep this session URL private. Stop with Ctrl-C; restart after input changes.", flush=True)
            print(server.url, flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError as error:
        # The shared adapter deliberately hides CLI stderr from browser responses.
        spec = json.loads((ROOT / REGISTRY).read_bytes())[args.preset]
        command = [str(args.binary), "index-inspect" if args.index else "index-build",
                   str(ROOT / spec["rdf"]), spec["format"],
                   *(str(ROOT / spec[k]) for k in ("policy", "scope", "config"))]
        if args.index:
            command.append(str(args.index))
        print(f"Cannot start {args.preset}: Rust {error.cmd[1]} exited {error.returncode}.\n"
              f"Inspect the validator error locally: {shlex.join(command)}\n"
              "Import/discovery/time/response limits are unchanged; do not trim records or raise caps.",
              file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Cannot start {args.preset}: {error}\n"
              "Restore the pinned checkout inputs, check the loopback port, and build the CLI with "
              "cargo build --locked --offline -p verity_cli (Python 3.11+ required).",
              file=sys.stderr)
        return 1
    finally:
        if bundle:
            bundle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
