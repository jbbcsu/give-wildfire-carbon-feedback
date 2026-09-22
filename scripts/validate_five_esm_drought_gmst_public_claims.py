#!/usr/bin/env python3
"""Validate public drought--GMST endpoint claims against checked evidence."""
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


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("result", "validation", "evidence", "report", "manuscript", "methods", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: resolve(getattr(args, name)) for name in
             ("result", "validation", "evidence", "report", "manuscript", "methods")}
    output = resolve(args.output); require(not output.exists(), "fresh claims output required")
    result = json.loads(paths["result"].read_text()); validation = json.loads(paths["validation"].read_text())
    evidence = json.loads(paths["evidence"].read_text())
    require(validation["status"] == "passed" and validation["result_sha256"] == digest(paths["result"]),
            "result validation binding differs")
    require(evidence["sources"]["result_sha256"] == digest(paths["result"]) and
            evidence["sources"]["validation_sha256"] == digest(paths["validation"]), "evidence binding differs")
    expected = {row["crop"]: row for row in result["primary_records"]}
    public = {row["crop"]: row for row in evidence["primary"]}
    require(set(expected) == set(public) == {"mai", "soy"}, "primary crop set differs")
    numeric_checks = 0; maximum = 0.0
    for crop in ("mai", "soy"):
        source = expected[crop]; exported = public[crop]
        for field, value in (("slope_spei_per_k", source["full_fit"]["slope_spei_per_k"]),
                             ("rmse", source["full_fit"]["rmse"]),
                             ("zero_change_rmse", source["full_fit"]["zero_change_rmse"])):
            difference = abs(exported[field] - value)
            require(math.isclose(exported[field], value, rel_tol=0, abs_tol=0), f"public {crop} {field} differs")
            maximum = max(maximum, difference); numeric_checks += 1
        require(exported["whole_esm_rule_passes"] is source["whole_esm_rule_passes"] and
                exported["whole_scenario_rule_passes"] is source["whole_scenario_rule_passes"] and
                exported["combined_predictive_rule_passes"] is source["combined_predictive_rule_passes"],
                "public pass flags differ")
    require(evidence["summary_by_crop"] == result["summary_by_crop"], "public summary differs")
    claims = {"report": ("-0.1876 SPEI K-1", "-0.1469", "fails the whole-ESM rule", "not an"),
              "manuscript": ("-0.1876 SPEI K-1", "-0.1469 SPEI K-1", "37/45 maize", "13/45 soybean"),
              "methods": ("-0.187585 SPEI K-1", "-0.146942 SPEI K-1", "6,893 numeric checks")}
    text_checks = 0
    for name, needles in claims.items():
        text = paths[name].read_text()
        for needle in needles:
            require(needle in text, f"claim missing from {name}: {needle}"); text_checks += 1
    checked = {"schema": "five_esm_drought_gmst_public_claims_validation_v1", "status": "passed",
               "role": "claim_binding_validation_not_attribution_yield_damage_or_scc",
               "result_sha256": digest(paths["result"]), "validation_sha256": digest(paths["validation"]),
               "evidence_sha256": digest(paths["evidence"]), "numeric_checks": numeric_checks,
               "text_checks": text_checks, "maximum_numeric_absolute_difference": maximum,
               "documents": {name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
                             for name, path in paths.items() if name in ("report", "manuscript", "methods")},
               "gates": {"claims_transcription": True, "transient_climate_response": False,
                         "yield_response": False, "damage": False, "scc": False},
               "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                  "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(checked, indent=2, sort_keys=True) + "\n"); temporary.replace(output)
    print(json.dumps(checked))


if __name__ == "__main__":
    main()
