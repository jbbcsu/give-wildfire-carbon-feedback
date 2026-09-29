#!/usr/bin/env python3
"""Synthetic-only executor for the frozen corn quantity/PDSI spatial design."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_us_corn_quantity_pdsi_spatial_dry_run as adapter  # noqa: E402
from us_corn_spatial_inference_primitives import (  # noqa: E402
    county_cr1_meat,
    county_plus_spatial_covariance,
    contrast_standard_error,
)


PROTOCOL = PROJECT / "us_county_validation/us_corn_quantity_pdsi_spatial_inference_v1.toml"
OUTPUT = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_synthetic_executor_20260929.json"
KEYS = ["county_geoid", "harvest_year"]
PRACTICES = ["non_irrigated", "irrigated"]
FAMILIES = ["quantity", "pdsi"]
EXPOSURES = [
    "state", "latitude", "longitude", "precip_mm", "pdsi_season_mean",
    "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def execute_real_path(
    authorization_path: Path | None,
    real_loader: Callable[[], Any],
    real_fitter: Callable[[Any], Any],
) -> Any:
    """Future real seam: authorization is checked before loader or fitter."""
    config = adapter.load_config()
    adapter.require_real_run_authorization(config, authorization_path)
    loaded = real_loader()
    return real_fitter(loaded)


def make_synthetic_fixture(seed: int = 29092026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    states = ["CO", "IA", "KS", "NE", "TX"]
    centers = {
        "CO": (39.0, -105.5), "IA": (42.0, -93.5), "KS": (38.5, -98.0),
        "NE": (41.5, -99.5), "TX": (32.0, -99.0),
    }
    rows: list[dict[str, object]] = []
    county_effects: dict[str, float] = {}
    for state_index, state in enumerate(states):
        for county_index in range(6):
            geoid = f"{state_index + 1:02d}{county_index + 1:03d}"
            county_effects[geoid] = float(rng.normal(0, 0.08))
            latitude = centers[state][0] + 0.35 * county_index
            longitude = centers[state][1] + 0.30 * county_index
            for year in range(1981, 2019):
                time = year - 1981
                shared = rng.normal()
                precip = 430 + 45 * np.sin(time / 4) + 10 * state_index + 18 * shared + rng.normal(0, 20)
                pdsi = 0.9 * np.sin(time / 5) + 0.15 * state_index + 0.45 * shared + rng.normal(0, 0.35)
                temperatures = [
                    16 + 0.025 * time + 0.30 * state_index + rng.normal(0, 1.2),
                    22 + 0.030 * time + 0.25 * state_index + rng.normal(0, 1.3),
                    19 + 0.020 * time + 0.20 * state_index + rng.normal(0, 1.1),
                ]
                state_year = 0.002 * time + 0.02 * np.cos(time / 3 + state_index)
                for practice in PRACTICES:
                    moisture = (
                        0.040 * precip / 100 - 0.004 * (precip / 100) ** 2
                        + 0.018 * pdsi - 0.003 * pdsi**2
                    )
                    practice_scale = 1.0 if practice == "non_irrigated" else 0.35
                    synthetic_log_yield = (
                        4.2 + county_effects[geoid] + state_year
                        + practice_scale * moisture
                        + 0.004 * temperatures[0] - 0.00008 * temperatures[1] ** 2
                        + rng.normal(0, 0.035)
                    )
                    rows.append({
                        "county_geoid": geoid, "state": state, "harvest_year": year,
                        "irrigation_practice": practice, "latitude": latitude,
                        "longitude": longitude, "precip_mm": precip,
                        "pdsi_season_mean": pdsi, "stage1_tmean_c": temperatures[0],
                        "stage2_tmean_c": temperatures[1], "stage3_tmean_c": temperatures[2],
                        "synthetic_log_yield": synthetic_log_yield,
                    })
    frame = pd.DataFrame(rows)
    frame.attrs["source_role"] = "synthetic_fixture_only"
    frame.attrs["contains_real_outcomes"] = False
    return frame


def validate_synthetic_frame(frame: pd.DataFrame) -> None:
    if frame.attrs.get("source_role") != "synthetic_fixture_only" or frame.attrs.get("contains_real_outcomes") is not False:
        raise ValueError("executor accepts only an explicitly marked synthetic fixture")
    required = {*KEYS, "irrigation_practice", "synthetic_log_yield", *EXPOSURES}
    if missing := required - set(frame.columns):
        raise ValueError(f"synthetic fixture lacks {sorted(missing)}")
    forbidden = {"yield_bu_acre", "yield", "log_yield"}
    if forbidden & set(frame.columns):
        raise ValueError("synthetic fixture contains a forbidden real-outcome column name")
    if frame.duplicated([*KEYS, "irrigation_practice"]).any():
        raise ValueError("synthetic fixture has duplicate practice keys")
    if set(frame.irrigation_practice.astype(str)) != set(PRACTICES):
        raise ValueError("synthetic fixture does not contain the exact practices")
    grouped = frame.groupby(KEYS, observed=True, sort=False)
    if not grouped.irrigation_practice.agg(set).map(lambda x: x == set(PRACTICES)).all():
        raise ValueError("synthetic practice rows are not exactly paired")
    for column in EXPOSURES:
        if grouped[column].nunique(dropna=False).ne(1).any():
            raise ValueError(f"synthetic practices do not share {column}")


def residualize(values: np.ndarray, groups: list[np.ndarray]) -> np.ndarray:
    result = values.astype(float, copy=True)
    for _ in range(1000):
        previous = result.copy()
        for group in groups:
            count = np.bincount(group).astype(float)
            for column in range(result.shape[1]):
                totals = np.bincount(group, weights=result[:, column], minlength=len(count))
                result[:, column] -= (totals / count)[group]
        if np.max(np.abs(result - previous)) <= 1e-10:
            return result
    raise ValueError("synthetic fixed-effect projection did not converge")


def design(frame: pd.DataFrame, family: str) -> tuple[np.ndarray, list[str]]:
    columns: list[np.ndarray] = []
    names: list[str] = []
    for name in ("stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"):
        value = frame[name].to_numpy(float)
        columns.extend([value, value**2])
        names.extend([name, f"{name}_squared"])
    if family == "quantity":
        value = frame.precip_mm.to_numpy(float) / 100.0
        columns.extend([value, value**2])
        names.extend(["precipitation_per_100mm", "precipitation_per_100mm_squared"])
    elif family == "pdsi":
        value = frame.pdsi_season_mean.to_numpy(float)
        columns.extend([value, value**2])
        names.extend(["pdsi_season_mean", "pdsi_season_mean_squared"])
    else:
        raise ValueError("families must be quantity or pdsi and cannot be stacked")
    return np.column_stack(columns), names


def target_vectors(frame: pd.DataFrame, family: str, names: list[str]) -> list[dict[str, Any]]:
    feature = "precip_mm" if family == "quantity" else "pdsi_season_mean"
    targets = []
    for quantile in (0.25, 0.50, 0.75):
        reference = float(frame[feature].quantile(quantile))
        vector = np.zeros(len(names))
        if family == "quantity":
            scaled = reference / 100
            vector[names.index("precipitation_per_100mm")] = 1.0
            vector[names.index("precipitation_per_100mm_squared")] = (scaled + 1) ** 2 - scaled**2
            change = 100.0
        else:
            vector[names.index("pdsi_season_mean")] = -1.0
            vector[names.index("pdsi_season_mean_squared")] = (reference - 1) ** 2 - reference**2
            change = -1.0
        targets.append({"reference_quantile": quantile, "reference_value": reference, "change": change, "vector": vector})
    return targets


def fit_cell(frame: pd.DataFrame, family: str, cutoffs: list[float]) -> dict[str, Any]:
    raw_x, names = design(frame, family)
    if family == "quantity" and any("pdsi" in name for name in names):
        raise ValueError("quantity design contains PDSI")
    if family == "pdsi" and any("precipitation" in name for name in names):
        raise ValueError("PDSI design contains direct rainfall")
    county, _ = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year, _ = pd.factorize(frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True)
    transformed = residualize(
        np.column_stack([frame.synthetic_log_yield.to_numpy(float), raw_x]),
        [county, state_year],
    )
    y, x = transformed[:, 0], transformed[:, 1:]
    gram = np.einsum("ni,nj->ij", x, x, optimize=False)
    score = np.einsum("ni,n->i", x, y, optimize=False)
    beta = np.linalg.solve(gram, score)
    error = y - np.einsum("ni,i->n", x, beta, optimize=False)
    bread = np.linalg.inv(gram)
    covariance = np.einsum(
        "ij,jk,kl->il", bread,
        county_cr1_meat(x, error, frame.county_geoid.to_numpy()), bread,
        optimize=False,
    )
    spatial = {
        str(int(cutoff)): county_plus_spatial_covariance(
            x, error, frame.county_geoid.to_numpy(), frame.harvest_year.to_numpy(),
            frame.latitude.to_numpy(float), frame.longitude.to_numpy(float), cutoff,
        )
        for cutoff in cutoffs
    }
    contrasts = []
    for target in target_vectors(frame, family, names):
        vector = target.pop("vector")
        estimate = float(np.einsum("i,i->", vector, beta, optimize=False))
        ses = {"county_cr1": contrast_standard_error(covariance, vector)}
        ses.update({f"spatial_{key}km": contrast_standard_error(value, vector) for key, value in spatial.items()})
        contrasts.append({
            **target, "estimate": estimate,
            "standard_errors": ses,
            "normal_95_intervals": {name: [estimate - 1.96 * se, estimate + 1.96 * se] for name, se in ses.items()},
        })
    return {
        "rows": int(len(frame)), "counties": int(frame.county_geoid.nunique()),
        "states": int(frame.state.nunique()), "year_min": int(frame.harvest_year.min()),
        "year_max": int(frame.harvest_year.max()), "design_terms": names,
        "design_rank": int(np.linalg.matrix_rank(x)), "contrasts": contrasts,
    }


def run_synthetic(loader: Callable[[], pd.DataFrame]) -> dict[str, Any]:
    frame = loader()
    validate_synthetic_frame(frame)
    protocol = tomllib.loads(PROTOCOL.read_text(encoding="utf-8"))
    cutoffs = list(map(float, protocol["spatial_covariance"]["cutoffs_km"]))
    full = []
    leave_state = []
    terminal = []
    for practice in PRACTICES:
        practice_frame = frame.loc[frame.irrigation_practice.eq(practice)].copy()
        for family in FAMILIES:
            full.append({"practice": practice, "family": family, **fit_cell(practice_frame, family, cutoffs)})
            omissions = []
            for state in sorted(practice_frame.state.unique()):
                subset = practice_frame.loc[~practice_frame.state.eq(state)].copy()
                omissions.append({"omitted_state": state, **fit_cell(subset, family, cutoffs)})
            leave_state.append({"practice": practice, "family": family, "omissions": omissions})
            development = practice_frame.loc[practice_frame.harvest_year.between(1981, 2011)].copy()
            confirmation = practice_frame.loc[practice_frame.harvest_year.between(2012, 2018)].copy()
            terminal.append({
                "practice": practice, "family": family,
                "development": fit_cell(development, family, cutoffs),
                "terminal": fit_cell(confirmation, family, cutoffs),
            })
    return {
        "schema": "us_corn_quantity_pdsi_spatial_synthetic_executor_v1",
        "status": "completed_synthetic_only_post_authorization_plumbing",
        "protocol": {"path": str(PROTOCOL.relative_to(PROJECT)), "sha256": digest(PROTOCOL)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "source_role": "synthetic_fixture_only", "real_outcome_rows_read": 0,
        "real_response_fits": 0, "practices_pooled": False,
        "families_stacked": False, "spatial_cutoffs_km": cutoffs,
        "full_sample": full, "leave_one_state": leave_state,
        "terminal_validation": terminal,
        "national_claim_authorized": False, "causal_claim_authorized": False,
        "damage_claim_authorized": False, "scc_claim_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = run_synthetic(make_synthetic_fixture)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "full_cells": len(result["full_sample"]), "leave_state_blocks": len(result["leave_one_state"]), "terminal_blocks": len(result["terminal_validation"])}, indent=2))


if __name__ == "__main__":
    main()
