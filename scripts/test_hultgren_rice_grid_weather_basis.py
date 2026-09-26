#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hultgren_rice_grid_weather_basis import WEATHER, assemble_year, crop_month_keys


def main() -> None:
    assert crop_month_keys(2000, 5, 10) == tuple((2000, month) for month in range(5, 11))
    assert crop_month_keys(2000, 10, 3) == (
        (1999, 10), (1999, 11), (1999, 12), (2000, 1), (2000, 2), (2000, 3)
    )
    months = pd.date_range("1999-01-01", "2000-12-01", freq="MS")
    values = months.month.to_numpy(dtype=float)
    arrays = {
        "rain": np.column_stack([values, values]),
        "dd14": np.full((len(months), 2), 10.0),
        "dd30": np.full((len(months), 2), 2.0),
        "monthly_tmin": np.full((len(months), 2), 12.0),
    }
    support = pd.DataFrame(
        [
            {"native_lat_index": 1, "native_lon_index": 2, "latitude": 89.25, "longitude": -178.75,
             "plant_month": 5, "harvest_month": 10},
            {"native_lat_index": 3, "native_lon_index": 4, "latitude": 88.25, "longitude": -177.75,
             "plant_month": 10, "harvest_month": 3},
        ]
    )
    result = assemble_year(2000, months, arrays, support, "ri1_noirr")
    assert len(result) == 2 and result.complete.all()
    assert set(WEATHER) <= set(result.columns)
    same = result.iloc[0]
    assert same.gdd == 48.0 and same.kdd == 12.0 and same.tmin == 72.0
    assert same.prcp_poly_1_bin1 == 11.0
    assert same.prcp_poly_1_bin2 == 24.0
    assert same.prcp_poly_1_bin3 == 10.0
    assert same.prcp_poly_2_bin1 == 25.0 + 36.0
    assert same.prcp_poly_2_bin2 == 49.0 + 64.0 + 81.0
    assert same.prcp_poly_2_bin3 == 100.0
    cross = result.iloc[1]
    assert bool(cross.cross_year) and cross.tmin == 72.0
    assert cross.prcp_poly_1_bin1 == 21.0
    assert cross.prcp_poly_1_bin2 == 15.0
    assert cross.prcp_poly_1_bin3 == 3.0
    assert not any("area" in column or "weight" in column for column in result.columns)
    print("Hultgren rice grid-weather assembly tests passed")


if __name__ == "__main__":
    main()
