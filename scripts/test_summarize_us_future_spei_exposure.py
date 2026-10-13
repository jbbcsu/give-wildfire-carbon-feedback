#!/usr/bin/env python3
"""Focused synthetic tests for the U.S. future-SPEI exposure summarizer."""
from __future__ import annotations

import copy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from summarize_us_future_spei_exposure import derive_summaries, load_contract, validate_contract  # noqa: E402


def synthetic_contract() -> dict:
    return {
        "estimand": {"harvest_years": [2092, 2093], "models": ["a", "b", "c", "d", "e"],
                     "scenarios": ["ssp126", "ssp370", "ssp585"], "reference_scenario": "ssp126",
                     "windows": ["season"], "scales_months": [3]},
    }


def main() -> None:
    contract = synthetic_contract(); rows = []
    for m, model in enumerate(contract["estimand"]["models"]):
        for scenario, shift in (("ssp126", 0.0), ("ssp370", -0.2 - 0.01*m), ("ssp585", -0.5 - 0.02*m)):
            for year in contract["estimand"]["harvest_years"]:
                rows.append({"model": model, "scenario": scenario, "window": "season", "scale_months": 3,
                             "harvest_year": year, "rainfed_area_ha": 10.0,
                             "area_weighted_mean_spei": shift + 0.01*(year-2092)})
    means, contrasts, ensemble = derive_summaries(rows, contract)
    assert len(means) == 15 and len(contrasts) == 10 and len(ensemble) == 2
    primary = next(x for x in ensemble if x["contrast"] == "ssp585_minus_ssp126")
    assert primary["negative_models"] == 5 and abs(primary["equal_model_mean"] + 0.54) < 1e-12
    assert abs(primary["minimum"] + 0.58) < 1e-12 and abs(primary["maximum"] + 0.50) < 1e-12
    real = load_contract(ROOT / "config/us_future_spei_exposure_v1.toml")
    bad = copy.deepcopy(real); bad["authorization"]["fit_crop_outcomes"] = True
    try:
        validate_contract(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("open outcome gate was not rejected")
    assert not real["authorization"]["bridge_to_nass_response"]
    assert not real["authorization"]["future_yield_projection"]
    assert real["method"]["direct_rainfall_relationship"] == "competing_family_never_stacked_or_added"
    print("PASS: 8 U.S. future-SPEI synthetic and fail-closed checks")


if __name__ == "__main__":
    main()
