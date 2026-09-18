#!/usr/bin/env python3
"""Reconstruct 20-year source, published formula, and score arithmetic."""
import argparse
import calendar
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import xarray as xr

from audit_peeps_mpi_change_decomposition import audit as audit_change


ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "data/interim/peeps_author_mpi_ssp585_monthly_20260917/selected_months_receipt.json"
GMST = ROOT / "data/interim/peeps_published_mpi_ssp585_tgav_20260917/selected_member_receipt.json"
AUTHOR_SHA = "fafe91fafb0f64b1448501bb49b623e21ad86e3c882a6b65b5fb337d8b6fa753"
GMST_SHA = "cd632ffb21d171c48787f5d4766a2ae29f22d657db56a074738a7dc2c9a2bad3"
PERIODS = {"early": range(2015, 2035), "late": range(2081, 2101)}
CHUNKS = {"r1i1p1f1": (0, 1), "r2i1p1f1": (0, 1, 3, 4)}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(a, b, name, atol=2e-8):
    if not np.allclose(a, b, rtol=2e-11, atol=atol):
        raise AssertionError(name + " differs")


def reconstruct_direct(saved):
    source = {}
    mapping = None
    verified_chunks = 0
    for member, chunks in CHUNKS.items():
        period_sums = {period: None for period in PERIODS}
        period_counts = {period: np.zeros(12, dtype=np.int64) for period in PERIODS}
        for chunk in chunks:
            directory = ROOT / f"data/interim/peeps_mpi_20yr_{member[:2]}_chunk{chunk}_20260918"
            receipt_file = directory / "result.json"
            array_file = directory / "monthly_crop_center_partial.npz"
            receipt = json.loads(receipt_file.read_text())
            identity = next((x for x in saved["source_partials"]
                             if x["member"] == member and x["chunk"] == chunk), None)
            if (identity is None or sha(receipt_file) != identity["receipt_sha256"]
                    or sha(array_file) != identity["partial_sha256"]
                    or receipt["source_compressed_sha256"] != identity["source_compressed_sha256"]
                    or receipt["partial_array_sha256"] != identity["partial_sha256"]
                    or not receipt["gcs_crc32c_verified"] or not receipt["gcs_md5_verified"]):
                raise ValueError("source chunk receipt or hash differs")
            with np.load(array_file, allow_pickle=False) as archive:
                part = {key: archive[key].copy() for key in archive.files}
            if mapping is None:
                mapping = {name: part[name] for name in ("ii", "jj", "hectares")}
            elif any(not np.array_equal(mapping[name], part[name]) for name in mapping):
                raise ValueError("crop-center map differs across chunks")
            for period in PERIODS:
                matrix = part[f"{period}_sum_mm"]
                if matrix.shape != (12, 30821):
                    raise ValueError("partial source shape differs")
                period_sums[period] = matrix if period_sums[period] is None else period_sums[period] + matrix
                period_counts[period] += part[f"{period}_counts"]
            verified_chunks += 1
        for period in PERIODS:
            if not np.array_equal(period_counts[period], np.full(12, 20)):
                raise ValueError("incomplete twenty-year month count")
            source[(member, period)] = period_sums[period] / 20
    return {period: (source[("r1i1p1f1", period)] + source[("r2i1p1f1", period)])/2
            for period in PERIODS}, mapping, verified_chunks


def reconstruct_published(mapping):
    if sha(AUTHOR) != AUTHOR_SHA or sha(GMST) != GMST_SHA:
        raise ValueError("published receipt changed")
    author = json.loads(AUTHOR.read_text())
    gmst_receipt = json.loads(GMST.read_text())
    gmst_path = ROOT / gmst_receipt["output_relative_to_project"]
    if sha(gmst_path) != gmst_receipt["member_sha256"]:
        raise ValueError("published GMST member changed")
    with xr.open_dataset(gmst_path) as ds:
        years = ds.time.dt.year.values.astype(int)
        temperatures = ds.tas.values.astype(float)
    if not np.array_equal(years, np.arange(2015, 2101)):
        raise ValueError("GMST chronology differs")
    temperature = dict(zip(years.tolist(), temperatures.tolist()))
    output = {period: np.empty((12, 30821), dtype=np.float64) for period in PERIODS}
    for month, item in enumerate(author["selected_members"], 1):
        path = AUTHOR.parent / item["name"]
        if sha(path) != item["sha256"]:
            raise ValueError("published coefficient changed")
        with xr.open_dataset(path) as ds:
            beta = ds.slope.values[0, mapping["ii"], mapping["jj"]]
            alpha = ds.intercept.values[0, mapping["ii"], mapping["jj"]]
        for period, period_years in PERIODS.items():
            sum_tdays = math.fsum(temperature[y]*calendar.monthrange(y, month)[1] for y in period_years)
            sum_days = math.fsum(calendar.monthrange(y, month)[1] for y in period_years)
            output[period][month-1] = (beta*sum_tdays/20 + alpha*sum_days/20)*86400
    return output


