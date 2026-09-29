#!/usr/bin/env python3
"""Independent schema and identity validator for the synthetic corn executor."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CANDIDATE = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_synthetic_executor_20260929.json"
TESTS = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_synthetic_executor_tests_20260929.json"
OUTPUT = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_synthetic_executor_validation_20260929.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    parser.add_argument("--tests", type=Path, default=TESTS)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    if candidate.get("status") != "completed_synthetic_only_post_authorization_plumbing":
        raise AssertionError("candidate status changed")
    if candidate.get("source_role") != "synthetic_fixture_only" or candidate.get("real_outcome_rows_read") != 0 or candidate.get("real_response_fits") != 0:
        raise AssertionError("candidate is not synthetic-only")
    if candidate.get("practices_pooled") is not False or candidate.get("families_stacked") is not False:
        raise AssertionError("candidate pools practices or stacks families")
    implementation = PROJECT / candidate["implementation"]["path"]
    protocol = PROJECT / candidate["protocol"]["path"]
    if digest(implementation) != candidate["implementation"]["sha256"] or digest(protocol) != candidate["protocol"]["sha256"]:
        raise AssertionError("candidate code/protocol identity changed")
    if tests.get("status") != "passed" or tests.get("tests_run") != 7 or tests.get("failures") != 0 or tests.get("errors") != 0:
        raise AssertionError("focused tests are incomplete")
    if tests.get("executor", {}).get("sha256") != digest(implementation):
        raise AssertionError("focused tests do not bind candidate executor")
    expected = {(practice, family) for practice in ("non_irrigated", "irrigated") for family in ("quantity", "pdsi")}
    observed = {(cell["practice"], cell["family"]) for cell in candidate["full_sample"]}
    if observed != expected or len(candidate["full_sample"]) != 4:
        raise AssertionError("full cells changed")
    checks = 8
    for cell in candidate["full_sample"]:
        terms = cell["design_terms"]
        if cell["family"] == "quantity" and (not any("precipitation" in x for x in terms) or any("pdsi" in x for x in terms)):
            raise AssertionError("quantity family is not exclusive")
        if cell["family"] == "pdsi" and (not any("pdsi" in x for x in terms) or any("precipitation" in x for x in terms)):
            raise AssertionError("PDSI family is not exclusive")
        if cell["design_rank"] != len(terms) or len(cell["contrasts"]) != 3:
            raise AssertionError("full synthetic design rank/schema changed")
        for contrast in cell["contrasts"]:
            if set(contrast["standard_errors"]) != {"county_cr1", "spatial_250km", "spatial_500km"}:
                raise AssertionError("covariance outputs changed")
            if not all(math.isfinite(value) and value > 0 for value in contrast["standard_errors"].values()):
                raise AssertionError("covariance output is nonpositive/nonfinite")
        checks += 5
    if len(candidate["leave_one_state"]) != 4 or any(len(block["omissions"]) != 5 for block in candidate["leave_one_state"]):
        raise AssertionError("leave-state schema changed")
    if len(candidate["terminal_validation"]) != 4:
        raise AssertionError("terminal schema changed")
    for block in candidate["terminal_validation"]:
        if (block["development"]["year_min"], block["development"]["year_max"]) != (1981, 2011):
            raise AssertionError("development years changed")
        if (block["terminal"]["year_min"], block["terminal"]["year_max"]) != (2012, 2018):
            raise AssertionError("terminal years changed")
        checks += 2
    result = {
        "schema": "us_corn_quantity_pdsi_spatial_synthetic_executor_validation_v1",
        "status": "validated_synthetic_executor_schema_and_identities",
        "candidate": {"path": str(args.candidate.resolve().relative_to(PROJECT)), "sha256": digest(args.candidate)},
        "tests": {"path": str(args.tests.resolve().relative_to(PROJECT)), "sha256": digest(args.tests)},
        "validator": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "checks": checks, "real_outcome_rows_read": 0, "real_response_fits": 0,
        "national_claim_authorized": False, "causal_claim_authorized": False,
        "damage_claim_authorized": False, "scc_claim_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
