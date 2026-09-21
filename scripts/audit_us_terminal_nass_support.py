#!/usr/bin/env python3
"""Key-only 2020–2025 NASS outcome and irrigation-selector support audit."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq
import shapefile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from prepare_nass_api_county_yields import prepare
from audit_nass_irrigation_practice_coverage import prepare_yield

SOURCE = ROOT / "data/interim/nass_terminal_2020_2025_20260916/source"
DIRECT = ROOT / "data/raw/us_county/nass_api/irrigation_practice_screen/yield_practice"
HIST = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
TIGER = ROOT / "data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp"
SHARES = {year: ROOT / f"data/interim/us_county/nass_{year}_crop_irrigation_shares.csv"
          for year in (2017, 2022)}
SERIES = {"corn": ("CORN", "GRAIN", "corn_grain"),
          "soybeans": ("SOYBEANS", "ALL UTILIZATION PRACTICES", "soybeans")}
PRACTICES = ("irrigated", "non_irrigated")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_snapshot():
    summary = json.loads((SOURCE / "snapshot_summary.json").read_text())
    if summary["status"] != "raw_outcomes_acquired_no_values_analyzed" or len(summary["snapshots"]) != 12:
        raise ValueError("terminal acquisition incomplete")
    manifest = [json.loads(line) for line in (SOURCE / "MANIFEST.jsonl").read_text().splitlines()]
    if len(manifest) != 12:
        raise ValueError("terminal manifest incomplete")
    mapped = {}
    for record in summary["snapshots"]:
        key = (record["commodity"], record["year"])
        path = ROOT / record["raw_path"]
        if key in mapped or not path.is_relative_to(SOURCE):
            raise ValueError("duplicate or misplaced terminal source")
        if sha(path) != record["raw_sha256"]:
            raise ValueError("terminal source hash changed")
        match = [item for item in manifest if item["raw_file"] == str(path)]
        if len(match) != 1 or int(match[0]["preflight_count"]) != record["preflight_rows"]:
            raise ValueError("terminal manifest/count mismatch")
        mapped[key] = path
    if set(mapped) != {(commodity, year) for commodity, _, _ in SERIES.values()
                       for year in range(2020, 2026)}:
        raise ValueError("terminal crop-year matrix incomplete")
    return mapped, sha(SOURCE / "snapshot_summary.json"), sha(SOURCE / "MANIFEST.jsonl")


def tiger_keys():
    with shapefile.Reader(str(TIGER)) as source:
        keys = {str(record.as_dict()["GEOID"]) for record in source.iterRecords()}
    if len(keys) < 3000 or not all(len(key) == 5 and key.isdigit() for key in keys):
        raise ValueError("unexpected TIGER county identities")
    return keys


def load_shares():
    output = {}
    hashes = {}
    for year, path in SHARES.items():
        hashes[str(year)] = sha(path)
        lookup = {}
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (row["crop"], row["county_geoid"])
                if key in lookup:
                    raise ValueError("duplicate Census share")
                eligible = row["share_eligible"] == "True"
                value = float(row["irrigation_share"]) if eligible else None
                if eligible and (not math.isfinite(value) or not 0 <= value <= 1):
                    raise ValueError("invalid Census irrigation share")
                lookup[key] = value
        output[year] = lookup
    return output, hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim") or out == ROOT / "data/interim":
        raise ValueError("fresh ignored output required")
    snapshot, summary_hash, manifest_hash = load_snapshot()
    tiger = tiger_keys()
    share, share_hashes = load_shares()
    hist = pq.read_table(HIST, columns=["county_geoid", "outcome_crop"]).to_pylist()
    weather_countries = {crop: set() for crop in SERIES}
    for row in hist:
        for crop, (_, _, outcome) in SERIES.items():
            if row["outcome_crop"] == outcome:
                weather_countries[crop].add(row["county_geoid"])
    if not all(weather_countries.values()):
        raise ValueError("historical weather geography empty")
    outcomes = {}
    annual = {}
    for crop, (commodity, util, _) in SERIES.items():
        paths = [snapshot[(commodity, year)] for year in range(2020, 2026)]
        frame, source_audit = prepare(paths, commodity=commodity, unit="BU / ACRE",
                                      utilization_practice=util,
                                      year_start=2020, year_end=2025)
        frame["tiger_match"] = frame["county_geoid"].isin(tiger)
        frame["positive"] = frame["yield_value"].gt(0).fillna(False).astype(bool)
        frame["zero"] = frame["yield_value"].eq(0).fillna(False).astype(bool)
        frame["negative"] = frame["yield_value"].lt(0).fillna(False).astype(bool)
        for year in (2017, 2022):
            frame[f"share_{year}"] = pd.to_numeric(
                [share[year].get((crop, key)) for key in frame["county_geoid"]],
                errors="coerce")
            for cutoff in (10, 20, 30):
                frame[f"selected_{year}_{cutoff}"] = frame[f"share_{year}"].le(cutoff / 100).fillna(False)
        frame["historic_weather_county"] = frame["county_geoid"].isin(weather_countries[crop])
        annual[crop] = {}
        for year, group in frame.groupby("harvest_year", sort=True):
            verified = group["tiger_match"] & group["positive"]
            record = {
                "api_rows": int(source_audit["raw_records_by_year"][str(year)]),
                "ansi_county_rows": int(len(group)),
                "tiger2019_matched_rows": int(group["tiger_match"].sum()),
                "positive_reported_tiger_counties": int(verified.sum()),
                "zero_reported_tiger_counties": int((group["tiger_match"] & group["zero"]).sum()),
                "negative_reported_tiger_counties": int((group["tiger_match"] & group["negative"]).sum()),
                "suppressed_or_nonnumeric_tiger_counties": int((group["tiger_match"] & ~group["yield_reported"]).sum()),
                "positive_in_historical_weather_geography": int((verified & group["historic_weather_county"]).sum()),
            }
            for vintage in (2017, 2022):
                record[f"numeric_{vintage}_irrigation_share"] = int((verified & group[f"share_{vintage}"].notna()).sum())
                for cutoff in (10, 20, 30):
                    selected = verified & group[f"selected_{vintage}_{cutoff}"]
                    record[f"selected_{vintage}_le_{cutoff}pct"] = int(selected.sum())
                    record[f"selected_{vintage}_le_{cutoff}pct_historical_weather_geography"] = int(
                        (selected & group["historic_weather_county"]).sum())
            annual[crop][str(year)] = record
        outcomes[crop] = frame
    consecutive = {}
    for crop, frame in outcomes.items():
        consecutive[crop] = {}
        by_year = {year: group.set_index("county_geoid") for year, group in frame.groupby("harvest_year")}
        for year in range(2021, 2026):
            left, right = by_year[year - 1], by_year[year]
            common = set(left.index) & set(right.index)
            counts = {"positive_both_tiger": 0,
                      "selected_2017_le_10pct_historical_weather_geography": 0,
                      "selected_2017_le_20pct_historical_weather_geography": 0,
                      "selected_2017_le_30pct_historical_weather_geography": 0}
            for key in common:
                a, b = left.loc[key], right.loc[key]
                if not (a["tiger_match"] and b["tiger_match"] and a["positive"] and b["positive"]):
                    continue
                counts["positive_both_tiger"] += 1
                if key in weather_countries[crop]:
                    for cutoff in (10, 20, 30):
                        if a[f"selected_2017_{cutoff}"] and b[f"selected_2017_{cutoff}"]:
                            counts[f"selected_2017_le_{cutoff}pct_historical_weather_geography"] += 1
            consecutive[crop][str(year)] = counts
    direct = {}
    for crop in SERIES:
        sets = {}
        for practice in PRACTICES:
            path = DIRECT / f"survey_{crop}_{practice}_yield_all_years.json"
            rows = prepare_yield(path)
            rows = rows.loc[rows["year"].between(2020, 2025)]
            sets[practice] = {(int(row.year), str(row.county_geoid))
                              for row in rows.itertuples() if row.yield_eligible and row.county_geoid in tiger}
        direct[crop] = {str(year): {"paired_positive_tiger2019_counties":
                           sum(y == year for y, _ in sets["irrigated"] & sets["non_irrigated"])}
                        for year in range(2020, 2026)}
    result = {"status": "key_and_availability_support_only",
              "source_snapshot_sha256": summary_hash, "source_manifest_sha256": manifest_hash,
              "direct_weather_panel_sha256": sha(HIST),
              "tiger2019_dbf_sha256": sha(TIGER.with_suffix(".dbf")),
              "irrigation_share_sha256": share_hashes,
              "historical_weather_geography_counties": {crop: len(rows) for crop, rows in weather_countries.items()},
              "annual": annual, "consecutive": consecutive,
              "direct_practice_paired": direct,
              "yield_magnitudes_reported": False, "response_estimated": False,
              "weather_2020_2025_acquired": False, "scc_calculated": False,
              "code_sha256": sha(Path(__file__))}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"],
                      "corn_2025_primary_weather_counties": annual["corn"]["2025"]["selected_2017_le_10pct_historical_weather_geography"],
                      "soy_2025_primary_weather_counties": annual["soybeans"]["2025"]["selected_2017_le_10pct_historical_weather_geography"]}))


if __name__ == "__main__":
    main()
