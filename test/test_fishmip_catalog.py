#!/usr/bin/env python3
from __future__ import annotations

import copy
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
            "version": version,
            "size": size,
            "checksum_type": "sha512",
            "checksum": f"{index:0128x}",
            "file_url": f"https://files.isimip.org/example-{index}.nc",
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


def run(payload: dict[str, object], succeeds: bool) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "catalog.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            result = MODULE.validate(path)
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

print("FishMIP catalogue tests passed")
