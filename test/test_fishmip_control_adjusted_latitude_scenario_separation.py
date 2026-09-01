#!/usr/bin/env python3
"""Synthetic failures for the latitude-band scenario-separation audit."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_fishmip_control_adjusted_latitude_scenario_separation import (  # noqa: E402
    BANDS,
    FORCINGS,
    MODELS,
    SCENARIOS,
    WINDOWS,
    evaluate,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_failure(path: Path, expected_hash: str, message: str) -> None:
    try:
        evaluate(path, expected_hash)
    except ValueError:
        return
    raise AssertionError(message)


with TemporaryDirectory() as directory:
    root = Path(directory)
    rows = []
    for scenario in SCENARIOS:
        for start, end in WINDOWS:
            for band_index, band in enumerate(BANDS):
                for forcing in FORCINGS:
                    for model in MODELS:
                        base = -0.01 * (band_index + 1)
                        rows.append({
                            "climate_scenario": scenario,
                            "future_period": {"start_year": start, "end_year": end},
                            "latitude_band": band,
                            "climate_forcing": forcing,
                            "ecosystem_model": model,
                            "band_mean_normalized_control_adjusted_change": base - (0.02 if scenario == "ssp585" else 0),
                        })
    source = {
        "schema": "fishmip_control_adjusted_latitude_band_time_windows_v1",
        "trajectory_results": rows,
        "forced_response_estimated": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    path = root / "source.json"
    path.write_text(json.dumps(source, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate(path, digest(path))
    assert len(result["trajectory_comparisons"]) == 60
    assert len(result["band_window_summaries"]) == 15
    assert all(row["all_four_ssp585_more_negative"] for row in result["band_window_summaries"])

    expect_failure(path, "0" * 64, "wrong source hash passed")
    broken = dict(source)
    broken["trajectory_results"] = rows[:-1]
    path.write_text(json.dumps(broken, sort_keys=True) + "\n", encoding="utf-8")
    expect_failure(path, digest(path), "missing trajectory passed")

print("FishMIP latitude-band scenario-separation synthetic tests passed")
