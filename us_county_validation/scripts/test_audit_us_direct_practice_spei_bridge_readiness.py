#!/usr/bin/env python3
"""Synthetic checks for the fail-closed U.S. SPEI bridge readiness audit."""
from __future__ import annotations

import copy
from pathlib import Path
import sys

from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from audit_us_direct_practice_spei_bridge_readiness import audit_coverage, native_indices, validate_contract  # noqa: E402


def main() -> None:
    import tomllib
    contract = tomllib.loads((ROOT / "config/us_direct_practice_spei_bridge_readiness_v1.toml").read_text())
    validate_contract(contract)
    assert native_indices(48.25, 261.25) == (83, 162)
    assert native_indices(28.25, 263.25) == (123, 166)
    assert native_indices(38.25, 284.25) == (103, 208)
    bad = copy.deepcopy(contract); bad["authorization"]["fit_outcomes"] = True
    try:
        validate_contract(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("open outcome-fit gate was not rejected")
    bad = copy.deepcopy(contract); bad["geography"]["minimum_geometric_coverage"] = 0.9
    try:
        validate_contract(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("weakened geographic gate was not rejected")
    assert not set(contract["sample"]["outcome_columns_forbidden"]) & {
        "county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice"
    }
    coverage, weights, missing = audit_coverage(
        [("00001", box(-100.0, 40.0, -99.0, 40.5))], {(40.25, 260.25)}, 0.999
    )
    assert len(coverage) == 1 and coverage.iloc[0].available_grid_cells == 1
    assert not bool(coverage.iloc[0].passes_0_999_gate)
    assert len(weights) == 1 and abs(float(weights.iloc[0].spatial_weight_within_available) - 1.0) < 1e-15
    assert len(missing) >= 1 and 161 in set(missing.native_lon_index)
    assert 0.49 < float(coverage.iloc[0].coverage_fraction) < 0.51
    print("PASS: 12 U.S. direct-practice SPEI bridge readiness checks")


if __name__ == "__main__":
    main()
