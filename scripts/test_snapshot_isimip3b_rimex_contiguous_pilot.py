#!/usr/bin/env python3
"""Synthetic failure gates for the contiguous RIME-X pilot metadata snapshot."""
from __future__ import annotations

import copy
import tomllib

from snapshot_isimip3b_rimex_contiguous_pilot import ROOT, build_snapshot, validate_contract


contract = tomllib.loads((ROOT / "config/isimip3b_rimex_contiguous_gfdl_ssp126_pilot_v1.toml").read_text(encoding="utf-8"))
validate_contract(contract)
periods = contract["selection"]["file_periods"]


def fake_dataset(dataset_id: str) -> dict:
    selected = next(item for item in contract["datasets"] if item["dataset_id"] == dataset_id)
    variable = selected["variable"]
    files = [{
        "id": f"{variable}-{period}",
        "name": f"gfdl-esm4_r1i1p1f1_w5e5_ssp126_{variable}_global_daily_{period}.nc",
        "version": "20210512", "size": 1000 + index, "checksum": str(index + 1) * 128,
        "checksum_type": "sha512", "file_url": f"https://files.isimip.org/{variable}/{period}.nc",
    } for index, period in enumerate(periods)]
    return {
        "id": dataset_id, "version": "20210512", "public": True, "restricted": False,
        "rights": {"short": "CC0 1.0"}, "resources": [{"doi": "10.48364/ISIMIP.842396.1"}],
        "specifiers": {
            "simulation_round": "ISIMIP3b", "product": "InputData", "region": "global", "time_step": "daily",
            "climate_forcing": "gfdl-esm4", "ensemble_member": "r1i1p1f1", "climate_scenario": "ssp126",
            "climate_variable": variable,
        },
        "files": files,
    }


def fetch(url: str) -> dict:
    return fake_dataset(url.rstrip("/").split("/")[-1])


rows, audit = build_snapshot(contract, fetch)
assert len(rows) == 6 and audit["total_bytes"] == 6006
assert audit["centered_21_year_output_years"] == list(range(2042, 2050))
assert audit["all_public_unrestricted_cc0"] is True and audit["damage_or_scc_authorized"] is False


def must_fail(mutator) -> None:
    def bad_fetch(url: str) -> dict:
        dataset = copy.deepcopy(fetch(url))
        mutator(dataset)
        return dataset
    try:
        build_snapshot(contract, bad_fetch)
    except ValueError:
        return
    raise AssertionError("expected metadata gate failure")


must_fail(lambda dataset: dataset.update(public=False))
must_fail(lambda dataset: dataset["rights"].update(short="restricted"))
must_fail(lambda dataset: dataset["specifiers"].update(climate_scenario="ssp585"))
must_fail(lambda dataset: dataset["resources"].clear())
must_fail(lambda dataset: dataset["files"].pop())
must_fail(lambda dataset: dataset["files"][0].update(checksum="short"))

print("Contiguous RIME-X pilot metadata snapshot synthetic tests passed")
