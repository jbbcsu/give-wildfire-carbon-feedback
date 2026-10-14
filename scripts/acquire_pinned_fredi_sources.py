#!/usr/bin/env python3
"""Verify or explicitly reacquire only the small pinned FrEDI audit surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(262144), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--download-missing",
        action="store_true",
        help="Explicitly allow downloading a missing small file from its commit-pinned official EPA URL.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "provenance/fredi_source_manifest_v4_1_1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified = 0
    downloaded = 0
    for item in manifest["files"]:
        relative = item["raw_path"]
        if relative is None:
            continue
        destination = root / relative
        if not destination.exists():
            if not args.download_missing:
                raise SystemExit(f"missing {relative}; rerun with --download-missing only after reviewing the manifest")
            upstream = manifest["upstreams"][item["upstream"]]
            repository = upstream["repository"].removeprefix("https://github.com/")
            url = f"https://raw.githubusercontent.com/{repository}/{upstream['commit']}/{item['path']}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as tmp:
                temporary = Path(tmp.name)
                with urllib.request.urlopen(url, timeout=60) as response:
                    while block := response.read(262144):
                        tmp.write(block)
            try:
                if temporary.stat().st_size != item["bytes"] or sha256(temporary) != item["sha256"]:
                    raise SystemExit(f"downloaded source failed pinned hash/size: {item['path']}")
                os.replace(temporary, destination)
                downloaded += 1
            finally:
                if temporary.exists():
                    temporary.unlink()
        if destination.stat().st_size != item["bytes"] or sha256(destination) != item["sha256"]:
            raise SystemExit(f"local source failed pinned hash/size: {relative}")
        verified += 1
    print(json.dumps({"status": "PASS", "verified_files": verified, "downloaded_files": downloaded}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
