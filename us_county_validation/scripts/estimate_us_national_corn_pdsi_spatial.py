#!/usr/bin/env python3
"""Spatially robust U.S. corn PDSI associations on national rainfed-proxy support."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_corn_peeps_climate_yield_bridge import digest, load_coordinates, require
from estimate_us_national_all_practice_pdsi_association import (
    DEFAULT_CONFIG,
    alternating_residualize,
    design,
    load_config,
    project_path,
    sample_mask,
)
from us_corn_spatial_inference_primitives import (
    contrast_standard_error,
    county_cr1_meat,
    county_plus_spatial_covariance,
    influence_gate,
    terminal_stability_gate,
)


def fit(frame: pd.DataFrame, spatial: bool) -> dict[str, object]:
    state_year = frame.state.astype(str) + "_" + frame.harvest_year.astype(str)
    county, _ = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year_code, _ = pd.factorize(state_year, sort=True)
    raw, names = design(frame, "quadratic", 2000)
    transformed, iterations, change = alternating_residualize(
        np.column_stack([frame.log_yield.to_numpy(float), raw]),
        [county, state_year_code], 1e-10, 1000,
    )
    y, x = transformed[:, 0], transformed[:, 1:]
    gram = np.einsum("ni,nj->ij", x, x, optimize=False)
    require(np.linalg.matrix_rank(gram) == len(names), "residualized design is rank deficient")
    bread = np.linalg.inv(gram)
    beta = np.linalg.solve(gram, np.einsum("ni,n->i", x, y, optimize=False))
    residual = y - np.einsum("ij,j->i", x, beta, optimize=False)
    covariances = {"county_cr1": bread @ county_cr1_meat(x, residual, frame.county_geoid.to_numpy()) @ bread}
    if spatial:
        for cutoff in (250.0, 500.0):
            covariances[f"spatial_{int(cutoff)}km"] = county_plus_spatial_covariance(
                x, residual, frame.county_geoid.to_numpy(), frame.harvest_year.to_numpy(),
                frame.latitude.to_numpy(float), frame.longitude.to_numpy(float), cutoff,
            )
    return {"beta": beta, "covariances": covariances, "iterations": iterations, "change": change,
            "rows": len(frame), "counties": frame.county_geoid.nunique(), "states": frame.state.nunique()}


def contrast(start: float, end: float) -> np.ndarray:
    """Quadratic design change f(end)-f(start)."""
    return np.array([end - start, end**2 - start**2], dtype=float)


def summarize(fitted: dict[str, object], vector: np.ndarray) -> dict[str, object]:
    beta = np.asarray(fitted["beta"], dtype=float)
    estimate = float(vector @ beta)
    ses = {name: contrast_standard_error(np.asarray(cov), vector) for name, cov in fitted["covariances"].items()}
    return {
        "estimate_log_yield": estimate,
        "estimate_percent_yield": 100.0 * np.expm1(estimate),
        "standard_errors_log_yield": ses,
        "normal_95_intervals_percent_yield": {
            name: [100.0 * np.expm1(estimate - 1.96 * se), 100.0 * np.expm1(estimate + 1.96 * se)]
            for name, se in ses.items()
        },
        "spatially_robust_excludes_zero": spatial_excludes_zero(estimate, ses),
    }


def spatial_excludes_zero(estimate: float, standard_errors: dict[str, float]) -> bool:
    required = {"county_cr1", "spatial_250km", "spatial_500km"}
    if not required.issubset(standard_errors):
        return False
    return all((estimate - 1.96 * standard_errors[name]) * (estimate + 1.96 * standard_errors[name]) > 0 for name in required)


def load_primary(config: dict[str, object]) -> tuple[pd.DataFrame, dict[str, object]]:
    """Read only the corn/season columns and rows needed by this bounded job."""
    inputs = config["input"]
    path = project_path(inputs["joined_panel"])
    receipt_path = project_path(inputs["public_receipt"])
    receipt = json.loads(receipt_path.read_text())
    joined = receipt.get("files", {}).get("joined", {})
    require(joined.get("sha256") == digest(path), "joined PDSI panel differs from public receipt")
    columns = ["county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice",
               "yield_bu_acre", "irrigation_share_vintage", "rainfed_dominant_10pct",
               "outcome_source_id", "response_estimation_authorized", "scc_authorized",
               "calendar_role", "window_id", "index_source_id", "response_estimation_authorized_pdsi",
               "scc_authorized_pdsi", inputs["pdsi_feature"] if "pdsi_feature" in inputs else config["models"]["pdsi_feature"]]
    frame = pd.read_parquet(path, columns=list(dict.fromkeys(columns)), filters=[
        ("outcome_crop", "==", "corn_grain"), ("window_id", "==", inputs["window_id"]),
        ("irrigation_practice", "==", inputs["practice"]),
    ])
    frame = frame.loc[
        frame.calendar_role.astype(str).eq(str(inputs["calendar_role"]))
        & frame.harvest_year.between(int(inputs["year_min"]), int(inputs["year_max"]))
    ].copy()
    require(set(frame.outcome_source_id.astype(str)) == {str(inputs["outcome_source_id"])}, "outcome source changed")
    require(set(frame.index_source_id.astype(str)) == {str(inputs["index_source_id"])}, "PDSI source changed")
    require(set(pd.to_numeric(frame.irrigation_share_vintage, errors="raise")) == {int(config["samples"]["irrigation_share_vintage"])}, "irrigation vintage changed")
    for gate in ("response_estimation_authorized", "scc_authorized", "response_estimation_authorized_pdsi", "scc_authorized_pdsi"):
        require(not frame[gate].fillna(True).astype(bool).any(), f"upstream data unexpectedly opens {gate}")
    frame["yield"] = pd.to_numeric(frame.yield_bu_acre, errors="raise")
    frame["pdsi"] = pd.to_numeric(frame[config["models"]["pdsi_feature"]], errors="raise")
    require((frame["yield"] > 0).all() and np.isfinite(frame[["yield", "pdsi"]]).all().all(), "yield/PDSI invalid")
    frame["log_yield"] = np.log(frame["yield"])
    return frame, {"path": inputs["joined_panel"], "sha256": digest(path), "rows_read": len(frame)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--coordinate-dbf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "fresh output required")
    config = load_config(args.config.resolve())
    frame, input_record = load_primary(config)
    frame = frame.loc[sample_mask(frame, "rainfed_dominant_10pct")].copy()
    frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5)
    frame = frame.merge(load_coordinates(args.coordinate_dbf), on="county_geoid", validate="many_to_one")
    require(len(frame) == 15660 and frame.county_geoid.nunique() == 424 and frame.state.nunique() == 28, "primary national corn support differs")

    full = fit(frame, spatial=True)
    targets = {"pdsi_minus1_vs_0": contrast(0, -1), "pdsi_minus2_vs_0": contrast(0, -2), "pdsi_minus4_vs_0": contrast(0, -4)}
    summaries = {name: summarize(full, vector) for name, vector in targets.items()}

    primary_vector = targets["pdsi_minus2_vs_0"]
    full_primary = summaries["pdsi_minus2_vs_0"]
    full_se = full_primary["standard_errors_log_yield"]["county_cr1"]
    omissions = []
    for state in sorted(frame.state.unique()):
        omitted = fit(frame.loc[frame.state.ne(state)], spatial=False)
        estimate = float(primary_vector @ np.asarray(omitted["beta"]))
        omissions.append({"omitted_state": state, "estimate_log_yield": estimate,
                          "estimate_percent_yield": 100.0 * np.expm1(estimate),
                          "rows": omitted["rows"], "counties": omitted["counties"]})
    influence = influence_gate(full_primary["estimate_log_yield"], full_se,
                               np.array([item["estimate_log_yield"] for item in omissions]), 1.0)

    development = fit(frame.loc[frame.harvest_year.between(1981, 2011)], spatial=False)
    terminal = fit(frame.loc[frame.harvest_year.between(2012, 2019)], spatial=False)
    split = {}
    for label, fitted in (("development_1981_2011", development), ("terminal_2012_2019", terminal)):
        split[label] = summarize(fitted, primary_vector)
        split[label].update({"rows": fitted["rows"], "counties": fitted["counties"], "states": fitted["states"]})
    stability = terminal_stability_gate(
        split["development_1981_2011"]["estimate_log_yield"], split["development_1981_2011"]["standard_errors_log_yield"]["county_cr1"],
        split["terminal_2012_2019"]["estimate_log_yield"], split["terminal_2012_2019"]["standard_errors_log_yield"]["county_cr1"], 1.96,
    )

    result = {
        "schema": "us_national_corn_pdsi_spatial/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "spatially_robust_historical_all_practice_rainfed_proxy_association_not_climate_attribution_damage_or_scc",
        "definition": "National NASS all-practice corn yield in counties with 2017 irrigated share <=10%, associated with growing-season NOAA nClimDiv PDSI using county and state-year fixed effects.",
        "sources": {"panel": input_record, "config": {"path": str(args.config), "sha256": digest(args.config)}, "coordinates": {"path": str(args.coordinate_dbf), "sha256": digest(args.coordinate_dbf)}},
        "support": {"rows": len(frame), "counties": int(frame.county_geoid.nunique()), "states": int(frame.state.nunique()), "years": [1981, 2019]},
        "contrasts": summaries,
        "leave_state_out": {"target": "pdsi_minus2_vs_0", "gate": influence, "records": omissions},
        "temporal_stability": {"target": "pdsi_minus2_vs_0", "gate": stability, "splits": split},
        "validation": {"finite_outputs": True, "spatial_cutoffs_km": [250, 500], "frozen_primary_coefficient_reproduced": abs(float(np.asarray(full["beta"])[0]) - 0.032065262249988485) <= 1e-12},
        "claim_gates": {"historical_association": True, "national_rainfed_yield_effect": False, "precipitation_attribution": False, "future_climate_attribution": False, "damage": False, "scc": False},
        "limitations": ["All-practice yield in low-irrigation counties is a rainfed proxy, not directly reported non-irrigated yield.", "PDSI combines precipitation supply and temperature-driven atmospheric demand.", "The fixed 2017 irrigation selector is applied retrospectively.", "No projected PDSI response to marginal warming is supplied by this analysis."],
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())},
    }
    require(result["validation"]["frozen_primary_coefficient_reproduced"], "frozen primary coefficient not reproduced")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "support": result["support"], "contrasts": summaries,
                      "leave_state_gate": influence, "temporal_gate": stability}, indent=2))


if __name__ == "__main__":
    main()