def audit_levels(saved_levels, direct, published, weights):
    total = math.fsum(float(w) for w in weights)
    checks = 0
    valid_by_period = {
        period: np.all(published[period] >= 0, axis=0)
        & (published[period].sum(axis=0) > 0)
        & (direct[period].sum(axis=0) > 0)
        for period in PERIODS
    }
    both_valid = np.logical_and.reduce(list(valid_by_period.values()))
    common_area = math.fsum(float(weights[i]) for i in np.flatnonzero(both_valid))

    def tv_on(support, target, model):
        area = math.fsum(float(weights[i]) for i in np.flatnonzero(support))
        if not area:
            return None
        return math.fsum(
            float(weights[i])*math.fsum(abs(float(target[m, i]/target[:, i].sum() - model[m, i]/model[:, i].sum()))
                                        for m in range(12))/2 for i in np.flatnonzero(support))/area

    for period in PERIODS:
        model, target = published[period], direct[period]
        invalid = np.any(model < 0, axis=0)
        valid = valid_by_period[period]
        expected = {
            "negative_month_center_count": int(np.count_nonzero(model < 0)),
            "any_negative_month_area_fraction": math.fsum(float(weights[i]) for i in np.flatnonzero(invalid))/total,
            "minimum_published_monthly_mm": float(np.min(model)),
            "valid_share_area_fraction": math.fsum(float(weights[i]) for i in np.flatnonzero(valid))/total,
            "fixed_both_periods_valid_area_fraction": common_area/total,
            "fixed_both_periods_month_share_tv": tv_on(both_valid, target, model),
        }
        expected["valid_support_month_share_tv"] = tv_on(valid, target, model)
        for key, value in expected.items():
            observed = saved_levels[period][key]
            if (observed is None) != (value is None) or (value is not None and
                    not math.isclose(observed, value, rel_tol=2e-11, abs_tol=2e-8)):
                raise AssertionError(f"{period}.{key} differs")
            checks += 1
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result_file, out = args.result.resolve(), args.out.resolve()
    if (not result_file.is_relative_to(ROOT / "data/interim")
            or not out.is_relative_to(ROOT / "data/interim") or out.exists()):
        parser.error("ignored source and fresh output required")
    saved = json.loads(result_file.read_text())
    array_file = result_file.parent / "twenty_year_crop_center_climatology_mm.npz"
    if saved["status"] != "same_source_twenty_year_monthly_climatology_not_yield_damage_scc" or sha(array_file) != saved["saved_arrays_sha256"]:
        raise ValueError("wrong source result or saved arrays")
    with np.load(array_file, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    direct, mapping, chunks = reconstruct_direct(saved)
    predicted = reconstruct_published(mapping)
    for name in ("ii", "jj", "hectares"):
        if not np.array_equal(arrays[name], mapping[name]):
            raise AssertionError("saved crop mapping differs")
    for period in PERIODS:
        close(arrays[f"direct_{period}_mm"], direct[period], "direct " + period)
        close(arrays[f"published_{period}_mm"], predicted[period], "published " + period)
    level_checks = audit_levels(saved["levels"], direct, predicted, mapping["hectares"])
    saved_change = dict(saved["change"])
    saved_change["result_sha256"] = sha(result_file)
    change_checks = audit_change(saved_change, {
        "hectares": mapping["hectares"],
        "direct_ensemble_mean_mm_2015": direct["early"],
        "direct_ensemble_mean_mm_2100": direct["late"],
        "published_mm_2015": predicted["early"],
        "published_mm_2100": predicted["late"],
    })["numeric_checks"]
    result = {"status": "independent_twenty_year_source_and_score_audit_passed",
              "verified_source_chunks": chunks, "level_numeric_checks": level_checks,
              "change_numeric_checks": change_checks,
              "array_matrix_reconstructions": 4,
              "primary_result_sha256": sha(result_file),
              "source_saved_arrays_sha256": sha(array_file)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
