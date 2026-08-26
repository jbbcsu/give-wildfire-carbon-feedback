#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).with_name("estimate_us_direct_practice_precipitation_association.py")
SPEC = importlib.util.spec_from_file_location("direct_precip", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.path.insert(0, str(SCRIPT.parent))
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def main() -> None:
    config = {
        "models": {
            "heat_controls": ["stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"],
            "quantity_scale_mm": 100.0,
            "quantity_feature": "precip_mm",
            "timing_features": ["stage1_precip_share", "stage2_precip_share"],
        },
        "contrasts": {
            "quantity_increment_mm": 100.0,
            "quantity_reference_percentiles": [0.25, 0.5, 0.75],
            "timing_shift_share": 0.1,
        },
    }
    frame = pd.DataFrame({
        "stage1_tmean_c": [10.0, 11.0, 12.0, 13.0],
        "stage2_tmean_c": [20.0, 21.0, 22.0, 23.0],
        "stage3_tmean_c": [15.0, 16.0, 17.0, 18.0],
        "precip_mm": [200.0, 300.0, 400.0, 500.0],
        "stage1_precip_share": [0.2, 0.2, 0.2, 0.2],
        "stage2_precip_share": [0.3, 0.4, 0.5, 0.6],
    })
    matrix, names = MODULE.raw_design(frame, "quantity_timing", config)
    assert matrix.shape == (4, 10)
    assert names[-2:] == ["stage1_precip_share", "stage2_precip_share"]
    beta = np.zeros(len(names))
    beta[names.index("precipitation_per_100mm")] = 0.02
    beta[names.index("precipitation_per_100mm_squared")] = -0.001
    beta[names.index("stage2_precip_share")] = 0.5
    covariance = np.eye(len(names)) * 0.0004
    contrasts = MODULE.contrast_summary(frame, "quantity_timing", names, beta, covariance, config)
    assert math.isclose(
        contrasts["stage3_to_stage2_shift"]["fitted_percent_yield_difference"],
        100 * math.expm1(0.05),
    )
    assert len(contrasts["quantity_increment_contrasts"]) == 3
    assert contrasts["stage3_to_stage2_shift"]["standard_error_cluster_county_log_difference"] > 0
    assert len(contrasts["quantity_increment_contrasts"][0]["ci95_normal_percent_yield_difference"]) == 2
    try:
        MODULE.raw_design(frame, "unregistered", config)
    except ValueError as error:
        assert "unknown model" in str(error)
    else:
        raise AssertionError("unregistered model form must fail")
    print("U.S. direct-practice precipitation association tests passed")


if __name__ == "__main__":
    main()
