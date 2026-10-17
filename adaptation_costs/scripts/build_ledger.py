#!/usr/bin/env python3
"""Validate the adaptation ledger and emit fail-closed readiness outputs."""

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_ledger():
    with (ROOT / "ledger" / "adaptation_ledger.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate(rows, contract):
    allowed = set(contract["cost_treatments"])
    assert rows
    assert len({(r["model"], r["scenario"]) for r in rows}) == len(rows)
    for row in rows:
        assert row["cost_treatment"] in allowed
        assert row["net_damage_ready"] in {"true", "false"}
        assert row["net_scc_ready"] in {"true", "false"}
        if row["cost_treatment"] in {"explicitly_zero_unpriced", "unresolved"}:
            assert row["net_damage_ready"] == "false"
            assert row["net_scc_ready"] == "false"
        if row["cost_treatment"] in {"embedded_in_total", "explicit_modeled"}:
            assert "add" in row["double_count_rule"].lower() or "once" in row["double_count_rule"].lower()
    return Counter(r["cost_treatment"] for r in rows)


def build():
    contract = read_json(ROOT / "contracts" / "accounting_contract.json")
    rows = read_ledger()
    counts = validate(rows, contract)
    benchmark = read_json(ROOT / "config" / "bounded_agriculture_cost_benchmark.json")
    assert benchmark["give_mapping_available"] is False
    assert benchmark["scc_ready"] is False
    assert benchmark["low_billion_usd_per_year"] < benchmark["high_billion_usd_per_year"]
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    readiness = {
        "schema": "give_adaptation_cost_readiness/v1",
        "ledger_rows": len(rows),
        "cost_treatment_counts": dict(sorted(counts.items())),
        "free_adaptation_rows": [
            {"sector": r["sector"], "model": r["model"], "scenario": r["scenario"]}
            for r in rows if r["cost_treatment"] == "explicitly_zero_unpriced"
        ],
        "cost_inclusive_rows": [
            {"sector": r["sector"], "model": r["model"], "scenario": r["scenario"]}
            for r in rows if r["cost_treatment"] in {"embedded_in_total", "explicit_modeled"}
        ],
        "agriculture_net_adaptation_scc_status": "BLOCKED",
        "reason": "Trend and upper agriculture scenarios attenuate impacts while setting adaptation costs to zero.",
        "frEDI_adjustment": "ZERO_ADDITIONAL_CHARGE: source totals already include specified adaptation expenditures.",
        "coastal_adjustment": "ZERO_ADDITIONAL_CHARGE: CIAM OptimalCost already contains adaptation and residual costs.",
        "bounded_benchmark_is_not_allocated": True
    }
    with (results / "readiness.json").open("w", encoding="utf-8") as stream:
        json.dump(readiness, stream, indent=2)
        stream.write("\n")
    benchmark_row = {
        "benchmark_id": benchmark["benchmark_id"],
        "geography": benchmark["geography"],
        "period": benchmark["period"],
        "price_year": benchmark["price_year"],
        "low_billion_usd_per_year": benchmark["low_billion_usd_per_year"],
        "high_billion_usd_per_year": benchmark["high_billion_usd_per_year"],
        "give_mapping_available": "false",
        "scc_ready": "false"
    }
    with (results / "bounded_agriculture_cost_benchmark.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=benchmark_row.keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(benchmark_row)
    return rows, readiness, benchmark_row


if __name__ == "__main__":
    _, readiness, benchmark = build()
    print(json.dumps({"readiness": readiness, "bounded_benchmark": benchmark}, indent=2))
