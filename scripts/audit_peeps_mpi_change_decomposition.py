#!/usr/bin/env python3
"""Independently check saved monthly-change scores using scalar math.fsum."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/peeps_mpi_source_reconstruction_20260917/source_vs_published_crop_center_mm.npz"
INPUT_SHA = "f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def assert_close(actual, expected, name):
    if not math.isclose(float(actual), float(expected), rel_tol=2e-11, abs_tol=2e-8):
        raise AssertionError(f"{name}: saved={actual}, independently recomputed={expected}")


def audit(saved, arrays):
    weights = arrays["hectares"]
    old = arrays["direct_ensemble_mean_mm_2015"]
    new = arrays["direct_ensemble_mean_mm_2100"]
    pub_old = arrays["published_mm_2015"]
    pub_new = arrays["published_mm_2100"]
    n = len(weights)
    if n != 30821 or any(x.shape != (12, n) for x in (old, new, pub_old, pub_new)):
        raise ValueError("source support changed")
    total_weight = math.fsum(float(x) for x in weights)
    checks = 0

    def check(actual, expected, name):
        nonlocal checks
        assert_close(actual, expected, name)
        checks += 1

    check(saved["center_count"], n, "center_count")
    check(saved["area_ha"], total_weight, "area_ha")
    direct_annual = [math.fsum(float(new[m, i] - old[m, i]) for m in range(12)) for i in range(n)]
    pub_annual = [math.fsum(float(pub_new[m, i] - pub_old[m, i]) for m in range(12)) for i in range(n)]
    error = [p - d for p, d in zip(pub_annual, direct_annual)]

    def mean(iterator):
        return math.fsum(iterator) / total_weight

    annual = saved["annual"]
    check(annual["direct_mean_change_mm"], mean(float(weights[i])*direct_annual[i] for i in range(n)), "annual_direct")
    check(annual["published_mean_change_mm"], mean(float(weights[i])*pub_annual[i] for i in range(n)), "annual_published")
    check(annual["published_minus_direct_mean_change_mm"], mean(float(weights[i])*error[i] for i in range(n)), "annual_bias")
    check(annual["spatial_change_rmse_mm"], math.sqrt(mean(float(weights[i])*error[i]**2 for i in range(n))), "annual_rmse")
    check(annual["spatial_change_mae_mm"], mean(float(weights[i])*abs(error[i]) for i in range(n)), "annual_mae")
    agreement = mean(float(weights[i]) * ((direct_annual[i] > 0) == (pub_annual[i] > 0)
                                       and (direct_annual[i] < 0) == (pub_annual[i] < 0)) for i in range(n))
    check(annual["sign_agreement_area_fraction"], agreement, "annual_sign_agreement")

    monthly_mean_squared = []
    centered_mean_squared = []
    if len(saved["monthly"]) != 12:
        raise ValueError("missing monthly scores")
    for month in range(12):
        direct = [float(new[month, i] - old[month, i]) for i in range(n)]
        published = [float(pub_new[month, i] - pub_old[month, i]) for i in range(n)]
        difference = [p - d for p, d in zip(published, direct)]
        row = saved["monthly"][month]
        check(row["month"], month + 1, f"month_{month+1}_id")
        check(row["direct_mean_change_mm"], mean(float(weights[i])*direct[i] for i in range(n)), f"month_{month+1}_direct")
        check(row["published_mean_change_mm"], mean(float(weights[i])*published[i] for i in range(n)), f"month_{month+1}_published")
        check(row["published_minus_direct_mean_change_mm"], mean(float(weights[i])*difference[i] for i in range(n)), f"month_{month+1}_bias")
        mse = mean(float(weights[i])*difference[i]**2 for i in range(n))
        check(row["spatial_change_rmse_mm"], math.sqrt(mse), f"month_{month+1}_rmse")
        monthly_mean_squared.append(mse)
        centered_mean_squared.append(mean(float(weights[i])*(difference[i] - error[i]/12)**2 for i in range(n)))
    overall = math.fsum(monthly_mean_squared)/12
    amount = mean(float(weights[i])*(error[i]/12)**2 for i in range(n))
    redistribution = math.fsum(centered_mean_squared)/12
    decomposition = saved["decomposition"]
    check(decomposition["overall_monthly_change_rmse_mm"], math.sqrt(overall), "overall_monthly_rmse")
    check(decomposition["annual_amount_component_rmse_per_month_mm"], math.sqrt(amount), "annual_amount_component")
    check(decomposition["within_year_redistribution_component_rmse_mm"], math.sqrt(redistribution), "redistribution_component")
    check(decomposition["squared_identity_residual_mm2"], overall-amount-redistribution, "decomposition_residual")
    if not math.isclose(overall, amount+redistribution, rel_tol=2e-11, abs_tol=2e-8):
        raise AssertionError("independent orthogonal decomposition failed")
    return {"status": "independent_scalar_change_arithmetic_passed", "numeric_checks": checks,
            "source_arrays_sha256": INPUT_SHA, "result_sha256": saved["result_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = args.result.resolve()
    output = args.out.resolve()
    if not result.is_relative_to(ROOT / "data/interim") or not output.is_relative_to(ROOT / "data/interim") or output.exists():
        parser.error("ignored project inputs and fresh output required")
    if digest(SOURCE) != INPUT_SHA:
        raise ValueError("frozen source arrays changed")
    saved = json.loads(result.read_text())
    if saved["input_array_sha256"] != INPUT_SHA or saved["status"] != "same_source_in_sample_rainfall_change_decomposition_not_yield_damage_scc":
        raise ValueError("wrong score input or status")
    saved["result_sha256"] = digest(result)
    with np.load(SOURCE, allow_pickle=False) as archive:
        verified = audit(saved, archive)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(verified, indent=2) + "\n")
    print(json.dumps(verified))


if __name__ == "__main__":
    main()
