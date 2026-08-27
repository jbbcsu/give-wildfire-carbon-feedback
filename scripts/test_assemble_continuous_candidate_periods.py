#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).with_name("assemble_continuous_candidate_periods.py")
SPEC = importlib.util.spec_from_file_location("continuous_candidates", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def frame(start: int, end: int) -> pd.DataFrame:
    rows = []
    for year in range(start, end + 1):
        rows.append({
            "harvest_year": year, "lat": 0.25, "lon_360": 0.25, "crop": "mai",
            "yield_observed": True, "yield_t_ha": 2.0,
            "scc_authorized": False, "fit_authorized": False,
            "production_model_form_frozen": False,
            "response_basis_contract_id": "gdhy_aggregate_irrigation_distribution_candidate_v1",
        })
    return pd.DataFrame(rows)


with tempfile.TemporaryDirectory(dir=MODULE.PROJECT) as name:
    root = Path(name)
    paths = {}
    for period, (start, end) in MODULE.PERIODS.items():
        path = root / f"{period}.parquet"
        frame(start, end).to_parquet(path, index=False)
        paths[period] = path
    output = root / "continuous.parquet"
    result = MODULE.assemble(paths, crop="mai", family="direct", output=output)
    assert result["output"]["rows"] == 35
    assert set(pd.read_parquet(output).harvest_year) == set(range(1982, 2017))
    try:
        MODULE.assemble(paths, crop="mai", family="direct", output=output)
    except FileExistsError:
        pass
    else:
        raise AssertionError("overwrite must fail")
    bad = frame(*MODULE.PERIODS["middle"])
    bad.loc[0, "scc_authorized"] = True
    try:
        MODULE.validate_frame(bad, crop="mai", family="direct", period="middle")
    except ValueError as error:
        assert "opens scc_authorized" in str(error)
    else:
        raise AssertionError("opened SCC gate must fail")
    missing = frame(1990, 2010)
    try:
        MODULE.validate_frame(missing, crop="mai", family="direct", period="middle")
    except ValueError as error:
        assert "exact period" in str(error)
    else:
        raise AssertionError("missing year must fail")

print("continuous candidate period assembly tests passed")
