#!/usr/bin/env python3
"""Independent audit of the aggregate response-evidence decision."""
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
        raise ValueError(f"decision audit mismatch: {a} != {b}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result_path, out = args.result.resolve(), args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        parser.error("fresh ignored audit output required")
    decision = json.loads(result_path.read_text())
    inputs = {}
    for name, source in decision["sources"].items():
        path = ROOT / source["path"]
        if sha(path) != source["sha256"]:
            raise ValueError("decision source hash changed")
        inputs[name] = json.loads(path.read_text())
    y = inputs["yield"]
    expected_global = all(y[x] is True for x in ("production_promotion_authorized", "independent_outcomes", "new_untouched_holdout"))
    if decision["global_independent_promotion_gate"] is not expected_global:
        raise ValueError("global promotion gate differs")
    rules = {
        "quantity": ("quantity", ("controls_only", "zero_change"), ("quantity_minus_heat", "quantity_minus_zero")),
        "distribution_increment": ("quantity_distribution", ("quantity",), ("distribution_minus_quantity",)),
        "seasonal_scpdsi": ("scpdsi_mean", ("quantity",), ("scpdsi_mean_minus_quantity",)),
        "stage_scpdsi": ("scpdsi_stages", ("quantity",), ("scpdsi_stages_minus_quantity",)),
    }
    checks = 0
    for family, (candidate, references, interval_keys) in rules.items():
        passes = []
        for crop_name in ("maize", "soy"):
            crop = y["crops"][crop_name]
            folds = sum(x["status"] == "evaluated" for x in crop["folds"])
            point = all(crop["pooled_metrics"][candidate][weight] < crop["pooled_metrics"][reference][weight]
                        for weight in ("pooled_rmse", "equal_country_rmse") for reference in references)
            boot = crop["bootstrap"]
            interval = boot.get("status") == "conditional_country_cluster_bootstrap" and all(
                boot["intervals"][weight][key][2] < 0
                for weight in ("pooled_rmse", "equal_country_rmse") for key in interval_keys)
            observed = decision["families"][family]["per_crop"][crop_name]
            if observed != {"scored_country_folds": folds, "point_better_on_both_weightings": point,
                            "paired_interval_upper_below_zero_on_both_weightings": interval}:
                raise ValueError("per-crop predictive decision differs")
            passes.append(folds == 5 and point and interval); checks += 3
        expected = all(passes)
        if decision["families"][family]["passes_predictive_rule"] is not expected or decision["families"][family]["promoted"] is not (expected and expected_global):
            raise ValueError("family promotion decision differs")
        checks += 2
    climate = inputs["climate"]["records"]
    for feature, sign in {"wet_days_n": -1, "cdd_max_days": 1, "rx1day_mm": 1, "rx5day_mm": 1}.items():
        expected = all(sign * x["feature_change_per_k"][feature] > 0 for x in climate)
        if decision["climate_distribution_sign_consistency_six_endpoints"][feature] is not expected:
            raise ValueError("physical sign decision differs")
        checks += 1
    summaries = inputs["support"]["esm_scenario_summary"]
    for feature, observed in decision["future_same_cell_minmax_outside_area_fraction_range"].items():
        values = [row["mean_area_fraction"]["below_min"][feature] + row["mean_area_fraction"]["above_max"][feature]
                  for scenarios in summaries.values() for row in scenarios.values()]
        close(observed[0], min(values)); close(observed[1], max(values)); checks += 2
    if decision["status"] != "no_empirical_global_response_promoted" or decision["empirical_damage_or_scc_export_allowed"] is not False:
        raise ValueError("claim boundary differs")
    audit = {"status": "passed", "result_sha256": sha(result_path),
             "sources_rehashed": len(inputs), "decision_checks": checks,
             "no_raw_or_row_level_data_read": True}
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
