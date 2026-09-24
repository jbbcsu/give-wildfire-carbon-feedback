#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hultgren_grid_climate_moderators import annual_frame


def main() -> None:
    months = pd.date_range("1999-01-01", "2000-12-01", freq="MS")
    rain = np.arange(1, 25, dtype=float)[:, None]
    tmax = (20.0 + np.arange(24, dtype=float))[:, None]
    support = pd.DataFrame([{
        "native_lat_index": 1, "native_lon_index": 2,
        "latitude": 89.25, "longitude": -178.75,
        "plant_month": 10, "harvest_month": 3,
        "mirca_area_ha": 4.0,
    }])
    result = annual_frame(2000, months, rain, tmax, support)
    # October--December 1999 plus January--March 2000.
    np.testing.assert_allclose(result.season_mean_monthly_precip_mm, np.mean([10, 11, 12, 13, 14, 15]))
    np.testing.assert_allclose(result.season_mean_monthly_tmax_c, np.mean([29, 30, 31, 32, 33, 34]))
    assert result.cross_year.iloc[0] and result.season_months.iloc[0] == 6 and result.complete.iloc[0]
    print("Hultgren grid climate moderator unit checks passed")


if __name__ == "__main__":
    main()
