#!/usr/bin/env python3
"""Build bounded April--September NOAA county weather controls for 2001--2013."""
from __future__ import annotations

import argparse
import calendar
import hashlib
import importlib.util
import json
import tomllib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "scripts" / "build_us_county_average_crop_year_features.py"
SPEC = importlib.util.spec_from_file_location("county_weather_builder", BUILDER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load county-average weather builder")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
SUMMARY = ROOT / "data" / "interim" / "nclimgrid_county_averages_full_20260916" / "acquisition_summary.json"
SOURCE_RECEIPT = ROOT / "data" / "provenance" / "noaa_nclimgrid_county_average_20260916.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def controls_for_year(
    year: int, batch_hashes: dict[tuple[int, int], str]
) -> tuple[pd.DataFrame, list[dict]]:
    counties, weather, versions = BUILDER.source_year(year, batch_hashes)
    start = date(year, 1, 1)
    first, last = date(year, 4, 1), date(year, 9, 30)
    left, right = (first - start).days, (last - start).days + 1
    if right - left != 183:
        raise ValueError("April--September window must contain 183 days")
    rain = weather["PRCP"][:, left:right]
    tavg = weather["TAVG"][:, left:right]
    tmax = weather["TMAX"][:, left:right]
    precipitation = rain.sum(axis=1, dtype="float64")
    tmean = tavg.mean(axis=1, dtype="float64")
    if not np.isfinite(precipitation).all() or not np.isfinite(tmean).all():
        raise ValueError("weather controls contain nonfinite values")
    if (precipitation < 0).any() or np.max(tavg - tmax) > 0.011:
        raise ValueError("weather controls violate physical checks")
    state_map = BUILDER.state_fips_to_alpha()
    frames = []
    for crop, threshold in (("corn_grain", 29.0), ("soybeans", 30.0)):
        heat = np.maximum(tmax - threshold, 0).sum(axis=1, dtype="float64")
        p100 = precipitation / 100
        frame = pd.DataFrame({
            "county_geoid": counties,
            "state": [state_map.get(value[:2]) for value in counties],
            "outcome_crop": crop,
            "harvest_year": year,
            "weather_start": first.isoformat(),
            "weather_end": last.isoformat(),
            "weather_days": right - left,
            "precipitation_mm": precipitation,
            "precipitation_per_100mm": p100,
            "precipitation_per_100mm_squared": np.square(p100),
            "tmean_c": tmean,
            "tmean_c_per_10c": tmean / 10,
            "crop_heat_threshold_c": threshold,
            "crop_tmax_exceedance_c_days": heat,
            "crop_tmax_exceedance_c_days_per_100": heat / 100,
            "weather_source": "noaa_nclimgrid_daily_county_scaled_v1_0_0",
            "weather_spatial_estimator": "published_county_area_average",
            "published_weather_replication": False,
            "analysis_role": "historical_external_validation_only",
            "scc_authorized": False,
        })
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    if result.state.isna().any() or result.duplicated(
        ["county_geoid", "outcome_crop", "harvest_year"]
    ).any():
        raise ValueError("weather control keys or state crosswalk invalid")
    return result, versions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    year_min, year_max = int(contract["year_min"]), int(contract["year_max"])
    source = json.loads(SUMMARY.read_text(encoding="utf-8"))
    source_receipt = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    if source["status"] != "complete" or source["completed_batches"] != 90:
        raise ValueError("NOAA county-average source acquisition is incomplete")
    if source_receipt["full_acquisition_summary_sha256"] != sha256(SUMMARY):
        raise ValueError("tracked NOAA source receipt does not pin the acquisition summary")
    batch_hashes = {
        (int(item["year"]), int(item["half"])): str(item["result_sha256"])
        for item in source["batches"]
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    rows = 0
    audits = []
    try:
        for year in range(year_min, year_max + 1):
            frame, versions = controls_for_year(year, batch_hashes)
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(arguments.out, table.schema, compression="zstd")
            elif writer.schema != table.schema:
                raise ValueError(f"weather control schema drift in {year}")
            writer.write_table(table)
            rows += len(frame)
            audits.append({
                "year": year, "rows": len(frame),
                "counties": int(frame.county_geoid.nunique()),
                "version_months": len(versions),
            })
    finally:
        if writer is not None:
            writer.close()
    if writer is None or pq.ParquetFile(arguments.out).metadata.num_rows != rows:
        raise RuntimeError("weather control output row count mismatch")
    audit = {
        "schema": "usdm_aprsep_weather_controls_v1",
        "contract": contract,
        "source_summary": {"path": str(SUMMARY), "sha256": sha256(SUMMARY)},
        "tracked_source_receipt": {
            "path": str(SOURCE_RECEIPT.relative_to(ROOT)),
            "sha256": sha256(SOURCE_RECEIPT),
            "dataset": source_receipt["dataset"],
            "doi": source_receipt["doi"],
            "metadata_url": source_receipt["metadata_url"],
            "source_root": source_receipt["source_root"],
        },
        "years": audits,
        "output": {"path": str(arguments.out), "sha256": sha256(arguments.out), "rows": rows},
        "published_difference": contract["published_difference"],
        "role": "historical_external_validation_only_not_damage_or_scc",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(f"wrote {rows} April--September crop-county-year weather rows")


if __name__ == "__main__":
    main()
