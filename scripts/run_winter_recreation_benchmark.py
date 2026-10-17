#!/usr/bin/env python3
"""Run the source-pinned FrEDI/Wobus winter-recreation revenue benchmark."""

from __future__ import annotations

import csv, hashlib, json, resource, sys
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


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, data: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(data)


def make_curve(points: list[tuple[Decimal, Decimal]]) -> dict[Decimal, Decimal]:
    clean = sorted(set([(Decimal(0), Decimal(0))] + points))
    if len(clean) < 2:
        raise ValueError("response curve has fewer than two points")
    x1, y1 = clean[-2]; x2, y2 = clean[-1]
    if x2 != Decimal(30):
        clean.append((Decimal(30), y2 + (Decimal(30) - x2) * (y2 - y1) / (x2 - x1)))
    return dict(clean)


def linear(curve: dict[Decimal, Decimal], x: Decimal) -> Decimal:
    xs = sorted(curve)
    if x < xs[0] or x > xs[-1]:
        raise ValueError(f"driver {x} outside [{xs[0]}, {xs[-1]}]")
    if x in curve:
        return curve[x]
    hi = next(v for v in xs if v > x); lo = xs[xs.index(hi) - 1]
    return curve[lo] + (x - lo) * (curve[hi] - curve[lo]) / (hi - lo)


def snapshot_value(v2010: Decimal, v2090: Decimal, year: int) -> Decimal:
    if year >= 2090:
        return v2090
    weight = Decimal(year - 2010) / Decimal(80)
    return v2010 + weight * (v2090 - v2010)


