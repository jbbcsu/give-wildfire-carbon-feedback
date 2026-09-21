#!/usr/bin/env python3
"""Assemble fixed-screen U.S. NASS outcomes with validated NOAA features; no fit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_us_terminal_nass_support import load_snapshot, tiger_keys
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from prepare_nass_api_county_yields import prepare

HIST = ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet"
GEO = ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019_geography_gate.csv"
SHARES = ROOT / "data/interim/us_county/nass_2017_crop_irrigation_shares.csv"
FEATURES = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_feature_validation_20260916/result.json"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md"
KEY = ["outcome_crop", "county_geoid", "harvest_year"]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def fixed_selector() -> pd.DataFrame:
    shares = pd.read_csv(SHARES, dtype={"county_geoid": str})
    if shares.duplicated(["crop", "county_geoid"]).any() or set(shares.census_year) != {2017}:
        raise ValueError("fixed 2017 Census irrigation selector invalid")
    shares["outcome_crop"] = shares["crop"].map({"corn": "corn_grain", "soybeans": "soybeans"})
    shares = shares.loc[shares.outcome_crop.notna()].copy()
    shares["selected_10pct"] = (shares.share_eligible.astype(str).str.lower().eq("true") &
                                 shares.irrigation_share.notna() &
                                 shares.irrigation_share.between(0, 0.1))
    return shares[["outcome_crop", "county_geoid", "irrigation_share", "selected_10pct"]]


def geo_selector() -> pd.DataFrame:
    geo = pd.read_csv(GEO, dtype={"county_geoid": str})
    if geo.county_geoid.duplicated().any():
        raise ValueError("historical 2019 TIGER geography gate duplicates county")
    geo["selected_geography"] = geo.feature_construction_eligible.astype(str).str.lower().eq("true")
    return geo[["county_geoid", "selected_geography"]]


def historic_outcomes() -> pd.DataFrame:
    hist = pd.read_parquet(HIST)
    if (hist.duplicated(KEY).any() or set(hist.irrigation_practice) != {"all_practices"} or
        set(hist.irrigation_share_vintage) != {2017} or not hist.harvest_year.between(1981, 2019).all()):
        raise ValueError("historical all-practice NASS panel identity changed")
    checked = hist[["outcome_crop", "county_geoid", "irrigation_share",
                    "rainfed_dominant_10pct"]].merge(
                        fixed_selector(), on=["outcome_crop", "county_geoid"],
                        how="left", validate="many_to_one", suffixes=("_historical", "_fixed"))
    valid = checked.irrigation_share_historical.notna() & checked.irrigation_share_fixed.notna()
    if (valid.any() and
        (checked.loc[valid, "irrigation_share_historical"] -
         checked.loc[valid, "irrigation_share_fixed"]).abs().max() > 1e-12):
        raise ValueError("historical outcome irrigation share differs from fixed 2017 source")
    fixed_selection = checked.selected_10pct.astype("boolean").fillna(False).astype(bool)
    if not checked.rainfed_dominant_10pct.astype(bool).eq(fixed_selection).all():
        raise ValueError("historical NASS 10-percent screen differs from fixed Census selector")
    return hist[KEY + ["yield_bu_acre", "outcome_value_eligible"]].assign(period="historical")


def terminal_outcomes() -> tuple[pd.DataFrame, dict]:
    snapshot, summary_hash, manifest_hash = load_snapshot()
    tiger = tiger_keys()
    frames = []
    for crop, commodity, utilization in (("corn_grain", "CORN", "GRAIN"),
                                          ("soybeans", "SOYBEANS", "ALL UTILIZATION PRACTICES")):
        paths = [snapshot[(commodity, year)] for year in range(2020, 2026)]
        frame, audit = prepare(paths, commodity=commodity, unit="BU / ACRE",
                               utilization_practice=utilization,
                               year_start=2020, year_end=2025)
        if frame.duplicated(["county_geoid", "harvest_year"]).any():
            raise ValueError("terminal NASS county/year key duplicated")
        frame = frame.loc[frame.county_geoid.isin(tiger)].copy()
        frame["outcome_crop"] = crop
        frame["yield_bu_acre"] = frame.yield_value
        frame["outcome_value_eligible"] = frame.yield_reported & frame.yield_value.gt(0)
        frames.append(frame[KEY + ["yield_bu_acre", "outcome_value_eligible"]].assign(period="terminal"))
    terminal = pd.concat(frames, ignore_index=True)
    if terminal.duplicated(KEY).any():
        raise ValueError("terminal corn/soy NASS keys duplicated")
    return terminal, {"snapshot_summary_sha256": summary_hash,
                      "snapshot_manifest_sha256": manifest_hash}


def feature_partitions() -> tuple[pd.DataFrame, str]:
    summary_path = FEATURES / "feature_summary.json"
    summary = json.loads(summary_path.read_text())
    validation = json.loads(VALIDATION.read_text())
    if (summary["status"] != "complete" or summary["completed_years"] != 45 or
        validation["status"] != "independent_county_average_crop_year_features_validated" or
        validation["numeric_checks"] != 4 * 4 * 2 * 19):
        raise ValueError("complete/independently checked NOAA features unavailable")
    by_year = {int(item["year"]): item for item in summary["years"]}
    if set(by_year) != set(range(1981, 2026)):
        raise ValueError("NOAA feature year matrix incomplete")
    frames = []
    for year in range(1981, 2026):
        path = FEATURES / str(year) / "features.parquet"
        if sha(path) != by_year[year]["features_sha256"]:
            raise ValueError("NOAA feature partition changed")
        frame = pd.read_parquet(path)
        if not frame.harvest_year.eq(year).all() or frame.duplicated(KEY).any():
            raise ValueError("NOAA feature partition year/keys changed")
        frames.append(frame)
    features = pd.concat(frames, ignore_index=True)
    if features.duplicated(KEY).any():
        raise ValueError("NOAA feature union duplicates crop/county/year")
    return features, sha(summary_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored response-panel output required")
    hist = historic_outcomes()
    terminal, terminal_identity = terminal_outcomes()
    outcomes = pd.concat([hist, terminal], ignore_index=True)
    if outcomes.duplicated(KEY).any():
        raise ValueError("historical/terminal NASS overlap or duplicate")
    raw_rows = len(outcomes)
    outcomes = outcomes.loc[outcomes.outcome_value_eligible & outcomes.yield_bu_acre.gt(0)].copy()
    positive_rows = len(outcomes)
    outcomes = outcomes.merge(fixed_selector(), on=["outcome_crop", "county_geoid"],
                              how="left", validate="many_to_one")
    numeric_selector_rows = int(outcomes.irrigation_share.notna().sum())
    outcomes = outcomes.loc[
        outcomes.selected_10pct.astype("boolean").fillna(False).astype(bool)
    ].copy()
    fixed_share_rows = len(outcomes)
    outcomes = outcomes.merge(geo_selector(), on="county_geoid", how="left", validate="many_to_one")
    outcomes = outcomes.loc[
        outcomes.selected_geography.astype("boolean").fillna(False).astype(bool)
    ].copy()
    geography_rows = len(outcomes)
    features, feature_hash = feature_partitions()
    panel = outcomes.merge(features, on=KEY, how="inner", validate="one_to_one")
    if panel.duplicated(KEY).any() or panel.empty:
        raise ValueError("screened NASS/NOAA panel keys invalid")
    final_rows = len(panel)
    panel = panel.drop(columns=["outcome_value_eligible", "selected_10pct", "selected_geography"])
    out.mkdir(parents=True)
    panel_path = out / "panel.parquet"
    panel.to_parquet(panel_path, index=False)
    annual = {f"{crop}:{year}": int(count) for (crop, year), count in
              panel.groupby(["outcome_crop", "harvest_year"]).size().items()}
    result = {"status": "county_average_nass_panel_assembled_no_response",
              "rows_raw_historical_terminal": raw_rows,
              "rows_positive_reported": positive_rows,
              "rows_with_numeric_2017_share": numeric_selector_rows,
              "rows_selected_2017_le_10pct": fixed_share_rows,
              "rows_after_fixed_geography": geography_rows,
              "rows_with_weather": final_rows,
              "annual_crop_rows": annual,
              "historical_rows_with_weather": int(panel.period.eq("historical").sum()),
              "terminal_rows_with_weather": int(panel.period.eq("terminal").sum()),
              "panel_sha256": sha(panel_path),
              "feature_summary_sha256": feature_hash,
              "historical_panel_sha256": sha(HIST), "geography_gate_sha256": sha(GEO),
              "census_share_sha256": sha(SHARES), "validation_sha256": sha(VALIDATION),
              "preanalysis_protocol_sha256": sha(PROTOCOL), **terminal_identity,
              "code_sha256": sha(Path(__file__)),
              "response_or_scc_estimated": False}
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "rows_with_weather": final_rows,
                      "historical_rows": result["historical_rows_with_weather"],
                      "terminal_rows": result["terminal_rows_with_weather"]}))


if __name__ == "__main__":
    main()
