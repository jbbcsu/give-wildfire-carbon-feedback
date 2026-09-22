#!/usr/bin/env python3
"""Export validated aggregate evidence for the conditional FAIR sensitivity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
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
    result_path = args.result if args.result.is_absolute() else ROOT/args.result
    validation_path = args.validation if args.validation.is_absolute() else ROOT/args.validation
    output = args.output if args.output.is_absolute() else ROOT/args.output
    require(not output.exists(), "fresh public output required")
    result = json.loads(result_path.read_text()); validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed" and validation["result_sha256"] == digest(result_path),
            "independent validation binding differs")
    require(validation["row_slope_records"] == 13224 and validation["numeric_checks"] == 52933,
            "validation coverage differs")
    public = {"schema": "five_esm_drought_fair_conditional_public_evidence_v1", "status": "validated_numerical_sensitivity",
              "role": "linear_endpoint_fair_sensitivity_not_transient_response_yield_damage_or_scc",
              "sources": {"result_path": str(result_path.relative_to(ROOT)), "result_sha256": digest(result_path),
                          "validation_path": str(validation_path.relative_to(ROOT)), "validation_sha256": digest(validation_path),
                          "numeric_checks": validation["numeric_checks"],
                          "maximum_numeric_absolute_difference": validation["maximum_numeric_absolute_difference"]},
              "slopes": result["slopes"], "selected_full_slope_records": result["selected_full_slope_records"],
              "maximum_by_slope_and_pulse": result["maximum_by_slope_and_pulse"],
              "convergence": result["convergence"],
              "full_slope_maximum_absolute_normalized_spei_per_gtc": result["full_slope_maximum_absolute_normalized_spei_per_gtc"],
              "identities": result["identities"],
              "interpretation": ["This is a deterministic linear sensitivity using a multi-forcing endpoint slope.",
                                 "It is not a validated transient, CO2-only, or marginal climate-feature response.",
                                 "No crop-yield response, economic damage, or SCC is estimated."],
              "gates": {"numerical_fair_interface": True, "transient_climate_response": False,
                        "yield_response": False, "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(public, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps({"status": public["status"], "selected_records": len(public["selected_full_slope_records"]),
                      "slopes": len(public["slopes"])}))


if __name__ == "__main__":
    main()
