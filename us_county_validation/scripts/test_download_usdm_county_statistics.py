#!/usr/bin/env python3
"""Synthetic checks for fail-closed USDM acquisition and identity pinning."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("download_usdm_county_statistics.py")
HEADER = (
    "MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4,"
    "ValidStart,ValidEnd,StatisticFormatID\n"
)


def payload(*, state: str = "IA", year: int = 2001, duplicate: bool = False) -> bytes:
    row = (
        f"{year}0102,19001,Adair County,{state},100.00,0.00,0.00,0.00,0.00,0.00,"
        f"{year}-01-02,{year}-01-08,2\n"
    )
    return (HEADER + row + (row if duplicate else "")).encode()


def run(out_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state",
            "IA",
            "--year-min",
            "2001",
            "--year-max",
            "2001",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    target = root / "usdm_county_area_pct_IA_2001.csv"
    target.write_bytes(payload())

    first = run(root)
    assert first.returncode == 0, first.stderr
    records = [json.loads(line) for line in (root / "MANIFEST.jsonl").read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["status"] == "existing_validated"
    assert records[0]["retrieved_utc"] is None
    assert records[0]["rows"] == 1
    assert records[0]["counties"] == 1
    assert records[0]["map_date_min"] == "2001-01-02"

    second = run(root)
    assert second.returncode == 0, second.stderr
    assert len((root / "MANIFEST.jsonl").read_text().splitlines()) == 2

    # A syntactically valid but silently changed local file must not supersede
    # the identity established by the first check.
    changed = payload().replace(b"100.00", b"099.99")
    target.write_bytes(changed)
    mismatch = run(root)
    assert mismatch.returncode != 0
    assert "identity mismatch" in mismatch.stderr
    assert len((root / "MANIFEST.jsonl").read_text().splitlines()) == 2

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    target = root / "usdm_county_area_pct_IA_2001.csv"
    malformed_cases = [
        (b"<html>upstream error</html>", "missing columns"),
        (payload(state="NE"), "expected IA"),
        (payload(year=2002), "does not overlap requested year 2001"),
        (payload(duplicate=True), "duplicate county-week key"),
    ]
    for bad_payload, expected_error in malformed_cases:
        target.write_bytes(bad_payload)
        result = run(root)
        assert result.returncode != 0
        assert expected_error in result.stderr, result.stderr
        assert not (root / "MANIFEST.jsonl").read_text().strip()

print("USDM county-statistics download tests passed")
