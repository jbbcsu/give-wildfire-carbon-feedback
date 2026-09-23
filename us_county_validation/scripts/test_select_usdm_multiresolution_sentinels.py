#!/usr/bin/env python3
"""Small deterministic tests for outcome-blind sentinel selection helpers."""
from datetime import date, timedelta

import numpy as np

from select_usdm_multiresolution_sentinels import choose_counties, separated_top_dates


def main() -> None:
    start = date(2000, 1, 1)
    dates = [start + timedelta(days=7 * i) for i in range(20)]
    values = np.arange(20, dtype=float)
    picked = separated_top_dates(values, dates, 3, 28)
    assert picked == [19, 15, 11]
    counties = np.asarray(["01001", "01003", "02001", "02003"], dtype="U5")
    states = np.asarray(["01", "01", "02", "02"], dtype="U2")
    area = np.asarray([1, 2, 3, 4], dtype=float)
    p95 = np.asarray([.5, .8, .7, .6])
    maximum = np.asarray([.6, .9, .8, .7])
    chosen = choose_counties(counties, states, area, p95, maximum, 2)
    assert chosen == [(0, 1), (1, 2)]
    print("multi-resolution sentinel selection helper tests passed")


if __name__ == "__main__":
    main()
