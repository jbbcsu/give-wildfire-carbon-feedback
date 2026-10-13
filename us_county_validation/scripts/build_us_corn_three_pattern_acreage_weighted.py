#!/usr/bin/env python3
"""Acreage-weight the frozen U.S. corn three-pattern transport diagnostic."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_corn_peeps_climate_yield_bridge import (
    digest,
    fit_quantity,
    load_coordinates,
    month_overlap_days,
    peeps_slopes,
    require,
    summarize,
)
from build_us_corn_three_pattern_sensitivity import fitted_pattern


def acreage_weighted_vector(frame: pd.DataFrame, weight: str) -> np.ndarray:
    """Average annual contrast within county, then weight counties by fixed acres."""
    columns = [f"contrast_{index}" for index in range(8)]
    county = frame.groupby("county_geoid", as_index=False)[columns].mean()
    weights = frame[["county_geoid", weight]].drop_duplicates("county_geoid")
    county = county.merge(weights, on="county_geoid", validate="one_to_one")
    require(county[weight].notna().all() and county[weight].ge(0).all(), "invalid acreage weights")
    require(float(county[weight].sum()) > 0, "zero acreage support")
    return np.average(county[columns].to_numpy(float), axis=0, weights=county[weight].to_numpy(float))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--acreage", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.state_output.exists() and not args.receipt.exists(), "fresh outputs required")

    source = json.loads(args.source_receipt.read_text())
    require(source["schema"] == "us_corn_three_pattern_sensitivity/v1", "source receipt differs")
    paths = source["sources"]
    panel_path = Path(paths["panel"]["path"])
    coordinate_path = Path(paths["coordinates"]["path"])
    require(digest(panel_path) == paths["panel"]["sha256"], "panel hash differs")
    require(digest(coordinate_path) == paths["coordinates"]["sha256"], "coordinate hash differs")

    columns = ["county_geoid", "state", "harvest_year", "irrigation_practice", "outcome_crop",
               "yield_bu_acre", "precip_mm", "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c",
               "season_start", "season_end"]
    full_panel = pd.read_parquet(panel_path, columns=columns)
    full_panel = full_panel.loc[full_panel.outcome_crop.eq("corn_grain") & full_panel.harvest_year.between(1981, 2018)].copy()
    full_panel["county_geoid"] = full_panel.county_geoid.astype(str).str.zfill(5)
    full_panel = full_panel.merge(load_coordinates(coordinate_path), on="county_geoid", validate="many_to_one")
    require(len(full_panel) == 14026 and full_panel.county_geoid.nunique() == 361, "U.S. support differs")

    responses = {}
    frozen_response = json.loads(Path(paths["us_response"]["receipt"]).read_text())
    for practice in ("non_irrigated", "irrigated"):
        frame = full_panel.loc[full_panel.irrigation_practice.eq(practice)].sort_values(["county_geoid", "harvest_year"])
        beta, covariance, median_contrast = fit_quantity(frame)
        frozen = next(item for item in frozen_response["central_full_sample_contrasts"] if item["practice"] == practice and item["family"] == "quantity")
        require(abs(median_contrast - frozen["estimate_log_yield"]) <= 1e-13, "frozen U.S. response not reproduced")
        responses[practice] = beta, covariance

    acres = pd.read_csv(args.acreage, dtype={"county_geoid": str})
    acres["county_geoid"] = acres.county_geoid.str.zfill(5)
    acres = acres.loc[acres.crop.eq("corn") & acres.share_eligible.eq(True)].copy()
    acres["non_irrigated_harvested_acres"] = acres.total_harvested_acres - acres.irrigated_harvested_acres
    require(not acres.county_geoid.duplicated().any(), "duplicate acreage counties")
    require(acres[["total_harvested_acres", "irrigated_harvested_acres", "non_irrigated_harvested_acres"]].notna().all().all(), "missing eligible acreage")
    require(acres.non_irrigated_harvested_acres.ge(0).all(), "negative non-irrigated acreage")
    panel = full_panel.merge(acres[["county_geoid", "total_harvested_acres", "irrigated_harvested_acres", "non_irrigated_harvested_acres"]], on="county_geoid", how="inner", validate="many_to_one")
    require(panel.county_geoid.nunique() == 300, "acreage-complete support differs")

    unique = panel.drop_duplicates(["county_geoid", "harvest_year"])[["county_geoid", "harvest_year", "season_start", "season_end", "latitude", "longitude"]].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    unique["season_start"], unique["season_end"] = pd.to_datetime(unique.season_start), pd.to_datetime(unique.season_end)
    overlap = np.vstack([month_overlap_days(row.season_start, row.season_end) for row in unique.itertuples(index=False)])
    published, _ = peeps_slopes(Path(paths["published_peeps"]["receipt"]), unique.latitude.to_numpy(float), unique.longitude.to_numpy(float))
    project = paths["project_patterns"]
    patterns = {
        "PEEPS_MPI-ESM1-2-HR_published": published,
        "project_fit_GFDL-ESM4": fitted_pattern(Path(project["GFDL-ESM4"]["path"]), project["GFDL-ESM4"]["sha256"], unique.latitude.to_numpy(float), unique.longitude.to_numpy(float)),
        "project_fit_IPSL-CM6A-LR": fitted_pattern(Path(project["IPSL-CM6A-LR"]["path"]), project["IPSL-CM6A-LR"]["sha256"], unique.latitude.to_numpy(float), unique.longitude.to_numpy(float)),
    }

    records = []
    for model, monthly in patterns.items():
        slopes = unique[["county_geoid", "harvest_year"]].copy()
        slopes["slope"] = np.sum(monthly * overlap * 86_400.0, axis=1)
        for practice, weight in (("non_irrigated", "non_irrigated_harvested_acres"), ("irrigated", "irrigated_harvested_acres")):
            frame = panel.loc[panel.irrigation_practice.eq(practice)].copy().merge(slopes, on=["county_geoid", "harvest_year"], validate="one_to_one")
            precip, slope = frame.precip_mm.to_numpy(float), frame.slope.to_numpy(float)
            require(np.all(precip + slope >= 0), "one-K seasonal rainfall becomes negative")
            vectors = np.zeros((len(frame), 8), dtype=float)
            vectors[:, 6] = slope / 100.0
            vectors[:, 7] = np.square((precip + slope) / 100.0) - np.square(precip / 100.0)
            for index in range(8):
                frame[f"contrast_{index}"] = vectors[:, index]
            beta, covariance = responses[practice]
            for geography, part in [("selected_sample", frame), *[(state, group) for state, group in frame.groupby("state")]]:
                county_weights = part[["county_geoid", weight]].drop_duplicates("county_geoid")
                if float(county_weights[weight].sum()) <= 0:
                    continue
                summary = summarize(acreage_weighted_vector(part, weight), beta, covariance)
                records.append({"model": model, "practice": practice, "geography": geography,
                                "counties": int(part.county_geoid.nunique()), "weight": weight,
                                "harvested_acres": float(county_weights[weight].sum()),
                                **summary})

    result_frame = pd.DataFrame(records).sort_values(["model", "practice", "geography"])
    args.state_output.parent.mkdir(parents=True, exist_ok=True)
    result_frame.to_csv(args.state_output, index=False)
    central = result_frame.loc[result_frame.geography.eq("selected_sample")].to_dict("records")
    receipt = {
        "schema": "us_corn_three_pattern_acreage_weighted/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "acreage_weighted_selected_sample_structural_sensitivity_not_national_damage_or_scc",
        "definition": "Frozen practice-specific U.S. corn response transported through three precipitation patterns and weighted by 2017 Census harvested acres on complete irrigation-share support.",
        "sources": {"three_pattern_receipt": {"path": str(args.source_receipt), "sha256": digest(args.source_receipt)}, "acreage": {"path": str(args.acreage), "sha256": digest(args.acreage)}},
        "support": {"counties": int(panel.county_geoid.nunique()), "states": int(panel.state.nunique()), "complete_irrigation_area_required": True},
        "selected_sample_results": central,
        "output": {"path": str(args.state_output), "sha256": digest(args.state_output), "bytes": args.state_output.stat().st_size},
        "claim_gates": {"acreage_weighted_selected_sample_yield_diagnostic": True, "national_yield_effect": False, "monetary_damage": False, "scc": False},
        "limitations": ["The 2017 acreage snapshot is fixed over the historical panel.", "Counties with suppressed irrigated acreage are excluded rather than treated as zero.", "Acreage weighting is not production or welfare weighting.", "The historical rainfall response fails strict geographic and temporal stability gates.", "Only the MPI pattern is published; GFDL and IPSL are project-fitted structural sensitivities, not a probability-weighted ensemble."],
        "validation": {"finite_numeric_output": bool(np.isfinite(result_frame.select_dtypes(include=[np.number]).to_numpy()).all()), "nonnegative_weights": True, "frozen_us_quantity_response_reproduced_tolerance": 1e-13},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "support": receipt["support"], "selected_sample_results": central}, indent=2))


if __name__ == "__main__":
    main()
