#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_fishmip_control_adjusted_matrix import ADJUSTED_ROLE, DRIFT_ROLE, audit  # noqa: E402


def write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def periods(kind: str, offset: float = 0.0) -> list[dict[str, object]]:
    years = {"near": (2021, 2030), "mid": (2041, 2050), "late": (2081, 2090)}
    output = []
    for index, period in enumerate(("near", "mid", "late")):
        start, end = years[period]
        control = -0.1 - index * 0.01
        row: dict[str, object] = {"id": period, "start_year": start, "end_year": end}
        if kind == "drift":
            row["relative_change_from_reference"] = control
        else:
            row["control_relative_change"] = control
            row["difference_in_relative_changes"] = offset - 0.01 * index
        output.append(row)
    return output


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    drift_paths = []
    adjusted_paths = []
    for forcing in ("gfdl-esm4", "ipsl-cm6a-lr"):
        for model in ("boats", "ecoocean"):
            drift_paths.append(write(root / f"{forcing}_{model}_drift.json", {
                "result": "passed", "role": DRIFT_ROLE, "climate_forcing": forcing, "model": model,
                "common_finite_grid_cells": 10, "reference_start_year": 2005, "reference_end_year": 2014,
                "reporting_periods": periods("drift"),
            }))
            for scenario in ("ssp126", "ssp585"):
                offset = -0.02 if scenario == "ssp585" else (0.01 if model == "boats" else -0.01)
                adjusted_paths.append(write(root / f"{forcing}_{model}_{scenario}.json", {
                    "result": "passed", "role": ADJUSTED_ROLE, "climate_forcing": forcing, "model": model,
                    "forced_scenario": scenario, "common_finite_grid_cells": 10,
                    "reference_start_year": 2005, "reference_end_year": 2014,
                    "reporting_periods": periods("adjusted", offset),
                }))

    result = audit(drift_paths, adjusted_paths)
    assert result["result"] == "passed"
    assert result["matrix_cell_count"] == 8
    late_ssp585 = next(row for row in result["sign_summary"] if row["scenario"] == "ssp585" and row["period"] == "late")
    assert late_ssp585["all_negative"] is True
    try:
        audit(drift_paths[:-1], adjusted_paths)
    except ValueError as error:
        assert "four drift" in str(error)
    else:
        raise AssertionError("incomplete matrix should fail")

print("FishMIP control-adjusted matrix audit tests passed")
