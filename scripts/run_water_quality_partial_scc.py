#!/usr/bin/env python3
"""Compute a bounded CONUS FrEDI freshwater-quality partial SCC benchmark."""
import csv
import hashlib
import json
import resource
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main():
    config_path = ROOT / "config/water_quality_conus_partial_scc_v1.json"
    config = json.loads(config_path.read_text())
    assert config["schema"] == "terrestrial_ecosystem_water_quality_partial_scc/v1"
    assert not config["scope"]["global_extrapolation_authorized"]
    assert not config["scope"]["cross_sector_additivity_authorized"]
    source = config["sources"]
    manifest = json.loads((ROOT / "provenance/source_manifest_v1.json").read_text())
    runtime = ROOT / source["fredi_runtime"]
    pair = ROOT / source["give_pair"]
    assert sha(runtime) == manifest["fredi"]["runtime_sha256"]
    assert sha(pair) == manifest["give_pair"]["sha256"]
    price = source["price_source"]
    assert sha(ROOT / price["path"]) == price["sha256"]
    factor = Decimal(str(price["values"]["2020"])) / Decimal(str(price["values"]["2015"]))
    assert abs(factor - Decimal(str(price["conversion_2015usd_to_2020usd"]))) < Decimal("1e-15")

    annual_path = ROOT / config["outputs"]["annual_pair"]
    subprocess.run(["Rscript", str(ROOT / "scripts/run_water_quality_annual_pair.R"), str(runtime), str(pair), str(annual_path)], check=True)
    annual = list(csv.DictReader(annual_path.open(newline="", encoding="utf-8")))
    assert len(annual) == 340
    pulse = Decimal(str(config["give_target"]["pulse_size_metric_tonnes_co2"]))
    totals = {gcm: Decimal(0) for gcm in config["response"]["gcm_surfaces"]}
    for row in annual:
        marginal_2020 = Decimal(row["marginal_damage_2015usd"]) * factor
        discounted = marginal_2020 * Decimal(row["ramsey_discount_factor"])
        row["marginal_damage_2020usd"] = format(marginal_2020, ".12f")
        row["discounted_marginal_damage_2020usd"] = format(discounted, ".12f")
        totals[row["gcm"]] += discounted
    write_csv(annual_path, annual)

    by_gcm = [{
        "scope": "CONUS_48_plus_DC",
        "endpoint": "freshwater_recreation_WTP",
        "support_years": "2025-2092",
        "gcm": gcm,
        "partial_scc_2020usd_per_tco2": format(totals[gcm] / pulse, ".12f")
    } for gcm in config["response"]["gcm_surfaces"]]
    write_csv(ROOT / config["outputs"]["by_gcm"], by_gcm)
    values = sorted(Decimal(x["partial_scc_2020usd_per_tco2"]) for x in by_gcm)
    summary = [{
        "scope": "CONUS_48_plus_DC",
        "endpoint": "freshwater_recreation_WTP",
        "support_years": "2025-2092",
        "gcm_count": str(len(values)),
        "mean_partial_scc_2020usd_per_tco2": format(sum(values) / Decimal(len(values)), ".12f"),
        "median_partial_scc_2020usd_per_tco2": format(values[2], ".12f"),
        "min_partial_scc_2020usd_per_tco2": format(values[0], ".12f"),
        "max_partial_scc_2020usd_per_tco2": format(values[-1], ".12f")
    }]
    write_csv(ROOT / config["outputs"]["summary"], summary)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    receipt = {
        "schema": "terrestrial_ecosystem_water_quality_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "bounded_CONUS_partial_SCC_benchmark_not_additive",
        "config_sha256": sha(config_path),
        "input_sha256": {"fredi_runtime": sha(runtime), "give_pair": sha(pair), "price_source": sha(ROOT / price["path"])},
        "output_sha256": {name: sha(ROOT / config["outputs"][name]) for name in ("annual_pair", "by_gcm", "summary")},
        "price_conversion_2015_to_2020": str(factor),
        "pulse_metric_tonnes_co2": str(pulse),
        "support": {"years": [2025, 2092], "max_common_conus_anomaly_c": 3.0},
        "claim_gates": config["claim_gates"],
        "peak_rss_mib_python": round(rss, 3)
    }
    (ROOT / config["outputs"]["receipt"]).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "summary": summary[0], "peak_rss_mib": receipt["peak_rss_mib_python"]}, indent=2))


if __name__ == "__main__":
    main()

