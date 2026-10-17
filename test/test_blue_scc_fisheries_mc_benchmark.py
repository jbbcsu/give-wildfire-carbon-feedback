#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_blue_scc_fisheries_mc_benchmark.py"
SPEC = importlib.util.spec_from_file_location("fish_mc", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def fixture() -> tuple[list[dict[str, object]], dict[str, object]]:
    components = [("Fisheries", "consumption"), ("Fisheries", "usenm"), ("Total", "total")]
    rows = []
    for draw, values in {"9999": [1.0, 10.0, 20.0], "0": [2.0, 20.0, 40.0], "1": [4.0, 40.0, 80.0]}.items():
        for (capital, valuation), value in zip(components, values):
            rows.append({"t": 2020, "scc": value, "oc_capital": capital, "valuation": valuation, "id": draw})
    config = {"expected": {
        "year": 2020, "row_count": 9, "id_count": 3, "monte_carlo_draw_count": 2,
        "baseline_id": "9999", "component_count": 3,
        "fisheries_market_valuation": "consumption", "fisheries_nutrition_valuation": "usenm",
    }}
    return rows, config


def main() -> None:
    rows, config = fixture()
    result = MODULE.summarize(rows, config)
    assert result["published_deterministic_baseline_usd_per_tco2"]["combined"] == 11.0
    assert result["published_monte_carlo_usd_per_tco2"]["market"]["mean"] == 3.0
    assert result["published_monte_carlo_usd_per_tco2"]["combined"]["median"] == 33.0
    try:
        MODULE.summarize(rows[:-1], config)
    except ValueError as error:
        assert "row count" in str(error)
    else:
        raise AssertionError("incomplete artifact must fail")
    duplicate = rows.copy()
    duplicate[-1] = duplicate[-2]
    try:
        MODULE.summarize(duplicate, config)
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate draw-component must fail")
    print("Blue-SCC fisheries Monte Carlo benchmark tests passed")


if __name__ == "__main__":
    main()

