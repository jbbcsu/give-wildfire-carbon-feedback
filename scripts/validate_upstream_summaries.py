#!/usr/bin/env python3
"""Audit checked-in EPA globalAQ_rft summaries against the final article."""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor" / "globalAQ_rft" / "output" / "npd"
RATE = "2.0% Ramsey"
ARTICLE = {"Ozone": 23.0, "PM": -38.0, "Net": -15.0}


def read_csv(name: str) -> list[dict[str, str]]:
    with (UPSTREAM / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def mean_component(rows: list[dict[str, str]], pollutant: str) -> tuple[float, dict[str, float]]:
    selected = {
        row["Model"]: float(row["mean_npd"])
        for row in rows
        if row["discount.rate"] == RATE and row["Pollutant"] == pollutant
    }
    if set(selected) != {"CESM2", "GISS"}:
        raise ValueError(f"Unexpected models for {pollutant}: {sorted(selected)}")
    return statistics.mean(selected.values()), selected


def main() -> None:
    components = read_csv("npd_global_rff_means.csv")
    net_rows = read_csv("npd_global_rff_net_means.csv")
    ozone, ozone_models = mean_component(components, "Ozone")
    pm, pm_models = mean_component(components, "PM")
    net_models = {
        row["Model"]: float(row["mean_npd"])
        for row in net_rows
        if row["discount.rate"] == RATE
    }
    if set(net_models) != {"CESM2", "GISS"}:
        raise ValueError(f"Unexpected net models: {sorted(net_models)}")
    net = statistics.mean(net_models.values())
    report = {
        "discount_schedule": RATE,
        "upstream_component_means": {"Ozone": ozone, "PM": pm},
        "upstream_net_mean": net,
        "upstream_model_values": {
            "Ozone": ozone_models,
            "PM": pm_models,
            "Net": net_models,
        },
        "component_sum": ozone + pm,
        "net_minus_component_sum": net - (ozone + pm),
        "article_reported_means": ARTICLE,
        "article_minus_upstream": {
            "Ozone": ARTICLE["Ozone"] - ozone,
            "PM": ARTICLE["PM"] - pm,
            "Net": ARTICLE["Net"] - net,
        },
        "local_reproduction_passed": False,
        "reason": (
            "Checked-in upstream summaries differ from final article values and the "
            "checked-in net summary is not arithmetically equal to the component means."
        ),
    }
    output = ROOT / "data" / "provenance" / "epa_globalaq_summary_audit_20261009.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
