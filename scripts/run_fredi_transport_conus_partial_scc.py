#!/usr/bin/env python3
"""Run the bounded, CONUS-only FrEDI Roads + Rail matched-pulse SCC calculation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import resource
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def peak_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024 if sys.platform == "darwin" else 1024)


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/fredi_transport_conus_partial_scc_v1.json")
    args = parser.parse_args()
    config_path = ROOT / args.config
    config = json.loads(config_path.read_text())
    assert config["schema"] == "fredi_transport_conus_partial_scc_contract/v1"
    assert not config["scope"]["global_extrapolation_authorized"]
    assert not config["scope"]["additivity_to_other_give_sectors_authorized"]

    price = config["sources"]["fred_price_source"]
    price_path = ROOT / price["path"]
    assert sha(price_path) == price["sha256"]
    factor = Decimal(str(price["values"]["2020"])) / Decimal(str(price["values"]["2015"]))
    assert abs(factor - Decimal(str(price["conversion_2015usd_to_2020usd"]))) < Decimal("1e-15")

    annual_path = ROOT / config["outputs"]["annual_pair"]
    subprocess.run(
        ["Rscript", str(ROOT / "scripts/run_fredi_transport_annual_pair.R"),
         str(ROOT / config["sources"]["fredi_runtime"]),
         str(ROOT / config["sources"]["give_pair"]), str(annual_path)],
        check=True,
    )

    annual = list(csv.DictReader(annual_path.open(encoding="utf-8", newline="")))
    assert len(annual) == 2448
    pulse_tco2 = Decimal(str(config["give_target"]["pulse_size_gtc"])) * Decimal("1e9") * Decimal(44) / Decimal(12)
    groups: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for row in annual:
        marginal_2015 = Decimal(row["marginal_damage_2015usd"])
        marginal_2020 = marginal_2015 * factor
        discounted = marginal_2020 * Decimal(row["ramsey_discount_factor"])
        row["marginal_damage_2020usd"] = format(marginal_2020, ".12f")
        row["discounted_marginal_damage_2020usd"] = format(discounted, ".12f")
        groups[(row["variant"], row["gcm"])][row["released_aggregate"]] += discounted

    annual_fields = list(annual[0])
    write_rows(annual_path, annual, annual_fields)

    by_gcm = []
    for variant in config["response"]["sensitivity_variants"] + [config["response"]["primary_variant"]]:
        for gcm in config["response"]["gcm_surfaces"]:
            values = groups[(variant, gcm)]
            roads = values["Roads"] / pulse_tco2
            rail = values["Rail"] / pulse_tco2
            by_gcm.append({
                "scope": "CONUS_48_plus_DC",
                "support_years": "2025-2092",
                "variant": variant,
                "gcm": gcm,
                "roads_partial_scc_2020usd_per_tco2": format(roads, ".12f"),
                "rail_partial_scc_2020usd_per_tco2": format(rail, ".12f"),
                "total_partial_scc_2020usd_per_tco2": format(roads + rail, ".12f"),
            })
    by_gcm_path = ROOT / config["outputs"]["by_gcm"]
    write_rows(by_gcm_path, by_gcm, list(by_gcm[0]))

    summary = []
    for variant in config["response"]["sensitivity_variants"] + [config["response"]["primary_variant"]]:
        selected = [row for row in by_gcm if row["variant"] == variant]
        for component, column in (
            ("Roads", "roads_partial_scc_2020usd_per_tco2"),
            ("Rail", "rail_partial_scc_2020usd_per_tco2"),
            ("Roads_plus_Rail", "total_partial_scc_2020usd_per_tco2"),
        ):
            values = sorted(Decimal(row[column]) for row in selected)
            mean = sum(values, Decimal(0)) / Decimal(len(values))
            median = (values[2] + values[3]) / Decimal(2)
            summary.append({
                "scope": "CONUS_48_plus_DC",
                "support_years": "2025-2092",
                "variant": variant,
                "component": component,
                "gcm_count": str(len(values)),
                "mean_partial_scc_2020usd_per_tco2": format(mean, ".12f"),
                "median_partial_scc_2020usd_per_tco2": format(median, ".12f"),
                "min_partial_scc_2020usd_per_tco2": format(values[0], ".12f"),
                "max_partial_scc_2020usd_per_tco2": format(values[-1], ".12f"),
            })
    summary_path = ROOT / config["outputs"]["summary"]
    write_rows(summary_path, summary, list(summary[0]))

    receipt = {
        "schema": "fredi_transport_conus_partial_scc_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CONUS_partial_SCC_only",
        "config": {"path": args.config, "sha256": sha(config_path)},
        "inputs": {name: {"path": path, "sha256": sha(ROOT / path)} for name, path in {
            "fredi_manifest": config["sources"]["fredi_manifest"],
            "fredi_runtime": config["sources"]["fredi_runtime"],
            "give_pair": config["sources"]["give_pair"],
            "fred_price_source": price["path"],
        }.items()},
        "execution_code": {path: sha(ROOT / path) for path in (
            "scripts/run_fredi_transport_annual_pair.R",
            "scripts/run_fredi_transport_conus_partial_scc.py",
        )},
        "outputs": {name: {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "rows": count} for name, path, count in (
            ("annual_pair", annual_path, len(annual)), ("by_gcm", by_gcm_path, len(by_gcm)), ("summary", summary_path, len(summary))
        )},
        "price_conversion": {"2015_to_2020": str(factor), "source_series": "GDPDEF"},
        "normalization": {"pulse_metric_tonnes_co2": str(pulse_tco2), "discount_factor_source": "matched GIVE base consumption path"},
        "support": {"years": [2025, 2092], "first_excluded_year": 2093, "max_common_conus_anomaly_c": 3.0},
        "claim_gates": config["claim_gates"],
        "peak_rss_mib_python": round(peak_mib(), 3),
    }
    receipt_path = ROOT / config["outputs"]["receipt"]
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    primary = next(row for row in summary if row["variant"] == "Reactive" and row["component"] == "Roads_plus_Rail")
    print(json.dumps({"status": receipt["status"], "primary": primary, "peak_rss_mib": receipt["peak_rss_mib_python"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
