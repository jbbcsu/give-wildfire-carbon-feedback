#!/usr/bin/env python3
"""Build one outcome-free NOAA county-average corn/soy feature year."""
from __future__ import annotations

import argparse
import calendar as cal
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from audit_nclimgrid_county_average_sample import load_area_average, load_crosswalk

BASE = ROOT / "data/interim/nclimgrid_county_averages_full_20260916"
CALENDAR_DIR = ROOT / "data/interim/us_county/nass_calendar_1981_2025_20260916"
CALENDAR = CALENDAR_DIR / "nass_usual_date_calendars_1981_2025.csv"
CROSSWALK = ROOT / "data/raw/us_county/nclimgrid_county_averages/us-state-codes_ncei-to-fips.csv"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_CROP_YEAR_FEATURE_PROTOCOL_20260916.md"
VARIABLES = ("PRCP", "TAVG", "TMIN", "TMAX")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_year(year: int, batch_hashes: dict[tuple[int, int], str]) -> tuple[list[str], dict[str, np.ndarray], list[dict]]:
    state_map = load_crosswalk(CROSSWALK)
    source_keys: list[str] | None = None
    source_versions: list[dict] = []
    pieces: dict[str, list[np.ndarray]] = {name: [] for name in VARIABLES}
    for month in range(1, 13):
        half = 1 if month <= 6 else 2
        receipt_path = BASE / f"{year}_h{half}" / "result.json"
        if sha(receipt_path) != batch_hashes[(year, half)]:
            raise ValueError("NOAA half-year result differs from full-acquisition summary")
        receipt = json.loads(receipt_path.read_text())
        if (receipt["status"] != "complete_county_average_weather_batch" or
            receipt["year"] != year or receipt["half"] != half):
            raise ValueError("NOAA half-year source receipt identity changed")
        record = receipt["months"][f"{year}{month:02d}"]
        if record["county_rows"] != 3107 or record["real_days"] != cal.monthrange(year, month)[1]:
            raise ValueError("NOAA month support/calendar changed")
        for variable in VARIABLES:
            spec = record["sources"][variable]
            path = ROOT / spec["path"]
            if (not path.is_relative_to(BASE / f"{year}_h{half}") or
                sha(path) != spec["sha256"] or
                path.stat().st_size != spec["http"]["content_length"]):
                raise ValueError("NOAA source file/hash/byte count changed")
            loaded = load_area_average(path, variable, state_map)
            if loaded["year_month"] != (year, month):
                raise ValueError("NOAA source date changed")
            keys = sorted(loaded["records"])
            if len(keys) != 3107 or (source_keys is not None and keys != source_keys):
                raise ValueError("NOAA county keys changed across months")
            source_keys = keys
            values = np.stack([loaded["records"][key]["values"] for key in keys])
            if not np.isfinite(values).all():
                raise ValueError("NOAA source has nonfinite real days")
            pieces[variable].append(values.astype("float32"))
        version_spec = record["version"]
        version_path = ROOT / version_spec["path"]
        if (not version_path.is_relative_to(BASE / f"{year}_h{half}") or
            sha(version_path) != version_spec["sha256"]):
            raise ValueError("NOAA version file changed")
        source_versions.append({"year_month": f"{year}{month:02d}",
                                "version_sha256": version_spec["sha256"],
                                "version_text": version_spec["text"]})
    if source_keys is None:
        raise ValueError("NOAA year has no counties")
    arrays = {variable: np.concatenate(pieces[variable], axis=1) for variable in VARIABLES}
    days = 366 if cal.isleap(year) else 365
    if any(value.shape != (3107, days) for value in arrays.values()):
        raise ValueError("NOAA annual weather dimensions changed")
    if (np.min(arrays["PRCP"]) < 0 or
        np.max(arrays["TMIN"] - arrays["TAVG"]) > 0.011 or
        np.max(arrays["TAVG"] - arrays["TMAX"]) > 0.011):
        raise ValueError("NOAA annual physical weather check failed")
    return source_keys, arrays, source_versions


def max_dry_run(rain: np.ndarray) -> np.ndarray:
    current = np.zeros(rain.shape[0], dtype="int16")
    maximum = current.copy()
    for day in range(rain.shape[1]):
        current = np.where(rain[:, day] < 1.0, current + 1, 0)
        maximum = np.maximum(maximum, current)
    return maximum


