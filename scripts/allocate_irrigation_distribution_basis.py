#!/usr/bin/env python3
"""Build a direct precipitation-pattern candidate basis before irrigation weighting.

The output contains one aggregate GDHY outcome row and a versioned set of
rainfall-quantity, within-season distribution, dry-spell, wet-extreme, and
temperature-control basis columns. Every nonlinear quantity is constructed
inside each calendar/irrigation regime before fixed MIRCA area weighting.

This is a data-contract and candidate-feature builder. It does not select a
wet-day definition, freeze a response model, fit a coefficient, or authorize a
damage or SCC input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from allocate_outcome_exposures import (
    PANEL_REQUIRED,
    allocate,
    read_table,
    require_columns,
    write_table,
)


CONTRACT_ID = "gdhy_aggregate_irrigation_distribution_candidate_v1"
ALLOCATION_ORDER = "regime_basis_before_fixed_area_weighting"
DEFAULT_STAGES = 3


def primitive_columns(stages: int) -> set[str]:
    columns = {
        "season_days",
        "tmean_c",
        "precip_mm",
        "wet_days_n",
        "cdd_max_days",
        "rx1day_mm",
        "rx5day_mm",
        "wet_day_threshold_mm",
    }
    for stage in range(1, stages + 1):
        prefix = f"stage{stage}_"
        columns.update(
            {
                f"{prefix}stage_days",
                f"{prefix}tmean_c",
                f"{prefix}precip_mm",
                f"{prefix}wet_days_n",
                f"{prefix}cdd_max_days",
                f"{prefix}rx1day_mm",
                f"{prefix}rx5day_mm",
            }
        )
    return columns


def basis_feature_names(stages: int) -> list[str]:
    features = [
        "season_days",
        "tmean_c",
        "precip_mm",
        "log1p_precip_mm",
        "wet_days_n",
        "wet_day_frequency",
        "mean_wet_day_intensity_mm",
        "cdd_max_days",
        "cdd_fraction",
        "rx1day_mm",
        "rx5day_mm",
        "tmean_x_log1p_precip",
        "zero_precipitation_season",
        "precipitation_concentration_hhi",
        "precipitation_timing_centroid",
    ]
    for stage in range(1, stages + 1):
        prefix = f"stage{stage}_"
        features.extend(
            [
                f"{prefix}stage_days",
                f"{prefix}tmean_c",
                f"{prefix}precip_mm",
                f"{prefix}log1p_precip_mm",
                f"{prefix}precip_share",
                f"{prefix}wet_days_n",
                f"{prefix}wet_day_frequency",
                f"{prefix}mean_wet_day_intensity_mm",
                f"{prefix}cdd_max_days",
                f"{prefix}cdd_fraction",
                f"{prefix}rx1day_mm",
                f"{prefix}rx5day_mm",
                f"{prefix}tmean_x_log1p_precip",
            ]
        )
    return features


def _validate_window(
    frame: pd.DataFrame,
    *,
    days: str,
    precip: str,
    wet_days: str,
    cdd: str,
    rx1: str,
    rx5: str,
    label: str,
) -> None:
    values = frame[[days, precip, wet_days, cdd, rx1, rx5]].apply(
        pd.to_numeric, errors="coerce"
    )
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} primitive weather must be finite")
    if (values[days] <= 0).any() or (values[precip] < 0).any():
        raise ValueError(f"{label} has nonpositive days or negative precipitation")
    if (
        (values[wet_days] < 0)
        | (values[wet_days] > values[days])
        | (values[cdd] < 0)
        | (values[cdd] > values[days])
    ).any():
        raise ValueError(f"{label} wet/dry counts exceed its duration")
    if (
        (values[rx1] < 0)
        | (values[rx5] + 1e-12 < values[rx1])
        # Legacy float32 season totals can differ from float64 rolling sums by
        # a few 1e-5 mm; use the same sub-millimetre reconciliation tolerance
        # as the stage/season gate while still rejecting material violations.
        | (values[rx5] > values[precip] + 1e-3)
    ).any():
        raise ValueError(f"{label} Rx1day/Rx5day/total ordering fails")
    frame[[days, precip, wet_days, cdd, rx1, rx5]] = values


def build_regime_candidate_basis(
    panel: pd.DataFrame, stages: int = DEFAULT_STAGES
) -> tuple[pd.DataFrame, list[str], float]:
    """Construct all registered direct-pattern candidate columns by regime."""
    if stages < 2:
        raise ValueError("At least two crop windows are required for a distribution basis")
    require_columns(panel, PANEL_REQUIRED | primitive_columns(stages), "Exposure panel")
    frame = panel.copy()
    thresholds = pd.to_numeric(frame["wet_day_threshold_mm"], errors="coerce")
    if not np.isfinite(thresholds).all() or (thresholds <= 0).any():
        raise ValueError("wet_day_threshold_mm must be finite and positive")
    unique_thresholds = np.unique(thresholds.to_numpy(dtype=float))
    if len(unique_thresholds) != 1:
        raise ValueError("Every regime row must use one common wet-day threshold")
    threshold = float(unique_thresholds[0])

    _validate_window(
        frame,
        days="season_days",
        precip="precip_mm",
        wet_days="wet_days_n",
        cdd="cdd_max_days",
        rx1="rx1day_mm",
        rx5="rx5day_mm",
        label="season",
    )
    for stage in range(1, stages + 1):
        prefix = f"stage{stage}_"
        _validate_window(
            frame,
            days=f"{prefix}stage_days",
            precip=f"{prefix}precip_mm",
            wet_days=f"{prefix}wet_days_n",
            cdd=f"{prefix}cdd_max_days",
            rx1=f"{prefix}rx1day_mm",
            rx5=f"{prefix}rx5day_mm",
            label=f"stage {stage}",
        )

    stage_days = [f"stage{i}_stage_days" for i in range(1, stages + 1)]
    stage_precip = [f"stage{i}_precip_mm" for i in range(1, stages + 1)]
    stage_wet = [f"stage{i}_wet_days_n" for i in range(1, stages + 1)]
    if not np.allclose(frame[stage_days].sum(axis=1), frame["season_days"], rtol=0, atol=0):
        raise ValueError("Stage days do not reproduce season_days")
    if not np.allclose(frame[stage_precip].sum(axis=1), frame["precip_mm"], rtol=0, atol=1e-3):
        raise ValueError("Stage precipitation does not reproduce seasonal precipitation")
    if not np.allclose(frame[stage_wet].sum(axis=1), frame["wet_days_n"], rtol=0, atol=0):
        raise ValueError("Stage wet days do not reproduce seasonal wet days")

    features = basis_feature_names(stages)
    frame["log1p_precip_mm"] = np.log1p(frame["precip_mm"])
    frame["wet_day_frequency"] = frame["wet_days_n"] / frame["season_days"]
    frame["mean_wet_day_intensity_mm"] = np.divide(
        frame["precip_mm"],
        frame["wet_days_n"],
        out=np.zeros(len(frame), dtype=float),
        where=frame["wet_days_n"].to_numpy(dtype=float) > 0,
    )
    frame["cdd_fraction"] = frame["cdd_max_days"] / frame["season_days"]
    frame["tmean_x_log1p_precip"] = frame["tmean_c"] * frame["log1p_precip_mm"]
    frame["zero_precipitation_season"] = frame["precip_mm"].eq(0).astype(float)

    totals = frame["precip_mm"].to_numpy(dtype=float)
    stage_values = frame[stage_precip].to_numpy(dtype=float)
    shares = np.divide(
        stage_values,
        totals[:, None],
        out=np.zeros_like(stage_values),
        where=totals[:, None] > 0,
    )
    midpoints = (np.arange(stages, dtype=float) + 0.5) / stages
    frame["precipitation_concentration_hhi"] = np.square(shares).sum(axis=1)
    frame["precipitation_timing_centroid"] = (shares * midpoints).sum(axis=1)

    for index in range(stages):
        stage = index + 1
        prefix = f"stage{stage}_"
        frame[f"{prefix}log1p_precip_mm"] = np.log1p(frame[f"{prefix}precip_mm"])
        frame[f"{prefix}wet_day_frequency"] = (
            frame[f"{prefix}wet_days_n"] / frame[f"{prefix}stage_days"]
        )
        frame[f"{prefix}mean_wet_day_intensity_mm"] = np.divide(
            frame[f"{prefix}precip_mm"],
            frame[f"{prefix}wet_days_n"],
            out=np.zeros(len(frame), dtype=float),
            where=frame[f"{prefix}wet_days_n"].to_numpy(dtype=float) > 0,
        )
        frame[f"{prefix}cdd_fraction"] = (
            frame[f"{prefix}cdd_max_days"] / frame[f"{prefix}stage_days"]
        )
        frame[f"{prefix}tmean_x_log1p_precip"] = (
            frame[f"{prefix}tmean_c"] * frame[f"{prefix}log1p_precip_mm"]
        )
        frame[f"{prefix}precip_share"] = shares[:, index]
    if not np.isfinite(frame[features].to_numpy(dtype=float)).all():
        raise ValueError("Constructed candidate basis contains nonfinite values")
    return frame, features, threshold


def allocate_distribution_candidate(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
    expected: list[str],
    *,
    stages: int = DEFAULT_STAGES,
    exclude_missing_weight_cells: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    basis, features, threshold = build_regime_candidate_basis(panel, stages)
    output, audit = allocate(
        basis,
        weights,
        features,
        expected,
        exclude_missing_weight_cells=exclude_missing_weight_cells,
    )
    output["response_basis_contract_id"] = CONTRACT_ID
    output["basis_allocation_order"] = ALLOCATION_ORDER
    output["wet_day_threshold_mm"] = threshold
    output["nonlinear_post_allocation_transform_authorized"] = False
    output["direct_pattern_candidate_basis_complete"] = True
    output["production_model_form_frozen"] = False
    output["fit_authorized"] = False
    audit.update(
        {
            "response_basis_contract_id": CONTRACT_ID,
            "basis_allocation_order": ALLOCATION_ORDER,
            "basis_features": features,
            "basis_feature_count": len(features),
            "stage_count": stages,
            "wet_day_threshold_mm": threshold,
            "wet_day_threshold_status": "candidate_definition_not_production_selection",
            "direct_pattern_candidate_basis_complete": True,
            "heat_basis_included": False,
            "alternative_drought_family_included": False,
            "production_model_form_frozen": False,
            "fit_authorized": False,
            "scc_authorized": False,
        }
    )
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--expected-irrigation", action="append", required=True)
    parser.add_argument("--stages", type=int, default=DEFAULT_STAGES)
    parser.add_argument("--exclude-missing-weight-cells", action="store_true")
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    panel = pd.concat([read_table(Path(path)) for path in args.panel], ignore_index=True)
    output, audit = allocate_distribution_candidate(
        panel,
        read_table(Path(args.weights)),
        args.expected_irrigation,
        stages=args.stages,
        exclude_missing_weight_cells=args.exclude_missing_weight_cells,
    )
    audit["input_panel_files"] = [str(Path(path)) for path in args.panel]
    write_table(output, Path(args.out))
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "basis_features"}, indent=2))


if __name__ == "__main__":
    main()
