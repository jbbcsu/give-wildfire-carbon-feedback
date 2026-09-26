#!/usr/bin/env python3
"""Small-array invariants for proportional rice-season reconciliation."""
from __future__ import annotations

import numpy as np

import audit_mirca_rice_proportional_reconciliation as module


def run() -> None:
    old_shape = module.COARSE_SHAPE
    module.COARSE_SHAPE = (1, 3)
    try:
        seasonal = {
            1: np.array([[2.0, 0.0, 1.0]]),
            2: np.array([[1.0, 0.0, 0.0]]),
            3: np.array([[1.0, 0.0, 0.0]]),
        }
        annual = np.array([[8.0, 0.0, 0.0]])
        repaired, scale, audit = module.reconcile_arrays(seasonal, annual)
        assert np.array_equal(scale, np.array([[2.0, 0.0, 0.0]]))
        assert sum(value[0, 0] for value in repaired.values()) == 8.0
        assert audit["seasonal_positive_annual_zero_cells"] == 1
        assert audit["annual_positive_seasonal_zero_cells"] == 0
        assert audit["postrepair_maximum_absolute_cell_error_ha"] == 0.0

        unsupported = np.array([[8.0, 3.0, 0.0]])
        _, _, blocked = module.reconcile_arrays(seasonal, unsupported)
        assert blocked["annual_positive_seasonal_zero_cells"] == 1
        assert blocked["annual_area_without_seasonal_support_ha"] == 3.0
    finally:
        module.COARSE_SHAPE = old_shape


if __name__ == "__main__":
    run()
    print("MIRCA rice proportional-reconciliation tests passed")
