"""Independently recompute four holdout score tables from saved year ledgers."""
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDICTORS = ("unchanged", "quantity_only", "monthly_pattern")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def d(value):
    return Decimal(str(value))


def independently_aggregate(years):
    with localcontext() as ctx:
        ctx.prec = 50
        annual_den = sum(d(r["area_sum_m2"]) for r in years)
        monthly_den = 12*annual_den
        share_den = sum(d(r["common_valid_area_m2"]) for r in years)
        if min(annual_den, monthly_den, share_den) <= 0:
            raise ValueError("invalid score denominators")
        scores = {}
        for name in PREDICTORS:
            rows = [r["metrics"][name] for r in years]
            scores[name] = dict(
                monthly_amount_rmse_mm=(sum(d(e["monthly_squared_error_area_sum"]) for e in rows)/monthly_den).sqrt(),
                monthly_amount_bias_mm=sum(d(e["monthly_error_area_sum"]) for e in rows)/monthly_den,
                annual_amount_rmse_mm=(sum(d(e["annual_squared_error_area_sum"]) for e in rows)/annual_den).sqrt(),
                annual_amount_bias_mm=sum(d(e["annual_error_area_sum"]) for e in rows)/annual_den,
                common_area_mean_month_share_tv=sum(d(e["share_tv_area_sum"]) for e in rows)/share_den,
                negative_cell_months=sum(e["negative_cell_months"] for e in rows),
                nonpositive_annual_cells=sum(e["nonpositive_annual_cells"] for e in rows),
                minimum_predicted_monthly_mm=min(d(e["minimum_monthly_mm"]) for e in rows))
        return scores, share_den/annual_den, annual_den, share_den


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh holdout audit output required")
    records = []
    checks = 0
    maximum = 0.0
    for model in ("GFDL-ESM4", "IPSL-CM6A-LR"):
        slug = model.lower().replace("-", "_")
        for holdout, experiment, start, end in (("ssp126", "ssp126", 2031, 2060),
                                                ("ssp585_late", "ssp585", 2081, 2100)):
            path = ROOT / f"data/interim/pangeo_{slug}_{holdout}_monthly_pattern_holdout_20260917/result.json"
            result = json.loads(path.read_text())
            if (result["status"] != "monthly_raw_cmip6_holdout_scored_not_crop_validated"
                    or result["model"] != model or result["holdout"] != holdout
                    or result["source"]["experiment_id"] != experiment
                    or result["source"]["member_id"] != "r1i1p1f1"
                    or result["years"] != [start, end]
                    or result["whole_scenario_holdout"] != (holdout == "ssp126")
                    or any(not c["server_md5_verified"] for c in result["source_chunks"])):
                raise ValueError("holdout source, identity, scenario or checksum differs")
            fit_path = ROOT / f"data/interim/pangeo_{slug}_ssp585_monthly_pattern_fit_20260917/result.json"
            if result["fit_result_sha256"] != sha(fit_path):
                raise ValueError("frozen training fit binding differs")
            years = result["annual_sufficient_statistics"]
            if [r["year"] for r in years] != list(range(start, end+1)):
                raise ValueError("holdout years incomplete or out of order")
            lo, hi = result["training_gmst_range_k"]
            outside = [r["year"] for r in years if not lo <= r["gmst_anomaly_k"] <= hi]
            if outside != result["out_of_training_gmst_years"]:
                raise ValueError("out-of-support year accounting differs")
            for row in years:
                if not 0 < row["common_valid_area_m2"] <= row["area_sum_m2"]:
                    raise ValueError("invalid common support area")
            scores, fraction, total, common = independently_aggregate(years)
            pooled = result["pooled"]
            for got, expected in ((pooled["common_valid_area_fraction"], fraction),
                                  (pooled["total_cell_year_area_m2"], total),
                                  (pooled["common_valid_cell_year_area_m2"], common)):
                error = abs(d(got)-expected)/max(Decimal(1), abs(expected))
                maximum = max(maximum, float(error)); checks += 1
            for name in PREDICTORS:
                for key, expected in scores[name].items():
                    got = pooled["models"][name][key]
                    error = abs(d(got)-expected)/max(Decimal(1), abs(expected))
                    maximum = max(maximum, float(error)); checks += 1
            records.append(dict(model=model, holdout=holdout, years=[start, end],
                                result_sha256=sha(path), out_of_support_years=len(outside),
                                common_area_fraction=float(fraction)))
    if checks != 4*(3+3*8) or maximum > 1e-11:
        raise ValueError(f"independent holdout summary arithmetic differs: {checks} {maximum}")
    args.out_dir.mkdir(parents=True)
    output = dict(status="four_raw_cmip6_monthly_holdouts_independently_aggregated",
                  checks=checks, maximum_scaled_error=maximum, records=records,
                  limitation="Recomputes saved area-weighted score summaries, not source precipitation or crop-calendar effects; no yield, damage or SCC validation.")
    (args.out_dir / "result.json").write_text(json.dumps(output, indent=2))
    print(output["status"], checks, maximum)


if __name__ == "__main__":
    main()
