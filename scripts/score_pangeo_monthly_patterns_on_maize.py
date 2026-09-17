"""Crop-calendar check of frozen monthly GMT-rain benchmarks on maize area."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from climate_grid_transfer import stencil, interpolate
from ggcmi_calendar import CONVENTIONS, month_terms
from monthly_rainfall_pattern import season_bins, pattern_metrics

PREDICTORS = ("unchanged", "quantity_only", "monthly_pattern")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantity_mean_flux(qa, qb, shares, gmst_monthly, gmst_annual, years, origin):
    """Mean of year-specific quantity/month-duration fluxes, not ratio of means."""
    seconds = {(r["year"], r["month"]): r["seconds"] for r in gmst_monthly}
    g = {r["year"]: r["gmst_value_k"]-origin for r in gmst_annual}
    if len(years) != 30 or any(y not in g for y in years):
        raise ValueError("predecessor/current GMST window incomplete")
    fields = np.empty((12,) + qa.shape, dtype=np.float64)
    for month in range(1, 13):
        field = np.zeros_like(qa)
        for year in years:
            duration = seconds.get((year, month))
            if duration is None or duration <= 0:
                raise ValueError("month duration missing from same-model GMST receipt")
            field += (qa+qb*g[year])*shares[month-1]/duration
        fields[month-1] = field/30
    return fields


def summary(table, full_area):
    """Area-weighted common-support crop-season scores from a saved cell ledger."""
    eligible = table[table.category == "valid_actual_calendar_climate"]
    common = eligible[eligible.common_physical_support]
    den = math.fsum(eligible.area_ha)
    common_den = math.fsum(common.area_ha)
    if den <= 0 or common_den <= 0:
        raise ValueError("no crop-calendar amount or common-share support")
    models = {}
    for name in PREDICTORS:
        delta = eligible[f"{name}_season_mm"]-eligible.actual_season_mm
        models[name] = dict(
            season_amount_rmse_mm=math.sqrt(math.fsum(eligible.area_ha*delta*delta)/den),
            season_amount_bias_mm=math.fsum(eligible.area_ha*delta)/den,
            common_area_month_share_tv=math.fsum(common.area_ha*common[f"{name}_share_tv"])/common_den,
            common_area_absolute_centroid_error_days=math.fsum(common.area_ha*abs(common[f"{name}_centroid_error_days"]))/common_den,
            negative_crop_cell_months=int(eligible[f"{name}_negative_months"].sum()),
            crop_cells_with_negative_month=int((eligible[f"{name}_negative_months"] > 0).sum()))
    return dict(full_mapped_area_ha=full_area, valid_actual_area_ha=den,
                common_physical_area_ha=common_den, valid_actual_area_fraction=den/full_area,
                common_of_valid_area_fraction=common_den/den, valid_actual_cells=len(eligible),
                common_physical_cells=len(common), models=models)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=("GFDL-ESM4", "IPSL-CM6A-LR"), required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh crop-calendar benchmark output required")
    slug = args.model.lower().replace("-", "_")
    fit_audit_path = ROOT / "data/interim/pangeo_monthly_pattern_fit_validation_20260917/result.json"
    hold_audit_path = ROOT / "data/interim/pangeo_monthly_pattern_holdouts_independent_20260917/result.json"
    fit_audit = json.loads(fit_audit_path.read_text())
    hold_audit = json.loads(hold_audit_path.read_text())
    if (fit_audit["status"] != "two_monthly_climate_fits_independently_audited_not_holdout_validated"
            or hold_audit["status"] != "four_raw_cmip6_monthly_holdouts_independently_aggregated"):
        raise ValueError("independent climate fit/holdout audit absent")
    fit_rec, = [r for r in fit_audit["records"] if r["model"] == args.model]
    hold_rec, = [r for r in hold_audit["records"] if (r["model"], r["holdout"]) == (args.model, "ssp126")]
    fit_dir = ROOT / f"data/interim/pangeo_{slug}_ssp585_monthly_pattern_fit_20260917"
    fit_path = fit_dir / "result.json"
    fit = json.loads(fit_path.read_text())
    coef_path = fit_dir / "monthly_pattern_coefficients.npz"
    if sha(fit_path) != fit_rec["fit_result_sha256"] or sha(coef_path) != fit_rec["coefficient_sha256"]:
        raise ValueError("frozen fit binding differs")
    hold_path = ROOT / f"data/interim/pangeo_{slug}_ssp126_monthly_pattern_holdout_20260917/result.json"
    if sha(hold_path) != hold_rec["result_sha256"]:
        raise ValueError("whole-scenario holdout binding differs")
    with np.load(coef_path, allow_pickle=False) as saved:
        alpha = saved["monthly_intercept_flux"]
        beta = saved["monthly_slope_flux_per_k"]
        qa = saved["annual_quantity_intercept_mm"]
        qb = saved["annual_quantity_slope_mm_per_k"]
        shares = saved["historical_month_share"]
        historical = saved["historical_monthly_flux"]
        latitude, longitude = saved["latitude"], saved["longitude"]

    matrix_path = ROOT / "data/interim/pangeo_monthly_reduction_matrix_20260908/result.json"
    matrix = json.loads(matrix_path.read_text())
    rec, = [r for r in matrix["records"] if (r["source"]["source_id"], r["source"]["experiment_id"], r["source"]["variable_id"]) == (args.model, "ssp126", "pr")]
    dir_climate = ROOT / rec["directory"]
    climate_receipt = json.loads((dir_climate / "result.json").read_text())
    climate_path = dir_climate / "native_monthly_climatologies.npz"
    if (sha(dir_climate / "result.json") != rec["result_sha256"]
            or sha(climate_path) != climate_receipt["output_sha256"]
            or rec["source"]["member_id"] != fit["source"]["member_id"]):
        raise ValueError("whole-scenario climatology source binding differs")
    with np.load(climate_path, allow_pickle=False) as saved:
        if (not np.allclose(saved["lat"], latitude, atol=1e-10, rtol=0)
                or not np.allclose(saved["lon"], longitude, atol=1e-10, rtol=0)):
            raise ValueError("climate/fit grid differs")
        actual = saved["monthly_mean"].copy()
    gmst_path = ROOT / f"data/interim/pangeo_{slug}_ssp126_annual_gmst_20260917/result.json"
    gmst = json.loads(gmst_path.read_text())
    origin = fit["historical_gmst_reference_k"]
    annual_by_year = {r["year"]: r["gmst_value_k"] for r in gmst["annual"]}
    fields = {name: np.empty_like(actual, dtype=np.float64) for name in PREDICTORS}
    mean_gmst = []
    for shift, years in enumerate((range(2031, 2061), range(2030, 2060))):
        x = math.fsum(annual_by_year[y]-origin for y in years)/30
        mean_gmst.append(x)
        fields["unchanged"][shift] = historical
        fields["monthly_pattern"][shift] = alpha+beta*x
        fields["quantity_only"][shift] = quantity_mean_flux(qa, qb, shares, gmst["monthly"], gmst["annual"], list(years), origin)

    area_path = ROOT / "data/interim/ggcmi_crop_area_gridaligned_20260908/area_support.parquet"
    if sha(area_path) != "6d38d074734a69c27af298cb3c33bb88baa6ffe00f50509f96030da41e2cf284":
        raise ValueError("fixed MIRCA-2000 maize area source differs")
    area = pq.read_table(area_path, filters=[("year", "=", 2000)],
                         columns=["latitude", "longitude", "regime", "area_ha"]).to_pandas()
    area = area[area.regime == "rainfed"].reset_index(drop=True)
    if len(area) != 30821 or (area.area_ha <= 0).any() or not np.isfinite(area.area_ha).all():
        raise ValueError("fixed rainfed maize area support differs")
    calendar_receipt_path = ROOT / "data/interim/maize_calendar_point_alignment_20260908/result.json"
    if sha(calendar_receipt_path) != "b80c1dbf17895f19958dc4e55150a3030875f8741d83677b643c3ec1b59627c7":
        raise ValueError("maize calendar receipt differs")
    source, = [s for s in json.loads(calendar_receipt_path.read_text())["sources"]
               if s["phase"] == "phase2" and "Maize_rf_" in s["path"]]
    calendar_path = ROOT / source["path"]
    if sha(calendar_path) != source["hash"]:
        raise ValueError("source maize crop calendar differs")
    with h5py.File(calendar_path, "r") as data:
        clat, clon = data["lat"][:], data["lon"][:]
        i = np.searchsorted(clat, area.latitude.to_numpy())
        j = np.searchsorted(clon, area.longitude.to_numpy())
        if not np.array_equal(clat[i], area.latitude) or not np.array_equal(clon[j], area.longitude):
            raise ValueError("maize calendar/area grid differs")
        planting, harvest = data["planting day"][:][i, j], data["harvest day"][:][i, j]
    mapping = stencil(latitude, longitude, area.latitude.to_numpy(), area.longitude.to_numpy())
    crop_flux = {"actual": interpolate(actual, mapping)}
    crop_flux.update({name: interpolate(fields[name], mapping) for name in PREDICTORS})
    if not np.isfinite(crop_flux["actual"]).all():
        raise ValueError("actual crop-grid monthly climate missing")

    args.out_dir.mkdir(parents=True)
    records, summaries = [], []
    full_area = math.fsum(area.area_ha)
    for convention in CONVENTIONS:
        cells = []
        for k, site in enumerate(area.itertuples(index=False)):
            cell = dict(latitude=float(site.latitude), longitude=float(site.longitude),
                        area_ha=float(site.area_ha), category="valid_actual_calendar_climate",
                        common_physical_support=False)
            try:
                order, days, mid = season_bins(float(planting[k]), float(harvest[k]))
                terms = month_terms(float(planting[k]), float(harvest[k]), year=2000, convention=convention)
            except ValueError:
                cell["category"] = "invalid_source_calendar"
                cells.append(cell)
                continue
            shifts = {month: int(year == 1999) for year, month, _ in terms}
            observed = np.array([crop_flux["actual"][shifts[m], m-1, k] for m in order])
            if not np.isfinite(observed).all() or (observed < 0).any():
                cell["category"] = "invalid_actual_climate"
                cells.append(cell)
                continue
            actual_mm = float(math.fsum(observed*days*86400))
            if actual_mm <= 0:
                cell["category"] = "zero_actual_season"
                cells.append(cell)
                continue
            cell["actual_season_mm"] = actual_mm
            all_physical = True
            predicted = {}
            for name in PREDICTORS:
                values = np.array([crop_flux[name][shifts[m], m-1, k] for m in order])
                if not np.isfinite(values).all():
                    raise ValueError("nonfinite crop-calendar model prediction")
                predicted[name] = values
                cell[f"{name}_season_mm"] = float(math.fsum(values*days*86400))
                cell[f"{name}_negative_months"] = int(np.count_nonzero(values < 0))
                all_physical &= bool((values >= 0).all() and cell[f"{name}_season_mm"] > 0)
            if all_physical:
                cell["common_physical_support"] = True
                for name in PREDICTORS:
                    metrics = pattern_metrics(observed, predicted[name], days, mid)
                    cell[f"{name}_share_tv"] = metrics["month_share_total_variation"]
                    cell[f"{name}_centroid_error_days"] = metrics["centroid_shift_days"]
            cells.append(cell)
        table = pd.DataFrame(cells)
        score = summary(table, full_area)
        path = args.out_dir / f"{slug}_{convention}_maize_rainfed.parquet"
        pq.write_table(pa.Table.from_pandas(table, preserve_index=False), path, compression="zstd")
        records.append(dict(path=str(path.resolve().relative_to(ROOT)), sha256=sha(path), convention=convention))
        summaries.append(dict(convention=convention, **score))
        print(args.model, convention, score["valid_actual_cells"],
              score["common_physical_cells"], flush=True)
    result = dict(status="monthly_gmt_patterns_crop_calendar_climatology_scored_not_yield_validated",
                  model=args.model, source=rec["source"], license=climate_receipt["license"],
                  target_crop="rainfed_maize", period=[2031, 2060], predecessor_period=[2030, 2059],
                  mean_gmst_anomaly_k=mean_gmst,
                  fit_result_sha256=sha(fit_path), climate_result_sha256=sha(dir_climate / "result.json"),
                  gmst_result_sha256=sha(gmst_path), area_source_sha256=sha(area_path),
                  calendar_receipt_sha256=sha(calendar_receipt_path),
                  source_calendar_sha256=sha(calendar_path),
                  fit_audit_sha256=sha(fit_audit_path), holdout_audit_sha256=sha(hold_audit_path),
                  records=records, summaries=summaries, code_sha256=sha(Path(__file__)),
                  limitation="Raw-CMIP6 30-year monthly-climatology maize-calendar climate scores only; not annual/daily sequence validation, yields, damages or SCC.")
    (args.out_dir / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
