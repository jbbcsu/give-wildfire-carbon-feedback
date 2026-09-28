#!/usr/bin/env python3
"""Rebuild and validate paired sorghum/cotton NASS support from raw JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PAIR_KEYS = ["crop", "harvest_year", "county_geoid"]
PRACTICES = {"IRRIGATED": "irrigated", "NON-IRRIGATED": "non_irrigated"}


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: object) -> float:
    text = str(value).strip().replace(",", "")
    try:
        parsed = float(text)
    except ValueError:
        return float("nan")
    return parsed if re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text) and np.isfinite(parsed) and parsed > 0 else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--secrets", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    acquisition = json.loads(args.acquisition.read_text(encoding="utf-8"))
    receipt = json.loads(args.panel_receipt.read_text(encoding="utf-8"))
    require(digest(args.panel) == receipt["output"]["sha256"], "panel hash differs")
    secret_values = []
    for line in args.secrets.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            value = line.split("=", 1)[1].strip().strip("'\"")
            if value:
                secret_values.append(value.encode())
    require(secret_values, "no secret value found for credential scan")
    for checked in (args.acquisition, args.panel_receipt):
        content = checked.read_bytes()
        require(not any(secret in content for secret in secret_values), f"credential value found in {checked}")

    rows = []
    raw_rows = {"cotton_upland": 0, "sorghum_grain": 0}
    coded = {crop: 0 for crop in raw_rows}
    numeric = {crop: 0 for crop in raw_rows}
    eligible_count = {crop: 0 for crop in raw_rows}
    for record in acquisition["records"]:
        path = ROOT / record["raw_path"]
        require(digest(path, "sha512") == record["sha512"], "raw hash differs")
        data = json.loads(path.read_text(encoding="utf-8"))["data"]
        crop = record["crop"]
        raw_rows[crop] += len(data)
        for item in data:
            state, county = str(item.get("state_ansi", "")).strip(), str(item.get("county_ansi", "")).strip()
            geography = bool(re.fullmatch(r"\d{2}", state) and re.fullmatch(r"\d{3}", county))
            value = number(item.get("Value", ""))
            coded[crop] += int(geography)
            numeric[crop] += int(np.isfinite(value))
            eligible_count[crop] += int(geography and np.isfinite(value))
            if geography and np.isfinite(value):
                rows.append({
                    "crop": crop, "harvest_year": int(record["year"]), "county_geoid": state + county,
                    "practice": PRACTICES[record["practice"]], "yield_value": value,
                    "yield_unit": str(item.get("unit_desc", "")).strip(),
                    "state_ansi": state, "state_alpha": str(item.get("state_alpha", "")).strip(),
                    "county_name": str(item.get("county_name", "")).strip(),
                    "value_raw": str(item.get("Value", "")).strip(), "cv_percent_raw": str(item.get("CV (%)", "")).strip(),
                })
    rebuilt = pd.DataFrame(rows)
    require(not rebuilt.duplicated(PAIR_KEYS + ["practice"]).any(), "duplicate rebuilt keys")
    pair_counts = rebuilt.groupby(PAIR_KEYS, observed=True).practice.nunique()
    keys = pair_counts.loc[pair_counts.eq(2)].reset_index()[PAIR_KEYS]
    rebuilt = rebuilt.merge(keys, on=PAIR_KEYS, how="inner", validate="many_to_one")
    observed = pd.read_parquet(args.panel)
    compare = [*PAIR_KEYS, "state_ansi", "state_alpha", "county_name", "practice", "yield_value", "yield_unit", "value_raw", "cv_percent_raw"]
    rebuilt = rebuilt[compare].sort_values(PAIR_KEYS + ["practice"]).reset_index(drop=True)
    observed_core = observed[compare].sort_values(PAIR_KEYS + ["practice"]).reset_index(drop=True)
    require(rebuilt.drop(columns="yield_value").equals(observed_core.drop(columns="yield_value")), "panel text/key fields differ")
    require(np.allclose(rebuilt.yield_value, observed_core.yield_value, rtol=0, atol=0), "panel values differ")
    require(observed.calendar_available.eq(False).all() and observed.weather_joined.eq(False).all(), "downstream gate opened")
    require(observed.response_estimation_authorized.eq(False).all() and observed.scc_authorized.eq(False).all(), "response gate opened")

    for expected in receipt["crop_summaries"]:
        crop = expected["crop"]
        part = observed.loc[observed.crop.eq(crop)]
        pairs = part.drop_duplicates(PAIR_KEYS)
        require(raw_rows[crop] == expected["raw_rows"], "raw count differs")
        require(coded[crop] == expected["coded_geography_rows"], "coded count differs")
        require(numeric[crop] == expected["numeric_positive_rows"], "numeric count differs")
        require(eligible_count[crop] == expected["eligible_rows"], "eligible count differs")
        require(len(pairs) == expected["paired_county_years"], "pair count differs")
        require(part.county_geoid.nunique() == expected["counties"], "county count differs")
        require(part.state_ansi.nunique() == expected["states"], "state count differs")
    result = {
        "status": "validated_full_raw_rebuild_and_credential_scan",
        "acquisition_sha256": digest(args.acquisition), "panel_receipt_sha256": digest(args.panel_receipt),
        "panel_sha256": digest(args.panel), "raw_files_revalidated": len(acquisition["records"]),
        "panel_rows": len(observed), "credential_value_found": False,
        "calendar_or_weather_joined": False, "response_damage_or_scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
