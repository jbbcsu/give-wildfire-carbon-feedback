#!/usr/bin/env python3
"""Independent joint sparse-design validation of the weather hierarchy."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsmr


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--yields", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--drought", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    result = json.loads(arguments.result.read_text())
    contract = result["contract"]
    year_min, year_max = int(contract["year_min"]), int(contract["year_max"])
    yields = pd.read_parquet(arguments.yields)
    yields = yields.loc[yields.harvest_year.between(year_min, year_max)]
    classifier = pd.read_csv(arguments.classifier, dtype={"county_geoid": "string"})
    classifier = classifier.loc[classifier.classifier_eligible.eq(True)]
    drought = pd.read_parquet(arguments.drought)
    weather = pd.read_parquet(arguments.weather)
    for label, path in {
        "yields": arguments.yields, "classifier": arguments.classifier,
        "drought": arguments.drought, "weather": arguments.weather,
    }.items():
        if result["inputs"][label]["sha256"] != sha256(path):
            raise ValueError(f"{label} input hash differs")
    drought_terms = list(map(str, contract["drought_terms"]))
    weather_terms = list(map(str, contract["weather_terms"]))
    panel = yields.merge(
        classifier[["county_geoid", "irrigation_class"]], on="county_geoid",
        how="inner", validate="many_to_one",
    ).merge(drought[KEYS + drought_terms], on=KEYS, how="inner", validate="one_to_one").merge(
        weather[KEYS + weather_terms], on=KEYS, how="inner", validate="one_to_one"
    )
    if len(panel) != int(result["common_panel_rows"]):
        raise ValueError("common panel row count differs")
    audits = []
    for model in result["results"]:
        terms = list(map(str, model["terms"]))
        frame = panel.loc[
            panel.outcome_crop.eq(model["outcome_crop"])
            & panel.irrigation_class.eq(model["irrigation_class"])
        ].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        nuisance, _ = BASE.nuisance_matrix(frame)
        x = frame[terms].to_numpy(dtype=float)
        y = np.log(frame.yield_bu_acre.to_numpy(dtype=float))
        design = sparse.hstack([nuisance, sparse.csr_matrix(x)], format="csr")
        solution = lsmr(design, y, atol=1e-12, btol=1e-12, maxiter=50_000)
        direct = solution[0][-len(terms):]
        reported = np.array([
            row["estimate_log_points_per_area_equivalent_week"]
            for row in model["coefficients"]
        ])
        maximum = float(np.max(np.abs(direct - reported)))
        if maximum > 5e-8:
            raise ValueError(f"coefficient mismatch {maximum}")
        covariance = np.asarray(model["covariance_county_cluster_cr1"])
        if not np.allclose(covariance, covariance.T, rtol=0, atol=1e-12):
            raise ValueError("covariance is not symmetric")
        if np.linalg.eigvalsh(covariance).min() < -1e-12:
            raise ValueError("covariance is not positive semidefinite")
        audits.append({
            "outcome_crop": model["outcome_crop"],
            "irrigation_class": model["irrigation_class"],
            "family": model["family"],
            "rows": len(frame),
            "joint_lsmr_iterations": int(solution[2]),
            "maximum_absolute_coefficient_difference": maximum,
        })
    payload = {
        "schema": "usdm_weather_hierarchy_independent_validation_v1",
        "status": "passed",
        "result": {"path": str(arguments.result), "sha256": sha256(arguments.result)},
        "models": audits,
        "claim_boundary": "historical noncausal validation only; not damage or SCC",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"passed independent validation for {len(audits)} weather-hierarchy models")


if __name__ == "__main__":
    main()
