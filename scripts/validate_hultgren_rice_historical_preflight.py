#!/usr/bin/env python3
"""Independently validate paired, unweighted ri1 historical basis branches."""

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
from src.hultgren_rice_response import PublishedRiceEstimate
from src.hultgren_rice_weather import build_rice_weather_basis_from_daily

KEYS = ["harvest_year", "native_lat_index", "native_lon_index"]
WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]
CALENDAR = ["plant_month", "harvest_month", "season_months", "cross_year"]
PROHIBITED_COLUMN_PARTS = ("area", "weight", "production", "value", "damage", "scc", "yield")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_basis(path: Path, branch: str) -> tuple[pd.DataFrame, dict[str, object], dict[str, object]]:
    receipt_path = path.with_suffix(path.suffix + ".result.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(
        receipt["status"] == "complete_unweighted_rice_calendar_branch_basis_not_response_damage_or_scc",
        f"basis build status failed: {path}",
    )
    require(receipt["calendar_branch"] == branch, f"basis branch differs: {path}")
    require(receipt["output"]["sha256"] == digest(path), f"basis hash differs: {path}")
    require(
        receipt["support_audit"]["annual_mirca_values_used_as_weights"] is False,
        f"MIRCA values were weighted: {path}",
    )
    schema_columns = pq.read_schema(path).names
    prohibited = [
        column for column in schema_columns
        if any(part in column.lower() for part in PROHIBITED_COLUMN_PARTS)
    ]
    require(not prohibited, f"prohibited weighted/impact columns present: {prohibited}")
    columns = ["calendar_branch", "complete", *KEYS, *CALENDAR, *WEATHER]
    frame = pd.read_parquet(path, columns=columns)
    require(frame.calendar_branch.eq(branch).all(), f"row branch differs: {path}")
    require(frame.complete.all(), f"incomplete basis rows: {path}")
    require(frame.season_months.between(6, 12, inclusive="both").all(), f"season domain differs: {path}")
    require(np.isfinite(frame[WEATHER].to_numpy()).all(), f"nonfinite weather basis: {path}")
    require(len(frame) == len(frame.drop_duplicates(KEYS)), f"duplicate cell-years: {path}")
    source = {
        "path": str(path), "sha256": digest(path), "rows": len(frame),
        "build_receipt": str(receipt_path), "build_receipt_sha256": digest(receipt_path),
    }
    return frame.sort_values(KEYS).reset_index(drop=True), source, receipt


def direct_weather_check(frame: pd.DataFrame, source: dict[str, object], samples: int) -> dict[str, object]:
    paths = {
        name: ROOT / source["sources"][name]["path"]
        for name in ("pr", "tasmin", "tasmax")
    }
    years = source["harvest_years"]
    candidates = frame.loc[frame.harvest_year.between(years[0], years[1], inclusive="both")]
    positions = np.linspace(0, len(candidates) - 1, min(samples, len(candidates)), dtype=int)
    selected = candidates.iloc[positions]
    maximum_errors = {column: 0.0 for column in WEATHER}
    with xr.open_dataset(paths["pr"], engine="h5netcdf", decode_times=True, cache=False) as pr, xr.open_dataset(
        paths["tasmin"], engine="h5netcdf", decode_times=True, cache=False
    ) as tmin, xr.open_dataset(paths["tasmax"], engine="h5netcdf", decode_times=True, cache=False) as tmax:
        dates = pd.DatetimeIndex(pr.time.values).normalize()
        require(dates.equals(pd.DatetimeIndex(tmin.time.values).normalize()), "direct-check pr/tasmin dates differ")
        require(dates.equals(pd.DatetimeIndex(tmax.time.values).normalize()), "direct-check pr/tasmax dates differ")
        lookup = {value.date(): index for index, value in enumerate(dates)}
        for row in selected.itertuples(index=False):
            month_keys = calendar_months_for_report_year(
                int(row.harvest_year), int(row.plant_month), int(row.harvest_month), "USA"
            )
            records = []
            for year, month in month_keys:
                month_dates = pd.date_range(f"{year:04d}-{month:02d}-01", periods=1, freq="MS")
                end = month_dates[0] + pd.offsets.MonthEnd(0)
                for stamp in pd.date_range(month_dates[0], end, freq="D"):
                    position = lookup[stamp.date()]
                    i, j = int(row.native_lat_index), int(row.native_lon_index)
                    records.append(
                        (
                            date(stamp.year, stamp.month, stamp.day),
                            float(pr.pr.isel(time=position, lat=i, lon=j).values) * 86_400.0,
                            float(tmin.tasmin.isel(time=position, lat=i, lon=j).values) - 273.15,
                            float(tmax.tasmax.isel(time=position, lat=i, lon=j).values) - 273.15,
                        )
                    )
            rebuilt = build_rice_weather_basis_from_daily(
                records,
                report_year=int(row.harvest_year),
                plant_month=int(row.plant_month),
                harvest_month=int(row.harvest_month),
                iso="USA",
            )
            expected = {
                "gdd": rebuilt.gdd, "kdd": rebuilt.kdd, "tmin": rebuilt.tmin,
                **{f"prcp_poly_1_bin{i}": value for i, value in enumerate(rebuilt.prcp_poly_1_bins, 1)},
                **{f"prcp_poly_2_bin{i}": value for i, value in enumerate(rebuilt.prcp_poly_2_bins, 1)},
            }
            for column, value in expected.items():
                maximum_errors[column] = max(maximum_errors[column], abs(float(getattr(row, column)) - value))
    require(max(maximum_errors.values()) <= 1e-7, f"direct weather reconstruction differs: {maximum_errors}")
    return {"sample_rows": len(selected), "maximum_absolute_error": maximum_errors}


