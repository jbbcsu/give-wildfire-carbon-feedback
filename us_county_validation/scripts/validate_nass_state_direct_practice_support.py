#!/usr/bin/env python3
"""Structural and arithmetic audit of the count-only NASS state support result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from audit_nass_state_direct_practice_support import (
    CROPS, PRACTICES, PROTOCOL, ROOT, TERMINAL_YEARS, YEARS, parameters, sha, summarize,
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
    if (result["status"] != "nass_state_direct_practice_count_support_audited_not_yield_response" or
            result["protocol_sha256"] != sha(PROTOCOL) or
            result["yield_values_downloaded"] is not False or
            result["response_estimated"] is not False or result["damage_or_scc_estimated"] is not False):
        raise ValueError("NASS state support result identity or boundary invalid")
    queries = result["queries"]
    checks = 0
    for row in queries:
        expected = parameters(row["crop"], row["practice"], int(row["year"]))
        if row["query_parameters_excluding_key"] != expected or "key" in row["query_parameters_excluding_key"]:
            raise ValueError("NASS state query parameters differ or expose key")
        checks += len(expected) + 1
    rebuilt = summarize(queries)
    if result["query_count"] != rebuilt["query_count"] or result["series"] != rebuilt["series"]:
        raise ValueError("NASS state support summary does not reconstruct")
    checks += 1 + 7 * len(rebuilt["series"])
    outcome = {
        "status": "nass_state_direct_practice_count_support_structurally_validated",
        "checks": checks,
        "source_sha256": sha(source),
        "protocol_sha256": sha(PROTOCOL),
        "validator_sha256": sha(Path(__file__)),
        "queries": len(queries),
        "terminal_years": [min(TERMINAL_YEARS), max(TERMINAL_YEARS)],
        "all_series_infeasible": all(row["state_panel_feasible"] is False for row in rebuilt["series"]),
        "yield_values_downloaded": False,
        "response_estimated": False,
        "damage_or_scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
