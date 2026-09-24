#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_hultgren_grid_weather_scenarios import compare


def fixture(scale: float) -> pd.DataFrame:
    rows = []
    for year in (2092, 2093):
        for cell, area in ((1, 1.0), (2, 3.0)):
            rows.append({
                "harvest_year": year, "native_lat_index": cell, "native_lon_index": cell,
                "plant_month": 5, "harvest_month": 10, "season_months": 6,
                "cross_year": False, "mirca_area_ha": area,
                "gdd": 100.0 * scale, "kdd": 2.0 * scale,
                "prcp_poly_1_bin1": 10.0 * scale,
                "prcp_poly_1_bin2": 30.0 * scale,
                "prcp_poly_1_bin3": 20.0 * scale,
                "prcp_poly_2_bin1": 100.0 * scale * scale,
                "prcp_poly_2_bin2": 300.0 * scale * scale,
                "prcp_poly_2_bin3": 200.0 * scale * scale,
            })
    return pd.DataFrame(rows)


def main() -> None:
    annual, pooled = compare(fixture(1.0), fixture(2.0))
    assert len(annual) == 2 and pooled["cell_years"] == 4 and pooled["years"] == 2
    assert pooled["reference_season_total_mm"] == 60.0
    assert pooled["comparison_season_total_mm"] == 120.0
    assert pooled["delta_season_total_mm"] == 60.0
    assert pooled["delta_phase1_share"] == 0.0
    assert pooled["delta_monthly_concentration"] == 0.0
    assert pooled["delta_gdd"] == 100.0
    zero_reference = fixture(1.0)
    zero_comparison = fixture(1.0)
    zero_reference.loc[0, [
        "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
        "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
    ]] = 0.0
    zero_comparison.loc[0, [
        "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
        "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
    ]] = 0.0
    annual_zero, pooled_zero = compare(zero_reference, zero_comparison)
    assert annual_zero.iloc[0].reference_zero_precipitation_area_fraction == 0.25
    assert pooled_zero["distribution_common_positive_area_year_fraction"] == 0.875
    assert pooled_zero["delta_phase1_share"] == 0.0
    print("Hultgren grid-weather scenario comparison tests passed")


if __name__ == "__main__":
    main()
