#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile
import tomllib

import numpy as np
import pandas as pd

from evaluate_isimip3b_rimex_dependence_stability import (
    COORDINATES,
    correlation_pairs,
    prepare_file_pair,
    summarize_holdouts,
)


root = Path(__file__).resolve().parents[1]
config = tomllib.loads((root / "config/isimip3b_rimex_dependence_stability_v1.toml").read_text(encoding="utf-8"))

with tempfile.TemporaryDirectory() as temporary:
    temporary = Path(temporary)
    season_rows = []
    stage_rows = []
    for year in range(2042, 2050):
        for index in range(3):
            base = {
                "lat": float(index), "lon": float(index + 10), "crop": "mai",
                "irrigation": "noirr", "center_year": year,
            }
            season_rows.append({
                **base, "season_days_21yr_mean": 100.0,
                "tmean_c_21yr_mean": 20.0 + index,
                "precip_mm_21yr_mean": 100.0 + 10 * index,
                "wet_days_n_21yr_mean": 20.0 + index,
                "cdd_max_days_21yr_mean": 10.0 - index,
                "rx1day_mm_21yr_mean": 10.0 + index,
                "rx5day_mm_21yr_mean": 20.0 + index,
            })
            for stage_id, share in enumerate((0.2, 0.3, 0.5), start=1):
                stage_rows.append({**base, "stage_id": stage_id, "precip_mm_21yr_mean": (100.0 + 10 * index) * share})
    season_path = temporary / "season.parquet"
    stage_path = temporary / "stages.parquet"
    pd.DataFrame(season_rows).to_parquet(season_path, index=False)
    pd.DataFrame(stage_rows).to_parquet(stage_path, index=False)
    prepared = prepare_file_pair(season_path, stage_path, 1e-6)
    assert set(prepared) == set(range(2042, 2050))
    assert all(list(frame.columns) == COORDINATES for frame in prepared.values())

rng = np.random.default_rng(20260903)
linked = pd.DataFrame(rng.normal(size=(100, len(COORDINATES))), columns=COORDINATES)
assert len(correlation_pairs(linked)) == 28

records = []
cells = [
    ("GFDL-ESM4", "ssp126"), ("GFDL-ESM4", "ssp370"), ("GFDL-ESM4", "ssp585"),
    ("IPSL-CM6A-LR", "ssp126"), ("IPSL-CM6A-LR", "ssp370"), ("IPSL-CM6A-LR", "ssp585"),
    ("MPI-ESM1-2-HR", "ssp126"), ("MPI-ESM1-2-HR", "ssp370"), ("MPI-ESM1-2-HR", "ssp585"),
    ("MRI-ESM2-0", "ssp126"), ("MRI-ESM2-0", "ssp370"),
]
pair_names = [
    f"rho|{left}|{right}"
    for index, left in enumerate(COORDINATES)
    for right in COORDINATES[index + 1:]
]
for esm, scenario in cells:
    for year in range(2042, 2050):
        records.append({"esm": esm, "scenario": scenario, "center_year": year, "rows": 7676, **{pair: 0.4 for pair in pair_names}})
templates = pd.DataFrame(records)
holdouts = summarize_holdouts(templates, config)
assert len(holdouts) == 7
assert all(item["passed_preregistered_stability_tolerances"] for item in holdouts)

templates.loc[templates.esm == "GFDL-ESM4", pair_names[0]] = -0.4
failed = summarize_holdouts(templates, config)
assert any(not item["passed_preregistered_stability_tolerances"] for item in failed)

print("RIME-X represented-template dependence stability evaluator tests passed")
