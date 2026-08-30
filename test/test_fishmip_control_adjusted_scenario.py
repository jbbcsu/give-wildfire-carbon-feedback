#!/usr/bin/env python3
"""Synthetic gates for the FishMIP control-adjusted scenario diagnostic."""
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
from evaluate_fishmip_control_adjusted_scenario import evaluate, load_config
from validate_fishmip_content import EXPECTED_LAT, EXPECTED_LON, expected_time


def write_file(path: Path, start: int, end: int, value: float) -> tuple[int, str]:
    meta = {"model": "boats", "climate_forcing": "gfdl-esm4", "start_year": str(start), "end_year": str(end)}
    time, units, calendar = expected_time(meta)
    values = np.full((len(time), 180, 360), value, dtype=np.float32)
    values[:, 0, :] = np.nan
    dataset = xr.Dataset(
        {"tc": (("time", "lat", "lon"), values, {"units": "g m-2"})},
        coords={"time": ("time", time, {"units": units, "calendar": calendar}), "lat": EXPECTED_LAT, "lon": EXPECTED_LON},
    )
    dataset["tc"].encoding.update({"chunksizes": (1, 180, 360), "_FillValue": np.float32(1e20), "missing_value": np.float32(1e20)})
    dataset.to_netcdf(path, engine="h5netcdf")
    raw = path.read_bytes()
    return len(raw), hashlib.sha512(raw).hexdigest()


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config_path = root / "config.toml"
    config_path.write_text(
        '''version = "test"
role = "biophysical_control_adjusted_scenario_diagnostic_not_pulse_welfare_or_scc"
model = "boats"
climate_forcing = "gfdl-esm4"
forced_scenario = "ssp126"
control_scenario = "picontrol"
historical_soc_scenario = "histsoc"
future_soc_scenario = "2015soc-from-histsoc"
historical_start_year = 2000
historical_end_year = 2001
future_start_year = 2002
future_end_year = 2003
reference_start_year = 2000
reference_end_year = 2001
support_rule = "intersection_across_control_and_forced_historical_future_files"
spatial_summary = "cosine_latitude_weighted_mean_density"
temporal_summary = "mean_of_twelve_monthly_spatial_means"
allowed_acquisition_stages = ["content_smoke", "deferred_full_matrix"]
[[reporting_periods]]
id = "future"
start_year = 2002
end_year = 2003
''',
        encoding="utf-8",
    )
    specs = [
        ("forced_historical.nc", "historical", "historical", "histsoc", 2000, 2001, 2.0, "content_smoke"),
        ("forced_future.nc", "future", "ssp126", "2015soc-from-histsoc", 2002, 2003, 2.4, "content_smoke"),
        ("control_historical.nc", "historical", "picontrol", "histsoc", 2000, 2001, 1.0, "deferred_full_matrix"),
        ("control_future.nc", "future", "picontrol", "2015soc-from-histsoc", 2002, 2003, 1.1, "deferred_full_matrix"),
    ]
    paths = []
    rows = []
    for name, period, scenario, soc, start, end, value, stage in specs:
        path = root / name
        size, digest = write_file(path, start, end, value)
        paths.append(path)
        rows.append({
            "dataset_id": name,
            "file_id": name,
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
            "file_url": f"https://example.test/{name}",
            "acquisition_stage": stage,
        })
    plan = root / "plan.csv"
    with plan.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = evaluate(load_config(config_path), config_path, plan, *paths)
    assert result["common_finite_grid_cells"] == 179 * 360
    period = result["reporting_periods"][0]
    assert abs(period["forced_relative_change"] - 0.2) < 1e-6
    assert abs(period["control_relative_change"] - 0.1) < 1e-6
    assert abs(period["difference_in_relative_changes"] - 0.1) < 1e-6
    for gate in ("forced_response_estimated", "matched_co2_pulse", "welfare_estimated", "damage_estimated", "scc_authorized"):
        assert result[gate] is False

    bad_rows = [dict(row) for row in rows]
    bad_rows[3]["soc_scenario"] = "other"
    bad_plan = root / "bad_plan.csv"
    with bad_plan.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(bad_rows[0]))
        writer.writeheader()
        writer.writerows(bad_rows)
    try:
        evaluate(load_config(config_path), config_path, bad_plan, *paths)
    except ValueError as error:
        assert "social scenarios differ" in str(error)
    else:
        raise AssertionError("mismatched social forcing passed")

print("FishMIP control-adjusted scenario synthetic tests passed")
