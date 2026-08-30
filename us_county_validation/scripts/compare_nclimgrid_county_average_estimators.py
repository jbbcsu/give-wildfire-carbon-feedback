#!/usr/bin/env python3
"""Compare NOAA county averages with the registered polygon-weight proxy.

This is an outcome-free measurement audit.  It does not select either spatial
estimator, estimate a climate-yield response, or authorize damages or SCC use.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from audit_nclimgrid_county_average_sample import (
    VARIABLES,
    load_area_average,
    load_crosswalk,
)


SCHEMA = "us_nclimgrid_county_average_estimator_comparison_v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_UNITS = {
    "PRCP": "millimeter",
    "TAVG": "degree_Celsius",
    "TMIN": "degree_Celsius",
    "TMAX": "degree_Celsius",
}
REQUIRED_WEIGHT_COLUMNS = {
    "county_geoid",
    "grid_lat_index",
    "grid_lon_index",
    "spatial_weight",
    "weather_source_id",
    "weather_grid_id",
    "weight_role",
    "analysis_role",
    "feature_construction_eligible",
    "scc_authorized",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def stable_float(value: float) -> float:
    return round(float(value), 12)


def strict_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        result = series.astype(bool)
    else:
        text = series.astype("string").str.strip().str.lower()
        require(not text.isna().any() and text.isin(["true", "false"]).all(), f"{label} is not boolean")
        result = text.eq("true")
    require(not result.isna().any(), f"{label} contains missing values")
    return result


def load_weights(path: Path, nlat: int, nlon: int) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
    frame = pd.read_parquet(path)
    require(not frame.empty, f"weight file is empty: {path}")
    require(not (REQUIRED_WEIGHT_COLUMNS - set(frame.columns)), f"weight schema is incomplete: {path}")
    county_values = frame["county_geoid"].astype("string").str.zfill(5).unique()
    require(len(county_values) == 1 and county_values[0].isdigit(), f"weight county identity is invalid: {path}")
    require(frame["weight_role"].eq("county_polygon_primary_proxy").all(), "weights are not the registered polygon proxy")
    require(
        frame["analysis_role"].eq("historical_county_validation_only").all(),
        "weight analysis role changed",
    )
    require(strict_bool(frame["feature_construction_eligible"], "feature eligibility").all(), "ineligible weights supplied")
    require(not strict_bool(frame["scc_authorized"], "SCC authorization").any(), "weights unexpectedly authorize SCC use")
    lat_index = pd.to_numeric(frame["grid_lat_index"], errors="raise").to_numpy(dtype=int)
    lon_index = pd.to_numeric(frame["grid_lon_index"], errors="raise").to_numpy(dtype=int)
    weights = pd.to_numeric(frame["spatial_weight"], errors="raise").to_numpy(dtype=float)
    require(np.isfinite(weights).all() and (weights > 0).all(), "spatial weights are not positive and finite")
    require(abs(float(weights.sum()) - 1.0) <= 1e-10, "spatial weights do not sum to one")
    require(((lat_index >= 0) & (lat_index < nlat)).all(), "latitude index is outside the grid")
    require(((lon_index >= 0) & (lon_index < nlon)).all(), "longitude index is outside the grid")
    require(len(set(zip(lat_index.tolist(), lon_index.tolist()))) == len(frame), "weight grid cells are duplicated")
    return str(county_values[0]), lat_index, lon_index, weights


def summarize_difference(polygon_values: np.ndarray, source_values: np.ndarray) -> dict[str, float | None]:
    polygon = np.asarray(polygon_values, dtype=float)
    source = np.asarray(source_values, dtype=float)
    require(polygon.ndim == source.ndim == 1 and len(polygon) == len(source) > 0, "daily series shape differs")
    require(np.isfinite(polygon).all() and np.isfinite(source).all(), "daily series contains nonfinite values")
    difference = polygon - source
    correlation = None
    if len(polygon) > 1 and float(np.std(polygon)) > 0 and float(np.std(source)) > 0:
        correlation = stable_float(np.corrcoef(polygon, source)[0, 1])
    return {
        "polygon_mean": stable_float(polygon.mean()),
        "source_mean": stable_float(source.mean()),
        "mean_difference": stable_float(difference.mean()),
        "mean_absolute_difference": stable_float(np.abs(difference).mean()),
        "root_mean_squared_difference": stable_float(np.sqrt(np.mean(difference**2))),
        "maximum_absolute_difference": stable_float(np.abs(difference).max()),
        "pearson_correlation": correlation,
    }


def compare(
    grid_path: Path,
    official_paths: dict[str, Path],
    version_path: Path,
    crosswalk_path: Path,
    weight_paths: list[Path],
) -> dict[str, object]:
    require(set(official_paths) == set(VARIABLES), "exact PRCP/TAVG/TMIN/TMAX official inputs are required")
    require(weight_paths, "at least one polygon-weight file is required")
    state_map = load_crosswalk(crosswalk_path)
    official = {
        variable: load_area_average(official_paths[variable], variable, state_map)
        for variable in VARIABLES
    }
    identities = {tuple(item["year_month"]) for item in official.values()}
    require(len(identities) == 1, "official inputs do not share one year-month")
    supports = {variable: set(item["records"]) for variable, item in official.items()}
    require(all(keys == supports["PRCP"] for keys in supports.values()), "official county support differs by variable")
    year, month = next(iter(identities))
    expected_days = calendar.monthrange(year, month)[1]

    with xr.open_dataset(grid_path, decode_cf=True) as dataset:
        require(set(VARIABLES) == {name.upper() for name in dataset.data_vars}, "gridded variable product changed")
        require(set(dataset.dims) == {"time", "lat", "lon"}, "gridded dimensions changed")
        require(int(dataset.sizes["time"]) == expected_days, "gridded month has the wrong day count")
        dates = pd.DatetimeIndex(dataset["time"].values)
        require(
            dates.equals(pd.date_range(f"{year:04d}-{month:02d}-01", periods=expected_days, freq="D")),
            "gridded daily chronology changed",
        )
        results: list[dict[str, object]] = []
        weight_receipts: list[dict[str, object]] = []
        seen_counties: set[str] = set()
        for weight_path in weight_paths:
            county, lat_index, lon_index, spatial_weight = load_weights(
                weight_path, int(dataset.sizes["lat"]), int(dataset.sizes["lon"])
            )
            require(county not in seen_counties, f"county {county} is duplicated")
            seen_counties.add(county)
            weight_receipts.append({"county_geoid": county, "path": display_path(weight_path), "sha256": sha256(weight_path)})
            for variable in VARIABLES:
                source_records = official[variable]["records"]
                require(county in source_records, f"official input lacks county {county}")
                field = dataset[variable.lower()]
                require(field.dims == ("time", "lat", "lon"), f"{variable} gridded dimensions changed")
                require(field.attrs.get("units") == EXPECTED_UNITS[variable], f"{variable} units changed")
                selected = field.isel(
                    lat=xr.DataArray(lat_index, dims="cell"),
                    lon=xr.DataArray(lon_index, dims="cell"),
                ).values
                require(selected.shape == (expected_days, len(spatial_weight)), f"{variable} extraction shape changed")
                require(np.isfinite(selected).all(), f"{variable} polygon cells contain nonfinite values")
                valid_min = float(field.attrs["valid_min"])
                valid_max = float(field.attrs["valid_max"])
                require(
                    ((selected >= valid_min) & (selected <= valid_max)).all(),
                    f"{variable} polygon cells violate declared physical bounds",
                )
                polygon_values = np.sum(selected * spatial_weight[None, :], axis=1)
                source_values = np.asarray(source_records[county]["values"], dtype=float)
                metrics = summarize_difference(polygon_values, source_values)
                if variable == "PRCP":
                    metrics["polygon_monthly_total"] = stable_float(polygon_values.sum())
                    metrics["source_monthly_total"] = stable_float(source_values.sum())
                    metrics["monthly_total_difference"] = stable_float(
                        polygon_values.sum() - source_values.sum()
                    )
                results.append({"county_geoid": county, "variable": variable, "days": expected_days, **metrics})

    return {
        "schema": SCHEMA,
        "status": "validated_measurement_comparison_not_estimator_equivalence",
        "year": year,
        "month": month,
        "counties": sorted(seen_counties),
        "variables": list(VARIABLES),
        "official_counties_per_variable": len(supports["PRCP"]),
        "results": results,
        "inputs": {
            "grid": {"path": display_path(grid_path), "bytes": grid_path.stat().st_size, "sha256": sha256(grid_path)},
            "official": {
                variable.lower(): {
                    "url": (
                        "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/"
                        f"{year}/{variable.lower()}-{year}{month:02d}-cty-scaled.csv"
                    ),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for variable, path in official_paths.items()
            },
            "version": {
                "url": (
                    "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/"
                    f"{year}/ncdd-{year}{month:02d}-version.txt"
                ),
                "bytes": version_path.stat().st_size,
                "sha256": sha256(version_path),
                "text": version_path.read_text(encoding="utf-8").strip(),
            },
            "state_crosswalk": {
                "url": "https://www.ncei.noaa.gov/data/nclimgrid-daily/doc/us-state-codes_ncei-to-fips.csv",
                "bytes": crosswalk_path.stat().st_size,
                "sha256": sha256(crosswalk_path),
            },
            "polygon_weights": weight_receipts,
        },
        "registered_polygon_route_replaced": False,
        "estimators_declared_equivalent": False,
        "relationship_estimated": False,
        "response_damage_or_scc_authorized": False,
        "disclaimer": (
            "A bounded source-versus-polygon weather measurement comparison is not evidence of general "
            "estimator equivalence, a climate-yield response, damages, or SCC effects."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=Path, required=True)
    for variable in VARIABLES:
        parser.add_argument(f"--{variable.lower()}", type=Path, required=True)
    parser.add_argument("--version", type=Path, required=True)
    parser.add_argument("--state-crosswalk", type=Path, required=True)
    parser.add_argument("--weights", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        args.grid.resolve(),
        {variable: getattr(args, variable.lower()).resolve() for variable in VARIABLES},
        args.version.resolve(),
        args.state_crosswalk.resolve(),
        [path.resolve() for path in args.weights],
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"compared {len(result['counties'])} counties across {len(result['variables'])} variables")


if __name__ == "__main__":
    main()
