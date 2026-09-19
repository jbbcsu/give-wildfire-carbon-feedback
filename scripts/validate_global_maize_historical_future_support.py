#!/usr/bin/env python3
"""Independent arithmetic and raw-source audit of weather-domain support output."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ("precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c",
            "stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm")
SEASON = FEATURES[:6]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(a, b):
    if not math.isclose(float(a), float(b), rel_tol=0, abs_tol=2e-12):
        raise ValueError(f"audit mismatch: {a} != {b}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result_path, out = args.result.resolve(), args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        parser.error("fresh ignored audit output required")
    result = json.loads(result_path.read_text())
    bounds_path = result_path.parent / "historical_cell_feature_bounds.npz"
    if sha(bounds_path) != result["bounds_sha256"] or tuple(result["features"]) != FEATURES:
        raise ValueError("saved bounds or feature order changed")
    for source in result["historical_inputs"]:
        path = ROOT / source["path"]
        if sha(path) != source["sha256"]:
            raise ValueError("historical source changed")
    saved = np.load(bounds_path)
    keys = list(zip(saved["lat"].astype(float), saved["lon_360"].astype(float)))
    if len(keys) != len(set(keys)) or len(keys) != result["matched_cells"]:
        raise ValueError("saved support keys invalid")
    index = {key: i for i, key in enumerate(keys)}
    hectares = saved["hectares"].astype(float)
    close(hectares.sum(), result["matched_area_ha"])
    lower, upper, p05, p95 = (saved[x] for x in ("min", "max", "p05", "p95"))
    if not (np.all(lower <= p05) and np.all(p05 <= p95) and np.all(p95 <= upper)):
        raise ValueError("historical support bounds invalid")
    panels = result["annual"]
    identities = {(x["esm"], x["scenario"], x["year"]) for x in panels}
    if len(panels) != 72 or len(identities) != 72:
        raise ValueError("annual panel identities incomplete")
    raw_rows = 0
    for record in panels:
        esm, scenario, year = record["esm"], record["scenario"], record["year"]
        directory = ROOT / "data/interim" / f"isimip3b_global_{esm}_{scenario}_{year}_mai_noirr_full_20260917"
        manifest_path = directory / "global_manifest.json"
        if sha(manifest_path) != record["source_global_manifest_sha256"]:
            raise ValueError("future manifest changed")
        manifest = json.loads(manifest_path.read_text())
        values = np.full((len(keys), len(FEATURES)), np.nan)
        for tile in manifest["tiles"]:
            folder = directory / f"lat{tile['lat_start']:03d}_{tile['lat_stop']:03d}"
            season_path, stage_path = folder / "season.parquet", folder / "stages.parquet"
            if sha(season_path) != tile["season_sha256"] or sha(stage_path) != tile["stages_sha256"]:
                raise ValueError("future tile changed")
            season = pd.read_parquet(season_path, columns=["lat", "lon_360", *SEASON])
            stages = pd.read_parquet(stage_path, columns=["lat", "lon_360", "stage_id", "precip_mm"])
            raw_rows += len(season) + len(stages)
            for row in season.itertuples(index=False):
                pos = index.get((float(row.lat), float(row.lon_360)))
                if pos is not None:
                    if np.isfinite(values[pos, 0]):
                        raise ValueError("duplicate future season key")
                    values[pos, :6] = [float(getattr(row, x)) for x in SEASON]
            for row in stages.itertuples(index=False):
                pos = index.get((float(row.lat), float(row.lon_360)))
                if pos is not None:
                    col = 5 + int(row.stage_id)
                    if not 6 <= col <= 8 or np.isfinite(values[pos, col]):
                        raise ValueError("duplicate or invalid future stage key")
                    values[pos, col] = float(row.precip_mm)
        if not np.isfinite(values).all():
            raise ValueError("future support incomplete")
        masks = {"below_min": values < lower, "above_max": values > upper,
                 "outside_5_95": (values < p05) | (values > p95)}
        for label, mask in masks.items():
            for column, feature in enumerate(FEATURES):
                observed = hectares[mask[:, column]].sum() / hectares.sum()
                close(observed, record["feature_area_fractions"][label][feature])
        close(hectares[np.any(masks["below_min"] | masks["above_max"], axis=1)].sum() / hectares.sum(),
              record["any_feature_outside_minmax_area_fraction"])
    for esm, scenarios in result["esm_scenario_summary"].items():
        for scenario, summary in scenarios.items():
            group = [x for x in panels if x["esm"] == esm and x["scenario"] == scenario]
            if len(group) != 8:
                raise ValueError("summary group incomplete")
            for label in ("below_min", "above_max", "outside_5_95"):
                for feature in FEATURES:
                    close(math.fsum(x["feature_area_fractions"][label][feature] for x in group) / 8,
                          summary["mean_area_fraction"][label][feature])
            close(math.fsum(x["any_feature_outside_minmax_area_fraction"] for x in group) / 8,
                  summary["any_feature_outside_minmax_mean_area_fraction"])
    audit = {"status": "passed", "result_sha256": sha(result_path),
             "bounds_sha256": sha(bounds_path), "annual_panels": len(panels),
             "raw_future_rows_rechecked": raw_rows, "matched_cells": len(keys),
             "checks": ["all source hashes", "all raw future tiles", "all annual weighted fractions",
                        "all eight-year summary arithmetic", "saved historical bound ordering"]}
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
