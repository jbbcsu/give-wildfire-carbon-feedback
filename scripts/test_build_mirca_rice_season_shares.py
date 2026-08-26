#!/usr/bin/env python3
"""Small-array invariants for MIRCA rice-season aggregation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

import numpy as np
import rasterio


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_mirca_rice_season_shares",
    PROJECT / "scripts" / "build_mirca_rice_season_shares.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

fine = np.ones((12, 18), dtype=float)
coarse = MODULE.aggregate_six_by_six(fine)
assert coarse.shape == (2, 3)
assert np.array_equal(coarse, np.full((2, 3), 36.0))
fine[:6, :6] = 2.0
coarse = MODULE.aggregate_six_by_six(fine)
assert coarse[0, 0] == 72.0 and coarse[1, 2] == 36.0

bad = fine.copy()
bad[0, 0] = -1
try:
    MODULE.aggregate_six_by_six(bad)
except ValueError as error:
    assert "nonnegative" in str(error)
else:
    raise AssertionError("Negative area was accepted")

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    valid = root / "valid.tif"
    profile = {
        "driver": "GTiff",
        "height": MODULE.COARSE_SHAPE[0],
        "width": MODULE.COARSE_SHAPE[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": MODULE.EXPECTED_COARSE_TRANSFORM,
        "nodata": 0.0,
    }
    with rasterio.open(valid, "w", **profile) as dataset:
        dataset.write(np.zeros(MODULE.COARSE_SHAPE, dtype=np.float32), 1)
    assert MODULE.read_annual(valid).shape == MODULE.COARSE_SHAPE

    wrong = root / "wrong.tif"
    profile["transform"] = rasterio.transform.Affine(0.5, 0, -179.5, 0, -0.5, 90)
    with rasterio.open(wrong, "w", **profile) as dataset:
        dataset.write(np.zeros(MODULE.COARSE_SHAPE, dtype=np.float32), 1)
    try:
        MODULE.read_annual(wrong)
    except ValueError as error:
        assert "transform" in str(error)
    else:
        raise AssertionError("Wrong annual transform was accepted")

    stale = root / "stale.parquet"
    stale.write_bytes(b"not-a-production-table")
    cleared = MODULE.clear_failed_output(stale)
    assert cleared == {
        "stale_output_removed": True,
        "output_path_absent_after_failure": True,
    }
    assert not stale.exists()

print("MIRCA rice-season aggregation tests passed")
