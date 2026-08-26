#!/usr/bin/env python3
"""Synthetic failure modes for the bounded ISIMIP3b engineering smoke."""
from __future__ import annotations

import json
import tempfile
import tomllib
from pathlib import Path

from validate_isimip3b_engineering_smoke import validate


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "data/provenance/isimip3b_paired_feature_driver.toml"
SELECTION = ROOT / "data/provenance/isimip3b_daily_catalog_selection.csv"
with PROVENANCE.open("rb") as handle:
    smoke = tomllib.load(handle)["engineering_smoke"]


def expect_failure(sidecar: Path, header: Path, message: str) -> None:
    try:
        validate(PROVENANCE, SELECTION, sidecar, header)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    sidecar = root / "smoke.json"
    header = root / "smoke.bin"
    base = {
        "path": smoke["file_path"],
        "size": smoke["file_size_bytes"],
        "checksum": smoke["file_checksum_sha512"],
        "checksum_type": "sha512",
        "specifiers": {
            "simulation_round": "ISIMIP3b",
            "product": "InputData",
            "region": "global",
            "time_step": "daily",
            "climate_scenario": "ssp370",
            "climate_forcing": "mri-esm2-0",
            "ensemble_member": "r1i1p1f1",
            "bias_adjustment": "w5e5",
            "climate_variable": "pr",
            "start_year": smoke["start_year"],
            "end_year": smoke["end_year"],
        },
    }
    sidecar.write_text(json.dumps(base), encoding="utf-8")
    header.write_bytes(bytes.fromhex(smoke["range_magic_hex"]) + b"\0" * (smoke["range_bytes_received"] - 8))
    validate(PROVENANCE, SELECTION, sidecar, header)

    bad = dict(base)
    bad["size"] = base["size"] + 1
    sidecar.write_text(json.dumps(bad), encoding="utf-8")
    expect_failure(sidecar, header, "Sidecar size mismatch")

    sidecar.write_text(json.dumps(base), encoding="utf-8")
    header.write_bytes(b"not-hdf5" + b"\0" * (smoke["range_bytes_received"] - 8))
    expect_failure(sidecar, header, "HDF5 signature")

    header.write_bytes(bytes.fromhex(smoke["range_magic_hex"]))
    expect_failure(sidecar, header, "Header byte count mismatch")

print("ISIMIP3b engineering smoke synthetic tests passed")
