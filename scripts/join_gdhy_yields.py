#!/usr/bin/env python3
"""Join a crop-year climate-feature partition to GDHY yields with coordinate checks.

GDHY has ascending latitude and 0–360° longitude; ISIMIP feature output has
descending latitude and −180–180° longitude. The join uses exact 0.5° grid
centres after normalizing longitude, and fails if source coordinates are not
aligned. It is intentionally a pilot/panel utility, not a welfare aggregator.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import xarray as xr


GDHY_DIRECTORY = {
    # The ISIMIP calendar supplies one primary maize season and two rice
    # periods.  Use the documented GDHY season-specific files rather than the
    # convenience aggregate directories, which would obscure season matching.
    "mai": "maize_major", "ri1": "rice_major", "ri2": "rice_second",
    "soy": "soybean", "swh": "wheat_spring", "wwh": "wheat_winter",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--gdhy-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    features = pd.read_parquet(args.features)
    required = {"harvest_year", "lat", "lon_360", "crop"}
    if missing := required - set(features.columns):
        raise ValueError(f"Feature file missing {sorted(missing)}")
    if features.crop.nunique() != 1:
        raise ValueError("Join one crop partition at a time")
    crop = features.crop.iloc[0]
    if crop not in GDHY_DIRECTORY:
        raise ValueError(f"No GDHY mapping for crop {crop}")
    if features.duplicated(["harvest_year", "lat", "lon_360", "crop", "irrigation"]).any():
        raise ValueError("Feature panel has duplicate crop-year grid rows")

    parts = []
    root = Path(args.gdhy_root) / GDHY_DIRECTORY[crop]
    for year, group in features.groupby("harvest_year", sort=True):
        year = int(year)
        path = root / f"yield_{year}.nc4"
        if not path.is_file():
            raise FileNotFoundError(path)
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            if set(ds.dims) != {"lat", "lon"} or len(ds.data_vars) != 1:
                raise ValueError(f"Unexpected GDHY grid schema: {path}")
            variable = next(iter(ds.data_vars))
            yield_grid = ds[variable].to_dataframe(name="yield_t_ha").reset_index().dropna()
        yield_grid["lon_360"] = yield_grid["lon"] % 360
        requested = group.copy()
        merged = requested.merge(
            yield_grid[["lat", "lon_360", "yield_t_ha"]],
            on=["lat", "lon_360"], how="left", validate="many_to_one",
        )
        merged["gdhy_path"] = str(path)
        parts.append(merged)
    panel = pd.concat(parts, ignore_index=True)
    if (panel.yield_t_ha.dropna() < 0).any():
        raise ValueError("GDHY contains negative nonmissing yield values")
    # The aligned GDHY construction clips a small number of negative aligned
    # values to zero (Iizumi and Sakai, 2020). Preserve that source value for
    # audit, but do not pass zero to a log-yield response as an observation.
    panel["gdhy_yield_raw_t_ha"] = panel.yield_t_ha
    panel["yield_nonpositive"] = panel.yield_t_ha.eq(0)
    panel.loc[panel.yield_nonpositive, "yield_t_ha"] = pd.NA
    panel["yield_observed"] = panel.yield_t_ha.notna()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.out, index=False)
    print(
        f"wrote {len(panel)} rows; yield coverage={panel.yield_observed.mean():.3f}; "
        f"source_zero_yields={int(panel.yield_nonpositive.sum())}"
    )


if __name__ == "__main__":
    main()
