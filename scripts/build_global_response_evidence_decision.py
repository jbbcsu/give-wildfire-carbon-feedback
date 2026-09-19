#!/usr/bin/env python3
"""Apply the frozen evidence hierarchy without fitting or reading raw data."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "yield": ROOT / "data/interim/global_country_heldout_20260908/result.json",
    "yield_audit": ROOT / "data/interim/global_country_heldout_20260908/aggregate_validation.json",
    "support": ROOT / "data/interim/global_maize_hist_future_support_20260918/result.json",
    "support_audit": ROOT / "data/interim/global_maize_hist_future_support_audit_20260918.json",
    "climate": ROOT / "data/interim/maize_gmst_normalized_weather_20260918.json",
    "climate_audit": ROOT / "data/interim/maize_gmst_normalized_weather_audit_20260918.json",
}
PROTOCOL = ROOT / "GLOBAL_RESPONSE_EVIDENCE_DECISION_PROTOCOL_20260919.md"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def interval_pass(crop, keys):
    bootstrap = crop["bootstrap"]
    if bootstrap.get("status") != "conditional_country_cluster_bootstrap":
        return False
    return all(bootstrap["intervals"][scheme][key][2] < 0
               for scheme in ("pooled_rmse", "equal_country_rmse") for key in keys)


def point_pass(crop, candidate, references):
    return all(crop["pooled_metrics"][candidate][scheme] < crop["pooled_metrics"][reference][scheme]
               for scheme in ("pooled_rmse", "equal_country_rmse") for reference in references)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        parser.error("fresh ignored output required")
    data = {name: json.loads(path.read_text()) for name, path in FILES.items()}
    if data["yield_audit"]["role"] != "independent_aggregate_verification_not_new_model" or data["support_audit"]["status"] != "passed" or data["climate_audit"]["status"] != "passed":
        raise ValueError("independent aggregate audits required")
    y = data["yield"]
    global_gate = (y["production_promotion_authorized"] is True
                   and y["independent_outcomes"] is True and y["new_untouched_holdout"] is True)
    families = {}
    rules = {
        "quantity": ("quantity", ("controls_only", "zero_change"), ("quantity_minus_heat", "quantity_minus_zero")),
        "distribution_increment": ("quantity_distribution", ("quantity",), ("distribution_minus_quantity",)),
        "seasonal_scpdsi": ("scpdsi_mean", ("quantity",), ("scpdsi_mean_minus_quantity",)),
        "stage_scpdsi": ("scpdsi_stages", ("quantity",), ("scpdsi_stages_minus_quantity",)),
    }
    for family, (candidate, references, intervals) in rules.items():
        per_crop = {}
        for crop_name in ("maize", "soy"):
            crop = y["crops"][crop_name]
            folds = sum(1 for fold in crop["folds"] if fold.get("status") == "evaluated")
            per_crop[crop_name] = {"scored_country_folds": folds,
                "point_better_on_both_weightings": point_pass(crop, candidate, references),
                "paired_interval_upper_below_zero_on_both_weightings": interval_pass(crop, intervals)}
        families[family] = {"per_crop": per_crop,
            "passes_predictive_rule": all(x["scored_country_folds"] == 5
                and x["point_better_on_both_weightings"]
                and x["paired_interval_upper_below_zero_on_both_weightings"]
                for x in per_crop.values()), "promoted": False}
    climate_records = data["climate"]["records"]
    signs = {"wet_days_n": -1, "cdd_max_days": 1, "rx1day_mm": 1, "rx5day_mm": 1}
    consistency = {feature: all(sign * row["feature_change_per_k"][feature] > 0 for row in climate_records)
                   for feature, sign in signs.items()}
    support_summary = data["support"]["esm_scenario_summary"]
    def span(feature):
        values = []
        for scenarios in support_summary.values():
            for row in scenarios.values():
                values.append(row["mean_area_fraction"]["below_min"][feature]
                              + row["mean_area_fraction"]["above_max"][feature])
        return [min(values), max(values)]
    for family in families.values():
        family["promoted"] = bool(global_gate and family["passes_predictive_rule"])
    output = {"status": "no_empirical_global_response_promoted",
        "protocol_sha256": sha(PROTOCOL),
        "sources": {name: {"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for name, path in FILES.items()},
        "global_independent_promotion_gate": global_gate, "families": families,
        "climate_distribution_sign_consistency_six_endpoints": consistency,
        "future_same_cell_minmax_outside_area_fraction_range": {
            feature: span(feature) for feature in ("precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c")},
        "research_benchmark": "seasonal precipitation quantity plus temperature controls",
        "distribution_status": "retain as physical and predictive sensitivity; not a damage function",
        "drought_status": "retain scPDSI and future SPEI as mutually exclusive competitors; not promoted",
        "process_crop_model_status": "structural benchmark only",
        "empirical_damage_or_scc_export_allowed": False}
    out.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
