#!/usr/bin/env python3
"""Acquire the exact pinned public sources; never silently replace files."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    config = json.loads((ROOT / "config/inland_flood_scc_v1.json").read_text())
    spec = config["sources"]["fredi_table"]
    target = ROOT / spec["path"]
    url = f"https://raw.githubusercontent.com/USEPA/FrEDI_Data/{spec['commit']}/{spec['upstream_path']}"
    if target.exists():
        if digest(target) != spec["sha256"]:
            raise ValueError(f"existing file has wrong hash: {target}")
        print(f"verified existing {target}")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != spec["sha256"]:
        raise ValueError("download hash mismatch")
    target.write_bytes(payload)
    print(f"downloaded and verified {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

