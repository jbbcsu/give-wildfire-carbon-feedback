"""Independent cell-ledger audit of two-ESM, two-calendar maize climate scores."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PREDICTORS = ("unchanged", "quantity_only", "monthly_pattern")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def near(got, expected, label):
    if not math.isfinite(got) or abs(got-expected) > 1e-9*max(1.0, abs(expected)):
        raise ValueError(f"independent maize score differs: {label}: {got} {expected}")
    return abs(got-expected)/max(1.0, abs(expected))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh crop benchmark audit output required")
    records, checks, maximum = [], 0, 0.0
    for model, suffix in (("GFDL-ESM4", "_v2"), ("IPSL-CM6A-LR", "")):
        slug = model.lower().replace("-", "_")
        directory = ROOT / f"data/interim/pangeo_{slug}_ssp126_maize_monthly_crop_benchmark{suffix}_20260917"
        result_path = directory / "result.json"
        result = json.loads(result_path.read_text())
        if (result["status"] != "monthly_gmt_patterns_crop_calendar_climatology_scored_not_yield_validated"
                or result["model"] != model or result["target_crop"] != "rainfed_maize"
                or result["period"] != [2031, 2060] or result["predecessor_period"] != [2030, 2059]
                or len(result["summaries"]) != 2 or len(result["records"]) != 2):
            raise ValueError("maize climate benchmark source/period contract differs")
        for summary in result["summaries"]:
            convention = summary["convention"]
            entry, = [r for r in result["records"] if r["convention"] == convention]
            path = ROOT / entry["path"]
            if sha(path) != entry["sha256"]:
                raise ValueError("crop-cell ledger hash differs")
            table = pq.read_table(path).to_pandas()
            if len(table) != 30821 or table.duplicated(["latitude", "longitude"]).any():
                raise ValueError("crop-cell ledger key support differs")
            if not np.isfinite(table.area_ha).all() or (table.area_ha <= 0).any():
                raise ValueError("crop-cell area invalid")
            valid = table.loc[table.category == "valid_actual_calendar_climate"]
            common = valid.loc[valid.common_physical_support]
            if (len(valid) != 28328 or len(common) <= 0
                    or not np.isfinite(valid.actual_season_mm).all()
                    or (valid.actual_season_mm <= 0).any()):
                raise ValueError("valid maize climate/calendar support differs")
            full_area = math.fsum(table.area_ha)
            valid_area = math.fsum(valid.area_ha)
            common_area = math.fsum(common.area_ha)
            numbers = dict(full_mapped_area_ha=full_area, valid_actual_area_ha=valid_area,
                           common_physical_area_ha=common_area,
                           valid_actual_area_fraction=valid_area/full_area,
                           common_of_valid_area_fraction=common_area/valid_area,
                           valid_actual_cells=len(valid), common_physical_cells=len(common))
            for key, expected in numbers.items():
                maximum = max(maximum, near(float(summary[key]), float(expected), key)); checks += 1
            for name in PREDICTORS:
                forecast = valid[f"{name}_season_mm"]
                if not np.isfinite(forecast).all():
                    raise ValueError("nonfinite crop-season prediction")
                error = forecast-valid.actual_season_mm
                tv = common[f"{name}_share_tv"]
                centroid = common[f"{name}_centroid_error_days"]
                if (not np.isfinite(tv).all() or (tv < 0).any() or (tv > 1).any()
                        or not np.isfinite(centroid).all()
                        or (common[f"{name}_negative_months"] > 0).any()):
                    raise ValueError("common-share physical values invalid")
                expected = dict(
                    season_amount_rmse_mm=math.sqrt(math.fsum(valid.area_ha*error*error)/valid_area),
                    season_amount_bias_mm=math.fsum(valid.area_ha*error)/valid_area,
                    common_area_month_share_tv=math.fsum(common.area_ha*tv)/common_area,
                    common_area_absolute_centroid_error_days=math.fsum(common.area_ha*abs(centroid))/common_area,
                    negative_crop_cell_months=int(valid[f"{name}_negative_months"].sum()),
                    crop_cells_with_negative_month=int((valid[f"{name}_negative_months"] > 0).sum()))
                for key, value in expected.items():
                    maximum = max(maximum, near(float(summary["models"][name][key]), float(value), name+"/"+key))
                    checks += 1
            records.append(dict(model=model, convention=convention, result_sha256=sha(result_path),
                                ledger_sha256=sha(path), valid_cells=len(valid), common_cells=len(common)))
    if checks != 4*(7+3*6):
        raise ValueError(f"independent maize score check count differs: {checks}")
    args.out_dir.mkdir(parents=True)
    output = dict(status="four_maize_monthly_climate_benchmarks_independently_aggregated",
                  checks=checks, maximum_scaled_error=maximum, records=records,
                  limitation="Recalculates saved crop-cell climate score aggregates, not raw climate chunks, yield effects, damages or SCC.")
    (args.out_dir / "result.json").write_text(json.dumps(output, indent=2))
    print(output["status"], checks, maximum)


if __name__ == "__main__":
    main()
