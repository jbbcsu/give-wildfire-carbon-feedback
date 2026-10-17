#!/usr/bin/env python3
"""Compute a bounded CONUS riverine-flood property partial SCC."""

from __future__ import annotations

import argparse
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def interpolate(knots: dict[Decimal, Decimal], x: Decimal) -> Decimal:
    """Piecewise-linear interpolation with FrEDI's endpoint extrapolation."""
    xs = sorted(knots)
    if x <= xs[0]:
        left, right = xs[0], xs[1]
    elif x >= xs[-1]:
        left, right = xs[-2], xs[-1]
    else:
        right = next(value for value in xs if value >= x)
        left = xs[xs.index(right) - 1]
    return knots[left] + (x - left) * (knots[right] - knots[left]) / (right - left)


def quantile(values: list[Decimal], probability: Decimal) -> Decimal:
    ordered = sorted(values)
    position = probability * Decimal(len(ordered) - 1)
    lower = int(position)
    fraction = position - Decimal(lower)
    if fraction == 0:
        return ordered[lower]
    return ordered[lower] + fraction * (ordered[lower + 1] - ordered[lower])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/inland_flood_scc_v1.json")
    args = parser.parse_args()
    config_path = ROOT / args.config
    config = json.loads(config_path.read_text())
    assert config["schema"] == "inland_flood_scc_contract/v1"
    assert not config["claim_gates"]["global_scc_authorized"]
    assert not config["claim_gates"]["pluvial_flooding_included"]

    source_spec = config["sources"]["fredi_table"]
    pair_spec = config["sources"]["give_pair"]
    price_spec = config["sources"]["price_source"]
    for spec in (source_spec, pair_spec, price_spec):
        if digest(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"source hash mismatch: {spec['path']}")

    source_rows = read_csv(ROOT / source_spec["path"])
    if len(source_rows) != 245:
        raise ValueError("expected 245 EPA rows (49 jurisdictions x 5 knots)")
    curves: dict[str, dict[Decimal, Decimal]] = defaultdict(lambda: {Decimal(0): Decimal(0)})
    names: dict[str, str] = {}
    for row in source_rows:
        if row["sector"] != "InlandFlooding" or row["model"] != "GCM Ensemble":
            raise ValueError("source contains an unauthorized sector or model")
        if row["variant"] != "NA" or row["impactType"] != "NA":
            raise ValueError("unexpected released variant or impact type")
        postal = row["postal"]
        curves[postal][Decimal(row["modelUnitValue"])] = Decimal(row["value"])
        names[postal] = row["state"]
    if len(curves) != 49 or any(set(curve) != {Decimal(i) for i in range(6)} for curve in curves.values()):
        raise ValueError("incomplete state/DC response support")

    pair = [row for row in read_csv(ROOT / pair_spec["path"]) if int(row["year"]) >= pair_spec["pulse_year"]]
    if len(pair) != 276 or int(pair[0]["year"]) != 2025 or int(pair[-1]["year"]) != 2300:
        raise ValueError("GIVE pair must cover 2025-2300")

    deflator = Decimal(str(price_spec["values"]["2020"])) / Decimal(str(price_spec["values"]["2015"]))
    pulse_tco2 = Decimal(str(config["give_target"]["pulse_size_metric_tonnes_co2"]))
    annual: list[dict[str, object]] = []
    discounted_state: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    max_bounded_year = 0
    for row in pair:
        year = int(row["year"])
        base_t = Decimal(row["base_conus_anomaly_c"])
        pulse_t = Decimal(row["pulse_conus_anomaly_c"])
        discount = Decimal(row["ramsey_discount_factor"])
        if max(base_t, pulse_t) <= 5:
            max_bounded_year = year
        base_total = Decimal(0)
        pulse_total = Decimal(0)
        for postal, curve in curves.items():
            base = interpolate(curve, base_t)
            pulse = interpolate(curve, pulse_t)
            base_total += base
            pulse_total += pulse
            if year <= 2300:
                discounted_state[2300][postal] += (pulse - base) * deflator * discount
        marginal_2015 = pulse_total - base_total
        annual.append({
            "year": year,
            "base_conus_anomaly_c": format(base_t, "f"),
            "pulse_conus_anomaly_c": format(pulse_t, "f"),
            "base_damage_2015usd": format(base_total, ".12f"),
            "pulse_damage_2015usd": format(pulse_total, ".12f"),
            "marginal_damage_2015usd": format(marginal_2015, ".12f"),
            "marginal_damage_2020usd": format(marginal_2015 * deflator, ".12f"),
            "ramsey_discount_factor": row["ramsey_discount_factor"],
            "discounted_marginal_damage_2020usd": format(marginal_2015 * deflator * discount, ".12f"),
            "uses_response_extrapolation": str(max(base_t, pulse_t) > 5).lower(),
        })

    annual_path = ROOT / config["outputs"]["annual_national"]
    write_csv(annual_path, annual)
    horizons = [2092, max_bounded_year, 2300]
    summary: list[dict[str, object]] = []
    for horizon in horizons:
        selected = [row for row in annual if int(row["year"]) <= horizon]
        present_value = sum(Decimal(str(row["discounted_marginal_damage_2020usd"])) for row in selected)
        summary.append({
            "scope": "CONUS_48_plus_DC",
            "endpoint": "riverine_flood_property_damage",
            "support_years": f"2025-{horizon}",
            "horizon": horizon,
            "response_treatment": "within_released_0_5C_knots" if horizon <= max_bounded_year else "official_linear_endpoint_extrapolation",
            "discounted_marginal_damage_2020usd": format(present_value, ".12f"),
            "partial_scc_2020usd_per_tco2": format(present_value / pulse_tco2, ".12f"),
        })
    summary_path = ROOT / config["outputs"]["summary"]
    write_csv(summary_path, summary)

    # State results use the primary full horizon. Distribution statistics describe
    # spatial heterogeneity, not statistical uncertainty.
    state_rows = []
    for postal in sorted(curves):
        pv = discounted_state[2300][postal]
        state_rows.append({
            "state": names[postal], "postal": postal, "support_years": "2025-2300",
            "discounted_marginal_damage_2020usd": format(pv, ".12f"),
            "partial_scc_2020usd_per_tco2": format(pv / pulse_tco2, ".12f"),
        })
    state_path = ROOT / config["outputs"]["by_state"]
    write_csv(state_path, state_rows)

    state_scc = [Decimal(str(row["partial_scc_2020usd_per_tco2"])) for row in state_rows]
    receipt = {
        "schema": "inland_flood_partial_scc_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CONUS_partial_SCC_benchmark",
        "config": {"path": args.config, "sha256": digest(config_path)},
        "inputs": {name: {"path": spec["path"], "sha256": spec["sha256"]} for name, spec in (
            ("fredi_table", source_spec), ("give_pair", pair_spec), ("price_source", price_spec)
        )},
        "outputs": {name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "rows": len(rows)} for name, path, rows in (
            ("annual_national", annual_path, annual), ("summary", summary_path, summary), ("by_state", state_path, state_rows)
        )},
        "price_conversion_2015_to_2020": str(deflator),
        "last_year_within_released_0_5c_response": max_bounded_year,
        "spatial_heterogeneity_not_uncertainty": {
            "negative_state_count": sum(value < 0 for value in state_scc),
            "p05": format(quantile(state_scc, Decimal("0.05")), ".12f"),
            "median": format(quantile(state_scc, Decimal("0.5")), ".12f"),
            "p95": format(quantile(state_scc, Decimal("0.95")), ".12f")
        },
        "released_uncertainty": "none: EPA table contains one GCM Ensemble surface and no parametric draws",
        "claim_gates": config["claim_gates"],
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024), 3)
    }
    receipt_path = ROOT / config["outputs"]["receipt"]
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"primary": summary[-1], "bounded": summary[1], "receipt": str(receipt_path), "peak_rss_mib": receipt["peak_rss_mib"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
