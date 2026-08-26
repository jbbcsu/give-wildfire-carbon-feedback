#!/usr/bin/env python3
"""Validate the reviewed ISIMIP3b FishMIP total-catch catalogue snapshot.

This checks catalogue metadata only. It does not validate NetCDF contents,
estimate a climate response, translate catch to welfare, or calculate an SCC.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
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
PLAN_FIELDS = [
    "dataset_id",
    "file_id",
    "model",
    "climate_forcing",
    "period",
    "climate_scenario",
    "soc_scenario",
    "version",
    "start_year",
    "end_year",
    "bytes",
    "sha512",
    "file_url",
    "acquisition_stage",
]
PERIOD_YEARS = {"historical": (1950, 2014), "future": (2015, 2100)}
CONTENT_SMOKE_EXPERIMENTS = {"historical", "ssp126"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def expected_stage(specifiers: dict[str, object]) -> str:
    """Return the frozen, outcome-blind acquisition stage for a dataset."""
    if (
        specifiers.get("climate_forcing") == "gfdl-esm4"
        and specifiers.get("climate_scenario") in CONTENT_SMOKE_EXPERIMENTS
    ):
        return "content_smoke"
    return "deferred_full_matrix"


def catalog_record(dataset: dict[str, object], file_record: dict[str, object]) -> dict[str, str]:
    specifiers = dataset["specifiers"]
    filename = str(file_record.get("name", ""))
    match = re.search(r"_(\d{4})_(\d{4})\.nc$", filename)
    require(match is not None, f"file name has no year range for {dataset.get('id', '')}")
    start_year, end_year = (int(value) for value in match.groups())
    require(
        (start_year, end_year) == PERIOD_YEARS.get(str(specifiers.get("period"))),
        f"file year range changed for {dataset.get('id', '')}",
    )
    return {
        "dataset_id": str(dataset["id"]),
        "file_id": str(file_record["id"]),
        "model": str(specifiers["model"]),
        "climate_forcing": str(specifiers["climate_forcing"]),
        "period": str(specifiers["period"]),
        "climate_scenario": str(specifiers["climate_scenario"]),
        "soc_scenario": str(specifiers["soc_scenario"]),
        "version": str(dataset["version"]),
        "start_year": str(start_year),
        "end_year": str(end_year),
        "bytes": str(file_record["size"]),
        "sha512": str(file_record["checksum"]),
        "file_url": str(file_record["file_url"]),
        "acquisition_stage": expected_stage(specifiers),
    }


def read_plan(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == PLAN_FIELDS, "acquisition-plan columns changed")
        rows = list(reader)
    require(len(rows) == 20, "acquisition plan must contain 20 files")
    return rows


def validate(path: Path, plan_path: Path | None = None) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    results = payload.get("results")
    require(isinstance(results, list), "catalogue results must be a list")
    require(payload.get("next") is None, "catalogue response is paginated")
    require(payload.get("count") == len(results), "catalogue response is incomplete")
    require(len(results) == 20, "reviewed catalogue snapshot must contain 20 datasets")

    seen_ids: set[str] = set()
    seen_file_ids: set[str] = set()
    seen_file_urls: set[str] = set()
    observed: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    catalog_records: list[dict[str, str]] = []
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
        file_id = file_record.get("id", "")
        require(bool(file_id), f"file id is missing for {dataset_id}")
        require(file_id not in seen_file_ids, f"duplicate file id {file_id}")
        seen_file_ids.add(file_id)
        require(file_record.get("version") == dataset.get("version"), f"file version mismatch for {dataset_id}")
        require(file_record.get("rights", {}).get("short") == "CC0 1.0", f"file license changed for {dataset_id}")
        require(file_record.get("checksum_type") == "sha512", f"file checksum type changed for {dataset_id}")
        checksum = file_record.get("checksum", "")
        require(len(checksum) == 128 and all(c in "0123456789abcdef" for c in checksum), f"invalid SHA-512 for {dataset_id}")
        file_url = str(file_record.get("file_url", ""))
        require(file_url.startswith("https://files.isimip.org/"), f"invalid file URL for {dataset_id}")
        require(file_url not in seen_file_urls, f"duplicate file URL {file_url}")
        seen_file_urls.add(file_url)
        require(file_url == f"https://files.isimip.org/{file_record.get('path', '')}", f"file URL/path mismatch for {dataset_id}")
        size = file_record.get("size")
        require(isinstance(size, int) and size > 0, f"invalid file size for {dataset_id}")
        require(size == dataset.get("size"), f"dataset/file size mismatch for {dataset_id}")
        total_bytes += size
        catalog_records.append(catalog_record(dataset, file_record))

    expected_keys = {(model, forcing) for model in EXPECTED_MODELS for forcing in EXPECTED_FORCINGS}
    require(set(observed) == expected_keys, "ecosystem-model/climate-forcing grid is incomplete")
    for key, experiments in observed.items():
        require(experiments == EXPECTED_EXPERIMENTS, f"experiment grid is incomplete for {key}")

    smoke_records = [record for record in catalog_records if record["acquisition_stage"] == "content_smoke"]
    require(len(smoke_records) == 4, "content smoke must contain four files")
    require({record["model"] for record in smoke_records} == set(EXPECTED_MODELS), "content smoke omits an ecosystem model")
    require({record["climate_forcing"] for record in smoke_records} == {"gfdl-esm4"}, "content smoke must use one forcing")
    require({record["climate_scenario"] for record in smoke_records} == CONTENT_SMOKE_EXPERIMENTS, "content smoke experiment pair changed")

    if plan_path is not None:
        plan_records = read_plan(plan_path)
        require(
            sorted(plan_records, key=lambda row: row["dataset_id"])
            == sorted(catalog_records, key=lambda row: row["dataset_id"]),
            "acquisition plan does not exactly match catalogue metadata",
        )

    return {
        "datasets": len(results),
        "bytes": total_bytes,
        "models": sorted(EXPECTED_MODELS),
        "climate_forcings": sorted(EXPECTED_FORCINGS),
        "content_smoke_datasets": len(smoke_records),
        "content_smoke_bytes": sum(int(record["bytes"]) for record in smoke_records),
        "scenario_training_only": True,
        "matched_pulse": False,
        "welfare_output": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_json")
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    summary = validate(Path(args.catalog_json), args.plan)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
