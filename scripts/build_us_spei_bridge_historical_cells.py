#!/usr/bin/env python3
"""Construct frozen-method historical SPEI for the 11 U.S. bridge cells only."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_spei_grid_chunk as engine  # noqa: E402
from spei_daily_stream import MonthlyAccumulator  # noqa: E402
from spei_monthly_engine import construct_monthly_spei  # noqa: E402
from spei_source_session import SourceVerificationSession  # noqa: E402

EXPECTED_CELLS_SHA256 = "2eda25a0328314001a7109f9f6aeb49fab1ffd5485f186c2f76327d0c84f33c8"
EXPECTED_SOURCE_PROVENANCE_SHA256 = "2a695e38329d1960a9a341137ac699219346528a50cd59e906fb4bb3b0bcacda"
EXPECTED_MONTHS = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
FALSE_GATES = ("historical_exact_361_county_support", "historical_county_spei_panel",
               "future_exact_361_county_support", "future_county_spei_panel",
               "bridge_to_nass_response", "fit_outcomes", "future_yield_projection",
               "causal_claim", "damage", "scc")


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_cells(path: Path) -> pd.DataFrame:
    require(digest(path) == EXPECTED_CELLS_SHA256, "11-cell inventory hash changed")
    cells = pd.read_csv(path)
    require(list(cells.columns) == ["latitude", "longitude_360", "native_lat_index", "native_lon_index"],
            "cell inventory schema changed")
    require(len(cells) == 11 and not cells.duplicated(["native_lat_index", "native_lon_index"]).any(),
            "exactly 11 unique cells required")
    require(np.array_equal(cells.latitude.to_numpy(), 89.75 - 0.5*cells.native_lat_index.to_numpy()),
            "latitude/index mapping changed")
    require(np.array_equal(cells.longitude_360.to_numpy(),
                           np.mod(-179.75 + 0.5*cells.native_lon_index.to_numpy(), 360)),
            "longitude/index mapping changed")
    return cells


def extract_block(records: list, cells: pd.DataFrame) -> tuple[list[pd.DatetimeIndex], list[np.ndarray], list[np.ndarray]]:
    by_variable = {record.variable: record for record in records}
    require(set(by_variable) == {"pr", "tas", "tasmin", "tasmax"}, "source block variable set changed")
    ii = xr.DataArray(cells.native_lat_index.to_numpy(dtype=np.int64), dims="cell")
    jj = xr.DataArray(cells.native_lon_index.to_numpy(dtype=np.int64), dims="cell")
    with ExitStack() as stack:
        datasets = {name: stack.enter_context(xr.open_dataset(record.path, engine="h5netcdf",
                                                               decode_times=True, mask_and_scale=True,
                                                               cache=False))
                    for name, record in by_variable.items()}
        dates = {}
        for name, dataset in datasets.items():
            engine._validate_isimip_schema(dataset, by_variable[name])
            dates[name] = engine._require_daily_dates(dataset.time.values, by_variable[name].start_date,
                                                       by_variable[name].end_date)
        require(all(dates[name].equals(dates["pr"]) for name in dates), "source block chronologies differ")
        arrays = {name: np.asarray(datasets[name][name].isel(lat=ii, lon=jj).values, dtype=np.float64)
                  for name in ("pr", "tasmin", "tasmax")}
    require(all(value.shape == (len(dates["pr"]), len(cells)) for value in arrays.values()),
            "extracted source shape changed")
    months, precipitation, et0 = [], [], []
    for year in sorted(set(dates["pr"].year)):
        positions = np.flatnonzero(dates["pr"].year == year)
        accumulator = MonthlyAccumulator(int(year), cells.latitude.to_numpy(dtype=np.float64))
        for source_position in positions:
            accumulator.add(dates["pr"][source_position], arrays["pr"][source_position]*86400.0,
                            arrays["tasmin"][source_position]-273.15,
                            arrays["tasmax"][source_position]-273.15)
        year_months, year_pr, year_et0, counts, day_counts = accumulator.finish()
        require(bool((counts == day_counts[:, None]).all()), f"incomplete daily triplet in {year}")
        require(not any(accumulator.audit.values()), f"unexpected daily audit count in {year}")
        months.append(year_months); precipitation.append(year_pr); et0.append(year_et0)
    return months, precipitation, et0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, default=ROOT / "config/us_spei_bridge_missing_cells_v1.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    cells_path = args.cells if args.cells.is_absolute() else ROOT / args.cells
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    require(not output_dir.exists(), "fresh output directory required")
    cells = load_cells(cells_path)
    source_provenance = ROOT / "data/provenance/isimip3a_daily_climate_plan.toml"
    require(digest(source_provenance) == EXPECTED_SOURCE_PROVENANCE_SHA256, "historical source provenance changed")
    inventory = engine.load_source_inventory("isimip", engine.load_contract(engine.DEFAULT_CONTRACT))
    started = time.perf_counter()
    session = SourceVerificationSession(engine.verify_source_files)
    source_validation = session.verify(inventory)
    hash_seconds = time.perf_counter() - started
    all_months, all_pr, all_et0 = [], [], []
    block_records = []
    for block in ("1981_1990", "1991_2000", "2001_2010", "2011_2019"):
        records = [record for record in inventory.records if record.block == block]
        months, precipitation, et0 = extract_block(records, cells)
        all_months.extend(months); all_pr.extend(precipitation); all_et0.extend(et0)
        block_records.append({"block": block, "objects": [record.public_identity() for record in records]})
        session.assert_unchanged(inventory)
    months = pd.DatetimeIndex(np.concatenate([part.values for part in all_months]))
    precipitation = np.concatenate(all_pr, axis=0)
    et0 = np.concatenate(all_et0, axis=0)
    require(months.equals(EXPECTED_MONTHS), "historical monthly chronology changed")
    require(precipitation.shape == et0.shape == (468, 11), "historical monthly shape changed")
    spei = construct_monthly_spei(months, precipitation, et0)
    require(spei.audit["fit_status_counts"]["valid"] == 396, "not all 11x3x12 frozen fits are valid")
    require(sum(value for key, value in spei.audit["fit_status_counts"].items() if key != "valid") == 0,
            "invalid historical SPEI fit")
    variables = {
        "precipitation_mm": (("month", "cell"), spei.precipitation_mm),
        "et0_hargreaves_mm": (("month", "cell"), spei.et0_mm),
        "water_balance_mm": (("month", "cell"), spei.water_balance_mm),
        "accumulated_water_balance_mm": (("scale", "month", "cell"), spei.accumulated_balance_mm),
        "glo_cdf_probability": (("scale", "month", "cell"), spei.cdf_probability),
        "spei": (("scale", "month", "cell"), spei.spei),
        "cdf_clip_code": (("scale", "month", "cell"), spei.cdf_clip_code),
        "glo_location_xi_mm": (("scale", "calendar_month", "cell"), spei.location_xi_mm),
        "glo_scale_alpha_mm": (("scale", "calendar_month", "cell"), spei.scale_alpha_mm),
        "glo_shape_kappa": (("scale", "calendar_month", "cell"), spei.shape_kappa),
        "calibration_finite_count": (("scale", "calendar_month", "cell"), spei.calibration_finite_count),
        "fit_status_code": (("scale", "calendar_month", "cell"), spei.fit_status_code),
        "latitude": (("cell",), cells.latitude.to_numpy()),
        "longitude": (("cell",), cells.longitude_360.to_numpy() - 360.0),
        "native_lat_index": (("cell",), cells.native_lat_index.to_numpy(dtype=np.int16)),
        "native_lon_index": (("cell",), cells.native_lon_index.to_numpy(dtype=np.int16)),
    }
    dataset = xr.Dataset(variables, coords={"month": months, "cell": np.arange(11),
                                           "scale": [1, 3, 6], "calendar_month": np.arange(1, 13)},
                         attrs={"schema": "us_spei_bridge_historical_cells_v1",
                                "scientific_role": "climate_only_exact_support_extension_no_county_panel_or_outcome_fit",
                                "source": inventory.source_id, "source_doi": inventory.dataset_doi,
                                "source_license": inventory.license,
                                "calibration": "1982-2011 calendar-month GLO/UBPWM frozen",
                                "pet": "Hargreaves-Samani",
                                **{f"gate_{name}": "false" for name in FALSE_GATES}})
    output_dir.mkdir(parents=True)
    output_path = output_dir / "historical_spei_11_cells.nc"
    engine.write_netcdf_atomic(output_path, dataset)
    result = {
        "schema": "us_spei_bridge_historical_cells_result_v1", "status": "completed_pending_independent_validation",
        "role": "climate_only_exact_support_extension_no_county_panel_or_outcome_fit",
        "cells": 11, "months": 468, "scales": [1, 3, 6], "fits": 396,
        "cell_inventory": {"path": str(cells_path.relative_to(ROOT)), "sha256": digest(cells_path)},
        "source_provenance": {"path": str(source_provenance.relative_to(ROOT)), "sha256": digest(source_provenance)},
        "source_validation": source_validation, "source_blocks": block_records,
        "hash_seconds": hash_seconds, "wall_seconds": time.perf_counter() - started,
        "audit": spei.audit,
        "output": {"path": str(output_path.relative_to(ROOT)), "bytes": output_path.stat().st_size,
                   "sha256": digest(output_path)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                           "sha256": digest(Path(__file__).resolve())},
        "helper_hashes": {name: digest(ROOT / f"scripts/{name}.py") for name in
                          ("spei_daily_stream", "spei_monthly_engine", "spei_construction_primitives", "spei_distribution")},
        "gates": {name: False for name in FALSE_GATES},
    }
    engine.write_json_atomic(output_dir / "result.json", result)
    print(json.dumps({"status": result["status"], "cells": 11, "months": 468, "fits": 396,
                      "output": result["output"], "audit": result["audit"]}))


if __name__ == "__main__":
    main()
