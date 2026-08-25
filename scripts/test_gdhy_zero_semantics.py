#!/usr/bin/env python3
"""Synthetic regression test for source-zero handling in the GDHY join."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "scripts" / "join_gdhy_yields.py"


def run_case(values: np.ndarray, expect_success: bool) -> pd.DataFrame | None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        features = pd.DataFrame({
            "harvest_year": [2007, 2007, 2007],
            "lat": [-0.25, -0.25, -0.25],
            "lon_360": [0.25, 0.75, 1.25],
            "crop": ["soy", "soy", "soy"],
            "irrigation": ["noirr", "noirr", "noirr"],
        })
        feature_path = root / "features.parquet"
        features.to_parquet(feature_path, index=False)
        crop_root = root / "gdhy" / "soybean"
        crop_root.mkdir(parents=True)
        xr.Dataset(
            {"var": (("lat", "lon"), values.reshape(1, 3))},
            coords={"lat": [-0.25], "lon": [0.25, 0.75, 1.25]},
        ).to_netcdf(crop_root / "yield_2007.nc4", engine="h5netcdf")
        output = root / "panel.parquet"
        result = subprocess.run([
            sys.executable, str(SCRIPT), "--features", str(feature_path),
            "--gdhy-root", str(root / "gdhy"), "--out", str(output),
        ], text=True, capture_output=True)
        assert (result.returncode == 0) is expect_success, result.stderr
        return pd.read_parquet(output) if expect_success else None


panel = run_case(np.array([2.5, 0.0, np.nan]), True)
assert panel is not None
assert panel.yield_observed.tolist() == [True, False, False]
assert panel.yield_nonpositive.tolist() == [False, True, False]
assert panel.gdhy_yield_raw_t_ha.iloc[0] == 2.5
assert panel.gdhy_yield_raw_t_ha.iloc[1] == 0.0
assert pd.isna(panel.yield_t_ha.iloc[1])
assert pd.isna(panel.gdhy_yield_raw_t_ha.iloc[2])
run_case(np.array([2.5, -0.1, np.nan]), False)

print("GDHY source-zero semantics tests passed")
