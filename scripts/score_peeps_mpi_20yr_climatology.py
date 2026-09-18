#!/usr/bin/env python3
"""Compare published monthly patterns with two twenty-year source climates."""
import calendar
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import xarray as xr

from score_peeps_mpi_change_decomposition import compute


ROOT = Path(__file__).resolve().parents[1]
AUTHOR_RECEIPT = ROOT / "data/interim/peeps_author_mpi_ssp585_monthly_20260917/selected_months_receipt.json"
GMST_RECEIPT = ROOT / "data/interim/peeps_published_mpi_ssp585_tgav_20260917/selected_member_receipt.json"
AUTHOR_SHA = "fafe91fafb0f64b1448501bb49b623e21ad86e3c882a6b65b5fb337d8b6fa753"
GMST_SHA = "cd632ffb21d171c48787f5d4766a2ae29f22d657db56a074738a7dc2c9a2bad3"
PARTS = {"r1i1p1f1": (0, 1), "r2i1p1f1": (0, 1, 3, 4)}
PERIODS = {"early": range(2015, 2035), "late": range(2081, 2101)}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def aggregate_member(partials):
    """Sum nonoverlapping time-chunk arrays; require 20 per month/period."""
    output = {}
    for period in PERIODS:
        sums = np.sum([part[f"{period}_sum_mm"] for part in partials], axis=0)
        counts = np.sum([part[f"{period}_counts"] for part in partials], axis=0)
        if not np.array_equal(counts, np.full(12, 20)):
            raise ValueError("source member does not have twenty years per month")
        if not np.isfinite(sums).all() or np.any(sums < 0):
            raise ValueError("invalid direct member monthly sums")
        output[period] = sums / 20
    return output


def load_partials():
    members = {}
    identities = []
    first_map = None
    for member, chunks in PARTS.items():
        partials = []
        for chunk in chunks:
            directory = ROOT / f"data/interim/peeps_mpi_20yr_{member[:2]}_chunk{chunk}_20260918"
            receipt_path = directory / "result.json"
            receipt = json.loads(receipt_path.read_text())
            array_path = directory / "monthly_crop_center_partial.npz"
            if (receipt["status"] != "single_source_chunk_20yr_partial_not_climate_response_or_scc"
                    or receipt["member"] != member or receipt["chunk_index"] != chunk
                    or not receipt["gcs_crc32c_verified"] or not receipt["gcs_md5_verified"]
                    or receipt["partial_array_sha256"] != sha(array_path)
                    or receipt["selected_native_negative_cells"] != 0):
                raise ValueError("source partial identity or integrity failed")
            with np.load(array_path, allow_pickle=False) as archive:
                part = {name: archive[name].copy() for name in archive.files}
            if set(part) != {"ii", "jj", "hectares", "early_sum_mm", "early_counts", "late_sum_mm", "late_counts"}:
                raise ValueError("source partial schema changed")
            coordinate = {name: part[name] for name in ("ii", "jj", "hectares")}
            if first_map is None:
                first_map = coordinate
            elif any(not np.array_equal(first_map[name], coordinate[name]) for name in coordinate):
                raise ValueError("crop-center map differs across chunks")
            partials.append(part)
            identities.append({"member": member, "chunk": chunk,
                               "receipt_sha256": sha(receipt_path), "partial_sha256": sha(array_path),
                               "source_compressed_sha256": receipt["source_compressed_sha256"],
                               "selected_plane_count": receipt["selected_plane_count"]})
        members[member] = aggregate_member(partials)
    if len(first_map["hectares"]) != 30821 or len(identities) != 6:
        raise ValueError("fixed crop-center/chunk support changed")
    direct = {period: (members["r1i1p1f1"][period] + members["r2i1p1f1"][period]) / 2
              for period in PERIODS}
    return direct, first_map, identities


