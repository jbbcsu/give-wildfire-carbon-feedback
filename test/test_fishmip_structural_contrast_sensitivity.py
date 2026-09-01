#!/usr/bin/env python3
"""Synthetic tests for FishMIP structural-contrast sensitivity."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_fishmip_structural_contrast_sensitivity import (  # noqa: E402
    BANDS, FORCINGS, MODELS, SCENARIOS, WINDOWS, evaluate,
)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "source.json"
    rows = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        for window_index, (start, end) in enumerate(WINDOWS):
            for band_index, band in enumerate(BANDS):
                for forcing_index, forcing in enumerate(FORCINGS):
                    for model_index, model in enumerate(MODELS):
                        rows.append({
                            "climate_scenario": scenario,
                            "future_period": {"start_year": start, "end_year": end},
                            "latitude_band": band,
                            "climate_forcing": forcing,
                            "ecosystem_model": model,
                            "band_mean_normalized_control_adjusted_change": (
                                scenario_index + window_index + band_index / 10
                                + forcing_index * 0.2 + model_index * 0.5
                            ),
                        })
    payload = {
        "schema": "fishmip_control_adjusted_latitude_band_time_windows_v1",
        "trajectory_results": rows,
        "forced_response_estimated": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    source.write_text(json.dumps(payload, sort_keys=True) + "\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    result = evaluate(source, digest)
    assert result["status"] == "validated_factor_contrasts_structural_sensitivity_only"
    assert len(result["cells"]) == 30
    assert result["larger_rms_structural_contrast_counts"] == {
        "ecosystem_model": 30, "climate_forcing": 0, "tie": 0
    }
    assert result["scc_authorized"] is False

    broken = dict(payload)
    broken["trajectory_results"] = rows[:-1]
    source.write_text(json.dumps(broken, sort_keys=True) + "\n")
    broken_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        evaluate(source, broken_digest)
    except ValueError as error:
        assert "exact frozen product" in str(error), error
    else:
        raise AssertionError("incomplete product should fail closed")

print("FishMIP structural-contrast sensitivity synthetic tests passed")
