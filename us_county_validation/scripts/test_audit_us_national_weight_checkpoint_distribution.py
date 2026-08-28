#!/usr/bin/env python3
"""Synthetic tests for the partial national county-weight checkpoint audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

import pandas as pd

from audit_us_national_weight_checkpoint_distribution import audit


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    receipts = root / "receipts"
    geography = root / "geography.csv"
    checkpoint = root / "checkpoint.json"
    pd.DataFrame([
        {"county_geoid": "01001", "state": "AL", "crop_county_years": 10, "feature_construction_eligible": True},
        {"county_geoid": "01003", "state": "AL", "crop_county_years": 20, "feature_construction_eligible": True},
    ]).to_csv(geography, index=False)
    checkpoint.write_text(json.dumps({
        "schema": "us_national_all_practice_nclimgrid_weight_checkpoint_v1",
        "status": "failed_closed_on_registered_weather_valid_area_gate",
        "completed_county_receipts": 2,
        "registered_counties": 4,
        "threshold_relaxed": False,
        "contract": {"sha256": "contract"},
        "failure": {"registered_minimum_weather_valid_area_relative_to_declared_land": 0.95},
    }), encoding="utf-8")
    for geoid, ratio, years in [("01001", 0.951, 10), ("01003", 1.001, 20)]:
        directory_path = receipts / f"county_geoid={geoid}"
        directory_path.mkdir(parents=True)
        weights = directory_path / "weights.parquet"
        weights.write_bytes(geoid.encode("ascii"))
        receipt = {
            "schema": "us_national_county_nclimgrid_weight_partition_v1",
            "county_geoid": geoid,
            "input_fingerprint_sha256": f"input-{geoid}",
            "input_identity": {
                "contract_sha256": "contract",
                "minimum_weather_valid_area_relative_to_declared_land": 0.95,
            },
            "output_sha256": digest(weights),
            "weight_rows": 2,
            "positive_weather_cells": 2,
            "coverage_fraction": 1.0,
            "weather_valid_area_relative_to_declared_land": ratio,
            "weather_masked_intersection_area_m2": 1.0 if geoid == "01001" else 0.0,
            "spatial_weight_sum": 1.0,
            "support_crop_county_years": years,
            "analysis_role": "historical_county_validation_weight_input_only",
            "crop_pixel_exposure": False,
            "relationship_estimated": False,
            "response_estimation_authorized": False,
            "scc_authorized": False,
        }
        (directory_path / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    result = audit(receipts, geography, checkpoint)
    assert result["completed_county_receipts"] == 2
    assert result["completed_fraction_of_registered_counties"] == 0.5
    assert result["minimum_completed_ratio_county_geoid"] == "01001"
    assert result["completed_count_below_ratio_threshold"]["0.96"] == 1
    assert result["completed_count_with_positive_masked_area"] == 1
    assert result["total_supported_crop_county_years"] == 30

    bad = receipts / "county_geoid=01001" / "receipt.json"
    value = json.loads(bad.read_text(encoding="utf-8"))
    value["weather_valid_area_relative_to_declared_land"] = 0.94
    bad.write_text(json.dumps(value), encoding="utf-8")
    try:
        audit(receipts, geography, checkpoint)
    except ValueError as error:
        assert "fails threshold" in str(error)
    else:
        raise AssertionError("a below-threshold completed receipt should fail")

print("national weight-checkpoint distribution tests passed")
