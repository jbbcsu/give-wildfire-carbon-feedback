#!/usr/bin/env python3
"""Synthetic failure checks for matched FAIR temperature-path validation."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from validate_give_fair_temperature_paths import validate


CONFIG = """
schema = "give_fair_temperature_path_smoke_config_v1"
role = "matched_core_fair_temperature_path_numerical_gate_not_feature_response_damage_or_scc"
core_root = "."
model_start_year = 2000
model_end_year = 2003
pulse_year = 2001
pulse_sizes_gtc = [0.0, 0.0001, 0.00005, 0.000025]
convergence_rtol = 0.05

[limitations]
damage_or_scc_authorized = false
"""


def frame() -> pd.DataFrame:
    rows = []
    for scale in (0.0, 1e-4, 5e-5, 2.5e-5):
        for year in range(2000, 2004):
            difference = 0.0 if year <= 2001 else scale * 0.1
            rows.append({
                "year": year,
                "pulse_size_gtc": scale,
                "baseline_temperature_c": 1.0,
                "pulse_temperature_c": 1.0 + difference,
                "difference_k": difference,
            })
    return pd.DataFrame(rows)


def expect_failure(config: Path, path: Path, data: pd.DataFrame, message: str) -> None:
    data.to_csv(path, index=False)
    try:
        validate(config, path)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config = root / "config.toml"
    paths = root / "paths.csv"
    config.write_text(CONFIG, encoding="utf-8")
    good = frame()
    good.to_csv(paths, index=False)
    assert validate(config, paths)["result"] == "passed"

    case = good.copy()
    case.loc[(case["pulse_size_gtc"] == 0) & (case["year"] == 2003), "pulse_temperature_c"] += 0.01
    case.loc[(case["pulse_size_gtc"] == 0) & (case["year"] == 2003), "difference_k"] += 0.01
    expect_failure(config, paths, case, "zero-pulse")

    case = good.copy()
    mask = (case["pulse_size_gtc"] == 1e-4) & (case["year"] == 2001)
    case.loc[mask, "pulse_temperature_c"] += 0.01
    case.loc[mask, "difference_k"] += 0.01
    expect_failure(config, paths, case, "before the pulse")

print("matched FAIR temperature-path synthetic tests passed")
