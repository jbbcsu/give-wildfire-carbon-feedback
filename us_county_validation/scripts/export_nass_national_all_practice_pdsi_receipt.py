#!/usr/bin/env python3
"""Validate the real national all-practice PDSI route and export a safe receipt."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

import prepare_nass_national_all_practice_pdsi as route


DEFAULTS = {
    "panel": "data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet",
    "geography_gate": "data/interim/us_county/nass_national_all_practice_panel_1981_2019_geography_gate.csv",
    "calendar": "data/interim/us_county/nass_usual_date_calendars_1981_2022.csv",
    "monthly": "data/interim/us_county/nclimdiv_pdsi_nass_national_all_practice_eligible_1980_2019.parquet",
    "features": "data/interim/us_county/nclimdiv_pdsi_nass_national_all_practice_calendar_features_1981_2019.parquet",
    "joined": "data/interim/us_county/nass_national_all_practice_pdsi_join_1981_2019.parquet",
    "contract": "config/us_county_drought_predictor_contract_v1.toml",
    "pdsi_provenance": "data/provenance/nclimdiv_county_pdsi_20260806.toml",
    "pdsi_raw": f"data/raw/us_county/nclimdiv_pdsicy/{route.BULK_NAME}",
    "out": "data/provenance/nass_national_all_practice_pdsi_1981_2019_receipt.json",
}


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value


def validate_public_receipt(receipt: dict[str, Any]) -> None:
    expected_false = {
        "contains_raw_values", "contains_outcome_values", "contains_api_key",
        "contains_absolute_paths", "response_estimated", "causal_effect_estimated",
        "damage_calculated", "scc_calculated",
    }
    claims = receipt.get("claim_gates")
    if not isinstance(claims, dict) or any(claims.get(key) is not False for key in expected_false):
        raise ValueError("public receipt must retain every disclosure/scientific claim gate as false")
    if any(text.startswith("/") for text in _walk_strings(receipt)):
        raise ValueError("public receipt contains an absolute path")
    serialized_keys = set()

    def collect_keys(value: Any) -> None:
        if isinstance(value, dict):
            serialized_keys.update(map(str, value))
            for item in value.values():
                collect_keys(item)
        elif isinstance(value, list):
            for item in value:
                collect_keys(item)

    collect_keys(receipt)
    if serialized_keys & {"yield_bu_acre", "index_value"}:
        raise ValueError("public receipt contains a raw outcome or PDSI-value field")


def build_receipt(paths: dict[str, Path]) -> dict[str, Any]:
    panel = route.read_table(paths["panel"])
    geography = route.read_table(paths["geography_gate"])
    eligible, blocked = route.eligible_support(panel, geography)
    contract, family = route.load_contract(paths["contract"], "pdsi")
    calendar = route.filter_calendars(route.read_table(paths["calendar"]), eligible, contract)
    monthly = route.validate_monthly(route.read_table(paths["monthly"]), "pdsi", family)
    features = route.read_table(paths["features"])
    expected_join = route.join_features(eligible, features)
    stored_join = route.read_table(paths["joined"])
    if set(stored_join.columns) != set(expected_join.columns):
        raise ValueError("stored national PDSI join columns differ from exact reconstruction")
    stored_join = stored_join[expected_join.columns].sort_values(
        route.OUTCOME_KEYS + ["calendar_role", "window_id"]
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(stored_join, expected_join, check_dtype=False, check_exact=True)

    _, pins = route.load_pins(paths["pdsi_provenance"])
    bulk_pin = next(item for item in pins if item["name"] == route.BULK_NAME)
    route.validate_local(paths["pdsi_raw"], bulk_pin)
    validation = bulk_pin.get("validation")
    if not isinstance(validation, dict):
        raise ValueError("PDSI provenance lacks decoded validation expectations")
    route.validate_bulk_schema(paths["pdsi_raw"], validation)

    implementation = [
        Path(__file__).resolve(),
        *route.IMPLEMENTATION_FILES,
    ]
    receipt = {
        "schema_version": 1,
        "receipt_id": "nass_national_all_practice_pdsi_1981_2019_v1",
        "role": "validated aggregate receipt for a historical predictive input only",
        "support": {
            "input_positive_outcome_rows": int(len(eligible) + len(blocked)),
            "geography_eligible_outcome_rows": int(len(eligible)),
            "geography_blocked_outcome_rows": int(len(blocked)),
            "eligible_counties": int(eligible.county_geoid.nunique()),
            "eligible_corn_rows": int(eligible.outcome_crop.eq("corn_grain").sum()),
            "eligible_soybean_rows": int(eligible.outcome_crop.eq("soybeans").sum()),
            "missing_irrigation_share_rows": int((~eligible.irrigation_share_eligible).sum()),
            "fixed_2017_high_rainfed_10pct_rows": int(eligible.rainfed_dominant_10pct.sum()),
            "calendar_rows": int(len(calendar)),
            "monthly_pdsi_rows": int(len(monthly)),
            "feature_rows": int(len(features)),
            "joined_rows": int(len(stored_join)),
        },
        "contracts": {
            "outcome_interpretation": "all-practice yield mixture; never direct rainfed yield",
            "irrigation_share": "fixed-2017 sample selector; missing/suppressed remains missing",
            "geography": "fixed-2019 county-envelope proxy after registered historical-change screen",
            "moisture_family": "PDSI competes with and is never stacked with direct weather or SPEI",
            "pdsi_source_id": str(family["source_id"]),
            "pdsi_calibration": [
                int(family["calibration_start_year"]), int(family["calibration_end_year"])
            ],
        },
        "claim_gates": {
            "contains_raw_values": False,
            "contains_outcome_values": False,
            "contains_api_key": False,
            "contains_absolute_paths": False,
            "response_estimated": False,
            "causal_effect_estimated": False,
            "damage_calculated": False,
            "scc_calculated": False,
        },
        "files": {
            name: {
                "path": route.project_relative(path),
                "sha256": route.sha256(path),
            }
            for name, path in paths.items() if name != "out"
        },
        "implementation": {
            route.project_relative(path): {"sha256": route.sha256(path)}
            for path in dict.fromkeys(implementation)
        },
    }
    validate_public_receipt(receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    for name, default in DEFAULTS.items():
        parser.add_argument(f"--{name.replace('_', '-')}", default=default)
    args = parser.parse_args()
    paths = {name: Path(getattr(args, name)) for name in DEFAULTS}
    receipt = build_receipt(paths)
    route.atomic_json(receipt, paths["out"])
    print(
        f"wrote safe aggregate receipt for {receipt['support']['joined_rows']} rows; "
        "response_estimated=false; scc_calculated=false"
    )


if __name__ == "__main__":
    main()
