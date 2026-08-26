#!/usr/bin/env python3
"""Build fixed-2017 CDL crop-pixel weights on the nClimGrid grid.

This is a spatial-measurement sensitivity, not the full-period primary U.S.
exposure. Pixels are selected by center inclusion in the county polygon and
assigned by their centers to nClimGrid cells. The official CDL is an equal-area
30 m raster, so each selected pixel contributes 900 m2. Earlier-year use must
remain labeled ``retrospective_2017_mask_sensitivity``.

The script does not read yields, calculate weather features, estimate a
response, or authorize an SCC input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.features import geometry_mask
from rasterio.transform import array_bounds
from rasterio.windows import Window, from_bounds, transform as window_transform
from shapely.geometry import mapping
from shapely.ops import transform


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from build_county_polygon_nclimgrid_weights import (  # noqa: E402
    AREA_CRS,
    WEATHER_GRID_ID,
    WEATHER_SOURCE_ID,
    coordinate_edges,
    load_county,
    load_grid,
)
from validate_county_crop_weather_contract import validate_weights  # noqa: E402


CDL_SOURCE_ID = "usda_nass_cdl_2017_30m_national"
CDL_MASK_VINTAGE = "2017-01-01"
CDL_BACKGROUND_CODE = 0
CDL_SHA512 = (
    "a2423a5a9cb45e029d7cb1aa3ccaa9fc3fd8e2aedf593ccf430d04a044e62633"
    "cd1997f1fe73c9ba20073309c80a9adcf910ff372ad98b4abfe3120ab553e55f"
)
TIGER_SOURCE_ID = "tigerline_2019_county"
TIGER_VINTAGE = "2019-01-01"
OFFICIAL_MEMBER = "2017_30m_cdls.tif"
OFFICIAL_PROFILE = {
    "crs": "EPSG:5070",
    "dtype": "uint8",
    "count": 1,
    "width": 153811,
    "height": 96523,
    "transform": (30.0, 0.0, -2356095.0, 0.0, -30.0, 3172605.0),
    "block_shape": (512, 512),
    "nodata": None,
    "statistics_excluded_values": "0",
}
CROP_CLASSES = {
    "corn_grain": {"outcome_crop": "corn_grain", "class_code": 1},
    "soybeans": {"outcome_crop": "soybeans", "class_code": 5},
    "durum_wheat": {"outcome_crop": "wheat_all_classes", "class_code": 22},
    "spring_wheat": {"outcome_crop": "wheat_all_classes", "class_code": 23},
    "winter_wheat": {"outcome_crop": "wheat_all_classes", "class_code": 24},
}
ALLOWED_TEMPORAL_ROLES = {
    "pre_outcome_fixed_2017_sensitivity",
    "retrospective_2017_mask_sensitivity",
}


def cdl_dataset_path(archive: Path, member: str = OFFICIAL_MEMBER) -> str:
    return f"zip://{archive.resolve()}!{member}"


def bounded_window(bounds: tuple[float, float, float, float], dataset: rasterio.DatasetReader) -> Window:
    candidate = from_bounds(*bounds, transform=dataset.transform)
    left = max(0, int(np.floor(candidate.col_off)))
    top = max(0, int(np.floor(candidate.row_off)))
    right = min(dataset.width, int(np.ceil(candidate.col_off + candidate.width)))
    bottom = min(dataset.height, int(np.ceil(candidate.row_off + candidate.height)))
    if right <= left or bottom <= top:
        raise ValueError("County polygon does not overlap the CDL raster")
    return Window(left, top, right - left, bottom - top)


def validate_cdl_profile(dataset: rasterio.DatasetReader, strict_official_profile: bool) -> float:
    if dataset.crs is None or CRS.from_user_input(dataset.crs) != AREA_CRS:
        raise ValueError("CDL raster must use EPSG:5070")
    if dataset.count != 1 or dataset.dtypes != ("uint8",):
        raise ValueError("CDL raster must be one uint8 thematic band")
    transform_values = tuple(dataset.transform)[:6]
    pixel_area = abs(
        dataset.transform.a * dataset.transform.e
        - dataset.transform.b * dataset.transform.d
    )
    if not np.isclose(pixel_area, 900.0, rtol=0, atol=1e-9):
        raise ValueError("CDL pixels must have 900 m2 equal-area support")
    if dataset.tags().get("AREA_OR_POINT") not in {None, "Area"}:
        raise ValueError("CDL raster AREA_OR_POINT metadata changed")
    if strict_official_profile:
        observed = {
            "crs": str(dataset.crs),
            "dtype": dataset.dtypes[0],
            "count": dataset.count,
            "width": dataset.width,
            "height": dataset.height,
            "transform": transform_values,
            "block_shape": dataset.block_shapes[0],
            "nodata": dataset.nodata,
            "statistics_excluded_values": dataset.tags(1).get("STATISTICS_EXCLUDEDVALUES"),
        }
        if observed != OFFICIAL_PROFILE:
            raise ValueError(f"CDL raster profile differs from pinned official object: {observed}")
    return float(pixel_area)


def _validate_requested_classes(calendar_crops: list[str]) -> list[str]:
    requested = list(dict.fromkeys(calendar_crops))
    if not requested:
        raise ValueError("At least one calendar crop is required")
    if unknown := set(requested) - set(CROP_CLASSES):
        raise ValueError(f"Unknown calendar crops {sorted(unknown)}")
    wheat = {"winter_wheat", "spring_wheat", "durum_wheat"}
    selected_wheat = set(requested) & wheat
    if selected_wheat and selected_wheat != wheat:
        raise ValueError("A wheat sensitivity must request winter, spring, and durum together")
    return requested


def build_weights(
    shapefile_path: Path,
    county_geoid: str,
    climate_path: Path,
    cdl_path: str,
    calendar_crops: list[str],
    mask_temporal_role: str,
    min_weather_coverage: float = 0.999,
    max_county_pixel_area_relative_error: float = 0.01,
    strict_official_profile: bool = True,
) -> tuple[pd.DataFrame, dict[str, object]]:
    calendar_crops = _validate_requested_classes(calendar_crops)
    if mask_temporal_role not in ALLOWED_TEMPORAL_ROLES:
        raise ValueError("Unknown fixed-mask temporal role")
    if not 0 < min_weather_coverage <= 1:
        raise ValueError("min_weather_coverage must lie within (0, 1]")
    if max_county_pixel_area_relative_error < 0:
        raise ValueError("county pixel-area tolerance must be nonnegative")

    latitude, longitude = load_grid(climate_path)
    lat_edges = coordinate_edges(latitude, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    county_source, county_crs, county_metadata = load_county(shapefile_path, county_geoid)
    county_to_area = Transformer.from_crs(county_crs, AREA_CRS, always_xy=True)
    county_area = transform(county_to_area.transform, county_source)
    county_area_m2 = float(county_area.area)
    if not np.isfinite(county_area_m2) or county_area_m2 <= 0:
        raise ValueError("Projected county area is not positive and finite")

    with rasterio.open(cdl_path) as dataset:
        pixel_area_m2 = validate_cdl_profile(dataset, strict_official_profile)
        window = bounded_window(county_area.bounds, dataset)
        data = dataset.read(1, window=window)
        local_transform = window_transform(window, dataset.transform)
        inside_county = geometry_mask(
            [mapping(county_area)],
            out_shape=data.shape,
            transform=local_transform,
            invert=True,
            all_touched=False,
        )
        county_center_pixel_count = int(inside_county.sum())
        county_pixel_area_m2 = county_center_pixel_count * pixel_area_m2
        county_pixel_area_relative_error = abs(county_pixel_area_m2 - county_area_m2) / county_area_m2
        if county_pixel_area_relative_error > max_county_pixel_area_relative_error:
            raise ValueError("Pixel-center county mask does not reconcile to polygon area")

        to_wgs84 = Transformer.from_crs(dataset.crs, CRS.from_epsg(4326), always_xy=True)
        selected: dict[str, dict[str, object]] = {}
        for calendar_crop in calendar_crops:
            code = int(CROP_CLASSES[calendar_crop]["class_code"])
            rows, columns = np.nonzero(inside_county & (data == code))
            total_pixels = int(len(rows))
            if total_pixels == 0:
                selected[calendar_crop] = {
                    "class_code": code,
                    "total_pixels": 0,
                    "mapped_pixels": 0,
                    "pairs": np.empty((0, 2), dtype=int),
                    "counts": np.empty(0, dtype=int),
                    "coverage_fraction": np.nan,
                }
                continue
            x = (
                local_transform.c
                + (columns.astype(float) + 0.5) * local_transform.a
                + (rows.astype(float) + 0.5) * local_transform.b
            )
            y = (
                local_transform.f
                + (columns.astype(float) + 0.5) * local_transform.d
                + (rows.astype(float) + 0.5) * local_transform.e
            )
            lon, lat = to_wgs84.transform(x, y)
            lat_index = np.searchsorted(lat_edges, lat, side="right") - 1
            lon_index = np.searchsorted(lon_edges, lon, side="right") - 1
            mapped = (
                (lat_index >= 0)
                & (lat_index < len(latitude))
                & (lon_index >= 0)
                & (lon_index < len(longitude))
            )
            mapped_pixels = int(mapped.sum())
            coverage_fraction = mapped_pixels / total_pixels
            if coverage_fraction < min_weather_coverage:
                raise ValueError(
                    f"{calendar_crop} crop-pixel weather coverage {coverage_fraction:.9f} fails gate"
                )
            pairs, counts = np.unique(
                np.column_stack((lat_index[mapped], lon_index[mapped])),
                axis=0,
                return_counts=True,
            )
            selected[calendar_crop] = {
                "class_code": code,
                "total_pixels": total_pixels,
                "mapped_pixels": mapped_pixels,
                "pairs": pairs,
                "counts": counts,
                "coverage_fraction": coverage_fraction,
            }

    outcome_areas: dict[str, float] = {}
    for calendar_crop in calendar_crops:
        outcome_crop = str(CROP_CLASSES[calendar_crop]["outcome_crop"])
        mapped_area = int(selected[calendar_crop]["mapped_pixels"]) * pixel_area_m2
        outcome_areas[outcome_crop] = outcome_areas.get(outcome_crop, 0.0) + mapped_area
    if zero_outcomes := sorted(name for name, value in outcome_areas.items() if value <= 0):
        raise ValueError(f"No mapped CDL pixels for outcome crops {zero_outcomes}")

    rows_out: list[dict[str, object]] = []
    crop_audit: dict[str, object] = {}
    for calendar_crop in calendar_crops:
        details = selected[calendar_crop]
        if int(details["mapped_pixels"]) == 0:
            continue
        outcome_crop = str(CROP_CLASSES[calendar_crop]["outcome_crop"])
        calendar_area_m2 = int(details["mapped_pixels"]) * pixel_area_m2
        outcome_area_m2 = outcome_areas[outcome_crop]
        pairs = np.asarray(details["pairs"], dtype=int)
        counts = np.asarray(details["counts"], dtype=int)
        for (lat_index, lon_index), count in zip(pairs, counts, strict=True):
            crop_area_m2 = int(count) * pixel_area_m2
            rows_out.append(
                {
                    "county_geoid": county_geoid,
                    "state": county_metadata["state"],
                    "county_name": county_metadata["county_name"],
                    "outcome_crop": outcome_crop,
                    "calendar_crop": calendar_crop,
                    "weather_source_id": WEATHER_SOURCE_ID,
                    "weather_grid_id": WEATHER_GRID_ID,
                    "grid_lat_index": int(lat_index),
                    "grid_lon_index": int(lon_index),
                    "grid_lat": float(latitude[lat_index]),
                    "grid_lon": float(longitude[lon_index]),
                    "crop_area_m2": crop_area_m2,
                    "county_calendar_crop_area_m2": calendar_area_m2,
                    "county_outcome_crop_area_m2": outcome_area_m2,
                    "spatial_weight": crop_area_m2 / calendar_area_m2,
                    "calendar_class_share": calendar_area_m2 / outcome_area_m2,
                    "calendar_class_share_source_id": "usda_nass_cdl_2017_pixel_count",
                    "mask_source_id": CDL_SOURCE_ID,
                    "mask_source_sha512": CDL_SHA512,
                    "mask_vintage": CDL_MASK_VINTAGE,
                    "mask_temporal_role": mask_temporal_role,
                    "mask_pixel_assignment": "pixel_center_in_county_and_nclimgrid_cell",
                    "mask_pixel_area_m2": pixel_area_m2,
                    "cdl_class_code": int(details["class_code"]),
                    "double_crop_classes_included": False,
                    "boundary_source_id": TIGER_SOURCE_ID,
                    "boundary_vintage": TIGER_VINTAGE,
                    "coverage_fraction": float(details["coverage_fraction"]),
                    "weight_role": "fixed_crop_mask_sensitivity",
                    "analysis_role": "historical_county_validation_sensitivity_only",
                    "feature_construction_eligible": True,
                    "response_estimation_authorized": False,
                    "scc_authorized": False,
                }
            )
        crop_audit[calendar_crop] = {
            "cdl_class_code": int(details["class_code"]),
            "in_county_pixels": int(details["total_pixels"]),
            "mapped_weather_pixels": int(details["mapped_pixels"]),
            "weather_coverage_fraction": float(details["coverage_fraction"]),
            "mapped_area_m2": calendar_area_m2,
            "positive_weather_cells": int(len(pairs)),
        }

    weights = pd.DataFrame(rows_out)
    if weights.empty:
        raise ValueError("No crop-pixel weights were constructed")
    weights = validate_weights(weights, tolerance=1e-8)
    left, bottom, right, top = array_bounds(data.shape[0], data.shape[1], local_transform)
    audit = {
        "county_geoid": county_geoid,
        "state": county_metadata["state"],
        "county_name": county_metadata["county_name"],
        "cdl_source_id": CDL_SOURCE_ID,
        "cdl_sha512": CDL_SHA512,
        "cdl_mask_vintage": CDL_MASK_VINTAGE,
        "mask_temporal_role": mask_temporal_role,
        "weight_role": "fixed_crop_mask_sensitivity",
        "pixel_assignment": "pixel_center_in_county_and_nclimgrid_cell",
        "pixel_area_m2": pixel_area_m2,
        "county_polygon_area_m2_epsg5070": county_area_m2,
        "county_center_pixel_count": county_center_pixel_count,
        "county_center_pixel_area_m2": county_pixel_area_m2,
        "county_pixel_area_relative_error": county_pixel_area_relative_error,
        "raster_window": {
            "row_off": int(window.row_off),
            "col_off": int(window.col_off),
            "height": int(window.height),
            "width": int(window.width),
            "bounds_epsg5070": [left, bottom, right, top],
        },
        "crops": crop_audit,
        "double_crop_classes_included": False,
        "background_code": CDL_BACKGROUND_CODE,
        "background_handling": "explicitly excluded; source nodata is unset",
        "historical_measurement_warning": (
            "2017 pixels are not observed historical crop locations before 2017; "
            "earlier-year use is a retrospective-mask sensitivity only"
        ),
        "weather_features_constructed": False,
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    return weights, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counties", required=True, help="Census county shapefile (.shp)")
    parser.add_argument("--county-geoid", required=True)
    parser.add_argument("--climate", required=True, help="one validated nClimGrid monthly NetCDF")
    parser.add_argument("--cdl-archive", required=True)
    parser.add_argument("--cdl-member", default=OFFICIAL_MEMBER)
    parser.add_argument("--calendar-crops", nargs="+", default=["corn_grain", "soybeans"])
    parser.add_argument(
        "--mask-temporal-role",
        required=True,
        choices=sorted(ALLOWED_TEMPORAL_ROLES),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    weights, audit = build_weights(
        shapefile_path=Path(args.counties),
        county_geoid=args.county_geoid,
        climate_path=Path(args.climate),
        cdl_path=cdl_dataset_path(Path(args.cdl_archive), args.cdl_member),
        calendar_crops=args.calendar_crops,
        mask_temporal_role=args.mask_temporal_role,
        strict_official_profile=True,
    )
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    weights.to_parquet(destination, index=False)
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(weights)} fixed-2017 CDL sensitivity weights for {args.county_geoid}; "
        "no weather response estimated"
    )


if __name__ == "__main__":
    main()
