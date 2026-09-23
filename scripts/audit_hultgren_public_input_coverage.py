#!/usr/bin/env python3
"""Audit the locally pinned public Hultgren input files and source gaps."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import shapefile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/hultgren_response/gitlab_main_20250702"
CURRENT_CORN = RAW / "Fig1/Crop_Coverage/data/crops/corn_gmfd_v1.dta"
REGION_WEIGHTS = RAW / "Fig2/data/weights/agglomerated-world-new-hierid-crop-weights.csv"
CROP_MASK = RAW / "Fig2/data/shapes/cropped_area_maps/union_impact_regions_growing_corn.shp"
HISTORICAL_READY = ROOT / "data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
OUTPUT = ROOT / "data/provenance/hultgren_public_input_coverage_audit_20260923.json"

CURRENT_COMMIT = "3ccdffcd4e4ff6e55566ce76e2aac130ee86349a"
HISTORICAL_COMMIT = "dae5fe8d0d4a260328e4baa45b547368bd6790b3"
EXPECTED = {
    CURRENT_CORN: (62_512_316, "14851aada5bcf9f3272b23a356a6fd2f7d7d8abcb938e7ca3beb6b8ca91e8204ae8512e7df5bea319f67b350858db1f4b51d618d318b4cd0bcc38ab0e5684c3c"),
    REGION_WEIGHTS: (4_983_567, "0ebbde101209b0ebbde3ce613d0d7a7d6a19c9f0cf87f018379bff8725c10de8022d1cad3860f520dc2725b9429d61bf9e2d75e6e7543e8abfb8189fb80a1d23"),
    CROP_MASK.with_suffix(".shp"): (985_240, "b17f5c1cdb557e8e71c3f4a412c1ca1ed284a55a7398e1b226c877ad0edbc6385d6bea9727eced4880bc866e54b6c2bf5a311feb3667de26fc4ad76e2920c264"),
    CROP_MASK.with_suffix(".shx"): (108, "406d5aa3cba44f174f480c985a30f0ee9c4400170e2c913224d26f1366a3de05d1ada91b7e552e1130375cf3083b97418e34c716c9ca83399195d9d4fe1c6117"),
    CROP_MASK.with_suffix(".dbf"): (91, "3d2f0e834ac083dcea5bd30442ef49caaea3de422ab93cf59a694807bbec31cf3f8860eb66de1a02ea257494f99a2bf99836e1a57774a22f7c2ee176fe748536"),
    CROP_MASK.with_suffix(".prj"): (300, "10a7bbf6f1cbaa3c9ebc0fb054ae5be1e5f3ed0c7d8a7332a70b0b2dbe5dac5b186bc83de43e87e96349ab018f54070d501c815669c55cc3b058e518ce0339cc"),
}


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path: Path) -> dict[str, object]:
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha512": sha512(path),
    }


def stata_schema_and_rows(path: Path) -> tuple[list[str], int]:
    rows = 0
    with pd.read_stata(path, iterator=True, convert_categoricals=False) as reader:
        columns = list(reader.variable_labels())
        while True:
            try:
                chunk = reader.read(100_000)
            except StopIteration:
                break
            if chunk.empty:
                break
            rows += len(chunk)
    return columns, rows


def main() -> None:
    for path, (expected_bytes, expected_hash) in EXPECTED.items():
        if path.stat().st_size != expected_bytes or sha512(path) != expected_hash:
            raise AssertionError(f"source identity mismatch: {path}")
    corn_columns, corn_rows = stata_schema_and_rows(CURRENT_CORN)
    expected_corn_columns = [
        "iso", "adm1", "adm1_id", "adm2", "adm2_id", "year", "area_plant", "area_harv"
    ]
    if corn_columns != expected_corn_columns or corn_rows != 433_859:
        raise AssertionError("current corn_gmfd_v1 schema or row count changed")

    weight_columns = list(pd.read_csv(REGION_WEIGHTS, nrows=0).columns)
    weight_rows = sum(len(chunk) for chunk in pd.read_csv(REGION_WEIGHTS, chunksize=100_000))
    expected_weight_columns = [
        "hierid", "cassava", "corn", "cotton", "rice", "sorghum", "soy", "wheat", "allcrop",
        "cassava_buffer", "corn_buffer", "cotton_buffer", "rice_buffer", "sorghum_buffer",
        "soy_buffer", "wheat_buffer", "allcrop_buffer",
    ]
    if weight_columns != expected_weight_columns or weight_rows != 24_378:
        raise AssertionError("administrative weight table schema or row count changed")

    crop_mask = shapefile.Reader(str(CROP_MASK))
    crop_mask_fields = [field[0] for field in crop_mask.fields[1:]]
    if len(crop_mask) != 1 or crop_mask_fields != ["area"]:
        raise AssertionError("maize crop mask is not the expected one-feature dissolved mask")
    if not HISTORICAL_READY.is_file() or HISTORICAL_READY.stat().st_size != 345_639_713:
        raise AssertionError("historical prepared regression dataset is absent or changed")

    payload = {
        "schema": "hultgren_public_input_coverage_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "url": "https://gitlab.com/ClimateImpactLab/cil-ag-replication-package",
            "current_reviewed_commit": CURRENT_COMMIT,
            "current_recursive_tree_entries": 1_039,
            "current_recursive_tree_blobs": 598,
            "historical_reviewed_commit": HISTORICAL_COMMIT,
            "tree_query": "GitLab repository-tree API, recursive=true, per_page=100, pages 1-11",
        },
        "local_public_files": {
            "current_corn_gmfd_v1": {
                **identity(CURRENT_CORN),
                "rows": corn_rows,
                "columns": corn_columns,
                "role": "crop identifiers and annual planted/harvested area; no weather variables",
            },
            "administrative_crop_weights": {
                **identity(REGION_WEIGHTS),
                "rows": weight_rows,
                "columns": weight_columns,
                "role": "downstream administrative aggregation weights; not pixel-to-region weather weights",
            },
            "maize_crop_mask": {
                "components": {
                    suffix: identity(CROP_MASK.with_suffix(suffix))
                    for suffix in (".shp", ".shx", ".dbf", ".prj")
                },
                "features": len(crop_mask),
                "fields": crop_mask_fields,
                "role": "one dissolved global maize-growing-area mask; not administrative boundaries or weights",
            },
            "historical_prepared_regression_dataset": {
                "path": str(HISTORICAL_READY.relative_to(ROOT)),
                "bytes": HISTORICAL_READY.stat().st_size,
                "sha256": "06c2f0102580518a3eea88a6cd677af4636d40882452aa15b65ac7178cf9267a",
                "role": "prepared historical regression features recovered from public Git history",
            },
        },
        "current_tree_filename_search": {
            "gmfd_matches": 6,
            "gmfd_paths_are_crop_area_tables": True,
            "sage_matches": 0,
            "anycrop_matches": 0,
            "ready_dataset_matches": 0,
            "license_filename_matches": 0,
        },
        "availability_findings": {
            "published_coefficient_and_historical_feature_reproduction_possible": True,
            "primitive_historical_gmfd_daily_inputs_available": False,
            "source_sage_anycrop_pixel_weights_available": False,
            "source_future_nex_gddp_transformed_features_available": False,
            "alternative_product_transport_possible": True,
        },
        "claim_gates": {
            "exact_historical_response_reproduced": True,
            "exact_primitive_weather_pipeline_reproduced": False,
            "exact_source_spatial_aggregation_reproduced": False,
            "future_benchmark_transport_authorized_as_exact_replication": False,
            "author_input_request_still_material": True,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": payload["availability_findings"]}, indent=2))


if __name__ == "__main__":
    main()
