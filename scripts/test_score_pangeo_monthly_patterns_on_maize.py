"""Synthetic crop-climatology quantity conversion and score tests."""
import math

import numpy as np
import pandas as pd

from score_pangeo_monthly_patterns_on_maize import quantity_mean_flux, summary


def main():
    qa = np.array([[120.0]])
    qb = np.array([[12.0]])
    shares = np.full((12, 1, 1), 1/12)
    annual = [dict(year=y, gmst_value_k=280.0+(y-2000)) for y in range(2000, 2030)]
    monthly = [dict(year=y, month=m, seconds=(29 if y % 4 == 0 and m == 2 else 28 if m == 2 else 30)*86400)
               for y in range(2000, 2030) for m in range(1, 13)]
    got = quantity_mean_flux(qa, qb, shares, monthly, annual, list(range(2000, 2030)), 280.0)
    ref = math.fsum((120+12*(y-2000))/12/(29 if y % 4 == 0 else 28)/86400
                    for y in range(2000, 2030))/30
    assert math.isclose(got[1, 0, 0], ref, rel_tol=0, abs_tol=1e-18)
    fields = []
    for area in (1.0, 3.0):
        row = dict(area_ha=area, category="valid_actual_calendar_climate",
                   common_physical_support=True, actual_season_mm=10.0)
        for name, amount in (("unchanged", 10.0), ("quantity_only", 11.0), ("monthly_pattern", 9.0)):
            row.update({f"{name}_season_mm": amount, f"{name}_share_tv": 0.1,
                        f"{name}_centroid_error_days": -2.0, f"{name}_negative_months": 0})
        fields.append(row)
    score = summary(pd.DataFrame(fields), 4.0)
    assert score["common_of_valid_area_fraction"] == 1.0
    assert score["models"]["unchanged"]["season_amount_rmse_mm"] == 0
    assert score["models"]["quantity_only"]["season_amount_rmse_mm"] == 1
    assert score["models"]["monthly_pattern"]["common_area_absolute_centroid_error_days"] == 2
    print("monthly maize-calendar synthetic checks pass")


if __name__ == "__main__":
    main()
