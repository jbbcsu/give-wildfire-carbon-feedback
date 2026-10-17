#!/usr/bin/env python3
"""Build a hash-bound, labor-only GIVE transfer artifact from reproduced runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def build_release(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    require(config["schema"] == "labor_fasttrack_release_contract/v1", "wrong contract schema")
    require(config["structural_weights"] == {"ISO": 0.5, "LANCET": 0.5}, "weights must be frozen at 0.5 each")
    rules = config["accounting_rules"]
    require(rules["labor_disposition"] == "candidate_addition", "labor must be an addition")
    require(rules["require_target_has_no_active_labor_sector"] is True, "overlap gate must remain closed")
    require(rules["allow_mean_addition_under_matched_scc_contract"] is True, "matched-contract mean transfer is required")
    require(rules["allow_cross_function_quantile_pooling"] is False, "quantile pooling must remain prohibited")
    require(rules["allow_cross_function_standard_error_pooling"] is False, "SE pooling must remain prohibited")
    require(rules["include_updated_agriculture"] is False, "fast-track release must be labor only")
    require(rules["include_source_total"] is False, "source total must not be transferred")

    receipts = {}
    for case, item in config["receipts"].items():
        path = root / item["path"]
        require(path.is_file(), f"missing {case} receipt")
        require(digest(path) == item["sha256"], f"{case} receipt hash mismatch")
        receipt = json.loads(path.read_text())
        require(receipt["schema"] == "labor_ag_sectoral_scc_stage_receipt/v1", f"wrong {case} receipt schema")
        require(receipt["labor_function"] == case, f"wrong {case} function label")
        require(receipt["draws"] == config["draws_per_structural_case"], f"wrong {case} draw count")
        for key in ("currency", "pulse_year", "discount_rate_label", "socioeconomics"):
            require(receipt[key] == config[key], f"{case} invariant differs: {key}")
        require(receipt["source_doi"] == config["source_archive_doi"], f"{case} source DOI differs")
        receipts[case] = receipt

    cases = {}
    for case in ("ISO", "LANCET"):
        summary = receipts[case]["summary"]["labor"]
        cases[case] = {
            "weight": config["structural_weights"][case],
            "expected_scc_2020usd_per_tco2": summary["expected_scc_2020usd_per_tco2"],
            "monte_carlo_se_of_mean": summary["se_expected_scc"],
            "q05_within_case": summary["q05"],
            "median_within_case": summary["median"],
            "q95_within_case": summary["q95"],
        }
    central = sum(row["weight"] * row["expected_scc_2020usd_per_tco2"] for row in cases.values())
    case_means = [row["expected_scc_2020usd_per_tco2"] for row in cases.values()]
    return {
        "schema": "labor_fasttrack_release/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "labor_partial_scc_ready_for_matched-contract_mean transfer",
        "sector": "heat-related labor productivity",
        "estimate": {
            "central_equal_weight_mean_2020usd_per_tco2": central,
            "structural_case_mean_range_2020usd_per_tco2": [min(case_means), max(case_means)],
            "cases": cases,
            "pooled_quantiles": None,
            "pooled_standard_error": None,
        },
        "integration": {
            "operation": "add labor partial SCC mean to a target GIVE expected SCC only when pulse year, discounting, currency, and RFF-SP setup match",
            "precondition": "target model has no active labor-productivity damage sector",
            "forbidden": [
                "adding the source total SCC",
                "adding the source updated-agriculture result as part of this labor release",
                "averaging ISO and Lancet quantiles or standard errors",
                "claiming a joint combined uncertainty distribution from summary statistics",
            ],
        },
        "provenance": {
            "article_doi": config["article_doi"],
            "source_archive_doi": config["source_archive_doi"],
            "draws_per_case": config["draws_per_structural_case"],
            "config_path": str(config_path.relative_to(root)),
            "config_sha256": digest(config_path),
            "receipt_sha256": {case: config["receipts"][case]["sha256"] for case in cases},
        },
        "claim_boundary": "Published-function replication and matched-contract partial-SCC transfer; not a new causal estimate and not a pooled uncertainty distribution.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/labor_fasttrack_release_v1.json")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_json.exists(), "fresh JSON output required")
    require(not args.output_csv.exists(), "fresh CSV output required")
    result = build_release(ROOT, args.config.resolve())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with args.output_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case", "weight", "expected_scc_2020usd_per_tco2", "mc_se", "q05", "median", "q95"])
        for case, row in result["estimate"]["cases"].items():
            writer.writerow([case, row["weight"], row["expected_scc_2020usd_per_tco2"], row["monte_carlo_se_of_mean"], row["q05_within_case"], row["median_within_case"], row["q95_within_case"]])
        writer.writerow(["equal_weight_mean", 1.0, result["estimate"]["central_equal_weight_mean_2020usd_per_tco2"], "", "", "", ""])
    print(json.dumps(result["estimate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
