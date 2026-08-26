#!/usr/bin/env python3
"""Assemble separate direct-weather and scPDSI views on common outcome support.

This is a data-only comparison boundary.  It emits two separate files with
identical crop-grid-year outcomes and family-prefixed features.  It never
places both predictor families in one view, fits no model, and authorizes no
causal, damage, future-projection, or SCC use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_irrigation_distribution_basis import (
    basis_feature_names as direct_basis_feature_names,
)
from allocate_outcome_exposures import read_table, write_table
from allocate_irrigation_scpdsi_basis import (
    basis_feature_names as scpdsi_basis_feature_names,
)


CONTRACT_ID = "global_direct_scpdsi_common_support_v1"
DIRECT_INPUT_CONTRACT = "gdhy_aggregate_irrigation_distribution_candidate_v1"
SCPDSI_INPUT_CONTRACT = "gdhy_aggregate_irrigation_scpdsi_candidate_v1"
SCPDSI_SOURCE_ROLE = "historical_benchmark_not_future_scc_input"
KEYS = ["harvest_year", "lat", "lon_360", "crop"]
OUTCOMES = ["yield_observed", "yield_t_ha"]
DIRECT_PREFIX = "direct__"
SCPDSI_PREFIX = "scpdsi__"
EXPECTED_STAGE_COUNT = 3
DIRECT_FEATURE_ALLOWLIST = direct_basis_feature_names(EXPECTED_STAGE_COUNT)
SCPDSI_FEATURE_ALLOWLIST = scpdsi_basis_feature_names(EXPECTED_STAGE_COUNT)
FILE_AUDIT_FIELDS = {
    "direct_input_file",
    "direct_input_sha256",
    "scpdsi_input_file",
    "scpdsi_input_sha256",
    "direct_output_file",
    "direct_output_sha256",
    "scpdsi_output_file",
    "scpdsi_output_sha256",
}
FALSE_AUTHORIZATION_FLAGS = [
    "stacking_authorized",
    "fit_authorized",
    "coefficient_output_authorized",
    "causal_interpretation_authorized",
    "damage_calculation_authorized",
    "future_projection_authorized",
    "scc_authorized",
]

# These patterns identify primitive or derived direct-weather variables even
# when preceded by stage labels.  Calendar duration by itself is not weather
# and is therefore not on this list.
FORBIDDEN_DIRECT_WEATHER_IN_SCPDSI = re.compile(
    r"(^|_)(?:"
    r"pr|prcp|precip|precipitation|rain|rainfall|"
    r"tas|tmean|tavg|tmin|tmax|temperature|"
    r"pet|heat|gdd|vpd|cdd|dry_spell|dryspell|rx1day|rx5day|"
    r"wet_day|wet_days|wet_day_frequency|wet_extreme|mean_wet_day_intensity"
    r")(?:_|$)",
    re.IGNORECASE,
)
FORBIDDEN_DROUGHT_INDEX_IN_DIRECT = re.compile(
    r"(^|_)(?:scpdsi|pdsi|spei)(?:_|$)", re.IGNORECASE
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    if missing := columns - set(frame.columns):
        raise ValueError(f"{label} missing required columns {sorted(missing)}")


def _require_boolean_constant(
    frame: pd.DataFrame,
    column: str,
    expected: bool,
    label: str,
    *,
    required: bool = True,
) -> None:
    if column not in frame:
        if required:
            raise ValueError(f"{label} missing required Boolean gate {column}")
        return
    values = frame[column]
    if not is_bool_dtype(values.dtype) or values.isna().any() or not values.eq(expected).all():
        raise ValueError(f"{label} {column} must be exactly {str(expected).lower()}")


def _constant_text(frame: pd.DataFrame, column: str, label: str) -> str:
    if column not in frame:
        raise ValueError(f"{label} missing required metadata {column}")
    text = frame[column].astype("string").str.strip()
    if text.isna().any() or text.eq("").any():
        raise ValueError(f"{label} contains missing or blank {column}")
    values = text.unique()
    if len(values) != 1:
        raise ValueError(f"{label} must contain exactly one nonblank {column}")
    return str(values[0])


def _validate_feature_names(
    frame: pd.DataFrame,
    features: list[str],
    *,
    family: str,
) -> None:
    label = "Direct-weather input" if family == "direct" else "scPDSI input"
    if not features or len(features) != len(set(features)):
        raise ValueError(f"{label} requires at least one unique declared feature")
    if not all(isinstance(name, str) and name.strip() == name and name for name in features):
        raise ValueError(f"{label} feature names must be nonblank unpadded strings")
    reserved = set(KEYS + OUTCOMES)
    if reserved & set(features):
        raise ValueError(f"{label} feature declarations include key/outcome columns")
    if any(name.startswith((DIRECT_PREFIX, SCPDSI_PREFIX)) for name in features):
        raise ValueError(f"{label} features must use source names before family prefixing")
    _require_columns(frame, set(features), label)
    if family == "direct":
        forbidden = sorted(
            name for name in features if FORBIDDEN_DROUGHT_INDEX_IN_DIRECT.search(name)
        )
        if forbidden:
            raise ValueError(
                f"Direct-weather feature list contains drought-index terms {forbidden}"
            )
        if invalid := sorted(
            name
            for name in features
            if name not in DIRECT_FEATURE_ALLOWLIST
        ):
            raise ValueError(
                f"Direct-weather feature list contains terms outside the registered "
                f"{EXPECTED_STAGE_COUNT}-stage basis {invalid}"
            )
    else:
        if invalid := sorted(name for name in features if "scpdsi" not in name.lower()):
            raise ValueError(f"scPDSI feature list contains non-scPDSI terms {invalid}")
        if invalid := sorted(name for name in features if name not in SCPDSI_FEATURE_ALLOWLIST):
            raise ValueError(
                f"scPDSI feature list contains terms outside the registered "
                f"{EXPECTED_STAGE_COUNT}-stage basis {invalid}"
            )
    invalid_dtypes = sorted(
        name
        for name in features
        if is_bool_dtype(frame[name].dtype)
        or not pd.api.types.is_numeric_dtype(frame[name].dtype)
    )
    if invalid_dtypes:
        raise ValueError(
            f"{label} features must have non-Boolean numeric dtypes {invalid_dtypes}"
        )
    numeric = frame[features].astype("float64")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} declared features must be finite numeric values")
    frame[features] = numeric


def _validate_keys_and_outcomes(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if not frame.columns.is_unique:
        raise ValueError(f"{label} contains duplicate column names")
    _require_columns(frame, set(KEYS + OUTCOMES), label)
    if frame.empty:
        raise ValueError(f"{label} is empty")
    if frame[KEYS].isna().any().any():
        raise ValueError(f"{label} contains missing crop-grid-year keys")
    result = frame.copy()
    years = pd.to_numeric(result["harvest_year"], errors="coerce")
    lat = pd.to_numeric(result["lat"], errors="coerce")
    lon = pd.to_numeric(result["lon_360"], errors="coerce")
    if (
        not np.isfinite(years.to_numpy(dtype=float)).all()
        or not np.isfinite(lat.to_numpy(dtype=float)).all()
        or not np.isfinite(lon.to_numpy(dtype=float)).all()
        or not np.equal(years, np.floor(years)).all()
        or (years < 1).any()
        or (lat < -90).any()
        or (lat > 90).any()
        or (lon < 0).any()
        or (lon >= 360).any()
    ):
        raise ValueError(f"{label} has invalid numeric crop-grid-year keys")
    result["harvest_year"] = years.astype("int64")
    result["lat"] = lat
    result["lon_360"] = lon
    result["crop"] = result["crop"].astype("string").str.strip()
    if result["crop"].isna().any() or result["crop"].eq("").any():
        raise ValueError(f"{label} crop identifiers must be nonblank")
    if result.duplicated(KEYS).any():
        raise ValueError(f"{label} contains duplicate crop-grid-year keys")
    observed = result["yield_observed"]
    if not is_bool_dtype(observed.dtype) or observed.isna().any():
        raise ValueError(f"{label} yield_observed must be nonmissing Boolean")
    yields = pd.to_numeric(result["yield_t_ha"], errors="coerce")
    if not observed.eq(yields.notna()).all():
        raise ValueError(f"{label} yield_observed disagrees with yield_t_ha missingness")
    if (yields.loc[observed] <= 0).any() or not np.isfinite(
        yields.loc[observed].to_numpy(dtype=float)
    ).all():
        raise ValueError(f"{label} observed yields must be finite and positive")
    result["yield_t_ha"] = yields
    return result.sort_values(KEYS, kind="mergesort").reset_index(drop=True)


def _validate_input_contracts(direct: pd.DataFrame, scpdsi: pd.DataFrame) -> dict[str, str]:
    direct_contract = _constant_text(
        direct, "response_basis_contract_id", "Direct-weather input"
    )
    if direct_contract != DIRECT_INPUT_CONTRACT:
        raise ValueError("Direct-weather input has an unauthorized source contract")
    scpdsi_contract = _constant_text(
        scpdsi, "response_basis_contract_id", "scPDSI input"
    )
    if scpdsi_contract != SCPDSI_INPUT_CONTRACT:
        raise ValueError("scPDSI input has an unauthorized source contract")
    if _constant_text(scpdsi, "water_stress_family", "scPDSI input") != (
        "climatic_water_balance_scpdsi"
    ):
        raise ValueError("scPDSI input has an unauthorized water-stress family")
    if _constant_text(scpdsi, "drought_source_role", "scPDSI input") != SCPDSI_SOURCE_ROLE:
        raise ValueError("scPDSI input is not historical-benchmark-only")

    for frame, label in ((direct, "Direct-weather input"), (scpdsi, "scPDSI input")):
        _require_boolean_constant(frame, "fit_authorized", False, label)
        _require_boolean_constant(frame, "scc_authorized", False, label)
        for optional_gate in (
            "stacking_authorized",
            "coefficient_output_authorized",
            "causal_interpretation_authorized",
            "damage_calculation_authorized",
            "future_projection_authorized",
            "diagnostic_fit_authorized",
            "production_fit_authorized",
        ):
            _require_boolean_constant(
                frame, optional_gate, False, label, required=False
            )
    _require_boolean_constant(
        scpdsi, "direct_weather_terms_included", False, "scPDSI input"
    )

    if leaked := sorted(
        column
        for column in scpdsi.columns
        if FORBIDDEN_DIRECT_WEATHER_IN_SCPDSI.search(column)
    ):
        raise ValueError(f"scPDSI input contains forbidden direct-weather columns {leaked}")
    if leaked := sorted(
        column
        for column in direct.columns
        if FORBIDDEN_DROUGHT_INDEX_IN_DIRECT.search(column)
    ):
        raise ValueError(f"Direct-weather input contains forbidden drought-index columns {leaked}")

    comparable_metadata: dict[str, str] = {}
    expected_values = {
        "irrigation": "area_weighted",
        "exposure_allocation": "one_outcome_independent_fixed_area_weighted",
        "basis_allocation_order": "regime_basis_before_fixed_area_weighting",
    }
    for column in (
        "irrigation",
        "exposure_allocation",
        "basis_allocation_order",
        "weight_source_id",
        "weight_vintage",
    ):
        direct_value = _constant_text(direct, column, "Direct-weather input")
        scpdsi_value = _constant_text(scpdsi, column, "scPDSI input")
        if direct_value != scpdsi_value:
            raise ValueError(f"Input views disagree on comparison metadata {column}")
        if column in expected_values and direct_value != expected_values[column]:
            raise ValueError(f"Input views have unauthorized {column}")
        comparable_metadata[column] = direct_value
    return comparable_metadata


def _index(frame: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(frame[KEYS], names=KEYS)


def _support_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"rows": 0, "observed_outcomes": 0, "by_crop": {}}
    return {
        "rows": int(len(frame)),
        "observed_outcomes": int(frame["yield_observed"].sum()),
        "by_crop": {
            str(crop): {
                "rows": int(len(group)),
                "observed_outcomes": int(group["yield_observed"].sum()),
                "year_start": int(group["harvest_year"].min()),
                "year_end": int(group["harvest_year"].max()),
            }
            for crop, group in frame.groupby("crop", observed=True, sort=True)
        },
    }


def _require_exact_outcomes(direct: pd.DataFrame, scpdsi: pd.DataFrame) -> None:
    if not direct[KEYS].equals(scpdsi[KEYS]):
        raise AssertionError("Common-support keys differ after deterministic alignment")
    if not np.array_equal(
        direct["yield_observed"].to_numpy(),
        scpdsi["yield_observed"].to_numpy(),
    ):
        raise ValueError("Input views disagree exactly on yield_observed within common support")
    if not np.array_equal(
        direct["yield_t_ha"].to_numpy(dtype=float),
        scpdsi["yield_t_ha"].to_numpy(dtype=float),
        equal_nan=True,
    ):
        raise ValueError("Input views disagree exactly on yield_t_ha within common support")


def _make_view(
    frame: pd.DataFrame,
    features: list[str],
    *,
    prefix: str,
    candidate_view: str,
) -> pd.DataFrame:
    output = frame[KEYS + OUTCOMES].copy()
    renamed = frame[features].rename(columns={name: f"{prefix}{name}" for name in features})
    output = pd.concat([output, renamed], axis=1)
    output["common_support_contract_id"] = CONTRACT_ID
    output["candidate_view"] = candidate_view
    output["family_mutually_exclusive"] = True
    output["families_stacked"] = False
    output["data_only"] = True
    output["coefficients_emitted"] = False
    for flag in FALSE_AUTHORIZATION_FLAGS:
        output[flag] = False
    return output


def assemble_common_support(
    direct: pd.DataFrame,
    scpdsi: pd.DataFrame,
    direct_features: list[str],
    scpdsi_features: list[str],
    *,
    authorize_support_intersection: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return separate, key-identical predictor-family views and an audit."""
    if type(authorize_support_intersection) is not bool:
        raise ValueError("authorize_support_intersection must be exactly Boolean")
    direct = _validate_keys_and_outcomes(direct, "Direct-weather input")
    scpdsi = _validate_keys_and_outcomes(scpdsi, "scPDSI input")
    metadata = _validate_input_contracts(direct, scpdsi)
    _validate_feature_names(direct, direct_features, family="direct")
    _validate_feature_names(scpdsi, scpdsi_features, family="scpdsi")

    direct_keys = _index(direct)
    scpdsi_keys = _index(scpdsi)
    direct_only_index = direct_keys.difference(scpdsi_keys, sort=True)
    scpdsi_only_index = scpdsi_keys.difference(direct_keys, sort=True)
    direct_only = direct.loc[direct_keys.isin(direct_only_index), KEYS + OUTCOMES]
    scpdsi_only = scpdsi.loc[scpdsi_keys.isin(scpdsi_only_index), KEYS + OUTCOMES]
    if (len(direct_only) or len(scpdsi_only)) and not authorize_support_intersection:
        raise ValueError(
            "Input families have incomplete one-family support "
            f"(direct-only={len(direct_only)}, scPDSI-only={len(scpdsi_only)}); "
            "explicit common-support intersection was not authorized"
        )

    common_keys = (
        direct[KEYS]
        .merge(scpdsi[KEYS], on=KEYS, how="inner", validate="one_to_one")
        .sort_values(KEYS, kind="mergesort")
        .reset_index(drop=True)
    )
    if common_keys.empty:
        raise ValueError("The two candidate families have no common crop-grid-year support")
    direct_common = common_keys.merge(direct, on=KEYS, how="left", validate="one_to_one")
    scpdsi_common = common_keys.merge(scpdsi, on=KEYS, how="left", validate="one_to_one")
    _require_exact_outcomes(direct_common, scpdsi_common)
    if not direct_common["yield_observed"].any():
        raise ValueError("Common support contains no observed yield outcomes")

    direct_view = _make_view(
        direct_common,
        direct_features,
        prefix=DIRECT_PREFIX,
        candidate_view="direct_weather",
    )
    scpdsi_view = _make_view(
        scpdsi_common,
        scpdsi_features,
        prefix=SCPDSI_PREFIX,
        candidate_view="historical_scpdsi",
    )
    if not direct_view[KEYS + OUTCOMES].equals(scpdsi_view[KEYS + OUTCOMES]):
        raise AssertionError("Emitted family views do not retain identical outcomes")

    audit: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "purpose": "Data-only common-support comparison of mutually exclusive moisture families.",
        "direct_input_contract_id": DIRECT_INPUT_CONTRACT,
        "scpdsi_input_contract_id": SCPDSI_INPUT_CONTRACT,
        "scpdsi_source_role": SCPDSI_SOURCE_ROLE,
        "stage_count": EXPECTED_STAGE_COUNT,
        "direct_registered_basis_features": list(DIRECT_FEATURE_ALLOWLIST),
        "scpdsi_registered_basis_features": list(SCPDSI_FEATURE_ALLOWLIST),
        "upstream_validation_receipts_bound": False,
        "upstream_raw_source_recomputation_performed": False,
        "upstream_validation_dependency": (
            "External prerequisite: validate each immediate candidate with its upstream "
            "allocation/source validator and retain that receipt; this assembler binds "
            "and recomputes the immediate candidate tables only."
        ),
        "comparison_metadata": metadata,
        "direct_input": _support_summary(direct),
        "scpdsi_input": _support_summary(scpdsi),
        "direct_only_dropped": _support_summary(direct_only),
        "scpdsi_only_dropped": _support_summary(scpdsi_only),
        "common_support": _support_summary(direct_common),
        "support_policy": (
            "explicit_inner_intersection_with_whole_key_exclusion"
            if authorize_support_intersection
            else "exact_input_support_required"
        ),
        "support_intersection_authorized": bool(authorize_support_intersection),
        "exact_key_agreement_after_intersection": True,
        "exact_outcome_agreement": True,
        "direct_feature_source_names": list(direct_features),
        "scpdsi_feature_source_names": list(scpdsi_features),
        "direct_output_feature_names": [f"{DIRECT_PREFIX}{name}" for name in direct_features],
        "scpdsi_output_feature_names": [f"{SCPDSI_PREFIX}{name}" for name in scpdsi_features],
        "views_emitted_separately": True,
        "family_mutually_exclusive": True,
        "families_stacked": False,
        "data_only": True,
        "coefficients_emitted": False,
    }
    audit.update({flag: False for flag in FALSE_AUTHORIZATION_FLAGS})
    return direct_view, scpdsi_view, audit


