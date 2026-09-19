#!/usr/bin/env python3
"""Independent aggregate audit of the U.S. NASS evidence synthesis."""
import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(a, b):
    if not math.isclose(float(a), float(b), rel_tol=0, abs_tol=2e-15):
        raise ValueError(f"U.S. synthesis audit mismatch: {a} != {b}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result_path, out = args.result.resolve(), args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        parser.error("fresh ignored audit output required")
    result = json.loads(result_path.read_text())
    sources = {}
    for name, record in result["sources"].items():
        path = ROOT / record["path"]
        if sha(path) != record["sha256"]:
            raise ValueError("U.S. synthesis source changed")
        sources[name] = json.loads(path.read_text())
    checks = 0
    common = sources["common_range"]
    for key, saved in result["common_range_quantity"].items():
        crop, practice = key.split("|")
        rows = [x for x in common["results"] if x["crop"] == crop and x["practice"] == practice
                and x["form"] == "quantity" and x["primary_threshold"] is True]
        if len(rows) != 1:
            raise ValueError("common-range audit identity differs")
        row = rows[0]
        if saved["evaluation_counties"] != row["evaluation_counties"]:
            raise ValueError("evaluation counties differ")
        close(saved["mean_rainfall_reduction_mm"], -row["rainfall_change_mm"]["mean"]); checks += 2
        negative, include_zero = [], []
        for source, values in row["source_estimates"].items():
            source_saved = saved["weather_sources"][source]
            estimate = values["equal_county_mean_percent_response"]["estimate"]
            interval = values["equal_county_mean_percent_response"]["ci95_normal"]
            close(source_saved["mean_percent_response"], estimate)
            close(source_saved["ci95_percent"][0], interval[0]); close(source_saved["ci95_percent"][1], interval[1])
            negative.append(estimate < 0 and interval[1] < 0)
            include_zero.append(interval[0] <= 0 <= interval[1]); checks += 3
        if saved["both_sources_negative_upper_below_zero"] is not all(negative) or saved["both_source_intervals_include_zero"] is not all(include_zero):
            raise ValueError("common-range interpretation differs")
        checks += 2
    paired = sources["paired_loss"]
    for key, saved in result["pooled_nonirrigated_predictive_differences"].items():
        crop, comparison = key.split("|", 1)
        rows = [x for x in paired["comparisons"] if x["crop"] == crop and x["irrigation_practice"] == "non_irrigated"
                and x["report_scope"] == "pooled_development_oof" and x["comparison_id"] == comparison]
        if len(rows) != 1:
            raise ValueError("paired-loss audit identity differs")
        row = rows[0]
        if saved["test_row_count"] != row["test_row_count"] or saved["sign_convention"] != row["sign_convention"]:
            raise ValueError("paired-loss support differs")
        for metric in ("rmse", "mae"):
            close(saved[f"{metric}_difference"], row[f"{metric}_difference"])
            close(saved[f"{metric}_interval"]["lower"], row[f"{metric}_interval"]["lower"])
            close(saved[f"{metric}_interval"]["upper"], row[f"{metric}_interval"]["upper"])
            checks += 3
        checks += 2
    sensitivity = sources["tmax_sensitivity"]
    for key, saved in result["temperature_control_sensitivity"].items():
        design, crop = key.split("|")
        rows = [x for x in sensitivity["results"][design]["comparison_summaries"]
                if x["crop"] == crop and x["irrigation_practice"] == "non_irrigated"]
        if len(rows) != 1:
            raise ValueError("temperature-control audit identity differs")
        row = rows[0]
        pdsi = row["direct_quantity_minus_pdsi_season_rmse_by_eligible_state"]
        expected = {
            "distribution_selected_on_frozen_state_gate": row["direct_distribution_selected_on_development_leave_state_out"],
            "distribution_mean_state_rmse_improvement": row["direct_distribution_mean_leave_state_out_rmse_improvement"],
            "distribution_terminal_rmse_improvement": row["direct_distribution_terminal_rmse_improvement_not_used_for_selection"],
            "distribution_extreme_rmse_improvement": row["direct_distribution_extreme_rmse_improvement_not_used_for_selection"],
            "pdsi_states_favoring_pdsi": sum(x > 0 for x in pdsi.values()), "pdsi_eligible_states": len(pdsi),
            "pdsi_terminal_favors_pdsi": row["direct_quantity_minus_pdsi_season_terminal_rmse"] > 0}
        for field, value in expected.items():
            if isinstance(value, float): close(saved[field], value)
            elif saved[field] != value: raise ValueError("temperature-control summary differs")
            checks += 1
    boundary = result["interpretation"]
    if any(boundary[x] is not False for x in ("distribution_promoted", "drought_promoted_to_global_damage",
                                               "causal_climate_yield_response", "global_transfer_authorized",
                                               "damage_or_scc_export_allowed")):
        raise ValueError("U.S. interpretation boundary differs")
    audit = {"status": "passed", "result_sha256": sha(result_path),
             "sources_rehashed": len(sources), "aggregate_checks": checks,
             "no_county_rows_coefficients_predictions_or_raw_weather_read": True}
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
