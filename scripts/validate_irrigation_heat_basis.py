#!/usr/bin/env python3
"""Recompute and validate the aggregate-irrigation heat-control basis."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_irrigation_heat_basis import (
    ALLOCATION_ORDER,
    CONTRACT_ID,
    FALSE_GATES,
    SOURCE_ROLE,
    THRESHOLD_STATUS,
    allocate_heat_control_candidate,
    bind_file_provenance,
    heat_basis_feature_names,
    sha256_file,
)
from allocate_outcome_exposures import KEYS, read_table
from build_crop_heat_features import threshold_name
from heat_threshold_validation import validate_thresholds


MOISTURE_TERM = re.compile(
    r"(^|_)(?:pr|prcp|precip|precipitation|rain|rainfall|wet|dry|cdd|"
    r"rx1day|rx5day|pdsi|scpdsi|spei|soil_moisture|vpd)(?:_|$)",
    re.IGNORECASE,
)


def _require_bool_constant(
    frame: pd.DataFrame, column: str, expected: bool, label: str = "Candidate"
) -> None:
    if (
        column not in frame
        or not is_bool_dtype(frame[column].dtype)
        or frame[column].isna().any()
        or not frame[column].eq(expected).all()
    ):
        raise ValueError(f"{label} {column} must be exactly {str(expected).lower()} Boolean")


def _require_audit_bool(audit: dict[str, Any], column: str, expected: bool) -> None:
    if column not in audit or type(audit[column]) is not bool or audit[column] is not expected:
        raise ValueError(f"Allocation audit {column} must be exactly {str(expected).lower()} Boolean")


def validate_candidate_frame(
    candidate: pd.DataFrame,
    audit: dict[str, Any],
    *,
    expected_crop: str,
    expected_year_start: int,
    expected_year_end: int,
    thresholds: list[float],
    stages: int,
) -> None:
    thresholds = validate_thresholds(thresholds)
    features = heat_basis_feature_names(thresholds, stages)
    required = set(
        KEYS
        + ["yield_observed", "yield_t_ha"]
        + features
        + ["heat_control_basis_contract_id", "source_role", "diagnostic_fit_authorized"]
        + FALSE_GATES
    )
    if set(candidate.columns) != required:
        raise ValueError(
            "Candidate schema differs from the exact heat-control contract: "
            f"missing={sorted(required - set(candidate.columns))}, "
            f"extra={sorted(set(candidate.columns) - required)}"
        )
    if not candidate.columns.is_unique or candidate.empty or candidate.duplicated(KEYS).any():
        raise ValueError("Candidate must have unique columns and unique nonempty outcome keys")
    if candidate[KEYS].isna().any().any():
        raise ValueError("Candidate contains missing outcome keys")
    if set(candidate["crop"].astype(str).unique()) != {expected_crop}:
        raise ValueError("Candidate crop differs from the exact expectation")
    years = pd.to_numeric(candidate["harvest_year"], errors="coerce")
    if not np.isfinite(years).all() or not np.equal(years, np.floor(years)).all():
        raise ValueError("Candidate harvest_year must be finite integer-valued")
    if sorted(years.astype(int).unique()) != list(range(expected_year_start, expected_year_end + 1)):
        raise ValueError("Candidate does not contain the exact expected year range")
    constants = {
        "heat_control_basis_contract_id": CONTRACT_ID,
        "source_role": SOURCE_ROLE,
    }
    for column, expected in constants.items():
        values = candidate[column].astype("string")
        if values.isna().any() or set(values.unique()) != {expected}:
            raise ValueError(f"Candidate has invalid {column}")
    if not is_bool_dtype(candidate["yield_observed"].dtype) or candidate["yield_observed"].isna().any():
        raise ValueError("Candidate yield_observed must be nonmissing Boolean")
    yields = pd.to_numeric(candidate["yield_t_ha"], errors="coerce")
    if not candidate["yield_observed"].eq(yields.notna()).all():
        raise ValueError("Candidate yield_observed disagrees with yield_t_ha missingness")
    if not np.isfinite(yields.loc[candidate["yield_observed"]]).all() or (
        yields.loc[candidate["yield_observed"]] <= 0
    ).any():
        raise ValueError("Candidate observed yields must be finite and positive")
    _require_bool_constant(candidate, "diagnostic_fit_authorized", True)
    for column in FALSE_GATES:
        _require_bool_constant(candidate, column, False)

    invalid_features = [
        name
        for name in features
        if is_bool_dtype(candidate[name].dtype)
        or not pd.api.types.is_numeric_dtype(candidate[name].dtype)
    ]
    if invalid_features:
        raise ValueError(f"Candidate heat features must be non-Boolean numeric {invalid_features}")
    numeric = candidate[features].astype("float64")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Candidate heat-control basis contains nonfinite values")
    metric_features = [name for name in features if name.endswith(("_days", "_degree_days"))]
    if (numeric[metric_features] < 0).any().any():
        raise ValueError("Candidate weighted heat-day metrics cannot be negative")
    if leaked := sorted(column for column in candidate.columns if MOISTURE_TERM.search(column)):
        raise ValueError(f"Moisture terms leaked into the heat-control basis {leaked}")

    # Fixed-area weighted sums preserve cross-threshold nesting. Weighted day
    # counts are exposures and therefore need not be integers.
    for window in [f"stage{stage}" for stage in range(1, stages + 1)]:
        for lower, upper in zip(thresholds, thresholds[1:]):
            low, high = threshold_name(lower), threshold_name(upper)
            low_days = numeric[f"{window}_{low}_days"]
            high_days = numeric[f"{window}_{high}_days"]
            low_dd = numeric[f"{window}_{low}_degree_days"]
            high_dd = numeric[f"{window}_{high}_degree_days"]
            if (high_days > low_days + 1e-10).any():
                raise ValueError("Candidate hotter-threshold days are not nested")
            difference = low_dd - high_dd
            gap = upper - lower
            if (
                (difference < gap * high_days - 1e-8).any()
                or (difference > gap * low_days + 1e-8).any()
            ):
                raise ValueError("Candidate weighted degree days violate threshold nesting bounds")

    if audit.get("basis_features") != features or audit.get("basis_feature_count") != len(features):
        raise ValueError("Allocation audit heat-feature contract differs from expectation")
    if audit.get("output_rows") != len(candidate):
        raise ValueError("Allocation audit row count differs from candidate")
    if audit.get("observed_outcomes") != int(candidate["yield_observed"].sum()):
        raise ValueError("Allocation audit observed-outcome count differs from candidate")


def validate_candidate(
    candidate_path: Path,
    audit_path: Path,
    panel_paths: list[Path],
    season_heat_paths: list[Path],
    stage_heat_paths: list[Path],
    weights_path: Path,
    expected_irrigation: list[str],
    *,
    expected_crop: str,
    expected_year_start: int,
    expected_year_end: int,
    thresholds: list[float],
    stages: int,
) -> dict[str, Any]:
    thresholds = validate_thresholds(thresholds)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("response_basis_contract_id") != CONTRACT_ID:
        raise ValueError("Unexpected heat-control response-basis contract")
    if audit.get("basis_allocation_order") != ALLOCATION_ORDER:
        raise ValueError("Heat-control allocation order drifted")
    if audit.get("heat_threshold_status") != THRESHOLD_STATUS:
        raise ValueError("Heat thresholds are not marked diagnostic/nonproduction")
    if audit.get("source_role") != SOURCE_ROLE:
        raise ValueError("Heat-control source role drifted")
    expected_constants = {
        "expected_crop": expected_crop,
        "expected_year_start": expected_year_start,
        "expected_year_end": expected_year_end,
        "stage_count": stages,
        "heat_thresholds_c": [float(value) for value in thresholds],
        "irrigation_labels": expected_irrigation,
    }
    for field, expected in expected_constants.items():
        if audit.get(field) != expected:
            raise ValueError(f"Allocation audit {field} differs from the exact expectation")
    for field in (
        "whole_outcome_key_exclusions_only",
        "regime_calendar_identity_validated",
        "stage_season_reconciliation_validated",
        "threshold_nesting_validated",
        "common_support_ready",
        "data_only",
        "immediate_input_recomputation_by_validator_required",
        "diagnostic_fit_authorized",
    ):
        _require_audit_bool(audit, field, True)
    for field in (
        "weight_renormalization_performed",
        "moisture_terms_included",
        "nonlinear_post_allocation_transform_authorized",
        "upstream_raw_daily_heat_recomputation_performed",
        "fit_authorized",
    ) + tuple(FALSE_GATES):
        _require_audit_bool(audit, field, False)

    exact_paths = {
        "input_panel_files": [str(path) for path in panel_paths],
        "input_season_heat_files": [str(path) for path in season_heat_paths],
        "input_stage_heat_files": [str(path) for path in stage_heat_paths],
        "weight_file": str(weights_path),
        "candidate_file": str(candidate_path),
    }
    for field, expected in exact_paths.items():
        if audit.get(field) != expected:
            raise ValueError(f"Allocation audit {field} differs from validator inputs")
    exact_hashes = {
        "input_panel_sha256": [sha256_file(path) for path in panel_paths],
        "input_season_heat_sha256": [sha256_file(path) for path in season_heat_paths],
        "input_stage_heat_sha256": [sha256_file(path) for path in stage_heat_paths],
        "weight_file_sha256": sha256_file(weights_path),
        "candidate_sha256": sha256_file(candidate_path),
    }
    for field, expected in exact_hashes.items():
        if audit.get(field) != expected:
            raise ValueError(f"Allocation audit {field} differs from current file SHA256")

    heat_policy = audit.get("heat_coverage_policy")
    weight_policy = audit.get("missing_weight_policy")
    if heat_policy not in {
        "fail_closed",
        "exclude_entire_crop_grid_year_if_any_regime_or_heat_window_missing_without_infill",
    }:
        raise ValueError("Allocation audit has an unauthorized heat-coverage policy")
    if weight_policy not in {
        "fail_closed",
        "exclude_entire_crop_grid_year_outcome_without_infill_or_renormalization",
    }:
        raise ValueError("Allocation audit has an unauthorized missing-weight policy")

    recomputed, recomputed_audit = allocate_heat_control_candidate(
        [read_table(path) for path in panel_paths],
        [read_table(path) for path in season_heat_paths],
        [read_table(path) for path in stage_heat_paths],
        read_table(weights_path),
        expected_irrigation,
        expected_crop=expected_crop,
        expected_year_start=expected_year_start,
        expected_year_end=expected_year_end,
        thresholds=thresholds,
        stages=stages,
        exclude_missing_heat_cells=(
            heat_policy
            == "exclude_entire_crop_grid_year_if_any_regime_or_heat_window_missing_without_infill"
        ),
        exclude_missing_weight_cells=(
            weight_policy
            == "exclude_entire_crop_grid_year_outcome_without_infill_or_renormalization"
        ),
    )
    expected_audit = bind_file_provenance(
        recomputed_audit,
        panel_paths=panel_paths,
        season_heat_paths=season_heat_paths,
        stage_heat_paths=stage_heat_paths,
        weights_path=weights_path,
        candidate_path=candidate_path,
    )
    if set(audit) != set(expected_audit):
        raise ValueError("Allocation audit schema contains missing or unknown fields")
    for field, value in expected_audit.items():
        if audit.get(field) != value:
            raise ValueError(f"Allocation audit differs on complete recomputation: {field}")

    candidate = read_table(candidate_path)
    if list(candidate.columns) != list(recomputed.columns):
        raise ValueError("Candidate schema differs from the recomputed heat-control basis")
    pd.testing.assert_frame_equal(
        candidate.reset_index(drop=True),
        recomputed.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    validate_candidate_frame(
        candidate,
        audit,
        expected_crop=expected_crop,
        expected_year_start=expected_year_start,
        expected_year_end=expected_year_end,
        thresholds=thresholds,
        stages=stages,
    )
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": "validated_common_nonmoisture_heat_control_basis",
        "heat_control_basis_contract_id": CONTRACT_ID,
        "crop": expected_crop,
        "harvest_year_start": expected_year_start,
        "harvest_year_end": expected_year_end,
        "heat_control_sha256": sha256_file(candidate_path),
        "source_role": SOURCE_ROLE,
        "diagnostic_fit_authorized": True,
        "immediate_input_recomputation_passed": True,
        "raw_source_recomputation_performed": False,
        "source_files_sha256": {
            **{
                f"direct_panel_{irrigation}": sha256_file(path)
                for irrigation, path in zip(expected_irrigation, panel_paths)
            },
            **{
                f"season_heat_{irrigation}": sha256_file(path)
                for irrigation, path in zip(expected_irrigation, season_heat_paths)
            },
            **{
                f"stage_heat_{irrigation}": sha256_file(path)
                for irrigation, path in zip(expected_irrigation, stage_heat_paths)
            },
            "fixed_area_weights": sha256_file(weights_path),
            "allocation_audit": sha256_file(audit_path),
        },
    }
    for flag in FALSE_GATES:
        receipt[flag] = False
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--allocation-audit", required=True)
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
    parser.add_argument("--out")
    args = parser.parse_args()
    result = validate_candidate(
        Path(args.candidate),
        Path(args.allocation_audit),
        [Path(path) for path in args.panel],
        [Path(path) for path in args.season_heat],
        [Path(path) for path in args.stage_heat],
        Path(args.weights),
        args.expected_irrigation,
        expected_crop=args.expected_crop,
        expected_year_start=args.expected_year_start,
        expected_year_end=args.expected_year_end,
        thresholds=args.threshold_c,
        stages=args.stages,
    )
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
