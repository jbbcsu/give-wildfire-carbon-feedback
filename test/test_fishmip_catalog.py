#!/usr/bin/env python3
from __future__ import annotations

import copy
import csv
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_fishmip_catalog.py"
SPEC = importlib.util.spec_from_file_location("fishmip_catalog", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def dataset(model: str, forcing: str, experiment: tuple[str, str, str], index: int) -> dict[str, object]:
    period, climate_scenario, soc_scenario = experiment
    version = MODULE.EXPECTED_MODELS[model]
    size = 1000 + index
    start_year, end_year = MODULE.PERIOD_YEARS[period]
    filename = f"{model}_{forcing}_{period}_{climate_scenario}_{start_year}_{end_year}.nc"
    file_path = f"ISIMIP3b/OutputData/marine-fishery_global/{model}/{forcing}/{period}/{filename}"
    return {
        "id": f"dataset-{index}",
        "version": version,
        "size": size,
        "public": True,
        "restricted": False,
        "is_netcdf": True,
        "is_global": True,
        "rights": {"short": "CC0 1.0"},
        "specifiers": {
            **MODULE.FIXED_SPECIFIERS,
            "model": model,
            "climate_forcing": forcing,
            "period": period,
            "climate_scenario": climate_scenario,
            "soc_scenario": soc_scenario,
        },
        "files": [{
            "id": f"file-{index}",
            "name": filename,
            "path": file_path,
            "version": version,
            "size": size,
            "checksum_type": "sha512",
            "checksum": f"{index:0128x}",
            "file_url": f"https://files.isimip.org/{file_path}",
            "rights": {"short": "CC0 1.0"},
        }],
    }


records = []
index = 1
for model in sorted(MODULE.EXPECTED_MODELS):
    for forcing in sorted(MODULE.EXPECTED_FORCINGS):
        for experiment in sorted(MODULE.EXPECTED_EXPERIMENTS):
            records.append(dataset(model, forcing, experiment, index))
            index += 1
valid = {"count": len(records), "next": None, "previous": None, "results": records}


def run(payload: dict[str, object], succeeds: bool, plan_rows: list[dict[str, str]] | None = None) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "catalog.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        plan_path = None
        if plan_rows is not None:
            plan_path = Path(directory) / "plan.csv"
            with plan_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=MODULE.PLAN_FIELDS)
                writer.writeheader()
                writer.writerows(plan_rows)
        try:
            result = MODULE.validate(path, plan_path)
        except ValueError:
            if succeeds:
                raise
        else:
            if not succeeds:
                raise AssertionError(f"validation unexpectedly passed: {result}")


run(valid, True)
run({**valid, "next": "next-page"}, False)
run({**valid, "count": 21}, False)

changed = copy.deepcopy(valid)
changed["results"][0]["public"] = False
run(changed, False)

changed = copy.deepcopy(valid)
changed["results"][0]["specifiers"]["climate_scenario"] = "ssp370"
run(changed, False)

changed = copy.deepcopy(valid)
changed["results"][0]["files"][0]["checksum"] = "not-a-checksum"
run(changed, False)

changed = copy.deepcopy(valid)
changed["results"][0]["files"][0]["rights"]["short"] = "unknown"
run(changed, False)

changed = copy.deepcopy(valid)
changed["results"][0]["files"][0]["name"] = "file_without_years.nc"
run(changed, False)

valid_plan = [MODULE.catalog_record(record, record["files"][0]) for record in valid["results"]]
run(valid, True, valid_plan)

changed_plan = copy.deepcopy(valid_plan)
changed_plan[0]["sha512"] = "0" * 128
run(valid, False, changed_plan)

print("FishMIP catalogue tests passed")
