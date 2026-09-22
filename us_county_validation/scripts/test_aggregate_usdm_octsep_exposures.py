#!/usr/bin/env python3
"""Synthetic boundary tests for preceding-October/harvest-September aggregation."""
from __future__ import annotations

import pandas as pd

from aggregate_usdm_octsep_exposures import aggregate_state_harvest_year


def synthetic_weeks() -> pd.DataFrame:
    dates = pd.date_range("2000-09-26", "2001-10-02", freq="7D")
    rows = []
    for date in dates:
        rows.append({
            "county_geoid": "01001",
            "county_name": "Autauga County",
            "map_date": date,
            "valid_start": date,
            "valid_end": date + pd.Timedelta(days=6),
            "none_pct": 50.0,
            "d0_pct": 10.0,
            "d1_pct": 10.0,
            "d2_pct": 10.0,
            "d3_pct": 10.0,
            "d4_pct": 10.0,
        })
    return pd.DataFrame(rows)


def main() -> None:
    result = aggregate_state_harvest_year(synthetic_weeks(), "AL", 2001, ("corn_grain",))
    row = result.iloc[0]
    assert row.period_start == pd.Timestamp("2000-10-01")
    assert row.period_end == pd.Timestamp("2001-09-30")
    assert row.period_days == 365
    assert abs(row.all_category_weeks - 365 / 7) < 1e-12
    assert abs(row.none_weeks - 0.5 * 365 / 7) < 1e-12
    assert row.exposure_period == "previous_october_through_harvest_september"
    assert not bool(row.exact_published_exposure_replication)

    gapped = synthetic_weeks().drop(index=20).reset_index(drop=True)
    try:
        aggregate_state_harvest_year(gapped, "AL", 2001, ("corn_grain",))
    except ValueError as error:
        assert "gapped or overlapping" in str(error)
    else:
        raise AssertionError("gapped interval sequence was accepted")
    print("October--September exposure aggregation tests passed")


if __name__ == "__main__":
    main()
