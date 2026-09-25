#!/usr/bin/env python3
"""Re-run five validated transports and export quantity/timing cell components."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


MODELS = ("gfdl", "ipsl", "mpi", "mri", "ukesm")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument(
        "--source-flavor",
        choices=("conditional_value_cell_export", "production_weighted"),
        default="conditional_value_cell_export",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output_directory.mkdir(parents=True, exist_ok=True)
    for slug in MODELS:
        source_receipt = (
            root
            / "data/provenance"
            / f"hultgren_{slug}_grid_yield_transport_{args.source_flavor}_20260924.json"
        )
        source = json.loads(source_receipt.read_text())
        weather = source["sources"]["weather"]
        output = args.output_directory / f"hultgren_{slug}_timing_component_transport_20260925.json"
        cell_output = args.output_directory / f"hultgren_{slug}_timing_component_cells_20260925.parquet"
        command = [
            sys.executable,
            str(root / "scripts/estimate_hultgren_grid_yield_contrast.py"),
            "--reference-rainfed", weather[0]["path"],
            "--reference-irrigated", weather[1]["path"],
            "--comparison-rainfed", weather[2]["path"],
            "--comparison-irrigated", weather[3]["path"],
        ]
        for record in weather:
            command.extend(("--validation", record["validation"]))
        command.extend(
            (
                "--moderators", source["sources"]["moderators"]["path"],
                "--moderator-receipt", source["sources"]["moderators"]["receipt"],
                "--author-support", source["sources"]["author_estimation_sample_support"]["path"],
                "--coefficients", source["sources"]["coefficients"]["path"],
                "--covariance", source["sources"]["covariance"]["path"],
                "--climate-model", source["climate_contrast"]["climate_model"],
                "--reference-label", source["climate_contrast"]["reference"],
                "--comparison-label", source["climate_contrast"]["comparison"],
                "--moderator-support", source["support"]["moderator_support_selection"],
                "--weather-support", source["support"].get("weather_support_selection", "full"),
                "--analysis-weights", source["sources"]["analysis_weights"]["path"],
                "--analysis-weight-column", source["sources"]["analysis_weights"]["column"],
                "--analysis-weight-receipt", source["sources"]["analysis_weights"]["receipt"],
                "--analysis-weight-label", source["support"]["analysis_weight_label"],
                "--analysis-weight-unit", source["support"]["analysis_weight_unit"],
                "--output", str(output),
                "--component-cell-output", str(cell_output),
            )
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root)
        subprocess.run(command, check=True, cwd=root, env=environment)
        print(f"completed {source['climate_contrast']['climate_model']}")


if __name__ == "__main__":
    main()