def build_bundle(
    direct_input_path: Path,
    scpdsi_input_path: Path,
    direct_output_path: Path,
    scpdsi_output_path: Path,
    audit_output_path: Path,
    direct_features: list[str],
    scpdsi_features: list[str],
    *,
    authorize_support_intersection: bool = False,
) -> dict[str, Any]:
    """Read, assemble, write, and hash a common-support comparison bundle."""
    paths = [
        direct_input_path,
        scpdsi_input_path,
        direct_output_path,
        scpdsi_output_path,
        audit_output_path,
    ]
    resolved = [path.resolve() for path in paths]
    if len(resolved) != len(set(resolved)):
        raise ValueError("Input, output, and audit paths must all be distinct")
    direct_view, scpdsi_view, audit = assemble_common_support(
        read_table(direct_input_path),
        read_table(scpdsi_input_path),
        direct_features,
        scpdsi_features,
        authorize_support_intersection=authorize_support_intersection,
    )
    write_table(direct_view, direct_output_path)
    write_table(scpdsi_view, scpdsi_output_path)
    audit.update(
        {
            "direct_input_file": str(direct_input_path),
            "direct_input_sha256": sha256_file(direct_input_path),
            "scpdsi_input_file": str(scpdsi_input_path),
            "scpdsi_input_sha256": sha256_file(scpdsi_input_path),
            "direct_output_file": str(direct_output_path),
            "direct_output_sha256": sha256_file(direct_output_path),
            "scpdsi_output_file": str(scpdsi_output_path),
            "scpdsi_output_sha256": sha256_file(scpdsi_output_path),
        }
    )
    audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_output_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct-input", required=True)
    parser.add_argument("--scpdsi-input", required=True)
    parser.add_argument("--direct-feature", action="append")
    parser.add_argument("--scpdsi-feature", action="append")
    parser.add_argument("--all-registered-direct-features", action="store_true")
    parser.add_argument("--all-registered-scpdsi-features", action="store_true")
    parser.add_argument(
        "--authorize-support-intersection",
        action="store_true",
        help=(
            "Explicitly drop whole keys absent from either family; every drop is audited. "
            "Without this flag, unequal input support fails closed."
        ),
    )
    parser.add_argument("--direct-out", required=True)
    parser.add_argument("--scpdsi-out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    if bool(args.direct_feature) == bool(args.all_registered_direct_features):
        raise ValueError(
            "Choose exactly one of repeated --direct-feature or --all-registered-direct-features"
        )
    if bool(args.scpdsi_feature) == bool(args.all_registered_scpdsi_features):
        raise ValueError(
            "Choose exactly one of repeated --scpdsi-feature or --all-registered-scpdsi-features"
        )
    direct_features = (
        list(DIRECT_FEATURE_ALLOWLIST)
        if args.all_registered_direct_features
        else list(args.direct_feature)
    )
    scpdsi_features = (
        list(SCPDSI_FEATURE_ALLOWLIST)
        if args.all_registered_scpdsi_features
        else list(args.scpdsi_feature)
    )
    audit = build_bundle(
        Path(args.direct_input),
        Path(args.scpdsi_input),
        Path(args.direct_out),
        Path(args.scpdsi_out),
        Path(args.audit_out),
        direct_features,
        scpdsi_features,
        authorize_support_intersection=args.authorize_support_intersection,
    )
    print(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
