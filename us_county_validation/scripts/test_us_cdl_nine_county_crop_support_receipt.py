#!/usr/bin/env python3
"""Integrity checks for the fixed-sample CDL crop-support receipt."""
from __future__ import annotations

import json
from pathlib import Path


root = Path(__file__).resolve().parents[2]
receipt = json.loads(
    (root / "data/provenance/us_cdl_nine_county_crop_support_20260902.json").read_text(
        encoding="utf-8"
    )
)
assert receipt["schema"] == "us_cdl_nine_county_crop_support_audit_v1"
assert receipt["sample"]["sha256"] == "b909d2384abfad18819fd149c0c9afc9fa8b05e4b5e3fec78bfbb33c1b3379da"
cells = receipt["cells"]
assert len(cells) == 18
assert len({(item["county_geoid"], item["crop"]) for item in cells}) == 18
positive = [item for item in cells if item["support"] == "positive"]
zero = [item for item in cells if item["support"] == "zero"]
assert len(positive) == 16 and len(zero) == 2
assert all(item["coverage_fraction"] == 1.0 for item in positive)
assert all(item["in_county_pixels"] == item["mapped_weather_pixels"] for item in positive)
assert {(item["county_geoid"], item["crop"]) for item in zero} == {
    ("06019", "soybeans"),
    ("16019", "soybeans"),
}
assert receipt["outcomes_read"] is False
assert receipt["crop_mask_route_replaced"] is False
assert receipt["response_estimation_authorized"] is False
assert receipt["damage_or_scc_authorized"] is False
print("fixed-sample CDL crop-support receipt tests passed")
