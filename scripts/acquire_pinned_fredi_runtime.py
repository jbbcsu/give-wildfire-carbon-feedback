#!/usr/bin/env python3
"""Acquire the official FrEDI runtime at the exact admitted commit."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance/source_manifest_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-missing", action="store_true")
    args = parser.parse_args()
    info = json.loads(MANIFEST.read_text())["fredi"]
    target = ROOT / info["runtime_path"]
    if not target.exists() and args.download_missing:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "FrEDI"
            subprocess.run(["git", "clone", "--depth", "1", "--branch", info["tag"], info["repository"], str(repo)], check=True)
            commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            if commit != info["commit"]:
                raise SystemExit(f"commit mismatch: {commit}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / "FrEDI/R/sysdata.rda", target)
    if not target.exists():
        raise SystemExit("missing FrEDI runtime; pass --download-missing")
    if digest(target) != info["runtime_sha256"]:
        raise SystemExit("FrEDI runtime hash mismatch")
    print(f"verified FrEDI runtime {info['commit']}")


if __name__ == "__main__":
    main()

