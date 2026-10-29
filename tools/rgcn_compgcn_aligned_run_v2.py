#!/usr/bin/env python3
"""Aligned-v2 runner entry point with one-time PyTorch CPU runtime setup."""
import argparse
import json
import sys
from pathlib import Path

import rgcn_compgcn_aligned_run_v1 as base


def model_free_preflight(manifest_path: Path, preflight_path: Path,
                         asset_verification_path: Path, model_dir: Path) -> dict:
    manifest = base.read(manifest_path)
    base._validate_source_inputs(manifest, manifest_path)
    receipt = base.require_fresh_preflight(
        preflight_path, manifest_path, asset_verification_path=asset_verification_path)
    asset_report = base.read(asset_verification_path)
    if (asset_report.get("status") != "verified-without-loading-weights-or-running-inference" or
            asset_report.get("aligned_experiment_manifest_sha256") != base.sha_file(manifest_path) or
            asset_report.get("model_dir") != str(model_dir.resolve())):
        raise ValueError("Asset receipt is not bound to this version, manifest, and model directory")
    identity = base.embedding_runtime_identity(model_dir)
    verified = asset_report["identity"]
    if (identity["asset_set_sha256"] != verified["asset_set_sha256"] or
            identity["runtime_sha256"] != verified["runtime_sha256"]):
        raise ValueError("Current model assets or runtime differ from the verified receipt")
    output_path = base.ROOT / manifest["features"]["new_relation_feature_output"]
    output_relpath = base.registered_feature_output(manifest, output_path)
    if output_path.exists() or output_path.with_suffix(".manifest.json").exists():
        raise ValueError("Registered feature output already exists; create a new experiment version")
    import embedding_experiment
    spec, _ = embedding_experiment.verify()
    _, runtime = base.reusable_feature_runtime(embedding_experiment, identity)
    operation = base.read(manifest_path.parent / "feature-operation-v1.json")
    return {
        "status": "pass-ready-before-model-construction",
        "aligned_experiment_manifest_sha256": base.sha_file(manifest_path),
        "preflight_sha256": base.sha_file(preflight_path),
        "asset_verification_sha256": base.sha_file(asset_verification_path),
        "feature_operation_sha256": base.sha_file(manifest_path.parent / "feature-operation-v1.json"),
        "questions_sha256": manifest["benchmark"]["questions_sha256"],
        "feature_output_path": output_relpath,
        "model": spec["model"],
        "revision": spec["revision"],
        "runtime_sha256": identity["runtime_sha256"],
        "runtime_threads": [runtime["threads"], runtime["interop_threads"]],
        "input_count": operation["input_count"],
        "feature_resource_preflight_passed": receipt["feature_resource_preflight_passed"],
        "model_constructor_called": False,
        "model_weights_loaded": False,
        "inference_performed": False,
        "authorization_consumed": False,
    }


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "model-free-preflight":
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("command", choices=["model-free-preflight"])
        parser.add_argument("--manifest", type=Path, required=True)
        parser.add_argument("--preflight", type=Path, required=True)
        parser.add_argument("--asset-verification", type=Path, required=True)
        parser.add_argument("--model-dir", type=Path, required=True)
        parser.add_argument("--out", type=Path, required=True)
        args = parser.parse_args()
        result = model_free_preflight(args.manifest, args.preflight,
                                      args.asset_verification, args.model_dir)
        if args.out.exists():
            raise ValueError("Model-free preflight output exists; choose a fresh path")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    else:
        base.main()
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
