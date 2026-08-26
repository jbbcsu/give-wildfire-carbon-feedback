#!/usr/bin/env python3
"""Synthetic identity and inventory tests for MIRCA rice acquisition."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "download_mirca_rice_seasons", PROJECT / "scripts" / "download_mirca_rice_seasons.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

members = MODULE.selected_members()
assert len(members) == 30 and len(set(members)) == 30
assert "2000/MIRCA-OS_Rice1_2000_ir.nc" in members
assert "2020/MIRCA-OS_Rice3_2020_rf.nc" in members

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "source.bin"
    path.write_bytes(b"MIRCA-rice-test")
    digest = hashlib.sha512(path.read_bytes()).hexdigest()
    assert MODULE.verify_file(path, path.stat().st_size, digest)["sha512"] == digest
    content_md5 = hashlib.md5(path.read_bytes(), usedforsecurity=False).digest()
    expected_etag = hashlib.md5(content_md5, usedforsecurity=False).hexdigest() + "-1"
    assert MODULE.one_part_etag(path) == expected_etag
    try:
        MODULE.verify_file(path, path.stat().st_size + 1, digest)
    except ValueError as error:
        assert "Byte length differs" in str(error)
    else:
        raise AssertionError("Wrong byte length was accepted")

print("MIRCA rice acquisition tests passed")
