#!/usr/bin/env python3
"""Build a historical scPDSI candidate basis before irrigation weighting.

CRU scPDSI is a competing climatic-water-balance representation.  This
builder deliberately emits no direct precipitation or temperature terms and
does not authorize fitting, causal interpretation, future projection, damage,
or SCC use.  Crop-calendar features are constructed separately inside each
rainfed/irrigated regime and only then combined with fixed MIRCA area shares.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from allocate_outcome_exposures import (
    KEYS as OUTCOME_KEYS,
    PANEL_REQUIRED,
    allocate,
    read_table,
    require_columns,
    validate_outcomes,
    write_table,
)
from build_crop_stage_scpdsi_features import KEYS as DROUGHT_KEYS
from scpdsi_partition_provenance import (
    sha256_file,
    validate_combined_manifest,
)
from validate_stage_scpdsi_partition import validate_frame


CONTRACT_ID = "gdhy_aggregate_irrigation_scpdsi_candidate_v1"
BASIS_ORDER = "regime_basis_before_fixed_area_weighting"
SOURCE_ROLE = "historical_benchmark_not_future_scc_input"


def basis_feature_names(stages: int) -> list[str]:
    features = [
        "season_scpdsi_mean",
        "season_scpdsi_min",
        "season_scpdsi_days_at_or_below_threshold",
        "season_scpdsi_fraction_at_or_below_threshold",
    ]
    for stage in range(1, stages + 1):
        features.extend(
            [
                f"stage{stage}_scpdsi_mean",
                f"stage{stage}_scpdsi_min",
                f"stage{stage}_scpdsi_days_at_or_below_threshold",
                f"stage{stage}_scpdsi_fraction_at_or_below_threshold",
            ]
        )
    return features


def _wide_drought(drought: pd.DataFrame, threshold: float, stages: int) -> pd.DataFrame:
    validate_frame(drought, threshold, stages)
    if drought.empty:
        return pd.DataFrame(columns=DROUGHT_KEYS)
    calendar_columns = [
        "plant_year", "cross_year", "plant_doy", "maturity_doy", "season_days"
    ]
    calendar = drought.groupby(DROUGHT_KEYS, sort=False, as_index=False)[calendar_columns].first()
    value_columns = [
        "stage_days",
        "scpdsi_mean",
        "scpdsi_min",
        "scpdsi_days_at_or_below_threshold",
    ]
    wide = drought.pivot(index=DROUGHT_KEYS, columns="stage_id", values=value_columns)
    wide.columns = [f"stage{stage}_{name}" for name, stage in wide.columns]
    return wide.reset_index().merge(calendar, on=DROUGHT_KEYS, validate="one_to_one")


def build_regime_scpdsi_basis(
    panel: pd.DataFrame,
    drought: pd.DataFrame,
    *,
    threshold: float,
    stages: int,
    expected_irrigation: list[str],
    exclude_missing_drought_cells: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, object]]:
    """Join complete drought windows and construct nonlinear terms by regime."""
    if stages < 1:
        raise ValueError("stages must be positive")
    if len(expected_irrigation) < 2 or len(expected_irrigation) != len(set(expected_irrigation)):
        raise ValueError("Declare at least two unique irrigation regimes")
    stage_days = {f"stage{stage}_stage_days" for stage in range(1, stages + 1)}
    calendar_columns = {
        "plant_year", "cross_year", "plant_doy", "maturity_doy", "season_days"
    }
    require_columns(panel, PANEL_REQUIRED | stage_days | calendar_columns, "Exposure panel")
    if panel.duplicated(OUTCOME_KEYS + ["irrigation"]).any():
        raise ValueError("Exposure panel has duplicate crop-grid-year-irrigation rows")
    if set(panel["irrigation"].dropna().astype(str).unique()) != set(expected_irrigation):
        raise ValueError("Exposure-panel irrigation labels differ from the declared set")
    # Validate outcome agreement before any support exclusion.  Otherwise a
    # malformed aggregate outcome could disappear with an incomplete drought
    # key and evade the downstream allocation check.
    validate_outcomes(panel)

    wide = _wide_drought(drought, threshold, stages)
    merged = panel.merge(
        wide,
        on=DROUGHT_KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    merged["drought_supported"] = merged["_merge"].eq("both")
    merged = merged.drop(columns="_merge")

    support = (
        merged.groupby(OUTCOME_KEYS, sort=False, dropna=False)
        .agg(
            drought_regimes=("drought_supported", "sum"),
            irrigation_regimes=("irrigation", "nunique"),
            yield_observed=("yield_observed", "first"),
        )
        .reset_index()
    )
    complete = (
        support["drought_regimes"].eq(len(expected_irrigation))
        & support["irrigation_regimes"].eq(len(expected_irrigation))
    )
    missing = support.loc[~complete]
    if len(missing) and not exclude_missing_drought_cells:
        raise ValueError(
            "One or more outcome keys lack a complete scPDSI exposure in every "
            f"irrigation regime ({len(missing)} keys; explicit exclusion not authorized)"
        )
    if len(missing):
        keep = support.loc[complete, OUTCOME_KEYS]
        merged = merged.merge(keep.assign(_keep=True), on=OUTCOME_KEYS, how="left")
        merged = merged.loc[merged["_keep"].eq(True)].drop(columns="_keep")
    if merged.empty:
        raise ValueError("No complete scPDSI-supported outcome keys remain")
    if not merged["drought_supported"].all():
        raise AssertionError("Incomplete drought rows survived whole-key exclusion")
    merged = merged.drop(columns="drought_supported")

    # The drought feature windows and direct-weather panel must use the same
    # planting/maturity dates, not merely windows of equal duration.
    for name in ("plant_year", "plant_doy", "maturity_doy", "season_days"):
        panel_name, drought_name = f"{name}_x", f"{name}_y"
        if panel_name not in merged or drought_name not in merged:
            raise ValueError(f"Calendar field {name} was not joined from both sources")
        panel_values = pd.to_numeric(merged[panel_name], errors="coerce")
        drought_values = pd.to_numeric(merged[drought_name], errors="coerce")
        if not np.isfinite(panel_values).all() or not np.isfinite(drought_values).all():
            raise ValueError(f"Calendar field {name} must be finite")
        if not np.array_equal(panel_values.to_numpy(dtype=int), drought_values.to_numpy(dtype=int)):
            raise ValueError(f"Direct-weather and scPDSI {name} values differ")
        merged[name] = panel_values.to_numpy(dtype=int)
        merged = merged.drop(columns=[panel_name, drought_name])
    for name in ("cross_year",):
        panel_name, drought_name = f"{name}_x", f"{name}_y"
        if panel_name not in merged or drought_name not in merged:
            raise ValueError(f"Calendar field {name} was not joined from both sources")
        if not merged[panel_name].astype(bool).equals(merged[drought_name].astype(bool)):
            raise ValueError(f"Direct-weather and scPDSI {name} values differ")
        merged[name] = merged[panel_name].astype(bool)
        merged = merged.drop(columns=[panel_name, drought_name])

    for stage in range(1, stages + 1):
        # pandas suffixes both copies because panel and drought carry stage days.
        panel_days_name = f"stage{stage}_stage_days_x"
        drought_days_name = f"stage{stage}_stage_days_y"
        if panel_days_name not in merged or drought_days_name not in merged:
            raise ValueError(f"Stage {stage} length columns were not joined from both sources")
        panel_days = pd.to_numeric(merged[panel_days_name], errors="coerce")
        drought_days = pd.to_numeric(merged[drought_days_name], errors="coerce")
        if not np.isfinite(panel_days).all() or not np.isfinite(drought_days).all():
            raise ValueError("Stage lengths must be finite")
        if not np.array_equal(panel_days.to_numpy(dtype=int), drought_days.to_numpy(dtype=int)):
            raise ValueError(f"Panel and scPDSI stage {stage} lengths differ")
        merged[f"stage{stage}_stage_days"] = panel_days.to_numpy(dtype=int)
        merged = merged.drop(columns=[panel_days_name, drought_days_name])

    features = basis_feature_names(stages)
    day_columns = [f"stage{stage}_stage_days" for stage in range(1, stages + 1)]
    mean_columns = [f"stage{stage}_scpdsi_mean" for stage in range(1, stages + 1)]
    min_columns = [f"stage{stage}_scpdsi_min" for stage in range(1, stages + 1)]
    count_columns = [
        f"stage{stage}_scpdsi_days_at_or_below_threshold"
        for stage in range(1, stages + 1)
    ]
    numeric_columns = day_columns + mean_columns + min_columns + count_columns
    numeric = merged[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("scPDSI candidate inputs must be finite")
    merged[numeric_columns] = numeric
    season_days = merged[day_columns].sum(axis=1)
    if (season_days <= 0).any():
        raise ValueError("Crop seasons must have positive duration")
    merged["season_scpdsi_mean"] = sum(
        merged[mean] * merged[days] for mean, days in zip(mean_columns, day_columns)
    ) / season_days
    merged["season_scpdsi_min"] = merged[min_columns].min(axis=1)
    merged["season_scpdsi_days_at_or_below_threshold"] = merged[count_columns].sum(axis=1)
    merged["season_scpdsi_fraction_at_or_below_threshold"] = (
        merged["season_scpdsi_days_at_or_below_threshold"] / season_days
    )
    for stage in range(1, stages + 1):
        merged[f"stage{stage}_scpdsi_fraction_at_or_below_threshold"] = (
            merged[f"stage{stage}_scpdsi_days_at_or_below_threshold"]
            / merged[f"stage{stage}_stage_days"]
        )
    if not np.isfinite(merged[features].to_numpy(dtype=float)).all():
        raise ValueError("Constructed scPDSI basis contains nonfinite values")
    fraction_columns = [name for name in features if "fraction_at_or_below" in name]
    if ((merged[fraction_columns] < 0) | (merged[fraction_columns] > 1)).any().any():
        raise ValueError("scPDSI threshold fractions must lie in [0, 1]")

    audit = {
        "drought_source_role": SOURCE_ROLE,
        "drought_index_name": "CRU_TS_scpdsi",
        "scpdsi_threshold": float(threshold),
        "threshold_status": "diagnostic_candidate_not_production_selection",
        "original_outcome_keys_before_drought_coverage": int(len(support)),
        "original_observed_outcomes_before_drought_coverage": int(support["yield_observed"].sum()),
        "excluded_outcome_keys_missing_drought": int(len(missing)),
        "excluded_observed_outcomes_missing_drought": int(missing["yield_observed"].sum()),
        "drought_coverage_policy": (
            "exclude_entire_crop_grid_year_if_any_regime_missing_without_infill"
            if exclude_missing_drought_cells
            else "fail_closed"
        ),
        "remaining_regime_rows_before_weight_allocation": int(len(merged)),
    }
    return merged, features, audit


def allocate_scpdsi_candidate(
    panel: pd.DataFrame,
    drought: pd.DataFrame,
    weights: pd.DataFrame,
    expected_irrigation: list[str],
    *,
    threshold: float,
    stages: int = 3,
    exclude_missing_drought_cells: bool = False,
    exclude_missing_weight_cells: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    basis, features, coverage_audit = build_regime_scpdsi_basis(
        panel,
        drought,
        threshold=threshold,
        stages=stages,
        expected_irrigation=expected_irrigation,
        exclude_missing_drought_cells=exclude_missing_drought_cells,
    )
    output, audit = allocate(
        basis,
        weights,
        features,
        expected_irrigation,
        exclude_missing_weight_cells=exclude_missing_weight_cells,
    )
    output["response_basis_contract_id"] = CONTRACT_ID
    output["basis_allocation_order"] = BASIS_ORDER
    output["water_stress_family"] = "climatic_water_balance_scpdsi"
    output["drought_source_role"] = SOURCE_ROLE
    output["scpdsi_threshold"] = float(threshold)
    output["direct_weather_terms_included"] = False
    output["fit_authorized"] = False
    output["causal_interpretation_authorized"] = False
    output["future_projection_authorized"] = False
    audit.update(coverage_audit)
    audit.update(
        {
            "response_basis_contract_id": CONTRACT_ID,
            "basis_allocation_order": BASIS_ORDER,
            "water_stress_family": "climatic_water_balance_scpdsi",
            "basis_features": features,
            "basis_feature_count": len(features),
            "stage_count": stages,
            "direct_weather_terms_included": False,
            "competing_family_not_stacked": True,
            "fit_authorized": False,
            "causal_interpretation_authorized": False,
            "future_projection_authorized": False,
            "scc_authorized": False,
        }
    )
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--stage-scpdsi", action="append", required=True)
    parser.add_argument("--stage-scpdsi-manifest", action="append", required=True)
    parser.add_argument("--raw-scpdsi", required=True)
    parser.add_argument("--calendar", action="append", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--expected-irrigation", action="append", required=True)
    parser.add_argument("--expected-crop", required=True)
    parser.add_argument("--expected-year-start", type=int, required=True)
    parser.add_argument("--expected-year-end", type=int, required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--stages", type=int, default=3)
    parser.add_argument("--exclude-missing-drought-cells", action="store_true")
    parser.add_argument("--exclude-missing-weight-cells", action="store_true")
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    panel_paths = [Path(path) for path in args.panel]
    drought_paths = [Path(path) for path in args.stage_scpdsi]
    drought_manifest_paths = [Path(path) for path in args.stage_scpdsi_manifest]
    calendar_paths = [Path(path) for path in args.calendar]
    if not (
        len(panel_paths)
        == len(drought_paths)
        == len(drought_manifest_paths)
        == len(calendar_paths)
        == len(args.expected_irrigation)
    ):
        raise ValueError(
            "Declare one ordered stage table, source manifest, calendar, and irrigation label per regime"
        )
    raw_scpdsi_path = Path(args.raw_scpdsi)
    combined_manifests = [
        validate_combined_manifest(
            manifest_path,
            drought_path,
            scpdsi_path=raw_scpdsi_path,
            calendar_path=calendar_path,
            expected_crop=args.expected_crop,
            expected_irrigation=irrigation,
            expected_year_start=args.expected_year_start,
            expected_year_end=args.expected_year_end,
            expected_stages=args.stages,
            expected_threshold=args.threshold,
        )
        for manifest_path, drought_path, calendar_path, irrigation in zip(
            drought_manifest_paths, drought_paths, calendar_paths, args.expected_irrigation
        )
    ]
    weights_path = Path(args.weights)
    panel = pd.concat([read_table(path) for path in panel_paths], ignore_index=True)
    drought_frames = [read_table(path) for path in drought_paths]
    for frame in drought_frames:
        validate_frame(frame, args.threshold, args.stages)
    drought = pd.concat(drought_frames, ignore_index=True)
    validate_frame(drought, args.threshold, args.stages)
    output, audit = allocate_scpdsi_candidate(
        panel,
        drought,
        read_table(weights_path),
        args.expected_irrigation,
        threshold=args.threshold,
        stages=args.stages,
        exclude_missing_drought_cells=args.exclude_missing_drought_cells,
        exclude_missing_weight_cells=args.exclude_missing_weight_cells,
    )
    audit["input_panel_files"] = [str(path) for path in panel_paths]
    audit["input_panel_sha256"] = [sha256_file(path) for path in panel_paths]
    audit["input_scpdsi_files"] = [str(path) for path in drought_paths]
    audit["input_scpdsi_sha256"] = [sha256_file(path) for path in drought_paths]
    audit["input_scpdsi_manifest_files"] = [str(path) for path in drought_manifest_paths]
    audit["input_scpdsi_manifest_sha256"] = [
        sha256_file(path) for path in drought_manifest_paths
    ]
    audit["raw_scpdsi_file"] = str(raw_scpdsi_path)
    audit["raw_scpdsi_sha256"] = sha256_file(raw_scpdsi_path)
    audit["crop_calendar_files"] = [str(path) for path in calendar_paths]
    audit["crop_calendar_sha256"] = [sha256_file(path) for path in calendar_paths]
    audit["stage_source_manifest_contract_ids"] = [
        str(manifest["contract_id"]) for manifest in combined_manifests
    ]
    audit["raw_source_and_calendar_manifest_chain_validated"] = True
    audit["full_raw_metric_recomputation_in_candidate_validator"] = False
    audit["weight_file"] = str(weights_path)
    audit["weight_file_sha256"] = sha256_file(weights_path)
    write_table(output, Path(args.out))
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "basis_features"}, indent=2))


if __name__ == "__main__":
    main()
