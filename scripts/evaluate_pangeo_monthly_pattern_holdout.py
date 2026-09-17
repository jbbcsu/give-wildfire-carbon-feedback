"""Score frozen monthly GMT patterns on whole-scenario or late-time holdouts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from acquire_cmip6_native_cell_area import fetch

ROOT = Path(__file__).resolve().parents[1]
MODELS = ("GFDL-ESM4", "IPSL-CM6A-LR")
HOLDOUTS = {"ssp126": (2031, 2060), "ssp585_late": (2081, 2100)}
PREDICTORS = ("unchanged", "quantity_only", "monthly_pattern")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score_year(actual, predictions, area, np):
    """Return unnormalized sufficient statistics on one common valid support."""
    if actual.shape[0] != 12 or any(p.shape != actual.shape for p in predictions.values()):
        raise ValueError("whole-year monthly field shapes differ")
    if not np.isfinite(actual).all() or np.any(actual < 0):
        raise ValueError("holdout source precipitation invalid")
    actual_year = actual.sum(axis=0)
    common = actual_year > 0
    physical = {}
    for name in PREDICTORS:
        p = predictions[name]
        if not np.isfinite(p).all():
            raise ValueError("nonfinite holdout pattern prediction")
        annual = p.sum(axis=0)
        bad = np.any(p < 0, axis=0) | (annual <= 0)
        physical[name] = dict(negative_cell_months=int(np.count_nonzero(p < 0)),
                              nonpositive_annual_cells=int(np.count_nonzero(annual <= 0)),
                              minimum_monthly_mm=float(np.min(p)))
        common &= ~bad
    area_sum = float(np.sum(area, dtype=np.float64))
    common_area = float(np.sum(area[common], dtype=np.float64))
    if common_area <= 0:
        raise ValueError("no common valid precipitation-pattern area")
    stats = {}
    actual_share = np.divide(actual[:, common], actual_year[common])
    for name in PREDICTORS:
        p = predictions[name]
        difference = p - actual
        annual_difference = p.sum(axis=0)-actual_year
        pred_share = np.divide(p[:, common], p[:, common].sum(axis=0))
        tv = 0.5 * np.abs(pred_share-actual_share).sum(axis=0)
        stats[name] = dict(
            monthly_squared_error_area_sum=float(np.sum((difference*difference)*area[None], dtype=np.float64)),
            monthly_error_area_sum=float(np.sum(difference*area[None], dtype=np.float64)),
            annual_squared_error_area_sum=float(np.sum((annual_difference*annual_difference)*area, dtype=np.float64)),
            annual_error_area_sum=float(np.sum(annual_difference*area, dtype=np.float64)),
            share_tv_area_sum=float(np.sum(tv*area[common], dtype=np.float64)),
            **physical[name])
    return dict(area_sum_m2=area_sum, common_valid_area_m2=common_area, metrics=stats)


def aggregate(year_stats):
    """Pooled area-weighted scores from retained year-level sufficient stats."""
    import math

    monthly_den = math.fsum(r["area_sum_m2"]*12 for r in year_stats)
    annual_den = math.fsum(r["area_sum_m2"] for r in year_stats)
    tv_den = math.fsum(r["common_valid_area_m2"] for r in year_stats)
    if min(monthly_den, annual_den, tv_den) <= 0:
        raise ValueError("holdout scoring denominator absent")
    result = {}
    for name in PREDICTORS:
        entries = [r["metrics"][name] for r in year_stats]
        result[name] = dict(
            monthly_amount_rmse_mm=math.sqrt(math.fsum(e["monthly_squared_error_area_sum"] for e in entries)/monthly_den),
            monthly_amount_bias_mm=math.fsum(e["monthly_error_area_sum"] for e in entries)/monthly_den,
            annual_amount_rmse_mm=math.sqrt(math.fsum(e["annual_squared_error_area_sum"] for e in entries)/annual_den),
            annual_amount_bias_mm=math.fsum(e["annual_error_area_sum"] for e in entries)/annual_den,
            common_area_mean_month_share_tv=math.fsum(e["share_tv_area_sum"] for e in entries)/tv_den,
            negative_cell_months=sum(e["negative_cell_months"] for e in entries),
            nonpositive_annual_cells=sum(e["nonpositive_annual_cells"] for e in entries),
            minimum_predicted_monthly_mm=min(e["minimum_monthly_mm"] for e in entries))
    return dict(models=result, common_valid_area_fraction=tv_den/annual_den,
                total_cell_year_area_m2=annual_den, common_valid_cell_year_area_m2=tv_den)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=MODELS, required=True)
    p.add_argument("--holdout", choices=tuple(HOLDOUTS), required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--dependency-dir", type=Path)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh holdout result required")
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    import numpy as np
    import cftime
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)

    slug = args.model.lower().replace("-", "_")
    audit_path = ROOT / "data/interim/pangeo_monthly_pattern_fit_validation_20260917/result.json"
    audit = json.loads(audit_path.read_text())
    if audit["status"] != "two_monthly_climate_fits_independently_audited_not_holdout_validated":
        raise ValueError("frozen climate fits have not passed independent audit")
    audit_record, = [r for r in audit["records"] if r["model"] == args.model]
    fit_dir = ROOT / f"data/interim/pangeo_{slug}_ssp585_monthly_pattern_fit_20260917"
    fit_path = fit_dir / "result.json"
    fit = json.loads(fit_path.read_text())
    coefficient_path = fit_dir / "monthly_pattern_coefficients.npz"
    if sha(fit_path) != audit_record["fit_result_sha256"] or sha(coefficient_path) != audit_record["coefficient_sha256"]:
        raise ValueError("fitted coefficient binding differs")
    with np.load(coefficient_path, allow_pickle=False) as saved:
        alpha = saved["monthly_intercept_flux"]
        beta = saved["monthly_slope_flux_per_k"]
        qa = saved["annual_quantity_intercept_mm"]
        qb = saved["annual_quantity_slope_mm_per_k"]
        base_flux = saved["historical_monthly_flux"]
        base_share = saved["historical_month_share"]
        fit_lat, fit_lon = saved["latitude"], saved["longitude"]
    area_dir = ROOT / f"data/interim/cmip6_{slug}_native_area_20260917"
    area_receipt = json.loads((area_dir / "result.json").read_text())
    area_path = area_dir / "native_cell_area.npz"
    if sha(area_path) != area_receipt["output_sha256"] or area_receipt["model"] != args.model:
        raise ValueError("native area source binding differs")
    with np.load(area_path, allow_pickle=False) as saved:
        area = saved["area_m2"].astype(np.float64)
        if (not np.allclose(saved["latitude"], fit_lat, atol=1e-10, rtol=0)
                or not np.allclose(saved["longitude"], fit_lon, atol=1e-10, rtol=0)):
            raise ValueError("fitted and area grid coordinates differ")

    experiment = "ssp126" if args.holdout == "ssp126" else "ssp585"
    start, end = HOLDOUTS[args.holdout]
    gmst_path = ROOT / f"data/interim/pangeo_{slug}_{experiment}_annual_gmst_20260917/result.json"
    gmst = json.loads(gmst_path.read_text())
    year_x = {r["year"]: r["gmst_value_k"]-fit["historical_gmst_reference_k"]
              for r in gmst["annual"] if start <= r["year"] <= end}
    if sorted(year_x) != list(range(start, end+1)):
        raise ValueError("holdout GMST year support differs")
    lo, hi = fit["training_gmst_range_k"]
    outside = [y for y, x in year_x.items() if not lo <= x <= hi]

    mp = ROOT / "data/interim/pangeo_monthly_store_metadata_20260908/result.json"
    cp = ROOT / "data/interim/pangeo_monthly_coordinates_units_20260908/result.json"
    inv, coords = json.loads(mp.read_text()), json.loads(cp.read_text())
    if coords["metadata_inventory_sha256"] != sha(mp):
        raise ValueError("monthly source coordinate binding differs")
    selector = lambda r: (r["source"]["source_id"], r["source"]["experiment_id"], r["source"]["variable_id"]) == (args.model, experiment, "pr")
    rows, axes = [r for r in inv["records"] if selector(r)], [r for r in coords["records"] if selector(r)]
    if len(rows) != 1 or len(axes) != 1:
        raise ValueError("one exact holdout precipitation source required")
    row, axis = rows[0], axes[0]
    if (row["source"]["member_id"] != gmst["source"]["member_id"]
            or row["source"]["member_id"] != fit["source"]["member_id"]
            or row["time_attributes"]["calendar"] != gmst["calendar"]):
        raise ValueError("holdout rainfall/GMST realization or calendar differs")
    meta_path = ROOT / row["metadata_file"]
    if sha(meta_path) != row["metadata_sha256"]:
        raise ValueError("holdout precipitation metadata changed")
    meta = json.loads(meta_path.read_text())["metadata"]
    coords_data = {}
    for chunk in axis["chunks"]:
        path = ROOT / chunk["file"]
        if sha(path) != chunk["sha256"]:
            raise ValueError("holdout coordinate chunk changed")
        name = chunk["variable"]
        spec = meta[name + "/.zarray"]
        coords_data[name] = np.frombuffer(numcodecs.get_codec(spec["compressor"]).decode(path.read_bytes()),
                                          dtype=spec["dtype"]).reshape(spec["shape"])
    if (not np.allclose(coords_data["lat"], fit_lat, rtol=0, atol=1e-10)
            or not np.allclose(coords_data["lon"], fit_lon, rtol=0, atol=1e-10)):
        raise ValueError("holdout and fitted grid coordinates differ")
    ta = row["time_attributes"]
    dates = cftime.num2date(coords_data["time"], ta["units"], calendar=ta["calendar"])
    bound_name = ta["bounds"]
    battrs = meta[bound_name + "/.zattrs"]
    bounds = cftime.num2date(coords_data[bound_name], battrs.get("units", ta["units"]), calendar=ta["calendar"])
    seconds = np.array([(b-a).total_seconds() for a, b in bounds])
    years = np.array([d.year for d in dates]); months = np.array([d.month for d in dates])
    selected = np.flatnonzero((years >= start) & (years <= end))
    if len(selected) != 12*(end-start+1) or not (seconds[selected] > 0).all():
        raise ValueError("holdout source month support differs")
    shape = tuple(area.shape); spec = row["variable_array"]
    size = math.prod(spec["chunks"]) * np.dtype(spec["dtype"]).itemsize
    if (size > 192*1024**2 or spec["filters"] is not None or spec["order"] != "C"
            or tuple(spec["chunks"][1:]) != shape or spec["compressor"]["id"] != "blosc"):
        raise ValueError("unsupported holdout precipitation source chunk")

    arrays = {"actual": np.empty((12,) + shape, dtype=np.float64)}
    arrays.update({name: np.empty((12,) + shape, dtype=np.float64) for name in PREDICTORS})
    year_stats, receipts = [], []
    current_year, next_month = start, 1
    for chunk_number in sorted(set(selected // spec["chunks"][0])):
        key = f"{int(chunk_number)}.0.0"
        url = row["metadata_url"].removesuffix(".zmetadata") + "pr/" + key
        content, receipt = fetch(url, min(size + 1024**2, 112*1024**2))
        nbytes, cbytes, _ = _cbuffer_sizes(content)
        if nbytes != size or cbytes != len(content):
            raise ValueError("holdout precipitation compressed header differs")
        decoded = numcodecs.get_codec(spec["compressor"]).decode(content)
        del content
        data = np.frombuffer(decoded, dtype=spec["dtype"]).reshape(spec["chunks"])
        for index in selected[selected // spec["chunks"][0] == chunk_number]:
            year, month = int(years[index]), int(months[index])
            if (year, month) != (current_year, next_month):
                raise ValueError("holdout months out of order")
            plane = data[index % spec["chunks"][0]]
            if (not np.isfinite(plane).all() or np.any(plane == spec["fill_value"])
                    or np.any(plane < 0)):
                raise ValueError("holdout source precipitation invalid")
            m = month-1; x = year_x[year]; duration = seconds[index]
            arrays["actual"][m] = plane * duration
            arrays["unchanged"][m] = base_flux[m] * duration
            arrays["quantity_only"][m] = (qa + qb*x) * base_share[m]
            arrays["monthly_pattern"][m] = (alpha[m] + beta[m]*x) * duration
            if month == 12:
                year_stats.append(dict(year=year, gmst_anomaly_k=x,
                                       **score_year(arrays["actual"],
                                                    {name: arrays[name] for name in PREDICTORS}, area, np)))
                current_year += 1; next_month = 1
            else:
                next_month += 1
        receipts.append(receipt)
        del data, decoded
        print("holdout source chunk verified", key, flush=True)
    if (current_year, next_month) != (end+1, 1) or len(year_stats) != end-start+1:
        raise ValueError("holdout whole-year scoring incomplete")
    pooled = aggregate(year_stats)
    args.out_dir.mkdir(parents=True)
    result = dict(status="monthly_raw_cmip6_holdout_scored_not_crop_validated",
                  model=args.model, holdout=args.holdout, source=row["source"], license=row["license"],
                  years=[start, end], whole_scenario_holdout=(experiment == "ssp126"),
                  training_gmst_range_k=[lo, hi], holdout_gmst_range_k=[min(year_x.values()), max(year_x.values())],
                  out_of_training_gmst_years=outside, area_source_sha256=sha(area_dir / "result.json"),
                  fit_result_sha256=sha(fit_path), fit_coefficients_sha256=sha(coefficient_path),
                  fit_independent_audit_sha256=sha(audit_path), gmst_result_sha256=sha(gmst_path),
                  source_metadata_sha256=sha(meta_path), coordinate_receipt_sha256=sha(cp),
                  source_chunks=receipts, annual_sufficient_statistics=year_stats,
                  pooled=pooled, code_sha256=sha(Path(__file__)),
                  limitation="Raw-CMIP6 native-grid climate-only holdout; not yet crop-calendar or daily-feature validation, yield effects, damages, or SCC.")
    (args.out_dir / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    print(result["status"], args.model, args.holdout, pooled["common_valid_area_fraction"], flush=True)


if __name__ == "__main__":
    main()
