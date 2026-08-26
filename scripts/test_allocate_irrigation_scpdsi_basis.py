#!/usr/bin/env python3
"""Synthetic tests for the aggregate-outcome scPDSI candidate basis."""
from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from allocate_irrigation_scpdsi_basis import allocate_scpdsi_candidate, sha256_file
from build_crop_stage_scpdsi_features import COLUMNS
from scpdsi_partition_provenance import COMBINED_CONTRACT_ID, write_manifest
from validate_irrigation_scpdsi_basis import validate_candidate


def panel_row(lat: float, irrigation: str, observed: bool = True) -> dict[str, object]:
    return {
        "harvest_year": 2012,
        "lat": lat,
        "lon_360": 260.25,
        "crop": "mai",
        "irrigation": irrigation,
        "plant_year": 2012,
        "cross_year": False,
        "plant_doy": 100,
        "maturity_doy": 109,
        "season_days": 10,
        "yield_observed": observed,
        "yield_t_ha": 4.0 if observed else np.nan,
        "stage1_stage_days": 2,
        "stage2_stage_days": 3,
        "stage3_stage_days": 5,
        # These direct-weather fields must never leak into the competing basis.
        "precip_mm": 999.0,
        "tmean_c": 99.0,
    }


def drought_rows(lat: float, irrigation: str, means: list[float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    days = [2, 3, 5]
    counts = [2, 0, 3]
    for stage, (stage_days, mean, count) in enumerate(zip(days, means, counts), start=1):
        row = {name: None for name in COLUMNS}
        row.update(
            {
                "harvest_year": 2012,
                "plant_year": 2012,
                "lat": lat,
                "lon": 260.25,
                "lon_360": 260.25,
                "crop": "mai",
                "irrigation": irrigation,
                "cross_year": False,
                "plant_doy": 100,
                "maturity_doy": 109,
                "season_days": 10,
                "stage_id": stage,
                "stage_start_offset_day": sum(days[: stage - 1]) + 1,
                "stage_end_offset_day": sum(days[:stage]),
                "stage_days": stage_days,
                "stage_fractions": "0,0.2,0.5,1",
                "scpdsi_mean": mean,
                "scpdsi_min": mean - 0.5,
                "scpdsi_days_at_or_below_threshold": count,
                "scpdsi_threshold": -2.0,
                "monthly_index_days_covered": stage_days,
                "drought_index_name": "CRU_TS_scpdsi",
                "drought_source_role": "historical_benchmark_not_future_scc_input",
            }
        )
        rows.append(row)
    return rows


def weight_rows(lat: float) -> list[dict[str, object]]:
    return [
        {
            "lat": lat,
            "lon_360": 260.25,
            "crop": "mai",
            "irrigation": irrigation,
            "area_share": share,
            "weight_source_id": "synthetic_mirca",
            "weight_vintage": "fixed_2000",
            "source_role": "independent_fixed_baseline_crop_area_share",
            "production_eligible": True,
            "season_specific_share": True,
        }
        for irrigation, share in (("noirr", 0.75), ("firr", 0.25))
    ]


panel = pd.DataFrame([panel_row(40.25, "noirr"), panel_row(40.25, "firr")])
drought = pd.DataFrame(
    drought_rows(40.25, "noirr", [-3.0, -1.0, 0.0])
    + drought_rows(40.25, "firr", [-1.0, 1.0, 2.0])
)
weights = pd.DataFrame(weight_rows(40.25))
output, audit = allocate_scpdsi_candidate(
    panel,
    drought,
    weights,
    ["noirr", "firr"],
    threshold=-2.0,
)
assert len(output) == 1
row = output.iloc[0]
noirr_season_mean = (-3.0 * 2 - 1.0 * 3 + 0.0 * 5) / 10
firr_season_mean = (-1.0 * 2 + 1.0 * 3 + 2.0 * 5) / 10
assert np.isclose(row["season_scpdsi_mean"], 0.75 * noirr_season_mean + 0.25 * firr_season_mean)
assert np.isclose(row["season_scpdsi_fraction_at_or_below_threshold"], 0.5)
assert np.isclose(row["stage1_scpdsi_mean"], -2.5)
assert "precip_mm" not in output and "tmean_c" not in output
assert row["water_stress_family"] == "climatic_water_balance_scpdsi"
assert bool(row["fit_authorized"]) is False
assert bool(row["scc_authorized"]) is False
assert audit["basis_allocation_order"] == "regime_basis_before_fixed_area_weighting"
assert audit["competing_family_not_stacked"] is True


# Missing one irrigation-regime drought row must fail by default and, when
# explicitly excluded, remove the complete outcome key rather than one regime.
panel_two = pd.concat(
    [
        panel,
        pd.DataFrame([panel_row(41.25, "noirr", False), panel_row(41.25, "firr", False)]),
    ],
    ignore_index=True,
)
drought_two = pd.concat(
    [
        drought,
        pd.DataFrame(drought_rows(41.25, "noirr", [-2.0, -2.0, -2.0])),
    ],
    ignore_index=True,
)
weights_two = pd.DataFrame(weight_rows(40.25) + weight_rows(41.25))
try:
    allocate_scpdsi_candidate(
        panel_two,
        drought_two,
        weights_two,
        ["noirr", "firr"],
        threshold=-2.0,
    )
except ValueError as error:
    assert "explicit exclusion not authorized" in str(error)
else:
    raise AssertionError("Missing regime-specific drought exposure should fail closed")

filtered, filtered_audit = allocate_scpdsi_candidate(
    panel_two,
    drought_two,
    weights_two,
    ["noirr", "firr"],
    threshold=-2.0,
    exclude_missing_drought_cells=True,
)
assert len(filtered) == 1
assert filtered_audit["excluded_outcome_keys_missing_drought"] == 1
assert filtered_audit["excluded_observed_outcomes_missing_drought"] == 0


# Outcome disagreement must fail before an incomplete drought key can be
# explicitly excluded.
bad_outcome_panel = panel_two.copy()
bad_outcome_panel.loc[
    bad_outcome_panel["lat"].eq(41.25) & bad_outcome_panel["irrigation"].eq("firr"),
    ["yield_observed", "yield_t_ha"],
] = [True, 5.0]
try:
    allocate_scpdsi_candidate(
        bad_outcome_panel,
        drought_two,
        weights_two,
        ["noirr", "firr"],
        threshold=-2.0,
        exclude_missing_drought_cells=True,
    )
except ValueError as error:
    assert "Outcome missingness differs" in str(error)
else:
    raise AssertionError("Malformed outcomes must not be hidden by drought-support exclusion")


bad_role = drought.copy()
bad_role.loc[0, "drought_source_role"] = "future_scc_input"
try:
    allocate_scpdsi_candidate(
        panel,
        bad_role,
        weights,
        ["noirr", "firr"],
        threshold=-2.0,
    )
except ValueError as error:
    assert "historical-benchmark-only" in str(error)
else:
    raise AssertionError("Unauthorized drought source role should fail")


shifted_calendar = drought.copy()
shifted_calendar["plant_doy"] += 1
shifted_calendar["maturity_doy"] += 1
try:
    allocate_scpdsi_candidate(
        panel,
        shifted_calendar,
        weights,
        ["noirr", "firr"],
        threshold=-2.0,
    )
except ValueError as error:
    assert "plant_doy values differ" in str(error)
else:
    raise AssertionError("Equal-length but shifted crop calendars must fail")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    panel_paths: list[Path] = []
    drought_paths: list[Path] = []
    for irrigation in ("noirr", "firr"):
        panel_path = root / f"{irrigation}_panel.parquet"
        drought_path = root / f"{irrigation}_scpdsi.parquet"
        panel.loc[panel["irrigation"].eq(irrigation)].to_parquet(panel_path, index=False)
        drought.loc[drought["irrigation"].eq(irrigation)].to_parquet(drought_path, index=False)
        panel_paths.append(panel_path)
        drought_paths.append(drought_path)
    weights_path = root / "weights.parquet"
    raw_scpdsi_path = root / "raw_scpdsi.nc"
    raw_scpdsi_path.write_bytes(b"synthetic raw scpdsi")
    candidate_path = root / "candidate.parquet"
    audit_path = root / "audit.json"
    calendar_paths: list[Path] = []
    drought_manifest_paths: list[Path] = []
    weights.to_parquet(weights_path, index=False)
    output.to_parquet(candidate_path, index=False)
    for irrigation, drought_path in zip(("noirr", "firr"), drought_paths):
        calendar_path = root / f"{irrigation}_calendar.nc"
        calendar_path.write_bytes(f"synthetic {irrigation} calendar".encode())
        calendar_paths.append(calendar_path)
        manifest_path = root / f"{irrigation}_combined_manifest.json"
        write_manifest(
            manifest_path,
            {
                "schema_version": 1,
                "contract_id": COMBINED_CONTRACT_ID,
                "output_file": str(drought_path.resolve()),
                "output_sha256": sha256_file(drought_path),
                "output_rows": int(len(pd.read_parquet(drought_path))),
                "scpdsi_source_file": str(raw_scpdsi_path.resolve()),
                "scpdsi_source_sha256": sha256_file(raw_scpdsi_path),
                "calendar_source_file": str(calendar_path.resolve()),
                "calendar_source_sha256": sha256_file(calendar_path),
                "crop": "mai",
                "irrigation": irrigation,
                "year_start": 2012,
                "year_end": 2012,
                "expected_stages": 3,
                "threshold": -2.0,
                "partition_source_manifests_validated": True,
                "complete_latitude_partition_coverage": True,
            },
        )
        drought_manifest_paths.append(manifest_path)
    audit.update(
        {
            "input_panel_files": [str(path) for path in panel_paths],
            "input_panel_sha256": [sha256_file(path) for path in panel_paths],
            "input_scpdsi_files": [str(path) for path in drought_paths],
            "input_scpdsi_sha256": [sha256_file(path) for path in drought_paths],
            "input_scpdsi_manifest_files": [str(path) for path in drought_manifest_paths],
            "input_scpdsi_manifest_sha256": [
                sha256_file(path) for path in drought_manifest_paths
            ],
            "raw_scpdsi_file": str(raw_scpdsi_path),
            "raw_scpdsi_sha256": sha256_file(raw_scpdsi_path),
            "crop_calendar_files": [str(path) for path in calendar_paths],
            "crop_calendar_sha256": [sha256_file(path) for path in calendar_paths],
            "stage_source_manifest_contract_ids": [COMBINED_CONTRACT_ID, COMBINED_CONTRACT_ID],
            "raw_source_and_calendar_manifest_chain_validated": True,
            "full_raw_metric_recomputation_in_candidate_validator": False,
            "weight_file": str(weights_path),
            "weight_file_sha256": sha256_file(weights_path),
        }
    )
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validated = validate_candidate(
        candidate_path,
        audit_path,
        panel_paths,
        drought_paths,
        drought_manifest_paths,
        raw_scpdsi_path,
        calendar_paths,
        weights_path,
        expected_crop="mai",
        expected_year_start=2012,
        expected_year_end=2012,
    )
    assert validated["full_derived_allocation_recomputation_passed"] is True
    assert validated["raw_source_and_calendar_manifest_chain_passed"] is True
    assert validated["full_raw_metric_recomputation_passed"] is False
    assert validated["fit_authorized"] is False

    original_calendar = calendar_paths[0].read_bytes()
    calendar_paths[0].write_bytes(original_calendar + b" changed")
    try:
        validate_candidate(
            candidate_path,
            audit_path,
            panel_paths,
            drought_paths,
            drought_manifest_paths,
            raw_scpdsi_path,
            calendar_paths,
            weights_path,
            expected_crop="mai",
            expected_year_start=2012,
            expected_year_end=2012,
        )
    except ValueError as error:
        assert "crop-calendar SHA-256 differs" in str(error)
    else:
        raise AssertionError("A changed crop calendar must invalidate the candidate chain")
    finally:
        calendar_paths[0].write_bytes(original_calendar)

    tampered = output.copy()
    tampered.loc[0, "season_scpdsi_mean"] += 0.01
    tampered.to_parquet(candidate_path, index=False)
    try:
        validate_candidate(
            candidate_path,
            audit_path,
            panel_paths,
            drought_paths,
            drought_manifest_paths,
            raw_scpdsi_path,
            calendar_paths,
            weights_path,
            expected_crop="mai",
            expected_year_start=2012,
            expected_year_end=2012,
        )
    except AssertionError:
        pass
    else:
        raise AssertionError("A tampered candidate should fail full recomputation")

print("aggregate-outcome scPDSI candidate-basis tests passed")