def load_author_prediction(ii, jj):
    if sha(AUTHOR_RECEIPT) != AUTHOR_SHA or sha(GMST_RECEIPT) != GMST_SHA:
        raise ValueError("published author receipts changed")
    author = json.loads(AUTHOR_RECEIPT.read_text())
    gmst_record = json.loads(GMST_RECEIPT.read_text())
    if author["model"] != "MPI-ESM1-2-HR" or author["scenario"] != "ssp585" or len(author["selected_members"]) != 12:
        raise ValueError("published author pattern identity changed")
    gmst_file = ROOT / gmst_record["output_relative_to_project"]
    if sha(gmst_file) != gmst_record["member_sha256"]:
        raise ValueError("published GMST series changed")
    with xr.open_dataset(gmst_file) as dataset:
        years = dataset.time.dt.year.values.astype(int)
        temperatures = dataset.tas.values.astype(float)
    if not np.array_equal(years, np.arange(2015, 2101)) or not np.isfinite(temperatures).all():
        raise ValueError("published GMST chronology changed")
    t = dict(zip(years.tolist(), temperatures.tolist()))
    predicted = {period: np.empty((12, len(ii)), dtype=np.float64) for period in PERIODS}
    for month, member in enumerate(author["selected_members"], 1):
        path = AUTHOR_RECEIPT.parent / member["name"]
        if sha(path) != member["sha256"]:
            raise ValueError("published monthly coefficient changed")
        with xr.open_dataset(path) as dataset:
            slope = dataset.slope.values[0, ii, jj]
            intercept = dataset.intercept.values[0, ii, jj]
        if not np.isfinite(slope).all() or not np.isfinite(intercept).all():
            raise ValueError("published coefficient nonfinite")
        for period, period_years in PERIODS.items():
            gmst_day_mean = np.mean([t[year]*calendar.monthrange(year, month)[1] for year in period_years])
            day_mean = np.mean([calendar.monthrange(year, month)[1] for year in period_years])
            predicted[period][month-1] = (slope*gmst_day_mean + intercept*day_mean)*86400
    return predicted


def period_levels(direct, predicted, weights):
    outcome = {}
    valid_by_period = {
        period: np.all(predicted[period] >= 0, axis=0)
        & (direct[period].sum(axis=0) > 0)
        & (predicted[period].sum(axis=0) > 0)
        for period in PERIODS
    }
    both_valid = np.logical_and.reduce(list(valid_by_period.values()))

    def share_tv(source, model, support):
        if not np.any(support):
            return None
        a = source[:, support] / source[:, support].sum(axis=0)
        b = model[:, support] / model[:, support].sum(axis=0)
        return float(np.sum(np.sum(np.abs(a-b), axis=0)*weights[support])
                     / np.sum(weights[support]) / 2)

    for period in PERIODS:
        source = direct[period]
        model = predicted[period]
        invalid = np.any(model < 0, axis=0)
        valid = valid_by_period[period]
        total = np.sum(weights)
        area = float(np.sum(weights[valid]) / total)
        outcome[period] = {
            "negative_month_center_count": int(np.count_nonzero(model < 0)),
            "any_negative_month_area_fraction": float(np.sum(weights[invalid])/total),
            "minimum_published_monthly_mm": float(np.min(model)),
            "valid_share_area_fraction": area,
            "valid_support_month_share_tv": share_tv(source, model, valid),
            "fixed_both_periods_valid_area_fraction": float(np.sum(weights[both_valid])/total),
            "fixed_both_periods_month_share_tv": share_tv(source, model, both_valid),
        }
    return outcome


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if (out.exists() or not out.is_relative_to(ROOT / "data/interim")
            or shutil.disk_usage(ROOT).free < 130*2**30):
        parser.error("fresh ignored output and free-disk reserve required")
    direct, mapping, identities = load_partials()
    predicted = load_author_prediction(mapping["ii"], mapping["jj"])
    weights = mapping["hectares"]
    levels = period_levels(direct, predicted, weights)
    change = compute(direct["early"], direct["late"], predicted["early"], predicted["late"], weights)
    out.mkdir(parents=True)
    arrays_path = out / "twenty_year_crop_center_climatology_mm.npz"
    np.savez_compressed(arrays_path, hectares=weights, ii=mapping["ii"], jj=mapping["jj"],
                        direct_early_mm=direct["early"], direct_late_mm=direct["late"],
                        published_early_mm=predicted["early"], published_late_mm=predicted["late"])
    report = {"status": "same_source_twenty_year_monthly_climatology_not_yield_damage_scc",
              "periods": {name: [min(years), max(years)] for name, years in PERIODS.items()},
              "author_receipt_sha256": AUTHOR_SHA, "gmst_receipt_sha256": GMST_SHA,
              "source_partials": identities, "saved_arrays_sha256": sha(arrays_path),
              "levels": levels, "change": change,
              "forcing_approved": False, "yield_damage_scc_estimated": False}
    (out / "result.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "levels": levels,
                      "annual_change": change["annual"], "decomposition": change["decomposition"]}))


if __name__ == "__main__":
    main()
