#!/usr/bin/env python3
"""Synthetic tests for the support-matched FishMIP scenario benchmark."""
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
from evaluate_fishmip_scenario_benchmark import evaluate, load_config
from validate_fishmip_content import EXPECTED_LAT, EXPECTED_LON, expected_time


def write_file(path: Path, model: str, start: int, end: int, scenario: str, value: float, missing_row: int) -> tuple[int, str]:
    metadata = {"model": model, "start_year": str(start), "end_year": str(end)}
    time, units, calendar = expected_time(metadata)
    values = np.full((len(time), 180, 360), value, dtype=np.float32)
    values[:, missing_row, :] = np.nan
    dataset = xr.Dataset(
        {"tc": (("time", "lat", "lon"), values, {"units": "g m-2"})},
        coords={
            "time": ("time", time, {"units": units, "calendar": calendar}),
            "lat": EXPECTED_LAT,
            "lon": EXPECTED_LON,
        },
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
role = "biophysical_scenario_benchmark_not_pulse_welfare_or_scc"
climate_forcing = "gfdl-esm4"
climate_scenario = "ssp126"
models = ["boats", "ecoocean"]
historical_start_year = 2000
historical_end_year = 2001
future_start_year = 2002
future_end_year = 2003
reference_start_year = 2000
reference_end_year = 2001
support_rule = "intersection_of_time_stable_finite_masks"
spatial_summary = "cosine_latitude_weighted_mean_density"
temporal_summary = "mean_of_twelve_monthly_spatial_means"
[[reporting_periods]]
id = "future"
start_year = 2002
end_year = 2003
''',
        encoding="utf-8",
    )
    plan = root / "plan.csv"
    rows = []
    historical = {}
    future = {}
    for model, missing_row in (("boats", 0), ("ecoocean", 1)):
        for scenario, start, end, value, target in (
            ("historical", 2000, 2001, 2.0, historical),
            ("ssp126", 2002, 2003, 3.0, future),
        ):
            path = root / f"{model}_{scenario}.nc"
            size, digest = write_file(path, model, start, end, scenario, value, missing_row)
            target[model] = path
            rows.append(
                {
                    "dataset_id": f"{model}-{scenario}", "file_id": f"{model}-{scenario}",
                    "file_url": f"https://example.test/{path.name}", "model": model,
                    "climate_forcing": "gfdl-esm4", "climate_scenario": scenario,
                    "version": "test", "start_year": start, "end_year": end,
                    "bytes": size, "sha512": digest, "acquisition_stage": "content_smoke",
                }
            )
    with plan.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = evaluate(load_config(config_path), plan, historical, future)
    assert result["result"] == "passed"
    assert result["common_finite_grid_cells"] == 178 * 360
    assert result["matched_co2_pulse"] is False
    for model in result["models"]:
        assert abs(model["reference_mean_density_g_m2"] - 2.0) < 1e-6
        period = model["reporting_periods"][0]
        assert abs(period["mean_density_g_m2"] - 3.0) < 1e-6
        assert abs(period["relative_change_from_reference"] - 0.5) < 1e-6

    bad = load_config(config_path)
    bad["models"] = ["boats"]
    try:
        evaluate(bad, plan, historical, future)
    except ValueError as error:
        assert "historical model set" in str(error)
    else:
        raise AssertionError("expected model-set failure")

print("FishMIP scenario benchmark synthetic tests passed")
