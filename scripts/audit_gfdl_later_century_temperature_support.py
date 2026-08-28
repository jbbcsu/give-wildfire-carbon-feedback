#!/usr/bin/env python3
"""Re-audit mapped FAIR temperature support after bounded GFDL expansion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from validate_paired_feature_emulator import validate_pairs


ESM_ID = "GFDL-ESM4"
MEMBER_ID = "r1i1p1f1"
EXPECTED_SCENARIO_YEARS = {
    "historical": set(range(2011, 2015)),
    "ssp126": set(range(2015, 2021)) | set(range(2041, 2051)) | set(range(2091, 2101)),
    "ssp370": set(range(2015, 2021)) | set(range(2041, 2051)),
    "ssp585": set(range(2015, 2021)) | set(range(2041, 2051)),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify(values: pd.Series, lower: float, upper: float) -> pd.Series:
    numeric = pd.to_numeric(values, errors="raise").to_numpy(float)
    if not np.isfinite(numeric).all() or not np.isfinite([lower, upper]).all() or lower >= upper:
        raise ValueError("temperature support inputs are invalid")
    return pd.Series(np.where(numeric < lower, "below", np.where(numeric > upper, "above", "within")), index=values.index)


def horizon(years: pd.Series, states: pd.Series) -> dict[str, int | None]:
    frame = pd.DataFrame({"year": pd.to_numeric(years, errors="raise").astype(int), "state": states.astype(str)})
    if frame.duplicated("year").any() or not set(frame.state).issubset({"below", "within", "above"}):
        raise ValueError("temperature support horizon rows are invalid")
    by_state = {state: sorted(frame.loc[frame.state == state, "year"].tolist()) for state in ("below", "within", "above")}
    if not by_state["within"]:
        raise ValueError("mapped FAIR baseline never enters expanded temperature support")
    return {
        "first_within_year": by_state["within"][0],
        "last_within_year": by_state["within"][-1],
        "within_year_count": len(by_state["within"]),
        "last_below_year": by_state["below"][-1] if by_state["below"] else None,
        "first_above_year": by_state["above"][0] if by_state["above"] else None,
    }


def validate_gmst_coverage(frame: pd.DataFrame) -> dict[str, list[int]]:
    observed = {
        str(scenario): set(pd.to_numeric(block.year, errors="raise").astype(int))
        for scenario, block in frame.groupby("scenario", sort=True)
    }
    if observed != EXPECTED_SCENARIO_YEARS:
        raise ValueError("expanded GMST scenario/year coverage differs from the fixed input contract")
    return {scenario: sorted(years) for scenario, years in observed.items()}


def audit(pairs_path: Path, gmst_paths: list[Path]) -> dict[str, object]:
    if len(gmst_paths) != 8 or len(set(gmst_paths)) != len(gmst_paths):
        raise ValueError("expanded support requires the eight unique fixed GMST inputs")
    pairs = pd.read_parquet(pairs_path)
    member_counts = pairs.groupby("esm_id")["member_id"].nunique()
    if (member_counts != 1).any():
        raise ValueError("paired paths contain multiple members per ESM")
    members = pairs.groupby("esm_id")["member_id"].first().astype(str).to_dict()
    validate_pairs(pairs, members)
    selected = pairs.loc[pairs.esm_id.astype(str).eq(ESM_ID)].copy()
    if selected.empty or set(selected.member_id.astype(str)) != {MEMBER_ID}:
        raise ValueError("GFDL paired-path identity is missing or changed")

    gmst_frames = []
    receipts = []
    for path in gmst_paths:
        frame = pd.read_parquet(path)
        required = {"esm_id", "member_id", "scenario", "gmst_source_id", "year", "gmst_value_k"}
        if missing := required - set(frame):
            raise ValueError(f"GMST input lacks {sorted(missing)}: {path}")
        observed_esms = set(frame.esm_id.astype(str))
        if {value.lower() for value in observed_esms} != {ESM_ID.lower()} or set(frame.member_id.astype(str)) != {MEMBER_ID}:
            raise ValueError(f"GMST realization identity changed: {path}")
        values = pd.to_numeric(frame.gmst_value_k, errors="raise")
        source_ids = set(frame.gmst_source_id.astype(str))
        if not values.between(150, 350).all() or len(source_ids) != 1 or not next(iter(source_ids)).strip():
            raise ValueError(f"GMST values or source IDs are invalid: {path}")
        gmst_frames.append(frame[list(required)].copy())
        receipts.append({
            "path": str(path),
            "sha256": sha256(path),
            "rows": int(len(frame)),
            "observed_esm_id": sorted(observed_esms),
            "canonical_esm_id": ESM_ID,
        })
    gmst = pd.concat(gmst_frames, ignore_index=True)
    if gmst.duplicated(["scenario", "year"]).any():
        raise ValueError("expanded GMST files overlap within scenario/year")
    coverage = validate_gmst_coverage(gmst)
    if gmst.gmst_source_id.astype(str).nunique() != len(gmst_paths):
        raise ValueError("expanded GMST inputs do not have one unique source ID per file")
    lower, upper = float(gmst.gmst_value_k.min()), float(gmst.gmst_value_k.max())

    baseline = selected.loc[
        selected.alignment_method.astype(str).eq("absolute_anomaly_mapping")
        & pd.to_numeric(selected.pulse_size_gtc, errors="raise").eq(0),
        ["year", "baseline_temperature_k", "baseline_temperature_support"],
    ].drop_duplicates()
    if baseline.duplicated("year").any():
        raise ValueError("baseline mapped temperature differs across feature families")
    prior = horizon(baseline.year, baseline.baseline_temperature_support)
    expanded_states = classify(baseline.baseline_temperature_k, lower, upper)
    expanded = horizon(baseline.year, expanded_states)

    for side in ("baseline", "pulse"):
        selected[f"expanded_{side}_temperature_support"] = classify(
            selected[f"{side}_temperature_k"], lower, upper
        )
    counts = {
        method: {
            side: block[f"expanded_{side}_temperature_support"].value_counts().sort_index().astype(int).to_dict()
            for side in ("baseline", "pulse")
        }
        for method, block in selected.groupby("alignment_method", sort=True)
    }
    return {
        "schema": "gfdl_later_century_fair_temperature_support_audit_v1",
        "role": "temperature_support_sensitivity_not_feature_support_response_damage_or_scc",
        "result": "passed",
        "esm_id": ESM_ID,
        "member_id": MEMBER_ID,
        "expanded_training_temperature_min_k": lower,
        "expanded_training_temperature_max_k": upper,
        "prior_bounded_temperature_support_horizon": prior,
        "expanded_temperature_support_horizon": expanded,
        "expanded_support_counts": counts,
        "fixed_scenario_year_coverage": coverage,
        "gmst_inputs": receipts,
        "paired_paths": {"path": str(pairs_path), "sha256": sha256(pairs_path)},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "common_random_number_pairing_revalidated": True,
        "zero_pulse_and_predivergence_identity_revalidated": True,
        "decreasing_pulse_convergence_revalidated": True,
        "feature_support_rerun": False,
        "production_emulator_authorized": False,
        "damage_or_scc_authorized": False,
        "limitation": (
            "This reclassifies mapped FAIR temperatures against the expanded GFDL GMST envelope only. "
            "It does not extend feature support for every family or validate a production response."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--gmst", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.pairs.resolve(), [path.resolve() for path in args.gmst])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "GFDL expanded FAIR temperature-support audit passed: "
        f"last within {result['prior_bounded_temperature_support_horizon']['last_within_year']} -> "
        f"{result['expanded_temperature_support_horizon']['last_within_year']}"
    )


if __name__ == "__main__":
    main()
