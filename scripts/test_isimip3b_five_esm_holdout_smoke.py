#!/usr/bin/env python3
"""Synthetic tests for the bounded five-ESM feature holdout smoke."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_five_esm_holdout_smoke import (  # noqa: E402
    FEATURES,
    assemble_training,
    evaluate_leave_one_esm_out,
)


def write_fixture(root: Path, *, bad_member: bool = False) -> Path:
    lines = [
        'schema = "isimip3b_bounded_five_esm_holdout_smoke_config_v1"',
        "[selection]",
        'scenario = "ssp370"',
        "year_start = 2016",
        "year_end = 2017",
        "expected_esm_count = 5",
    ]
    for esm_index in range(5):
        esm = f"ESM{esm_index + 1}"
        member = "r1i1p1f1"
        season_rows = []
        stage_rows = []
        for year_index, year in enumerate((2016, 2017)):
            for cell, lon in enumerate((10.25, 10.75)):
                gmst = 286.0 + 0.2 * esm_index + 0.1 * year_index
                total = 90.0 + 2.0 * cell + 3.0 * (gmst - 286.0)
                base = {
                    "harvest_year": year,
                    "lat": 1.25,
                    "lon_360": lon,
                    "crop": "mai",
                    "irrigation": "noirr",
                }
                season_rows.append({
                    **base,
                    "tmean_c": 15.0 + gmst - 286.0,
                    "precip_mm": total,
                    "wet_days_n": 20.0 + gmst - 286.0,
                    "cdd_max_days": 8.0 + gmst - 286.0,
                    "rx1day_mm": 10.0 + gmst - 286.0,
                    "rx5day_mm": 20.0 + gmst - 286.0,
                })
                for stage, share in enumerate((0.2, 0.3, 0.5), start=1):
                    stage_rows.append({**base, "stage_id": stage, "precip_mm": total * share})
        season_path = root / f"{esm}_season.parquet"
        stage_path = root / f"{esm}_stages.parquet"
        gmst_path = root / f"{esm}_gmst.parquet"
        pd.DataFrame(season_rows).to_parquet(season_path, index=False)
        pd.DataFrame(stage_rows).to_parquet(stage_path, index=False)
        gmst_member = "wrong" if bad_member and esm_index == 4 else member
        pd.DataFrame({
            "esm_id": [esm, esm],
            "member_id": [gmst_member, gmst_member],
            "scenario": ["ssp370", "ssp370"],
            "gmst_source_id": [f"source-{esm}", f"source-{esm}"],
            "year": [2016, 2017],
            "gmst_value_k": [286.0 + 0.2 * esm_index, 286.1 + 0.2 * esm_index],
        }).to_parquet(gmst_path, index=False)
        lines.extend([
            "[[cells]]",
            f'esm_id = "{esm}"',
            f'member_id = "{member}"',
            f'season_path = "{season_path}"',
            f'stage_path = "{stage_path}"',
            f'gmst_path = "{gmst_path}"',
        ])
    config = root / "config" / "smoke.toml"
    config.parent.mkdir()
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    training, metadata = assemble_training(write_fixture(root))
    assert metadata["expected_esm_count"] == 5
    assert len(training) == 5 * 2 * 2 * len(FEATURES)
    holdouts = evaluate_leave_one_esm_out(training)
    assert len(holdouts) == 5 * len(FEATURES)
    assert set(holdouts["holdout_excluded"]) == {True}
    assert np.isfinite(holdouts[["rmse", "mae", "benchmark_rmse", "benchmark_mae"]]).all().all()

with tempfile.TemporaryDirectory() as directory:
    try:
        assemble_training(write_fixture(Path(directory), bad_member=True))
    except ValueError as error:
        assert "member identity mismatch" in str(error)
    else:
        raise AssertionError("GMST member mismatch was accepted")

print("bounded five-ESM holdout smoke synthetic tests passed")
