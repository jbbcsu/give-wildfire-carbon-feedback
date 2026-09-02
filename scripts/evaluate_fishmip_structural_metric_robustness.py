#!/usr/bin/env python3
"""Compare RMS and mean-absolute FishMIP structural-contrast rankings."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


SOURCE_SHA256 = "547ecc9a6cb5858dae1d68b3704fd715405cfb97330ddf34600ffddf35c74836"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def winner(left: float, right: float) -> str:
    require(np.isfinite(left) and np.isfinite(right) and left >= 0 and right >= 0, "structural metrics are invalid")
    if left > right:
        return "ecosystem_model"
    if right > left:
        return "climate_forcing"
    return "tie"


def summarize_cell(cell: dict[str, object]) -> dict[str, object]:
    ecosystem = cell["ecosystem_model_contrast_ecoocean_minus_boats"]
    climate = cell["climate_forcing_contrast_ipsl_minus_gfdl"]
    ecosystem_values = np.asarray(ecosystem["contrasts"], dtype=float)
    climate_values = np.asarray(climate["contrasts"], dtype=float)
    require(ecosystem_values.shape == climate_values.shape == (2,), "each structural axis requires two contrasts")
    require(np.isfinite(ecosystem_values).all() and np.isfinite(climate_values).all(), "contrast values are nonfinite")
    ecosystem_mean = float(np.abs(ecosystem_values).mean())
    climate_mean = float(np.abs(climate_values).mean())
    ecosystem_rms = float(np.sqrt(np.mean(ecosystem_values**2)))
    climate_rms = float(np.sqrt(np.mean(climate_values**2)))
    require(abs(ecosystem_mean - float(ecosystem["mean_absolute_contrast"])) <= 1e-12, "ecosystem mean-absolute contrast changed")
    require(abs(climate_mean - float(climate["mean_absolute_contrast"])) <= 1e-12, "climate mean-absolute contrast changed")
    require(abs(ecosystem_rms - float(ecosystem["root_mean_square_contrast"])) <= 1e-12, "ecosystem RMS contrast changed")
    require(abs(climate_rms - float(climate["root_mean_square_contrast"])) <= 1e-12, "climate RMS contrast changed")
    rms_winner = winner(ecosystem_rms, climate_rms)
    mean_winner = winner(ecosystem_mean, climate_mean)
    require(rms_winner == cell["larger_rms_structural_contrast"], "source RMS winner changed")
    return {
        "climate_scenario": cell["climate_scenario"],
        "future_period": cell["future_period"],
        "latitude_band": cell["latitude_band"],
        "rms": {"ecosystem_model": ecosystem_rms, "climate_forcing": climate_rms, "larger_axis": rms_winner},
        "mean_absolute": {"ecosystem_model": ecosystem_mean, "climate_forcing": climate_mean, "larger_axis": mean_winner},
        "larger_axis_agrees_across_metrics": rms_winner == mean_winner,
    }


def evaluate(source_path: Path) -> dict[str, object]:
    observed = sha256(source_path)
    require(observed == SOURCE_SHA256, "source receipt SHA-256 changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    require(source.get("schema") == "fishmip_structural_contrast_sensitivity_v1", "source schema changed")
    require(source.get("status") == "validated_factor_contrasts_structural_sensitivity_only", "source status changed")
    for gate in ("probability_or_variance_decomposition", "forced_response_estimated", "country_or_eez_allocation_performed", "matched_co2_pulse", "welfare_estimated", "damage_estimated", "scc_authorized"):
        require(source.get(gate) is False, f"source evidence boundary changed: {gate}")
    cells = [summarize_cell(cell) for cell in source.get("cells", [])]
    require(len(cells) == 30, "exact 30-cell product changed")
    keys = {
        (cell["climate_scenario"], cell["future_period"]["start_year"], cell["future_period"]["end_year"], cell["latitude_band"])
        for cell in cells
    }
    require(len(keys) == 30, "structural cells are duplicated")
    agreement = sum(cell["larger_axis_agrees_across_metrics"] for cell in cells)
    return {
        "schema": "fishmip_structural_metric_robustness_v1",
        "status": "validated_structural_metric_sensitivity_not_probability_variance_or_scc",
        "source": {"path": source_path.as_posix(), "sha256": observed},
        "implementation": {"path": Path(__file__).as_posix(), "sha256": sha256(Path(__file__))},
        "cells": cells,
        "summary": {
            "cells": len(cells),
            "larger_axis_agrees_across_rms_and_mean_absolute": agreement,
            "larger_axis_changes_across_metrics": len(cells) - agreement,
            "rms_winner_counts": {axis: sum(cell["rms"]["larger_axis"] == axis for cell in cells) for axis in ("ecosystem_model", "climate_forcing", "tie")},
            "mean_absolute_winner_counts": {axis: sum(cell["mean_absolute"]["larger_axis"] == axis for cell in cells) for axis in ("ecosystem_model", "climate_forcing", "tie")},
        },
        "preferred_metric_selected": False,
        "probability_or_variance_decomposition": False,
        "forced_response_estimated": False,
        "country_or_eez_allocation_performed": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": "RMS-versus-mean-absolute ranking agreement is a descriptive robustness check on four model structures, not probability weighting, variance decomposition, causal response, allocation, welfare, damage, or SCC evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FishMIP structural metric agreement: {result['summary']['larger_axis_agrees_across_rms_and_mean_absolute']}/30")


if __name__ == "__main__":
    main()
