#!/usr/bin/env python3
"""Synthetic cross-year and reconciliation test for stage heat features."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


PROJECT = Path(__file__).resolve().parents[1]
KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    dates = pd.date_range("2020-12-30", "2021-01-03", freq="D")
    coords = {"time": dates, "lat": [0.25], "lon": [0.25]}
    tmax_c = np.array([28.0, 30.0, 31.0, 35.0, 29.0]).reshape(5, 1, 1)
    xr.Dataset(
        {"tasmax": (("time", "lat", "lon"), tmax_c + 273.15, {"units": "K"})},
        coords=coords,
    ).to_netcdf(root / "tasmax.nc", engine="h5netcdf")
    xr.Dataset(
        {
            "planting_day": (("lat", "lon"), [[365.0]]),
            "maturity_day": (("lat", "lon"), [[3.0]]),
        },
        coords={"lat": [0.25], "lon": [0.25]},
    ).to_netcdf(root / "calendar.nc", engine="h5netcdf")
    seasonal = root / "seasonal.parquet"
    stages = root / "stages.parquet"
    common = [
        "--tasmax", str(root / "tasmax.nc"), "--calendar", str(root / "calendar.nc"),
        "--crop", "maize", "--irrigation", "noirr", "--year-start", "2021",
        "--year-end", "2021", "--lat-start", "0", "--lat-stop", "1",
        "--threshold-c", "30", "--threshold-c", "34",
    ]
    subprocess.run(
        [sys.executable, str(PROJECT / "scripts" / "build_crop_heat_features.py"), *common, "--out", str(seasonal)],
        check=True,
    )
    seasonal_partitions = root / "seasonal-partitions"
    seasonal_partitions.mkdir()
    (seasonal_partitions / "part-1.parquet").write_bytes(seasonal.read_bytes())
    combined_seasonal = root / "combined-seasonal.parquet"
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "combine_heat_partitions.py"),
            "--directory", str(seasonal_partitions), "--expected-partitions", "1",
            "--threshold-c", "30", "--threshold-c", "34", "--out", str(combined_seasonal),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "build_crop_stage_heat_features.py"),
            *common, "--stage-fractions", "0,0.4,0.8,1", "--out", str(stages),
        ],
        check=True,
    )
    partition_dir = root / "partitions"
    partition_dir.mkdir()
    (partition_dir / "part-1.parquet").write_bytes(stages.read_bytes())
    combined_stages = root / "combined-stages.parquet"
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "combine_stage_heat_partitions.py"),
            "--directory", str(partition_dir), "--expected-partitions", "1",
            "--expected-stages", "3", "--threshold-c", "30", "--threshold-c", "34",
            "--out", str(combined_stages),
        ],
        check=True,
    )
    audit_path = root / "reconciliation.json"
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "reconcile_stage_heat_features.py"),
            "--season", str(combined_seasonal), "--stages", str(combined_stages),
            "--expected-stages", "3", "--out-audit", str(audit_path),
        ],
        check=True,
    )
    assert json.loads(audit_path.read_text())["status"] == "stage_heat_reconciled"
    season = pd.read_parquet(seasonal).iloc[0]
    stage = pd.read_parquet(stages)
    assert season.cross_year and season.plant_year == 2020 and season.season_days == 5
    assert stage.stage_id.tolist() == [1, 2, 3]
    assert stage.stage_days.sum() == season.season_days
    assert stage.tmax_30c_days.sum() == season.tmax_30c_days == 3
    assert stage.tmax_34c_days.sum() == season.tmax_34c_days == 1
    assert np.isclose(stage.tmax_30c_degree_days.sum(), season.tmax_30c_degree_days)
    assert np.isclose(stage.tmax_34c_degree_days.sum(), season.tmax_34c_degree_days)
    assert np.isclose(np.average(stage.tmax_mean_c, weights=stage.stage_days), season.tmax_mean_c)

    panel = pd.DataFrame([{**{key: season[key] for key in KEYS}, "yield_observed": True}])
    panel.to_parquet(root / "panel.parquet", index=False)
    subprocess.run(
        [
            sys.executable, str(PROJECT / "scripts" / "join_stage_heat_features.py"),
            "--panel", str(root / "panel.parquet"), "--stage-heat", str(combined_stages),
            "--expected-stages", "3", "--out", str(root / "joined.parquet"),
        ],
        check=True,
    )
    joined = pd.read_parquet(root / "joined.parquet")
    assert joined.loc[0, "stage2_tmax_34c_degree_days"] == 1.0

print("stage-heat synthetic pipeline test passed")
