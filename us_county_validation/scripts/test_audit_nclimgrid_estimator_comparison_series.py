#!/usr/bin/env python3
"""Regression and failure tests for the estimator-comparison series audit."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from audit_nclimgrid_estimator_comparison_series import MONTHS, audit


root = Path(__file__).resolve().parents[2]
paths = [next((root / "data/provenance").glob(f"us_nclimgrid_county_average_estimator_comparison_{year}{month:02d}_*.json")) for year, month in MONTHS]
result = audit(paths)
assert result["comparisons"] == 56
assert len(result["summaries"]) == 8
assert result["estimators_declared_equivalent"] is False
assert result["response_damage_or_scc_authorized"] is False
assert result["minimum_correlation_all_defined_comparisons"] > 0.98
assert result["undefined_correlation_exact_constant_matches"] == 1

with tempfile.TemporaryDirectory() as directory:
    bad = Path(directory) / "bad.json"
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    payload["registered_polygon_route_replaced"] = True
    bad.write_text(json.dumps(payload), encoding="utf-8")
    try:
        audit([bad, *paths[1:]])
    except ValueError as error:
        assert "replaced" in str(error), error
    else:
        raise AssertionError("route replacement should fail closed")

print("nClimGrid estimator-comparison series tests passed")
