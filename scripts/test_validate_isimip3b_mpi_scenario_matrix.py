#!/usr/bin/env python3
"""Synthetic identity gates for the MPI scenario-matrix validator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_isimip3b_mpi_scenario_matrix import EXPECTED_CELLS, index_cells  # noqa: E402


rows = [{"scenario": scenario, "variable": variable} for scenario, variable in sorted(EXPECTED_CELLS)]
assert set(index_cells(rows)) == EXPECTED_CELLS

try:
    index_cells(rows + [rows[0]])
except ValueError as error:
    assert "duplicates" in str(error)
else:
    raise AssertionError("duplicate matrix cell was accepted")

try:
    index_cells(rows[:-1])
except ValueError as error:
    assert "exact new cell set" in str(error)
else:
    raise AssertionError("incomplete matrix was accepted")

print("MPI scenario-matrix validator synthetic tests passed")
