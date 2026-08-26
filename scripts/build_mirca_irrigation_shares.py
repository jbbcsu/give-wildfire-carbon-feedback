#!/usr/bin/env python3
"""Build fixed crop-grid irrigation exposure weights from MIRCA-OS v2.

The annual harvested-area rasters are independent inputs used only to combine
rainfed and fully irrigated calendar exposures for GDHY's single observed
crop-grid-year yield.  The script estimates no weather response, damage, or
SCC.  Annual rice and wheat rasters are deliberately marked ineligible for
production because they do not identify GDHY's rice-season or spring/winter
wheat outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from affine import Affine


SOURCE_ROLE = "independent_fixed_baseline_crop_area_share"
SOURCE_VERSION = "MIRCA-OS_v2_March_2026"
VALID_YEARS = (2000, 2005, 2010, 2015, 2020)
EXPECTED_SHAPE = (360, 720)
EXPECTED_TRANSFORM = Affine(0.5, 0.0, -180.0, 0.0, -0.5, 90.0)

# Exact crop-class mappings may enter allocation after all other gates pass.
# Annual parent-crop mappings are exported for sensitivity development only.
CROP_MAP: dict[str, tuple[dict[str, object], ...]] = {
    "Maize": (
        {
            "crop": "mai",
            "season_specific_share": True,
            "production_eligible": True,
            "mapping_note": "exact MIRCA maize class to GDHY maize-major outcome",
        },
    ),
    "Soybeans": (
        {
            "crop": "soy",
            "season_specific_share": True,
            "production_eligible": True,
            "mapping_note": "exact MIRCA soybean class to GDHY soybean outcome",
        },
    ),
    "Rice": (
        {
            "crop": "ri1",
            "season_specific_share": False,
            "production_eligible": False,
            "mapping_note": "annual parent-rice share does not identify GDHY first-season rice",
        },
        {
            "crop": "ri2",
            "season_specific_share": False,
            "production_eligible": False,
            "mapping_note": "annual parent-rice share does not identify GDHY second-season rice",
        },
    ),
    "Wheat": (
        {
            "crop": "swh",
            "season_specific_share": False,
            "production_eligible": False,
            "mapping_note": "annual parent-wheat share does not distinguish spring wheat",
        },
        {
            "crop": "wwh",
            "season_specific_share": False,
            "production_eligible": False,
            "mapping_note": "annual parent-wheat share does not distinguish winter wheat",
        },
    ),
}


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_raster(root: Path, mirca_crop: str, year: int, system: str) -> Path:
    name = f"MIRCA-OS_{mirca_crop}_{year}_{system}_30arcmin_v2.tif"
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} below {root}; found {len(matches)}")
    return matches[0]


def read_area_raster(path: Path) -> tuple[np.ndarray, dict[str, object]]:
    with rasterio.open(path) as dataset:
        if (dataset.height, dataset.width) != EXPECTED_SHAPE or dataset.count != 1:
            raise ValueError(f"Unexpected 30-arcminute grid shape/count in {path}")
        if dataset.crs is None or dataset.crs.to_epsg() != 4326:
            raise ValueError(f"Expected EPSG:4326 in {path}")
        if not np.allclose(
            tuple(dataset.transform)[:6], tuple(EXPECTED_TRANSFORM)[:6], rtol=0.0, atol=1e-9
        ):
            raise ValueError(f"Unexpected global 0.5-degree transform in {path}")
        if dataset.nodata is None or not np.isclose(float(dataset.nodata), 0.0):
            raise ValueError(f"Expected MIRCA zero-area/nodata encoding of 0 in {path}")
        values = dataset.read(1, masked=False).astype(np.float64)
        profile = {
            "shape": [dataset.height, dataset.width],
            "crs": dataset.crs.to_string(),
            "transform": list(tuple(dataset.transform)[:6]),
            "nodata": float(dataset.nodata),
        }
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"Harvested area must be finite and nonnegative in {path}")
    return values, profile


def build_weights(
    input_root: Path,
    year: int,
    outcome_crops: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if year not in VALID_YEARS:
        raise ValueError(f"Year must be one of {VALID_YEARS}")
    known_outcomes = {str(item["crop"]) for mappings in CROP_MAP.values() for item in mappings}
    selected = list(dict.fromkeys(outcome_crops or sorted(known_outcomes)))
    unknown = set(selected) - known_outcomes
    if unknown:
        raise ValueError(f"Unknown outcome crops {sorted(unknown)}")
    if not selected:
        raise ValueError("Select at least one outcome crop")

    frames: list[pd.DataFrame] = []
    input_records: list[dict[str, object]] = []
    source_summaries: list[dict[str, object]] = []
    latitude = 89.75 - 0.5 * np.arange(EXPECTED_SHAPE[0], dtype=np.float64)
    longitude = -179.75 + 0.5 * np.arange(EXPECTED_SHAPE[1], dtype=np.float64)
    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    weight_source_id = f"{SOURCE_VERSION}_AHAG_30arcmin_{year}"
    weight_vintage = f"fixed_{year}"

    for mirca_crop, mappings in CROP_MAP.items():
        requested_mappings = [item for item in mappings if str(item["crop"]) in selected]
        if not requested_mappings:
            continue
        irrigation_path = locate_raster(input_root, mirca_crop, year, "ir")
        rainfed_path = locate_raster(input_root, mirca_crop, year, "rf")
        irrigation_area, irrigation_profile = read_area_raster(irrigation_path)
        rainfed_area, rainfed_profile = read_area_raster(rainfed_path)
        if irrigation_profile != rainfed_profile:
            raise ValueError(f"Irrigated/rainfed raster grids differ for {mirca_crop} {year}")

        total_area = irrigation_area + rainfed_area
        supported = total_area > 0
        if not supported.any():
            raise ValueError(f"No positive harvested area for {mirca_crop} {year}")
        irrigated_share = irrigation_area[supported] / total_area[supported]
        rainfed_share = rainfed_area[supported] / total_area[supported]
        if not np.allclose(irrigated_share + rainfed_share, 1.0, rtol=0.0, atol=1e-12):
            raise AssertionError(f"Irrigated/rainfed shares fail to sum to one for {mirca_crop}")

        common = {
            "lat": lat_grid[supported],
            "lon": lon_grid[supported],
            "lon_360": np.mod(lon_grid[supported], 360.0),
            "mirca_crop": mirca_crop,
            "share_year": year,
            "irrigated_area_ha": irrigation_area[supported],
            "rainfed_area_ha": rainfed_area[supported],
            "total_area_ha": total_area[supported],
            "weight_source_id": weight_source_id,
            "weight_vintage": weight_vintage,
            "source_role": SOURCE_ROLE,
        }
        for mapping in requested_mappings:
            for irrigation, shares in (("firr", irrigated_share), ("noirr", rainfed_share)):
                frame = pd.DataFrame(common)
                frame["crop"] = str(mapping["crop"])
                frame["irrigation"] = irrigation
                frame["area_share"] = shares
                frame["season_specific_share"] = bool(mapping["season_specific_share"])
                frame["production_eligible"] = bool(mapping["production_eligible"])
                frame["mapping_note"] = str(mapping["mapping_note"])
                frames.append(frame)

        for system, path in (("ir", irrigation_path), ("rf", rainfed_path)):
            input_records.append(
                {
                    "mirca_crop": mirca_crop,
                    "system": system,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha512": sha512(path),
                }
            )
        source_summaries.append(
            {
                "mirca_crop": mirca_crop,
                "supported_cells": int(supported.sum()),
                "irrigated_area_ha": float(irrigation_area.sum()),
                "rainfed_area_ha": float(rainfed_area.sum()),
                "total_area_ha": float(total_area.sum()),
                "global_area_weighted_irrigated_share": float(
                    irrigation_area.sum() / total_area.sum()
                ),
                "outcome_crops": [str(item["crop"]) for item in requested_mappings],
            }
        )

    output = pd.concat(frames, ignore_index=True)
    output = output[
        [
            "lat", "lon", "lon_360", "crop", "irrigation", "area_share",
            "weight_source_id", "weight_vintage", "source_role", "mirca_crop",
            "share_year", "irrigated_area_ha", "rainfed_area_ha", "total_area_ha",
            "season_specific_share", "production_eligible", "mapping_note",
        ]
    ].sort_values(["crop", "lat", "lon_360", "irrigation"], ascending=[True, False, True, True])
    output = output.reset_index(drop=True)
    keys = ["lat", "lon_360", "crop", "irrigation"]
    if output.duplicated(keys).any():
        raise AssertionError("Built duplicate crop-grid-irrigation weights")
    group_sums = output.groupby(["lat", "lon_360", "crop"], observed=True)["area_share"].sum()
    if not np.allclose(group_sums.to_numpy(), 1.0, rtol=0.0, atol=1e-12):
        raise AssertionError("Built shares do not sum to one")

    audit: dict[str, object] = {
        "schema_version": 1,
        "purpose": "Fixed harvested-area weights for one-exposure-per-GDHY-outcome allocation.",
        "boundary": "Input preparation only; no yield response, damage, or SCC is estimated.",
        "source_version": SOURCE_VERSION,
        "share_year": year,
        "fixed_across_outcome_years": True,
        "area_units": "ha",
        "grid": "global 0.5 degree EPSG:4326 cell centres",
        "zero_encoding": "Raster nodata value 0 is interpreted as zero harvested area; cells with zero total area are omitted and never renormalized.",
        "selected_outcome_crops": selected,
        "production_eligible_outcome_crops": sorted(
            output.loc[output.production_eligible, "crop"].unique().tolist()
        ),
        "provisional_outcome_crops": sorted(
            output.loc[~output.production_eligible, "crop"].unique().tolist()
        ),
        "output_rows": int(len(output)),
        "supported_crop_grid_cells": int(output.groupby(["lat", "lon_360", "crop"]).ngroups),
        "input_files": input_records,
        "source_crop_summaries": source_summaries,
        "scc_authorized": False,
    }
    return output, audit


def write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        frame.to_csv(path, index=False)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        frame.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported output format for {path}; use CSV or Parquet")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--year", required=True, type=int, choices=VALID_YEARS)
    parser.add_argument("--outcome-crop", action="append")
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    output, audit = build_weights(Path(args.input_root), args.year, args.outcome_crop)
    write_table(output, Path(args.out))
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
