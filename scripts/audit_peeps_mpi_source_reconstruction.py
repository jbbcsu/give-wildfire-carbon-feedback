#!/usr/bin/env python3
"""Independent arithmetic audit of saved PEEPS versus direct-MPI arrays.

This deliberately does not import or call the primary score implementation.
All weighted statistics are reconstructed with Python's math.fsum.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/peeps_mpi_source_reconstruction_20260917"
PINNED_ARRAY_SHA256 = "f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d"
YEARS = (2015, 2100)
MEMBERS = (("r1", "r1i1p1f1"), ("r2", "r2i1p1f1"))


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def weighted(values, weights, total_weight):
    return math.fsum(float(v) * float(w) for v, w in zip(values, weights)) / total_weight


def audit_year(year, direct, published, hectares):
    if direct.shape != published.shape or direct.shape != (12, len(hectares)):
        raise ValueError("saved array dimensions changed")
    total_area = math.fsum(float(w) for w in hectares)
    months = []
    for month in range(12):
        d = [float(x) for x in direct[month]]
        p = [float(x) for x in published[month]]
        err = [b-a for a, b in zip(d, p)]
        months.append({
            "month": month+1,
            "direct_negative_area_percent": 100*math.fsum(float(w) for x, w in zip(d, hectares) if x < 0)/total_area,
            "predicted_negative_area_percent": 100*math.fsum(float(w) for x, w in zip(p, hectares) if x < 0)/total_area,
            "mean_direct_mm": weighted(d, hectares, total_area),
            "mean_predicted_mm": weighted(p, hectares, total_area),
            "mean_bias_mm": weighted(err, hectares, total_area),
            "mae_mm": weighted((abs(x) for x in err), hectares, total_area),
            "rmse_mm": math.sqrt(weighted((x*x for x in err), hectares, total_area)),
        })
    annual_direct = [math.fsum(float(direct[m, i]) for m in range(12)) for i in range(len(hectares))]
    annual_published = [math.fsum(float(published[m, i]) for m in range(12)) for i in range(len(hectares))]
    annual_error = [p-d for d, p in zip(annual_direct, annual_published)]
    direct_bad = [any(float(direct[m, i]) < 0 for m in range(12)) for i in range(len(hectares))]
    published_bad = [any(float(published[m, i]) < 0 for m in range(12)) for i in range(len(hectares))]
    valid = [not direct_bad[i] and not published_bad[i] and annual_direct[i] > 0 and
             annual_published[i] > 0 for i in range(len(hectares))]
    valid_area = math.fsum(float(w) for ok, w in zip(valid, hectares) if ok)
    tv = [0.5*math.fsum(abs(float(direct[m, i])/annual_direct[i] -
                             float(published[m, i])/annual_published[i]) for m in range(12))
          for i, ok in enumerate(valid) if ok]
    valid_weights = [float(w) for ok, w in zip(valid, hectares) if ok]
    valid_errors = [x for ok, x in zip(valid, annual_error) if ok]
    return {
        "year": year, "months": months,
        "direct_any_negative_area_percent": 100*math.fsum(float(w) for bad, w in zip(direct_bad, hectares) if bad)/total_area,
        "predicted_any_negative_area_percent": 100*math.fsum(float(w) for bad, w in zip(published_bad, hectares) if bad)/total_area,
        "all_area_annual_direct_mean_mm": weighted(annual_direct, hectares, total_area),
        "all_area_annual_predicted_mean_mm": weighted(annual_published, hectares, total_area),
        "all_area_annual_bias_mm": weighted(annual_error, hectares, total_area),
        "all_area_annual_rmse_mm": math.sqrt(weighted((x*x for x in annual_error), hectares, total_area)),
        "common_valid_centers": sum(valid),
        "common_valid_area_percent": 100*valid_area/total_area,
        "common_valid_mean_month_share_tv_error": weighted(tv, valid_weights, valid_area),
        "common_valid_annual_rmse_mm": math.sqrt(weighted((x*x for x in valid_errors), valid_weights, valid_area)),
    }


def compare(calculated, reported, path="result", checks=None):
    if checks is None:
        checks = []
    if isinstance(calculated, dict):
        if set(calculated) != set(reported):
            raise ValueError(f"reported field mismatch at {path}")
        for key, value in calculated.items():
            compare(value, reported[key], f"{path}.{key}", checks)
    elif isinstance(calculated, list):
        if len(calculated) != len(reported):
            raise ValueError(f"reported list length mismatch at {path}")
        for i, value in enumerate(calculated):
            compare(value, reported[i], f"{path}[{i}]", checks)
    elif isinstance(calculated, int):
        if calculated != reported:
            raise ValueError(f"integer disagreement at {path}: {calculated} != {reported}")
        checks.append(path)
    else:
        if not math.isclose(calculated, reported, rel_tol=1e-11, abs_tol=1e-8):
            raise ValueError(f"numeric disagreement at {path}: {calculated} != {reported}")
        checks.append(path)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(ROOT / "data/interim") or output.exists():
        raise ValueError("new ignored interim audit result required")
    array_path = SOURCE / "source_vs_published_crop_center_mm.npz"
    report_path = SOURCE / "result.json"
    if sha(array_path) != PINNED_ARRAY_SHA256:
        raise ValueError("frozen source/PEEPS array SHA-256 changed")
    report = json.loads(report_path.read_text())
    if (report["source_vs_published_arrays_sha256"] != PINNED_ARRAY_SHA256 or
        report["status"] != "same_source_in_sample_peeps_monthly_reconstruction_not_holdout_or_scc"):
        raise ValueError("primary report identity changed")
    with np.load(array_path, allow_pickle=False) as data:
        hectares = data["hectares"]
        if (len(hectares) != 30821 or not np.all(np.isfinite(hectares)) or
            not np.all(hectares > 0)):
            raise ValueError("crop-area support changed")
        if not math.isclose(math.fsum(float(w) for w in hectares),
                            report["rainfed_maize_area_ha"], rel_tol=1e-12):
            raise ValueError("crop-area total changed")
        results = []
        year_arrays = {}
        for year in YEARS:
            direct = data[f"direct_ensemble_mean_mm_{year}"]
            published = data[f"published_mm_{year}"]
            if not np.isfinite(direct).all() or not np.isfinite(published).all():
                raise ValueError("nonfinite saved monthly data")
            sources = []
            for short, full in MEMBERS:
                folder = ROOT / f"data/interim/peeps_mpi_direct_{short}_{year}_v3_20260917"
                with np.load(folder / "direct_crop_center_monthly_mm.npz", allow_pickle=False) as raw:
                    if not all(np.array_equal(raw[k], data[k]) for k in ("hectares", "ii", "jj")):
                        raise ValueError("source member crop mapping changed")
                    sources.append(raw[f"{full}_{year}_monthly_mm"].copy())
            if not np.allclose(direct, (sources[0]+sources[1])/2, rtol=0, atol=1e-12):
                raise ValueError("direct two-member mean is not source arithmetic")
            results.append(audit_year(year, direct, published, hectares))
            year_arrays[year] = (direct.copy(), published.copy())
    # The primary scorer defines its physical common support separately by
    # year. This additional, explicitly post-result diagnostic fixes one
    # intersection for comparisons between 2015 and 2100.
    jointly_valid = np.ones(len(hectares), dtype=bool)
    for direct, published in year_arrays.values():
        jointly_valid &= ((direct >= 0).all(axis=0) & (published >= 0).all(axis=0)
                          & (direct.sum(axis=0) > 0) & (published.sum(axis=0) > 0))
    fixed_area = math.fsum(float(w) for w in hectares[jointly_valid])
    fixed = {"centers": int(jointly_valid.sum()),
             "area_percent": 100*fixed_area/math.fsum(float(w) for w in hectares),
             "by_year": []}
    for year in YEARS:
        direct, published = year_arrays[year]
        d = direct[:, jointly_valid]
        p = published[:, jointly_valid]
        weights = hectares[jointly_valid]
        d_total = [math.fsum(float(d[m, i]) for m in range(12)) for i in range(len(weights))]
        p_total = [math.fsum(float(p[m, i]) for m in range(12)) for i in range(len(weights))]
        errors = [b-a for a, b in zip(d_total, p_total)]
        share_tv = [0.5*math.fsum(abs(float(d[m, i])/d_total[i]-
                                      float(p[m, i])/p_total[i]) for m in range(12))
                    for i in range(len(weights))]
        fixed["by_year"].append({"year": year,
            "mean_direct_annual_mm": weighted(d_total, weights, fixed_area),
            "mean_published_annual_mm": weighted(p_total, weights, fixed_area),
            "annual_bias_mm": weighted(errors, weights, fixed_area),
            "annual_rmse_mm": math.sqrt(weighted((x*x for x in errors), weights, fixed_area)),
            "mean_month_share_tv_error": weighted(share_tv, weights, fixed_area)})
    fixed["change_2100_minus_2015_direct_mm"] = (fixed["by_year"][1]["mean_direct_annual_mm"]-
                                                   fixed["by_year"][0]["mean_direct_annual_mm"])
    fixed["change_2100_minus_2015_published_mm"] = (fixed["by_year"][1]["mean_published_annual_mm"]-
                                                      fixed["by_year"][0]["mean_published_annual_mm"])
    checks = []
    for result, reported in zip(results, report["results"]):
        selected = {key: value for key, value in reported.items() if key != "author_absolute_gmst_K"}
        compare(result, selected, f"year_{result['year']}", checks)
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "passed_independent_saved_array_arithmetic_not_source_redecode",
               "source_arrays_sha256": PINNED_ARRAY_SHA256,
               "primary_report_sha256": sha(report_path),
               "metric_checks": len(checks),
               "years": list(YEARS),
               "post_result_fixed_two_year_support": fixed,
               "results": [{key: value for key, value in result.items() if key != "months"}
                           for result in results],
               "publication_or_scc_promotion": False}
    output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "metric_checks": len(checks),
                      "output": str(output)}))


if __name__ == "__main__":
    main()
