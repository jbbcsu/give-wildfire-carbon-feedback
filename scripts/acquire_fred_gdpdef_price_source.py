#!/usr/bin/env python3
"""Verify, or explicitly download, the frozen FRED/BEA GDPDEF price snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-missing", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "config/fredi_transport_conus_partial_scc_v1.json").read_text())
    source = config["sources"]["fred_price_source"]
    path = ROOT / source["path"]
    if not path.exists():
        if not args.download_missing:
            raise FileNotFoundError(f"missing {path}; rerun with --download-missing")
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != source["sha256"]:
            raise RuntimeError("downloaded FRED snapshot does not match the frozen hash")
        path.write_bytes(payload)
    if digest(path) != source["sha256"]:
        raise RuntimeError("local FRED snapshot hash mismatch")
    print(f"PASS {path.relative_to(ROOT)} sha256={source['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
