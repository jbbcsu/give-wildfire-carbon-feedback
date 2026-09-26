#!/usr/bin/env python3
"""Apply the source India crop-reporting-year rule to validated rice ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import calendar_months_for_report_year
from src.hultgren_rice_weather import build_rice_weather_basis_from_daily

KEYS = ["harvest_year", "native_lat_index", "native_lon_index"]
WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def validated_country_sets(
    crosswalk: Path, validation: Path, cells: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, object]]:
    checked = json.loads(validation.read_text(encoding="utf-8"))
    require(checked["status"].startswith("validated_"), "country crosswalk validation failed")
    require(checked["crosswalk"]["sha256"] == digest(crosswalk), "country crosswalk hash differs")
    frame = pd.read_parquet(
        crosswalk, columns=["native_lat_index", "native_lon_index", "region_key"]
    )
    frame["iso3"] = frame.region_key.str.slice(0, 3)
    # The source hierarchy uses the documented non-ISO placeholder ``KO-``
    # for Kosovo; retain it as a distinct non-India country token.
    require(frame.iso3.str.fullmatch(r"[A-Z-]{3}").all(), "invalid country prefix")
    grouped = (
        frame.groupby(["native_lat_index", "native_lon_index"], sort=False)
        .iso3.agg(lambda values: tuple(sorted(set(values))))
        .rename("country_candidates")
        .reset_index()
    )
    result = cells.merge(grouped, on=["native_lat_index", "native_lon_index"], how="left", validate="one_to_one")
    result["country_candidates"] = result.country_candidates.apply(
        lambda value: value if isinstance(value, tuple) else tuple()
    )
    result["india_candidate"] = result.country_candidates.apply(lambda values: "IND" in values)
    result["verified_india"] = result.country_candidates.apply(lambda values: values == ("IND",))
    result["country_status"] = np.select(
        [
            result.verified_india,
            result.india_candidate,
            result.country_candidates.apply(bool),
        ],
        ["verified_india", "mixed_country_including_india", "verified_not_india"],
        default="outside_all_author_region_geometry",
    )
    return result, checked


def load_target_weather(
    pr_paths: list[Path],
    tmin_paths: list[Path],
    tmax_paths: list[Path],
    targets: pd.DataFrame,
) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray], list[dict[str, object]]]:
    require(len(pr_paths) == len(tmin_paths) == len(tmax_paths), "weather block counts differ")
    rows = xr.DataArray(targets.native_lat_index.to_numpy(dtype=np.int64), dims="cell")
    cols = xr.DataArray(targets.native_lon_index.to_numpy(dtype=np.int64), dims="cell")
    dates: list[pd.DatetimeIndex] = []
    pieces: dict[str, list[np.ndarray]] = {"pr": [], "tasmin": [], "tasmax": []}
    sources = []
    for pr_path, tmin_path, tmax_path in zip(pr_paths, tmin_paths, tmax_paths, strict=True):
        block_dates: pd.DatetimeIndex | None = None
        for path, variable, units in (
            (pr_path, "pr", "kg m-2 s-1"),
            (tmin_path, "tasmin", "K"),
            (tmax_path, "tasmax", "K"),
        ):
            with xr.open_dataset(path, engine="h5netcdf", decode_times=True, cache=False) as dataset:
                require(variable in dataset, f"{variable} absent")
                require(dataset[variable].attrs.get("units") == units, f"{variable} units changed")
                require(
                    np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360))
                    and np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)),
                    f"{variable} grid changed",
                )
                current_dates = pd.DatetimeIndex(dataset.time.values).normalize()
                if block_dates is None:
                    block_dates = current_dates
                else:
                    require(block_dates.equals(current_dates), "weather dates differ within block")
                values = np.asarray(dataset[variable].isel(lat=rows, lon=cols).values, dtype=np.float64)
                require(values.shape == (len(current_dates), len(targets)), "target weather shape differs")
                pieces[variable].append(values)
            sources.append({"variable": variable, "path": str(path), "sha256": digest(path)})
        require(block_dates is not None, "empty weather block")
        dates.append(block_dates)
    combined_dates = dates[0].append(dates[1:])
    require(combined_dates.is_monotonic_increasing and not combined_dates.has_duplicates, "weather blocks overlap or are unordered")
    arrays = {name: np.concatenate(values, axis=0) for name, values in pieces.items()}
    arrays["pr"] *= 86_400.0
    arrays["tasmin"] -= 273.15
    arrays["tasmax"] -= 273.15
    require(np.isfinite(np.column_stack(list(arrays.values()))).all(), "nonfinite target weather")
    require(np.all(arrays["pr"] >= -1e-10), "negative target precipitation")
    require(np.all(arrays["tasmin"] <= arrays["tasmax"] + 5e-5), "target Tmin exceeds Tmax")
    arrays["pr"] = np.maximum(arrays["pr"], 0.0)
    return combined_dates, arrays, sources


def rebuilt_basis(
    row: pd.Series,
    target_position: int,
    dates: pd.DatetimeIndex,
    arrays: dict[str, np.ndarray],
) -> dict[str, float]:
    lookup = {value.date(): index for index, value in enumerate(dates)}
    records = []
    for year, month in calendar_months_for_report_year(
        int(row.harvest_year), int(row.plant_month), int(row.harvest_month), "IND"
    ):
        start = pd.Timestamp(year=year, month=month, day=1)
        end = start + pd.offsets.MonthEnd(0)
        for stamp in pd.date_range(start, end, freq="D"):
            position = lookup[stamp.date()]
            records.append(
                (
                    date(stamp.year, stamp.month, stamp.day),
                    arrays["pr"][position, target_position],
                    arrays["tasmin"][position, target_position],
                    arrays["tasmax"][position, target_position],
                )
            )
    basis = build_rice_weather_basis_from_daily(
        records,
        report_year=int(row.harvest_year),
        plant_month=int(row.plant_month),
        harvest_month=int(row.harvest_month),
        iso="IND",
    )
    return {
        "gdd": basis.gdd, "kdd": basis.kdd, "tmin": basis.tmin,
        **{f"prcp_poly_1_bin{i}": value for i, value in enumerate(basis.prcp_poly_1_bins, 1)},
        **{f"prcp_poly_2_bin{i}": value for i, value in enumerate(basis.prcp_poly_2_bins, 1)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", action="append", type=Path, required=True)
    parser.add_argument("--country-crosswalk", type=Path, required=True)
    parser.add_argument("--country-crosswalk-validation", type=Path, required=True)
    parser.add_argument("--pr", action="append", type=Path, required=True)
    parser.add_argument("--tasmin", action="append", type=Path, required=True)
    parser.add_argument("--tasmax", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists() and not args.receipt.exists(), "fresh outputs required")

    first = pd.read_parquet(
        args.basis[0], columns=["native_lat_index", "native_lon_index", "plant_month", "harvest_month"]
    ).drop_duplicates(["native_lat_index", "native_lon_index"])
    cells, country_validation = validated_country_sets(
        args.country_crosswalk, args.country_crosswalk_validation, first
    )
    cells["reporting_year_rule_sensitive"] = cells.apply(
        lambda row: calendar_months_for_report_year(2000, int(row.plant_month), int(row.harvest_month), "IND")
        != calendar_months_for_report_year(2000, int(row.plant_month), int(row.harvest_month), "USA"),
        axis=1,
    )
    ambiguous_sensitive = cells.india_candidate & ~cells.verified_india & cells.reporting_year_rule_sensitive
    require(not ambiguous_sensitive.any(), "India-border ambiguity affects reporting-year-sensitive cells")
    targets = cells.loc[cells.verified_india & cells.reporting_year_rule_sensitive].copy()
    require(not targets.empty, "no verified India reporting-year corrections")
    targets = targets.sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    target_lookup = {
        (int(row.native_lat_index), int(row.native_lon_index)): position
        for position, row in targets.iterrows()
    }
    dates, arrays, weather_sources = load_target_weather(
        args.pr, args.tasmin, args.tasmax, targets
    )

    args.output_dir.mkdir(parents=True)
    output_records = []
    corrections = []
    total_rows = 0
    total_corrected = 0
    for path in args.basis:
        build_path = path.with_suffix(path.suffix + ".result.json")
        build = json.loads(build_path.read_text(encoding="utf-8"))
        require(build["output"]["sha256"] == digest(path), f"basis hash differs: {path}")
        frame = pd.read_parquet(path)
        require(np.isfinite(frame[WEATHER].to_numpy()).all(), f"nonfinite input basis: {path}")
        frame["india_reporting_year_exception_applied"] = False
        affected = frame.apply(
            lambda row: (int(row.native_lat_index), int(row.native_lon_index)) in target_lookup,
            axis=1,
        )
        for index in frame.index[affected]:
            row = frame.loc[index]
            cell_key = (int(row.native_lat_index), int(row.native_lon_index))
            corrected = rebuilt_basis(row, target_lookup[cell_key], dates, arrays)
            record = {
                "calendar_branch": row.calendar_branch,
                **{key: int(row[key]) for key in KEYS},
                "plant_month": int(row.plant_month),
                "harvest_month": int(row.harvest_month),
                "original_first_calendar_year": int(row.harvest_year) - 1,
                "corrected_first_calendar_year": int(row.harvest_year),
            }
            for column in WEATHER:
                original = float(row[column])
                frame.at[index, column] = corrected[column]
                record[f"original_{column}"] = original
                record[f"corrected_{column}"] = corrected[column]
                record[f"delta_{column}"] = corrected[column] - original
            frame.at[index, "india_reporting_year_exception_applied"] = True
            corrections.append(record)
        output = args.output_dir / path.name
        partial = output.with_suffix(output.suffix + ".partial")
        pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), partial, compression="zstd")
        os.replace(partial, output)
        corrected_rows = int(frame.india_reporting_year_exception_applied.sum())
        total_rows += len(frame)
        total_corrected += corrected_rows
        output_records.append(
            {
                "input": {"path": str(path), "sha256": digest(path), "rows": len(frame)},
                "output": {"path": str(output), "sha256": digest(output), "bytes": output.stat().st_size, "rows": len(frame)},
                "calendar_branch": str(frame.calendar_branch.iloc[0]),
                "corrected_cell_years": corrected_rows,
            }
        )

    correction_frame = pd.DataFrame(corrections).sort_values(
        ["calendar_branch", "harvest_year", "native_lat_index", "native_lon_index"]
    )
    correction_path = args.output_dir / "india_reporting_year_cell_diagnostics.parquet"
    correction_frame.to_parquet(correction_path, index=False, compression="zstd")
    expected_corrections = len(targets) * sum(
        int(record["input"]["rows"] / first.shape[0]) for record in output_records
    )
    require(total_corrected == expected_corrections, "corrected row count differs")
    receipt = {
        "schema": "hultgren_rice_india_reporting_year_correction/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "india_reporting_year_exception_applied_to_verified_cells",
        "country_crosswalk": {
            "path": str(args.country_crosswalk), "sha256": digest(args.country_crosswalk),
            "validation": str(args.country_crosswalk_validation),
            "validation_sha256": digest(args.country_crosswalk_validation),
            "validation_status": country_validation["status"],
        },
        "country_rule_audit": {
            "retained_cells": len(cells),
            "verified_india_cells": int(cells.verified_india.sum()),
            "mixed_country_including_india_cells": int((cells.country_status == "mixed_country_including_india").sum()),
            "outside_all_author_region_geometry_cells": int((cells.country_status == "outside_all_author_region_geometry").sum()),
            "reporting_year_rule_sensitive_cells": int(cells.reporting_year_rule_sensitive.sum()),
            "verified_india_reporting_year_rule_sensitive_cells": len(targets),
            "ambiguous_india_reporting_year_rule_sensitive_cells": int(ambiguous_sensitive.sum()),
            "corrected_cell_coordinates": targets[["native_lat_index", "native_lon_index", "plant_month", "harvest_month"]].to_dict("records"),
        },
        "weather_sources": weather_sources,
        "outputs": output_records,
        "cell_diagnostics": {
            "path": str(correction_path), "sha256": digest(correction_path),
            "bytes": correction_path.stat().st_size, "rows": len(correction_frame),
        },
        "counts": {"input_and_output_rows": total_rows, "corrected_cell_years": total_corrected},
        "transformation": (
            "only verified-India cells whose source IND and non-IND month assignments differ are rebuilt; "
            "all other cell-years retain the prior basis exactly"
        ),
        "claim_gates": {
            "india_reporting_year_exception_applied": True,
            "season_or_irrigation_weights_used": False,
            "published_response_evaluated": False,
            "damage_or_scc_validated": False,
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "country_rule_audit": receipt["country_rule_audit"], "counts": receipt["counts"]}, indent=2))


if __name__ == "__main__":
    main()
