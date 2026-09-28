#!/usr/bin/env python3
"""Build one year of NOAA county-average weather features for sorghum/cotton."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "scripts/build_us_county_average_crop_year_features.py"
SOURCE_BASE = ROOT / "data/interim/nclimgrid_county_averages_full_20260916"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def load_base():
    spec = importlib.util.spec_from_file_location("county_average_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load validated county-average feature implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--county-inventory", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if not 1981 <= args.year <= 2018 or args.out_dir.exists():
        raise ValueError("year must be 1981--2018 and output must be fresh")
    base = load_base()
    summary_path = SOURCE_BASE / "acquisition_summary.json"
    summary = json.loads(summary_path.read_text())
    if summary["status"] != "complete" or summary["completed_batches"] != 90 or summary["source_objects"] != 2700:
        raise ValueError("NOAA source acquisition is not certified complete")
    batch_hashes = {(item["year"], item["half"]): item["result_sha256"] for item in summary["batches"]}
    counties, weather, versions = base.source_year(args.year, batch_hashes)
    inventory = pd.read_csv(args.county_inventory, dtype={"county_geoid": str, "state": str})
    if not inventory.feature_construction_eligible.eq(True).all() or inventory.scc_authorized.eq(True).any():
        raise ValueError("county inventory gate differs")
    requested = set(inventory.county_geoid.astype(str))
    missing = requested - set(counties)
    if missing:
        raise ValueError(f"eligible counties missing from NOAA keys: {sorted(missing)}")
    county_index = {geoid: index for index, geoid in enumerate(counties)}
    calendar = pd.read_csv(args.calendar)
    calendar = calendar.loc[calendar.harvest_year.eq(args.year) & calendar.calendar_role.eq("fixed_primary")].copy()
    if calendar.empty or calendar.duplicated(["calendar_crop", "state", "harvest_year"]).any():
        raise ValueError("primary crop/state/year calendar is empty or duplicated")
    records = []
    for row in calendar.itertuples(index=False):
        selected_geoids = sorted(inventory.loc[inventory.state.eq(row.state), "county_geoid"].astype(str))
        indexes = [county_index[geoid] for geoid in selected_geoids]
        first, last = date.fromisoformat(row.season_start), date.fromisoformat(row.season_end)
        if first.year != args.year or last.year != args.year or last < first:
            raise ValueError("primary calendar is not a within-year ordered window")
        left, right = (first - date(args.year, 1, 1)).days, (last - date(args.year, 1, 1)).days + 1
        values = base.features_for_window(
            weather["PRCP"][indexes, left:right], weather["TAVG"][indexes, left:right], weather["TMAX"][indexes, left:right]
        )
        for position, geoid in enumerate(selected_geoids):
            records.append({
                "county_geoid": geoid, "state": row.state, "crop": row.calendar_crop,
                "harvest_year": args.year, "season_start": row.season_start, "season_end": row.season_end,
                "season_days": right - left,
                "weather_source": "noaa_nclimgrid_daily_county_scaled_v1_0_0",
                "weather_spatial_estimator": "published_county_area_average",
                "calendar_source_id": row.calendar_source_id, "calendar_role": row.calendar_role,
                "calendar_vintage": row.calendar_vintage, "stage_definition": row.stage_definition,
                **{name: float(value[position]) for name, value in values.items()},
                "feature_construction_eligible": True,
                "response_estimation_authorized": False, "scc_authorized": False,
            })
    frame = pd.DataFrame(records).sort_values(["crop", "county_geoid", "harvest_year"]).reset_index(drop=True)
    keys = ["crop", "county_geoid", "harvest_year"]
    if frame.empty or frame.duplicated(keys).any() or not np.allclose(
        frame.stage1_precip_mm + frame.stage2_precip_mm + frame.stage3_precip_mm,
        frame.precip_mm, rtol=0, atol=1e-6,
    ):
        raise ValueError("output key or rainfall reconciliation gate failed")
    args.out_dir.mkdir(parents=True)
    output = args.out_dir / "features.parquet"
    frame.to_parquet(output, index=False)
    receipt = {
        "status": "sorghum_cotton_county_average_features_built", "year": args.year,
        "source_summary_sha256": digest(summary_path), "base_implementation_sha256": digest(BASE_SCRIPT),
        "implementation_sha256": digest(Path(__file__)), "calendar_sha256": digest(args.calendar),
        "county_inventory_sha256": digest(args.county_inventory), "features_sha256": digest(output),
        "source_version_texts": versions, "rows": len(frame), "counties": int(frame.county_geoid.nunique()),
        "rows_by_crop": {k: int(v) for k, v in frame.groupby("crop").size().items()},
        "yield_values_read": False, "response_estimation_authorized": False, "scc_authorized": False,
    }
    (args.out_dir / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"year": args.year, "rows": len(frame), "counties": int(frame.county_geoid.nunique())}))


if __name__ == "__main__":
    main()
