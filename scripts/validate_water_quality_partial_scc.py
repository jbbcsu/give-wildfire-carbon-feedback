#!/usr/bin/env python3
"""Independently validate the annual pair and summarized partial SCC."""
import csv
import json
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / "config/water_quality_conus_partial_scc_v1.json").read_text())
    annual = list(csv.DictReader((ROOT / config["outputs"]["annual_pair"]).open()))
    bygcm = list(csv.DictReader((ROOT / config["outputs"]["by_gcm"]).open()))
    summary = list(csv.DictReader((ROOT / config["outputs"]["summary"]).open()))
    errors = []
    if len(annual) != 340: errors.append("annual row count")
    keys = [(r["gcm"], r["year"]) for r in annual]
    if len(keys) != len(set(keys)): errors.append("duplicate gcm-year")
    years = sorted({int(r["year"]) for r in annual})
    if years != list(range(2025, 2093)): errors.append("year support")
    for row in annual:
        expected = Decimal(row["pulse_damage_2015usd"]) - Decimal(row["base_damage_2015usd"])
        # R writes large annual levels at finite decimal precision; the worst
        # subtraction residual is below 1e-5 USD on roughly billion-dollar levels.
        if abs(expected - Decimal(row["marginal_damage_2015usd"])) > Decimal("2e-5"):
            errors.append("marginal identity"); break
    pulse = Decimal(str(config["give_target"]["pulse_size_metric_tonnes_co2"]))
    recomputed = {}
    for gcm in config["response"]["gcm_surfaces"]:
        total = sum((Decimal(r["discounted_marginal_damage_2020usd"]) for r in annual if r["gcm"] == gcm), Decimal(0))
        recomputed[gcm] = total / pulse
    reported = {r["gcm"]: Decimal(r["partial_scc_2020usd_per_tco2"]) for r in bygcm}
    if set(recomputed) != set(reported): errors.append("gcm coverage")
    if any(abs(recomputed[g] - reported[g]) > Decimal("1e-9") for g in recomputed): errors.append("SCC reconciliation")
    vals = sorted(reported.values())
    if abs(sum(vals) / Decimal(5) - Decimal(summary[0]["mean_partial_scc_2020usd_per_tco2"])) > Decimal("1e-9"):
        errors.append("summary mean")
    gates = config["claim_gates"]
    if gates["global_extrapolation_allowed"] or gates["additive_give_scc_allowed"]:
        errors.append("release gate")
    receipt = {"schema": "terrestrial_ecosystem_water_quality_validation/v1", "passed": not errors, "errors": errors,
               "checks": ["unique annual keys", "fixed support", "marginal identity", "independent SCC reconciliation", "fail-closed scope"]}
    path = ROOT / config["outputs"]["validation"]
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__": main()
