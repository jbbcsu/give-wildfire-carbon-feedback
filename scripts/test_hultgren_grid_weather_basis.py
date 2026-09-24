#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hultgren_grid_weather_basis import assemble, crop_month_keys, write_year_batches


def main() -> None:
    assert crop_month_keys(2000, 5, 10) == tuple((2000, month) for month in range(5, 11))
    assert crop_month_keys(2000, 10, 3) == (
        (1999, 10), (1999, 11), (1999, 12), (2000, 1), (2000, 2), (2000, 3)
    )
    months = pd.date_range("1999-01-01", "2001-12-01", freq="MS")
    rain = np.column_stack([months.month.to_numpy(dtype=float), months.month.to_numpy(dtype=float)])
    dd8 = np.full((len(months), 2), 10.0)
    dd31 = np.full((len(months), 2), 2.0)
    support = pd.DataFrame([
        {"native_lat_index": 1, "native_lon_index": 2, "latitude": 89.25, "longitude": -178.75,
         "plant_month": 5, "harvest_month": 10, "mirca_area_ha": 100.0},
        {"native_lat_index": 3, "native_lon_index": 4, "latitude": 88.25, "longitude": -177.75,
         "plant_month": 10, "harvest_month": 3, "mirca_area_ha": 200.0},
    ])
    result = assemble(months, rain, dd8, dd31, support, range(2000, 2001))
    assert len(result) == 2 and result.complete.all()
    same = result.iloc[0]
    assert same.gdd == 48.0 and same.kdd == 12.0
    assert same.prcp_poly_1_bin1 == 5.0
    assert same.prcp_poly_1_bin2 == 21.0
    assert same.prcp_poly_1_bin3 == 19.0
    assert same.prcp_poly_2_bin1 == 25.0
    assert same.prcp_poly_2_bin2 == 36.0 + 49.0 + 64.0
    assert same.prcp_poly_2_bin3 == 81.0 + 100.0
    cross = result.iloc[1]
    assert cross.gdd == 48.0 and cross.kdd == 12.0 and bool(cross.cross_year)
    assert cross.prcp_poly_1_bin1 == 10.0
    assert cross.prcp_poly_1_bin2 == 24.0
    assert cross.prcp_poly_1_bin3 == 5.0
    output = Path("/private/tmp/test_hultgren_grid_weather_basis.parquet")
    if output.exists():
        output.unlink()
    rows, columns = write_year_batches(output, months, rain, dd8, dd31, support, range(2000, 2002))
    assert rows == 4 and columns == list(result.columns)
    metadata = pq.read_metadata(output)
    assert metadata.num_rows == 4 and metadata.num_row_groups == 2
    output.unlink()
    print("Hultgren grid-basis assembly tests passed")


if __name__ == "__main__":
    main()
