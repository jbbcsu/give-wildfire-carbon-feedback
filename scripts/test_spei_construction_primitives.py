#!/usr/bin/env python3
"""Unit tests for SPEI construction primitives; performs no distribution fit."""
from __future__ import annotations

import numpy as np
import pandas as pd

from spei_construction_primitives import (
    complete_monthly_water_balance,
    extraterrestrial_radiation_mj_m2_day,
    hargreaves_samani_et0_mm_day,
    right_aligned_balance_accumulation,
)


def rejected(function, expected: str, *args) -> None:
    try:
        function(*args)
    except ValueError as error:
        if expected.lower() not in str(error).lower():
            raise AssertionError(f"expected {expected!r}, got {error!r}") from error
    else:
        raise AssertionError(f"invalid primitive input accepted; expected {expected!r}")


def main() -> None:
    # FAO-56 Example 8: 3 September (J=246) at 20 degrees south is 32.2 MJ/m2/day.
    radiation = float(extraterrestrial_radiation_mj_m2_day(-20.0, 246))
    assert np.isclose(radiation, 32.2, atol=0.1)
    seasonal = extraterrestrial_radiation_mj_m2_day(
        np.array([40.0, 40.0, -40.0, -40.0]),
        np.array([172, 355, 172, 355]),
    )
    assert seasonal[0] > seasonal[1]
    assert seasonal[3] > seasonal[2]
    assert np.isfinite(extraterrestrial_radiation_mj_m2_day(0.0, 366))
    assert np.isfinite(
        extraterrestrial_radiation_mj_m2_day(np.array([89.0, -89.0]), np.array([172, 355]))
    ).all()
    rejected(extraterrestrial_radiation_mj_m2_day, "latitude", 90.0, 100)
    rejected(extraterrestrial_radiation_mj_m2_day, "day_of_year", 0.0, 0)
    rejected(extraterrestrial_radiation_mj_m2_day, "day_of_year", 0.0, 367)

    expected_et0 = 0.0023 * 0.408 * radiation * (20.0 + 17.8) * np.sqrt(20.0)
    et0 = float(hargreaves_samani_et0_mm_day(10.0, 30.0, -20.0, 246))
    assert np.isclose(et0, expected_et0, rtol=1e-12)
    assert float(hargreaves_samani_et0_mm_day(-30.0, -20.0, 45.0, 20)) == 0.0
    rejected(hargreaves_samani_et0_mm_day, "tmax_c", 11.0, 10.0, 40.0, 100)

    dates = pd.date_range("1984-01-01", "1984-02-29", freq="D")
    monthly = complete_monthly_water_balance(
        dates,
        np.ones(len(dates)),
        np.full(len(dates), 0.25),
    )
    assert monthly.month.tolist() == [pd.Timestamp("1984-01-01"), pd.Timestamp("1984-02-01")]
    assert monthly.precipitation_mm.tolist() == [31.0, 29.0]
    assert monthly.et0_mm.tolist() == [7.75, 7.25]
    assert monthly.water_balance_mm.tolist() == [23.25, 21.75]
    rejected(
        complete_monthly_water_balance,
        "consecutive",
        dates.delete(4),
        np.ones(len(dates) - 1),
        np.ones(len(dates) - 1),
    )
    rejected(
        complete_monthly_water_balance,
        "nonnegative",
        dates,
        np.concatenate(([-1.0], np.ones(len(dates) - 1))),
        np.ones(len(dates)),
    )

    six_months = pd.DataFrame(
        {
            "month": pd.date_range("1981-01-01", periods=6, freq="MS"),
            "water_balance_mm": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )
    accumulated = right_aligned_balance_accumulation(six_months, 3)
    values = accumulated.water_balance_3m_mm.to_numpy()
    assert np.isnan(values[:2]).all()
    assert values[2:].tolist() == [6.0, 9.0, 12.0, 15.0]
    gap = six_months.drop(index=2)
    rejected(right_aligned_balance_accumulation, "consecutive", gap, 3)
    rejected(right_aligned_balance_accumulation, "one of 1, 3, or 6", six_months, 12)

    print("SPEI construction primitive tests passed; no distribution or outcome fit executed")


if __name__ == "__main__":
    main()
