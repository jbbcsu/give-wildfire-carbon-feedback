#!/usr/bin/env python3
"""Score source-matched published versus direct 2015--2100 monthly changes.

This is an in-sample climate-input diagnostic, never a rainfall forcing or SCC.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


ARRAY_SHA = "f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d"
REPORT_SHA = "f5aeaef121ef712522f6ad4ada66acab4f060e5d60e57bdaf5b479c33b7727fa"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/peeps_mpi_source_reconstruction_20260917"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def weighted(values, weights):
    return float(np.sum(values * weights) / np.sum(weights))


def compute(direct_2015, direct_2100, published_2015, published_2100, weights):
    arrays = (direct_2015, direct_2100, published_2015, published_2100)
    if (weights.ndim != 1 or len(weights) == 0
            or any(a.shape != (12, len(weights)) for a in arrays)
            or not all(np.isfinite(a).all() for a in (*arrays, weights))
            or not np.all(weights > 0)
            or not np.all(direct_2015 >= 0) or not np.all(direct_2100 >= 0)):
        raise ValueError("invalid source geometry or physical direct rainfall")
    direct = direct_2100 - direct_2015
    published = published_2100 - published_2015
    direct_annual = direct.sum(axis=0)
    published_annual = published.sum(axis=0)
    annual_error = published_annual - direct_annual
    monthly_error = published - direct
    redistribution_error = monthly_error - annual_error[None, :] / 12
    mean_monthly_squared_error = weighted(np.mean(monthly_error**2, axis=0), weights)
    annual_level_squared = weighted((annual_error / 12)**2, weights)
    redistribution_squared = weighted(np.mean(redistribution_error**2, axis=0), weights)
    if not np.isclose(mean_monthly_squared_error, annual_level_squared + redistribution_squared,
                      rtol=1e-10, atol=1e-9):
        raise ValueError("monthly-change error decomposition failed")
    result = {
        "center_count": len(weights),
        "area_ha": float(np.sum(weights)),
        "annual": {
            "direct_mean_change_mm": weighted(direct_annual, weights),
            "published_mean_change_mm": weighted(published_annual, weights),
            "published_minus_direct_mean_change_mm": weighted(annual_error, weights),
            "spatial_change_rmse_mm": weighted(annual_error**2, weights)**0.5,
            "spatial_change_mae_mm": weighted(np.abs(annual_error), weights),
            "sign_agreement_area_fraction": weighted(np.sign(direct_annual) == np.sign(published_annual), weights),
        },
        "monthly": [{
            "month": month + 1,
            "direct_mean_change_mm": weighted(direct[month], weights),
            "published_mean_change_mm": weighted(published[month], weights),
            "published_minus_direct_mean_change_mm": weighted(monthly_error[month], weights),
            "spatial_change_rmse_mm": weighted(monthly_error[month]**2, weights)**0.5,
        } for month in range(12)],
        "decomposition": {
            "overall_monthly_change_rmse_mm": mean_monthly_squared_error**0.5,
            "annual_amount_component_rmse_per_month_mm": annual_level_squared**0.5,
            "within_year_redistribution_component_rmse_mm": redistribution_squared**0.5,
            "squared_identity_residual_mm2": mean_monthly_squared_error - annual_level_squared - redistribution_squared,
        },
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    if (not output.is_relative_to(ROOT / "data/interim") or output.exists()
            or shutil.disk_usage(ROOT).free < 130 * 2**30):
        parser.error("fresh ignored project output and disk reserve required")
    array_path = SOURCE / "source_vs_published_crop_center_mm.npz"
    report_path = SOURCE / "result.json"
    if digest(array_path) != ARRAY_SHA or digest(report_path) != REPORT_SHA:
        raise ValueError("frozen source-matched inputs changed")
    with np.load(array_path, allow_pickle=False) as archive:
        if set(archive.files) != {"hectares", "ii", "jj", "direct_ensemble_mean_mm_2015",
                                  "direct_ensemble_mean_mm_2100", "published_mm_2015", "published_mm_2100"}:
            raise ValueError("source array schema changed")
        record = compute(*(archive[name] for name in (
            "direct_ensemble_mean_mm_2015", "direct_ensemble_mean_mm_2100",
            "published_mm_2015", "published_mm_2100", "hectares")))
    if record["center_count"] != 30821:
        raise ValueError("crop-center support changed")
    result = {
        "status": "same_source_in_sample_rainfall_change_decomposition_not_yield_damage_scc",
        "protocol": "PEEPS_MPI_CHANGE_DECOMPOSITION_PROTOCOL_20260918.md",
        "input_array_sha256": ARRAY_SHA,
        "input_report_sha256": REPORT_SHA,
        "historical_reconstruction_not_holdout": True,
        "physically_valid_forcing_authorized": False,
        "yield_damage_scc_estimated": False,
        **record,
    }
    output.mkdir(parents=True)
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "annual": record["annual"],
                      "decomposition": record["decomposition"]}))


if __name__ == "__main__":
    main()
