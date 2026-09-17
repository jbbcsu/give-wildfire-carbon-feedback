"""Independent saved-sentinel audit of two PEEPS-style climate-only fits."""
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar_fit(rows, value_index):
    with localcontext() as ctx:
        ctx.prec = 50
        n = Decimal(len(rows))
        x = [Decimal(str(r["x"])) for r in rows]
        y = [Decimal(str(r["values"][value_index])) for r in rows]
        sx, sy = sum(x), sum(y)
        sxx = sum(v*v for v in x) - sx*sx/n
        if sxx <= 0:
            raise ValueError("scalar GMST variation absent")
        slope = (sum(a*b for a, b in zip(x, y))-sx*sy/n)/sxx
        intercept = (sy-slope*sx)/n
        return float(intercept), float(slope)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh audit output required")
    records = []
    checks = 0
    maximum = 0.0
    for model in ("GFDL-ESM4", "IPSL-CM6A-LR"):
        slug = model.lower().replace("-", "_")
        directory = ROOT / f"data/interim/pangeo_{slug}_ssp585_monthly_pattern_fit_20260917"
        path = directory / "result.json"
        result = json.loads(path.read_text())
        array_path = directory / "monthly_pattern_coefficients.npz"
        if (result["status"] != "published_style_monthly_pattern_fit_not_validated"
                or result["source"]["source_id"] != model
                or result["source"]["experiment_id"] != "ssp585"
                or result["years"] != [2015, 2080]
                or sha(array_path) != result["coefficients_sha256"]
                or any(not c["server_md5_verified"] for c in result["source_chunks"])):
            raise ValueError("climate fit source/hash gate differs")
        with np.load(array_path, allow_pickle=False) as saved:
            alpha = saved["monthly_intercept_flux"]
            beta = saved["monthly_slope_flux_per_k"]
            a_quantity = saved["annual_quantity_intercept_mm"]
            b_quantity = saved["annual_quantity_slope_mm_per_k"]
            shares = saved["historical_month_share"]
            if alpha.shape != (12,) + a_quantity.shape or beta.shape != alpha.shape:
                raise ValueError("coefficient shapes differ")
            if not np.isfinite(alpha).all() or not np.isfinite(beta).all():
                raise ValueError("nonfinite coefficients")
            if not np.isfinite(shares).all() or (shares < 0).any():
                raise ValueError("invalid historical quantity shares")
            positions = result["sentinel_flat_indices"]
            if len(positions) != 5 or len(result["sentinel_monthly_series"]) != 792 or len(result["sentinel_annual_series"]) != 66:
                raise ValueError("saved fit sentinel support differs")
            error_here = 0.0
            for month in range(1, 13):
                rows = [r for r in result["sentinel_monthly_series"] if r["month"] == month]
                if len(rows) != 66 or [r["year"] for r in rows] != list(range(2015, 2081)):
                    raise ValueError("month sentinel year order differs")
                for j, position in enumerate(positions):
                    intercept, slope = scalar_fit(rows, j)
                    for got, expected in ((alpha[month-1].ravel()[position], intercept),
                                          (beta[month-1].ravel()[position], slope)):
                        error_here = max(error_here, abs(float(got)-expected)/max(1.0, abs(expected)))
                        checks += 1
            rows = result["sentinel_annual_series"]
            if [r["year"] for r in rows] != list(range(2015, 2081)):
                raise ValueError("annual sentinel year order differs")
            for j, position in enumerate(positions):
                intercept, slope = scalar_fit(rows, j)
                for got, expected in ((a_quantity.ravel()[position], intercept),
                                      (b_quantity.ravel()[position], slope)):
                    error_here = max(error_here, abs(float(got)-expected)/max(1.0, abs(expected)))
                    checks += 1
        if error_here > 1e-10:
            raise ValueError(f"independent high-precision scalar fit differs: {model}")
        maximum = max(maximum, error_here)
        records.append(dict(model=model, fit_result_sha256=sha(path), coefficient_sha256=sha(array_path),
                            independent_scalar_checks=130, max_scaled_error=error_here))
    if checks != 260:
        raise ValueError("independent fit check count differs")
    args.out_dir.mkdir(parents=True)
    output = dict(status="two_monthly_climate_fits_independently_audited_not_holdout_validated",
                  independent_scalar_checks=checks, maximum_scaled_error=maximum, records=records,
                  limitation="Checks source bindings and fitted scalar algebra only; held-out precipitation skill, crop impacts and SCC remain open.")
    (args.out_dir / "result.json").write_text(json.dumps(output, indent=2))
    print(output["status"], checks, maximum)


if __name__ == "__main__":
    main()
