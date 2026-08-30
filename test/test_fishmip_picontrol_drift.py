#!/usr/bin/env python3
"""Synthetic gates for the bounded FishMIP piControl drift diagnostic."""
from __future__ import annotations

import csv
import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_fishmip_picontrol_drift import evaluate, load_config
from validate_fishmip_content import EXPECTED_LAT, EXPECTED_LON, expected_time


def write_file(path: Path, start: int, end: int, value: float) -> tuple[int, str]:
    metadata = {"model": "boats", "climate_forcing": "gfdl-esm4", "start_year": str(start), "end_year": str(end)}
    time, units, calendar = expected_time(metadata)
    values = np.full((len(time), 180, 360), value, dtype=np.float32)
    values[:, 0, :] = np.nan
    dataset = xr.Dataset(
        {"tc": (("time", "lat", "lon"), values, {"units": "g m-2"})},
        coords={
            "time": ("time", time, {"units": units, "calendar": calendar}),
            "lat": EXPECTED_LAT,
            "lon": EXPECTED_LON,
        },
    )
    dataset["tc"].encoding.update({
        "chunksizes": (1, 180, 360),
        "_FillValue": np.float32(1e20),
        "missing_value": np.float32(1e20),
    })
    dataset.to_netcdf(path, engine="h5netcdf")
    raw = path.read_bytes()
    return len(raw), hashlib.sha512(raw).hexdigest()


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config_path = root / "config.toml"
    config_path.write_text(
        '''version = "test"
role = "biophysical_picontrol_drift_diagnostic_not_forced_response_pulse_welfare_or_scc"
model = "boats"
climate_forcing = "gfdl-esm4"
climate_scenario = "picontrol"
historical_soc_scenario = "histsoc"
future_soc_scenario = "2015soc-from-histsoc"
historical_start_year = 2000
historical_end_year = 2001
future_start_year = 2002
future_end_year = 2003
reference_start_year = 2000
reference_end_year = 2001
support_rule = "intersection_of_time_stable_finite_masks"
spatial_summary = "cosine_latitude_weighted_mean_density"
temporal_summary = "mean_of_twelve_monthly_spatial_means"
allowed_acquisition_stages = ["deferred_full_matrix"]
[[reporting_periods]]
id = "future"
start_year = 2002
end_year = 2003
''',
        encoding="utf-8",
    )
    historical = root / "boats_picontrol_historical.nc"
    future = root / "boats_picontrol_future.nc"
    rows = []
    for path, period, scenario, soc, start, end, value in (
        (historical, "historical", "picontrol", "histsoc", 2000, 2001, 2.0),
        (future, "future", "picontrol", "2015soc-from-histsoc", 2002, 2003, 2.2),
    ):
        size, digest = write_file(path, start, end, value)
        rows.append({
            "dataset_id": period,
            "file_id": period,
            "model": "boats",
            "climate_forcing": "gfdl-esm4",
            "period": period,
            "climate_scenario": scenario,
            "soc_scenario": soc,
            "version": "test",
            "start_year": start,
            "end_year": end,
            "bytes": size,
            "sha512": digest,
            "file_url": f"https://example.test/{path.name}",
            "acquisition_stage": "deferred_full_matrix",
        })
    plan = root / "plan.csv"
    with plan.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    config = load_config(config_path)
    result = evaluate(config, config_path, plan, historical, future)
    assert result["result"] == "passed"
    assert result["common_finite_grid_cells"] == 179 * 360
    assert abs(result["reference_mean_density_g_m2"] - 2.0) < 1e-6
    assert abs(result["reporting_periods"][0]["relative_change_from_reference"] - 0.1) < 1e-6
    for gate in ("forced_response_estimated", "matched_co2_pulse", "welfare_estimated", "damage_estimated", "scc_authorized"):
        assert result[gate] is False

    bad_rows = [dict(row) for row in rows]
    bad_rows[1]["climate_scenario"] = "ssp585"
    bad_plan = root / "bad_plan.csv"
    with bad_plan.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(bad_rows[0]))
        writer.writeheader()
        writer.writerows(bad_rows)
    try:
        evaluate(config, config_path, bad_plan, historical, future)
    except ValueError as error:
        assert "not picontrol" in str(error)
    else:
        raise AssertionError("forced scenario passed the piControl gate")

print("FishMIP piControl drift synthetic tests passed")
