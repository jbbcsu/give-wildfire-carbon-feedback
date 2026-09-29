#!/usr/bin/env python3
"""Independent sparse-dummy validation of the outcome-blind design audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsmr


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "us_county_validation/us_corn_soy_response_design_readiness_v1.toml"
CANDIDATE = PROJECT / "data/provenance/us_corn_soy_response_design_readiness_20260928.json"
OUTPUT = PROJECT / "data/provenance/us_corn_soy_response_design_readiness_independent_validation_20260928.json"
KEYS = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def design(frame: pd.DataFrame, family: str) -> np.ndarray:
    columns: list[np.ndarray] = []
    for name in ("stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"):
        value = frame[name].to_numpy(float)
        columns.extend([value, value**2])
    if family in {"quantity", "distribution"}:
        rain = frame.precip_mm.to_numpy(float) / 100.0
        columns.extend([rain, rain**2])
        if family == "distribution":
            for name in (
                "cdd_max_days", "wet_day_frequency", "mean_wet_day_intensity_mm",
                "rx1day_mm", "rx5day_mm", "precipitation_concentration_hhi",
                "stage1_precip_share", "stage2_precip_share",
            ):
                columns.append(frame[name].to_numpy(float))
    else:
        value = frame.pdsi_season_mean.to_numpy(float)
        columns.extend([value, value**2])
    return np.column_stack(columns)


def sparse_residualize(frame: pd.DataFrame, x: np.ndarray) -> np.ndarray:
    county, county_labels = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year, state_year_labels = pd.factorize(
        frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True
    )
    n = len(frame)
    rows = np.repeat(np.arange(n), 2)
    columns = np.empty(2 * n, dtype=int)
    columns[0::2] = county
    columns[1::2] = len(county_labels) + state_year
    dummy = sparse.csr_matrix(
        (np.ones(2 * n), (rows, columns)),
        shape=(n, len(county_labels) + len(state_year_labels)),
    )
    result = np.empty_like(x, dtype=float)
    for column in range(x.shape[1]):
        coefficient = lsmr(
            dummy, x[:, column], atol=1e-13, btol=1e-13,
            conlim=1e12, maxiter=10000,
        )[0]
        result[:, column] = x[:, column] - dummy @ coefficient
    return result


def diagnostics(frame: pd.DataFrame, family: str) -> dict[str, float | int]:
    raw = design(frame, family)
    within = sparse_residualize(frame, raw)
    raw_sd = raw.std(axis=0)
    within_sd = within.std(axis=0)
    z = within / within_sd
    u, singular, vh = np.linalg.svd(z, full_matrices=False)
    relative = singular / singular[0]
    retained = relative > 1e-10
    rank = int(retained.sum())
    leverage = np.sum(u[:, :rank] ** 2, axis=1)
    vif = len(z) * np.sum(
        (vh[retained, :] ** 2) / (singular[retained, None] ** 2), axis=0
    )
    return {
        "rank": rank,
        "minimum_residual_to_raw_sd_ratio": float(np.min(within_sd / raw_sd)),
        "standardized_condition_number": float(singular[0] / singular[-1]),
        "maximum_vif": float(vif.max()),
        "maximum_row_leverage": float(leverage.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    if candidate.get("schema") != "us_corn_soy_response_design_readiness_v1":
        raise AssertionError("candidate schema changed")
    if candidate["protocol"]["sha256"] != digest(CONFIG):
        raise AssertionError("candidate protocol identity changed")
    for gate in (
        "response_fit_authorized", "coefficient_output_authorized",
        "causal_claim_authorized", "national_claim_authorized",
        "damage_claim_authorized", "scc_claim_authorized",
    ):
        if candidate.get(gate) is not False:
            raise AssertionError(f"candidate unexpectedly opens {gate}")
    if candidate["inputs"].get("outcome_columns_read") != []:
        raise AssertionError("candidate is not outcome blind")

    direct_path = PROJECT / config["inputs"]["direct_panel"]
    pdsi_path = PROJECT / config["inputs"]["pdsi_panel"]
    if digest(direct_path) != candidate["inputs"]["direct_panel"]["sha256"]:
        raise AssertionError("direct input identity changed")
    if digest(pdsi_path) != candidate["inputs"]["pdsi_panel"]["sha256"]:
        raise AssertionError("PDSI input identity changed")
    features = [
        "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c", "precip_mm",
        "cdd_max_days", "wet_day_frequency", "mean_wet_day_intensity_mm",
        "rx1day_mm", "rx5day_mm", "precipitation_concentration_hhi",
        "stage1_precip_share", "stage2_precip_share",
    ]
    direct = pd.read_parquet(direct_path, columns=[*KEYS, "state", *features])
    direct = direct.loc[
        direct.outcome_crop.isin(config["sample"]["crops"])
        & direct.irrigation_practice.isin(config["sample"]["practices"])
        & direct.harvest_year.between(config["sample"]["year_min"], config["sample"]["year_max"])
    ].copy()
    pdsi = pd.read_parquet(
        pdsi_path,
        columns=[*KEYS, "calendar_role", "window_id", "index_day_weighted_mean"],
    )
    pdsi = pdsi.loc[
        pdsi.outcome_crop.isin(config["sample"]["crops"])
        & pdsi.irrigation_practice.isin(config["sample"]["practices"])
        & pdsi.harvest_year.between(config["sample"]["year_min"], config["sample"]["year_max"])
        & pdsi.calendar_role.eq("fixed_primary")
        & pdsi.window_id.eq("season")
    ].rename(columns={"index_day_weighted_mean": "pdsi_season_mean"})
    frame = direct.merge(pdsi[[*KEYS, "pdsi_season_mean"]], on=KEYS, validate="one_to_one")

    maximum = 0.0
    comparisons = 0
    recomputed: list[dict[str, object]] = []
    for crop in config["sample"]["crops"]:
        left = frame.loc[
            frame.outcome_crop.eq(crop) & frame.irrigation_practice.eq("non_irrigated")
        ].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        right = frame.loc[
            frame.outcome_crop.eq(crop) & frame.irrigation_practice.eq("irrigated")
        ].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        if not left[["county_geoid", "harvest_year", "state", *features, "pdsi_season_mean"]].equals(
            right[["county_geoid", "harvest_year", "state", *features, "pdsi_season_mean"]]
        ):
            raise AssertionError(f"practice exposure identity failed for {crop}")
        for family in ("quantity", "distribution", "pdsi"):
            actual = diagnostics(left, family)
            reported = next(
                item for item in candidate["audits"]
                if item["crop"] == crop
                and item["irrigation_practice"] == "non_irrigated"
                and item["family"] == family
            )["diagnostics"]
            for field, value in actual.items():
                difference = abs(float(value) - float(reported[field]))
                maximum = max(maximum, difference)
                comparisons += 1
                tolerance = 1e-6 * max(1.0, abs(float(reported[field])))
                if difference > tolerance:
                    raise AssertionError(f"independent disagreement for {crop}/{family}/{field}: {difference}")
            recomputed.append({"crop": crop, "family": family, **actual})

    readiness = []
    for item in candidate["family_readiness"]:
        pair = [
            audit for audit in candidate["audits"]
            if audit["crop"] == item["crop"] and audit["family"] == item["family"]
        ]
        expected = all(all(audit["gates"].values()) for audit in pair)
        if expected != item["both_practices_pass"]:
            raise AssertionError("family readiness is inconsistent with recorded gates")
        readiness.append({
            "crop": item["crop"], "family": item["family"],
            "both_practices_pass": expected,
        })
    result = {
        "schema": "us_corn_soy_response_design_readiness_independent_validation_v1",
        "status": "validated_independent_sparse_dummy_projection",
        "candidate": {"path": str(args.candidate.resolve().relative_to(PROJECT)), "sha256": digest(args.candidate)},
        "protocol": {"path": str(CONFIG.relative_to(PROJECT)), "sha256": digest(CONFIG)},
        "validation_implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "numeric_comparisons": comparisons,
        "maximum_absolute_disagreement": maximum,
        "recomputed_diagnostics": recomputed,
        "family_readiness_reconciled": readiness,
        "outcome_columns_read": [],
        "response_fit_authorized": False,
        "causal_claim_authorized": False,
        "national_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "numeric_comparisons": comparisons, "maximum_absolute_disagreement": maximum}, indent=2))


if __name__ == "__main__":
    main()
