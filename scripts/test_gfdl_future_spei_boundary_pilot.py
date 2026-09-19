#!/usr/bin/env python3
"""Outcome-free registration tests for the bounded GFDL SPEI pilot."""

from build_gfdl_future_spei_boundary_pilot import registered_sources


records = registered_sources()
assert len(records) == 12
assert set(records) == {
    (scenario, variable)
    for scenario in ("historical", "ssp126", "ssp370", "ssp585")
    for variable in ("pr", "tasmin", "tasmax")
}
assert all(record["bytes"] > 0 for record in records.values())
assert all(len(record["sha512"]) == 128 for record in records.values())
assert len({record["name"] for record in records.values()}) == 12

print("GFDL future SPEI source-registration tests passed")
