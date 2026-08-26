#!/usr/bin/env python3
"""Validate the reviewed ISIMIP3b FishMIP total-catch catalogue snapshot.

This checks catalogue metadata only. It does not validate NetCDF contents,
estimate a climate response, translate catch to welfare, or calculate an SCC.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_MODELS = {"boats": "20210906", "ecoocean": "20230317"}
EXPECTED_FORCINGS = {"gfdl-esm4", "ipsl-cm6a-lr"}
EXPECTED_EXPERIMENTS = {
    ("historical", "historical", "histsoc"),
    ("historical", "picontrol", "histsoc"),
    ("future", "picontrol", "2015soc-from-histsoc"),
    ("future", "ssp126", "2015soc-from-histsoc"),
    ("future", "ssp585", "2015soc-from-histsoc"),
}
FIXED_SPECIFIERS = {
    "simulation_round": "ISIMIP3b",
    "product": "OutputData",
    "sector": "marine-fishery_global",
    "variable": "tc",
    "region": "global",
    "time_step": "monthly",
    "bias_adjustment": "nobasd",
    "sens_scenario": "default",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    results = payload.get("results")
    require(isinstance(results, list), "catalogue results must be a list")
    require(payload.get("next") is None, "catalogue response is paginated")
    require(payload.get("count") == len(results), "catalogue response is incomplete")
    require(len(results) == 20, "reviewed catalogue snapshot must contain 20 datasets")

    seen_ids: set[str] = set()
    observed: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    total_bytes = 0
    for dataset in results:
        dataset_id = dataset.get("id", "")
        require(bool(dataset_id), "dataset id is missing")
        require(dataset_id not in seen_ids, f"duplicate dataset id {dataset_id}")
        seen_ids.add(dataset_id)
        require(dataset.get("public") is True, f"dataset {dataset_id} is not public")
        require(dataset.get("restricted") is False, f"dataset {dataset_id} is restricted")
        require(dataset.get("is_netcdf") is True, f"dataset {dataset_id} is not NetCDF")
        require(dataset.get("is_global") is True, f"dataset {dataset_id} is not global")
        require(dataset.get("rights", {}).get("short") == "CC0 1.0", f"dataset {dataset_id} license changed")

        specifiers = dataset.get("specifiers", {})
        for name, expected in FIXED_SPECIFIERS.items():
            require(specifiers.get(name) == expected, f"dataset {dataset_id} has unexpected {name}")
        model = specifiers.get("model")
        forcing = specifiers.get("climate_forcing")
        require(model in EXPECTED_MODELS, f"unexpected ecosystem model {model!r}")
        require(forcing in EXPECTED_FORCINGS, f"unexpected climate forcing {forcing!r}")
        require(dataset.get("version") == EXPECTED_MODELS[model], f"dataset {dataset_id} version changed")
        experiment = (
            specifiers.get("period"),
            specifiers.get("climate_scenario"),
            specifiers.get("soc_scenario"),
        )
        require(experiment in EXPECTED_EXPERIMENTS, f"dataset {dataset_id} has unexpected experiment {experiment}")
        key = (model, forcing)
        require(experiment not in observed.setdefault(key, set()), f"duplicate experiment {experiment} for {key}")
        observed[key].add(experiment)

        files = dataset.get("files")
        require(isinstance(files, list) and len(files) == 1, f"dataset {dataset_id} must have one file")
        file_record = files[0]
        require(file_record.get("version") == dataset.get("version"), f"file version mismatch for {dataset_id}")
        require(file_record.get("checksum_type") == "sha512", f"file checksum type changed for {dataset_id}")
        checksum = file_record.get("checksum", "")
        require(len(checksum) == 128 and all(c in "0123456789abcdef" for c in checksum), f"invalid SHA-512 for {dataset_id}")
        require(str(file_record.get("file_url", "")).startswith("https://files.isimip.org/"), f"invalid file URL for {dataset_id}")
        size = file_record.get("size")
        require(isinstance(size, int) and size > 0, f"invalid file size for {dataset_id}")
        require(size == dataset.get("size"), f"dataset/file size mismatch for {dataset_id}")
        total_bytes += size

    expected_keys = {(model, forcing) for model in EXPECTED_MODELS for forcing in EXPECTED_FORCINGS}
    require(set(observed) == expected_keys, "ecosystem-model/climate-forcing grid is incomplete")
    for key, experiments in observed.items():
        require(experiments == EXPECTED_EXPERIMENTS, f"experiment grid is incomplete for {key}")

    return {
        "datasets": len(results),
        "bytes": total_bytes,
        "models": sorted(EXPECTED_MODELS),
        "climate_forcings": sorted(EXPECTED_FORCINGS),
        "scenario_training_only": True,
        "matched_pulse": False,
        "welfare_output": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_json")
    args = parser.parse_args()
    summary = validate(Path(args.catalog_json))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
