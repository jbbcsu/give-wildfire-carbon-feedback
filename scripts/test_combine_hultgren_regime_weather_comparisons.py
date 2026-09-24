#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from combine_hultgren_regime_weather_comparisons import ALL_SUPPORT, DISTRIBUTION, combine_rows


def fixture(year: int, area: float, value: float, positive_fraction: float) -> dict:
    row = {
        "harvest_year": year, "area_ha": area,
        "reference_zero_precipitation_area_fraction": 0.0,
        "comparison_zero_precipitation_area_fraction": 0.0,
        "distribution_common_positive_area_fraction": positive_fraction,
    }
    for metric in ALL_SUPPORT + DISTRIBUTION:
        row[f"reference_{metric}"] = value
        row[f"comparison_{metric}"] = value + 1.0
        row[f"delta_{metric}"] = 1.0
    return row


def main() -> None:
    result = combine_rows(fixture(2092, 3.0, 2.0, 1.0), fixture(2092, 1.0, 6.0, 0.5))
    assert result["fixed_irrigated_area_share"] == 0.25
    assert result["reference_season_total_mm"] == 3.0
    assert result["delta_season_total_mm"] == 1.0
    assert result["distribution_common_positive_area_fraction"] == 0.875
    assert result["reference_phase1_share"] == (3.0 * 2.0 + 0.5 * 6.0) / 3.5
    print("combined Hultgren regime weather comparison tests passed")


if __name__ == "__main__":
    main()
