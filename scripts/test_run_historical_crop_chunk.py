#!/usr/bin/env python3
"""Argument-gate tests for the resumable historical chunk orchestrator."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "scripts" / "run_historical_crop_chunk.sh"


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    inputs = []
    for name in ("pr.nc", "tas.nc", "calendar.nc"):
        path = root / name
        path.touch()
        inputs.append(path)
    gdhy = root / "gdhy"
    gdhy.mkdir()
    prefix = [str(SCRIPT), *(str(path) for path in inputs), str(gdhy), "mai", "noirr"]

    reversed_years = subprocess.run(
        [*prefix, "2016", "2012", "2011_2019"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert reversed_years.returncode == 2
    assert "ordered four-digit years" in reversed_years.stderr

    unsafe_tag = subprocess.run(
        [*prefix, "2012", "2016", "../../outside"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert unsafe_tag.returncode == 2
    assert "PERIOD_TAG" in unsafe_tag.stderr

    unsafe_crop = subprocess.run(
        [str(SCRIPT), *(str(path) for path in inputs), str(gdhy), "../mai", "noirr", "2012", "2016", "2011_2019"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert unsafe_crop.returncode == 2
    assert "Unsupported crop code" in unsafe_crop.stderr

    invalid_chunk = subprocess.run(
        [*prefix, "2012", "2016", "2011_2019", "7"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert invalid_chunk.returncode == 2
    assert "divisor of 360" in invalid_chunk.stderr

    nonnumeric_chunk = subprocess.run(
        [*prefix, "2012", "2016", "2011_2019", "invalid"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert nonnumeric_chunk.returncode == 2
    assert "divisor of 360" in nonnumeric_chunk.stderr

print("historical chunk orchestrator argument-gate tests passed")
