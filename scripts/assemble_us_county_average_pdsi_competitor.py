#!/usr/bin/env python3
"""Join pinned NOAA PDSI to the validated U.S. panel without fitting effects."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from download_nclimdiv_county_pdsi import BULK_NAME, DEFAULT_PROVENANCE, load_pins, validate_bulk_schema, validate_local
from extract_nclimdiv_county_pdsi import extract_rows
from build_county_crop_calendar_drought_features import window_metrics

PRIMARY_PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
HISTORICAL_PDSI = ROOT / "data/interim/us_county/nclimdiv_pdsi_nass_national_all_practice_calendar_features_1981_2019.parquet"
RAW = ROOT / "data/raw/us_county/nclimdiv_pdsicy" / BULK_NAME
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_PDSI_COMPETING_SENSITIVITY_20260916.md"
KEY = ["county_geoid", "outcome_crop", "harvest_year"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def historical_features() -> pd.DataFrame:
    columns = ["county_geoid", "calendar_crop", "harvest_year", "index_day_weighted_mean",
               "index_monthly_minimum", "drought_family", "index_name", "index_source_id",
               "index_calibration_start_year", "index_calibration_end_year", "irrigation_in_index"]
    frame = pd.read_parquet(HISTORICAL_PDSI, columns=columns,
                            filters=[("calendar_role", "==", "fixed_primary"),
                                     ("window_id", "==", "season")])
    if (frame.empty or frame.duplicated(["county_geoid", "calendar_crop", "harvest_year"]).any() or
        set(frame.drought_family) != {"pdsi"} or
        set(frame.index_source_id) != {"noaa_nclimdiv_county_pdsi_v1_0_0_20260806"} or
        set(frame.index_calibration_start_year) != {1931} or
        set(frame.index_calibration_end_year) != {1990} or
        frame.irrigation_in_index.astype(bool).any()):
        raise ValueError("historical PDSI feature identity or calibration differs")
    return frame.rename(columns={"calendar_crop": "outcome_crop",
                                 "index_day_weighted_mean": "pdsi_season_mean",
                                 "index_monthly_minimum": "pdsi_season_min"})[
        KEY + ["pdsi_season_mean", "pdsi_season_min"]]


def source_months(counties: list[str]) -> tuple[dict[str, dict[tuple[int, int], float]], dict]:
    _, pins = load_pins(DEFAULT_PROVENANCE)
    matches = [item for item in pins if item["name"] == BULK_NAME]
    if len(matches) != 1:
        raise ValueError("pinned NOAA PDSI source missing or ambiguous")
    pin = matches[0]
    validate_local(RAW, pin)
    validate_bulk_schema(RAW, pin["validation"])
    monthly = extract_rows(RAW, 2019, 2025, counties)
    if (monthly.duplicated(["county_geoid", "year", "month"]).any() or
        set(monthly.index_source_id) != {"noaa_nclimdiv_county_pdsi_v1_0_0_20260806"} or
        set(monthly.index_calibration_start_year) != {1931} or
        set(monthly.index_calibration_end_year) != {1990}):
        raise ValueError("recent NOAA PDSI source keys/calibration differ")
    lookup = {str(county): {(int(row.year), int(row.month)): float(row.index_value)
                             for row in group.itertuples(index=False)}
              for county, group in monthly.groupby("county_geoid")}
    if set(lookup) != set(counties) or any(len(values) != 84 for values in lookup.values()):
        raise ValueError("2019–2025 selected NOAA PDSI monthly matrix incomplete")
    return lookup, {"source_bytes": RAW.stat().st_size, "source_sha256": sha(RAW),
                    "source_provenance_sha256": sha(DEFAULT_PROVENANCE),
                    "monthly_rows": len(monthly), "counties": len(lookup),
                    "calibration_years": [1931, 1990]}


def calculate_season(row, values: dict[tuple[int, int], float]) -> tuple[float, float]:
    metrics = window_metrics(values, date.fromisoformat(row.season_start),
                             date.fromisoformat(row.season_end), -2.0, -3.0)
    if metrics["monthly_index_days_covered"] != int(row.season_days):
        raise ValueError("PDSI seasonal day coverage differs from NOAA crop-year calendar")
    return float(metrics["index_day_weighted_mean"]), float(metrics["index_monthly_minimum"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored PDSI panel output required")
    panel = pd.read_parquet(PRIMARY_PANEL)
    if panel.duplicated(KEY).any() or len(panel) != 34288:
        raise ValueError("validated main NASS/NOAA panel support changed")
    historical = panel.loc[panel.period.eq("historical")].copy()
    recent = panel.loc[panel.period.eq("terminal")].copy()
    hist_pdsi = historical_features()
    historical = historical.merge(hist_pdsi, on=KEY, how="left", validate="one_to_one", indicator=True)
    if len(historical) != 30213 or not historical._merge.eq("both").all():
        raise ValueError("PDSI historical features lack exact primary panel support")
    historical = historical.drop(columns="_merge")
    selected_counties = sorted(set(recent.county_geoid.astype(str)))
    monthly, source_audit = source_months(selected_counties)
    # Historical 2019 parity uses the old independently created feature table
    # and exact new NOAA calendar dates; no terminal yield is used.
    anchors = historical.loc[historical.harvest_year.eq(2019) &
                             historical.county_geoid.isin(selected_counties)]
    if len(anchors) < 100:
        raise ValueError("too few fixed historical source-parity anchors")
    max_parity_error = 0.0
    for row in anchors.itertuples(index=False):
        mean, minimum = calculate_season(row, monthly[row.county_geoid])
        max_parity_error = max(max_parity_error, abs(mean - row.pdsi_season_mean),
                               abs(minimum - row.pdsi_season_min))
    if max_parity_error > 1e-10:
        raise ValueError("2019 pinned raw PDSI does not reproduce historical seasonal features")
    recent_values = [calculate_season(row, monthly[row.county_geoid])
                     for row in recent.itertuples(index=False)]
    recent["pdsi_season_mean"] = [value[0] for value in recent_values]
    recent["pdsi_season_min"] = [value[1] for value in recent_values]
    combined = pd.concat([historical, recent], ignore_index=True)
    if (len(combined) != len(panel) or combined.duplicated(KEY).any() or
        not np.isfinite(combined[["pdsi_season_mean", "pdsi_season_min"]].to_numpy(dtype=float)).all()):
        raise ValueError("exact-support PDSI comparison panel incomplete")
    out.mkdir(parents=True)
    output = out / "panel_pdsi.parquet"
    combined.to_parquet(output, index=False)
    result = {"status": "exact_support_us_pdsi_competitor_panel_built",
              "main_panel_sha256": sha(PRIMARY_PANEL),
              "historical_pdsi_features_sha256": sha(HISTORICAL_PDSI),
              "source": source_audit, "historical_2019_parity_rows": len(anchors),
              "historical_2019_max_abs_parity_error": max_parity_error,
              "historical_rows": len(historical), "terminal_rows": len(recent),
              "total_rows": len(combined), "panel_sha256": sha(output),
              "protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
              "response_estimated": False, "climate_attribution_or_scc": False}
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "rows": len(combined),
                      "2019_parity_rows": len(anchors),
                      "2019_max_error": max_parity_error}))


if __name__ == "__main__":
    main()
