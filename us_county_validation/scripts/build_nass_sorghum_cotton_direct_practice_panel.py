#!/usr/bin/env python3
"""Build exact paired sorghum/cotton practice support from acquired NASS JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRACTICE_MAP = {"IRRIGATED": "irrigated", "NON-IRRIGATED": "non_irrigated"}
PAIR_KEYS = ["crop", "harvest_year", "county_geoid"]


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_value(value: object) -> float:
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return float("nan")
    number = float(text)
    return number if np.isfinite(number) and number > 0 else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    acquisition = json.loads(args.acquisition.read_text(encoding="utf-8"))
    require(acquisition["status"] == "acquired_exact_nass_records_no_modeling", "acquisition status differs")
    require(acquisition["record_count"] == 152, "acquisition matrix is incomplete")
    rows, file_audits = [], []
    for record in acquisition["records"]:
        path = ROOT / record["raw_path"]
        require(path.is_file(), f"raw file missing: {path}")
        require(digest(path, "sha512") == record["sha512"], "raw hash differs")
        payload = json.loads(path.read_text(encoding="utf-8"))
        data = payload.get("data")
        require(isinstance(data, list) and len(data) == record["count"], "raw row count differs")
        numeric, coded = 0, 0
        for raw in data:
            state = str(raw.get("state_ansi", "")).strip()
            county = str(raw.get("county_ansi", "")).strip()
            geography_ok = bool(re.fullmatch(r"\d{2}", state) and re.fullmatch(r"\d{3}", county))
            value = parse_value(raw.get("Value", ""))
            coded += int(geography_ok)
            numeric += int(np.isfinite(value))
            rows.append({
                "crop": record["crop"], "harvest_year": int(record["year"]),
                "county_geoid": state + county if geography_ok else None,
                "state_ansi": state if geography_ok else None,
                "state_alpha": str(raw.get("state_alpha", "")).strip(),
                "county_name": str(raw.get("county_name", "")).strip(),
                "practice": PRACTICE_MAP[record["practice"]],
                "yield_value": value, "yield_unit": str(raw.get("unit_desc", "")).strip(),
                "value_raw": str(raw.get("Value", "")).strip(),
                "cv_percent_raw": str(raw.get("CV (%)", "")).strip(),
                "geography_eligible": geography_ok,
                "numeric_positive_yield": bool(np.isfinite(value)),
            })
        file_audits.append({
            "crop": record["crop"], "practice": record["practice"], "year": record["year"],
            "raw_rows": len(data), "coded_geography_rows": coded, "numeric_positive_rows": numeric,
        })
    frame = pd.DataFrame(rows)
    eligible = frame.loc[frame.geography_eligible & frame.numeric_positive_yield].copy()
    duplicate = eligible.duplicated(PAIR_KEYS + ["practice"], keep=False)
    require(not duplicate.any(), f"duplicate eligible crop/county/year/practice keys: {eligible.loc[duplicate, PAIR_KEYS + ['practice']].head().to_dict('records')}")
    counts = eligible.groupby(PAIR_KEYS, observed=True).practice.nunique()
    paired_keys = counts.loc[counts.eq(2)].reset_index()[PAIR_KEYS]
    paired = eligible.merge(paired_keys, on=PAIR_KEYS, how="inner", validate="many_to_one")
    require(len(paired) == 2 * len(paired_keys), "paired panel does not have two practices per key")
    paired["outcome_source_id"] = "USDA_NASS_Quick_Stats_SURVEY_exact_direct_practice"
    paired["calendar_available"] = False
    paired["weather_joined"] = False
    paired["response_estimation_authorized"] = False
    paired["scc_authorized"] = False
    output_columns = PAIR_KEYS + [
        "state_ansi", "state_alpha", "county_name", "practice", "yield_value", "yield_unit",
        "value_raw", "cv_percent_raw", "outcome_source_id", "calendar_available",
        "weather_joined", "response_estimation_authorized", "scc_authorized",
    ]
    output = paired[output_columns].sort_values(PAIR_KEYS + ["practice"]).reset_index(drop=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    crop_summaries = []
    for crop, group in frame.groupby("crop", sort=True):
        out = output.loc[output.crop.eq(crop)]
        annual = (
            out.drop_duplicates(PAIR_KEYS).groupby("harvest_year").size()
            .reindex(range(1981, 2019), fill_value=0)
        )
        crop_summaries.append({
            "crop": crop, "raw_rows": len(group),
            "coded_geography_rows": int(group.geography_eligible.sum()),
            "numeric_positive_rows": int(group.numeric_positive_yield.sum()),
            "eligible_rows": int((group.geography_eligible & group.numeric_positive_yield).sum()),
            "paired_county_years": len(out) // 2, "long_practice_rows": len(out),
            "counties": int(out.county_geoid.nunique()), "states": int(out.state_ansi.nunique()),
            "years_with_pairs": int((annual > 0).sum()),
            "first_pair_year": int(annual[annual > 0].index.min()),
            "last_pair_year": int(annual[annual > 0].index.max()),
            "minimum_positive_annual_pairs": int(annual[annual > 0].min()),
            "maximum_annual_pairs": int(annual.max()),
            "annual_paired_county_years": [{"year": int(year), "pairs": int(value)} for year, value in annual.items()],
        })
    receipt = {
        "schema": "nass_sorghum_cotton_direct_practice_panel/v1",
        "created_at_utc": datetime.now(UTC).isoformat(), "status": "paired_outcome_support_built_no_weather_or_model",
        "sources": {"acquisition": {"path": str(args.acquisition), "sha256": digest(args.acquisition)}},
        "file_audits": file_audits, "crop_summaries": crop_summaries,
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size, "rows": len(output)},
        "claim_gates": {"calendar_available": False, "weather_joined": False, "causal_or_irrigation_treatment_authorized": False, "response_damage_or_scc_authorized": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "crop_summaries": crop_summaries}, indent=2))


if __name__ == "__main__":
    main()
