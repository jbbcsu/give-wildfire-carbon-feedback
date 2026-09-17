#!/usr/bin/env python3
"""Audit-gated, bounded global-tile centered weather-feature pilot.

Only source-derived 21-year means are built. No GMT response is fitted and no
yield, damage, or SCC quantity is computed. Run with run_bounded_job.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from audit_gfdl_contiguous_28yr_global import OUTPUT as SOURCE_AUDIT, directory
from build_rimex_centered_feature_means import (
    reconcile, smooth_features, smooth_gmst,
)
from pilot_gfdl_contiguous_global_boundary import BOUNDED, ROOT


GMST = BOUNDED / "same_realization_gmst_2031_2060.parquet"
GMST_REFERENCE = BOUNDED / "same_realization_gmst_2042_2049_centered21.parquet"
REFERENCE = {
    "season": BOUNDED / "mai_noirr_2042_2049_lat100_102_centered21_features.parquet",
    "stages": BOUNDED / "mai_noirr_2042_2049_lat100_102_centered21_stages.parquet",
}


def input_frame(start: int, stop: int, name: str,
                latitudes: list[float]) -> pd.DataFrame:
    frames = []
    for year in range(2032, 2060):
        path = directory(year) / f"lat{start:03d}_{stop:03d}" / f"{name}.parquet"
        frame = pd.read_parquet(path)
        require(set(frame.harvest_year) <= {year}, f"{year}: wrong tile year")
        frames.append(frame.loc[frame.lat.isin(latitudes)])
    return pd.concat(frames, ignore_index=True)


def empty_frame(name: str) -> pd.DataFrame:
    """Give zero-cell tiles a typed schema, using the prior reference."""
    frame = pd.read_parquet(REFERENCE[name]).iloc[:0].copy()
    geometry = (["stage_start_offset_day", "stage_end_offset_day", "stage_days"]
                if name == "stages" else ["season_days"])
    for field in geometry:
        frame = frame.rename(columns={field: f"{field}_21yr_mean"})
        frame[f"{field}_21yr_mean"] = frame[f"{field}_21yr_mean"].astype(float)
    return frame


def bounded_parity(frame: pd.DataFrame, name: str) -> int:
    old = pd.read_parquet(REFERENCE[name])
    new = frame.loc[frame.lat.isin(old.lat.unique())].copy()
    # The earlier bounded artifact retained fixed crop-calendar geometry as
    # unsuffixed columns; the reusable smoothing builder emits its 21-year
    # arithmetic means. The calendar is fixed within a cell, so compare the
    # values after an explicit schema-only rename, never dropping geometry.
    geometry = (["stage_start_offset_day", "stage_end_offset_day", "stage_days"]
                if name == "stages" else ["season_days"])
    new = new.rename(columns={f"{field}_21yr_mean": field for field in geometry})
    keys = ["center_year", "lat", "lon", "crop", "irrigation"]
    if name == "stages":
        keys.append("stage_id")
    require(set(new.columns) == set(old.columns), f"{name}: centered columns changed")
    old = old.sort_values(keys).reset_index(drop=True)
    new = new[old.columns].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(old, new, check_dtype=False,
                                  check_exact=False, atol=1e-9, rtol=0)
    return len(old)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat-start", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    start, stop = args.lat_start, args.lat_start + 10
    require(start in range(0, 360, 10), "latitude tile must be one registered 10-row band")
    require(args.out.resolve().is_relative_to((ROOT / "data/interim").resolve()),
            "output must remain in ignored interim data")
    source = json.loads(SOURCE_AUDIT.read_text())
    require(source["status"] == "passed_source_only_not_gmt_response_yield_damage_or_scc"
            and source["years"] == list(range(2032, 2060))
            and source["new_years_independent_raw_daily_samples"] == 252,
            "28-year full-global source audit gate closed")
    gmst = smooth_gmst(pd.read_parquet(GMST), first_feature_year=2032,
                       last_feature_year=2059, window=21)
    reference_gmst = pd.read_parquet(GMST_REFERENCE)
    pd.testing.assert_frame_equal(gmst.reset_index(drop=True),
                                  reference_gmst.reset_index(drop=True),
                                  check_dtype=False, check_exact=False,
                                  atol=1e-10, rtol=0)
    outputs = {
        "season": args.out / "centered_season_21yr.parquet",
        "stages": args.out / "centered_stages_21yr.parquet",
    }
    receipt = args.out / "centered_audit_21yr.json"
    require(not any(path.exists() for path in (*outputs.values(), receipt)),
            "existing centered tile needs review")
    args.out.mkdir(parents=True, exist_ok=True)
    base = pd.read_parquet(directory(2032) / f"lat{start:03d}_{stop:03d}" / "season.parquet",
                           columns=["lat"])
    latitudes = sorted(base.lat.astype(float).unique().tolist())
    prior_lat = (set(pd.read_parquet(REFERENCE["season"], columns=["lat"]).lat.unique())
                 if start == 100 else set())
    prior = {"season": [], "stages": []}
    count = {"season": 0, "stages": 0}
    max_difference = {"stage_days": 0.0, "precip_mm": 0.0, "wet_days_n": 0.0}
    writers: dict[str, pq.ParquetWriter] = {}
    try:
        for offset in range(0, len(latitudes), 2):
            subset = latitudes[offset:offset + 2]
            season = smooth_features(input_frame(start, stop, "season", subset),
                                     stage=False, window=21)
            stages = smooth_features(input_frame(start, stop, "stages", subset),
                                     stage=True, window=21)
            local = reconcile(season, stages, gmst, window=21)
            require(local["center_years"] == list(range(2042, 2050)),
                    "centered output years changed")
            for name, frame in (("season", season), ("stages", stages)):
                table = pa.Table.from_pandas(frame, preserve_index=False)
                if name not in writers:
                    writers[name] = pq.ParquetWriter(outputs[name], table.schema,
                                                      compression="zstd")
                writers[name].write_table(table)
                count[name] += len(frame)
                if prior_lat:
                    prior[name].append(frame.loc[frame.lat.isin(prior_lat)])
            for field, value in local["stage_season_additive_max_absolute_differences"].items():
                max_difference[field] = max(max_difference[field], value)
        if not latitudes:
            for name in outputs:
                table = pa.Table.from_pandas(empty_frame(name), preserve_index=False)
                writers[name] = pq.ParquetWriter(outputs[name], table.schema,
                                                  compression="zstd")
                writers[name].write_table(table)
    finally:
        for writer in writers.values():
            writer.close()
    require(count["season"] == len(base) * 8
            and count["stages"] == len(base) * 3 * 8,
            "centered tile row support changed")
    audit = {
        "role": "contiguous_centered_means_mechanics_not_response_damage_or_scc",
        "result": "passed", "window_years": 21,
        "center_years": list(range(2042, 2050)),
        "season_rows": count["season"], "stage_rows": count["stages"],
        "gmst_rows": len(gmst),
        "stage_season_additive_max_absolute_differences": max_difference,
        "latitude_chunk_size": 2,
    }
    if start == 100:
        audit["prior_two_latitude_parity_rows"] = {
            name: bounded_parity(pd.concat(prior[name], ignore_index=True), name)
            for name in ("season", "stages")
        }
        require(audit["prior_two_latitude_parity_rows"] ==
                {"season": 5488, "stages": 16464},
                "bounded full-year centered parity support changed")
    audit.update({
        "schema": "gfdl_ssp126_global_maize_centered_tile_source_only_v1",
        "status": "passed_centered_source_only_not_gmt_response_yield_damage_or_scc",
        "lat_start": start, "lat_stop": stop,
        "source_audit_sha256": digest(SOURCE_AUDIT),
        "gmst_input_sha256": digest(GMST),
        "season_sha256": digest(outputs["season"]),
        "stages_sha256": digest(outputs["stages"]),
    })
    receipt.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: audit[key] for key in
                      ("status", "lat_start", "season_rows", "stage_rows",
                       "center_years")}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
