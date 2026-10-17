#!/usr/bin/env python3
"""Independent raw-table validation of the CONUS FrEDI Roads + Rail partial SCC."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import resource
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def dec(value: str | float | int) -> Decimal:
    answer = Decimal(str(value))
    assert answer.is_finite()
    return answer


def interp_response(values: dict[int, Decimal], x: Decimal) -> Decimal:
    assert Decimal(0) <= x <= Decimal(3)
    if x <= 1:
        return x * values[1]
    lower = int(x)
    if x == lower:
        return values[lower]
    assert lower in (1, 2)
    return values[lower] + (x - lower) * (values[lower + 1] - values[lower])


def interp_year(values: dict[int, Decimal], year: int) -> Decimal:
    if year in values:
        return values[year]
    lower = max(y for y in values if y < year)
    upper = min(y for y in values if y > year)
    return values[lower] + Decimal(year - lower) / Decimal(upper - lower) * (values[upper] - values[lower])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config_path = ROOT / "config/fredi_transport_conus_partial_scc_v1.json"
    config = json.loads(config_path.read_text())
    assert config["schema"] == "fredi_transport_conus_partial_scc_contract/v1"
    assert config["claim_gates"]["conus_partial_scc_authorized"]
    assert not config["claim_gates"]["global_extrapolation_authorized"]
    assert not config["claim_gates"]["cross_sector_additivity_authorized"]

    price = config["sources"]["fred_price_source"]
    price_path = ROOT / price["path"]
    assert sha(price_path) == price["sha256"]
    price_rows = {row["observation_date"][:4]: dec(row["GDPDEF"]) for row in rows(price_path)}
    assert price_rows["2015"] == dec(price["values"]["2015"])
    assert price_rows["2020"] == dec(price["values"]["2020"])
    factor = price_rows["2020"] / price_rows["2015"]
    assert abs(factor - dec(price["conversion_2015usd_to_2020usd"])) < Decimal("1e-15")

    pair_rows = list(rows(ROOT / config["sources"]["give_pair"]))
    pair = {int(row["year"]): row for row in pair_rows}
    admitted = [y for y in pair if y >= 2025 and max(dec(pair[y]["base_conus_anomaly_c"]), dec(pair[y]["pulse_conus_anomaly_c"])) <= 3]
    assert admitted == list(range(2025, 2093))
    assert max(dec(pair[2093]["base_conus_anomaly_c"]), dec(pair[2093]["pulse_conus_anomaly_c"])) > 3

    raw = ROOT / "data/raw/fredi_data/inst/extdata/fredi"
    response: dict[tuple[str, str, str, str], dict[int, Decimal]] = defaultdict(dict)
    states: set[str] | None = None
    for sector in ("Roads", "Rail"):
        current_states = set()
        for row in rows(raw / "gcm" / f"{sector}_scaledimpacts.csv"):
            current_states.add(row["postal"])
            bin_number = int(row["modelUnitValue"])
            if bin_number <= 3:
                response[(sector, row["variant"], row["model"], row["postal"])][bin_number] = dec(row["value"])
        assert len(current_states) == 49
        states = current_states if states is None else states
        assert current_states == states
    assert all(set(value) == {1, 2, 3} for value in response.values())

    miles: dict[str, dict[str, Decimal]] = {}
    for sector, token in (("Roads", "road"), ("Rail", "rail")):
        by_state: dict[str, dict[int, Decimal]] = defaultdict(dict)
        for row in rows(raw / "scalars" / f"Scalar_physScalar_{token}_miles.csv"):
            by_state[row["postal"]][int(row["year"])] = dec(row["value"])
        assert set(by_state) == states
        assert all(set(value) == {2010, 2090} and value[2010] == value[2090] for value in by_state.values())
        miles[sector] = {postal: value[2010] for postal, value in by_state.items()}

    road_adj: dict[str, dict[str, dict[int, Decimal]]] = {}
    for variant in ("NoAdapt", "Proactive", "Reactive"):
        by_state = defaultdict(dict)
        for row in rows(raw / "scalars" / f"Scalar_damageAdj_road_miles_and_pop_{variant}.csv"):
            by_state[row["postal"]][int(row["year"])] = dec(row["value"])
        assert set(by_state) == states
        assert all(set(value) == set(range(2010, 2091)) for value in by_state.values())
        road_adj[variant] = by_state
    rail_growth = {int(row["year"]): dec(row["value"]) for row in rows(raw / "scalars/Scalar_damageAdj_rail_growth_factor.csv")}
    assert min(rail_growth) == 2010 and max(rail_growth) == 2300

    annual_path = ROOT / config["outputs"]["annual_pair"]
    observed_rows = list(rows(annual_path))
    assert len(observed_rows) == 2448
    observed = {(int(row["year"]), row["variant"], row["gcm"], row["released_aggregate"]): row for row in observed_rows}
    assert len(observed) == len(observed_rows)
    totals: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    max_abs_annual = Decimal(0)
    pulse_tco2 = dec(config["give_target"]["pulse_size_gtc"]) * Decimal("1e9") * Decimal(44) / Decimal(12)

    for key, row in observed.items():
        year, variant, gcm, sector = key
        assert year in admitted and row["scope"] == "CONUS_48_plus_DC"
        base_temp = dec(pair[year]["base_conus_anomaly_c"])
        pulse_temp = dec(pair[year]["pulse_conus_anomaly_c"])
        base = Decimal(0)
        pulse = Decimal(0)
        for postal in states:
            curve = response[(sector, variant, gcm, postal)]
            if sector == "Roads":
                adjustment = road_adj[variant][postal][min(year, 2090)]
            else:
                adjustment = interp_year(rail_growth, year)
            scalar = miles[sector][postal] * adjustment
            base += interp_response(curve, base_temp) * scalar
            pulse += interp_response(curve, pulse_temp) * scalar
        for expected, column in ((base, "base_damage_2015usd"), (pulse, "pulse_damage_2015usd"), (pulse - base, "marginal_damage_2015usd")):
            difference = abs(expected - dec(row[column]))
            max_abs_annual = max(max_abs_annual, difference)
            assert difference <= max(Decimal("0.001"), abs(expected) * Decimal("2e-12")), (key, column, difference)
        expected_2020 = (pulse - base) * factor
        expected_discounted = expected_2020 * dec(pair[year]["ramsey_discount_factor"])
        assert abs(expected_2020 - dec(row["marginal_damage_2020usd"])) < Decimal("0.001")
        assert abs(expected_discounted - dec(row["discounted_marginal_damage_2020usd"])) < Decimal("0.001")
        totals[(variant, gcm, sector)] += expected_discounted

    by_gcm_path = ROOT / config["outputs"]["by_gcm"]
    by_gcm_rows = list(rows(by_gcm_path))
    assert len(by_gcm_rows) == 18
    for row in by_gcm_rows:
        roads = totals[(row["variant"], row["gcm"], "Roads")] / pulse_tco2
        rail = totals[(row["variant"], row["gcm"], "Rail")] / pulse_tco2
        assert abs(roads - dec(row["roads_partial_scc_2020usd_per_tco2"])) < Decimal("1e-7")
        assert abs(rail - dec(row["rail_partial_scc_2020usd_per_tco2"])) < Decimal("1e-7")
        assert abs(roads + rail - dec(row["total_partial_scc_2020usd_per_tco2"])) < Decimal("1e-7")

    summary_path = ROOT / config["outputs"]["summary"]
    summary = list(rows(summary_path))
    assert len(summary) == 9
    primary = next(row for row in summary if row["variant"] == "Reactive" and row["component"] == "Roads_plus_Rail")
    assert dec(primary["mean_partial_scc_2020usd_per_tco2"]) > 0
    assert dec(primary["min_partial_scc_2020usd_per_tco2"]) <= dec(primary["mean_partial_scc_2020usd_per_tco2"]) <= dec(primary["max_partial_scc_2020usd_per_tco2"])

    receipt_path = ROOT / config["outputs"]["receipt"]
    receipt = json.loads(receipt_path.read_text())
    assert receipt["config"]["sha256"] == sha(config_path)
    assert receipt["outputs"]["annual_pair"]["sha256"] == sha(annual_path)
    assert receipt["outputs"]["by_gcm"]["sha256"] == sha(by_gcm_path)
    assert receipt["outputs"]["summary"]["sha256"] == sha(summary_path)
    assert receipt["support"] == {"years": [2025, 2092], "first_excluded_year": 2093, "max_common_conus_anomaly_c": 3.0}

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    assert rss < 512
    result = {
        "schema": "fredi_transport_conus_partial_scc_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "independent_raw_table_recomputation": True,
        "annual_rows": len(observed_rows),
        "by_gcm_rows": len(by_gcm_rows),
        "summary_rows": len(summary),
        "common_support_years": [2025, 2092],
        "first_excluded_year": 2093,
        "max_abs_annual_damage_difference_2015usd": str(max_abs_annual),
        "primary_reactive_mean_2020usd_per_tco2": primary["mean_partial_scc_2020usd_per_tco2"],
        "global_extrapolation": "PROHIBITED",
        "cross_sector_additivity": "NOT_AUTHORIZED",
        "peak_rss_mib": round(rss, 3),
    }
    output = args.output or (ROOT / config["outputs"]["validation"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
