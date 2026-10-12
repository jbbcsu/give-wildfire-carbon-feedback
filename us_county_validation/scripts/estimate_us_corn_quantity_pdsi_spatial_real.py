#!/usr/bin/env python3
"""Run the authorized U.S. corn quantity/PDSI spatial association design."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shapefile

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_us_corn_quantity_pdsi_spatial_synthetic_executor import design, residualize  # noqa: E402
from us_corn_spatial_inference_primitives import (  # noqa: E402
    contrast_standard_error,
    county_cr1_meat,
    county_plus_spatial_covariance,
    influence_gate,
    terminal_stability_gate,
)

DEFAULT_CONFIG = PROJECT / "us_county_validation/us_corn_quantity_pdsi_spatial_real_v1.toml"
DEFAULT_AUTHORIZATION = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_real_authorization_20261012.json"
KEYS = ["county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice"]
FAMILIES = ("quantity", "pdsi")
PRACTICES = ("non_irrigated", "irrigated")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def project_path(value: str) -> Path:
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, "paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def validate_authorization(config: dict[str, Any], authorization_path: Path) -> dict[str, Any]:
    require(config["real_outcome_read_authorized"] is True, "outcome read not authorized")
    require(config["real_response_fit_authorized"] is True, "response fit not authorized")
    require(config["target_contrast_output_authorized"] is True, "target contrast output not authorized")
    for gate in ("raw_coefficient_output_authorized", "national_claim_authorized", "causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized"):
        require(config[gate] is False, f"claim/output gate unexpectedly opened: {gate}")
    authorization = json.loads(authorization_path.read_text())
    require(authorization["status"] == "explicitly_authorized_for_one_bound_run", "authorization status differs")
    require(authorization["scope"] == "us_corn_quantity_pdsi_spatial_v1_real_outcome_fit", "authorization scope differs")
    expected = {
        "protocol_sha256": config["protocol"]["sha256"],
        "direct_sha256": config["direct"]["sha256"],
        "pdsi_sha256": config["pdsi"]["sha256"],
        "coordinate_archive_sha256": config["coordinates"]["archive_sha256"],
    }
    require(authorization["bound_hashes"] == expected, "authorization input hashes differ")
    return authorization


def coordinates(path: Path) -> pd.DataFrame:
    reader = shapefile.Reader(dbf=str(path))
    fields = [field[0] for field in reader.fields[1:]]
    needed = [fields.index(name) for name in ("GEOID", "INTPTLAT", "INTPTLON")]
    rows = []
    for record in reader.iterRecords():
        rows.append((str(record[needed[0]]).zfill(5), float(record[needed[1]]), float(record[needed[2]])))
    result = pd.DataFrame(rows, columns=["county_geoid", "latitude", "longitude"])
    require(len(result) == 3233 and not result.county_geoid.duplicated().any(), "coordinate support differs")
    return result


def load_panel(config: dict[str, Any]) -> pd.DataFrame:
    direct_path, pdsi_path = project_path(config["direct"]["path"]), project_path(config["pdsi"]["path"])
    require(digest(direct_path) == config["direct"]["sha256"], "direct input hash differs")
    require(digest(pdsi_path) == config["pdsi"]["sha256"], "PDSI input hash differs")
    require(digest(project_path(config["coordinates"]["archive"])) == config["coordinates"]["archive_sha256"], "coordinate archive hash differs")
    columns = KEYS + ["yield_bu_acre", "precip_mm", "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"]
    direct = pd.read_parquet(direct_path, columns=columns)
    sample = config["sample"]
    direct = direct.loc[
        direct.outcome_crop.eq(sample["crop"])
        & direct.harvest_year.between(sample["year_min"], sample["year_max"])
        & direct.irrigation_practice.isin(sample["practices"])
    ].copy()
    pdsi_columns = KEYS + ["yield_bu_acre", "calendar_role", "window_id", "index_day_weighted_mean"]
    moisture = pd.read_parquet(pdsi_path, columns=pdsi_columns)
    moisture = moisture.loc[
        moisture.outcome_crop.eq(sample["crop"])
        & moisture.harvest_year.between(sample["year_min"], sample["year_max"])
        & moisture.irrigation_practice.isin(sample["practices"])
        & moisture.calendar_role.eq(config["pdsi"]["calendar_role"])
        & moisture.window_id.eq(config["pdsi"]["window_id"])
    ].copy()
    require(not direct.duplicated(KEYS).any() and not moisture.duplicated(KEYS).any(), "input keys are not unique")
    panel = direct.merge(
        moisture[KEYS + ["yield_bu_acre", "index_day_weighted_mean"]],
        on=KEYS, how="inner", validate="one_to_one", suffixes=("", "_pdsi"),
    )
    require(len(panel) == len(direct) == len(moisture), "direct/PDSI support differs")
    require(np.array_equal(panel.yield_bu_acre.to_numpy(), panel.yield_bu_acre_pdsi.to_numpy()), "yield values differ across inputs")
    panel = panel.drop(columns="yield_bu_acre_pdsi").rename(columns={"index_day_weighted_mean": "pdsi_season_mean"})
    panel["county_geoid"] = panel.county_geoid.astype(str).str.zfill(5)
    panel = panel.merge(coordinates(project_path(config["coordinates"]["dbf"])), on="county_geoid", how="left", validate="many_to_one")
    required = ["yield_bu_acre", "precip_mm", "pdsi_season_mean", "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c", "latitude", "longitude"]
    require(panel[required].notna().all().all(), "analysis panel contains missing required values")
    require((panel.yield_bu_acre > 0).all(), "yield must be positive")
    require(set(panel.irrigation_practice) == set(PRACTICES), "practice support differs")
    pair_keys = ["county_geoid", "harvest_year"]
    grouped = panel.groupby(pair_keys, observed=True)
    require(grouped.irrigation_practice.agg(set).map(lambda value: value == set(PRACTICES)).all(), "practice pairs differ")
    for column in ["state", "precip_mm", "pdsi_season_mean", "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c", "latitude", "longitude"]:
        require(grouped[column].nunique(dropna=False).eq(1).all(), f"paired exposure differs: {column}")
    panel["log_yield_bu_acre"] = np.log(panel.yield_bu_acre.to_numpy(float))
    return panel.sort_values(["irrigation_practice", "county_geoid", "harvest_year"]).reset_index(drop=True)


def frozen_targets(frame: pd.DataFrame, family: str, names: list[str]) -> list[dict[str, Any]]:
    feature = "precip_mm" if family == "quantity" else "pdsi_season_mean"
    result = []
    for quantile in (0.25, 0.50, 0.75):
        reference = float(frame[feature].quantile(quantile))
        vector = np.zeros(len(names), dtype=float)
        if family == "quantity":
            scaled = reference / 100.0
            vector[names.index("precipitation_per_100mm")] = 1.0
            vector[names.index("precipitation_per_100mm_squared")] = (scaled + 1.0) ** 2 - scaled**2
            change = 100.0
        else:
            vector[names.index("pdsi_season_mean")] = -1.0
            vector[names.index("pdsi_season_mean_squared")] = (reference - 1.0) ** 2 - reference**2
            change = -1.0
        result.append({"reference_quantile": quantile, "reference_value": reference, "change": change, "vector": vector})
    return result


def fit(frame: pd.DataFrame, family: str, targets: list[dict[str, Any]] | None, cutoffs: list[float]) -> dict[str, Any]:
    raw_x, names = design(frame, family)
    county, _ = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year, _ = pd.factorize(frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True)
    transformed = residualize(np.column_stack([frame.log_yield_bu_acre.to_numpy(float), raw_x]), [county, state_year])
    y, x = transformed[:, 0], transformed[:, 1:]
    require(np.linalg.matrix_rank(x) == x.shape[1], "residualized design is rank deficient")
    gram = np.einsum("ni,nj->ij", x, x, optimize=False)
    beta = np.linalg.solve(gram, np.einsum("ni,n->i", x, y, optimize=False))
    error = y - np.einsum("ni,i->n", x, beta, optimize=False)
    bread = np.linalg.inv(gram)
    county_covariance = bread @ county_cr1_meat(x, error, frame.county_geoid.to_numpy()) @ bread
    spatial = {
        f"spatial_{int(cutoff)}km": county_plus_spatial_covariance(
            x, error, frame.county_geoid.to_numpy(), frame.harvest_year.to_numpy(),
            frame.latitude.to_numpy(float), frame.longitude.to_numpy(float), cutoff,
        )
        for cutoff in cutoffs
    }
    selected_targets = frozen_targets(frame, family, names) if targets is None else targets
    contrasts = []
    for target in selected_targets:
        vector = np.asarray(target["vector"], dtype=float)
        estimate = float(vector @ beta)
        ses = {"county_cr1": contrast_standard_error(county_covariance, vector)}
        ses.update({name: contrast_standard_error(covariance, vector) for name, covariance in spatial.items()})
        intervals = {name: [estimate - 1.96 * se, estimate + 1.96 * se] for name, se in ses.items()}
        contrasts.append({
            "reference_quantile": target["reference_quantile"], "reference_value": target["reference_value"],
            "change": target["change"], "estimate_log_yield": estimate,
            "estimate_percent_yield": 100.0 * np.expm1(estimate), "standard_errors_log_yield": ses,
            "normal_95_intervals_log_yield": intervals,
            "normal_95_intervals_percent_yield": {name: [100.0 * np.expm1(bounds[0]), 100.0 * np.expm1(bounds[1])] for name, bounds in intervals.items()},
            "spatially_robust_excludes_zero": all(bounds[0] * bounds[1] > 0 for bounds in intervals.values()),
        })
    return {
        "rows": len(frame), "counties": int(frame.county_geoid.nunique()), "states": int(frame.state.nunique()),
        "year_min": int(frame.harvest_year.min()), "year_max": int(frame.harvest_year.max()),
        "design_rank": int(np.linalg.matrix_rank(x)), "design_terms": names, "contrasts": contrasts,
        "targets_internal": selected_targets,
    }


def public_fit(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "targets_internal"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authorization", type=Path, default=DEFAULT_AUTHORIZATION)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    config_path, authorization_path = args.config.resolve(), args.authorization.resolve()
    config = tomllib.loads(config_path.read_text())
    authorization = validate_authorization(config, authorization_path)
    for section in ("protocol", "readiness"):
        require(digest(project_path(config[section]["path"] if section == "protocol" else config[section]["receipt"])) == config[section]["sha256"], f"{section} hash differs")
    require(digest(project_path(config["protocol"]["validation_receipt"])) == config["protocol"]["validation_sha256"], "protocol validation hash differs")
    panel = load_panel(config)
    cutoffs = [250.0, 500.0]
    full_results, state_results, temporal_results, influence_results = [], [], [], []
    for practice in PRACTICES:
        practice_frame = panel.loc[panel.irrigation_practice.eq(practice)].copy()
        for family in FAMILIES:
            full = fit(practice_frame, family, None, cutoffs)
            targets = full["targets_internal"]
            omissions = []
            omission_fits = []
            for state in sorted(practice_frame.state.unique()):
                subset = practice_frame.loc[~practice_frame.state.eq(state)].copy()
                fitted = fit(subset, family, targets, [])
                omissions.append({"omitted_state": state, **public_fit(fitted)})
                omission_fits.append(fitted)
            state_gates = []
            for index, contrast in enumerate(full["contrasts"]):
                estimates = np.asarray([item["contrasts"][index]["estimate_log_yield"] for item in omission_fits])
                state_gates.append({"reference_quantile": contrast["reference_quantile"], **influence_gate(contrast["estimate_log_yield"], contrast["standard_errors_log_yield"]["county_cr1"], estimates, 1.0)})
            development = fit(practice_frame.loc[practice_frame.harvest_year.le(2011)].copy(), family, targets, [])
            terminal = fit(practice_frame.loc[practice_frame.harvest_year.between(2012, 2018)].copy(), family, targets, [])
            temporal_gates = []
            for index in range(3):
                left, right = development["contrasts"][index], terminal["contrasts"][index]
                temporal_gates.append({"reference_quantile": left["reference_quantile"], **terminal_stability_gate(left["estimate_log_yield"], left["standard_errors_log_yield"]["county_cr1"], right["estimate_log_yield"], right["standard_errors_log_yield"]["county_cr1"], 1.96)})
            leave_row_frame = practice_frame.loc[~(practice_frame.county_geoid.eq("48277") & practice_frame.harvest_year.eq(2011))].copy()
            leave_county_frame = practice_frame.loc[~practice_frame.county_geoid.eq("48277")].copy()
            leave_row, leave_county = fit(leave_row_frame, family, targets, []), fit(leave_county_frame, family, targets, [])
            influence = []
            for index, contrast in enumerate(full["contrasts"]):
                se = contrast["standard_errors_log_yield"]["county_cr1"]
                row_change = abs(leave_row["contrasts"][index]["estimate_log_yield"] - contrast["estimate_log_yield"]) / se
                county_change = abs(leave_county["contrasts"][index]["estimate_log_yield"] - contrast["estimate_log_yield"]) / se
                influence.append({"reference_quantile": contrast["reference_quantile"], "leave_row_absolute_dfbeta": row_change, "leave_row_pass": row_change <= 0.5, "leave_county_absolute_dfbeta": county_change, "leave_county_pass": county_change <= 0.75})
            full_results.append({"practice": practice, "family": family, **public_fit(full)})
            state_results.append({"practice": practice, "family": family, "gates": state_gates, "omissions": omissions})
            temporal_results.append({"practice": practice, "family": family, "gates": temporal_gates, "development": public_fit(development), "terminal": public_fit(terminal)})
            influence_results.append({"practice": practice, "family": family, "diagnostics": influence, "leave_row": public_fit(leave_row), "leave_county": public_fit(leave_county)})
    result = {
        "schema": "us_corn_quantity_pdsi_spatial_real_v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_authorized_selected_sample_historical_association",
        "definition": "separate irrigated and non-irrigated corn associations for mutually exclusive rainfall-quantity and seasonal-PDSI families with county and state-year fixed effects",
        "authorization": {"path": str(authorization_path.relative_to(PROJECT)), "sha256": digest(authorization_path), "claim_boundary": authorization["claim_boundary"]},
        "sources": {"config": {"path": str(config_path.relative_to(PROJECT)), "sha256": digest(config_path)}, "direct": config["direct"], "pdsi": config["pdsi"], "coordinate_archive": config["coordinates"]},
        "support": {"rows": len(panel), "paired_exposures": len(panel) // 2, "counties": int(panel.county_geoid.nunique()), "states": int(panel.state.nunique()), "years": [int(panel.harvest_year.min()), int(panel.harvest_year.max())]},
        "full_sample": full_results, "leave_one_state": state_results, "temporal_validation": temporal_results, "preidentified_influence": influence_results,
        "claim_gates": {"historical_association": True, "national_effect": False, "causal_effect": False, "climate_attribution": False, "damage": False, "scc": False},
        "limitations": ["NASS reported-practice counties are a selected sample, not a nationally representative field panel.", "Associations can retain omitted management, soil, measurement, and spatial confounding.", "PDSI and direct precipitation are competing moisture representations and are not stacked.", "The result contains no future climate attribution, production aggregation, welfare mapping, or SCC calculation."],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
    }
    output = args.output.resolve() if args.output else project_path(config["output"]["result"])
    receipt = args.receipt.resolve() if args.receipt else project_path(config["output"]["receipt"])
    require(not output.exists() and not receipt.exists(), "fresh outputs required")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    medians = [{"practice": item["practice"], "family": item["family"], **next(value for value in item["contrasts"] if value["reference_quantile"] == 0.5)} for item in full_results]
    provenance = {
        "schema": "us_corn_quantity_pdsi_spatial_real_receipt/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": result["status"], "result": {"path": str(output.relative_to(PROJECT)), "bytes": output.stat().st_size, "sha256": digest(output)},
        "central_full_sample_contrasts": medians, "support": result["support"], "claim_gates": result["claim_gates"],
        "sources": result["sources"], "authorization": result["authorization"], "implementation": result["implementation"],
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "support": result["support"], "central_full_sample_contrasts": medians, "output": provenance["result"]}, indent=2))


if __name__ == "__main__":
    main()