def main() -> int:
    config = json.loads((ROOT / "config/winter_recreation_benchmark_v1.json").read_text())
    assert config["schema"] == "winter_recreation_benchmark_contract/v1"
    assert config["scope"]["additivity_to_give_authorized"] is False
    for key in ("response", "population", "give_pair", "price"):
        spec = config["sources"][key]
        if digest(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"hash mismatch: {spec['path']}")

    response = rows(ROOT / config["sources"]["response"]["path"])
    if len(response) != 6624:
        raise ValueError("expected 6,624 published WinterRec response rows")
    raw: dict[tuple[str, str, str, int], list[tuple[Decimal, Decimal]]] = defaultdict(list)
    for row in response:
        if row["sector"] != "WinterRec" or row["impactType"] not in config["model"]["impact_types"]:
            raise ValueError("unauthorized response row")
        if row["value"] not in ("", "NA"):
            raw[(row["impactType"], row["model"], row["postal"], int(row["impactYear"]))].append(
                (Decimal(row["modelUnitValue"]), Decimal(row["value"]))
            )
    curves = {key: make_curve(value) for key, value in raw.items()}
    if len(curves) != 1104:
        raise ValueError(f"expected 1,104 activity/GCM/state/snapshot curves, got {len(curves)}")

    pop_rows = rows(ROOT / config["sources"]["population"]["path"])
    population = {(row["postal"], int(row["year"])): Decimal(row["value"]) for row in pop_rows}
    if len(population) != 14259 or {year for _, year in population} != set(range(2010, 2301)):
        raise ValueError("unexpected FrEDI population scalar coverage")

    pair = [row for row in rows(ROOT / config["sources"]["give_pair"]["path"]) if int(row["year"]) >= 2025]
    if len(pair) != 276:
        raise ValueError("GIVE pair must span 2025-2300")
    pulse = Decimal(str(config["give_target"]["pulse_size_metric_tonnes_co2"]))
    prices = config["sources"]["price"]["values"]
    deflator = Decimal(str(prices["2020"])) / Decimal(str(prices["2015"]))
    postals = defaultdict(set)
    for activity, gcm, postal, _ in curves:
        postals[(activity, gcm)].add(postal)

    annual = []
    totals: dict[tuple[int, str, str], Decimal] = defaultdict(Decimal)
    for activity in config["model"]["impact_types"]:
        for gcm in config["model"]["gcms"]:
            for item in pair:
                year = int(item["year"]); base_t = Decimal(item["base_conus_anomaly_c"]); pulse_t = Decimal(item["pulse_conus_anomaly_c"])
                discount = Decimal(item["ramsey_discount_factor"]); base = Decimal(0); modified = Decimal(0)
                for postal in postals[(activity, gcm)]:
                    pop = population[(postal, year)]
                    base10 = linear(curves[(activity, gcm, postal, 2010)], base_t)
                    base90 = linear(curves[(activity, gcm, postal, 2090)], base_t)
                    pulse10 = linear(curves[(activity, gcm, postal, 2010)], pulse_t)
                    pulse90 = linear(curves[(activity, gcm, postal, 2090)], pulse_t)
                    base += snapshot_value(base10, base90, year) * pop
                    modified += snapshot_value(pulse10, pulse90, year) * pop
                marginal = modified - base; discounted = marginal * deflator * discount
                for horizon in (2092, 2300):
                    if year <= horizon:
                        totals[(horizon, gcm, activity)] += discounted
                annual.append({
                    "year": year, "gcm": gcm, "activity": activity,
                    "base_conus_anomaly_c": format(base_t, "f"), "pulse_conus_anomaly_c": format(pulse_t, "f"),
                    "base_lost_revenue_2015usd": format(base, ".12f"), "pulse_lost_revenue_2015usd": format(modified, ".12f"),
                    "marginal_lost_revenue_2015usd": format(marginal, ".12f"),
                    "discounted_marginal_lost_revenue_2020usd": format(discounted, ".12f")
                })
    annual_path = ROOT / config["outputs"]["annual"]; write(annual_path, annual)

    by_gcm = []
    for horizon in (2092, 2300):
        for gcm in config["model"]["gcms"]:
            values = {activity: totals[(horizon, gcm, activity)] / pulse for activity in config["model"]["impact_types"]}
            by_gcm.append({
                "scope": "CONUS", "support_years": f"2025-{horizon}", "horizon": horizon, "gcm": gcm,
                "alpine_revenue_benchmark_2020usd_per_tco2": format(values["Alpine"], ".12f"),
                "xc_revenue_benchmark_2020usd_per_tco2": format(values["XC"], ".12f"),
                "snowmobiling_revenue_benchmark_2020usd_per_tco2": format(values["Snowmobiling"], ".12f"),
                "total_revenue_benchmark_2020usd_per_tco2": format(sum(values.values()), ".12f")
            })
    by_gcm_path = ROOT / config["outputs"]["by_gcm"]; write(by_gcm_path, by_gcm)

    columns = (("Alpine", "alpine_revenue_benchmark_2020usd_per_tco2"), ("XC", "xc_revenue_benchmark_2020usd_per_tco2"),
               ("Snowmobiling", "snowmobiling_revenue_benchmark_2020usd_per_tco2"), ("Total", "total_revenue_benchmark_2020usd_per_tco2"))
    summary = []
    for horizon in (2092, 2300):
        selected = [r for r in by_gcm if r["horizon"] == horizon]
        for component, column in columns:
            values = sorted(Decimal(r[column]) for r in selected)
            summary.append({
                "scope": "CONUS", "support_years": f"2025-{horizon}", "horizon": horizon, "component": component,
                "gcm_count": len(values), "mean_2020usd_per_tco2": format(sum(values) / Decimal(len(values)), ".12f"),
                "median_2020usd_per_tco2": format((values[2] + values[3]) / 2, ".12f"),
                "min_2020usd_per_tco2": format(values[0], ".12f"), "max_2020usd_per_tco2": format(values[-1], ".12f"),
                "metric": "marginal lost ticket/entry revenue; not social welfare", "additive_to_give": "false"
            })
    summary_path = ROOT / config["outputs"]["summary"]; write(summary_path, summary)
    receipt = {
        "schema": "winter_recreation_partial_scc_receipt/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLISHED_CONUS_REVENUE_BENCHMARK_NOT_ADDITIVE",
        "broader_tourism_status": "BLOCKED_NO_EXECUTABLE_WELFARE_FUNCTION",
        "inputs": {k: {"path": config["sources"][k]["path"], "sha256": config["sources"][k]["sha256"]} for k in ("response", "population", "give_pair", "price")},
        "outputs": {name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "rows": len(data)} for name, path, data in (("annual", annual_path, annual), ("by_gcm", by_gcm_path, by_gcm), ("summary", summary_path, summary))},
        "price_conversion_2015_to_2020": str(deflator), "claim_scope": config["scope"],
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024), 3)
    }
    receipt_path = ROOT / config["outputs"]["receipt"]
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"full_horizon_total": summary[-1], "receipt": str(receipt_path), "peak_rss_mib": receipt["peak_rss_mib"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
