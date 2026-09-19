#!/usr/bin/env python3
"""Outcome-free crop-window allocation of the validated GFDL SPEI pilot."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from spei_calendar_windows import SCALES, WINDOWS  # noqa: E402
from spei_crop_window_metrics import window_metrics  # noqa: E402
from build_spei_tile_crop_features import spans  # noqa: E402


INPUT = ROOT / "data/interim/gfdl_future_spei_boundary_pilot_v2_20260919/gfdl_boundary_spei.nc"
INPUT_SHA = "b01acdffff4f69c735ca07f24f48415a134c1d59288dc85804aae0ffb84cfad8"
VALIDATION = ROOT / "data/interim/gfdl_future_spei_boundary_validation_20260919/result.json"
VALIDATION_SHA = "a72b37720af61ce0132d6cac596d4402c91741cd66d66c79c06cbaa0813c9957"
PARTITION = ROOT / "data/interim/spei_crop_key_partitions_20260908/block_00000.parquet"
PARTITION_SHA = "3b08339e3ef1482ec5464b1354388026d051e050ec2fb396d3f6135117290ba9"
COVERAGE = ROOT / "data/interim/spei_calendar_coverage_20260908/result.json"
COVERAGE_SHA = "70744aadd64e2aed35d693b41733ca45e5045e233a12bfde9f1aeb824b22e83c"
PROTOCOL = ROOT / "GFDL_FUTURE_SPEI_CROP_WINDOW_PROTOCOL_20260919.md"
SCENARIOS = ("ssp126", "ssp370", "ssp585")
YEARS = tuple(range(2015, 2021))


def sha(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def locked_support() -> pd.DataFrame:
    if sha(PARTITION) != PARTITION_SHA:
        raise ValueError("crop-support partition changed")
    frame = pq.read_table(PARTITION).to_pandas()
    fields = ["crop", "lat", "lon_360", "cell_id", "noirr_calendar_valid", "firr_calendar_valid"]
    support = frame[fields].drop_duplicates().sort_values(["crop", "lat", "lon_360"]).reset_index(drop=True)
    if support.duplicated(["crop", "lat", "lon_360"]).any() or len(support) != 557:
        raise ValueError("unique crop/cell support changed")
    for field in ("noirr_calendar_valid", "firr_calendar_valid"):
        if support.groupby(["crop", "lat", "lon_360"])[field].nunique().max() != 1:
            raise ValueError("calendar validity changes across historical years")
    return support


def source_inputs() -> tuple[dict, dict]:
    if sha(COVERAGE) != COVERAGE_SHA:
        raise ValueError("calendar coverage receipt changed")
    coverage = json.loads(COVERAGE.read_text())
    calendars: dict = {}
    weights = None
    bindings = []
    for binding in coverage["bindings"]:
        if binding["role"] not in {"calendar", "weights"}:
            continue
        path = ROOT / binding["path"]
        algorithm = "sha512" if binding["role"] == "calendar" else "sha256"
        if sha(path, algorithm) != binding[algorithm]:
            raise ValueError("calendar/weight source changed")
        bindings.append(binding)
        if binding["role"] == "weights":
            frame = pq.read_table(path, columns=["crop", "lat", "lon_360", "irrigation", "area_share"]).to_pandas()
            weights = frame.set_index(["crop", "lat", "lon_360", "irrigation"]).area_share.to_dict()
        else:
            crop, regime = path.stem.split("_")[-2:]
            with h5py.File(path, "r") as handle:
                calendars[(crop, regime)] = {
                    "lat": {float(value): index for index, value in enumerate(handle["lat"][:])},
                    "lon": {float(value) % 360: index for index, value in enumerate(handle["lon"][:])},
                    "plant": handle["planting_day"][:],
                    "maturity": handle["maturity_day"][:],
                }
    if weights is None or set(calendars) != {(crop, regime) for crop in ("mai", "soy") for regime in ("noirr", "firr")}:
        raise ValueError("calendar/weight registry incomplete")
    return {"calendars": calendars, "weights": weights}, {"coverage": coverage, "bindings": bindings}


def schema(kind: str) -> pa.Schema:
    common = [
        ("scenario", pa.string()), ("crop", pa.string()), ("lat", pa.float64()),
        ("lon_360", pa.float64()), ("harvest_year", pa.int64()), ("window", pa.string()),
        ("scale", pa.int64()), ("status", pa.string()), ("spei_mean", pa.float64()),
        ("month_end_spei_mean", pa.float64()),
    ]
    if kind == "regime":
        return pa.schema(common + [
            ("irrigation", pa.string()), ("area_share", pa.float64()),
            ("window_start", pa.string()), ("window_end", pa.string()),
            ("overlap_days", pa.int64()), ("month_end_days", pa.int64()),
            ("source_months", pa.int64()), ("tail_clipped_months", pa.int64()),
        ])
    return pa.schema(common + [
        ("weighted_window_days", pa.float64()), ("weighted_month_end_days", pa.float64()),
        ("any_tail_clipped", pa.bool_()),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out_dir = (args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir).resolve()
    if out_dir.exists():
        raise ValueError("fresh output directory required")
    if sha(INPUT) != INPUT_SHA or sha(VALIDATION) != VALIDATION_SHA:
        raise ValueError("validated GFDL SPEI input changed")
    validation = json.loads(VALIDATION.read_text())
    if validation["status"] != "passed" or validation["output_sha256"] != INPUT_SHA:
        raise ValueError("upstream independent validation not passed")
    support = locked_support()
    sources, source_receipt = source_inputs()
    with xr.open_dataset(INPUT, engine="h5netcdf", cache=False) as dataset:
        if tuple(dataset.scenario.values.astype(str)) != SCENARIOS or tuple(dataset.scale.values.tolist()) != SCALES:
            raise ValueError("input scenario/scale axes changed")
        months = pd.DatetimeIndex(dataset.month.values)
        values = dataset.spei.values
        clips = dataset.cdf_clip_code.values
        positions = {
            (float(lat), float(lon) % 360): index
            for index, (lat, lon) in enumerate(zip(dataset.latitude.values, dataset.longitude.values))
        }
    if len(positions) != 512 or any((row.lat, row.lon_360) not in positions for row in support.itertuples()):
        raise ValueError("support does not map exactly to input cells")
    lookup = {(month.year, month.month): index for index, month in enumerate(months)}
    out_dir.mkdir(parents=True)
    writers = {kind: pq.ParquetWriter(out_dir / f"{kind}.parquet", schema(kind), compression="zstd") for kind in ("regime", "combined")}
    counts = Counter()
    try:
        for scenario_index, scenario in enumerate(SCENARIOS):
            for year in YEARS:
                output = {"regime": [], "combined": []}
                for row in support.itertuples(index=False):
                    base = {"scenario": scenario, "crop": row.crop, "lat": row.lat, "lon_360": row.lon_360, "harvest_year": year}
                    regimes = []
                    for irrigation in ("noirr", "firr"):
                        share = float(sources["weights"][(row.crop, row.lat, row.lon_360, irrigation)])
                        if share <= 0:
                            continue
                        calendar = sources["calendars"][(row.crop, irrigation)]
                        i, j = calendar["lat"][row.lat], calendar["lon"][row.lon_360]
                        valid = bool(getattr(row, irrigation + "_calendar_valid"))
                        dates = spans(year, calendar["plant"][i, j], calendar["maturity"][i, j]) if valid else None
                        regimes.append((irrigation, share, dates))
                    if not math.isclose(math.fsum(item[1] for item in regimes), 1.0, rel_tol=0, abs_tol=1e-10):
                        raise ValueError("positive irrigation shares do not sum to one")
                    cell = positions[(row.lat, row.lon_360)]
                    for window in WINDOWS:
                        for scale_index, scale in enumerate(SCALES):
                            pieces = []
                            for irrigation, share, dates in regimes:
                                item = {**base, "window": window, "scale": scale, "irrigation": irrigation, "area_share": share}
                                if dates is None:
                                    item["status"] = "invalid_calendar"
                                else:
                                    start, end = dates[window]
                                    item.update(window_start=start.isoformat(), window_end=end.isoformat())
                                    item.update(window_metrics(values[scenario_index, scale_index, :, cell], clips[scenario_index, scale_index, :, cell], lookup, start, end))
                                pieces.append(item); output["regime"].append(item); counts[("regime", item["status"])] += 1
                            combined = {**base, "window": window, "scale": scale}
                            if pieces and all(item["status"] == "complete" for item in pieces):
                                combined.update(
                                    status="complete",
                                    spei_mean=math.fsum(item["area_share"] * item["spei_mean"] for item in pieces),
                                    month_end_spei_mean=(math.fsum(item["area_share"] * item["month_end_spei_mean"] for item in pieces) if all(item["month_end_spei_mean"] is not None for item in pieces) else None),
                                    weighted_window_days=math.fsum(item["area_share"] * item["overlap_days"] for item in pieces),
                                    weighted_month_end_days=math.fsum(item["area_share"] * item["month_end_days"] for item in pieces),
                                    any_tail_clipped=any(item["tail_clipped_months"] for item in pieces),
                                )
                            else:
                                combined["status"] = "incomplete_positive_regime"
                            output["combined"].append(combined); counts[("combined", combined["status"])] += 1
                for kind in output:
                    writers[kind].write_table(pa.Table.from_pylist(output[kind], schema=schema(kind)))
    finally:
        for writer in writers.values():
            writer.close()
    records = []
    for kind in ("regime", "combined"):
        path = out_dir / f"{kind}.parquet"
        records.append({"kind": kind, "path": str(path.relative_to(ROOT)), "rows": pq.ParquetFile(path).metadata.num_rows, "bytes": path.stat().st_size, "sha256": sha(path)})
    combined = pq.read_table(out_dir / "combined.parquet", columns=["scenario", "crop", "window", "scale", "status", "spei_mean"]).to_pandas()
    summary = (
        combined.loc[combined.status.eq("complete")]
        .groupby(["scenario", "crop", "window", "scale"], sort=True).spei_mean
        .agg(["count", "mean"]).reset_index().to_dict("records")
    )
    result = {
        "schema": "gfdl_future_spei_crop_windows_v1", "status": "completed_pending_independent_validation",
        "role": "outcome_free_engineering_not_future_yield_damage_or_scc",
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha(PROTOCOL)},
        "input": {"path": str(INPUT.relative_to(ROOT)), "sha256": INPUT_SHA, "validation_sha256": VALIDATION_SHA},
        "support": {"path": str(PARTITION.relative_to(ROOT)), "sha256": PARTITION_SHA, "crop_cell_pairs": len(support), "crops": support.groupby("crop").size().to_dict()},
        "source_receipt": source_receipt, "years": list(YEARS), "scenarios": list(SCENARIOS),
        "records": records, "counts": [{"ledger": key[0], "status": key[1], "rows": value} for key, value in sorted(counts.items())],
        "descriptive_unweighted_summary": summary,
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha(Path(__file__).resolve())},
        "gates": {"outcome_used": False, "response": False, "causal": False, "damage": False, "scc": False},
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "records": records, "counts": result["counts"]}))


if __name__ == "__main__":
    main()
