#!/usr/bin/env python3
"""Validate and receipt a staged legacy-versus-updated agriculture run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vendor/moore_2026/lrennels-paper-2026-give-labor-ag-5d034e7"
RUNNER = ROOT / "scripts/compare_agriculture_replacement.jl"
MEMORY_GUARD = ROOT / "scripts/run_agriculture_replacement_with_memory_guard.jl"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate(summary: Path) -> dict:
    match = re.fullmatch(r"pulse(?P<year>\d+)_n(?P<n>\d+)_seed(?P<seed>\d+)", summary.parent.name)
    require(match is not None, "unexpected output directory contract")
    require(int(match["year"]) == 2025, "pulse year differs")
    require(int(match["seed"]) == 24523438, "seed differs")
    with summary.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 2, "expected exactly two version rows")
    require({row["version"] for row in rows} == {"legacy", "updated"}, "version support differs")
    require({int(row["draws"]) for row in rows} == {int(match["n"])}, "draw count differs")
    parsed = {}
    for row in rows:
        metrics = {
            name: float(row[name])
            for name in ("expected_scc_2020usd_per_tco2", "se_expected_scc", "q05", "median", "q95")
        }
        require(all(math.isfinite(value) for value in metrics.values()), "non-finite metric")
        require(metrics["se_expected_scc"] > 0, "non-positive Monte Carlo SE")
        require(metrics["q05"] <= metrics["median"] <= metrics["q95"], "quantile order differs")
        draw_path = summary.parent / f"{row['version']}_agriculture_draws_2020usd_per_tco2.csv"
        require(draw_path.is_file(), f"missing draw file: {row['version']}")
        with draw_path.open(newline="") as handle:
            draw_rows = list(csv.DictReader(handle))
        require(len(draw_rows) == int(match["n"]), f"draw file length differs: {row['version']}")
        require([int(item["trial"]) for item in draw_rows] == list(range(1, int(match["n"]) + 1)),
                f"trial index differs: {row['version']}")
        parsed[row["version"]] = {**metrics, "draw_file": {
            "path": str(draw_path.relative_to(ROOT)), "sha256": digest(draw_path)}}

    delta = parsed["updated"]["expected_scc_2020usd_per_tco2"] - parsed["legacy"]["expected_scc_2020usd_per_tco2"]
    n = int(match["n"])
    metadata_path = summary.parent / "run_metadata.csv"
    memory = {"certified": False, "reason": "run predates structured RSS capture"}
    if metadata_path.is_file():
        with metadata_path.open(newline="") as handle:
            metadata_rows = list(csv.DictReader(handle))
        require(len(metadata_rows) == 1, "run metadata row count differs")
        metadata = metadata_rows[0]
        require(metadata["julia_version"] == "1.12.5", "metadata Julia version differs")
        require(int(metadata["julia_threads"]) == 1, "metadata thread count differs")
        require(int(metadata["pulse_year"]) == 2025, "metadata pulse year differs")
        require(math.isclose(float(metadata["pulse_size"]), 0.0001), "metadata pulse size differs")
        require(int(metadata["seed"]) == 24523438, "metadata seed differs")
        require(int(metadata["draws"]) == n, "metadata draws differ")
        peak = int(metadata["process_peak_rss_bytes"])
        cap = int(metadata["max_rss_bytes"])
        require(cap == 512 * 1024**2, "metadata memory cap differs")
        require(0 < peak <= cap, "memory cap exceeded")
        memory = {"certified": True, "peak_rss_bytes": peak, "cap_bytes": cap,
                  "metadata": {"path": str(metadata_path.relative_to(ROOT)), "sha256": digest(metadata_path)}}
    promoted = n >= 10_000 and memory["certified"]
    return {
        "schema": "moore_agriculture_replacement_stage/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "full_replacement_delta" if promoted else "staged_code_path_diagnostic_not_replacement_delta",
        "source": {
            "article_doi": "10.1038/s41558-026-02749-z",
            "archive_doi": "10.5281/zenodo.21483095",
            "source_evolution_script": {
                "path": str((SOURCE / "analysis/03_ag_scc_evolution.jl").relative_to(ROOT)),
                "sha256": digest(SOURCE / "analysis/03_ag_scc_evolution.jl"),
            },
            "runner": {"path": str(RUNNER.relative_to(ROOT)), "sha256": digest(RUNNER)},
            "memory_guard": {"path": str(MEMORY_GUARD.relative_to(ROOT)), "sha256": digest(MEMORY_GUARD)},
            "manifest": {"path": str((SOURCE / "Manifest.toml").relative_to(ROOT)),
                         "sha256": digest(SOURCE / "Manifest.toml")},
        },
        "contract": {
            "pulse_year": 2025,
            "last_year": 2300,
            "pulse_size": 0.0001,
            "gas": "CO2",
            "socioeconomics": "RFF-SP",
            "fair_sampling": "random",
            "rffsp_sampling": "random",
            "seed": 24523438,
            "draws": n,
            "discount_rate_label": "2.0%",
            "currency": "2020 USD per metric ton CO2",
            "julia_version": "1.12.5",
            "julia_threads": 1,
        },
        "versions": parsed,
        "memory": memory,
        "updated_minus_legacy_mean_2020usd_per_tco2": delta,
        "inference": {
            "mean_delta_promoted": promoted,
            "draw_level_delta_allowed": False,
            "delta_interval_available": False,
            "reason": "legacy and updated agriculture use different uncertainty parameterizations; resetting the common seed does not establish paired draws",
        },
        "claim_status": (
            "like-for-like full-draw mean replacement comparison; uncertainty on the delta remains unavailable"
            if promoted else
            "the source contains both configurations and the like-for-like execution path passed; numerical delta is staging-only"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = validate(args.summary.resolve())
    require(not args.output.exists(), "fresh receipt path required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "delta": result["updated_minus_legacy_mean_2020usd_per_tco2"]}, indent=2))


if __name__ == "__main__":
    main()
