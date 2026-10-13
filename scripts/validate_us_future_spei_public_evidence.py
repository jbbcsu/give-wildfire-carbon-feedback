#!/usr/bin/env python3
"""Validate the public U.S. future-SPEI evidence against ignored run artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    parser.add_argument("--evidence", type=Path, default=ROOT / "data/provenance/us_future_spei_exposure_20261013.json")
    args = parser.parse_args()
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    evidence = json.loads(evidence_path.read_text())
    checks = 0
    for name, record in evidence["artifacts"].items():
        path = ROOT / record["path"]
        require(path.is_file() and digest(path) == record["sha256"], f"artifact changed: {name}")
        checks += 2
        if "bytes" in record:
            require(path.stat().st_size == record["bytes"], f"artifact size changed: {name}")
            checks += 1
    result = json.loads((ROOT / evidence["artifacts"]["result"]["path"]).read_text())
    validation = json.loads((ROOT / evidence["artifacts"]["independent_validation"]["path"]).read_text())
    require(validation["status"] == "passed" and validation["result_sha256"] == evidence["artifacts"]["result"]["sha256"], "validation chain failed")
    checks += 2
    # Compare the shared support fields explicitly; the evidence also records the country rule.
    for name in ("positive_rainfed_cells", "rainfed_area_ha", "latitude_range", "longitude_360_range"):
        require(result["support"][name] == evidence["support"][name], f"support differs: {name}")
        checks += 1
    require(len(result["upstream"]) == 15 and len(result["annual_records"]) == 1800 and len(result["named_model_contrasts"]) == 150 and len(result["ensemble_summaries"]) == 30, "result factorial differs")
    checks += 4
    for label in ("ssp370_minus_ssp126", "ssp585_minus_ssp126"):
        observed = next(r for r in result["ensemble_summaries"] if r["contrast"] == label and r["window"] == "season" and r["scale_months"] == 3)
        expected = evidence["primary"][label]
        for model, value in observed["named_model_spei_differences"].items():
            require(math.isclose(value, expected[model], rel_tol=0, abs_tol=1e-15), f"named-model value differs: {label}/{model}")
            checks += 1
        for output_name, evidence_name in (("equal_model_mean", "equal_model_mean"), ("median", "median"),
                                           ("minimum", "minimum"), ("maximum", "maximum"), ("population_sd", "population_sd")):
            require(math.isclose(observed[output_name], expected[evidence_name], rel_tol=0, abs_tol=1e-15), f"summary differs: {label}/{output_name}")
            checks += 1
        require(observed["negative_models"] == expected["negative_models"] == 5, "model sign count differs")
        checks += 1
    require(validation["checks"] == evidence["validation"]["checks"] and validation["maximum_numeric_absolute_difference"] == evidence["validation"]["maximum_numeric_absolute_difference"], "validation statistics differ")
    checks += 2
    require(evidence["gates"] == validation["gates"] and not evidence["gates"]["bridge_to_nass_response"], "claim gates differ or bridge opened")
    checks += 2
    print(json.dumps({"status": "passed", "checks": checks, "evidence_sha256": digest(evidence_path)}))


if __name__ == "__main__":
    main()
