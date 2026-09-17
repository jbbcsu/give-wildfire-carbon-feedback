"""Synthetic amount, annual, share and physical-support scoring checks."""
import math

import numpy as np

from evaluate_pangeo_monthly_pattern_holdout import aggregate, score_year


def main():
    area = np.array([[1.0, 3.0]])
    actual = np.ones((12, 1, 2))
    pattern = actual.copy(); pattern[0] += 1; pattern[1] -= 1
    predictions = dict(unchanged=actual.copy(), quantity_only=2*actual,
                       monthly_pattern=pattern)
    one = dict(year=2001, **score_year(actual, predictions, area, np))
    pooled = aggregate([one])
    assert pooled["common_valid_area_fraction"] == 1
    assert pooled["models"]["unchanged"]["monthly_amount_rmse_mm"] == 0
    assert pooled["models"]["quantity_only"]["monthly_amount_rmse_mm"] == 1
    assert pooled["models"]["quantity_only"]["annual_amount_rmse_mm"] == 12
    assert math.isclose(pooled["models"]["monthly_pattern"]["monthly_amount_rmse_mm"], math.sqrt(2/12))
    assert math.isclose(pooled["models"]["monthly_pattern"]["common_area_mean_month_share_tv"], 1/12)
    broken = pattern.copy(); broken[1, 0, 0] = -1
    two = dict(year=2002, **score_year(actual, {**predictions, "monthly_pattern": broken}, area, np))
    assert math.isclose(two["common_valid_area_m2"]/two["area_sum_m2"], 0.75)
    assert two["metrics"]["monthly_pattern"]["negative_cell_months"] == 1
    print("monthly climate holdout synthetic scoring checks pass")


if __name__ == "__main__":
    main()
