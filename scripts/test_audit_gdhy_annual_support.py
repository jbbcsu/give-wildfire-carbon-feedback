#!/usr/bin/env python3
"""Synthetic tests for the annual GDHY source-support audit."""
from __future__ import annotations

import importlib.util
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import xarray as xr


PROJECT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT / "scripts" / "audit_gdhy_annual_support.py"
SPEC = importlib.util.spec_from_file_location("audit_gdhy_annual_support", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

with tempfile.TemporaryDirectory() as temporary:
    temporary_path = Path(temporary)
    extracted = temporary_path / "extracted"
    series_root = extracted / "maize_major"
    series_root.mkdir(parents=True)
    arrays = {
        2010: np.array([[1.0, 2.0, np.nan], [3.0, 0.0, np.nan]], dtype="float32"),
        2011: np.array([[1.0, np.nan, np.nan], [4.0, 0.0, np.nan]], dtype="float32"),
        2012: np.array([[1.0, 2.0, np.nan], [5.0, 0.0, np.nan]], dtype="float32"),
    }
    lat = np.array([-0.25, 0.25])
    lon = np.array([0.25, 0.75, 1.25])
    for year, values in arrays.items():
        dataset = xr.Dataset({"var": (("lat", "lon"), values)}, coords={"lat": lat, "lon": lon})
        dataset.to_netcdf(
            series_root / f"yield_{year}.nc4",
            engine="h5netcdf",
            encoding={"var": {"_FillValue": -999000000.0}},
        )
    archive_path = temporary_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in sorted(series_root.glob("*.nc4")):
            archive.write(path, path.relative_to(extracted))

    archive_audit = MODULE.audit_archive(archive_path, extracted)
    assert archive_audit["archive_file_members"] == 3
    assert archive_audit["exact_extracted_member_matches"] == 3
    assert archive_audit["missing_extracted_members"] == []
    assert archive_audit["mismatched_extracted_members"] == []

    audit = MODULE.audit_series(extracted, "maize_major", [2010, 2011, 2012])
    assert audit["annual"]["2010"]["finite_cells"] == 4
    assert audit["annual"]["2010"]["positive_cells"] == 3
    assert audit["annual"]["2010"]["source_zero_cells"] == 1
    assert audit["adjacent_transitions"]["2010-2011"]["finite_lost"] == 1
    assert audit["adjacent_transitions"]["2010-2011"]["finite_lost_south"] == 1
    assert audit["adjacent_transitions"]["2011-2012"]["finite_gained"] == 1

    changed = series_root / "yield_2012.nc4"
    changed.write_bytes(changed.read_bytes() + b"changed")
    changed_audit = MODULE.audit_archive(archive_path, extracted)
    assert changed_audit["mismatched_extracted_members"] == ["maize_major/yield_2012.nc4"]

print("GDHY annual-support audit tests passed")
