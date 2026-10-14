#!/usr/bin/env python3
"""Focused fail-closed tests for the 11-cell historical SPEI extension."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_us_spei_bridge_historical_cells as target  # noqa: E402


def main() -> None:
    path = ROOT / "config/us_spei_bridge_missing_cells_v1.csv"
    cells = target.load_cells(path)
    assert len(cells) == 11
    assert len(cells.drop_duplicates(["native_lat_index", "native_lon_index"])) == 11
    assert list(cells.iloc[0][["native_lat_index", "native_lon_index"]]) == [83.0, 162.0]
    assert list(cells.iloc[-1][["native_lat_index", "native_lon_index"]]) == [123.0, 167.0]
    assert target.EXPECTED_MONTHS[0].strftime("%Y-%m") == "1981-01"
    assert target.EXPECTED_MONTHS[-1].strftime("%Y-%m") == "2019-12"
    assert len(target.EXPECTED_MONTHS) == 468
    source = (ROOT / "scripts/build_us_spei_bridge_historical_cells.py").read_text()
    assert "yield_bu_acre" not in source and "read_parquet" not in source
    with tempfile.TemporaryDirectory() as directory:
        changed = Path(directory) / "cells.csv"
        changed.write_bytes(path.read_bytes() + b"\n")
        try:
            target.load_cells(changed)
        except ValueError:
            pass
        else:
            raise AssertionError("changed cell inventory was accepted")
    print("PASS: 9 historical 11-cell SPEI bridge tests")


if __name__ == "__main__":
    main()
