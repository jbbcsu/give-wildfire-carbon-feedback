#!/usr/bin/env python3
"""Synthetic tests for paired climate-feature-cell comparisons."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from compare_climate_feature_cells import compare


def make_season() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "harvest_year": [2019, 2019, 2020, 2020],
            "lat": [1.0, 1.0, 1.0, 1.0],
            "lon_360": [10.0, 11.0, 10.0, 11.0],
            "crop": ["mai"] * 4,
            "irrigation": ["noirr"] * 4,
            "tmean_c": [20.0, 21.0, 22.0, 23.0],
            "precip_mm": [60.0, 90.0, 120.0, 150.0],
            "wet_days_n": [6, 9, 12, 15],
            "cdd_max_days": [4, 3, 2, 1],
            "rx1day_mm": [15.0, 20.0, 25.0, 30.0],
            "rx5day_mm": [25.0, 35.0, 45.0, 55.0],
        }
    )


def make_stages(season: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for record in season.to_dict("records"):
        for stage, share in enumerate((0.2, 0.3, 0.5), start=1):
            rows.append(
                {
                    **{key: record[key] for key in ["harvest_year", "lat", "lon_360", "crop", "irrigation"]},
                    "stage_id": stage,
                    "precip_mm": record["precip_mm"] * share,
                }
            )
    return pd.DataFrame(rows)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    reference = make_season()
    candidate = reference.copy()
    candidate["precip_mm"] += 3.0
    reference_stages = make_stages(reference)
    candidate_stages = make_stages(candidate)
    paths = {
        "reference_season": root / "reference_season.parquet",
        "reference_stages": root / "reference_stages.parquet",
        "candidate_season": root / "candidate_season.parquet",
        "candidate_stages": root / "candidate_stages.parquet",
    }
    reference.to_parquet(paths["reference_season"], index=False)
    reference_stages.to_parquet(paths["reference_stages"], index=False)
    candidate.to_parquet(paths["candidate_season"], index=False)
    candidate_stages.to_parquet(paths["candidate_stages"], index=False)
    result = compare(
        paths["reference_season"],
        paths["reference_stages"],
        paths["candidate_season"],
        paths["candidate_stages"],
        reference_label="reference",
        candidate_label="candidate",
        year_start=2019,
        year_end=2020,
    )
    assert result["result"] == "passed"
    assert result["season_rows"] == 4
    assert np.isclose(
        result["metrics"]["precip_mm"]["paired_mean_difference_candidate_minus_reference"],
        3.0,
    )
    assert np.isclose(
        result["metrics"]["precipitation_timing_centroid"][
            "paired_root_mean_square_difference"
        ],
        0.0,
    )

    broken = candidate.iloc[:-1]
    broken.to_parquet(paths["candidate_season"], index=False)
    try:
        compare(
            paths["reference_season"],
            paths["reference_stages"],
            paths["candidate_season"],
            paths["candidate_stages"],
            reference_label="reference",
            candidate_label="candidate",
            year_start=2019,
            year_end=2020,
        )
    except ValueError as error:
        assert "identical ordered keys" in str(error), error
    else:
        raise AssertionError("missing candidate key should fail closed")

    candidate.to_parquet(paths["candidate_season"], index=False)
    candidate_stages.iloc[:-1].to_parquet(paths["candidate_stages"], index=False)
    try:
        compare(
            paths["reference_season"],
            paths["reference_stages"],
            paths["candidate_season"],
            paths["candidate_stages"],
            reference_label="reference",
            candidate_label="candidate",
            year_start=2019,
            year_end=2020,
        )
    except ValueError as error:
        assert "exactly the expected stage IDs" in str(error), error
    else:
        raise AssertionError("incomplete candidate stages should fail closed")

print("paired climate-feature-cell comparison synthetic tests passed")
