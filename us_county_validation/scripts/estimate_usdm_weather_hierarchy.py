#!/usr/bin/env python3
"""Estimate frozen weather-only and drought-plus-weather U.S. benchmarks."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "estimate_usdm_drought_only.py"
SPEC = importlib.util.spec_from_file_location("drought_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load drought estimator")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
KEYS = ["county_geoid", "outcome_crop", "harvest_year"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rainfall_contrasts(frame: pd.DataFrame, fit: dict, weather_terms: list[str]) -> list[dict]:
    index = {row["term"]: row for row in fit["coefficients"]}
    linear = index["precipitation_per_100mm"]["estimate_log_points_per_area_equivalent_week"]
    quadratic = index["precipitation_per_100mm_squared"]["estimate_log_points_per_area_equivalent_week"]
    values = frame.precipitation_per_100mm.to_numpy(dtype=float)
    rows = []
    for quantile in (0.25, 0.50, 0.75):
        reference = float(np.quantile(values, quantile))
        delta_log = linear + quadratic * ((reference + 1) ** 2 - reference**2)
        rows.append({
            "reference_quantile": quantile,
            "reference_precipitation_mm": reference * 100,
            "plus_100mm_exact_fitted_yield_percent_change": float(100 * np.expm1(delta_log)),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--yields", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--drought", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    drought_terms = list(map(str, contract["drought_terms"]))
    weather_terms = list(map(str, contract["weather_terms"]))
    year_min, year_max = int(contract["year_min"]), int(contract["year_max"])
    crops = list(map(str, contract["crops"]))
    classes = list(map(str, contract["irrigation_classes"]))

    yields = pd.read_parquet(arguments.yields)
    yields = yields.loc[
        yields.harvest_year.between(year_min, year_max)
        & yields.outcome_crop.isin(crops)
    ].copy()
    classifier = pd.read_csv(arguments.classifier, dtype={"county_geoid": "string"})
    classifier = classifier.loc[classifier.classifier_eligible.eq(True)].copy()
    drought = pd.read_parquet(arguments.drought)
    weather = pd.read_parquet(arguments.weather)
    for label, frame, terms in (
        ("drought", drought, drought_terms), ("weather", weather, weather_terms)
    ):
        if frame.duplicated(KEYS).any() or any(term not in frame for term in terms):
            raise ValueError(f"{label} panel has duplicate keys or missing terms")
        if frame.scc_authorized.any():
            raise ValueError(f"{label} panel violates SCC boundary")
    panel = yields.merge(
        classifier[["county_geoid", "irrigation_class"]],
        on="county_geoid", how="inner", validate="many_to_one",
    ).merge(
        drought[KEYS + drought_terms], on=KEYS, how="inner", validate="one_to_one"
    ).merge(
        weather[KEYS + weather_terms], on=KEYS, how="inner", validate="one_to_one"
    )
    if panel.empty or panel.duplicated(KEYS).any():
        raise ValueError("common weather/drought model panel is empty or duplicated")
    results = []
    families = {
        "weather_only": weather_terms,
        "drought_plus_weather": drought_terms + weather_terms,
    }
    if list(families) != list(map(str, contract["families"])):
        raise ValueError("config family ordering differs from estimator")
    for crop in crops:
        for irrigation_class in classes:
            sample = panel.loc[
                panel.outcome_crop.eq(crop)
                & panel.irrigation_class.eq(irrigation_class)
            ].copy()
            if sample.empty:
                raise ValueError(f"empty sample for {crop} {irrigation_class}")
            for family, terms in families.items():
                fit = BASE.fit_one(sample, terms)
                fit.update({
                    "outcome_crop": crop,
                    "irrigation_class": irrigation_class,
                    "family": family,
                    "terms": terms,
                    "rainfall_plus_100mm_contrasts": rainfall_contrasts(
                        sample, fit, weather_terms
                    ),
                })
                results.append(fit)
    payload = {
        "schema": "usdm_weather_hierarchy_result_v1",
        "contract": contract,
        "inputs": {
            label: {"path": str(path), "sha256": sha256(path)}
            for label, path in {
                "config": arguments.config, "yields": arguments.yields,
                "classifier": arguments.classifier, "drought": arguments.drought,
                "weather": arguments.weather,
            }.items()
        },
        "common_panel_rows": int(len(panel)),
        "common_panel_counties": int(panel.county_geoid.nunique()),
        "results": results,
        "published_replication": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"estimated {len(results)} weather-hierarchy models on {len(panel)} rows")


if __name__ == "__main__":
    main()
