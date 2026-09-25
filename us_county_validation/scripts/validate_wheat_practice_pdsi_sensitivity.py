#!/usr/bin/env python3
"""Independently check the real wheat/PDSI aggregate result with sparse LSMR."""
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


PROJECT = Path(__file__).resolve().parents[2]
ESTIMATOR = PROJECT / "us_county_validation/scripts/estimate_wheat_practice_pdsi_sensitivity.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def load_estimator_module():
    spec = importlib.util.spec_from_file_location("wheat_pdsi_estimator", ESTIMATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load estimator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def indicator(codes: np.ndarray, levels: int) -> sparse.csr_matrix:
    rows = np.arange(len(codes), dtype=np.int64)
    return sparse.csr_matrix(
        (np.ones(len(codes), dtype=float), (rows, codes)),
        shape=(len(codes), levels),
    )


def joint_sparse_coefficients(
    frame: pd.DataFrame, outcome: str, form: str,
) -> tuple[np.ndarray, dict[str, float | int]]:
    p = frame.pdsi.to_numpy(dtype=float)
    raw_x = p[:, None] if form == "linear" else np.column_stack([p, np.square(p)])
    scale = raw_x.std(axis=0, ddof=0)
    x = raw_x / scale
    county_codes, county_labels = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year_codes, state_year_labels = pd.factorize(
        frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True
    )
    design = sparse.hstack([
        sparse.csr_matrix(x),
        indicator(county_codes, len(county_labels)),
        indicator(state_year_codes, len(state_year_labels)),
    ], format="csr")
    solved = lsmr(
        design, frame[outcome].to_numpy(dtype=float),
        atol=1e-12, btol=1e-12, conlim=1e12, maxiter=20000,
    )
    coefficients = np.asarray(solved[0][: raw_x.shape[1]], dtype=float) / scale
    if not np.isfinite(coefficients).all():
        raise ValueError("independent sparse coefficients are nonfinite")
    return coefficients, {
        "lsmr_stop_code": int(solved[1]),
        "lsmr_iterations": int(solved[2]),
        "lsmr_normal_equation_residual": float(solved[4]),
        "design_rows": int(design.shape[0]),
        "design_columns": int(design.shape[1]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--resource", required=True)
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    result_path = project_path(arguments.result)
    resource_path = project_path(arguments.resource)
    out_path = project_path(arguments.out)
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite {out_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("schema") != "us_wheat_practice_pdsi_sensitivity_v1":
        raise ValueError("wrong result schema")
    for gate in (
        "predictive_claim_authorized", "causal_claim_authorized",
        "irrigation_treatment_claim_authorized",
        "national_representativeness_claim_authorized",
        "future_drought_claim_authorized", "global_transfer_authorized",
        "damage_claim_authorized", "scc_claim_authorized",
    ):
        if result.get(gate) is not False:
            raise ValueError(f"result unexpectedly opens {gate}")
    for record in result["inputs"].values():
        path = project_path(record["path"])
        if sha256(path) != record["sha256"]:
            raise ValueError(f"input identity changed: {record['path']}")
    resource = json.loads(resource_path.read_text(encoding="utf-8"))
    if (
        resource.get("status") != "command_completed"
        or int(resource.get("returncode", -1)) != 0
        or int(resource.get("peak_rss_bytes", 2**63)) > 512 * 1024 * 1024
    ):
        raise ValueError("resource receipt failed")

    module = load_estimator_module()
    join_path = project_path(result["inputs"]["joined_panel"]["path"])
    calendar_path = project_path(result["inputs"]["calendar_definitions"]["path"])
    weights = module.wheat_state_weights(calendar_path)
    pairs, panel = module.prepare_panel(join_path, weights)
    if panel != result["panel"]:
        raise ValueError("reconstructed panel audit differs")
    indexed = {
        (row["outcome"], row["form"]): row for row in result["estimates"]
    }
    checks = []
    maximum = 0.0
    for form in ("linear", "quadratic"):
        for outcome in (
            "log_yield_irrigated", "log_yield_non_irrigated", "log_yield_gap"
        ):
            independent, diagnostics = joint_sparse_coefficients(pairs, outcome, form)
            reported = np.array([
                row["estimate"] for row in indexed[(outcome, form)]["coefficients"]
            ], dtype=float)
            difference = float(np.max(np.abs(independent - reported)))
            maximum = max(maximum, difference)
            checks.append({
                "outcome": outcome, "form": form,
                "maximum_absolute_coefficient_difference": difference,
                **diagnostics,
            })
    if maximum > 2e-8:
        raise ValueError(f"independent coefficient tolerance failed: {maximum}")
    identity_max = max(
        float(row["maximum_absolute_gap_vs_practice_difference"])
        for row in result["numerical_identities"]
    )
    if identity_max > 1e-10:
        raise ValueError("paired-gap identity failed")
    leaveout = result["linear_gap_leave_one_state_out"]
    if int(leaveout["same_sign_count"]) != int(leaveout["omission_count"]):
        raise ValueError("leave-one-state-out sign gate failed")
    output = {
        "schema": "us_wheat_practice_pdsi_sensitivity_independent_validation_v1",
        "status": "passed",
        "result": {"path": arguments.result, "sha256": sha256(result_path)},
        "resource": {
            "path": arguments.resource, "sha256": sha256(resource_path),
            "peak_rss_bytes": int(resource["peak_rss_bytes"]),
        },
        "panel": panel,
        "joint_sparse_checks": checks,
        "maximum_absolute_coefficient_difference": maximum,
        "paired_gap_identity_maximum_difference": identity_max,
        "leave_one_state_out_same_sign": (
            f"{leaveout['same_sign_count']}/{leaveout['omission_count']}"
        ),
        "claim_boundary": (
            "regional historical measurement sensitivity only; not causal, "
            "national, predictive, future, global, damage, or SCC evidence"
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "maximum_absolute_coefficient_difference": maximum,
        "peak_rss_bytes": output["resource"]["peak_rss_bytes"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
