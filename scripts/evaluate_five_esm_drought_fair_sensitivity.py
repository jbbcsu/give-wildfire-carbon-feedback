#!/usr/bin/env python3
"""Map validated maize endpoint slopes onto matched GIVE/FAIR pulses."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "FIVE_ESM_DROUGHT_FAIR_SENSITIVITY_PROTOCOL_20260922.md"
CONFIG = ROOT / "config/give_fair_temperature_path_smoke_v1.toml"
FAIR_RECEIPT = ROOT / "data/provenance/give_fair_temperature_path_smoke_20260827.json"
SELECTED_YEARS = (2021, 2030, 2050, 2100, 2200, 2300)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-evidence", type=Path, required=True)
    parser.add_argument("--fair-paths", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence_path = args.endpoint_evidence if args.endpoint_evidence.is_absolute() else ROOT / args.endpoint_evidence
    fair_path = args.fair_paths if args.fair_paths.is_absolute() else ROOT / args.fair_paths
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh FAIR sensitivity output required")
    evidence = json.loads(evidence_path.read_text()); receipt = json.loads(FAIR_RECEIPT.read_text())
    require(receipt["result"] == "passed" and receipt["paths_sha256"] == digest(fair_path), "FAIR path validation differs")
    maize = [row for row in evidence["primary"] if row["crop"] == "mai"]
    require(len(maize) == 1 and maize[0]["combined_predictive_rule_passes"] is True, "validated primary maize endpoint required")
    primary = maize[0]
    slopes = [{"slope_id": "full", "slope_spei_per_k": primary["slope_spei_per_k"]}]
    for row in primary["whole_esm_holdouts"]:
        require(row["passes"] is True, "all maize whole-ESM folds must pass")
        slopes.append({"slope_id": f"leave_out_{row['held_out_esm']}",
                       "slope_spei_per_k": row["training_slope_spei_per_k"]})
    require(len(slopes) == 6 and len({row["slope_id"] for row in slopes}) == 6, "six named slope sensitivities required")

    frame = pd.read_csv(fair_path)
    require(len(frame) == 2204 and list(frame.columns) == ["year", "pulse_size_gtc", "baseline_temperature_c",
                                                            "pulse_temperature_c", "difference_k"], "FAIR schema differs")
    recomputed = frame.pulse_temperature_c - frame.baseline_temperature_c
    require(np.allclose(frame.difference_k, recomputed, rtol=0, atol=1e-15), "FAIR differences do not reconcile")
    frame = frame.assign(difference_k=recomputed)
    config = tomllib.loads(CONFIG.read_text()); pulse_year = int(config["pulse_year"])
    pulse_sizes = [float(value) for value in config["pulse_sizes_gtc"]]
    require(set(frame.pulse_size_gtc.astype(float)) == set(pulse_sizes), "FAIR pulse sizes differ")
    records = []
    for slope in slopes:
        for row in frame.itertuples(index=False):
            records.append({"slope_id": slope["slope_id"], "slope_spei_per_k": slope["slope_spei_per_k"],
                            "year": int(row.year), "pulse_size_gtc": float(row.pulse_size_gtc),
                            "temperature_difference_k": float(row.difference_k),
                            "conditional_spei_difference": slope["slope_spei_per_k"] * float(row.difference_k)})
    require(len(records) == 13224, "row-by-slope product differs")
    require(all(row["conditional_spei_difference"] == 0 for row in records if row["pulse_size_gtc"] == 0), "zero-pulse identity failed")
    require(all(row["conditional_spei_difference"] == 0 for row in records if row["year"] <= pulse_year), "pre-pulse identity failed")
    positive = sorted(value for value in pulse_sizes if value > 0)
    smallest, next_smallest = positive[0], positive[1]
    convergence = []
    for slope in slopes:
        values = {(row["year"], row["pulse_size_gtc"]): row["conditional_spei_difference"] for row in records if row["slope_id"] == slope["slope_id"]}
        differences = []; relative = []
        for year in range(int(config["model_start_year"]), int(config["model_end_year"]) + 1):
            left = values[(year, smallest)] / smallest; right = values[(year, next_smallest)] / next_smallest
            delta = abs(left-right); scale = max(abs(left), abs(right), 1e-15)
            require(delta <= 1e-12 + float(config["convergence_rtol"])*scale, "conditional SPEI pulse convergence failed")
            differences.append(delta); relative.append(delta/scale)
        convergence.append({"slope_id": slope["slope_id"], "smallest_pulse_gtc": smallest,
                            "next_smallest_pulse_gtc": next_smallest,
                            "maximum_absolute_normalized_disagreement_spei_per_gtc": max(differences),
                            "maximum_relative_normalized_disagreement": max(relative)})
    selected = [row for row in records if row["slope_id"] == "full" and row["year"] in SELECTED_YEARS and row["pulse_size_gtc"] > 0]
    maxima = []
    for slope in slopes:
        for pulse in sorted(pulse_sizes):
            subset = [abs(row["conditional_spei_difference"]) for row in records
                      if row["slope_id"] == slope["slope_id"] and row["pulse_size_gtc"] == pulse]
            maxima.append({"slope_id": slope["slope_id"], "pulse_size_gtc": pulse,
                           "maximum_absolute_conditional_spei_difference": max(subset)})
    full_normalized = max(abs(row["conditional_spei_difference"] / row["pulse_size_gtc"]) for row in records
                          if row["slope_id"] == "full" and row["pulse_size_gtc"] > 0)
    result = {"schema": "five_esm_drought_fair_conditional_sensitivity_v1",
              "status": "completed_conditional_fair_sensitivity_pending_independent_validation",
              "role": "linear_endpoint_sensitivity_not_validated_transient_response_yield_damage_or_scc",
              "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL)},
              "sources": {"endpoint_evidence_path": str(evidence_path.relative_to(ROOT)),
                          "endpoint_evidence_sha256": digest(evidence_path), "fair_paths_path": str(fair_path.relative_to(ROOT)),
                          "fair_paths_sha256": digest(fair_path), "fair_receipt_path": str(FAIR_RECEIPT.relative_to(ROOT)),
                          "fair_receipt_sha256": digest(FAIR_RECEIPT), "config_path": str(CONFIG.relative_to(ROOT)),
                          "config_sha256": digest(CONFIG)},
              "slopes": slopes, "records": records, "selected_full_slope_records": selected,
              "maximum_by_slope_and_pulse": maxima, "convergence": convergence,
              "full_slope_maximum_absolute_normalized_spei_per_gtc": full_normalized,
              "identities": {"zero_pulse": True, "pre_pulse_through_year": pulse_year,
                             "decreasing_pulse_convergence": True},
              "gates": {"numerical_fair_interface": False, "transient_climate_response": False,
                        "yield_response": False, "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); temporary.replace(output)
    print(json.dumps({"status": result["status"], "records": len(records), "slopes": len(slopes),
                      "full_slope_maximum_absolute_normalized_spei_per_gtc": full_normalized}))


if __name__ == "__main__":
    main()
