#!/usr/bin/env python3
"""Area-weight one validated late-century SPEI pair over crop calendars."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from spei_calendar_windows import SCALES, WINDOWS  # noqa: E402
from spei_crop_window_metrics import window_metrics  # noqa: E402
from build_spei_tile_crop_features import spans  # noqa: E402

PARTITIONS = ROOT/"data/interim/spei_crop_key_partitions_20260908/result.json"
PARTITION_VALIDATION = ROOT/"data/interim/spei_crop_key_partition_validation_20260908/result.json"
COVERAGE = ROOT/"data/interim/spei_calendar_coverage_20260908/result.json"
YEARS = tuple(range(2092, 2100))


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def frozen_support() -> pd.DataFrame:
    manifest = json.loads(PARTITIONS.read_text()); validation = json.loads(PARTITION_VALIDATION.read_text())
    require(manifest["status"] == "frozen_keys_partitioned" and validation["status"] == "passed", "crop-key validation not passed")
    require(validation["input_sha256"] == digest(PARTITIONS) and manifest["coverage_sha256"] == digest(COVERAGE), "crop-key binding changed")
    frames = []
    columns = ["crop", "lat", "lon_360", "cell_id", "noirr_calendar_valid", "firr_calendar_valid"]
    for record in manifest["records"]:
        raw = Path(record["path"]); path = raw if raw.is_absolute() else ROOT/raw
        require(digest(path) == record["sha256"], "crop-key partition hash changed")
        frame = pq.read_table(path, columns=columns).to_pandas().drop_duplicates()
        require(not frame.duplicated(["crop", "cell_id"]).any(), "crop-cell calendar flags vary across historical years")
        frames.append(frame)
    support = pd.concat(frames, ignore_index=True).sort_values(["crop", "cell_id"]).reset_index(drop=True)
    require(set(support.crop) == {"mai", "soy"} and not support.duplicated(["crop", "cell_id"]).any(), "exact maize/soy support required")
    return support


def sources() -> tuple[dict, pd.DataFrame, list[dict]]:
    coverage = json.loads(COVERAGE.read_text()); calendars = {}; weights = None; bindings = []
    for binding in coverage["bindings"]:
        if binding["role"] not in {"calendar", "weights"}:
            continue
        path = ROOT/binding["path"]; algorithm = "sha512" if binding["role"] == "calendar" else "sha256"
        require(digest(path, algorithm) == binding[algorithm], "calendar/weight source changed")
        bindings.append(binding)
        if binding["role"] == "weights":
            columns = ["crop", "lat", "lon_360", "irrigation", "area_share", "irrigated_area_ha", "rainfed_area_ha", "total_area_ha"]
            weights = pq.read_table(path, columns=columns, filters=[("crop", "in", ["mai", "soy"])]).to_pandas()
        else:
            crop, regime = path.stem.split("_")[-2:]
            with h5py.File(path, "r") as handle:
                calendars[(crop, regime)] = {"lat": {float(v): i for i, v in enumerate(handle["lat"][:])},
                                             "lon": {float(v)%360: i for i, v in enumerate(handle["lon"][:])},
                                             "plant": handle["planting_day"][:], "maturity": handle["maturity_day"][:]}
    require(weights is not None and set(calendars) == {(c, r) for c in ("mai", "soy") for r in ("noirr", "firr")}, "calendar/weight registry incomplete")
    require(not weights.duplicated(["crop", "lat", "lon_360", "irrigation"]).any(), "crop-area keys duplicated")
    return calendars, weights, bindings


def new_accumulator() -> dict:
    return {"declared_area_ha": 0.0, "complete_area_ha": 0.0, "area_x_spei": 0.0,
            "tail_clipped_area_ha": 0.0, "positive_regime_cells": 0, "complete_regime_cells": 0,
            "status_counts": defaultdict(int)}


def add(accumulator: dict, area: float, metric: dict) -> None:
    accumulator["declared_area_ha"] += area; accumulator["positive_regime_cells"] += 1
    status = metric["status"]; accumulator["status_counts"][status] += 1
    if status == "complete":
        accumulator["complete_area_ha"] += area; accumulator["area_x_spei"] += area*metric["spei_mean"]
        accumulator["tail_clipped_area_ha"] += area*bool(metric["tail_clipped_months"])
        accumulator["complete_regime_cells"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pair_dir = args.pair_dir if args.pair_dir.is_absolute() else ROOT/args.pair_dir
    output = args.output if args.output.is_absolute() else ROOT/args.output
    require(not output.exists(), "fresh crop-window output required")
    result_path = pair_dir/"result.json"; validation_path = pair_dir/"validation.json"
    result = json.loads(result_path.read_text()); validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed" and validation["pair_result_sha256"] == digest(result_path), "pair validation binding failed")
    cube = ROOT/result["output"]["path"]
    require(digest(cube) == result["output"]["sha256"] == validation["output_sha256"], "validated SPEI cube changed")
    support = frozen_support(); calendars, weights, bindings = sources()
    weight_lookup = weights.set_index(["crop", "lat", "lon_360", "irrigation"]).to_dict("index")
    accumulators = defaultdict(new_accumulator)
    with h5py.File(cube, "r") as handle:
        months = pd.DatetimeIndex(handle["month"][:].astype("datetime64[ns]"))
        require(tuple(handle["scale"][:]) == SCALES and months.equals(pd.date_range("2091-01-01", "2100-12-01", freq="MS")), "SPEI axes changed")
        latitudes = handle["latitude"][:]; longitudes = np.mod(handle["longitude"][:], 360)
        values = handle["spei"][:]; clips = handle["cdf_clip_code"][:]
    require(np.array_equal(support.lat.to_numpy(), latitudes[support.cell_id]) and np.array_equal(support.lon_360.to_numpy(), longitudes[support.cell_id]), "crop support does not map to SPEI cells")
    month_lookup = {(month.year, month.month): index for index, month in enumerate(months)}
    for row in support.itertuples(index=False):
        for regime in ("noirr", "firr"):
            weight = weight_lookup[(row.crop, row.lat, row.lon_360, regime)]
            area = float(weight["rainfed_area_ha"] if regime == "noirr" else weight["irrigated_area_ha"])
            share = float(weight["area_share"])
            require(abs(area-float(weight["total_area_ha"])*share) <= max(1e-8, 1e-10*float(weight["total_area_ha"])), "area/share arithmetic changed")
            if area <= 0:
                continue
            calendar = calendars[(row.crop, regime)]; i, j = calendar["lat"][row.lat], calendar["lon"][row.lon_360]
            valid = bool(getattr(row, regime+"_calendar_valid"))
            for year in YEARS:
                windows = spans(year, calendar["plant"][i,j], calendar["maturity"][i,j]) if valid else None
                for window in WINDOWS:
                    for scale_index, scale in enumerate(SCALES):
                        metric = ({"status": "invalid_calendar"} if windows is None else
                                  window_metrics(values[scale_index, :, row.cell_id], clips[scale_index, :, row.cell_id],
                                                 month_lookup, *windows[window]))
                        add(accumulators[(row.crop, year, window, scale, regime)], area, metric)
                        add(accumulators[(row.crop, year, window, scale, "combined")], area, metric)
    records = []
    for key in sorted(accumulators):
        crop, year, window, scale, regime = key; item = accumulators[key]
        complete = item["complete_area_ha"]
        records.append({"crop": crop, "harvest_year": year, "window": window, "scale_months": scale,
                        "irrigation": regime, "declared_area_ha": item["declared_area_ha"],
                        "complete_area_ha": complete, "complete_area_fraction": complete/item["declared_area_ha"],
                        "area_weighted_mean_spei": item["area_x_spei"]/complete if complete else None,
                        "tail_clipped_area_fraction_of_complete": item["tail_clipped_area_ha"]/complete if complete else None,
                        "positive_regime_cells": item["positive_regime_cells"], "complete_regime_cells": item["complete_regime_cells"],
                        "status_counts": dict(sorted(item["status_counts"].items()))})
    answer = {"schema": "isimip3b_late_drought_crop_window_summary_v1", "status": "completed_pending_independent_validation",
              "role": "fixed_area_crop_calendar_drought_exposure_not_yield_damage_or_scc", "esm": result["esm"],
              "scenario": result["scenario"], "harvest_years": list(YEARS), "windows": list(WINDOWS), "scales": list(SCALES),
              "support": {"crop_cell_pairs": len(support), "by_crop": support.groupby("crop").size().to_dict(),
                          "partition_manifest_sha256": digest(PARTITIONS), "partition_validation_sha256": digest(PARTITION_VALIDATION)},
              "sources": {"pair_result_sha256": digest(result_path), "pair_validation_sha256": digest(validation_path),
                          "cube_sha256": digest(cube), "coverage_sha256": digest(COVERAGE), "bindings": bindings},
              "records": records, "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                                       "sha256": digest(Path(__file__).resolve())},
              "gates": {"crop_window_exposure": False, "yield_response": False, "damage": False, "scc": False}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(answer, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps({"status": answer["status"], "records": len(records), "crop_cell_pairs": len(support)}))


if __name__ == "__main__":
    main()
