#!/usr/bin/env python3
"""Validate the paired GIVE global-maize drought structural sensitivity."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


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
    parser.add_argument("--paths-receipt", type=Path, required=True)
    parser.add_argument("--paired-output", type=Path, required=True)
    parser.add_argument("--resource-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")

    source = json.loads(args.paths_receipt.read_text())
    resource = json.loads(args.resource_receipt.read_text())
    frame = pd.read_csv(args.paired_output)
    require(source["schema"] == "drought_gmst_fund_paths_v1", "path source schema differs")
    require(source["gates"]["structural_sensitivity"] is True, "structural gate absent")
    require(source["gates"]["causal_drought_attribution"] is False, "causal gate changed")
    require(resource["status"] == "completed" and resource["returncode"] == 0, "paired job did not complete")
    require(len(frame) == 36, "paired output row count differs")
    require(not frame.duplicated(["response_case", "adaptation", "discount_rate_label"]).any(),
            "duplicate paired result")
    require(set(frame.response_case) == {"lower_95", "central", "upper_95"}, "response cases differ")
    require(set(frame.adaptation) == {"fixed", "trend", "upper"}, "adaptation cases differ")
    require(set(frame.discount_rate_label) == {"1.5%", "2.0%", "2.5%", "3.0%"}, "discount cases differ")
    require((frame.baseline_agriculture_error_usd == 0).all(), "baseline agriculture changed")
    require((frame.baseline_cpc_error == 0).all(), "baseline CPC changed")
    require((frame.regional_increment_error_billion_usd2005 <= 1e-12).all(), "regional increment differs")
    require((frame.aggregated_increment_error_usd <= 0.01).all(), "agriculture aggregation differs")
    require((frame.paired_replacement_usd2005_per_tco2 > 0).all(), "unexpected nonpositive drought SCC sensitivity")
    conversion_error = (frame.paired_replacement_usd2020_per_tco2 -
                        frame.paired_replacement_usd2005_per_tco2 * 1.2987749131468274).abs().max()
    require(conversion_error <= 1e-12, "currency conversion differs")

    ordered_response = {"lower_95": 0, "central": 1, "upper_95": 2}
    ordered_adaptation = {"upper": 0, "trend": 1, "fixed": 2}
    checks = 0
    for (_, adaptation, rate), group in frame.groupby([lambda _: True, "adaptation", "discount_rate_label"]):
        values = group.sort_values("response_case", key=lambda s: s.map(ordered_response)).paired_replacement_usd2020_per_tco2
        require(values.is_monotonic_increasing and values.is_unique, f"response ordering differs for {adaptation}/{rate}")
        checks += 1
    for (_, response, rate), group in frame.groupby([lambda _: True, "response_case", "discount_rate_label"]):
        values = group.sort_values("adaptation", key=lambda s: s.map(ordered_adaptation)).paired_replacement_usd2020_per_tco2
        require(values.is_monotonic_increasing and values.is_unique, f"adaptation ordering differs for {response}/{rate}")
        checks += 1
    for (_, response, adaptation), group in frame.groupby([lambda _: True, "response_case", "adaptation"]):
        values = group.sort_values("prtp").paired_replacement_usd2020_per_tco2
        require(values.is_monotonic_decreasing and values.is_unique, f"discount ordering differs for {response}/{adaptation}")
        checks += 1

    central = frame[(frame.response_case == "central") & (frame.discount_rate_label == "2.0%")]
    central_values = {row.adaptation: float(row.paired_replacement_usd2020_per_tco2)
                      for row in central.itertuples()}
    result = {
        "schema": "drought_gmst_replacement_sensitivity_validation_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_structural_sensitivity_not_causal_or_central_precipitation_scc",
        "checks": {"rows": 36, "ordering_groups": checks, "maximum_currency_conversion_error": conversion_error,
                   "baseline_agriculture_exact": True, "baseline_cpc_exact": True},
        "central_response_2pct_usd2020_per_tco2": central_values,
        "sources": {"paths_receipt": {"path": str(args.paths_receipt), "sha256": digest(args.paths_receipt)},
                    "paired_output": {"path": str(args.paired_output), "sha256": digest(args.paired_output)},
                    "resource_receipt": {"path": str(args.resource_receipt), "sha256": digest(args.resource_receipt)}},
        "gates": {"paired_give_engineering": True, "structural_sensitivity": True,
                  "causal_drought_attribution": False, "central_precipitation_scc": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "central": central_values}, indent=2))


if __name__ == "__main__":
    main()
