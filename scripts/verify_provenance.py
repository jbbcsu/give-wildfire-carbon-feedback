#!/usr/bin/env python3
"""Verify checksums recorded in project provenance TOML files.

Usage: .venv/bin/python scripts/verify_provenance.py data/provenance
"""
from __future__ import annotations

import hashlib
import sys
import tomllib
from pathlib import Path


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main(root: Path) -> int:
    project = root.parent.parent
    failures = 0
    for record_path in sorted(root.glob("*.toml")):
        record = tomllib.loads(record_path.read_text())
        entries = record.get("files", []) or [record]
        for entry in entries:
            name = entry.get("name") or entry.get("filename")
            checksum = entry.get("sha512") or entry.get("sha256")
            if not name or not checksum:
                continue
            algorithm = "sha512" if "sha512" in entry else "sha256"
            matches = list((project / "data" / "raw").rglob(name))
            if not matches:
                print(f"MISSING {record_path.name}: {name}")
                failures += 1
                continue
            actual = digest(matches[0], algorithm)
            state = "OK" if actual == checksum else "MISMATCH"
            print(f"{state} {name}")
            failures += state != "OK"
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/provenance")))
