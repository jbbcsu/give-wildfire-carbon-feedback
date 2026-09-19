#!/usr/bin/env python3
"""Normalize audited crop-weather scenario differences by matching GMST."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data/interim"
PARENT = INTERIM / "three_esm_maize_area_weather_20260918/result.json"
PARENT_SHA = "027bd174738cb8de16c218b4674c33e7360c88f50bf719ef9a901769976b44f1"
PROTOCOL = ROOT / "GLOBAL_MAIZE_GMST_NORMALIZED_WEATHER_PROTOCOL_20260918.md"
ESMS = {
    "ukesm1-0-ll": ("ukesm1-0-ll", "r1i1p1f2"),
    "ipsl-cm6a-lr": ("ipsl-cm6a-lr", "r1i1p1f1"),
    "mpi-esm1-2-hr": ("mpi-esm1-2-hr", "r1i1p1f1"),
}
SCENARIOS = ("ssp126", "ssp370", "ssp585")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gmst(esm, member, scenario):
    path = INTERIM / "isimip3b" / f"{esm}_{member}_{scenario}_gmst_2091_2100.parquet"
    frame = pd.read_parquet(path)
    def leap(year):
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    expected_days = {year: 366 if leap(year) else 365 for year in range(2091, 2101)}
    if (len(frame) != 10 or frame.year.tolist() != list(range(2091, 2101))
            or frame.year.duplicated().any() or set(frame.scenario) != {scenario}
            or set(frame.member_id) != {member}
            or not frame.gmst_value_k.map(math.isfinite).all()
            or any(int(row.daily_count) != expected_days[int(row.year)] for row in frame.itertuples())):
        raise ValueError("GMST identity, chronology, or finite-value gate failed")
    selected = frame.loc[frame.year.between(2092, 2099), "gmst_value_k"]
    if len(selected) != 8:
        raise ValueError("eight-year GMST window incomplete")
    return path, float(math.fsum(selected) / 8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(INTERIM):
        parser.error("fresh ignored output required")
    if sha(PARENT) != PARENT_SHA:
        raise ValueError("audited weather parent changed")
    parent = json.loads(PARENT.read_text())
    features = tuple(parent["annual_panels"][0]["annual_means"])
    weather = {}
    for row in parent["annual_panels"]:
        key = (row["esm"], row["scenario"])
        weather.setdefault(key, []).append((int(row["year"]),
            {name: float(row["annual_means"][name]["area_weighted"]) for name in features}))
    gmst_means, gmst_sources = {}, []
    for label, (source_esm, member) in ESMS.items():
        for scenario in SCENARIOS:
            path, value = gmst(source_esm, member, scenario)
            gmst_means[(label, scenario)] = value
            gmst_sources.append({"esm": label, "scenario": scenario, "member": member,
                                 "path": str(path.relative_to(ROOT)), "sha256": sha(path),
                                 "mean_2092_2099_k": value})
    records = []
    for esm in ESMS:
        base_rows = sorted(weather[(esm, "ssp126")])
        if [x[0] for x in base_rows] != list(range(2092, 2100)):
            raise ValueError("base weather years incomplete")
        base = {f: math.fsum(x[1][f] for x in base_rows) / 8 for f in features}
        for scenario in ("ssp370", "ssp585"):
            high_rows = sorted(weather[(esm, scenario)])
            if [x[0] for x in high_rows] != list(range(2092, 2100)):
                raise ValueError("high weather years incomplete")
            high = {f: math.fsum(x[1][f] for x in high_rows) / 8 for f in features}
            delta_k = gmst_means[(esm, scenario)] - gmst_means[(esm, "ssp126")]
            if not math.isfinite(delta_k) or delta_k <= 0:
                raise ValueError("nonpositive GMST scenario difference")
            records.append({"esm": esm, "higher_scenario": scenario,
                "reference_scenario": "ssp126", "gmst_difference_k": delta_k,
                "feature_differences": {f: high[f] - base[f] for f in features},
                "feature_change_per_k": {f: (high[f] - base[f]) / delta_k for f in features}})
    output = {"status": "descriptive_scenario_endpoint_normalization_not_emulator_or_scc",
              "parent_weather_sha256": PARENT_SHA, "protocol_sha256": sha(PROTOCOL),
              "gmst_sources": gmst_sources, "features": list(features), "records": records,
              "one_realization_per_esm": True, "uncertainty_interval_estimated": False,
              "yield_damage_scc_estimated": False}
    out.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
