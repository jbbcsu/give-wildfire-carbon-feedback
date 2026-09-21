#!/usr/bin/env python3
"""Independently recompute every area-weighted crop-window drought record."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from spei_calendar_windows import SCALES, WINDOWS  # noqa: E402
from spei_crop_window_metrics import window_metrics  # noqa: E402
from build_spei_tile_crop_features import spans  # noqa: E402
from summarize_isimip3b_late_drought_crop_windows import frozen_support, sources  # noqa: E402

YEARS = tuple(range(2092, 2100))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


class Kahan:
    def __init__(self) -> None:
        self.total = 0.0; self.correction = 0.0

    def add(self, value: float) -> None:
        adjusted = value-self.correction; updated = self.total+adjusted
        self.correction = (updated-self.total)-adjusted; self.total = updated


def state() -> dict:
    return {"declared": Kahan(), "complete": Kahan(), "weighted": Kahan(), "clipped": Kahan(),
            "positive": 0, "complete_count": 0, "statuses": defaultdict(int)}


def update(value: dict, area: float, metric: dict) -> None:
    value["declared"].add(area); value["positive"] += 1; value["statuses"][metric["status"]] += 1
    if metric["status"] == "complete":
        value["complete"].add(area); value["weighted"].add(area*metric["spei_mean"])
        value["clipped"].add(area*bool(metric["tail_clipped_months"])); value["complete_count"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary_path = args.summary if args.summary.is_absolute() else ROOT/args.summary
    output = args.output if args.output.is_absolute() else ROOT/args.output
    require(not output.exists(), "fresh validation output required")
    summary = json.loads(summary_path.read_text())
    require(summary["status"] == "completed_pending_independent_validation", "summary status changed")
    pair_result_path = next(ROOT.rglob(f"five_esm_late_drought_20260921/{summary['esm']}_{summary['scenario']}/result.json"))
    pair_validation_path = pair_result_path.parent/"validation.json"
    pair_result = json.loads(pair_result_path.read_text()); pair_validation = json.loads(pair_validation_path.read_text())
    require(pair_validation["status"] == "passed" and digest(pair_result_path) == summary["sources"]["pair_result_sha256"], "upstream pair binding failed")
    cube = ROOT/pair_result["output"]["path"]
    require(digest(cube) == summary["sources"]["cube_sha256"], "SPEI cube changed")
    support = frozen_support(); calendars, weights, _ = sources()
    weight_lookup = weights.set_index(["crop", "lat", "lon_360", "irrigation"]).to_dict("index")
    with h5py.File(cube, "r") as handle:
        months = pd.DatetimeIndex(handle["month"][:].astype("datetime64[ns]"))
        values = handle["spei"][:]; clips = handle["cdf_clip_code"][:]
        require(tuple(handle["scale"][:]) == SCALES, "scale axis changed")
        require(np.array_equal(support.lat.to_numpy(), handle["latitude"][:][support.cell_id]), "latitude mapping changed")
        require(np.array_equal(support.lon_360.to_numpy(), np.mod(handle["longitude"][:], 360)[support.cell_id]), "longitude mapping changed")
    lookup = {(month.year, month.month): index for index, month in enumerate(months)}
    audit = defaultdict(state)
    for row in support.itertuples(index=False):
        for irrigation in ("firr", "noirr"):
            weight = weight_lookup[(row.crop, row.lat, row.lon_360, irrigation)]
            area = float(weight["irrigated_area_ha"] if irrigation == "firr" else weight["rainfed_area_ha"])
            if area <= 0:
                continue
            calendar = calendars[(row.crop, irrigation)]; i = calendar["lat"][row.lat]; j = calendar["lon"][row.lon_360]
            valid = bool(getattr(row, irrigation+"_calendar_valid"))
            for year in YEARS:
                intervals = spans(year, calendar["plant"][i,j], calendar["maturity"][i,j]) if valid else None
                for scale_index, scale in enumerate(SCALES):
                    for window in WINDOWS:
                        metric = ({"status": "invalid_calendar"} if intervals is None else
                                  window_metrics(values[scale_index, :, row.cell_id], clips[scale_index, :, row.cell_id],
                                                 lookup, *intervals[window]))
                        update(audit[(row.crop, year, window, scale, irrigation)], area, metric)
                        update(audit[(row.crop, year, window, scale, "combined")], area, metric)
    observed = {(r["crop"], r["harvest_year"], r["window"], r["scale_months"], r["irrigation"]): r for r in summary["records"]}
    require(len(observed) == len(summary["records"]) == len(audit) == 720 and set(observed) == set(audit), "summary factorial differs")
    maximum = 0.0; checks = 0
    for key, expected in audit.items():
        record = observed[key]; declared = expected["declared"].total; complete = expected["complete"].total
        mean = expected["weighted"].total/complete if complete else None
        clipped = expected["clipped"].total/complete if complete else None
        numerical = (("declared_area_ha", declared), ("complete_area_ha", complete),
                     ("complete_area_fraction", complete/declared), ("area_weighted_mean_spei", mean),
                     ("tail_clipped_area_fraction_of_complete", clipped))
        for name, value in numerical:
            require(value is not None and record[name] is not None, "unexpected missing aggregate")
            difference = abs(float(record[name])-float(value)); maximum = max(maximum, difference)
            require(math.isclose(float(record[name]), float(value), rel_tol=2e-12, abs_tol=2e-7), f"aggregate differs: {key} {name}")
            checks += 1
        require(record["positive_regime_cells"] == expected["positive"] and record["complete_regime_cells"] == expected["complete_count"], "aggregate cell count differs")
        require(record["status_counts"] == dict(sorted(expected["statuses"].items())), "aggregate status ledger differs")
        checks += 3
    result = {"schema": "isimip3b_late_drought_crop_window_validation_v1", "status": "passed",
              "role": "independent_full_area_aggregation_validation_not_yield_damage_or_scc",
              "summary_sha256": digest(summary_path), "records_recomputed": len(audit), "checks": checks,
              "maximum_numeric_absolute_difference": maximum,
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
              "gates": {"crop_window_exposure": True, "yield_response": False, "damage": False, "scc": False}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
