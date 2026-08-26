#!/usr/bin/env python3
"""Local tests for pinned MIRCA-OS acquisition helpers."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "download_mirca_os_v2", PROJECT / "scripts" / "download_mirca_os_v2.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

members = MODULE.selected_members()
assert len(members) == 40 and len(set(members)) == 40
assert all("/30-arcminute/" in member for member in members)
assert any("MIRCA-OS_Maize_2000_ir_30arcmin_v2.tif" in member for member in members)

with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary) / "small.bin"
    payload = b"pinned-test-payload"
    path.write_bytes(payload)
    record = MODULE.verify_archive(
        path,
        expected_size=len(payload),
        expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
        expected_sha512=hashlib.sha512(payload).hexdigest(),
    )
    assert record["size_bytes"] == len(payload)
    try:
        MODULE.verify_archive(
            path,
            expected_size=len(payload) + 1,
            expected_md5="x",
            expected_sha512="y",
        )
    except ValueError as error:
        assert "byte length" in str(error)
    else:
        raise AssertionError("Wrong archive identity was accepted")

print("MIRCA acquisition helper tests passed")
