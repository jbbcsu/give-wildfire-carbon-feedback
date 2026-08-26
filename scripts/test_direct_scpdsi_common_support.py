#!/usr/bin/env python3
"""Synthetic failure-mode tests for global direct/scPDSI common support."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from build_direct_scpdsi_common_support import (  # noqa: E402
    DIRECT_INPUT_CONTRACT,
    DIRECT_PREFIX,
    FALSE_AUTHORIZATION_FLAGS,
    SCPDSI_INPUT_CONTRACT,
    SCPDSI_PREFIX,
    SCPDSI_SOURCE_ROLE,
    assemble_common_support,
    build_bundle,
    sha256_file,
)
from validate_direct_scpdsi_common_support import validate_bundle  # noqa: E402


DIRECT_FEATURES = ["tmean_c", "precip_mm", "precipitation_timing_centroid"]
SCPDSI_FEATURES = ["season_scpdsi_mean", "stage1_scpdsi_min"]


def direct_row(year: int, *, observed: bool = True) -> dict[str, object]:
    return {
        "harvest_year": year,
        "lat": 40.25,
        "lon_360": 260.25,
        "crop": "mai",
        "yield_observed": observed,
        "yield_t_ha": float(year - 1978) if observed else np.nan,
        "tmean_c": 20.0 + (year - 1980),
        "precip_mm": 400.0 + year - 1980,
        "precipitation_timing_centroid": 0.45,
        "irrigation": "area_weighted",
        "exposure_allocation": "one_outcome_independent_fixed_area_weighted",
        "weight_source_id": "synthetic_mirca_2000",
        "weight_vintage": "fixed_2000",
        "response_basis_contract_id": DIRECT_INPUT_CONTRACT,
        "basis_allocation_order": "regime_basis_before_fixed_area_weighting",
        "fit_authorized": False,
        "scc_authorized": False,
    }


def scpdsi_row(year: int, *, observed: bool = True) -> dict[str, object]:
    return {
        "harvest_year": year,
        "lat": 40.25,
        "lon_360": 260.25,
        "crop": "mai",
        "yield_observed": observed,
        "yield_t_ha": float(year - 1978) if observed else np.nan,
        "season_scpdsi_mean": -1.0 + 0.1 * (year - 1980),
        "stage1_scpdsi_min": -2.0 + 0.1 * (year - 1980),
        "irrigation": "area_weighted",
        "exposure_allocation": "one_outcome_independent_fixed_area_weighted",
        "weight_source_id": "synthetic_mirca_2000",
        "weight_vintage": "fixed_2000",
        "response_basis_contract_id": SCPDSI_INPUT_CONTRACT,
        "basis_allocation_order": "regime_basis_before_fixed_area_weighting",
        "water_stress_family": "climatic_water_balance_scpdsi",
        "drought_source_role": SCPDSI_SOURCE_ROLE,
        "direct_weather_terms_included": False,
        "fit_authorized": False,
        "causal_interpretation_authorized": False,
        "future_projection_authorized": False,
        "scc_authorized": False,
    }


def expect_failure(action: Callable[[], object], message: str) -> None:
    try:
        action()
    except (ValueError, AssertionError) as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


direct = pd.DataFrame([direct_row(1980), direct_row(1981), direct_row(1982, observed=False)])
scpdsi = pd.DataFrame(
    [scpdsi_row(1980), scpdsi_row(1981), scpdsi_row(1982, observed=False)]
)
direct_view, scpdsi_view, audit = assemble_common_support(
    direct, scpdsi.iloc[::-1], DIRECT_FEATURES, SCPDSI_FEATURES
)
assert len(direct_view) == len(scpdsi_view) == 3
assert direct_view[["harvest_year", "yield_observed", "yield_t_ha"]].equals(
    scpdsi_view[["harvest_year", "yield_observed", "yield_t_ha"]]
)
assert [name for name in direct_view if name.startswith(DIRECT_PREFIX)] == [
    f"{DIRECT_PREFIX}{name}" for name in DIRECT_FEATURES
]
assert not any(name.startswith(SCPDSI_PREFIX) for name in direct_view)
assert [name for name in scpdsi_view if name.startswith(SCPDSI_PREFIX)] == [
    f"{SCPDSI_PREFIX}{name}" for name in SCPDSI_FEATURES
]
assert not any(name.startswith(DIRECT_PREFIX) for name in scpdsi_view)
assert audit["exact_outcome_agreement"] is True
assert audit["families_stacked"] is False
assert audit["coefficients_emitted"] is False
assert all(audit[flag] is False for flag in FALSE_AUTHORIZATION_FLAGS)


# Duplicate outcome keys fail before any intersection can hide them.
duplicate_direct = pd.concat([direct, direct.iloc[[0]]], ignore_index=True)
expect_failure(
    lambda: assemble_common_support(
        duplicate_direct, scpdsi, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "duplicate crop-grid-year keys",
)


# Equal keys with a changed outcome must never be treated as common support.
outcome_mismatch = scpdsi.copy()
outcome_mismatch.loc[outcome_mismatch.harvest_year.eq(1981), "yield_t_ha"] += 0.01
expect_failure(
    lambda: assemble_common_support(
        direct, outcome_mismatch, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "disagree exactly on yield_t_ha",
)


# Incomplete family support fails by default.  Explicit authorization drops
# whole keys, reports them, and still produces exact two-view common support.
incomplete_scpdsi = scpdsi.loc[scpdsi.harvest_year.ne(1982)].copy()
expect_failure(
    lambda: assemble_common_support(
        direct, incomplete_scpdsi, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "explicit common-support intersection was not authorized",
)
intersection_direct, intersection_scpdsi, intersection_audit = assemble_common_support(
    direct,
    incomplete_scpdsi,
    DIRECT_FEATURES,
    SCPDSI_FEATURES,
    authorize_support_intersection=True,
)
assert len(intersection_direct) == len(intersection_scpdsi) == 2
assert intersection_audit["direct_only_dropped"] == {
    "rows": 1,
    "observed_outcomes": 0,
    "by_crop": {
        "mai": {
            "rows": 1,
            "observed_outcomes": 0,
            "year_start": 1982,
            "year_end": 1982,
        }
    },
}
assert intersection_audit["scpdsi_only_dropped"]["rows"] == 0


# The historical drought family cannot carry raw or derived direct weather,
# even when the leaked column is not named as a requested output feature.
leaking_scpdsi = scpdsi.copy()
leaking_scpdsi["stage1_precip_mm"] = 100.0
expect_failure(
    lambda: assemble_common_support(
        direct, leaking_scpdsi, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "forbidden direct-weather columns",
)
bad_input_gate = scpdsi.copy()
bad_input_gate["direct_weather_terms_included"] = True
expect_failure(
    lambda: assemble_common_support(
        direct, bad_input_gate, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "must be exactly false",
)
expect_failure(
    lambda: assemble_common_support(
        direct, scpdsi, ["fit_authorized"], SCPDSI_FEATURES
    ),
    "outside the registered",
)

threshold_metadata = scpdsi.copy()
threshold_metadata["scpdsi_threshold"] = -2.0
expect_failure(
    lambda: assemble_common_support(
        direct, threshold_metadata, DIRECT_FEATURES, ["scpdsi_threshold"]
    ),
    "outside the registered",
)

string_weather = direct.copy()
string_weather["tmean_c"] = string_weather["tmean_c"].astype(str)
expect_failure(
    lambda: assemble_common_support(
        string_weather, scpdsi, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "non-Boolean numeric dtypes",
)

boolean_weather = direct.copy()
boolean_weather["tmean_c"] = False
expect_failure(
    lambda: assemble_common_support(
        boolean_weather, scpdsi, DIRECT_FEATURES, SCPDSI_FEATURES
    ),
    "non-Boolean numeric dtypes",
)

no_observed_direct = pd.DataFrame([direct_row(1982, observed=False)])
no_observed_scpdsi = pd.DataFrame([scpdsi_row(1982, observed=False)])
expect_failure(
    lambda: assemble_common_support(
        no_observed_direct,
        no_observed_scpdsi,
        DIRECT_FEATURES,
        SCPDSI_FEATURES,
    ),
    "no observed yield outcomes",
)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    direct_input = root / "direct_input.parquet"
    scpdsi_input = root / "scpdsi_input.parquet"
    direct_output = root / "direct_view.parquet"
    scpdsi_output = root / "scpdsi_view.parquet"
    audit_path = root / "audit.json"
    direct.to_parquet(direct_input, index=False)
    scpdsi.to_parquet(scpdsi_input, index=False)
    build_bundle(
        direct_input,
        scpdsi_input,
        direct_output,
        scpdsi_output,
        audit_path,
        DIRECT_FEATURES,
        SCPDSI_FEATURES,
    )
    validated = validate_bundle(
        direct_output, scpdsi_output, audit_path, direct_input, scpdsi_input
    )
    assert validated["common_rows"] == 3
    assert validated["common_observed_outcomes"] == 2
    assert validated["input_sha256_verified"] is True
    assert validated["output_sha256_verified"] is True
    assert validated["immediate_input_recomputation_passed"] is True
    assert validated["upstream_validation_receipts_bound"] is False
    assert validated["upstream_raw_source_recomputation_performed"] is False
    assert validated["families_stacked"] is False
    assert all(validated[flag] is False for flag in FALSE_AUTHORIZATION_FLAGS)

    # Audit authorization tampering fails independently of file recomputation.
    original_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    for flag in ("stacking_authorized", "fit_authorized"):
        tampered_audit = copy.deepcopy(original_audit)
        tampered_audit[flag] = True
        audit_path.write_text(
            json.dumps(tampered_audit, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        expect_failure(
            lambda: validate_bundle(
                direct_output, scpdsi_output, audit_path, direct_input, scpdsi_input
            ),
            f"{flag} must be exactly false",
        )
    unknown_gate_audit = copy.deepcopy(original_audit)
    unknown_gate_audit["production_fit_authorized"] = True
    audit_path.write_text(
        json.dumps(unknown_gate_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expect_failure(
        lambda: validate_bundle(
            direct_output, scpdsi_output, audit_path, direct_input, scpdsi_input
        ),
        "unrecognized authorization fields",
    )
    audit_path.write_text(
        json.dumps(original_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # A changed output fails its recorded content hash.
    tampered_output = pd.read_parquet(direct_output)
    tampered_output.loc[0, f"{DIRECT_PREFIX}precip_mm"] += 1.0
    tampered_output.to_parquet(direct_output, index=False)
    expect_failure(
        lambda: validate_bundle(
            direct_output, scpdsi_output, audit_path, direct_input, scpdsi_input
        ),
        "SHA-256 differs",
    )

    # Even if an output hash is rewritten, immediate-input recomputation detects
    # the changed feature value.
    recompute_tampered_audit = copy.deepcopy(original_audit)
    recompute_tampered_audit["direct_output_sha256"] = sha256_file(direct_output)
    audit_path.write_text(
        json.dumps(recompute_tampered_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expect_failure(
        lambda: validate_bundle(
            direct_output, scpdsi_output, audit_path, direct_input, scpdsi_input
        ),
        "differs from immediate-input recomputation",
    )

    # Rebuild, then falsify an output fit gate and update its hash.  The
    # row-level authorization gate still fails before recomputation.
    build_bundle(
        direct_input,
        scpdsi_input,
        direct_output,
        scpdsi_output,
        audit_path,
        DIRECT_FEATURES,
        SCPDSI_FEATURES,
    )
    false_fit = pd.read_parquet(scpdsi_output)
    false_fit["fit_authorized"] = True
    false_fit.to_parquet(scpdsi_output, index=False)
    false_fit_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    false_fit_audit["scpdsi_output_sha256"] = sha256_file(scpdsi_output)
    audit_path.write_text(
        json.dumps(false_fit_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expect_failure(
        lambda: validate_bundle(
            direct_output, scpdsi_output, audit_path, direct_input, scpdsi_input
        ),
        "fit_authorized must be exactly false",
    )

print("direct-weather/scPDSI common-support tests passed")
