#!/usr/bin/env python3
"""Adversarial synthetic tests for the aggregate-irrigation heat basis."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from allocate_irrigation_heat_basis import (
    FALSE_GATES,
    allocate_heat_control_candidate,
    bind_file_provenance,
    heat_basis_feature_names,
)
from allocate_outcome_exposures import read_table, write_table
from build_crop_heat_features import threshold_name
from validate_irrigation_heat_basis import validate_candidate, validate_candidate_frame


THRESHOLDS = [29.0, 30.0]
REGIMES = ["noirr", "firr"]
STAGES = 3


def expect_failure(function, text: str | None = None) -> None:
    try:
        function()
    except (ValueError, AssertionError) as error:
        if text is not None and text not in str(error):
            raise AssertionError(f"Expected failure containing {text!r}, received {error!r}") from error
    else:
        raise AssertionError("Expected fail-closed validation error")


def heat_metrics(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    result: dict[str, float | int] = {"tmax_mean_c": float(array.mean())}
    for threshold in THRESHOLDS:
        name = threshold_name(threshold)
        result[f"{name}_days"] = int((array >= threshold).sum())
        result[f"{name}_degree_days"] = float(np.maximum(array - threshold, 0).sum())
    return result


def fixture() -> tuple[list[pd.DataFrame], list[pd.DataFrame], list[pd.DataFrame], pd.DataFrame]:
    weather = {
        "noirr": [
            [25.0, 31.0, 35.0, 36.0, 28.0, 33.0],
            [20.0, 29.0, 30.0, 34.0, 31.0, 32.0],
        ],
        "firr": [
            [28.0, 29.0, 29.0, 34.0, 28.0, 35.0],
            [27.0, 30.0, 33.0, 35.0, 29.0, 31.0],
        ],
    }
    panels: list[pd.DataFrame] = []
    seasons: list[pd.DataFrame] = []
    stages: list[pd.DataFrame] = []
    for regime in REGIMES:
        panel_rows: list[dict[str, object]] = []
        season_rows: list[dict[str, object]] = []
        stage_rows: list[dict[str, object]] = []
        plant_doy = 100 if regime == "noirr" else 120
        for index, values in enumerate(weather[regime]):
            lat = 1.25 + index
            lon = 10.25 + index
            outcome = {
                "harvest_year": 2020,
                "lat": lat,
                "lon_360": lon,
                "crop": "mai",
                "irrigation": regime,
            }
            calendar = {
                "plant_year": 2020,
                "lon": lon,
                "cross_year": False,
                "plant_doy": plant_doy,
                "maturity_doy": plant_doy + 5,
                "season_days": 6,
            }
            panel_rows.append(
                {
                    **outcome,
                    **calendar,
                    "yield_observed": True,
                    "yield_t_ha": 5.0 + index,
                    "stage1_stage_days": 2,
                    "stage2_stage_days": 2,
                    "stage3_stage_days": 2,
                    "stage1_tmean_c": float(np.mean(values[:2]) - 5.0),
                    "stage2_tmean_c": float(np.mean(values[2:4]) - 5.0),
                    "stage3_tmean_c": float(np.mean(values[4:]) - 5.0),
                    # A moisture input is intentionally present upstream; it
                    # must not leak into the heat-only output.
                    "precip_mm": 100.0 + index,
                }
            )
            season_rows.append({**outcome, **calendar, **heat_metrics(values)})
            for stage_id, subset in enumerate((values[:2], values[2:4], values[4:]), start=1):
                start = 1 + 2 * (stage_id - 1)
                stage_rows.append(
                    {
                        **outcome,
                        "plant_year": 2020,
                        "lon": lon,
                        "cross_year": False,
                        "stage_id": stage_id,
                        "stage_start_offset_day": start,
                        "stage_end_offset_day": start + 1,
                        "stage_days": 2,
                        "stage_fractions": "0,0.3333333333,0.6666666667,1",
                        **heat_metrics(subset),
                    }
                )
        panels.append(pd.DataFrame(panel_rows))
        seasons.append(pd.DataFrame(season_rows))
        stages.append(pd.DataFrame(stage_rows))
    weight_rows = []
    for index in range(2):
        for regime, share in (("noirr", 0.25), ("firr", 0.75)):
            weight_rows.append(
                {
                    "lat": 1.25 + index,
                    "lon_360": 10.25 + index,
                    "crop": "mai",
                    "irrigation": regime,
                    "area_share": share,
                    "weight_source_id": "mirca_os_v2_synthetic",
                    "weight_vintage": "2000",
                    "source_role": "independent_fixed_baseline_crop_area_share",
                    "production_eligible": True,
                    "season_specific_share": True,
                }
            )
    return panels, seasons, stages, pd.DataFrame(weight_rows)


def build(
    panels: list[pd.DataFrame],
    seasons: list[pd.DataFrame],
    stages: list[pd.DataFrame],
    weights: pd.DataFrame,
    **policies: bool,
) -> tuple[pd.DataFrame, dict[str, object]]:
    return allocate_heat_control_candidate(
        panels,
        seasons,
        stages,
        weights,
        REGIMES,
        expected_crop="mai",
        expected_year_start=2020,
        expected_year_end=2020,
        thresholds=THRESHOLDS,
        stages=STAGES,
        **policies,
    )


def write_bundle(
    root: Path,
) -> tuple[Path, Path, list[Path], list[Path], list[Path], Path]:
    panels, seasons, stages, weights = fixture()
    panel_paths = [root / f"{regime}_panel.parquet" for regime in REGIMES]
    season_paths = [root / f"{regime}_season.parquet" for regime in REGIMES]
    stage_paths = [root / f"{regime}_stage.parquet" for regime in REGIMES]
    for frame, path in zip(panels, panel_paths):
        write_table(frame, path)
    for frame, path in zip(seasons, season_paths):
        write_table(frame, path)
    for frame, path in zip(stages, stage_paths):
        write_table(frame, path)
    weights_path = root / "weights.parquet"
    write_table(weights, weights_path)
    candidate_path = root / "candidate.parquet"
    audit_path = root / "audit.json"
    candidate, audit = build(panels, seasons, stages, weights)
    write_table(candidate, candidate_path)
    audit = bind_file_provenance(
        audit,
        panel_paths=panel_paths,
        season_heat_paths=season_paths,
        stage_heat_paths=stage_paths,
        weights_path=weights_path,
        candidate_path=candidate_path,
    )
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return candidate_path, audit_path, panel_paths, season_paths, stage_paths, weights_path


def validate_bundle(
    candidate: Path,
    audit: Path,
    panels: list[Path],
    seasons: list[Path],
    stages: list[Path],
    weights: Path,
) -> dict[str, object]:
    return validate_candidate(
        candidate,
        audit,
        panels,
        seasons,
        stages,
        weights,
        REGIMES,
        expected_crop="mai",
        expected_year_start=2020,
        expected_year_end=2020,
        thresholds=THRESHOLDS,
        stages=STAGES,
    )


panels, seasons, stages, weights = fixture()
candidate, audit = build(panels, seasons, stages, weights)
features = heat_basis_feature_names(THRESHOLDS, STAGES)
assert not any("precip" in name or "scpdsi" in name or "spei" in name for name in features)
assert candidate.loc[candidate["lat"].eq(1.25), "stage1_tmean_c"].iloc[0] == 23.375
assert candidate.loc[candidate["lat"].eq(1.25), "stage1_tmax_30c_days"].iloc[0] == 0.25
assert audit["weight_renormalization_performed"] is False
assert audit["upstream_raw_daily_heat_recomputation_performed"] is False
assert all(not candidate[flag].any() for flag in FALSE_GATES)

# Outcome disagreement across the two direct panels cannot be hidden by heat
# support or allocation.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_panels[1].loc[0, "yield_t_ha"] += 0.5
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "Yield values differ")

# Equal-duration but shifted calendars are not interchangeable.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_panels[0]["plant_doy"] += 1
bad_panels[0]["maturity_doy"] += 1
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "plant_doy")

# One direct regime missing from an outcome key is a hard contract failure.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_panels[1] = bad_panels[1].iloc[:1].copy()
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "identical")

# Missing heat is excluded only as a complete outcome key under explicit
# authorization; no surviving regime is reweighted.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_seasons[1] = bad_seasons[1].loc[bad_seasons[1]["lat"].eq(1.25)].copy()
bad_stages[1] = bad_stages[1].loc[bad_stages[1]["lat"].eq(1.25)].copy()
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "whole-key exclusion")
reduced, reduced_audit = build(
    bad_panels,
    bad_seasons,
    bad_stages,
    bad_weights,
    exclude_missing_heat_cells=True,
)
assert len(reduced) == 1 and reduced.iloc[0]["lat"] == 1.25
assert reduced_audit["excluded_outcome_keys_missing_heat"] == 1

# Missing MIRCA support also requires explicit whole-key exclusion.  Shares
# within retained cells are never renormalized.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
missing_cell_weights = bad_weights.loc[bad_weights["lat"].eq(1.25)].copy()
expect_failure(
    lambda: build(bad_panels, bad_seasons, bad_stages, missing_cell_weights),
    "explicit exclusion",
)
reduced, reduced_audit = build(
    bad_panels,
    bad_seasons,
    bad_stages,
    missing_cell_weights,
    exclude_missing_weight_cells=True,
)
assert len(reduced) == 1 and reduced.iloc[0]["lat"] == 1.25
assert reduced_audit["excluded_outcome_keys_missing_weight"] == 1
bad_shares = bad_weights.copy()
bad_shares["area_share"] = 0.4
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_shares), "sum to one")

# Hotter thresholds must be nested in every immediate heat input.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_seasons[0].loc[0, "tmax_30c_days"] = bad_seasons[0].loc[0, "tmax_29c_days"] + 1
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "nested")

# A stage source can pass its own local schema yet still fail reconciliation
# to the seasonal heat product.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_stages[0].loc[0, "tmax_mean_c"] += 0.5
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "reconcile")

# Numeric weather columns and Boolean outcomes/gates cannot be represented by
# merely truthy/falsy integers.
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_seasons[0]["tmax_mean_c"] = True
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "non-Boolean numeric")
bad_panels, bad_seasons, bad_stages, bad_weights = fixture()
bad_panels[0]["yield_observed"] = 1
expect_failure(lambda: build(bad_panels, bad_seasons, bad_stages, bad_weights), "Boolean")
bad_candidate = candidate.copy()
bad_candidate["production_fit_authorized"] = 0
expect_failure(
    lambda: validate_candidate_frame(
        bad_candidate,
        audit,
        expected_crop="mai",
        expected_year_start=2020,
        expected_year_end=2020,
        thresholds=THRESHOLDS,
        stages=STAGES,
    ),
    "production_fit_authorized",
)

with tempfile.TemporaryDirectory() as temporary:
    paths = write_bundle(Path(temporary))
    receipt = validate_bundle(*paths)
    assert receipt["status"] == "validated_common_nonmoisture_heat_control_basis"
    assert receipt["source_role"] == "common_nonmoisture_controls_only"
    assert receipt["diagnostic_fit_authorized"] is True
    assert receipt["immediate_input_recomputation_passed"] is True
    assert receipt["raw_source_recomputation_performed"] is False
    assert len(receipt["source_files_sha256"]) == 8

    # A source changed after audit creation is stale even if it remains a
    # syntactically valid Parquet table.
    source_path = paths[3][0]
    original_source = source_path.read_bytes()
    changed_source = read_table(source_path)
    changed_source.loc[0, "tmax_mean_c"] += 0.01
    write_table(changed_source, source_path)
    expect_failure(lambda: validate_bundle(*paths), "SHA256")
    source_path.write_bytes(original_source)

    # Authorization and other audit tampering fail before recomputation.
    original_audit = paths[1].read_text(encoding="utf-8")
    tampered_audit = json.loads(original_audit)
    tampered_audit["production_fit_authorized"] = True
    paths[1].write_text(json.dumps(tampered_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expect_failure(lambda: validate_bundle(*paths), "production_fit_authorized")
    paths[1].write_text(original_audit, encoding="utf-8")

    # A post-weighting transform is not made legitimate by updating only the
    # candidate hash in the audit: complete immediate-input recomputation
    # detects the altered value.
    transformed = read_table(paths[0])
    transformed["stage1_tmax_30c_days"] = (
        transformed["stage1_tmean_c"] >= 30.0
    ).astype(float)
    write_table(transformed, paths[0])
    transformed_audit = json.loads(paths[1].read_text(encoding="utf-8"))
    from allocate_irrigation_heat_basis import sha256_file

    transformed_audit["candidate_sha256"] = sha256_file(paths[0])
    paths[1].write_text(
        json.dumps(transformed_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    expect_failure(lambda: validate_bundle(*paths))

print("aggregate-irrigation heat-control basis tests passed")
