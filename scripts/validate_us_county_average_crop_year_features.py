#!/usr/bin/env python3
"""Independent source-to-feature spot reconstruction; reads no crop outcomes."""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/nclimgrid_county_averages_full_20260916"
FEATURES = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
CROSSWALK = ROOT / "data/raw/us_county/nclimgrid_county_averages/us-state-codes_ncei-to-fips.csv"
SAMPLE_GEOIDS = ("19153", "31055", "13121", "48201")
SAMPLE_CROPS = ("corn_grain", "soybeans")
SAMPLE_YEARS = (1981, 2000, 2024, 2025)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def source_codes() -> dict[str, str]:
    with CROSSWALK.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    inverse = {row["FIPS_code"].zfill(2): row["NCEI_code"].zfill(2) for row in rows}
    if len(inverse) != len(rows):
        raise ValueError("county source-code mapping is not one-to-one")
    return {fips: inverse[fips[:2]] + fips[2:] for fips in SAMPLE_GEOIDS}


def read_selected_weather(year: int, selected: dict[str, str]) -> dict[str, dict[str, dict[date, float]]]:
    wanted = {source: fips for fips, source in selected.items()}
    result = {fips: {variable: {} for variable in ("PRCP", "TAVG", "TMAX")}
              for fips in selected}
    for month in range(1, 13):
        half = 1 if month <= 6 else 2
        receipt = json.loads((SOURCE / f"{year}_h{half}" / "result.json").read_text())
        member = receipt["months"][f"{year}{month:02d}"]
        days = calendar.monthrange(year, month)[1]
        for variable in ("PRCP", "TAVG", "TMAX"):
            spec = member["sources"][variable]
            path = ROOT / spec["path"]
            if sha(path) != spec["sha256"]:
                raise ValueError("independent raw-source hash check failed")
            found = set()
            with path.open(newline="", encoding="utf-8") as stream:
                for cells in csv.reader(stream):
                    if len(cells) != 37:
                        raise ValueError("independent NOAA CSV width changed")
                    code = cells[1]
                    if code not in wanted:
                        continue
                    if code in found or cells[0] != "cty" or cells[3:6] != [str(year), f"{month:02d}", variable]:
                        raise ValueError("independent NOAA selected-row identity changed")
                    found.add(code)
                    fips = wanted[code]
                    for day in range(1, days + 1):
                        value = float(cells[5 + day])
                        if not np.isfinite(value):
                            raise ValueError("independent NOAA selected value nonfinite")
                        result[fips][variable][date(year, month, day)] = value
            if found != set(wanted):
                raise ValueError("independent NOAA selected counties incomplete")
    return result


def assert_close(actual: float, expected: float, label: str, tolerance: float = 0.025) -> None:
    if not np.isfinite(actual) or abs(actual - expected) > tolerance:
        raise ValueError(f"independent feature mismatch: {label}: {actual} != {expected}")


def check_row(row, weather: dict[str, dict[date, float]]) -> int:
    first, last = date.fromisoformat(row.season_start), date.fromisoformat(row.season_end)
    days = [first + timedelta(days=index) for index in range((last - first).days + 1)]
    if len(days) != int(row.season_days):
        raise ValueError("feature season chronology changed")
    rain = [weather["PRCP"][day] for day in days]
    tavg = [weather["TAVG"][day] for day in days]
    tmax = [weather["TMAX"][day] for day in days]
    total = sum(rain)
    assert_close(row.precip_mm, total, "seasonal precipitation")
    assert_close(row.wet_days_ge_1mm, sum(value >= 1 for value in rain), "wet days", 1e-8)
    assert_close(row.rx5day_mm, max(sum(rain[index:index + 5]) for index in range(len(rain) - 4)), "Rx5")
    running = maximum = 0
    for value in rain:
        running = running + 1 if value < 1 else 0
        maximum = max(maximum, running)
    assert_close(row.cdd_max_days, maximum, "longest dry spell", 1e-8)
    assert_close(row.tmean_c, sum(tavg) / len(tavg), "season TAVG")
    for threshold in (29, 30):
        assert_close(getattr(row, f"tmax_exceedance_{threshold}c_c_days"),
                     sum(max(value - threshold, 0) for value in tmax), "season heat")
        assert_close(getattr(row, f"tmax_days_gt_{threshold}c"),
                     sum(value > threshold for value in tmax), "hot-day count", 1e-8)
    bounds = [int(np.floor(frac * len(days))) for frac in (0, 0.3, 0.7, 1)]
    shares = []
    for stage in (1, 2, 3):
        left, right = bounds[stage - 1], bounds[stage]
        amount = sum(rain[left:right])
        share = amount / total if total > 0 else 0.0
        shares.append(share)
        assert_close(getattr(row, f"stage{stage}_precip_mm"), amount, "stage rainfall")
        assert_close(getattr(row, f"stage{stage}_precip_share"), share, "stage rainfall share")
        assert_close(getattr(row, f"stage{stage}_tmean_c"),
                     sum(tavg[left:right]) / (right - left), "stage TAVG")
    assert_close(row.precipitation_concentration_hhi, sum(value * value for value in shares), "rain HHI")
    return 19


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored validation directory required")
    selected = source_codes()
    checks = 0
    years = []
    for year in SAMPLE_YEARS:
        partition = FEATURES / str(year)
        receipt = json.loads((partition / "result.json").read_text())
        output = partition / "features.parquet"
        if (receipt["status"] != "county_average_crop_year_features_built" or
            receipt["year"] != year or sha(output) != receipt["features_sha256"]):
            raise ValueError("feature partition identity/hash differs")
        frame = pd.read_parquet(output)
        if frame.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).any():
            raise ValueError("feature partition duplicates key")
        raw = read_selected_weather(year, selected)
        subset = frame.loc[frame.county_geoid.isin(SAMPLE_GEOIDS) &
                           frame.outcome_crop.isin(SAMPLE_CROPS)]
        if len(subset) != len(SAMPLE_GEOIDS) * len(SAMPLE_CROPS):
            raise ValueError("prespecified county/crop reconstruction support missing")
        for row in subset.itertuples(index=False):
            checks += check_row(row, raw[row.county_geoid])
        years.append({"year": year, "source_counties": len(raw), "reconstructed_rows": len(subset),
                      "partition_sha256": sha(output)})
    result = {"status": "independent_county_average_crop_year_features_validated",
              "sample_years": years, "sample_geoids": list(SAMPLE_GEOIDS),
              "sample_crops": list(SAMPLE_CROPS), "numeric_checks": checks,
              "yield_outcomes_read": False, "response_or_scc_estimated": False,
              "code_sha256": sha(Path(__file__))}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "checks": checks}))


if __name__ == "__main__":
    main()
