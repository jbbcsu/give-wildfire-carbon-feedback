#!/usr/bin/env python3
"""Run the published CONUS CIL/FrEDI crime matched-pulse benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
import resource
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def linear(curve: dict[Decimal, Decimal], x: Decimal) -> Decimal:
    xs = sorted(curve)
    if x <= xs[0]:
        lo, hi = xs[0], xs[1]
    elif x >= xs[-1]:
        lo, hi = xs[-2], xs[-1]
    else:
        hi = next(k for k in xs if k >= x)
        lo = xs[xs.index(hi) - 1]
    return curve[lo] + (x - lo) * (curve[hi] - curve[lo]) / (hi - lo)


def main() -> int:
    config_path = ROOT / "config/conflict_crime_benchmark_v1.json"
    config = json.loads(config_path.read_text())
    assert config["schema"] == "conflict_crime_benchmark_contract/v1"
    assert config["scope"]["organized_armed_conflict"] == "BLOCKED_NO_SCC"
    assert config["scope"]["additivity_to_give_authorized"] is False
    for key in ("response", "property_cost", "violent_cost", "give_pair", "price"):
        spec = config["sources"][key]
        if digest(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"hash mismatch: {spec['path']}")

    response = read_rows(ROOT / config["sources"]["response"]["path"])
    if len(response) != 3038:
        raise ValueError("unexpected response row count")
    curves: dict[tuple[str, str, str], dict[Decimal, Decimal]] = defaultdict(lambda: {Decimal(0): Decimal(0)})
    for row in response:
        if row["sector"] != "CILCrime" or row["impactType"] not in config["model"]["impact_types"]:
            raise ValueError("unauthorized response row")
        curves[(row["impactType"], row["model"], row["postal"])][Decimal(row["modelUnitValue"])] = Decimal(row["value"])
    expected = {(impact, gcm, postal) for impact in config["model"]["impact_types"] for gcm in config["model"]["gcms"] for postal in {row["postal"] for row in response}}
    if set(curves) != expected or len({key[2] for key in curves}) != 49:
        raise ValueError("response does not cover 2 impacts x 6 GCMs x 49 jurisdictions")

    costs = {}
    for impact, key in (("Property", "property_cost"), ("Violent", "violent_cost")):
        rows = read_rows(ROOT / config["sources"][key]["path"])
        if len(rows) != 49 or {int(row["year"]) for row in rows} != {2010}:
            raise ValueError("cost scalar must be 49 state/DC values for 2010")
        costs[impact] = {row["postal"]: Decimal(row["value"]) for row in rows}

    pair = [row for row in read_rows(ROOT / config["sources"]["give_pair"]["path"]) if int(row["year"]) >= 2025]
    if len(pair) != 276:
        raise ValueError("GIVE pair must span 2025-2300")
    price = config["sources"]["price"]["values"]
    deflator = Decimal(str(price["2020"])) / Decimal(str(price["2015"]))
    pulse = Decimal(str(config["give_target"]["pulse_size_metric_tonnes_co2"]))

    annual = []
    totals: dict[tuple[int, str, str], Decimal] = defaultdict(Decimal)
    for impact in config["model"]["impact_types"]:
        for gcm in config["model"]["gcms"]:
            for item in pair:
                year = int(item["year"]); base_t = Decimal(item["base_conus_anomaly_c"]); pulse_t = Decimal(item["pulse_conus_anomaly_c"])
                discount = Decimal(item["ramsey_discount_factor"]); base = Decimal(0); modified = Decimal(0); extrapolated = False
                for postal in costs[impact]:
                    curve = curves[(impact, gcm, postal)]
                    extrapolated |= max(base_t, pulse_t) > max(curve)
                    base += linear(curve, base_t) * costs[impact][postal]
                    modified += linear(curve, pulse_t) * costs[impact][postal]
                marginal_2015 = modified - base
                discounted = marginal_2015 * deflator * discount
                for horizon in (2092, 2300):
                    if year <= horizon:
                        totals[(horizon, gcm, impact)] += discounted
                annual.append({
                    "year": year, "gcm": gcm, "impact_type": impact,
                    "base_conus_anomaly_c": format(base_t, "f"), "pulse_conus_anomaly_c": format(pulse_t, "f"),
                    "base_damage_2015usd": format(base, ".12f"), "pulse_damage_2015usd": format(modified, ".12f"),
                    "marginal_damage_2015usd": format(marginal_2015, ".12f"),
                    "discounted_marginal_damage_2020usd": format(discounted, ".12f"),
                    "uses_response_extrapolation": str(extrapolated).lower()
                })
    annual_path = ROOT / config["outputs"]["annual"]
    write_rows(annual_path, annual)

    by_gcm = []
    for horizon in (2092, 2300):
        for gcm in config["model"]["gcms"]:
            prop = totals[(horizon, gcm, "Property")] / pulse
            violent = totals[(horizon, gcm, "Violent")] / pulse
            by_gcm.append({
                "scope": "CONUS_48_plus_DC", "support_years": f"2025-{horizon}", "horizon": horizon, "gcm": gcm,
                "property_partial_scc_2020usd_per_tco2": format(prop, ".12f"),
                "violent_partial_scc_2020usd_per_tco2": format(violent, ".12f"),
                "total_benchmark_2020usd_per_tco2": format(prop + violent, ".12f")
            })
    by_gcm_path = ROOT / config["outputs"]["by_gcm"]
    write_rows(by_gcm_path, by_gcm)

    summary = []
    columns = (("Property", "property_partial_scc_2020usd_per_tco2"), ("Violent", "violent_partial_scc_2020usd_per_tco2"), ("Total", "total_benchmark_2020usd_per_tco2"))
    for horizon in (2092, 2300):
        selected = [row for row in by_gcm if row["horizon"] == horizon]
        for component, column in columns:
            values = sorted(Decimal(str(row[column])) for row in selected)
            summary.append({
                "scope": "CONUS_48_plus_DC", "support_years": f"2025-{horizon}", "horizon": horizon, "component": component,
                "gcm_count": len(values), "mean_2020usd_per_tco2": format(sum(values) / Decimal(len(values)), ".12f"),
                "median_2020usd_per_tco2": format((values[2] + values[3]) / 2, ".12f"),
                "min_2020usd_per_tco2": format(values[0], ".12f"), "max_2020usd_per_tco2": format(values[-1], ".12f"),
                "additive_to_give": "false"
            })
    summary_path = ROOT / config["outputs"]["summary"]
    write_rows(summary_path, summary)

    receipt = {
        "schema": "crime_partial_scc_receipt/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLISHED_CONUS_BENCHMARK_NOT_ADDITIVE", "organized_armed_conflict_status": "BLOCKED_NO_SCC",
        "inputs": {key: {"path": config["sources"][key]["path"], "sha256": config["sources"][key]["sha256"]} for key in ("response", "property_cost", "violent_cost", "give_pair", "price")},
        "outputs": {name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "rows": len(rows)} for name, path, rows in (("annual", annual_path, annual), ("by_gcm", by_gcm_path, by_gcm), ("summary", summary_path, summary))},
        "price_conversion_2015_to_2020": str(deflator), "claim_scope": config["scope"],
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024), 3)
    }
    receipt_path = ROOT / config["outputs"]["receipt"]
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"full_horizon": summary[-1], "receipt": str(receipt_path), "peak_rss_mib": receipt["peak_rss_mib"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

