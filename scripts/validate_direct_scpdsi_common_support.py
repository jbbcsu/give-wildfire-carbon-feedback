#!/usr/bin/env python3
"""Validate a direct-weather/scPDSI bundle from its immediate inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_outcome_exposures import read_table
from build_direct_scpdsi_common_support import (
    CONTRACT_ID,
    DIRECT_PREFIX,
    FILE_AUDIT_FIELDS,
    FALSE_AUTHORIZATION_FLAGS,
    KEYS,
    OUTCOMES,
    SCPDSI_PREFIX,
    assemble_common_support,
    sha256_file,
)


def _require_exact_false(mapping: dict[str, Any], key: str, label: str) -> None:
    if key not in mapping or mapping[key] is not False:
        raise ValueError(f"{label} {key} must be exactly false")


def _require_bool_column(
    frame: pd.DataFrame, column: str, expected: bool, label: str
) -> None:
    if column not in frame:
        raise ValueError(f"{label} missing required Boolean field {column}")
    values = frame[column]
    if not is_bool_dtype(values.dtype) or values.isna().any() or not values.eq(expected).all():
        raise ValueError(f"{label} {column} must be exactly {str(expected).lower()}")


def _validate_view(
    frame: pd.DataFrame,
    *,
    label: str,
    expected_view: str,
    own_prefix: str,
    forbidden_prefix: str,
    expected_features: list[str],
) -> None:
    expected_columns = (
        KEYS
        + OUTCOMES
        + expected_features
        + [
            "common_support_contract_id",
            "candidate_view",
            "family_mutually_exclusive",
            "families_stacked",
            "data_only",
            "coefficients_emitted",
        ]
        + FALSE_AUTHORIZATION_FLAGS
    )
    if list(frame.columns) != expected_columns:
        raise ValueError(f"{label} schema or column order differs from the contract")
    if frame.empty or frame.duplicated(KEYS).any():
        raise ValueError(f"{label} must contain unique, nonempty crop-grid-year keys")
    if not all(name.startswith(own_prefix) for name in expected_features):
        raise ValueError(f"{label} audit feature names lack their family prefix")
    if any(column.startswith(forbidden_prefix) for column in frame.columns):
        raise ValueError(f"{label} contains columns from the competing predictor family")
    if set(frame["common_support_contract_id"].dropna().astype(str)) != {CONTRACT_ID}:
        raise ValueError(f"{label} common-support contract identity differs")
    if set(frame["candidate_view"].dropna().astype(str)) != {expected_view}:
        raise ValueError(f"{label} candidate-view identity differs")
    _require_bool_column(frame, "family_mutually_exclusive", True, label)
    _require_bool_column(frame, "families_stacked", False, label)
    _require_bool_column(frame, "data_only", True, label)
    _require_bool_column(frame, "coefficients_emitted", False, label)
    for flag in FALSE_AUTHORIZATION_FLAGS:
        _require_bool_column(frame, flag, False, label)
    numeric = frame[expected_features].apply(pd.to_numeric, errors="coerce")
    invalid_dtypes = sorted(
        name
        for name in expected_features
        if is_bool_dtype(frame[name].dtype)
        or not pd.api.types.is_numeric_dtype(frame[name].dtype)
    )
    if invalid_dtypes:
        raise ValueError(f"{label} contains nonnumeric or Boolean features {invalid_dtypes}")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} contains missing or nonfinite feature values")


def _assert_recomputed(
    actual: pd.DataFrame, expected: pd.DataFrame, label: str
) -> None:
    if list(actual.columns) != list(expected.columns):
        raise ValueError(f"{label} schema differs from immediate-input recomputation")
    try:
        pd.testing.assert_frame_equal(
            actual.reset_index(drop=True),
            expected.reset_index(drop=True),
            check_dtype=True,
            check_exact=True,
        )
    except AssertionError as error:
        raise ValueError(f"{label} differs from immediate-input recomputation") from error


def validate_bundle(
    direct_output_path: Path,
    scpdsi_output_path: Path,
    audit_path: Path,
    direct_input_path: Path,
    scpdsi_input_path: Path,
) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("schema_version") != 1 or audit.get("contract_id") != CONTRACT_ID:
        raise ValueError("Unexpected common-support audit contract")
    known_authorization_fields = set(FALSE_AUTHORIZATION_FLAGS) | {
        "support_intersection_authorized"
    }
    if unknown_authorizations := sorted(
        key
        for key in audit
        if key.endswith("_authorized") and key not in known_authorization_fields
    ):
        raise ValueError(
            f"Audit contains unrecognized authorization fields {unknown_authorizations}"
        )
    if audit.get("views_emitted_separately") is not True:
        raise ValueError("Audit does not require separate candidate-family views")
    if audit.get("family_mutually_exclusive") is not True:
        raise ValueError("Audit does not enforce mutually exclusive candidate families")
    if audit.get("families_stacked") is not False:
        raise ValueError("Audit improperly records stacked candidate families")
    if audit.get("data_only") is not True or audit.get("coefficients_emitted") is not False:
        raise ValueError("Audit is not an unfitted data-only boundary")
    for flag in FALSE_AUTHORIZATION_FLAGS:
        _require_exact_false(audit, flag, "Audit")
    if type(audit.get("support_intersection_authorized")) is not bool:
        raise ValueError("Audit support_intersection_authorized must be exactly Boolean")

    expected_paths = {
        "direct_input_file": str(direct_input_path),
        "scpdsi_input_file": str(scpdsi_input_path),
        "direct_output_file": str(direct_output_path),
        "scpdsi_output_file": str(scpdsi_output_path),
    }
    for key, expected in expected_paths.items():
        if audit.get(key) != expected:
            raise ValueError(f"Audit path differs for {key}")
    expected_hashes = {
        "direct_input_sha256": sha256_file(direct_input_path),
        "scpdsi_input_sha256": sha256_file(scpdsi_input_path),
        "direct_output_sha256": sha256_file(direct_output_path),
        "scpdsi_output_sha256": sha256_file(scpdsi_output_path),
    }
    for key, expected in expected_hashes.items():
        if audit.get(key) != expected:
            raise ValueError(f"Audit SHA-256 differs for {key}")

    direct_features = audit.get("direct_feature_source_names")
    scpdsi_features = audit.get("scpdsi_feature_source_names")
    if not isinstance(direct_features, list) or not all(
        isinstance(value, str) for value in direct_features
    ):
        raise ValueError("Audit direct feature list is invalid")
    if not isinstance(scpdsi_features, list) or not all(
        isinstance(value, str) for value in scpdsi_features
    ):
        raise ValueError("Audit scPDSI feature list is invalid")
    direct_output_features = audit.get("direct_output_feature_names")
    scpdsi_output_features = audit.get("scpdsi_output_feature_names")
    if direct_output_features != [f"{DIRECT_PREFIX}{name}" for name in direct_features]:
        raise ValueError("Audit direct output-feature mapping differs")
    if scpdsi_output_features != [f"{SCPDSI_PREFIX}{name}" for name in scpdsi_features]:
        raise ValueError("Audit scPDSI output-feature mapping differs")

    direct_output = read_table(direct_output_path)
    scpdsi_output = read_table(scpdsi_output_path)
    _validate_view(
        direct_output,
        label="Direct-weather output view",
        expected_view="direct_weather",
        own_prefix=DIRECT_PREFIX,
        forbidden_prefix=SCPDSI_PREFIX,
        expected_features=direct_output_features,
    )
    _validate_view(
        scpdsi_output,
        label="scPDSI output view",
        expected_view="historical_scpdsi",
        own_prefix=SCPDSI_PREFIX,
        forbidden_prefix=DIRECT_PREFIX,
        expected_features=scpdsi_output_features,
    )
    if not direct_output[KEYS + OUTCOMES].equals(scpdsi_output[KEYS + OUTCOMES]):
        raise ValueError("Output views do not have exact common key/outcome agreement")

    recomputed_direct, recomputed_scpdsi, recomputed_audit = assemble_common_support(
        read_table(direct_input_path),
        read_table(scpdsi_input_path),
        direct_features,
        scpdsi_features,
        authorize_support_intersection=audit["support_intersection_authorized"],
    )
    expected_audit_fields = set(recomputed_audit) | FILE_AUDIT_FIELDS
    if set(audit) != expected_audit_fields:
        missing = sorted(expected_audit_fields - set(audit))
        extra = sorted(set(audit) - expected_audit_fields)
        raise ValueError(f"Audit schema differs: missing={missing}, extra={extra}")
    for key, value in recomputed_audit.items():
        if audit.get(key) != value:
            raise ValueError(f"Audit field differs on immediate-input recomputation: {key}")
    _assert_recomputed(direct_output, recomputed_direct, "Direct-weather output view")
    _assert_recomputed(scpdsi_output, recomputed_scpdsi, "scPDSI output view")

    return {
        "schema_version": 1,
        "status": (
            "validated_immediate_input_data_only_mutually_exclusive_common_support_"
            "not_fit_causal_damage_future_or_scc_authorized"
        ),
        "contract_id": CONTRACT_ID,
        "common_rows": int(len(direct_output)),
        "common_observed_outcomes": int(direct_output["yield_observed"].sum()),
        "direct_feature_count": len(direct_features),
        "scpdsi_feature_count": len(scpdsi_features),
        "direct_only_keys_dropped": int(audit["direct_only_dropped"]["rows"]),
        "scpdsi_only_keys_dropped": int(audit["scpdsi_only_dropped"]["rows"]),
        "input_sha256_verified": True,
        "output_sha256_verified": True,
        "immediate_input_recomputation_passed": True,
        "upstream_validation_receipts_bound": False,
        "upstream_raw_source_recomputation_performed": False,
        "views_emitted_separately": True,
        "family_mutually_exclusive": True,
        "families_stacked": False,
        "data_only": True,
        "coefficients_emitted": False,
        **{flag: False for flag in FALSE_AUTHORIZATION_FLAGS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct-view", required=True)
    parser.add_argument("--scpdsi-view", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--direct-input", required=True)
    parser.add_argument("--scpdsi-input", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = validate_bundle(
        Path(args.direct_view),
        Path(args.scpdsi_view),
        Path(args.audit),
        Path(args.direct_input),
        Path(args.scpdsi_input),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
