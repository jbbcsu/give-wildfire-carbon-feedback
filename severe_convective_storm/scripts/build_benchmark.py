#!/usr/bin/env python3
"""Build a bounded published hail-damage benchmark; never manufacture an SCC."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate(source, contract):
    assert source["scc_ready"] is False
    assert source["additive_to_give"] is False
    assert contract["scc_ready"] is False
    assert contract["additive_to_give"] is False
    assert source["currency"] == "CHF"
    assert source["currency_price_year"] is None
    assert source["geography"] == "Swiss calibration region"
    assert source["present_annual_average_loss_chf"] > 0
    assert source["pgw_3c_annual_average_loss_chf"] > source["present_annual_average_loss_chf"]
    exact = source["pgw_3c_annual_average_loss_chf"] / source["present_annual_average_loss_chf"] - 1
    assert round(exact, 2) == source["published_rounded_relative_change"]
    return exact


def build():
    source = load_json(ROOT / "config" / "published_benchmark.json")
    contract = load_json(ROOT / "contracts" / "hail_property_contract.json")
    exact = validate(source, contract)
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    row = {
        "benchmark_id": source["benchmark_id"],
        "geography": source["geography"],
        "endpoint": source["endpoint"],
        "present_aal_chf": source["present_annual_average_loss_chf"],
        "pgw_3c_aal_chf": source["pgw_3c_annual_average_loss_chf"],
        "difference_chf_per_year": source["pgw_3c_annual_average_loss_chf"] - source["present_annual_average_loss_chf"],
        "exact_relative_change": f"{exact:.12f}",
        "published_rounded_relative_change": source["published_rounded_relative_change"],
        "scc_ready": "false",
        "additive_to_give": "false"
    }
    with (results / "swiss_hail_benchmark.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=row.keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    readiness = {
        "status": "BLOCKED_FROM_SCC_BY_DESIGN",
        "passed": ["separable building-hail endpoint", "matched climate and damage experiment", "published regional monetary benchmark"],
        "missing": contract["required_scc_gates"],
        "prohibited_outputs": ["global damages", "USD damages", "dollars_per_tCO2"]
    }
    with (results / "readiness.json").open("w", encoding="utf-8") as stream:
        json.dump(readiness, stream, indent=2)
        stream.write("\n")
    return row, readiness


if __name__ == "__main__":
    row, readiness = build()
    print(json.dumps({"benchmark": row, "readiness": readiness["status"]}, indent=2))
