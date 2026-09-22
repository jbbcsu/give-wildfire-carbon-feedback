#!/usr/bin/env python3
"""Export the independently validated drought--GMST endpoint evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result if args.result.is_absolute() else ROOT / args.result
    validation_path = args.validation if args.validation.is_absolute() else ROOT / args.validation
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh public output required")
    result = json.loads(result_path.read_text()); validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed" and validation["result_sha256"] == digest(result_path),
            "independent validation binding differs")
    require(validation["numeric_checks"] == 6893 and validation["feature_records"] == 90,
            "independent validation coverage differs")
    require(result["summary_by_crop"] == validation["summary_by_crop"], "validated summary differs")
    primary = []
    for row in result["primary_records"]:
        primary.append({"crop": row["crop"], "window": row["window"], "scale_months": row["scale_months"],
                        "irrigation": row["irrigation"], "slope_spei_per_k": row["full_fit"]["slope_spei_per_k"],
                        "rmse": row["full_fit"]["rmse"], "zero_change_rmse": row["full_fit"]["zero_change_rmse"],
                        "whole_esm_rule_passes": row["whole_esm_rule_passes"],
                        "whole_scenario_rule_passes": row["whole_scenario_rule_passes"],
                        "combined_predictive_rule_passes": row["combined_predictive_rule_passes"],
                        "whole_esm_holdouts": row["whole_esm_holdouts"],
                        "whole_scenario_holdouts": row["whole_scenario_holdouts"],
                        "named_endpoint_points": row["full_fit"]["points"]})
    public = {"schema": "five_esm_drought_gmst_endpoint_public_evidence_v1", "status": "validated_endpoint_diagnostic",
              "role": "multi_forcing_endpoint_slope_not_attribution_transient_emulator_yield_damage_or_scc",
              "sources": {"result_path": str(result_path.relative_to(ROOT)), "result_sha256": digest(result_path),
                          "validation_path": str(validation_path.relative_to(ROOT)), "validation_sha256": digest(validation_path),
                          "numeric_checks": validation["numeric_checks"],
                          "maximum_numeric_absolute_difference": validation["maximum_numeric_absolute_difference"]},
              "primary": primary, "summary_by_crop": result["summary_by_crop"],
              "interpretation": ["The slope is an origin-constrained endpoint scenario diagnostic in SPEI units per kelvin.",
                                 "Whole-ESM and whole-scenario holdouts reuse the same five-model climate ensemble.",
                                 "SSP contrasts contain multiple forcings and internal variability.",
                                 "The result is not anthropogenic attribution, a transient or marginal-pulse response, a yield effect, damage, or SCC."],
              "gates": {"endpoint_diagnostic": True, "transient_climate_response": False,
                        "yield_response": False, "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n"); temporary.replace(output)
    print(json.dumps({"status": public["status"], "primary_records": len(primary),
                      "summary_by_crop": public["summary_by_crop"]}))


if __name__ == "__main__":
    main()
