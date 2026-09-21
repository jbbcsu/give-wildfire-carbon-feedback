#!/usr/bin/env python3
"""Structural audit of Census practice-specific outcome support counts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_nass_census_direct_practice_outcome_support import (
    PROTOCOL, ROOT, parameters, sha, summarize,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    if (not source.is_file() or not source.is_relative_to(ROOT / "data/interim") or
            out.exists() or not out.is_relative_to(ROOT / "data/interim")):
        raise ValueError("valid ignored source and fresh ignored output required")
    result = json.loads(source.read_text())
    if (result["status"] != "nass_census_direct_practice_outcome_count_support_audited_not_yields" or
            result["protocol_sha256"] != sha(PROTOCOL) or result["values_downloaded"] is not False or
            result["yield_ratios_calculated"] is not False or result["response_estimated"] is not False or
            result["damage_or_scc_estimated"] is not False):
        raise ValueError("Census support result identity or claim boundary invalid")
    checks = 0
    for row in result["queries"]:
        expected = parameters(row["crop"], row["practice"], int(row["year"]), row["statistic"])
        if row["query_parameters_excluding_key"] != expected or "key" in row["query_parameters_excluding_key"]:
            raise ValueError("Census query differs or exposes key")
        checks += len(expected) + 1
    rebuilt = summarize(result["queries"])
    if any(result[field] != rebuilt[field] for field in ("query_count", "cells", "feasible_cells")):
        raise ValueError("Census support summary does not reconstruct")
    checks += 3 + 6 * len(rebuilt["cells"])
    outcome = {
        "status": "nass_census_direct_practice_outcome_count_support_structurally_validated",
        "checks": checks,
        "source_sha256": sha(source),
        "protocol_sha256": sha(PROTOCOL),
        "validator_sha256": sha(Path(__file__)),
        "queries": len(result["queries"]),
        "feasible_cells": rebuilt["feasible_cells"],
        "values_downloaded": False,
        "yield_ratios_calculated": False,
        "response_estimated": False,
        "damage_or_scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
