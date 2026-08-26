#!/usr/bin/env python3
"""Synthetic nested and exact-path tests for the provenance verifier."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_provenance", PROJECT / "scripts" / "verify_provenance.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

with tempfile.TemporaryDirectory() as directory:
    project = Path(directory) / "project"
    provenance = project / "data" / "provenance"
    raw = project / "data" / "raw" / "nested"
    provenance.mkdir(parents=True)
    raw.mkdir(parents=True)
    historical = raw / "historical.nc"
    local = raw / "local.bin"
    tracked = project / "config" / "tracked.csv"
    tracked.parent.mkdir(parents=True)
    historical.write_bytes(b"historical")
    local.write_bytes(b"local")
    tracked.write_bytes(b"tracked")
    historical_hash = hashlib.sha512(historical.read_bytes()).hexdigest()
    local_hash = hashlib.sha512(local.read_bytes()).hexdigest()
    tracked_hash = hashlib.sha512(tracked.read_bytes()).hexdigest()
    (provenance / "test.toml").write_text(
        "[[variable]]\n"
        "historical_file_name = \"historical.nc\"\n"
        f"historical_bytes = {historical.stat().st_size}\n"
        f"historical_sha512 = \"{historical_hash}\"\n"
        "\n[local]\n"
        "local_ignored_path = \"data/raw/nested/local.bin\"\n"
        f"size_bytes = {local.stat().st_size}\n"
        f"local_sha512 = \"{local_hash}\"\n"
        "\n[tracked]\n"
        "local_path = \"config/tracked.csv\"\n"
        f"size_bytes = {tracked.stat().st_size}\n"
        f"local_sha512 = \"{tracked_hash}\"\n",
        encoding="utf-8",
    )
    assert MODULE.main(provenance) == 0
    historical.write_bytes(b"changed")
    assert MODULE.main(provenance) == 1

print("nested provenance-verifier tests passed")
