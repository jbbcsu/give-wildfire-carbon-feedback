#!/usr/bin/env python3
"""Validate the no-fit receipt-only temporal-distinctness contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "isimip3b_rimex_temporal_distinctness_contract_v1"
ESMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
SCENARIOS = ["ssp126", "ssp370", "ssp585"]
PERIODS = {
    "historical_and_early_future": (2012, 2019),
    "midcentury": (2042, 2049),
    "endcentury": (2092, 2099),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_esm(value: str) -> str:
    lookup = {item.lower(): item for item in ESMS}
    require(value.lower() in lookup, f"unexpected ESM: {value}")
    return lookup[value.lower()]


def validate_source_audits(combined: dict[str, object], root: Path, period: str) -> list[dict[str, object]]:
    observed = []
    for item in combined.get("inputs", []):
        esm = normalized_esm(str(item["esm_id"]))
        source_path = root / str(item["source_audit"])
        require(sha256(source_path) == str(item["source_audit_sha256"]), f"nested source audit hash changed: {source_path}")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        require(normalized_esm(str(source["esm_id"])) == esm, "nested source ESM changed")
        require(source.get("year_start") == PERIODS[period][0], f"{period} start year changed")
        require(source.get("year_end") == PERIODS[period][1], f"{period} end year changed")
        scenarios = sorted(str(row["scenario"]) for row in source.get("inputs", []))
        expected = ["historical", *SCENARIOS] if period == "historical_and_early_future" else SCENARIOS
        require(scenarios == sorted(expected), f"{period} scenario coverage changed for {esm}")
        observed.append({"esm": esm, "source_audit": str(item["source_audit"]), "sha256": sha256(source_path)})
    require(sorted(row["esm"] for row in observed) == ESMS, f"{period} ESM coverage changed")
    return sorted(observed, key=lambda row: row["esm"])


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require(config.get("role") == "outcome_blind_no_fit_receipt_only_temporal_distinctness_upper_bound", "contract role changed")
    for gate in ("dependence_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    matrix = config.get("matrix", {})
    require(matrix.get("expected_esms") == ESMS, "expected ESM set changed")
    require(matrix.get("expected_future_scenarios") == SCENARIOS, "future scenario set changed")
    require(matrix.get("historical_scenario") == "historical", "historical label changed")
    expected_years = {
        "historical_center_years": [2012, 2013, 2014],
        "early_future_center_years": [2016, 2017, 2018, 2019],
        "midcentury_center_years": list(range(2042, 2050)),
        "endcentury_center_years": list(range(2092, 2100)),
    }
    for key, years in expected_years.items():
        require(matrix.get(key) == years, f"center-year set changed: {key}")

    distinctness = config.get("distinctness", {})
    require(distinctness.get("centered_window_years") == 21, "centered-window length changed")
    require(distinctness.get("window_year_radius") == 10, "window radius changed")
    require(distinctness.get("minimum_distinct_training_templates_per_permitted_pool") == 51, "minimum template gate changed")
    for gate in (
        "closed_support_intervals", "same_esm_member_scenario_windows_must_be_pairwise_nonoverlapping",
        "different_scenario_branches_counted_as_distinct_for_permissive_upper_bound",
        "permissive_upper_bound_is_not_independence_evidence", "future_only_pool_is_primary",
        "historical_augmented_pool_is_diagnostic_only", "whole_esm_holdout_training_count_required",
        "whole_scenario_holdout_training_count_required", "no_fit_if_upper_bound_below_minimum", "no_outcome_columns",
    ):
        require(distinctness.get(gate) is True, f"distinctness gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    for gate in ("large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden", "receipt_json_inputs_only"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    receipts = {}
    nested = {}
    for record in config.get("source_receipts", []):
        path = root / str(record["path"])
        require(sha256(path) == str(record["sha256"]), f"source receipt hash changed: {path}")
        receipts[str(record["period"])] = json.loads(path.read_text(encoding="utf-8"))
    require(set(receipts) == {*PERIODS, "combined_period_inventory"}, "source receipt roles changed")

    early = receipts["historical_and_early_future"]
    require(early.get("schema") == "isimip3b_bounded_five_esm_four_scenario_holdout_v1", "early receipt schema changed")
    require(early.get("complete_bounded_five_esm_four_scenario_matrix") is True, "early matrix no longer complete")
    nested["historical_and_early_future"] = validate_source_audits(early, root, "historical_and_early_future")
    for period in ("midcentury", "endcentury"):
        receipt = receipts[period]
        require(receipt.get("schema") == "isimip3b_five_esm_later_century_holdout_audit_v1", f"{period} schema changed")
        require(receipt.get("period") == period, f"{period} receipt label changed")
        require(receipt.get("complete_five_esm_matrix") is True, f"{period} matrix no longer complete")
        require(sorted(normalized_esm(str(item)) for item in receipt.get("esm_ids", [])) == ESMS, f"{period} ESM set changed")
        require(sorted(str(item) for item in receipt.get("scenarios", [])) == SCENARIOS, f"{period} scenario set changed")
        nested[period] = validate_source_audits(receipt, root, period)

    combined = receipts["combined_period_inventory"]
    require(combined.get("schema") == "isimip3b_expanded_fair_training_audit_v1", "combined receipt schema changed")
    require(combined.get("years") == [2012, 2013, 2014, 2016, 2017, 2018, 2019, *range(2042, 2050), *range(2092, 2100)], "combined year inventory changed")
    require(combined.get("rows") == 2376990, "combined row inventory changed")
    require(combined.get("production_emulator_authorized") is False, "combined product authorization changed")

    return {
        "schema": "isimip3b_rimex_temporal_distinctness_preregistration_v1",
        "status": "validated_before_temporal_distinctness_audit",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "top_level_receipts_read": 4,
        "nested_receipts_read": sum(len(rows) for rows in nested.values()),
        "minimum_distinct_training_templates": 51,
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config, args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("temporal distinctness preregistration passed")


if __name__ == "__main__":
    main()
