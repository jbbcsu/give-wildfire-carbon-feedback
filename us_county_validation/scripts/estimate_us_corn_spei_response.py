#!/usr/bin/env python3
"""Estimate the frozen U.S. corn SPEI association and climate-only transport."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import shapefile

from estimate_us_national_all_practice_pdsi_association import alternating_residualize, clustered_ols
from us_corn_spatial_inference_primitives import county_plus_spatial_covariance, contrast_standard_error

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config/us_corn_spei_response_v1.toml"
KEYS = ["county_geoid", "state", "harvest_year"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() and path.exists():
        return path
    if path.is_absolute() and "data" in path.parts:
        relocated = ROOT / Path(*path.parts[path.parts.index("data"):])
        if relocated.exists():
            return relocated
    return path if path.is_absolute() else ROOT / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def coordinates(path: Path) -> pd.DataFrame:
    reader = shapefile.Reader(dbf=str(path))
    fields = [field[0] for field in reader.fields[1:]]
    positions = [fields.index(name) for name in ("GEOID", "INTPTLAT", "INTPTLON")]
    rows = [(str(record[positions[0]]).zfill(5), float(record[positions[1]]), float(record[positions[2]]))
            for record in reader.iterRecords()]
    frame = pd.DataFrame(rows, columns=["county_geoid", "latitude", "longitude"])
    require(not frame.county_geoid.duplicated().any(), "coordinate keys are not unique")
    return frame


def load(config_path: Path) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    cfg = tomllib.loads(config_path.read_text())
    require(cfg["analysis_id"] == "us_corn_spei_response_v1", "contract identity changed")
    require(cfg["response_fit_authorized"] and cfg["future_climate_transport_authorized"], "run not authorized")
    require(not any(cfg[name] for name in ("causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized")),
            "downstream claim gate unexpectedly open")
    for name in ("direct_panel", "historical_spei", "future_spei", "climate_result", "climate_validation"):
        path = resolve(cfg["inputs"][name])
        require(digest(path) == cfg["inputs"][f"{name}_sha256"], f"input hash changed: {name}")
    validation = json.loads(resolve(cfg["inputs"]["climate_validation"]).read_text())
    require(validation["status"] == "passed" and validation["validated"]["future_cases"] == 15,
            "climate panels lack independent validation")
    coordinate_path = resolve(cfg["coordinates"]["dbf"])
    require(digest(coordinate_path) == cfg["coordinates"]["dbf_sha256"], "coordinate hash changed")
    sample = cfg["sample"]
    columns = KEYS + ["outcome_crop", "irrigation_practice", "yield_bu_acre",
                      "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"]
    direct = pd.read_parquet(resolve(cfg["inputs"]["direct_panel"]), columns=columns)
    direct = direct.loc[
        direct.outcome_crop.eq(sample["crop"]) & direct.irrigation_practice.eq(sample["practice"])
        & direct.harvest_year.between(sample["year_min"], sample["year_max"])
    ].copy()
    historical = pd.read_parquet(resolve(cfg["inputs"]["historical_spei"]))
    historical = historical.rename(columns={"crop": "outcome_crop", "practice": "irrigation_practice"})
    require(not direct.duplicated(KEYS).any() and not historical.duplicated(KEYS).any(), "analysis keys not unique")
    features = cfg["models"]["spei_features"]
    panel = direct.merge(historical[KEYS + features], on=KEYS, how="inner", validate="one_to_one")
    panel["county_geoid"] = panel.county_geoid.astype(str).str.zfill(5)
    panel = panel.merge(coordinates(coordinate_path), on="county_geoid", how="left", validate="many_to_one")
    require(len(panel) == sample["expected_rows"] and panel.county_geoid.nunique() == sample["expected_counties"],
            "exact response support changed")
    required = ["yield_bu_acre", "latitude", "longitude", *cfg["models"]["heat_controls"], *features]
    require(np.isfinite(panel[required].to_numpy(float)).all() and (panel.yield_bu_acre > 0).all(),
            "response panel contains invalid values")
    panel["log_yield"] = np.log(panel.yield_bu_acre.to_numpy(float))
    future = pd.read_parquet(resolve(cfg["inputs"]["future_spei"]))
    require(len(future) == 43200 and future.county_geoid.nunique() == sample["expected_counties"],
            "future climate support changed")
    return cfg, panel, future


def design(frame: pd.DataFrame, feature: str, cfg: dict) -> tuple[np.ndarray, list[str]]:
    vectors, names = [], []
    for name in cfg["models"]["heat_controls"]:
        value = frame[name].to_numpy(float)
        vectors.extend([value, value**2]); names.extend([name, f"{name}_squared"])
    value = frame[feature].to_numpy(float)
    vectors.extend([value, value**2]); names.extend([feature, f"{feature}_squared"])
    return np.column_stack(vectors), names


def fit(frame: pd.DataFrame, feature: str, cfg: dict, spatial: bool = False) -> dict:
    x_raw, names = design(frame, feature, cfg)
    county, _ = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year, _ = pd.factorize(frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True)
    transformed, iterations, change = alternating_residualize(
        np.column_stack([frame.log_yield.to_numpy(float), x_raw]), [county, state_year],
        float(cfg["models"]["demeaning_tolerance"]), int(cfg["models"]["demeaning_max_iterations"]),
    )
    y, x = transformed[:, 0], transformed[:, 1:]
    require(np.linalg.matrix_rank(x) == x.shape[1], "residualized design rank deficient")
    result = clustered_ols(y, x, frame.county_geoid.to_numpy())
    beta = np.asarray(result["beta"], float); covariance = np.asarray(result["covariance_beta_cluster_county"], float)
    residual = y - x @ beta
    spatial_covariances = {}
    if spatial:
        for cutoff in cfg["coordinates"]["spatial_cutoffs_km"]:
            spatial_covariances[f"spatial_{int(cutoff)}km"] = county_plus_spatial_covariance(
                x, residual, frame.county_geoid.to_numpy(), frame.harvest_year.to_numpy(),
                frame.latitude.to_numpy(float), frame.longitude.to_numpy(float), float(cutoff))
    contrasts = []
    for quantile in cfg["models"]["contrast_reference_quantiles"]:
        reference = float(frame[feature].quantile(quantile)); change_value = float(cfg["models"]["contrast_change"])
        vector = np.zeros(len(names)); vector[names.index(feature)] = change_value
        vector[names.index(f"{feature}_squared")] = (reference + change_value) ** 2 - reference**2
        estimate = float(vector @ beta); se = float(np.sqrt(max(vector @ covariance @ vector, 0)))
        standard_errors = {"county_cr1": se}
        standard_errors.update({name: contrast_standard_error(value, vector)
                                for name, value in spatial_covariances.items()})
        contrasts.append({"reference_quantile": quantile, "reference_value": reference, "change": change_value,
                          "estimate_log_yield": estimate, "standard_errors_log_yield": standard_errors,
                          "estimate_percent_yield": 100 * math.expm1(estimate),
                          "ci95_percent_yield": {name: [100 * math.expm1(estimate - 1.96 * value),
                                                        100 * math.expm1(estimate + 1.96 * value)]
                                                       for name, value in standard_errors.items()}})
    return {"rows": len(frame), "counties": int(frame.county_geoid.nunique()),
            "years": [int(frame.harvest_year.min()), int(frame.harvest_year.max())],
            "demeaning_iterations": iterations, "demeaning_final_change": change,
            "within_r_squared": float(result["within_r_squared"]), "terms": names,
            "beta": beta.tolist(), "covariance_cluster_county": covariance.tolist(), "contrasts": contrasts}


def transport(panel: pd.DataFrame, future: pd.DataFrame, feature: str, fitted: dict) -> list[dict]:
    historical = panel.groupby("county_geoid", observed=True)[feature].mean()
    beta = np.asarray(fitted["beta"], float); names = fitted["terms"]
    linear, square = names.index(feature), names.index(f"{feature}_squared")
    rows = []
    for keys, group in future.groupby(["model", "scenario"], observed=True):
        projected = group.groupby("county_geoid", observed=True)[feature].mean()
        aligned = pd.concat([historical.rename("baseline"), projected.rename("future")], axis=1).dropna()
        delta = beta[linear] * (aligned.future - aligned.baseline) + beta[square] * (aligned.future**2 - aligned.baseline**2)
        rows.append({"model": keys[0], "scenario": keys[1], "counties": len(aligned),
                     "equal_county_mean_log_yield_change": float(delta.mean()),
                     "equal_county_mean_percent_yield_change": float((100 * np.expm1(delta)).mean()),
                     "county_percent_yield_change_p05_p50_p95": [float(v) for v in np.quantile(100 * np.expm1(delta), [.05, .5, .95])]})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); cfg, panel, future = load(args.config.resolve())
    estimates = []
    for feature in cfg["models"]["spei_features"]:
        full = fit(panel, feature, cfg, spatial=True)
        development = fit(panel.loc[panel.harvest_year.le(cfg["sample"]["development_year_max"])], feature, cfg)
        terminal = fit(panel.loc[panel.harvest_year.between(cfg["sample"]["terminal_year_min"], cfg["sample"]["terminal_year_max"])], feature, cfg)
        reference = full["contrasts"][1]["estimate_log_yield"]
        omissions = []
        for state in sorted(panel.state.unique()):
            omitted = fit(panel.loc[~panel.state.eq(state)], feature, cfg)
            estimate = omitted["contrasts"][1]["estimate_log_yield"]
            omissions.append({"state": state, "estimate_log_yield": estimate,
                              "same_sign_as_full": bool(estimate * reference > 0)})
        estimates.append({"feature": feature, "primary": feature == cfg["models"]["primary_feature"],
                          "full": full, "development": development, "terminal": terminal,
                          "leave_one_state_out_median_contrast": omissions,
                          "future_climate_transport": transport(panel, future, feature, full)})
    output = {"schema": "us_corn_spei_response_result_v1", "status": "completed_historical_association_and_climate_transport",
              "claim_boundary": "historical association and mechanical climate-index transport; not causal damage or SCC",
              "config": {"path": str(args.config.resolve().relative_to(ROOT)), "sha256": digest(args.config.resolve())},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__))},
              "support": {"rows": len(panel), "counties": int(panel.county_geoid.nunique()), "future_cases": 15},
              "estimates": estimates,
              "gates": {"historical_association": True, "future_climate_transport": True, "causal_claim": False,
                        "damage": False, "scc": False}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    require(not args.output.exists(), "fresh output required")
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "features": len(estimates), "rows": len(panel)}))


if __name__ == "__main__":
    main()
