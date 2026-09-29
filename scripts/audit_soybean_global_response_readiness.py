#!/usr/bin/env python3
"""Build a fail-closed, no-fit soybean global-response readiness audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import tomllib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def calendar_summary(path: Path) -> dict[str, Any]:
    with xr.open_dataset(path, decode_times=False) as dataset:
        require(dict(dataset.sizes) == {"lon": 720, "lat": 360}, "calendar grid changed")
        require(dataset.attrs.get("title") == "GGCMI crop calendar for Phase 3", "calendar title changed")
        require(dataset.attrs.get("version") == "1.01", "calendar version changed")
        planting = np.asarray(dataset.planting_day.values, dtype=float)
        maturity = np.asarray(dataset.maturity_day.values, dtype=float)
        length = np.asarray(dataset.growing_season_length.values, dtype=float)
        mask = np.isfinite(planting) & np.isfinite(maturity) & np.isfinite(length)
        return {
            "title": dataset.attrs["title"], "version": dataset.attrs["version"],
            "finite_calendar_cells": int(mask.sum()),
            "growing_season_length_days_minimum": float(length[mask].min()),
            "growing_season_length_days_maximum": float(length[mask].max()),
        }


def direct_panel_summary(path: Path) -> dict[str, Any]:
    parquet = pq.ParquetFile(path)
    required = {"harvest_year", "lat", "lon_360", "crop", "yield_observed", "yield_t_ha", "fit_authorized", "scc_authorized"}
    require(required <= set(parquet.schema_arrow.names), "direct panel schema is incomplete")
    table = parquet.read(columns=list(required), use_threads=False).to_pandas()
    require(table.crop.astype(str).eq("soy").all(), "direct panel contains another crop")
    require(not table.fit_authorized.astype(bool).any() and not table.scc_authorized.astype(bool).any(), "panel authorization opened")
    observed = table.loc[table.yield_observed.astype(bool) & table.yield_t_ha.gt(0), ["harvest_year", "lat", "lon_360", "yield_t_ha"]].copy()
    observed = observed.sort_values(["lat", "lon_360", "harvest_year"])
    consecutive = observed.groupby(["lat", "lon_360"], sort=False).harvest_year.diff().eq(1)
    return {
        "rows": len(table), "unique_cells": int(table[["lat", "lon_360"]].drop_duplicates().shape[0]),
        "year_minimum": int(table.harvest_year.min()), "year_maximum": int(table.harvest_year.max()),
        "rows_by_year": {str(key): int(value) for key, value in table.groupby("harvest_year").size().items()},
        "positive_observed_outcomes": len(observed),
        "positive_observed_outcomes_by_year": {str(key): int(value) for key, value in observed.groupby("harvest_year").size().items()},
        "cells_with_positive_outcome": int(observed[["lat", "lon_360"]].drop_duplicates().shape[0]),
        "direct_only_consecutive_positive_pairs": int(consecutive.sum()),
        "one_outcome_per_cell_year": not table.duplicated(["crop", "lat", "lon_360", "harvest_year"]).any(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    raw = args.config.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config["contract_id"] == "soybean_global_response_readiness_audit_v1", "contract id changed")
    for record in config["sources"].values():
        path = resolve(record["path"])
        require(path.is_file(), f"missing source: {path}")
        require(digest(path) == record["sha256"], f"source hash differs: {path}")
    require(config["claim_gates"]["readiness_audit_authorized"] is True, "audit not authorized")
    require(all(value is False for key, value in config["claim_gates"].items() if key != "readiness_audit_authorized"), "downstream gate opened")

    sources = config["sources"]
    direct_receipt = load(resolve(sources["direct_receipt"]["path"]))
    heat_receipt = load(resolve(sources["heat_receipt"]["path"]))
    scpdsi_receipt = load(resolve(sources["scpdsi_receipt"]["path"]))
    for family, receipt, source_key in (
        ("direct", direct_receipt, "direct_panel"), ("heat", heat_receipt, "heat_panel"), ("scpdsi", scpdsi_receipt, "scpdsi_panel")
    ):
        require(receipt["status"] == "validated_continuous_candidate_1982_2016", f"{family} receipt not validated")
        require(receipt["output"]["sha256"] == sources[source_key]["sha256"], f"{family} receipt output hash differs")
        require(receipt["fit_performed"] is False and receipt["scc_authorized"] is False, f"{family} boundary opened")
    panel = direct_panel_summary(resolve(sources["direct_panel"]["path"]))
    require(panel["rows"] == direct_receipt["output"]["rows"] == 837690, "direct row count differs")
    require(panel["positive_observed_outcomes"] == direct_receipt["output"]["observed_outcomes"] == 206087, "direct outcome count differs")

    calendars = {
        "noirr": calendar_summary(resolve(sources["calendar_noirr"]["path"])),
        "firr": calendar_summary(resolve(sources["calendar_firr"]["path"])),
    }
    weights = pd.read_parquet(resolve(sources["mirca_weights"]["path"]), filters=[[('crop', '==', 'soy')]])
    require(len(weights) == 48108 and weights[["lat", "lon_360"]].drop_duplicates().shape[0] == 24054, "soy MIRCA support differs")
    require(set(weights.irrigation.astype(str)) == {"noirr", "firr"}, "soy MIRCA regimes differ")
    share_sums = weights.groupby(["lat", "lon_360"], sort=False).area_share.sum()
    require(float(np.max(np.abs(share_sums - 1.0))) <= 1e-12, "MIRCA shares do not sum to one")
    area_rows = weights.drop_duplicates(["lat", "lon_360"])
    weight_summary = {
        "rows": len(weights), "supported_cells": len(area_rows),
        "irrigation_regimes": sorted(weights.irrigation.astype(str).unique()),
        "global_total_area_ha": float(area_rows.total_area_ha.sum()),
        "global_irrigated_area_ha": float(area_rows.irrigated_area_ha.sum()),
        "global_rainfed_area_ha": float(area_rows.rainfed_area_ha.sum()),
        "global_area_weighted_irrigated_share": float(area_rows.irrigated_area_ha.sum() / area_rows.total_area_ha.sum()),
        "maximum_absolute_cell_share_sum_error": float(np.max(np.abs(share_sums - 1.0))),
        "fixed_vintage": sorted(weights.weight_vintage.astype(str).unique()),
        "production_eligible": bool(weights.production_eligible.astype(bool).all()),
    }

    spatial = load(resolve(sources["spatial_prediction"]["path"]))["crops"]["soy"]
    country = load(resolve(sources["country_association"]["path"]))["crops"]["soy"]
    later = load(resolve(sources["later_distribution_confirmation"]["path"]))
    later_soy = next(item for item in later["results"] if item["crop"] == "soy")
    nonlinear = load(resolve(sources["nonlinear_prediction"]["path"]))
    historical = load(resolve(sources["historical_association"]["path"]))["crops"]["soy"]
    historical_pairs = sorted({int(item["pairs"]) for item in historical["fits"] if item["status"] == "completed"})
    require(historical_pairs == [166870], "historical association support differs")

    welfare = load(resolve(sources["mirca_welfare_support"]["path"]))
    soy_welfare = next(item for item in welfare["crop_summaries"] if item["crop"] == "soy")
    mapspam = load(resolve(sources["mapspam_production_audit"]["path"]))["extraction"]
    faostat = load(resolve(sources["faostat_value_audit"]["path"]))["items"]["236"]
    crosswalk = load(resolve(sources["value_crosswalk_audit"]["path"]))["crops"]["soybean"]
    structural = load(resolve(sources["structural_spatial_validation"]["path"]))

    result = {
        "schema": "soybean_global_response_readiness_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_soybean_selected_nonmaize_readiness_audit_fail_closed_no_fit",
        "contract": {"path": str(args.config), "sha256": hashlib.sha256(raw).hexdigest()},
        "crop_selection": {
            "selected": "soybean", "wheat_detailed_audit_needed": False,
            "reason": "soybean has identified single-season outcome/calendar mapping and production-eligible rainfed/irrigated MIRCA shares; resident wheat weights do not identify spring versus winter GDHY outcomes",
        },
        "assets": {
            "outcome_and_direct_weather": panel,
            "continuous_candidate_families": {
                "direct": direct_receipt["output"], "heat": heat_receipt["output"], "scpdsi": scpdsi_receipt["output"],
                "direct_and_heat_share_rows_and_observed_outcomes": direct_receipt["output"]["rows"] == heat_receipt["output"]["rows"] and direct_receipt["output"]["observed_outcomes"] == heat_receipt["output"]["observed_outcomes"],
                "scpdsi_is_mutually_exclusive_and_has_narrower_support": True,
            },
            "calendars": calendars,
            "irrigation_exposure_weights": weight_summary,
            "historical_welfare_support": {
                "observed_cell_count_coverage_fraction": soy_welfare["observed_cell_count_coverage_fraction"],
                "consecutive_pair_area_coverage_fraction": soy_welfare["harvested_area"]["consecutive_pair_area_coverage_fraction"],
                "global_observed_production_coverage_identified": soy_welfare["conditional_production_proxy"]["global_observed_production_coverage_identified"],
                "revenue_coverage_identified": soy_welfare["revenue_coverage"]["identified"],
            },
            "candidate_value_weights": {
                "mapspam_positive_5arcmin_cells": mapspam["positive_cells"]["soybean"],
                "mapspam_global_production_mt": mapspam["global_production_mt"]["soybean"],
                "faostat_baseline_constant_usd_countries": faostat["baseline_1999_2001_constant_usd_countries"],
                "matched_faostat_value_production_share": crosswalk["buckets"]["matched_faostat_value"]["production_share"],
                "spatial_value_weights_authorized": False,
            },
        },
        "response_evidence": {
            "historical_equal_weight_association_pairs": historical_pairs[0],
            "causal_interpretation": False,
            "spatial_terminal_prediction": {
                "training_pairs": spatial["unique_training_pairs"], "terminal_pairs": spatial["unique_terminal_pairs"],
                "training_10degree_blocks": spatial["training_source_blocks"], "terminal_10degree_blocks": spatial["held_out_source_blocks"],
                "quantity_minus_heat_rmse": spatial["paired_rmse_contrasts"]["quantity_minus_controls_only"],
                "distribution_minus_quantity_rmse": spatial["paired_rmse_contrasts"]["quantity_distribution_minus_quantity"],
                "scpdsi_mean_minus_quantity_rmse": spatial["paired_rmse_contrasts"]["scpdsi_mean_minus_quantity"],
            },
            "country_mapping": {
                "training_pairs_single_country": country["support"]["singleton"],
                "training_pairs_ambiguous_country": country["support"]["ambiguous"],
                "training_pairs_absent_country": country["support"]["absent"],
                "mapped_country_labels": country["mapped_country_labels"],
                "mapped_country_years": country["mapped_country_years"],
                "country_is_crop_footprint_proxy_not_authoritative_boundary": True,
            },
            "independent_later_rainfed_distribution_confirmation": {
                "pairs": later_soy["pair_count"], "occupied_10degree_clusters": later_soy["occupied_10degree_clusters"],
                "candidate_minus_quantity_rmse": later_soy["candidate_minus_reference_rmse"],
                "bootstrap_interval": later_soy["paired_cluster_bootstrap_rmse_difference_quantiles"],
                "folds_improving": int(sum(item["candidate_has_lower_rmse"] for item in later_soy["spatial_fold_differences"])),
                "passes": later_soy["passes_prespecified_later_period_confirmation_gate"],
            },
            "nonlinear_rescue": {
                "training_pairs": nonlinear["training_pairs"], "terminal_pairs": nonlinear["terminal_pairs"],
                "quantity_nonlinear_minus_linear_pooled_rmse": nonlinear["rmse_differences"]["pooled_rmse"]["quantity_nonlinear_minus_linear"],
                "uncertainty_status": nonlinear["uncertainty"]["status"], "passes": nonlinear["promotion"]["quantity_nonlinear_minus_linear"]["passes_exploratory_rule"],
            },
            "external_structural_spatial_benchmark": {
                "validation_passed": structural["validation"]["status"] == "passed",
                "yield_response_gate": structural["gates"]["yield_response"],
                "conclusion": structural["conclusion"],
            },
        },
        "readiness": {
            "outcome_weather_calendar_exposure_chain_ready": True,
            "continuous_1982_2016_direct_and_heat_panel_ready": True,
            "competing_historical_scpdsi_family_ready": True,
            "soil_moisture_family_ready": False,
            "response_protocol_frozen": False,
            "causal_response_ready": False,
            "geographic_heterogeneity_response_ready": False,
            "economic_winner_loser_weights_ready": False,
            "matched_marginal_co2_climate_path_ready": False,
            "damage_or_scc_ready": False,
        },
        "single_highest_value_next_computation": {
            "name": config["next_gate"]["name"],
            "action": "freeze, then run an outcome-blind continuous-panel design/heterogeneity preflight; do not estimate yield slopes",
            "exact_scope": "1982-2010 soybean direct seasonal-quantity basis with fixed-MIRCA-2000 basis-before-weighting, one GDHY outcome, cell first differences, predeclared country/region-year controls, and separate direct-distribution and climatic-water-balance views",
            "outputs": ["residualized rank and condition", "within-stratum precipitation variation and overlap", "country and 10-degree-block pair/year support", "leverage and effective cluster counts", "support-qualified heterogeneity resolution"],
            "why": "the physical input chain is already continuous; another response fit before proving heterogeneity design support would repeat the existing noncausal and unstable evidence",
            "fit_authorized": False,
        },
        "claim_gates": {key: value for key, value in config["claim_gates"].items()},
    }
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"memory cap exceeded: {rss} >= {cap}")
    result["resources"] = {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True}
    result["implementation"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "crop_selection": result["crop_selection"], "readiness": result["readiness"], "next": result["single_highest_value_next_computation"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
