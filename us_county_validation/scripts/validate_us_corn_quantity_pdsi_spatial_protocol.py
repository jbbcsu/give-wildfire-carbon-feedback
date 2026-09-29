#!/usr/bin/env python3
"""Mechanical validator for the frozen synthetic-only corn spatial protocol."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = PROJECT / "us_county_validation/us_corn_quantity_pdsi_spatial_inference_v1.toml"
DEFAULT_OUTPUT = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_protocol_validation_20260928.json"
FALSE_GATES = (
    "real_outcome_read_authorized", "real_response_fit_authorized",
    "coefficient_output_authorized", "national_claim_authorized",
    "causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate_contract(contract: dict[str, Any]) -> None:
    required = {
        "schema_version", "protocol_id", "analysis_role",
        "synthetic_validation_authorized", *FALSE_GATES, "sample",
        "fixed_effects", "common_controls", "quantity_family", "pdsi_family",
        "family_separation", "spatial_covariance", "geographic_influence",
        "terminal_validation", "preidentified_influence", "execution", "output",
    }
    if set(contract) != required:
        raise ValueError("protocol top-level schema changed")
    if contract["schema_version"] != 1 or contract["protocol_id"] != "us_corn_quantity_pdsi_spatial_inference_v1":
        raise ValueError("protocol identity changed")
    if contract["analysis_role"] != "frozen_future_response_and_spatial_inference_protocol_only":
        raise ValueError("analysis role changed")
    if contract["synthetic_validation_authorized"] is not True:
        raise ValueError("synthetic validation is not authorized")
    for gate in FALSE_GATES:
        if contract[gate] is not False:
            raise ValueError(f"protocol unexpectedly opens {gate}")
    sample = contract["sample"]
    if sample["crop"] != "corn_grain" or sample["practices"] != ["non_irrigated", "irrigated"]:
        raise ValueError("crop/practice scope changed")
    if sample["year_min"] != 1981 or sample["year_max"] != 2018:
        raise ValueError("analysis years changed")
    if sample["terminal_year_min"] != 2012 or sample["terminal_year_max"] != 2018:
        raise ValueError("terminal years changed")
    if contract["fixed_effects"]["effects"] != ["county_geoid", "state_by_harvest_year"]:
        raise ValueError("fixed effects changed")
    if contract["fixed_effects"]["primary_covariance"] != "county_CR1":
        raise ValueError("primary covariance changed")
    if contract["common_controls"]["features"] != [
        "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"
    ] or contract["common_controls"]["form"] != "linear_and_quadratic":
        raise ValueError("temperature basis changed")
    quantity, pdsi = contract["quantity_family"], contract["pdsi_family"]
    if quantity["features"] != ["precip_mm"] or quantity["form"] != "linear_and_quadratic":
        raise ValueError("quantity basis changed")
    if pdsi["features"] != ["pdsi_season_mean"] or pdsi["form"] != "linear_and_quadratic":
        raise ValueError("PDSI basis changed")
    separation = contract["family_separation"]
    if separation["candidate_families"] != ["quantity", "pdsi"]:
        raise ValueError("candidate family list changed")
    for key in (
        "stacking_direct_rainfall_and_pdsi", "stacking_with_spei",
        "cross_family_selection_on_response_results",
    ):
        if separation[key] is not False:
            raise ValueError(f"family separation unexpectedly permits {key}")
    spatial = contract["spatial_covariance"]
    if spatial["method"] != "county_CR1_plus_same_year_cross_county_Bartlett_distance_scores":
        raise ValueError("spatial covariance method changed")
    if spatial["kernel"] != "Bartlett" or spatial["cutoffs_km"] != [250.0, 500.0]:
        raise ValueError("spatial kernel/cutoffs changed")
    for key in (
        "coordinate_file_hash_required_before_real_fit", "same_harvest_year_pairs_only",
        "exclude_same_county_pairs_from_spatial_addition",
    ):
        if spatial[key] is not True:
            raise ValueError(f"spatial requirement {key} changed")
    if spatial["psd_clipping_authorized"] is not False:
        raise ValueError("PSD clipping unexpectedly authorized")
    influence = contract["geographic_influence"]
    if influence["unit"] != "state" or influence["omit_each_observed_state"] is not True:
        raise ValueError("geographic influence design changed")
    if float(influence["maximum_absolute_dfbeta_in_full_sample_CR1_se_units"]) != 1.0:
        raise ValueError("state influence ceiling changed")
    terminal = contract["terminal_validation"]
    if (terminal["development_year_min"], terminal["development_year_max"]) != (1981, 2011):
        raise ValueError("development split changed")
    if (terminal["terminal_year_min"], terminal["terminal_year_max"]) != (2012, 2018):
        raise ValueError("terminal split changed")
    if float(terminal["maximum_absolute_standardized_difference"]) != 1.96:
        raise ValueError("terminal stability ceiling changed")
    preidentified = contract["preidentified_influence"]
    if (preidentified["county_geoid"], preidentified["state"], preidentified["harvest_year"]) != ("48277", "TX", 2011):
        raise ValueError("preidentified exposure changed")
    if preidentified["identified_without_outcomes"] is not True:
        raise ValueError("preidentified exposure is not outcome blind")
    if preidentified["distribution_family_status"] != "ineligible_after_outcome_blind_row_leverage_gate":
        raise ValueError("distribution status changed")
    execution = contract["execution"]
    if execution["real_run_requires_separate_authorization"] is not True:
        raise ValueError("real run no longer requires separate authorization")
    if execution["output_coefficients_before_real_run_authorization"] is not False:
        raise ValueError("coefficient output unexpectedly authorized")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--synthetic-test-resource", type=Path)
    parser.add_argument("--synthetic-test-result", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    contract = tomllib.loads(args.protocol.read_text(encoding="utf-8"))
    validate_contract(contract)
    test_module = PROJECT / contract["execution"]["synthetic_test_module"]
    primitives = PROJECT / "us_county_validation/scripts/us_corn_spatial_inference_primitives.py"
    if not test_module.is_file() or not primitives.is_file():
        raise ValueError("synthetic test implementation is incomplete")
    test_record: dict[str, object] = {"bound": False}
    if args.synthetic_test_resource:
        resource = json.loads(args.synthetic_test_resource.read_text(encoding="utf-8"))
        if resource.get("status") != "command_completed" or resource.get("returncode") != 0:
            raise ValueError("synthetic tests did not complete successfully")
        test_record = {
            "bound": True,
            "path": str(args.synthetic_test_resource.resolve().relative_to(PROJECT)),
            "sha256": digest(args.synthetic_test_resource),
            "status": resource["status"],
            "peak_rss_bytes": int(resource["peak_rss_bytes"]),
            "wall_seconds": float(resource["wall_seconds"]),
        }
    test_result_record: dict[str, object] = {"bound": False}
    if args.synthetic_test_result:
        test_result = json.loads(args.synthetic_test_result.read_text(encoding="utf-8"))
        if (
            test_result.get("status") != "passed"
            or test_result.get("tests_run") != 10
            or test_result.get("failures") != 0
            or test_result.get("errors") != 0
            or test_result.get("real_outcome_rows_read") != 0
            or test_result.get("real_response_fits") != 0
        ):
            raise ValueError("synthetic test result is incomplete or failed")
        if test_result.get("protocol", {}).get("sha256") != digest(args.protocol):
            raise ValueError("synthetic tests do not bind the validated protocol")
        test_result_record = {
            "bound": True,
            "path": str(args.synthetic_test_result.resolve().relative_to(PROJECT)),
            "sha256": digest(args.synthetic_test_result),
            "status": test_result["status"],
            "tests_run": int(test_result["tests_run"]),
        }
    result = {
        "schema": "us_corn_quantity_pdsi_spatial_protocol_validation_v1",
        "status": "validated_synthetic_only_protocol",
        "protocol": {"path": str(args.protocol.resolve().relative_to(PROJECT)), "sha256": digest(args.protocol)},
        "validator": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "synthetic_test_module": {"path": str(test_module.relative_to(PROJECT)), "sha256": digest(test_module)},
        "inference_primitives": {"path": str(primitives.relative_to(PROJECT)), "sha256": digest(primitives)},
        "synthetic_tests": test_record,
        "synthetic_test_result": test_result_record,
        "candidate_families": ["quantity", "pdsi"],
        "practices_fitted_separately": True,
        "spatial_cutoffs_km": [250.0, 500.0],
        "preidentified_exposure_retained_in_primary_candidates": True,
        "distribution_family_eligible": False,
        "real_outcome_rows_read": 0,
        "real_response_fits": 0,
        **{gate: False for gate in FALSE_GATES},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "synthetic_tests": test_record}, indent=2))


if __name__ == "__main__":
    main()