def rx5(rain: np.ndarray) -> np.ndarray:
    if rain.shape[1] < 5:
        raise ValueError("crop season is shorter than five days")
    prefix = np.pad(np.cumsum(rain, axis=1, dtype="float64"), ((0, 0), (1, 0)))
    return np.max(prefix[:, 5:] - prefix[:, :-5], axis=1)


def features_for_window(rain: np.ndarray, tavg: np.ndarray, tmax: np.ndarray) -> dict[str, np.ndarray]:
    if rain.shape != tavg.shape or rain.shape != tmax.shape or rain.shape[1] < 30:
        raise ValueError("crop-year daily shape invalid")
    if (not np.isfinite(rain).all() or not np.isfinite(tavg).all() or
        not np.isfinite(tmax).all() or np.min(rain) < 0 or
        np.max(tavg - tmax) > 0.011):
        raise ValueError("crop-year daily weather physical values invalid")
    n = rain.shape[1]
    total = np.sum(rain, axis=1, dtype="float64")
    output = {
        "precip_mm": total,
        "wet_days_ge_1mm": np.sum(rain >= 1.0, axis=1),
        "cdd_max_days": max_dry_run(rain),
        "rx5day_mm": rx5(rain),
        "tmean_c": np.mean(tavg, axis=1, dtype="float64"),
        "tmax_exceedance_29c_c_days": np.sum(np.maximum(tmax - 29.0, 0), axis=1, dtype="float64"),
        "tmax_exceedance_30c_c_days": np.sum(np.maximum(tmax - 30.0, 0), axis=1, dtype="float64"),
        "tmax_days_gt_29c": np.sum(tmax > 29.0, axis=1),
        "tmax_days_gt_30c": np.sum(tmax > 30.0, axis=1),
        "zero_precipitation_season": (total == 0).astype("int8"),
    }
    bounds = np.floor(np.array([0.0, 0.3, 0.7, 1.0]) * n).astype(int)
    stage_amounts = []
    for stage, (left, right) in enumerate(zip(bounds[:-1], bounds[1:]), 1):
        amount = np.sum(rain[:, left:right], axis=1, dtype="float64")
        stage_amounts.append(amount)
        output[f"stage{stage}_precip_mm"] = amount
        output[f"stage{stage}_precip_share"] = np.divide(
            amount, total, out=np.zeros_like(total), where=total > 0)
        output[f"stage{stage}_tmean_c"] = np.mean(tavg[:, left:right], axis=1, dtype="float64")
        for threshold in (29, 30):
            output[f"stage{stage}_tmax_exceedance_{threshold}c_c_days"] = np.sum(
                np.maximum(tmax[:, left:right] - threshold, 0), axis=1, dtype="float64")
    if not np.allclose(np.sum(stage_amounts, axis=0), total, rtol=0, atol=1e-6):
        raise ValueError("stage rainfall fails sum-to-season identity")
    output["precipitation_concentration_hhi"] = sum(
        np.square(output[f"stage{stage}_precip_share"]) for stage in (1, 2, 3))
    if not all(np.isfinite(values).all() for values in output.values()):
        raise ValueError("crop-year feature nonfinite")
    return output


def state_fips_to_alpha() -> dict[str, str]:
    with CROSSWALK.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    result = {row["FIPS_code"].zfill(2): row["postal_code"] for row in rows}
    if len(result) != len(rows) or any(len(key) != 2 or len(value) != 2 for key, value in result.items()):
        raise ValueError("state FIPS-to-alpha crosswalk invalid")
    return result


