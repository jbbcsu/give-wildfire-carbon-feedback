#!/usr/bin/env python3
"""Independent audit of descriptive crop-weather/GMST scenario ratios."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "data/interim/three_esm_maize_area_weather_20260918/result.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(left, right):
    if not math.isclose(float(left), float(right), rel_tol=2e-14, abs_tol=2e-12):
        raise ValueError(f"numerical audit failed: {left} != {right}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result_path, out = args.result.resolve(), args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        parser.error("fresh ignored output required")
    result = json.loads(result_path.read_text())
    if sha(PARENT) != result["parent_weather_sha256"]:
        raise ValueError("weather parent changed")
    parent = json.loads(PARENT.read_text())
    source_means = {}
    for source in result["gmst_sources"]:
        path = ROOT / source["path"]
        if sha(path) != source["sha256"]:
            raise ValueError("GMST source changed")
        columns = pq.read_table(path, columns=["year", "gmst_value_k"]).to_pydict()
        values = [float(value) for year, value in zip(columns["year"], columns["gmst_value_k"])
                  if 2092 <= int(year) <= 2099]
        if len(values) != 8:
            raise ValueError("GMST audit window incomplete")
        mean = math.fsum(values) / 8
        close(mean, source["mean_2092_2099_k"])
        source_means[(source["esm"], source["scenario"])] = mean
    weather = {}
    for annual in parent["annual_panels"]:
        key = (annual["esm"], annual["scenario"])
        weather.setdefault(key, []).append(annual)
    checks = 0
    for record in result["records"]:
        esm, higher = record["esm"], record["higher_scenario"]
        base_rows, high_rows = weather[(esm, "ssp126")], weather[(esm, higher)]
        if len(base_rows) != 8 or len(high_rows) != 8:
            raise ValueError("weather audit window incomplete")
        delta_k = source_means[(esm, higher)] - source_means[(esm, "ssp126")]
        close(delta_k, record["gmst_difference_k"]); checks += 1
        for feature in result["features"]:
            base = math.fsum(float(x["annual_means"][feature]["area_weighted"]) for x in base_rows) / 8
            high = math.fsum(float(x["annual_means"][feature]["area_weighted"]) for x in high_rows) / 8
            difference = high - base
            close(difference, record["feature_differences"][feature])
            close(difference / delta_k, record["feature_change_per_k"][feature])
            checks += 2
    audit = {"status": "passed", "result_sha256": sha(result_path),
             "weather_parent_sha256": sha(PARENT), "gmst_files": len(result["gmst_sources"]),
             "scenario_ratios": len(result["records"]), "numerical_checks": checks}
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
