#!/usr/bin/env python3
"""Verify or download only the small, source-pinned Childs et al. code files."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance/source_manifest_v1.json"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-missing", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    commit = manifest["upstream_commit"]
    base = "https://raw.githubusercontent.com/marissachilds/global-dengue-temperature/" + commit + "/"
    failures = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.exists() and args.download_missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = urlopen(base + item["upstream_path"], timeout=30).read()
            path.write_bytes(payload)
        if not path.exists():
            failures.append(f"missing: {item['path']}")
            continue
        if path.stat().st_size != item["bytes"]:
            failures.append(f"size mismatch: {item['path']}")
        if digest(path) != item["sha256"]:
            failures.append(f"sha256 mismatch: {item['path']}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"verified {len(manifest['files'])} files at {commit}")


if __name__ == "__main__":
    main()

