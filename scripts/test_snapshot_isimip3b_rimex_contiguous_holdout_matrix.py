#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from snapshot_isimip3b_rimex_contiguous_holdout_matrix import build, load_contract


root = Path(__file__).resolve().parents[1]
config, selected = load_contract(root / "config/isimip3b_rimex_contiguous_holdout_matrix_v1.toml", root)


def fake(url: str) -> dict:
    dataset_id = url.rstrip("/").split("/")[-1]
    row = next(item for item in selected if item["dataset_id"] == dataset_id)
    files = []
    for index, period in enumerate(config["selection"]["file_periods"]):
        files.append({
            "id": f"{dataset_id}-{index}", "name": f"{row['forcing']}_{row['scenario']}_{row['variable']}_{period}.nc",
            "version": "20210512", "size": index + 1, "checksum_type": "sha512", "checksum": str(index) * 128,
            "file_url": f"https://files.isimip.org/{dataset_id}/{period}.nc",
        })
    return {
        "id": dataset_id, "version": "20210512", "public": True, "restricted": False,
        "rights": {"short": "CC0 1.0"}, "resources": [{"doi": "10.48364/ISIMIP.842396.1"}], "files": files,
        "specifiers": {"simulation_round": "ISIMIP3b", "product": "InputData", "region": "global", "time_step": "daily", "climate_forcing": row["forcing"], "ensemble_member": row["member"], "climate_scenario": row["scenario"], "climate_variable": row["variable"]},
    }


rows, audit = build(config, selected, fake)
assert len(rows) == 90
assert audit["complete_templates_if_all_content_passes"] == 120
assert audit["training_templates_after_whole_esm_holdout"] == 96
assert audit["training_templates_after_whole_scenario_holdout"] == 80
assert audit["whole_esm_holdouts_passed"] is False
assert audit["damage_or_scc_authorized"] is False
print("contiguous RIME-X holdout-matrix metadata tests passed")
