#!/usr/bin/env python3
"""Synthetic contract checks for the MRI scenario-expansion validator."""
from __future__ import annotations

from validate_isimip3b_mri_scenario_expansion import EXPECTED_CELLS, index_cells, project_path


rows = [{"scenario": scenario, "variable": variable} for scenario, variable in sorted(EXPECTED_CELLS)]
assert set(index_cells(rows)) == EXPECTED_CELLS

try:
    index_cells(rows + [dict(rows[0])])
except ValueError as error:
    assert "duplicates" in str(error)
else:
    raise AssertionError("duplicate MRI cell was accepted")

try:
    index_cells(rows[:-1])
except ValueError as error:
    assert "exact new cell set" in str(error)
else:
    raise AssertionError("incomplete MRI cell set was accepted")

for value in ("/tmp/outside", "../outside"):
    try:
        project_path(value)
    except ValueError:
        pass
    else:
        raise AssertionError(f"unsafe provenance path was accepted: {value}")

print("MRI scenario-expansion validator synthetic tests passed")
