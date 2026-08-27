#!/usr/bin/env python3
"""Synthetic matrix-identity gates for the IPSL scenario evidence bundle."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_isimip3b_ipsl_scenario_matrix import EXPECTED_CELLS, index_cells  # noqa: E402


rows = [{"scenario": scenario, "variable": variable} for scenario, variable in sorted(EXPECTED_CELLS)]
assert set(index_cells(rows)) == EXPECTED_CELLS

duplicate = copy.deepcopy(rows)
duplicate[-1] = copy.deepcopy(duplicate[0])
try:
    index_cells(duplicate)
except ValueError as error:
    assert "duplicates" in str(error)
else:
    raise AssertionError("duplicate IPSL cell was accepted")

try:
    index_cells(rows[:-1])
except ValueError as error:
    assert "exact new cell set" in str(error)
else:
    raise AssertionError("incomplete IPSL cell matrix was accepted")

print("IPSL scenario-matrix synthetic tests passed")
