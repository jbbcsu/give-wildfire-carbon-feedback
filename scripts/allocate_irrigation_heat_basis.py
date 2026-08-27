#!/usr/bin/env python3
"""Build a fixed-area-weighted heat-control basis for future diagnostics.

Seasonal and stage-resolved daily-maximum-temperature summaries are first
validated and represented inside each irrigation-calendar regime.  Only then
are those basis columns combined with fixed MIRCA area shares.  The output is
a narrow, common non-moisture control table; it contains no moisture predictor
and authorizes only the locked predictive diagnostic—not coefficient export,
causal interpretation, production fitting, damage calculation, future
projection, or SCC use.

The provenance record binds the immediate direct-panel, seasonal-heat,
stage-heat, and weight files.  It does not claim to recompute the heat metrics
from raw daily temperature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_outcome_exposures import (
    KEYS,
    PANEL_REQUIRED,
    allocate,
    read_table,
    require_columns,
    write_table,
)
from build_crop_heat_features import threshold_name
from heat_threshold_validation import metric_columns, validate_thresholds
from validate_heat_partition import validate_frame as validate_season_heat
from validate_stage_heat_partition import validate_frame as validate_stage_heat


CONTRACT_ID = "global_crop_stage_heat_control_basis_v1"
ALLOCATION_ORDER = "regime_basis_before_fixed_area_weighting"
THRESHOLD_STATUS = "diagnostic_nonproduction_not_selected_by_outcome_or_scc"
SOURCE_ROLE = "common_nonmoisture_controls_only"
EXPECTED_IRRIGATION = {"firr", "noirr"}
CALENDAR_FIELDS = [
    "plant_year",
    "cross_year",
    "plant_doy",
    "maturity_doy",
    "season_days",
]
FALSE_GATES = [
    "family_stacking_authorized",
    "coefficient_export_authorized",
    "causal_interpretation_authorized",
    "production_model_selection_authorized",
    "production_fit_authorized",
    "response_draw_authorized",
    "damage_calculation_authorized",
    "future_projection_authorized",
    "scc_authorized",
    "selection_by_scc_authorized",
]
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def heat_basis_feature_names(thresholds: list[float], stages: int) -> list[str]:
    ordered = validate_thresholds(thresholds)
    if stages != 3:
        raise ValueError("The locked heat-control contract requires exactly three stages")
    features: list[str] = []
    for window in [f"stage{stage}" for stage in range(1, stages + 1)]:
        features.append(f"{window}_tmean_c")
        for threshold in ordered:
            name = threshold_name(threshold)
            features.extend(
                [
                    f"{window}_{name}_days",
                    f"{window}_{name}_degree_days",
                ]
            )
    return features


def _key_index(frame: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(frame[KEYS], names=KEYS)


def _require_boolean(frame: pd.DataFrame, column: str, label: str) -> None:
    if column not in frame or not is_bool_dtype(frame[column].dtype) or frame[column].isna().any():
        raise ValueError(f"{label} {column} must be nonmissing Boolean")


def _validate_exact_scope(
    frame: pd.DataFrame,
    *,
    label: str,
    crop: str,
    irrigation: str,
    year_start: int,
    year_end: int,
    require_every_year: bool,
) -> None:
    if frame.empty:
        raise ValueError(f"{label} must be nonempty")
    if frame[KEYS].isna().any().any():
        raise ValueError(f"{label} contains missing crop-grid-year keys")
    if set(frame["crop"].astype(str).unique()) != {crop}:
        raise ValueError(f"{label} crop differs from the exact expectation")
    if set(frame["irrigation"].astype(str).unique()) != {irrigation}:
        raise ValueError(f"{label} irrigation regime differs from the path mapping")
    years = pd.to_numeric(frame["harvest_year"], errors="coerce")
    if not np.isfinite(years.to_numpy(dtype=float)).all() or not np.equal(years, np.floor(years)).all():
        raise ValueError(f"{label} harvest years must be finite integers")
    actual = set(years.astype(int).unique())
    expected = set(range(year_start, year_end + 1))
    if not actual.issubset(expected) or (require_every_year and actual != expected):
        raise ValueError(f"{label} does not satisfy the exact expected year scope")
    numeric_keys = frame[["lat", "lon_360"]].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric_keys.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} has nonfinite spatial keys")
    if (
        (numeric_keys["lat"] < -90)
        | (numeric_keys["lat"] > 90)
        | (numeric_keys["lon_360"] < 0)
        | (numeric_keys["lon_360"] >= 360)
    ).any():
        raise ValueError(f"{label} has spatial keys outside their valid bounds")


def _validate_panel(
    panel: pd.DataFrame,
    *,
    crop: str,
    irrigation: str,
    year_start: int,
    year_end: int,
    stages: int,
) -> pd.DataFrame:
    label = f"Direct candidate panel ({irrigation})"
    stage_days = [f"stage{stage}_stage_days" for stage in range(1, stages + 1)]
    stage_tmean = [f"stage{stage}_tmean_c" for stage in range(1, stages + 1)]
    require_columns(
        panel,
        PANEL_REQUIRED | set(CALENDAR_FIELDS + ["lon"] + stage_days + stage_tmean),
        label,
    )
    if panel.duplicated(KEYS + ["irrigation"]).any():
        raise ValueError(f"{label} has duplicate crop-grid-year-regime rows")
    _require_boolean(panel, "yield_observed", label)
    _require_boolean(panel, "cross_year", label)
    _validate_exact_scope(
        panel,
        label=label,
        crop=crop,
        irrigation=irrigation,
        year_start=year_start,
        year_end=year_end,
        require_every_year=True,
    )
    result = panel.copy()
    integer_fields = ["plant_year", "plant_doy", "maturity_doy", "season_days"] + stage_days
    for name in stage_tmean:
        if is_bool_dtype(result[name].dtype) or not pd.api.types.is_numeric_dtype(result[name].dtype):
            raise ValueError(f"{label} {name} must have a non-Boolean numeric dtype")
    numeric = result[integer_fields + ["lon"] + stage_tmean].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} calendar metadata must be finite numeric values")
    if not np.equal(numeric[integer_fields], np.floor(numeric[integer_fields])).all().all():
        raise ValueError(f"{label} calendar day metadata must be integers")
    if (numeric[["season_days"] + stage_days] <= 0).any().any():
        raise ValueError(f"{label} season and stage lengths must be positive")
    if not np.array_equal(
        numeric[stage_days].sum(axis=1).to_numpy(dtype=int),
        numeric["season_days"].to_numpy(dtype=int),
    ):
        raise ValueError(f"{label} stage lengths do not sum to season_days")
    result[integer_fields + ["lon"] + stage_tmean] = numeric
    return result


def _validate_heat_dtypes(frame: pd.DataFrame, thresholds: list[float], label: str) -> None:
    _require_boolean(frame, "cross_year", label)
    fields = ["tmax_mean_c"] + sorted(metric_columns(thresholds))
    invalid = [
        field
        for field in fields
        if field not in frame
        or is_bool_dtype(frame[field].dtype)
        or not pd.api.types.is_numeric_dtype(frame[field].dtype)
    ]
    if invalid:
        raise ValueError(f"{label} heat metrics must have non-Boolean numeric dtypes {invalid}")


def _validate_stage_offsets(stages_frame: pd.DataFrame, expected_stages: int, label: str) -> str:
    if not is_bool_dtype(stages_frame["cross_year"].dtype):
        raise ValueError(f"{label} cross_year must be Boolean")
    fractions = stages_frame["stage_fractions"].astype("string")
    if fractions.isna().any() or fractions.str.strip().eq("").any() or fractions.nunique() != 1:
        raise ValueError(f"{label} must use one nonblank stage-fraction definition")
    ordered = stages_frame.sort_values(KEYS + ["stage_id"], kind="mergesort").copy()
    starts = pd.to_numeric(ordered["stage_start_offset_day"], errors="coerce")
    ends = pd.to_numeric(ordered["stage_end_offset_day"], errors="coerce")
    days = pd.to_numeric(ordered["stage_days"], errors="coerce")
    if not np.isfinite(np.column_stack([starts, ends, days])).all():
        raise ValueError(f"{label} stage offsets must be finite")
    if not (
        np.equal(starts, np.floor(starts)).all()
        and np.equal(ends, np.floor(ends)).all()
        and np.equal(days, np.floor(days)).all()
    ):
        raise ValueError(f"{label} stage offsets and lengths must be integers")
    ordered["_start"] = starts.astype(int)
    ordered["_end"] = ends.astype(int)
    ordered["_days"] = days.astype(int)
    if not np.array_equal(
        (ordered["_end"] - ordered["_start"] + 1).to_numpy(),
        ordered["_days"].to_numpy(),
    ):
        raise ValueError(f"{label} stage offsets disagree with stage_days")
    grouped = ordered.groupby(KEYS, sort=False, observed=True)
    identity_counts = grouped[["plant_year", "cross_year", "lon", "stage_fractions"]].nunique(
        dropna=False
    )
    if (identity_counts > 1).any().any():
        raise ValueError(f"{label} calendar identity differs across stages")
    if not grouped["_start"].first().eq(1).all():
        raise ValueError(f"{label} first stage must start on crop-season day one")
    previous_end = grouped["_end"].shift(1)
    later_stage = ordered["stage_id"].ne(1)
    if not ordered.loc[later_stage, "_start"].eq(previous_end.loc[later_stage] + 1).all():
        raise ValueError(f"{label} stage offsets are not contiguous")
    return str(fractions.iloc[0])


def _compare_columns(
    joined: pd.DataFrame,
    left: str,
    right: str,
    label: str,
    *,
    boolean: bool = False,
) -> None:
    if boolean:
        if not joined[left].astype(bool).equals(joined[right].astype(bool)):
            raise ValueError(f"{label} differs")
        return
    lhs = pd.to_numeric(joined[left], errors="coerce")
    rhs = pd.to_numeric(joined[right], errors="coerce")
    if not np.isfinite(lhs).all() or not np.isfinite(rhs).all() or not np.array_equal(
        lhs.to_numpy(), rhs.to_numpy()
    ):
        raise ValueError(f"{label} differs")


def _validate_cross_regime_outcomes(panel: pd.DataFrame) -> None:
    """Fail on any outcome mismatch before a support exclusion can hide it."""
    observed = panel["yield_observed"]
    yields = pd.to_numeric(panel["yield_t_ha"], errors="coerce")
    if not observed.eq(yields.notna()).all():
        raise ValueError("yield_observed does not match yield_t_ha missingness")
    if not np.isfinite(yields.loc[observed]).all() or (yields.loc[observed] <= 0).any():
        raise ValueError("Observed yields must be finite and positive")
    grouped = panel.assign(_yield=yields).groupby(KEYS, sort=False, dropna=False)
    if (grouped["yield_observed"].nunique(dropna=False) != 1).any():
        raise ValueError("Outcome missingness differs across irrigation exposures")
    if (grouped["_yield"].nunique(dropna=False) != 1).any():
        raise ValueError("Yield values differ across irrigation exposures")


def _regime_heat_basis(
    panel: pd.DataFrame,
    season: pd.DataFrame,
    stage: pd.DataFrame,
    *,
    thresholds: list[float],
    stages: int,
    crop: str,
    irrigation: str,
    year_start: int,
    year_end: int,
) -> tuple[pd.DataFrame, str, dict[str, int]]:
    label = f"Heat input ({irrigation})"
    validate_season_heat(season, thresholds)
    validate_stage_heat(stage, thresholds, stages)
    _validate_heat_dtypes(season, thresholds, f"Seasonal {label}")
    _validate_heat_dtypes(stage, thresholds, f"Stage {label}")
    _validate_exact_scope(
        season,
        label=f"Seasonal {label}",
        crop=crop,
        irrigation=irrigation,
        year_start=year_start,
        year_end=year_end,
        require_every_year=False,
    )
    _validate_exact_scope(
        stage,
        label=f"Stage {label}",
        crop=crop,
        irrigation=irrigation,
        year_start=year_start,
        year_end=year_end,
        require_every_year=False,
    )
    fraction_definition = _validate_stage_offsets(stage, stages, f"Stage {label}")

    panel_keys = set(_key_index(panel).tolist())
    season_keys = set(_key_index(season).tolist())
    stage_keys = set(_key_index(stage).tolist())
    if extra := (season_keys | stage_keys) - panel_keys:
        raise ValueError(f"{label} contains {len(extra)} crop-grid-year keys without an outcome panel row")
    supported_keys = season_keys & stage_keys
    supported = pd.DataFrame(list(supported_keys), columns=KEYS)
    if supported.empty:
        return (
            pd.DataFrame(columns=KEYS + ["irrigation", "yield_observed", "yield_t_ha"]),
            fraction_definition,
            {"season_rows": len(season), "stage_rows": len(stage), "supported_rows": 0},
        )

    season_supported = season.merge(supported, on=KEYS, validate="one_to_one")
    stage_supported = stage.merge(supported, on=KEYS, validate="many_to_one")
    panel_supported = panel.merge(supported, on=KEYS, validate="one_to_one")

    # Reconcile stage summaries to the seasonal summary before any irrigation
    # weighting.  This is the only scientifically valid allocation order.
    threshold_metrics = sorted(metric_columns(thresholds))
    stage_sum = stage_supported.groupby(KEYS, as_index=False, observed=True).agg(
        stage_days=("stage_days", "sum"),
        **{f"sum__{name}": (name, "sum") for name in threshold_metrics},
    )
    weighted_tmax = (
        stage_supported.assign(_weighted=stage_supported["tmax_mean_c"] * stage_supported["stage_days"])
        .groupby(KEYS, as_index=False, observed=True)["_weighted"]
        .sum()
    )
    stage_sum = stage_sum.merge(weighted_tmax, on=KEYS, validate="one_to_one")
    reconciled = season_supported.merge(stage_sum, on=KEYS, validate="one_to_one")
    if not np.array_equal(
        reconciled["season_days"].to_numpy(dtype=int),
        reconciled["stage_days"].to_numpy(dtype=int),
    ):
        raise ValueError(f"{label} stage lengths do not reconcile to season_days")
    if not np.allclose(
        reconciled["tmax_mean_c"].to_numpy(dtype=float),
        (reconciled["_weighted"] / reconciled["stage_days"]).to_numpy(dtype=float),
        rtol=0,
        atol=1e-9,
    ):
        raise ValueError(f"{label} stage-weighted tmax mean does not reconcile to the season")
    for name in threshold_metrics:
        if not np.allclose(
            reconciled[name].to_numpy(dtype=float),
            reconciled[f"sum__{name}"].to_numpy(dtype=float),
            rtol=0,
            atol=1e-9,
        ):
            raise ValueError(f"{label} stage {name} does not reconcile to the season")

    panel_calendar = panel_supported[KEYS + ["irrigation", "lon"] + CALENDAR_FIELDS].rename(
        columns={name: f"panel__{name}" for name in ["lon"] + CALENDAR_FIELDS}
    )
    season_calendar = season_supported[KEYS + ["irrigation", "lon"] + CALENDAR_FIELDS].rename(
        columns={name: f"season__{name}" for name in ["lon"] + CALENDAR_FIELDS}
    )
    calendar = panel_calendar.merge(
        season_calendar, on=KEYS + ["irrigation"], validate="one_to_one"
    )
    for name in ["lon", "plant_year", "plant_doy", "maturity_doy", "season_days"]:
        _compare_columns(
            calendar,
            f"panel__{name}",
            f"season__{name}",
            f"Direct-panel and seasonal-heat {name} ({irrigation})",
        )
    _compare_columns(
        calendar,
        "panel__cross_year",
        "season__cross_year",
        f"Direct-panel and seasonal-heat cross_year ({irrigation})",
        boolean=True,
    )

    stage_identity = (
        stage_supported.groupby(KEYS, as_index=False, observed=True)
        .agg(plant_year=("plant_year", "first"), cross_year=("cross_year", "first"), lon=("lon", "first"))
    )
    identity = season_supported[KEYS + ["plant_year", "cross_year", "lon"]].merge(
        stage_identity, on=KEYS, validate="one_to_one", suffixes=("__season", "__stage")
    )
    for name in ("plant_year", "lon"):
        _compare_columns(
            identity,
            f"{name}__season",
            f"{name}__stage",
            f"Seasonal- and stage-heat {name} ({irrigation})",
        )
    _compare_columns(
        identity,
        "cross_year__season",
        "cross_year__stage",
        f"Seasonal- and stage-heat cross_year ({irrigation})",
        boolean=True,
    )
    for stage_id in range(1, stages + 1):
        direct_days = panel_supported.set_index(KEYS)[f"stage{stage_id}_stage_days"].sort_index()
        heat_days = (
            stage_supported.loc[stage_supported["stage_id"].eq(stage_id)]
            .set_index(KEYS)["stage_days"]
            .sort_index()
        )
        if not direct_days.index.equals(heat_days.index) or not np.array_equal(
            direct_days.to_numpy(dtype=int), heat_days.to_numpy(dtype=int)
        ):
            raise ValueError(f"Direct-panel and stage-heat stage {stage_id} lengths differ")

    basis = panel_supported[KEYS + ["irrigation", "yield_observed", "yield_t_ha"]].copy()
    for stage_id in range(1, stages + 1):
        values = stage_supported.loc[stage_supported["stage_id"].eq(stage_id)].set_index(KEYS)
        values = values.loc[_key_index(panel_supported)]
        basis[f"stage{stage_id}_tmean_c"] = panel_supported[
            f"stage{stage_id}_tmean_c"
        ].to_numpy(dtype=float)
        for threshold in thresholds:
            name = threshold_name(threshold)
            for metric in ("days", "degree_days"):
                basis[f"stage{stage_id}_{name}_{metric}"] = values[
                    f"{name}_{metric}"
                ].to_numpy(dtype=float)
    return basis, fraction_definition, {
        "season_rows": int(len(season)),
        "stage_rows": int(len(stage)),
        "supported_rows": int(len(basis)),
    }


def allocate_heat_control_candidate(
    panels: list[pd.DataFrame],
    season_heat: list[pd.DataFrame],
    stage_heat: list[pd.DataFrame],
    weights: pd.DataFrame,
    expected_irrigation: list[str],
    *,
    expected_crop: str,
    expected_year_start: int,
    expected_year_end: int,
    thresholds: list[float],
    stages: int,
    exclude_missing_heat_cells: bool = False,
    exclude_missing_weight_cells: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    thresholds = validate_thresholds(thresholds)
    if not set(thresholds).issubset({29.0, 30.0}):
        raise ValueError("Only the registered diagnostic 29 C and 30 C thresholds are allowed")
    if expected_year_end < expected_year_start:
        raise ValueError("Expected year end precedes year start")
    if stages != 3:
        raise ValueError("The locked heat-control contract requires exactly three stages")
    if (
        len(expected_irrigation) != 2
        or len(set(expected_irrigation)) != 2
        or set(expected_irrigation) != EXPECTED_IRRIGATION
    ):
        raise ValueError("Expected irrigation must declare exactly firr and noirr")
    if not (
        len(panels) == len(season_heat) == len(stage_heat) == len(expected_irrigation)
    ):
        raise ValueError("Declare one ordered panel, seasonal heat table, and stage heat table per regime")

    checked_panels = [
        _validate_panel(
            frame,
            crop=expected_crop,
            irrigation=irrigation,
            year_start=expected_year_start,
            year_end=expected_year_end,
            stages=stages,
        )
        for frame, irrigation in zip(panels, expected_irrigation)
    ]
    reference_keys = _key_index(checked_panels[0].sort_values(KEYS, kind="mergesort"))
    for frame in checked_panels[1:]:
        candidate_keys = _key_index(frame.sort_values(KEYS, kind="mergesort"))
        if not reference_keys.equals(candidate_keys):
            raise ValueError("Direct candidate panels must contain identical crop-grid-year outcome keys")
    all_panel = pd.concat(checked_panels, ignore_index=True)
    _validate_cross_regime_outcomes(all_panel)
    support = all_panel.groupby(KEYS, as_index=False, sort=True, dropna=False).agg(
        yield_observed=("yield_observed", "first"), yield_t_ha=("yield_t_ha", "first")
    )

    regime_bases: list[pd.DataFrame] = []
    fraction_definitions: list[str] = []
    source_counts: dict[str, dict[str, int]] = {}
    for panel, season, stage, irrigation in zip(
        checked_panels, season_heat, stage_heat, expected_irrigation
    ):
        basis, fractions, counts = _regime_heat_basis(
            panel,
            season,
            stage,
            thresholds=thresholds,
            stages=stages,
            crop=expected_crop,
            irrigation=irrigation,
            year_start=expected_year_start,
            year_end=expected_year_end,
        )
        regime_bases.append(basis)
        fraction_definitions.append(fractions)
        source_counts[irrigation] = counts
    if len(set(fraction_definitions)) != 1:
        raise ValueError("Irrigation regimes use different stage-fraction definitions")

    available = pd.concat(regime_bases, ignore_index=True)
    counts = available.groupby(KEYS, dropna=False)["irrigation"].agg(set)
    complete_keys = counts.index[counts.map(lambda labels: labels == set(expected_irrigation))]
    complete_index = pd.MultiIndex.from_tuples(complete_keys, names=KEYS)
    missing_mask = ~_key_index(support).isin(complete_index)
    missing = support.loc[missing_mask]
    if len(missing) and not exclude_missing_heat_cells:
        raise ValueError(
            "One or more outcome keys lack complete seasonal and stage heat in every "
            f"irrigation regime ({len(missing)} keys; explicit whole-key exclusion not authorized)"
        )
    if len(missing):
        available = available.loc[_key_index(available).isin(complete_index)].copy()
    if available.empty:
        raise ValueError("No complete heat-supported outcome keys remain")

    features = heat_basis_feature_names(thresholds, stages)
    if set(features) - set(available.columns):
        raise AssertionError("Constructed heat basis is incomplete")
    output, audit = allocate(
        available,
        weights,
        features,
        expected_irrigation,
        exclude_missing_weight_cells=exclude_missing_weight_cells,
    )
    # The downstream diagnostic intentionally accepts only exact keys,
    # outcomes, registered stage controls, and this narrow metadata set.  Rich
    # allocation/provenance metadata remains in the sidecar audit.
    output = output[KEYS + ["yield_observed", "yield_t_ha"] + features].copy()
    output["heat_control_basis_contract_id"] = CONTRACT_ID
    output["source_role"] = SOURCE_ROLE
    output["diagnostic_fit_authorized"] = True
    for flag in FALSE_GATES:
        output[flag] = False

    audit.update(
        {
            "response_basis_contract_id": CONTRACT_ID,
            "basis_allocation_order": ALLOCATION_ORDER,
            "basis_features": features,
            "basis_feature_count": len(features),
            "expected_crop": expected_crop,
            "expected_year_start": int(expected_year_start),
            "expected_year_end": int(expected_year_end),
            "stage_count": int(stages),
            "stage_fractions": fraction_definitions[0],
            "heat_thresholds_c": [float(value) for value in thresholds],
            "heat_threshold_status": THRESHOLD_STATUS,
            "source_role": SOURCE_ROLE,
            "source_row_counts_by_irrigation": source_counts,
            "original_outcome_keys_before_heat_coverage": int(len(support)),
            "original_observed_outcomes_before_heat_coverage": int(support["yield_observed"].sum()),
            "excluded_outcome_keys_missing_heat": int(len(missing)),
            "excluded_observed_outcomes_missing_heat": int(missing["yield_observed"].sum()),
            "heat_coverage_policy": (
                "exclude_entire_crop_grid_year_if_any_regime_or_heat_window_missing_without_infill"
                if exclude_missing_heat_cells
                else "fail_closed"
            ),
            "whole_outcome_key_exclusions_only": True,
            "weight_renormalization_performed": False,
            "regime_calendar_identity_validated": True,
            "stage_season_reconciliation_validated": True,
            "threshold_nesting_validated": True,
            "common_support_ready": True,
            "data_only": True,
            "moisture_terms_included": False,
            "nonlinear_post_allocation_transform_authorized": False,
            "fit_authorized": False,
            "diagnostic_fit_authorized": True,
            "immediate_input_recomputation_by_validator_required": True,
            "upstream_raw_daily_heat_recomputation_performed": False,
        }
    )
    for flag in FALSE_GATES:
        audit[flag] = False
    return output, audit


def bind_file_provenance(
    audit: dict[str, Any],
    *,
    panel_paths: list[Path],
    season_heat_paths: list[Path],
    stage_heat_paths: list[Path],
    weights_path: Path,
    candidate_path: Path,
) -> dict[str, Any]:
    result = dict(audit)
    result.update(
        {
            "input_panel_files": [str(path) for path in panel_paths],
            "input_panel_sha256": [sha256_file(path) for path in panel_paths],
            "input_season_heat_files": [str(path) for path in season_heat_paths],
            "input_season_heat_sha256": [sha256_file(path) for path in season_heat_paths],
            "input_stage_heat_files": [str(path) for path in stage_heat_paths],
            "input_stage_heat_sha256": [sha256_file(path) for path in stage_heat_paths],
            "weight_file": str(weights_path),
            "weight_file_sha256": sha256_file(weights_path),
            "candidate_file": str(candidate_path),
            "candidate_sha256": sha256_file(candidate_path),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--season-heat", action="append", required=True)
    parser.add_argument("--stage-heat", action="append", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--expected-irrigation", action="append", required=True)
    parser.add_argument("--expected-crop", required=True)
    parser.add_argument("--expected-year-start", type=int, required=True)
    parser.add_argument("--expected-year-end", type=int, required=True)
    parser.add_argument("--threshold-c", action="append", type=float, required=True)
    parser.add_argument("--stages", type=int, default=3)
    parser.add_argument("--exclude-missing-heat-cells", action="store_true")
    parser.add_argument("--exclude-missing-weight-cells", action="store_true")
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    panel_paths = [Path(path) for path in args.panel]
    season_paths = [Path(path) for path in args.season_heat]
    stage_paths = [Path(path) for path in args.stage_heat]
    weights_path = Path(args.weights)
    candidate_path = Path(args.out)
    output, audit = allocate_heat_control_candidate(
        [read_table(path) for path in panel_paths],
        [read_table(path) for path in season_paths],
        [read_table(path) for path in stage_paths],
        read_table(weights_path),
        args.expected_irrigation,
        expected_crop=args.expected_crop,
        expected_year_start=args.expected_year_start,
        expected_year_end=args.expected_year_end,
        thresholds=args.threshold_c,
        stages=args.stages,
        exclude_missing_heat_cells=args.exclude_missing_heat_cells,
        exclude_missing_weight_cells=args.exclude_missing_weight_cells,
    )
    write_table(output, candidate_path)
    audit = bind_file_provenance(
        audit,
        panel_paths=panel_paths,
        season_heat_paths=season_paths,
        stage_heat_paths=stage_paths,
        weights_path=weights_path,
        candidate_path=candidate_path,
    )
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "basis_features"}, indent=2))


if __name__ == "__main__":
    main()
