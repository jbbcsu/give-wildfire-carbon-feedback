#!/usr/bin/env python3
"""Synthetic gates for the pinned ISIMIP3b daily catalogue selection."""
from __future__ import annotations

import copy

from select_isimip3b_daily_catalog import (
    EXPECTED_MEMBERS,
    EXPECTED_YEARS,
    SCENARIOS,
    VARIABLES,
    validate_payloads,
)


def payloads() -> dict[tuple[str, str], dict]:
    output = {}
    for scenario in SCENARIOS:
        start, end = EXPECTED_YEARS[scenario]
        results = []
        for forcing, member in EXPECTED_MEMBERS.items():
            name = f"{forcing}_{member}_w5e5_{scenario}"
            results.append(
                {
                    "id": f"{forcing}-{scenario}-{VARIABLES.index('pr')}",
                    "name": name,
                    "version": "20210512",
                    "size": 10,
                    "public": True,
                    "restricted": False,
                    "rights": {"short": "CC0 1.0"},
                    "specifiers": {
                        "simulation_round": "ISIMIP3b",
                        "product": "InputData",
                        "region": "global",
                        "time_step": "daily",
                        "climate_scenario": scenario,
                        "climate_variable": "pr",
                        "climate_forcing": forcing,
                        "ensemble_member": member,
                        "bias_adjustment": "w5e5",
                    },
                    "files": [
                        {
                            "name": f"{name}_{start}_{end}.nc",
                            "version": "20210512",
                            "size": 10,
                            "checksum_type": "sha512",
                            "checksum": "a" * 128,
                            "file_url": f"https://files.isimip.org/{name}_{start}_{end}.nc",
                        }
                    ],
                    "resources": [{"doi": "10.48364/ISIMIP.842396.1"}],
                }
            )
        for variable in VARIABLES:
            variable_results = copy.deepcopy(results)
            for item in variable_results:
                item["id"] = f"{item['specifiers']['climate_forcing']}-{scenario}-{variable}"
                item["specifiers"]["climate_variable"] = variable
                item["name"] += f"_{variable}"
                item["files"][0]["name"] = f"{item['name']}_{start}_{end}.nc"
            output[(scenario, variable)] = {"count": 5, "results": variable_results}
    return output


def expect_failure(source: dict[tuple[str, str], dict], message: str) -> None:
    try:
        validate_payloads(source)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


valid = payloads()
rows = validate_payloads(valid)
assert len(rows) == 80
assert len({row["dataset_id"] for row in rows}) == 80

case = copy.deepcopy(valid)
case[("ssp370", "pr")]["results"].pop()
case[("ssp370", "pr")]["count"] = 4
expect_failure(case, "expected exactly five")

case = copy.deepcopy(valid)
case[("ssp370", "tas")]["results"][0]["specifiers"]["ensemble_member"] = "r9i9p9f9"
expect_failure(case, "unexpected forcing/member")

case = copy.deepcopy(valid)
case[("ssp585", "tasmax")]["results"][0]["files"][0]["checksum"] = "bad"
expect_failure(case, "API SHA-512")

case = copy.deepcopy(valid)
case[("historical", "tasmin")]["results"][0]["files"][0]["name"] = "bad_1851_2014.nc"
expect_failure(case, "expected years")

case = copy.deepcopy(valid)
case[("ssp126", "pr")]["results"][0]["restricted"] = True
expect_failure(case, "not public/unrestricted")

print("ISIMIP3b daily catalogue selection synthetic tests passed")
