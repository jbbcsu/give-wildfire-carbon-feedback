#!/usr/bin/env python3
"""Combine ISO and Lancet replication means without inventing a distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--lancet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    receipts = [json.loads(args.iso.read_text()), json.loads(args.lancet.read_text())]
    require({item["labor_function"] for item in receipts} == {"ISO", "LANCET"}, "expected ISO and LANCET receipts")
    for item in receipts:
        require(item["schema"] == "labor_ag_sectoral_scc_stage_receipt/v1", "receipt schema differs")
        require(item["draws"] == 10_000, "full 10,000-draw receipts required")
    invariants = ["currency", "discount_rate_label", "draws", "julia_threads", "julia_version", "pulse_year", "seed", "socioeconomics", "source_doi"]
    for name in invariants:
        require(receipts[0][name] == receipts[1][name], f"receipt invariant differs: {name}")
    require(set(receipts[0]["summary"]) == set(receipts[1]["summary"]), "sector support differs")

    iso = next(item for item in receipts if item["labor_function"] == "ISO")
    lancet = next(item for item in receipts if item["labor_function"] == "LANCET")
    sectors = {}
    for sector in sorted(iso["summary"]):
        values = {
            "ISO": float(iso["summary"][sector]["expected_scc_2020usd_per_tco2"]),
            "LANCET": float(lancet["summary"][sector]["expected_scc_2020usd_per_tco2"]),
        }
        sectors[sector] = {
            "equal_weight_structural_mean_2020usd_per_tco2": sum(values.values()) / 2.0,
            "structural_range_2020usd_per_tco2": [min(values.values()), max(values.values())],
            "single_function_means_2020usd_per_tco2": values,
        }

    published_rounded = {"agriculture": 29.0, "labor": 41.0, "total": 179.0}
    consistency = {}
    for sector, headline in published_rounded.items():
        midpoint = sectors[sector]["equal_weight_structural_mean_2020usd_per_tco2"]
        consistency[sector] = {
            "published_rounded_2020usd_per_tco2": headline,
            "replicated_structural_midpoint_2020usd_per_tco2": midpoint,
            "difference_from_published_rounded": midpoint - headline,
            "consistent_with_nearest_dollar_rounding": round(midpoint) == int(headline),
        }
        require(consistency[sector]["consistent_with_nearest_dollar_rounding"], f"{sector} midpoint misses rounded headline")

    result = {
        "schema": "labor_ag_equal_weight_structural_means/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_structural_mean_reconciliation_not_cross_function_uncertainty_distribution",
        "method": "arithmetic mean of independently replicated ISO and Lancet 10,000-draw expected SCCs, with equal 0.5 structural weights",
        "sources": {
            "ISO": {"path": str(args.iso), "sha256": digest(args.iso)},
            "LANCET": {"path": str(args.lancet), "sha256": digest(args.lancet)},
        },
        "invariants": {name: iso[name] for name in invariants},
        "sectors": sectors,
        "published_headline_consistency": consistency,
        "published_article": {
            "doi": "10.1038/s41558-026-02749-z",
            "claim": "article abstract reports labor 41, agriculture 29, and total 179 in 2020 USD/tCO2 for 2025 and states that two labor response functions are used",
        },
        "limitations": [
            "The equal structural weights are a transparent reconciliation that reproduces the rounded published means; the archived analysis code runs the two functions separately and does not itself document a cross-function pooling operator.",
            "Trial-level outputs were not retained by the local summary wrapper, so cross-function standard errors, quantiles, and confidence intervals are not reconstructed.",
            "Averages of the two reported quantiles or standard errors would not be valid and are intentionally omitted.",
            "Agriculture is a replacement candidate for GIVE agriculture, not an additive precipitation damage term.",
        ],
        "claim_gates": {"single_function_replications": True, "equal_weight_mean_reconciliation": True, "cross_function_uncertainty_distribution": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "headline_consistency": consistency}, indent=2))


if __name__ == "__main__":
    main()
