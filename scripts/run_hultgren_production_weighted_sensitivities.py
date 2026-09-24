#!/usr/bin/env python3
"""Run external fixed-weight sensitivity transports from area-run manifests."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area-transport", action="append", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--weight-receipt", type=Path, required=True)
    parser.add_argument("--weight-column", default="maize_total_mt")
    parser.add_argument("--weight-label", default="fixed MapSPAM 2000 maize production")
    parser.add_argument("--weight-unit", default="mt")
    parser.add_argument("--output-tag", default="production_weighted")
    parser.add_argument("--weather-support", choices=("full", "author_minmax", "author_p01_p99"), default="full")
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get("PYTHONPATH", "")

    outputs = []
    for manifest_path in args.area_transport:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        support = manifest["support"]["moderator_support_selection"]
        weather = manifest["sources"]["weather"]
        require(len(weather) == 4, "transport manifest needs four weather inputs")
        stem = manifest_path.stem.replace("_20260924", "")
        output = args.output_directory / f"{stem}_{args.output_tag}_20260924.json"
        require(not output.exists(), f"fresh output required: {output}")
        source = manifest["sources"]
        command = [
            sys.executable, str(ROOT / "scripts/estimate_hultgren_grid_yield_contrast.py"),
            "--reference-rainfed", weather[0]["path"],
            "--reference-irrigated", weather[1]["path"],
            "--comparison-rainfed", weather[2]["path"],
            "--comparison-irrigated", weather[3]["path"],
        ]
        for item in weather:
            command.extend(["--validation", item["validation"]])
        command.extend([
            "--moderators", source["moderators"]["path"],
            "--moderator-receipt", source["moderators"]["receipt"],
            "--author-support", source["author_estimation_sample_support"]["path"],
            "--coefficients", source["coefficients"]["path"],
            "--covariance", source["covariance"]["path"],
            "--climate-model", manifest["climate_contrast"]["climate_model"],
            "--reference-label", manifest["climate_contrast"]["reference"],
            "--comparison-label", manifest["climate_contrast"]["comparison"],
            "--moderator-support", support,
            "--weather-support", args.weather_support,
            "--analysis-weights", str(args.weights),
            "--analysis-weight-column", args.weight_column,
            "--analysis-weight-receipt", str(args.weight_receipt),
            "--analysis-weight-label", args.weight_label,
            "--analysis-weight-unit", args.weight_unit,
            "--output", str(output),
        ])
        subprocess.run(command, cwd=ROOT, env=environment, check=True)
        outputs.append(str(output))
    print(json.dumps({"status": "complete", "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
