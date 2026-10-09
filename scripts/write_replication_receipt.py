#!/usr/bin/env python3
"""Create a tracked receipt from an ignored staged SCC replication output."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "vendor"
    / "moore_2026"
    / "lrennels-paper-2026-give-labor-ag-5d034e7"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    summary = args.summary.resolve()
    match = re.fullmatch(
        r"pulse(?P<year>\d+)_n(?P<n>\d+)_(?P<function>iso|lancet)_seed(?P<seed>\d+)",
        summary.parent.name,
    )
    if not match:
        raise SystemExit("Unexpected replication directory naming convention")

    with summary.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if {row["sector"] for row in rows} != {
        "agriculture",
        "cromar_mortality",
        "energy",
        "labor",
        "slr",
        "total",
    }:
        raise SystemExit("Sector set is incomplete")
    if {row["draws"] for row in rows} != {match.group("n")}:
        raise SystemExit("Draw count does not match directory name")

    result = {
        "schema": "labor_ag_sectoral_scc_stage_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_status": (
            "staged Monte Carlo diagnostic; not eligible as a paper reproduction "
            "until 10,000 draws and prespecified comparison checks pass"
        ),
        "source_doi": "10.5281/zenodo.21483095",
        "julia_version": "1.12.5",
        "julia_threads": 1,
        "pulse_year": int(match.group("year")),
        "draws": int(match.group("n")),
        "seed": int(match.group("seed")),
        "labor_function": match.group("function").upper(),
        "socioeconomics": "RFF-SP",
        "discount_rate_label": "2.0%",
        "currency": "2020 USD per metric ton CO2",
        "summary": {
            row["sector"]: {
                key: float(row[key])
                for key in (
                    "expected_scc_2020usd_per_tco2",
                    "se_expected_scc",
                    "q05",
                    "median",
                    "q95",
                )
            }
            for row in rows
        },
        "files": {
            "summary": {
                "path": str(summary.relative_to(ROOT)),
                "sha256": sha256(summary),
            },
            "runner": {
                "path": "scripts/replicate_sectoral_scc.jl",
                "sha256": sha256(ROOT / "scripts" / "replicate_sectoral_scc.jl"),
            },
            "manifest": {
                "path": str((SOURCE / "Manifest.toml").relative_to(ROOT)),
                "sha256": sha256(SOURCE / "Manifest.toml"),
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "output": str(args.output)}))


if __name__ == "__main__":
    main()