def build_year(year: int, calendar_path: Path, batch_hashes: dict[tuple[int, int], str]) -> tuple[pd.DataFrame, dict]:
    counties, weather, versions = source_year(year, batch_hashes)
    state_alpha = state_fips_to_alpha()
    frame = pd.read_csv(calendar_path, dtype={"state": str, "calendar_crop": str})
    frame = frame.loc[frame.harvest_year.eq(year) &
                      frame.calendar_crop.isin(("corn_grain", "soybeans")) &
                      frame.calendar_role.eq("fixed_primary")].copy()
    if frame.empty or frame.duplicated(["state", "calendar_crop"]).any():
        raise ValueError("fixed state/crop/year calendar missing or duplicated")
    start = date(year, 1, 1)
    groups: dict[str, list[int]] = {}
    for index, fips in enumerate(counties):
        alpha = state_alpha.get(fips[:2])
        if alpha is not None:
            groups.setdefault(alpha, []).append(index)
    records: list[dict] = []
    for row in frame.itertuples(index=False):
        indexes = groups.get(row.state, [])
        if not indexes:
            continue
        first = date.fromisoformat(row.season_start)
        last = date.fromisoformat(row.season_end)
        if first.year != year or last.year != year or last < first:
            raise ValueError("unregistered cross-year crop calendar")
        left = (first - start).days
        right = (last - start).days + 1
        if right > weather["PRCP"].shape[1]:
            raise ValueError("crop-year season extends past NOAA weather year")
        values = features_for_window(
            weather["PRCP"][indexes, left:right],
            weather["TAVG"][indexes, left:right],
            weather["TMAX"][indexes, left:right])
        for position, index in enumerate(indexes):
            records.append({"county_geoid": counties[index], "state": row.state,
                            "outcome_crop": row.calendar_crop, "harvest_year": year,
                            "season_start": row.season_start, "season_end": row.season_end,
                            "season_days": right - left,
                            "weather_source": "noaa_nclimgrid_daily_county_scaled_v1_0_0",
                            "weather_spatial_estimator": "published_county_area_average",
                            "calendar_source_id": row.calendar_source_id,
                            "calendar_role": row.calendar_role,
                            "calendar_vintage": row.calendar_vintage,
                            "stage_definition": row.stage_definition,
                            **{name: float(value[position]) for name, value in values.items()}})
    result = pd.DataFrame(records).sort_values(
        ["outcome_crop", "county_geoid", "harvest_year"]).reset_index(drop=True)
    if result.empty or result.duplicated(["outcome_crop", "county_geoid", "harvest_year"]).any():
        raise ValueError("county crop-year feature keys invalid")
    if not np.allclose(sum(result[f"stage{s}_precip_mm"] for s in (1, 2, 3)),
                       result.precip_mm, rtol=0, atol=1e-6):
        raise ValueError("output stage-rainfall identity failed")
    return result, {"version_texts": versions, "input_counties": len(counties),
                    "output_rows": len(result), "output_counties": int(result.county_geoid.nunique()),
                    "rows_by_crop": result.groupby("outcome_crop").size().to_dict()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if not 1981 <= args.year <= 2025 or out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("year or fresh ignored output directory invalid")
    summary_path = BASE / "acquisition_summary.json"
    summary = json.loads(summary_path.read_text())
    if summary["status"] != "complete" or summary["completed_batches"] != 90 or summary["source_objects"] != 2700:
        raise ValueError("complete 1981–2025 NOAA source acquisition not certified")
    calendar_receipt = json.loads((CALENDAR_DIR / "result.json").read_text())
    if (calendar_receipt["status"] != "nass_calendar_1981_2025_overlap_validated" or
        calendar_receipt["calendar_sha256"] != sha(CALENDAR) or
        calendar_receipt["protocol_sha256"] != sha(PROTOCOL)):
        raise ValueError("NASS 1981–2025 calendar overlap receipt invalid")
    batch_hashes = {(item["year"], item["half"]): item["result_sha256"]
                    for item in summary["batches"]}
    if len(batch_hashes) != 90 or any((args.year, half) not in batch_hashes for half in (1, 2)):
        raise ValueError("NOAA source summary lacks exact half-year identities")
    frame, audit = build_year(args.year, CALENDAR, batch_hashes)
    out.mkdir(parents=True)
    output = out / "features.parquet"
    frame.to_parquet(output, index=False)
    receipt = {"status": "county_average_crop_year_features_built",
               "year": args.year, "protocol_sha256": sha(PROTOCOL),
               "source_summary_sha256": sha(summary_path),
               "calendar_sha256": sha(CALENDAR), "crosswalk_sha256": sha(CROSSWALK),
               "code_sha256": sha(Path(__file__)), "features_sha256": sha(output),
               "audit": audit, "nass_outcomes_read": False,
               "response_or_scc_estimated": False}
    (out / "result.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "year": args.year,
                      "rows": len(frame), "counties": audit["output_counties"]}))


if __name__ == "__main__":
    main()
