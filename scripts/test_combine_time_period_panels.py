#!/usr/bin/env python3
"""Synthetic gates for contiguous period-panel combination."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from combine_time_period_panels import combine


def frame(years: list[int]) -> pd.DataFrame:
    return pd.DataFrame({
        "harvest_year": years,
        "lat": [0.25] * len(years),
        "lon_360": [0.25] * len(years),
        "crop": ["mai"] * len(years),
        "irrigation": ["noirr"] * len(years),
        "yield_t_ha": [1.0] * len(years),
    })


def expect_failure(paths: list[Path], message: str) -> None:
    try:
        combine(paths, "mai", "noirr", 1982, 1984)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    first, second = root / "first.parquet", root / "second.parquet"
    frame([1982, 1983]).to_parquet(first, index=False)
    frame([1984]).to_parquet(second, index=False)
    output = combine([first, second], "mai", "noirr", 1982, 1984)
    assert output.harvest_year.tolist() == [1982, 1983, 1984]

    frame([1983, 1984]).to_parquet(second, index=False)
    expect_failure([first, second], "overlap")
    frame([1982, 1984]).to_parquet(first, index=False)
    frame([1984]).to_parquet(second, index=False)
    expect_failure([first, second], "overlap")

    frame([1982]).to_parquet(first, index=False)
    frame([1984]).to_parquet(second, index=False)
    expect_failure([first, second], "not complete")

    bad = frame([1984]).rename(columns={"yield_t_ha": "yield_bushel_acre"})
    bad.to_parquet(second, index=False)
    expect_failure([first, second], "schema")

print("time-period panel combination synthetic tests passed")
