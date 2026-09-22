#!/usr/bin/env python3
"""Independently validate conditional drought signals on GIVE/FAIR paths."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SELECTED_YEARS = {2021, 2030, 2050, 2100, 2200, 2300}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(actual: float, expected: float, label: str) -> float:
    difference = abs(float(actual)-float(expected))
    require(math.isclose(float(actual), float(expected), rel_tol=2e-14, abs_tol=2e-14), f"numeric disagreement: {label}")
    return difference


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result if args.result.is_absolute() else ROOT / args.result
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh validation output required")
    observed = json.loads(result_path.read_text())
    require(digest(ROOT/observed["protocol"]["path"]) == observed["protocol"]["sha256"], "protocol hash differs")
    for name in ("endpoint_evidence", "fair_paths", "fair_receipt", "config"):
        require(digest(ROOT/observed["sources"][f"{name}_path"]) == observed["sources"][f"{name}_sha256"], f"{name} hash differs")
    evidence = json.loads((ROOT/observed["sources"]["endpoint_evidence_path"]).read_text())
    maize = [row for row in evidence["primary"] if row["crop"] == "mai"]
    require(len(maize) == 1 and maize[0]["combined_predictive_rule_passes"] is True, "validated maize record differs")
    expected_slopes = {"full": maize[0]["slope_spei_per_k"]}
    expected_slopes.update({f"leave_out_{row['held_out_esm']}": row["training_slope_spei_per_k"]
                            for row in maize[0]["whole_esm_holdouts"]})
    require({row["slope_id"]: row["slope_spei_per_k"] for row in observed["slopes"]} == expected_slopes,
            "slope registry differs")
    fair = pd.read_csv(ROOT/observed["sources"]["fair_paths_path"])
    config = tomllib.loads((ROOT/observed["sources"]["config_path"]).read_text())
    expected = {}; checks = 0; maximum = 0.0
    for slope_id, slope in expected_slopes.items():
        for row in fair.itertuples(index=False):
            delta = float(row.pulse_temperature_c)-float(row.baseline_temperature_c)
            maximum = max(maximum, close(row.difference_k, delta, "temperature difference")); checks += 1
            expected[(slope_id, int(row.year), float(row.pulse_size_gtc))] = (slope, delta, slope*delta)
    actual = {(row["slope_id"], row["year"], row["pulse_size_gtc"]): row for row in observed["records"]}
    require(len(expected) == len(actual) == 13224 and set(expected) == set(actual), "row-slope product differs")
    for key, (slope, delta, spei) in expected.items():
        row = actual[key]
        for value, target, label in ((row["slope_spei_per_k"], slope, "slope"),
                                     (row["temperature_difference_k"], delta, "temperature"),
                                     (row["conditional_spei_difference"], spei, "conditional SPEI")):
            maximum = max(maximum, close(value, target, label)); checks += 1
    pulse_year = int(config["pulse_year"])
    require(all(value[2] == 0 for key, value in expected.items() if key[2] == 0), "zero pulse differs")
    require(all(value[2] == 0 for key, value in expected.items() if key[1] <= pulse_year), "pre-pulse differs")
    selected = [row for row in observed["records"] if row["slope_id"] == "full" and row["year"] in SELECTED_YEARS and row["pulse_size_gtc"] > 0]
    require(observed["selected_full_slope_records"] == selected and len(selected) == 18, "selected-year records differ")
    observed_maxima = {(row["slope_id"], row["pulse_size_gtc"]): row["maximum_absolute_conditional_spei_difference"]
                       for row in observed["maximum_by_slope_and_pulse"]}
    for slope_id in expected_slopes:
        for pulse in sorted(set(fair.pulse_size_gtc.astype(float))):
            value = max(abs(spei) for (sid, _, p), (_, _, spei) in expected.items() if sid == slope_id and p == pulse)
            maximum = max(maximum, close(observed_maxima[(slope_id, pulse)], value, "maximum")); checks += 1
    positives = sorted(value for value in set(fair.pulse_size_gtc.astype(float)) if value > 0)
    smallest, next_smallest = positives[0], positives[1]
    observed_convergence = {row["slope_id"]: row for row in observed["convergence"]}
    for slope_id in expected_slopes:
        absolute = []; relative = []
        for year in sorted(set(fair.year.astype(int))):
            left = expected[(slope_id, year, smallest)][2]/smallest
            right = expected[(slope_id, year, next_smallest)][2]/next_smallest
            difference = abs(left-right); scale = max(abs(left), abs(right), 1e-15)
            require(difference <= 1e-12+float(config["convergence_rtol"])*scale, "convergence differs")
            absolute.append(difference); relative.append(difference/scale)
        row = observed_convergence[slope_id]
        maximum = max(maximum, close(row["maximum_absolute_normalized_disagreement_spei_per_gtc"], max(absolute), "convergence absolute"))
        maximum = max(maximum, close(row["maximum_relative_normalized_disagreement"], max(relative), "convergence relative")); checks += 2
    normalized = max(abs(spei/pulse) for (slope_id, _, pulse), (_, _, spei) in expected.items()
                     if slope_id == "full" and pulse > 0)
    maximum = max(maximum, close(observed["full_slope_maximum_absolute_normalized_spei_per_gtc"], normalized, "normalized maximum")); checks += 1
    require(observed["identities"] == {"zero_pulse": True, "pre_pulse_through_year": pulse_year,
                                        "decreasing_pulse_convergence": True}, "identity flags differ")
    result = {"schema": "five_esm_drought_fair_conditional_sensitivity_validation_v1", "status": "passed",
              "role": "independent_numerical_validation_not_transient_response_yield_damage_or_scc",
              "result_sha256": digest(result_path), "row_slope_records": 13224, "slopes": 6,
              "numeric_checks": checks, "maximum_numeric_absolute_difference": maximum,
              "gates": {"numerical_fair_interface": True, "transient_climate_response": False,
                        "yield_response": False, "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
