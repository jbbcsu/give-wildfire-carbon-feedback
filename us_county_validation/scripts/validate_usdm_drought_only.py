#!/usr/bin/env python3
"""Independent joint-design validation of the frozen drought-only estimates."""
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
ESTIMATOR_PATH = HERE / "estimate_usdm_drought_only.py"
SPEC = importlib.util.spec_from_file_location("drought_estimator", ESTIMATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load drought estimator")
ESTIMATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ESTIMATOR)
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
    parser.add_argument("--exposures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--coefficient-tolerance", type=float, default=2e-8)
    arguments = parser.parse_args()
    result = json.loads(arguments.result.read_text(encoding="utf-8"))
    if result.get("schema") != "usdm_kuwayama_drought_only_result_v1":
        raise ValueError("unexpected result schema")
    contract = result["contract"]
    terms = list(map(str, contract["exposure_terms"]))
    year_min, year_max = int(contract["year_min"]), int(contract["year_max"])

    for label, path in {
        "yields": arguments.yields,
        "classifier": arguments.classifier,
        "exposures": arguments.exposures,
    }.items():
        if result["inputs"][label]["sha256"] != sha256(path):
            raise ValueError(f"{label} hash differs from frozen result")
    yields = pd.read_parquet(arguments.yields)
    yields = yields.loc[yields.harvest_year.between(year_min, year_max)].copy()
    classifier = pd.read_csv(arguments.classifier, dtype={"county_geoid": "string"})
    classifier = classifier.loc[classifier.classifier_eligible.eq(True)]
    exposures = pd.read_parquet(arguments.exposures)
    expected_days = exposures.harvest_year.map(
        lambda year: 366 if pd.Timestamp(int(year), 12, 31).is_leap_year else 365
    )
    reconciliation = (
        exposures[["none_weeks", *terms]].sum(axis=1) - expected_days / 7
    ).abs()
    if reconciliation.max() > 0.08 + 1e-12:
        raise ValueError("annual exposure arithmetic exceeds frozen rounding tolerance")
    if exposures.scc_authorized.any() or exposures.exact_published_exposure_replication.any():
        raise ValueError("exposure claim boundary changed")
    panel = yields.merge(
        classifier[["county_geoid", "irrigation_class"]], on="county_geoid",
        how="inner", validate="many_to_one",
    ).merge(exposures[KEYS + terms], on=KEYS, how="inner", validate="one_to_one")
    if len(panel) != int(result["joined_panel_rows"]):
        raise ValueError("joined panel row count differs from result")

    audits = []
    for model in result["results"]:
        frame = panel.loc[
            panel.outcome_crop.eq(model["outcome_crop"])
            & panel.irrigation_class.eq(model["irrigation_class"])
        ].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        if len(frame) != int(model["rows"]):
            raise ValueError("model row count differs")
        nuisance, _ = ESTIMATOR.nuisance_matrix(frame)
        x = frame[terms].to_numpy(dtype=float)
        y = np.log(frame.yield_bu_acre.to_numpy(dtype=float))
        joint = sparse.hstack([nuisance, sparse.csr_matrix(x)], format="csr")
        solution = lsmr(joint, y, atol=1e-12, btol=1e-12, maxiter=50_000)
        direct = solution[0][-len(terms):]
        reported = np.array([
            value["estimate_log_points_per_area_equivalent_week"]
            for value in model["coefficients"]
        ])
        maximum = float(np.max(np.abs(direct - reported)))
        if maximum > arguments.coefficient_tolerance:
            raise ValueError(f"joint-design coefficient mismatch: {maximum}")
        covariance = np.asarray(model["covariance_county_cluster_cr1"], dtype=float)
        if not np.allclose(covariance, covariance.T, rtol=0, atol=1e-12):
            raise ValueError("reported covariance is not symmetric")
        if np.linalg.eigvalsh(covariance).min() < -1e-12:
            raise ValueError("reported covariance is not positive semidefinite")
        se = np.sqrt(np.diag(covariance))
        reported_se = np.array([
            value["standard_error_county_cluster_cr1"]
            for value in model["coefficients"]
        ])
        if not np.allclose(se, reported_se, rtol=0, atol=1e-12):
            raise ValueError("reported standard errors do not equal covariance diagonal")
        audits.append({
            "outcome_crop": model["outcome_crop"],
            "irrigation_class": model["irrigation_class"],
            "rows": len(frame),
            "joint_lsmr_stop_code": int(solution[1]),
            "joint_lsmr_iterations": int(solution[2]),
            "maximum_absolute_coefficient_difference": maximum,
        })
    payload = {
        "schema": "usdm_kuwayama_drought_only_independent_validation_v1",
        "status": "passed",
        "result": {"path": str(arguments.result), "sha256": sha256(arguments.result)},
        "coefficient_tolerance": arguments.coefficient_tolerance,
        "maximum_annual_category_reconciliation_error_weeks": float(reconciliation.max()),
        "models": audits,
        "validated_claim_boundary": "historical external validation only; not causal, damage, or SCC",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"passed independent joint-design validation for {len(audits)} models")


if __name__ == "__main__":
    main()
