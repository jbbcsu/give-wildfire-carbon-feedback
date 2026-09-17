"""Fit a published-style monthly raw-CMIP6 rain pattern to same-ESM GMST."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from acquire_cmip6_native_cell_area import fetch

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ols_from_sums(sum_y, sum_xy, x, n, np):
    """Gridwise intercept/slope for one shared, prechecked predictor vector."""
    if len(x) != n or n < 3:
        raise ValueError("regression sample size differs")
    sx = math.fsum(float(t) for t in x)
    sxx = math.fsum(float(t) ** 2 for t in x) - sx * sx / n
    if not math.isfinite(sxx) or sxx <= 0.01:
        raise ValueError("training GMST variation is insufficient")
    slope = (sum_xy - sx * sum_y / n) / sxx
    intercept = (sum_y - slope * sx) / n
    if not np.isfinite(slope).all() or not np.isfinite(intercept).all():
        raise ValueError("nonfinite pattern fit")
    return intercept, slope


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=("GFDL-ESM4", "IPSL-CM6A-LR"), required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--dependency-dir", type=Path)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh model output required")
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    import numpy as np
    import cftime
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)

    audit_path = ROOT / "data/interim/pangeo_annual_gmst_validation_20260917/result.json"
    audit = json.loads(audit_path.read_text())
    if audit["status"] != "six_annual_gmst_saved_products_independently_audited" or audit["annual_checks"] != 404:
        raise ValueError("same-model GMST independent audit absent")
    slug = args.model.lower().replace("-", "_")
    def gmst_result(experiment):
        path = ROOT / f"data/interim/pangeo_{slug}_{experiment}_annual_gmst_20260917/result.json"
        record = next(r for r in audit["records"] if (r["model"], r["experiment"]) == (args.model, experiment))
        if sha(path) != record["source_result_sha256"]:
            raise ValueError("same-model GMST receipt hash differs")
        return json.loads(path.read_text()), sha(path)
    history, historical_hash = gmst_result("historical")
    future, future_hash = gmst_result("ssp585")
    if (history["source"]["member_id"] != future["source"]["member_id"]
            or history["source"]["source_id"] != args.model
            or future["source"]["source_id"] != args.model):
        raise ValueError("GMST model/member identity differs")
    base_gmst = math.fsum(r["gmst_value_k"] for r in history["annual"]) / 30
    x_by_year = {r["year"]: r["gmst_value_k"] - base_gmst for r in future["annual"]}
    years_train = list(range(2015, 2081))
    x = [x_by_year[year] for year in years_train]

    mp = ROOT / "data/interim/pangeo_monthly_store_metadata_20260908/result.json"
    cp = ROOT / "data/interim/pangeo_monthly_coordinates_units_20260908/result.json"
    inv, coords = json.loads(mp.read_text()), json.loads(cp.read_text())
    if coords["metadata_inventory_sha256"] != sha(mp):
        raise ValueError("monthly source coordinate binding differs")
    selector = lambda r: (r["source"]["source_id"], r["source"]["experiment_id"], r["source"]["variable_id"]) == (args.model, "ssp585", "pr")
    rows, axes = [r for r in inv["records"] if selector(r)], [r for r in coords["records"] if selector(r)]
    if len(rows) != 1 or len(axes) != 1:
        raise ValueError("one exact SSP585 precipitation source required")
    row, axis = rows[0], axes[0]
    if row["source"]["member_id"] != future["source"]["member_id"]:
        raise ValueError("rainfall and GMST realizations differ")
    meta_path = ROOT / row["metadata_file"]
    if sha(meta_path) != row["metadata_sha256"]:
        raise ValueError("precipitation metadata changed")
    meta = json.loads(meta_path.read_text())["metadata"]
    coordinates = {}
    for chunk in axis["chunks"]:
        path = ROOT / chunk["file"]
        if sha(path) != chunk["sha256"]:
            raise ValueError("precipitation coordinate chunk changed")
        name = chunk["variable"]
        spec = meta[name + "/.zarray"]
        coordinates[name] = np.frombuffer(
            numcodecs.get_codec(spec["compressor"]).decode(path.read_bytes()),
            dtype=spec["dtype"]).reshape(spec["shape"])
    ta = row["time_attributes"]
    dates = cftime.num2date(coordinates["time"], ta["units"], calendar=ta["calendar"])
    bound_name = ta["bounds"]
    bound_attrs = meta[bound_name + "/.zattrs"]
    bounds = cftime.num2date(coordinates[bound_name], bound_attrs.get("units", ta["units"]), calendar=ta["calendar"])
    seconds = np.array([(hi-lo).total_seconds() for lo, hi in bounds])
    years = np.array([d.year for d in dates]); months = np.array([d.month for d in dates])
    selected = np.flatnonzero((years >= 2015) & (years <= 2080))
    if len(selected) != 66 * 12 or not np.isfinite(seconds[selected]).all():
        raise ValueError("training source months incomplete")

    matrix_path = ROOT / "data/interim/pangeo_monthly_reduction_matrix_20260908/result.json"
    matrix = json.loads(matrix_path.read_text())
    hrow, = [r for r in matrix["records"] if (r["source"]["source_id"], r["source"]["experiment_id"], r["source"]["variable_id"]) == (args.model, "historical", "pr")]
    hpath = ROOT / hrow["directory"] / "native_monthly_climatologies.npz"
    hreceipt = json.loads((ROOT / hrow["directory"] / "result.json").read_text())
    if sha(hpath) != hreceipt["output_sha256"] or sha(ROOT / hrow["directory"] / "result.json") != hrow["result_sha256"]:
        raise ValueError("historical precipitation climatology binding differs")
    with np.load(hpath, allow_pickle=False) as saved:
        historical_flux = saved["monthly_mean"][0].copy()
        historical_mm = saved["monthly_total_mm"][0].copy()
        if (not np.allclose(saved["lat"], coordinates["lat"], atol=1e-10, rtol=0)
                or not np.allclose(saved["lon"], coordinates["lon"], atol=1e-10, rtol=0)):
            raise ValueError("scenario and historical precipitation grids differ")
    annual_historical = historical_mm.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        historical_month_share = np.divide(historical_mm, annual_historical,
                                           out=np.zeros_like(historical_mm), where=annual_historical > 0)
    if (not np.isfinite(historical_month_share).all() or (historical_month_share < 0).any()
            or np.max(np.abs(historical_month_share.sum(axis=0)[annual_historical > 0] - 1)) > 1e-12):
        raise ValueError("historical monthly water shares invalid")

    shape = tuple(historical_flux.shape[1:]); spec = row["variable_array"]
    size = math.prod(spec["chunks"]) * np.dtype(spec["dtype"]).itemsize
    if (size > 192 * 1024**2 or spec["filters"] is not None or spec["order"] != "C"
            or tuple(spec["chunks"][1:]) != shape or spec["compressor"]["id"] != "blosc"):
        raise ValueError("unsupported precipitation chunk")
    sy = np.zeros((12,) + shape, dtype=np.float64)
    sxy = np.zeros_like(sy)
    sy_annual = np.zeros(shape, dtype=np.float64)
    sxy_annual = np.zeros(shape, dtype=np.float64)
    year_water = np.zeros(shape, dtype=np.float64)
    sentinel = sorted(set((0, math.prod(shape)//4, math.prod(shape)//2,
                           3*math.prod(shape)//4, math.prod(shape)-1)))
    samples = []; annual_samples = []; receipts = []
    current_year, next_month = 2015, 1
    for chunk_number in sorted(set(selected // spec["chunks"][0])):
        key = f"{int(chunk_number)}.0.0"
        url = row["metadata_url"].removesuffix(".zmetadata") + "pr/" + key
        content, receipt = fetch(url, min(size + 1024**2, 112 * 1024**2))
        nbytes, cbytes, _ = _cbuffer_sizes(content)
        if nbytes != size or cbytes != len(content):
            raise ValueError("precipitation compressed source header differs")
        decoded = numcodecs.get_codec(spec["compressor"]).decode(content)
        del content
        data = np.frombuffer(decoded, dtype=spec["dtype"]).reshape(spec["chunks"])
        for index in selected[selected // spec["chunks"][0] == chunk_number]:
            year, month = int(years[index]), int(months[index])
            if (year, month) != (current_year, next_month):
                raise ValueError("training source month order differs")
            plane = data[index % spec["chunks"][0]]
            if (not np.isfinite(plane).all() or np.any(plane == spec["fill_value"])
                    or np.any(plane < 0)):
                raise ValueError("training precipitation invalid or negative")
            year_x = x_by_year[year]
            sy[month-1] += plane
            sxy[month-1] += plane * year_x
            year_water += plane * seconds[index]
            samples.append(dict(year=year, month=month, x=year_x,
                                values=plane.ravel()[sentinel].tolist()))
            if month == 12:
                sy_annual += year_water
                sxy_annual += year_water * year_x
                annual_samples.append(dict(year=year, x=year_x,
                                           values=year_water.ravel()[sentinel].tolist()))
                year_water.fill(0)
                current_year += 1; next_month = 1
            else:
                next_month += 1
        receipts.append(receipt)
        del data, decoded
        print("monthly rain fit source chunk verified", key, flush=True)
    if (current_year, next_month) != (2081, 1) or len(annual_samples) != 66:
        raise ValueError("training annual water accumulation incomplete")
    monthly_intercept, monthly_slope = ols_from_sums(sy, sxy, x, 66, np)
    quantity_intercept, quantity_slope = ols_from_sums(sy_annual, sxy_annual, x, 66, np)

    # A separate scalar math.fsum calculation checks all twelve fitted
    # calendar-month slopes at five fixed source-grid positions.
    max_scalar_error = 0.0; scalar_checks = 0
    sx = math.fsum(x); sxx = math.fsum(v*v for v in x)-sx*sx/66
    for month in range(1, 13):
        rows = [r for r in samples if r["month"] == month]
        if len(rows) != 66:
            raise ValueError("scalar source month count differs")
        for j, site in enumerate(sentinel):
            ysum = math.fsum(r["values"][j] for r in rows)
            xysum = math.fsum(r["x"]*r["values"][j] for r in rows)
            ref_slope = (xysum - sx*ysum/66)/sxx
            ref_intercept = (ysum-ref_slope*sx)/66
            for ref, got in ((ref_slope, monthly_slope[month-1].ravel()[site]),
                             (ref_intercept, monthly_intercept[month-1].ravel()[site])):
                error = abs(ref-got)/max(1.0, abs(ref))
                max_scalar_error = max(max_scalar_error, error); scalar_checks += 1
    for j, site in enumerate(sentinel):
        ysum = math.fsum(r["values"][j] for r in annual_samples)
        xysum = math.fsum(r["x"]*r["values"][j] for r in annual_samples)
        ref_slope = (xysum-sx*ysum/66)/sxx
        ref_intercept = (ysum-ref_slope*sx)/66
        for ref, got in ((ref_slope, quantity_slope.ravel()[site]),
                         (ref_intercept, quantity_intercept.ravel()[site])):
            error = abs(ref-got)/max(1.0, abs(ref))
            max_scalar_error = max(max_scalar_error, error); scalar_checks += 1
    if scalar_checks != 130 or max_scalar_error > 1e-10:
        raise ValueError("independent scalar OLS check failed")

    args.out_dir.mkdir(parents=True)
    output = args.out_dir / "monthly_pattern_coefficients.npz"
    np.savez_compressed(output, monthly_intercept_flux=monthly_intercept,
                        monthly_slope_flux_per_k=monthly_slope,
                        annual_quantity_intercept_mm=quantity_intercept,
                        annual_quantity_slope_mm_per_k=quantity_slope,
                        historical_monthly_flux=historical_flux,
                        historical_month_share=historical_month_share,
                        latitude=coordinates["lat"], longitude=coordinates["lon"])
    result = dict(status="published_style_monthly_pattern_fit_not_validated",
                  method="PEEPS-style per-ESM/per-calendar-month linear precipitation-on-annual-GMST fit",
                  source=row["source"], license=row["license"], years=[2015, 2080],
                  historical_gmst_reference_k=base_gmst, training_gmst_range_k=[min(x), max(x)],
                  training_gmst_centered_sxx=sxx, calendar=ta["calendar"],
                  baseline_monthly_source_sha256=sha(hpath),
                  gmst_historical_result_sha256=historical_hash,
                  gmst_future_result_sha256=future_hash, gmst_audit_sha256=sha(audit_path),
                  source_chunks=receipts, sentinel_flat_indices=sentinel,
                  sentinel_monthly_series=samples, sentinel_annual_series=annual_samples,
                  scalar_checks=scalar_checks, max_scaled_scalar_error=max_scalar_error,
                  coefficients_sha256=sha(output), source_metadata_sha256=sha(meta_path),
                  coordinate_receipt_sha256=sha(cp), code_sha256=sha(Path(__file__)),
                  limitation="Raw-CMIP6 statistical climate fit only; scenario/time holdouts, crop-calendar metrics, daily timing, crop response, damage and SCC remain unvalidated.")
    (args.out_dir / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    print(result["status"], args.model, scalar_checks, max_scalar_error, output.stat().st_size, flush=True)


if __name__ == "__main__":
    main()
