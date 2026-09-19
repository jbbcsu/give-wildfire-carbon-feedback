#!/usr/bin/env python3
"""Synthetic parsing and fail-closed tests for the future-drought audit."""

from pathlib import Path
from tempfile import TemporaryDirectory

from audit_future_drought_pathway import scan_resident


with TemporaryDirectory() as temporary:
    root = Path(temporary)
    good = root / "gfdl-esm4_r1i1p1f1_w5e5_ssp126_tasmin_global_daily_2041_2050.nc"
    good.write_bytes(b"1234")
    bad = root / "unregistered.nc"
    bad.write_bytes(b"x")
    rows, rejected = scan_resident(root)
    assert len(rows) == 1
    assert rows[0]["forcing"] == "gfdl-esm4"
    assert rows[0]["member"] == "r1i1p1f1"
    assert rows[0]["scenario"] == "ssp126"
    assert rows[0]["variable"] == "tasmin"
    assert rows[0]["period"] == "2041_2050"
    assert rows[0]["logical_bytes"] == 4
    assert len(rejected) == 1 and rejected[0].endswith("unregistered.nc")

print("Future-drought readiness audit parser tests passed")
