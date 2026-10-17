#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_fisheries_market_give_target.py"
SPEC = importlib.util.spec_from_file_location("fish_target", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def main() -> None:
    config = {
        "source_conventions": {
            "pulse_year": 2020, "pulse_size_tco2": 1e6,
            "output_unit": "2020_USD_per_tCO2", "deflator_2005_numerator": 113.647,
            "deflator_2005_denominator": 87.504, "deterministic_prtp": 0.015,
            "deterministic_eta": 1.45, "mc_prtp_min": 0.01, "mc_prtp_max": 0.02,
            "mc_eta_min": 1.1, "mc_eta_max": 1.6,
        },
        "give_target_conventions": {
            "pulse_year": 2020, "pulse_size_gtc": 1e-4, "carbon_to_co2_ratio": 44/12,
            "output_unit": "2020_USD_per_tCO2", "deflator_2005_numerator": 113.648,
            "deflator_2005_denominator": 87.504, "prtp": math.exp(0.001972641)-1,
            "eta": 1.244458999,
        },
        "accounting_boundary": {
            "source_measure": "profit", "required_give_measure": "direct_consumer_plus_producer_surplus"
        },
    }
    benchmark = {"result": {
        "published_monte_carlo_usd_per_tco2": {"market": {"p05": 1.0, "median": 2.0, "p95": 3.0}},
        "published_deterministic_baseline_usd_per_tco2": {"market": 2.5},
    }}
    result = MODULE.harmonize(config, benchmark)
    factor = 113.648 / 113.647
    assert math.isclose(result["market_external_sensitivity_2020_usd_per_tco2"]["published_mc_median"], 2*factor)
    assert math.isclose(result["harmonization"]["give_pulse_tco2"], 1e-4*1e9*44/12)
    assert result["harmonization"]["per_tco2_unit_factor"] == 1.0
    assert result["harmonization"]["pulse_year_match"] is True
    assert result["harmonization"]["discount_parameters_match"] is False
    assert result["harmonization"]["give_discount_target_inside_source_mc_support"] is False
    assert result["harmonization"]["welfare_measure_match"] is False
    assert result["target_interface"]["additive_eligible"] is False
    assert result["nutrition_nonmarket"]["role"] == "nonadditive_literature_bound"
    print("Fisheries market GIVE-target tests passed")


if __name__ == "__main__":
    main()

