#!/usr/bin/env python3
"""Build an aggregate-only U.S. NASS evidence synthesis."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "common_range": ROOT / "data/interim/us_source_matched_response_20260908/common_range_rainfall.json",
    "paired_loss": ROOT / "data/provenance/us_competing_moisture_paired_loss_uncertainty_20260826.json",
    "tmax_sensitivity": ROOT / "data/provenance/us_moisture_tmax_sensitivity_verified_20260905.json",
    "recent_terminal": ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_prediction_20260916/result.json",
    "recent_terminal_audit": ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_validation_20260916/result.json",
}
PROTOCOL = ROOT / "US_NASS_EVIDENCE_SYNTHESIS_PROTOCOL_20260919.md"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        parser.error("fresh ignored output required")
    data = {name: json.loads(path.read_text()) for name, path in SOURCES.items()}
    common = data["common_range"]
    if common["causal_or_scc_result"] is not False or common["status"] != "us_common_range_rainfall_sensitivity_complete":
        raise ValueError("qualified common-range source required")
    quantity = {}
    for crop in ("corn_grain", "soybeans"):
        for practice in ("non_irrigated", "irrigated"):
            rows = [x for x in common["results"] if x["crop"] == crop and x["practice"] == practice
                    and x["form"] == "quantity" and x["primary_threshold"] is True]
            if len(rows) != 1:
                raise ValueError("unique common-range primary quantity result required")
            row = rows[0]
            source_rows = row["source_estimates"]
            compact = {source: {
                "mean_percent_response": values["equal_county_mean_percent_response"]["estimate"],
                "ci95_percent": values["equal_county_mean_percent_response"]["ci95_normal"]}
                for source, values in source_rows.items()}
            quantity[f"{crop}|{practice}"] = {
                "evaluation_counties": row["evaluation_counties"],
                "mean_rainfall_reduction_mm": -row["rainfall_change_mm"]["mean"],
                "weather_sources": compact,
                "both_sources_negative_upper_below_zero": all(
                    x["mean_percent_response"] < 0 and x["ci95_percent"][1] < 0 for x in compact.values()),
                "both_source_intervals_include_zero": all(
                    x["ci95_percent"][0] <= 0 <= x["ci95_percent"][1] for x in compact.values()),
            }
    paired = data["paired_loss"]
    if paired["status"] != "validated_conditional_us_county_paired_predictive_loss_sensitivity":
        raise ValueError("validated paired-loss source required")
    pooled = {}
    for crop in ("corn_grain", "soybeans"):
        for comparison in ("direct_quantity_distribution_minus_direct_quantity", "pdsi_season_mean_minus_direct_quantity"):
            rows = [x for x in paired["comparisons"] if x["crop"] == crop and x["irrigation_practice"] == "non_irrigated"
                    and x["report_scope"] == "pooled_development_oof" and x["comparison_id"] == comparison]
            if len(rows) != 1:
                raise ValueError("unique pooled non-irrigated comparison required")
            row = rows[0]
            pooled[f"{crop}|{comparison}"] = {k: row[k] for k in
                ("test_row_count", "rmse_difference", "rmse_interval", "mae_difference", "mae_interval", "sign_convention")}
    sensitivity = data["tmax_sensitivity"]
    if sensitivity["causal_or_scc_result"] is not False:
        raise ValueError("noncausal sensitivity source required")
    controls = {}
    for design in ("baseline", "additional_stage_tmax"):
        summaries = sensitivity["results"][design]["comparison_summaries"]
        for crop in ("corn_grain", "soybeans"):
            rows = [x for x in summaries if x["crop"] == crop and x["irrigation_practice"] == "non_irrigated"]
            if len(rows) != 1:
                raise ValueError("unique non-irrigated control summary required")
            row = rows[0]
            pdsi = row["direct_quantity_minus_pdsi_season_rmse_by_eligible_state"]
            controls[f"{design}|{crop}"] = {
                "distribution_selected_on_frozen_state_gate": row["direct_distribution_selected_on_development_leave_state_out"],
                "distribution_mean_state_rmse_improvement": row["direct_distribution_mean_leave_state_out_rmse_improvement"],
                "distribution_terminal_rmse_improvement": row["direct_distribution_terminal_rmse_improvement_not_used_for_selection"],
                "distribution_extreme_rmse_improvement": row["direct_distribution_extreme_rmse_improvement_not_used_for_selection"],
                "pdsi_states_favoring_pdsi": sum(value > 0 for value in pdsi.values()),
                "pdsi_eligible_states": len(pdsi),
                "pdsi_terminal_favors_pdsi": row["direct_quantity_minus_pdsi_season_terminal_rmse"] > 0,
            }
    recent = data["recent_terminal"]
    recent_audit = data["recent_terminal_audit"]
    if (recent["status"] != "post_result_pdsi_competing_prediction_not_causal"
            or recent_audit["status"] != "independent_post_result_pdsi_competitor_validated"
            or recent_audit["source_result_sha256"] != sha(SOURCES["recent_terminal"])):
        raise ValueError("validated recent all-practice comparison required")
    terminal = {}
    for trend in ("common", "state"):
        for crop in ("corn_grain", "soybeans"):
            scores = recent["crops"][trend][crop]["terminal_scores"]
            compact = {model: {"n": row["n"], "rmse_log_yield": row["rmse_log_yield"]}
                       for model, row in scores.items()}
            terminal[f"{trend}|{crop}"] = {"scores": compact,
                "lowest_rmse_model": min(compact, key=lambda model: compact[model]["rmse_log_yield"])}
    result = {"status": "us_nass_validation_priority_not_damage_model",
        "protocol_sha256": sha(PROTOCOL),
        "sources": {name: {"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for name, path in SOURCES.items()},
        "common_range_quantity": quantity, "pooled_nonirrigated_predictive_differences": pooled,
        "temperature_control_sensitivity": controls,
        "recent_2020_2025_all_practice_terminal_qualification": terminal,
        "interpretation": {
            "strongest_validation_priority": "non-irrigated corn moisture stress, especially PDSI, with precipitation distribution secondary",
            "distribution_promoted": False, "drought_promoted_to_global_damage": False,
            "causal_climate_yield_response": False, "global_transfer_authorized": False,
            "damage_or_scc_export_allowed": False}}
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
