#!/usr/bin/env python3
"""Verify every locally acquired checksum exposed by provenance TOML records.

The walker supports conventional ``[[files]]`` arrays, exact ignored local
paths, and the nested historical/projection records used by the ISIMIP3b
boundary audit. A successful run is therefore not allowed to silently skip a
known checksum merely because it is nested under a different table name.
"""
from __future__ import annotations

import hashlib
import sys
import tomllib
from pathlib import Path
from typing import Iterator


SPECS = (
    ("name", "sha512", "size_bytes", False),
    ("name", "sha256", "size_bytes", False),
    ("filename", "sha512", "size_bytes", False),
    ("filename", "sha256", "size_bytes", False),
    ("historical_file_name", "historical_sha512", "historical_bytes", False),
    ("projection_file_name", "projection_sha512", "projection_bytes", False),
    ("file_name", "file_checksum_sha512", "file_size_bytes", False),
    ("file_name", "file_checksum_sha256", "file_size_bytes", False),
    ("local_ignored_path", "local_sha512", "size_bytes", True),
    ("local_ignored_path", "local_sha256", "size_bytes", True),
    ("local_path", "local_sha512", "size_bytes", True),
    ("local_path", "local_sha256", "size_bytes", True),
)


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def iter_entries(value: object) -> Iterator[dict[str, object]]:
    if isinstance(value, dict):
        for name_key, checksum_key, size_key, exact_path in SPECS:
            name = value.get(name_key)
            checksum = value.get(checksum_key)
            if isinstance(name, str) and name and isinstance(checksum, str) and checksum:
                yield {
                    "name": name,
                    "checksum": checksum,
                    "algorithm": "sha512" if "sha512" in checksum_key else "sha256",
                    "size_bytes": value.get(size_key),
                    "exact_path": exact_path,
                }
        for child in value.values():
            yield from iter_entries(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_entries(child)


def locate(entry: dict[str, object], project: Path) -> list[Path]:
    name = str(entry["name"])
    if bool(entry["exact_path"]):
        path = Path(name)
        if path.is_absolute():
            raise ValueError(f"Tracked provenance must not contain an absolute raw-data path: {path}")
        return [project / path]
    return sorted((project / "data" / "raw").rglob(Path(name).name))


def main(root: Path) -> int:
    project = root.parent.parent
    failures = 0
    checked = 0
    for record_path in sorted(root.glob("*.toml")):
        record = tomllib.loads(record_path.read_text(encoding="utf-8"))
        seen: set[tuple[str, str]] = set()
        for entry in iter_entries(record):
            identity = (str(entry["name"]), str(entry["checksum"]))
            if identity in seen:
                continue
            seen.add(identity)
            matches = locate(entry, project)
            if len(matches) != 1 or not matches[0].is_file():
                state = "MISSING" if len(matches) == 0 else "AMBIGUOUS"
                print(f"{state} {record_path.name}: {entry['name']}")
                failures += 1
                continue
            path = matches[0]
            expected_size = entry.get("size_bytes")
            if expected_size is not None:
                try:
                    expected_size = int(expected_size)
                except (TypeError, ValueError):
                    print(f"INVALID_SIZE {record_path.name}: {entry['name']}")
                    failures += 1
                    continue
                if path.stat().st_size != expected_size:
                    print(
                        f"SIZE_MISMATCH {record_path.name}: {entry['name']} "
                        f"({path.stat().st_size} != {expected_size})"
                    )
                    failures += 1
                    continue
            actual = digest(path, str(entry["algorithm"]))
            state = "OK" if actual == entry["checksum"] else "MISMATCH"
            print(f"{state} {entry['name']}")
            failures += state != "OK"
            checked += 1
    print(f"SUMMARY checked={checked} failures={failures}")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/provenance")))
