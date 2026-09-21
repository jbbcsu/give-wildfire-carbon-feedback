#!/usr/bin/env python3
"""Independent standard-library reconstruction of 2020–2025 NASS support."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import pyarrow.parquet as pq
import shapefile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/nass_terminal_2020_2025_20260916/source"
AUDIT = ROOT / "data/interim/nass_terminal_2020_2025_20260916/support_audit/result.json"
DIRECT = ROOT / "data/raw/us_county/nass_api/irrigation_practice_screen/yield_practice"
HIST = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
TIGER = ROOT / "data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp"
SERIES = {"corn": ("CORN", "GRAIN", "corn_grain"),
          "soybeans": ("SOYBEANS", "ALL UTILIZATION PRACTICES", "soybeans")}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric(text):
    try:
        return float(text.replace(",", ""))
    except (ValueError, TypeError, AttributeError):
        return None


def geoid(row):
    state, county = row.get("state_ansi"), row.get("county_ansi")
    return state + county if (isinstance(state, str) and len(state) == 2 and state.isdigit()
                              and isinstance(county, str) and len(county) == 3 and county.isdigit()) else None


def check(actual, expected, description):
    if actual != expected:
        raise AssertionError(f"{description}: {actual!r} != {expected!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim") or out == ROOT / "data/interim":
        raise ValueError("fresh ignored output required")
    audit = json.loads(AUDIT.read_text())
    snapshot = json.loads((SOURCE / "snapshot_summary.json").read_text())
    check(sha(SOURCE / "snapshot_summary.json"), audit["source_snapshot_sha256"], "snapshot hash")
    check(sha(SOURCE / "MANIFEST.jsonl"), audit["source_manifest_sha256"], "manifest hash")
    check(sha(HIST), audit["direct_weather_panel_sha256"], "historical weather key source")
    check(sha(TIGER.with_suffix(".dbf")), audit["tiger2019_dbf_sha256"], "county reference")
    tiger = {str(row.as_dict()["GEOID"]) for row in shapefile.Reader(str(TIGER)).iterRecords()}
    hist_rows = pq.read_table(HIST, columns=["county_geoid", "outcome_crop"]).to_pylist()
    geo = {crop: {row["county_geoid"] for row in hist_rows if row["outcome_crop"] == outcome}
           for crop, (_, _, outcome) in SERIES.items()}
    check({crop: len(keys) for crop, keys in geo.items()},
          audit["historical_weather_geography_counties"], "weather geography")
    shares = {}
    for vintage in (2017, 2022):
        path = ROOT / f"data/interim/us_county/nass_{vintage}_crop_irrigation_shares.csv"
        check(sha(path), audit["irrigation_share_sha256"][str(vintage)], "share source")
        with path.open(newline="", encoding="utf-8") as handle:
            records = list(csv.DictReader(handle))
        shares[vintage] = {(row["crop"], row["county_geoid"]):
                           float(row["irrigation_share"]) if row["share_eligible"] == "True" else None
                           for row in records}
        check(len(shares[vintage]), len(records), "unique share keys")
    files = {(row["commodity"], row["year"]): ROOT / row["raw_path"]
             for row in snapshot["snapshots"]}
    check(len(files), 12, "source matrix")
    annual = {}
    positive = {}
    checks = 0
    for crop, (commodity, utilization, _) in SERIES.items():
        annual[crop] = {}
        positive[crop] = {}
        for year in range(2020, 2026):
            path = files[(commodity, year)]
            reference = next(x for x in snapshot["snapshots"]
                             if x["commodity"] == commodity and x["year"] == year)
            check(sha(path), reference["raw_sha256"], "raw outcome content")
            rows = json.loads(path.read_text())["data"]
            check(len(rows), reference["preflight_rows"], "preflight row count")
            point = {key: 0 for key in audit["annual"][crop][str(year)]}
            point["api_rows"] = len(rows)
            selected = set()
            keys = set()
            for row in rows:
                check((str(row["year"]), row["commodity_desc"], row["util_practice_desc"],
                       row["prodn_practice_desc"]),
                      (str(year), commodity, utilization, "ALL PRODUCTION PRACTICES"),
                      "locked NASS series")
                county = geoid(row)
                if county is None:
                    continue
                point["ansi_county_rows"] += 1
                check(county not in keys, True, "unique county/year")
                keys.add(county)
                if county not in tiger:
                    continue
                point["tiger2019_matched_rows"] += 1
                value = numeric(row["Value"])
                if value is None:
                    point["suppressed_or_nonnumeric_tiger_counties"] += 1
                    continue
                if not math.isfinite(value):
                    raise ValueError("nonfinite reported yield")
                if value == 0:
                    point["zero_reported_tiger_counties"] += 1
                    continue
                if value < 0:
                    point["negative_reported_tiger_counties"] += 1
                    continue
                point["positive_reported_tiger_counties"] += 1
                selected.add(county)
                if county in geo[crop]:
                    point["positive_in_historical_weather_geography"] += 1
                for vintage in (2017, 2022):
                    share = shares[vintage].get((crop, county))
                    if share is not None:
                        point[f"numeric_{vintage}_irrigation_share"] += 1
                        for cutoff in (10, 20, 30):
                            if share <= cutoff / 100:
                                point[f"selected_{vintage}_le_{cutoff}pct"] += 1
                                if county in geo[crop]:
                                    point[f"selected_{vintage}_le_{cutoff}pct_historical_weather_geography"] += 1
            check(point, audit["annual"][crop][str(year)], f"{crop}/{year} annual support")
            checks += len(point)
            annual[crop][str(year)] = point
            positive[crop][year] = selected
    for crop in SERIES:
        for year in range(2021, 2026):
            paired = positive[crop][year - 1] & positive[crop][year]
            point = {"positive_both_tiger": len(paired)}
            for cutoff in (10, 20, 30):
                point[f"selected_2017_le_{cutoff}pct_historical_weather_geography"] = sum(
                    county in geo[crop] and shares[2017].get((crop, county)) is not None and
                    shares[2017][(crop, county)] <= cutoff / 100 for county in paired)
            check(point, audit["consecutive"][crop][str(year)], "consecutive support")
            checks += len(point)
    for crop in SERIES:
        practice_sets = {}
        for practice in ("irrigated", "non_irrigated"):
            path = DIRECT / f"survey_{crop}_{practice}_yield_all_years.json"
            rows = json.loads(path.read_text())["data"]
            practice_sets[practice] = {(int(row["year"]), county) for row in rows
                                       if 2020 <= int(row["year"]) <= 2025
                                       for county in [geoid(row)]
                                       if county in tiger and numeric(row["Value"]) is not None
                                       and numeric(row["Value"]) > 0}
        paired = practice_sets["irrigated"] & practice_sets["non_irrigated"]
        for year in range(2020, 2026):
            check(sum(y == year for y, _ in paired),
                  audit["direct_practice_paired"][crop][str(year)]["paired_positive_tiger2019_counties"],
                  "direct-practice paired support")
            checks += 1
    result = {"status": "independently_validated_key_support",
              "audit_sha256": sha(AUDIT), "checks_passed": checks,
              "year_crop_coverage": "2020-2025 corn and soybeans",
              "yield_magnitudes_exported": False, "code_sha256": sha(Path(__file__))}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "checks": checks}))


if __name__ == "__main__":
    main()
