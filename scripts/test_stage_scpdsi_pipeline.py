#!/usr/bin/env python3
"""Synthetic cross-year test for the historical crop-stage scPDSI builder."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


PROJECT = Path(__file__).resolve().parents[1]


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    # Reverse latitude and use -180..180 longitude to exercise exact,
    # non-interpolating coordinate normalization against the crop calendar.
    xr.Dataset(
        {"scpdsi": (("time", "latitude", "longitude"), np.array([-1.0, -3.0]).reshape(2, 1, 1))},
        coords={
            "time": pd.to_datetime(["2020-12-01", "2021-01-01"]),
            "latitude": [0.25], "longitude": [-0.25],
        },
    ).to_netcdf(root / "scpdsi.nc", engine="h5netcdf")
    xr.Dataset(
        {
            "planting_day": (("lat", "lon"), [[365.0]]),
            "maturity_day": (("lat", "lon"), [[3.0]]),
        },
        coords={"lat": [0.25], "lon": [359.75]},
    ).to_netcdf(root / "calendar.nc", engine="h5netcdf")
    output = root / "stages.parquet"
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "build_crop_stage_scpdsi_features.py"),
            "--scpdsi", str(root / "scpdsi.nc"), "--calendar", str(root / "calendar.nc"),
            "--crop", "maize", "--irrigation", "noirr", "--year-start", "2021",
            "--year-end", "2021", "--lat-start", "0", "--lat-stop", "1",
            "--threshold", "-2", "--stage-fractions", "0,0.4,0.8,1", "--out", str(output),
        ],
        check=True,
    )
    partition_dir = root / "partitions"
    partition_dir.mkdir()
    (partition_dir / "part-1.parquet").write_bytes(output.read_bytes())
    combined = root / "combined.parquet"
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "combine_stage_scpdsi_partitions.py"),
            "--directory", str(partition_dir), "--out", str(combined),
            "--expected-partitions", "1", "--expected-stages", "3", "--threshold", "-2",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "validate_stage_scpdsi_partition.py"),
            str(output), "--threshold", "-2", "--expected-stages", "3",
        ],
        check=True,
    )
    frame = pd.read_parquet(output)
    assert frame.stage_id.tolist() == [1, 2, 3]
    assert frame.stage_days.tolist() == [2, 2, 1]
    assert np.allclose(frame.scpdsi_mean, [-1.0, -3.0, -3.0])
    assert np.allclose(frame.scpdsi_min, [-1.0, -3.0, -3.0])
    assert frame.scpdsi_days_at_or_below_threshold.tolist() == [0, 2, 1]
    assert frame.monthly_index_days_covered.sum() == 5
    assert np.isclose(np.average(frame.scpdsi_mean, weights=frame.stage_days), -2.2)
    panel = frame.iloc[[0]][["harvest_year", "lat", "lon_360", "crop", "irrigation"]].copy()
    panel["yield_observed"] = True
    panel.to_parquet(root / "panel.parquet", index=False)
    joined_path = root / "joined.parquet"
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "join_stage_scpdsi_features.py"),
            "--panel", str(root / "panel.parquet"), "--stage-scpdsi", str(combined),
            "--threshold", "-2", "--expected-stages", "3", "--out", str(joined_path),
        ],
        check=True,
    )
    joined = pd.read_parquet(joined_path)
    assert joined.loc[0, "stage2_scpdsi_days_at_or_below_threshold"] == 2
    assert joined.loc[0, "drought_source_role"] == "historical_benchmark_not_future_scc_input"

print("stage-scPDSI synthetic pipeline test passed")
