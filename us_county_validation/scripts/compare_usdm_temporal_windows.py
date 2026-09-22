#!/usr/bin/env python3
"""Compare frozen calendar-year and corrected October--September USDM results."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


TERMS = ["d0_weeks", "d1_weeks", "d2_weeks", "d3_weeks", "d4_weeks"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def model_index(payload: dict, family: str | None = None) -> dict[tuple[str, str], dict]:
    source = payload["results"]
    if family is not None:
        source = [row for row in source if row.get("family") == family]
    return {(row["outcome_crop"], row["irrigation_class"]): row for row in source}


def coefficient_index(model: dict) -> dict[str, dict]:
    return {row["term"]: row for row in model["coefficients"]}


def compare_models(calendar: dict, corrected: dict, family: str | None = None) -> list[dict]:
    old = model_index(calendar, family)
    new = model_index(corrected, family)
    if set(old) != set(new):
        raise ValueError("calendar and corrected model coverage differs")
    comparisons = []
    for key in sorted(old):
        old_terms = coefficient_index(old[key])
        new_terms = coefficient_index(new[key])
        for term in TERMS:
            before = float(old_terms[term]["estimate_log_points_per_area_equivalent_week"])
            after = float(new_terms[term]["estimate_log_points_per_area_equivalent_week"])
            comparisons.append({
                "outcome_crop": key[0],
                "irrigation_class": key[1],
                "family": family or "drought_only",
                "term": term,
                "calendar_year_estimate": before,
                "october_september_estimate": after,
                "october_september_minus_calendar_year": after - before,
                "calendar_year_sign": -1 if before < 0 else (1 if before > 0 else 0),
                "october_september_sign": -1 if after < 0 else (1 if after > 0 else 0),
            })
    return comparisons


def exposure_summary(path: Path) -> dict:
    frame = pd.read_parquet(path)
    unique = frame.drop_duplicates(["county_geoid", "harvest_year"])
    if len(unique) * 2 != len(frame):
        raise ValueError("expected exactly two crop copies per county-harvest-year")
    return {
        "crop_county_year_rows": int(len(frame)),
        "unique_county_year_rows": int(len(unique)),
        "counties": int(unique.county_geoid.nunique()),
        "harvest_year_min": int(unique.harvest_year.min()),
        "harvest_year_max": int(unique.harvest_year.max()),
        "mean_area_equivalent_weeks": {
            term: float(unique[term].mean()) for term in TERMS
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar-exposures", type=Path, required=True)
    parser.add_argument("--corrected-exposures", type=Path, required=True)
    parser.add_argument("--calendar-drought-result", type=Path, required=True)
    parser.add_argument("--corrected-drought-result", type=Path, required=True)
    parser.add_argument("--calendar-weather-result", type=Path, required=True)
    parser.add_argument("--corrected-weather-result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    paths = {
        "calendar_exposures": arguments.calendar_exposures,
        "corrected_exposures": arguments.corrected_exposures,
        "calendar_drought_result": arguments.calendar_drought_result,
        "corrected_drought_result": arguments.corrected_drought_result,
        "calendar_weather_result": arguments.calendar_weather_result,
        "corrected_weather_result": arguments.corrected_weather_result,
    }
    calendar_drought = read_json(arguments.calendar_drought_result)
    corrected_drought = read_json(arguments.corrected_drought_result)
    calendar_weather = read_json(arguments.calendar_weather_result)
    corrected_weather = read_json(arguments.corrected_weather_result)
    comparisons = compare_models(calendar_drought, corrected_drought)
    comparisons.extend(compare_models(calendar_weather, corrected_weather, "drought_plus_weather"))
    payload = {
        "schema": "usdm_temporal_window_comparison_v1",
        "inputs": {
            name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()
        },
        "published_target": {
            "source": "Kuwayama et al. (2019), Table 2",
            "area_basis": "agricultural area",
            "county_year_observations": 40040,
            "mean_area_equivalent_weeks": {
                "d0_weeks": 8.47,
                "d1_weeks": 5.66,
                "d2_weeks": 3.87,
                "d3_weeks": 2.26,
                "d4_weeks": 0.80,
            },
        },
        "calendar_exposure_summary": exposure_summary(arguments.calendar_exposures),
        "october_september_exposure_summary": exposure_summary(arguments.corrected_exposures),
        "coefficient_comparisons": comparisons,
        "interpretation": "timing sensitivity only; county-area exposures do not replicate published agricultural-area weighting",
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(comparisons)} temporal-window coefficient comparisons")


if __name__ == "__main__":
    main()
