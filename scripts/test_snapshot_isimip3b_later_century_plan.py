#!/usr/bin/env python3
"""Synthetic failure gates for the later-century metadata snapshot."""

from __future__ import annotations

import copy
import csv
import tomllib
from pathlib import Path

from snapshot_isimip3b_later_century_plan import ROOT, build_snapshot, validate_config


config = tomllib.loads((ROOT / "config/isimip3b_later_century_expansion_v1.toml").read_text(encoding="utf-8"))
selected, periods = validate_config(config, ROOT / "config/isimip3b_later_century_expansion_v1.toml")
assert len(selected) == 30 and periods == ["2041_2050", "2091_2100"]


def fake_dataset(dataset_id: str) -> dict:
    row = next(item for item in selected if item["dataset_id"] == dataset_id)
    files = []
    for index, period in enumerate(periods):
        files.append({
            "id": f"{dataset_id}-{index}",
            "name": f"{row['forcing']}_{row['member']}_w5e5_{row['scenario']}_{row['variable']}_global_daily_{period}.nc",
            "version": "20210512",
            "size": 1000 + index,
            "checksum": str(index + 1) * 128,
            "checksum_type": "sha512",
            "file_url": f"https://example.invalid/{dataset_id}/{period}.nc",
        })
    return {
        "id": dataset_id,
        "version": "20210512",
        "public": True,
        "restricted": False,
        "rights": {"short": "CC0 1.0"},
        "specifiers": {
            "simulation_round": "ISIMIP3b", "product": "InputData", "region": "global", "time_step": "daily",
            "climate_forcing": row["forcing"], "ensemble_member": row["member"],
            "climate_scenario": row["scenario"], "climate_variable": row["variable"],
        },
        "files": files,
    }


def fetch(url: str) -> dict:
    return fake_dataset(url.rstrip("/").split("/")[-1])


rows, audit = build_snapshot(config, fetch)
assert len(rows) == 60 and audit["dataset_count"] == 30 and audit["file_count"] == 60
assert audit["all_public_unrestricted_cc0"] is True and audit["damage_or_scc_authorized"] is False


def must_fail(mutator) -> None:
    def bad_fetch(url: str) -> dict:
        dataset = fetch(url)
        mutator(dataset)
        return dataset
    try:
        build_snapshot(config, bad_fetch)
    except ValueError:
        return
    raise AssertionError("expected metadata gate failure")


must_fail(lambda dataset: dataset.update(public=False))
must_fail(lambda dataset: dataset["rights"].update(short="restricted"))
must_fail(lambda dataset: dataset["specifiers"].update(climate_variable="tasmax"))
must_fail(lambda dataset: dataset["files"].pop())
must_fail(lambda dataset: dataset["files"][0].update(checksum="short"))

print("Later-century ISIMIP3b metadata snapshot synthetic tests passed")
