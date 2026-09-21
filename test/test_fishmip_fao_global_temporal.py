#!/usr/bin/env python3
"""Synthetic arithmetic tests for the FishMIP--FAO temporal diagnostic."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_fishmip_fao_global_temporal import metrics, pearson, slope


years = np.arange(2000, 2005)
observed = np.asarray([1.0, 1.1, 1.2, 1.3, 1.4])
same = observed.copy()
result = metrics(years, observed, same)
assert abs(result["level_pearson"] - 1) < 1e-14
assert result["level_rmse"] == 0
assert result["first_difference_rmse"] == 0
assert result["first_difference_sign_agreement"] == 1
assert abs(slope(years, observed) - 0.1) < 1e-14
reverse = observed[::-1]
assert abs(pearson(observed, reverse) + 1) < 1e-14
try:
    pearson(np.ones(5), observed)
except ValueError:
    pass
else:
    raise AssertionError("constant correlation input accepted")
print("FishMIP--FAO global temporal synthetic checks passed")