def unweighted_summary(values_by_column: dict[str, list[np.ndarray]]) -> dict[str, dict[str, float]]:
    result = {}
    for column in WEATHER:
        values = np.concatenate(values_by_column[column])
        result[column] = {
            "minimum": float(values.min()),
            "p01": float(np.quantile(values, 0.01)),
            "median": float(np.quantile(values, 0.50)),
            "p99": float(np.quantile(values, 0.99)),
            "maximum": float(values.max()),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--noirr-basis", action="append", type=Path, required=True)
    parser.add_argument("--firr-basis", action="append", type=Path, required=True)
    parser.add_argument("--coefficients", type=Path, required=True)
    parser.add_argument("--covariance", type=Path, required=True)
    parser.add_argument("--comparison-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--direct-samples-per-file", type=int, default=2)
    args = parser.parse_args()
    partial = args.comparison_output.with_suffix(args.comparison_output.suffix + ".partial")
    require(
        not args.comparison_output.exists() and not args.receipt.exists() and not partial.exists(),
        "fresh outputs required",
    )
    require(args.direct_samples_per_file > 0, "direct sample count must be positive")
    require(len(args.noirr_basis) == len(args.firr_basis), "branch chunk counts differ")

    estimate = PublishedRiceEstimate.from_exports(args.coefficients, args.covariance)
    term_factors = {
        factor.removeprefix("c.")
        for term in estimate.terms for factor in term.split("#")
    }
    require(set(WEATHER) <= term_factors, "published response does not contain every rice weather primitive")
    require(
        {"ln_gdppc", "irrigated_share", "lr_tmax_crop", "pbarcut_gdd", "pbarcut_kdd", "pbarcut_prcp", "pbarcut_tmin"} <= term_factors,
        "published response moderator support differs",
    )

    direct_checks: list[dict[str, object]] = []
    sources: dict[str, list[dict[str, object]]] = {"ri1_noirr": [], "ri1_firr": []}
    summaries = {
        branch: {column: [] for column in WEATHER}
        for branch in ("ri1_noirr", "ri1_firr")
    }
    delta_values = {column: [] for column in WEATHER}
    total_rows = 0
    calendar_equal_rows = 0
    weather_different_rows = 0
    previous_last_key: tuple[int, int, int] | None = None
    writer: pq.ParquetWriter | None = None
    args.comparison_output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for noirr_path, firr_path in zip(args.noirr_basis, args.firr_basis, strict=True):
            noirr, noirr_source, noirr_build = load_basis(noirr_path, "ri1_noirr")
            firr, firr_source, firr_build = load_basis(firr_path, "ri1_firr")
            sources["ri1_noirr"].append(noirr_source)
            sources["ri1_firr"].append(firr_source)
            require(len(noirr) == len(firr), "paired branch row counts differ")
            require(noirr[KEYS].equals(firr[KEYS]), "paired branch cell-year support differs")
            first_key = tuple(int(value) for value in noirr.loc[0, KEYS])
            last_key = tuple(int(value) for value in noirr.loc[len(noirr) - 1, KEYS])
            require(previous_last_key is None or first_key > previous_last_key, "branch chunks overlap or are unordered")
            previous_last_key = last_key
            direct_checks.append({"basis": str(noirr_path), **direct_weather_check(noirr, noirr_build, args.direct_samples_per_file)})
            direct_checks.append({"basis": str(firr_path), **direct_weather_check(firr, firr_build, args.direct_samples_per_file)})

            output = noirr[KEYS].copy()
            output["in_both_branches"] = True
            output["calendar_equal"] = np.ones(len(noirr), dtype=bool)
            for column in CALENDAR:
                left = noirr[column].to_numpy()
                right = firr[column].to_numpy()
                output["calendar_equal"] &= left == right
                output[f"{column}_noirr"] = left
                output[f"{column}_firr"] = right
            output["any_weather_difference"] = np.zeros(len(noirr), dtype=bool)
            for column in WEATHER:
                left = noirr[column].to_numpy(dtype=np.float64)
                right = firr[column].to_numpy(dtype=np.float64)
                difference = right - left
                summaries["ri1_noirr"][column].append(left.copy())
                summaries["ri1_firr"][column].append(right.copy())
                delta_values[column].append(difference.copy())
                output[f"delta_firr_minus_noirr_{column}"] = difference
                output["any_weather_difference"] |= difference != 0.0
            table = pa.Table.from_pandas(output, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(partial, table.schema, compression="zstd")
            writer.write_table(table)
            total_rows += len(output)
            calendar_equal_rows += int(output.calendar_equal.sum())
            weather_different_rows += int(output.any_weather_difference.sum())
            del noirr, firr, output, table
    finally:
        if writer is not None:
            writer.close()
    require(writer is not None and total_rows > 0, "branches have no common cell-year support")
    os.replace(partial, args.comparison_output)

    delta_summary = {}
    for column in WEATHER:
        values = np.concatenate(delta_values[column])
        delta_summary[column] = {
            "minimum": float(values.min()), "median": float(np.median(values)), "maximum": float(values.max()),
            "nonzero_cell_years": int(np.count_nonzero(values)),
        }
    receipt = {
        "schema": "hultgren_rice_historical_transport_preflight/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_unweighted_ri1_branch_preflight_not_response_damage_or_scc",
        "branches": sources,
        "published_response": {
            "coefficients": {"path": str(args.coefficients), "sha256": digest(args.coefficients)},
            "covariance": {"path": str(args.covariance), "sha256": digest(args.covariance)},
            "terms": len(estimate.terms),
            "weather_primitive_contract_complete": True,
            "evaluated": False,
            "reason_not_evaluated": "cell moderators and source rice application-domain bounds are not available on this season-separated support",
        },
        "direct_weather_reconstruction": direct_checks,
        "cell_level_support": {
            "ri1_noirr_cell_years": total_rows,
            "ri1_firr_cell_years": total_rows,
            "common_cell_years": total_rows,
            "noirr_only_cell_years": 0,
            "firr_only_cell_years": 0,
            "unweighted_ri1_noirr": unweighted_summary(summaries["ri1_noirr"]),
            "unweighted_ri1_firr": unweighted_summary(summaries["ri1_firr"]),
        },
        "branch_diagnostics": {
            "common_calendar_equal_cell_years": calendar_equal_rows,
            "common_calendar_different_cell_years": total_rows - calendar_equal_rows,
            "common_weather_different_cell_years": weather_different_rows,
            "unweighted_firr_minus_noirr": delta_summary,
        },
        "comparison_output": {
            "path": str(args.comparison_output), "rows": total_rows,
            "bytes": args.comparison_output.stat().st_size, "sha256": digest(args.comparison_output),
        },
        "domain": {
            "implemented_calendar_domain": "6 through 12 whole crop-season months",
            "all_emitted_rows_inside_implemented_calendar_domain": True,
            "all_emitted_weather_primitives_finite": True,
            "author_rice_estimation_sample_available": False,
            "author_minmax_or_p01_p99_domain_assessed": False,
            "india_reporting_year_exception_applied": False,
        },
        "weighting": {
            "area_or_production_columns_present": False,
            "weighted_statistics_reported": False,
            "calendar_branches_aggregated": False,
        },
        "claim_gates": {
            "cell_level_historical_weather_preflight_validated": True,
            "published_response_transport_validated": False,
            "global_weighted_response_validated": False,
            "damage_validated": False,
            "scc_validated": False,
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "cell_level_support": receipt["cell_level_support"], "branch_diagnostics": receipt["branch_diagnostics"]}, indent=2))


if __name__ == "__main__":
    main()
