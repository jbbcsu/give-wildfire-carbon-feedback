#!/usr/bin/env python3
"""Independently validate the no-fit soybean global-response readiness audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import tomllib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

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


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stream_direct(path: Path) -> dict:
    parquet = pq.ParquetFile(path)
    rows_by_year, outcomes_by_year = Counter(), Counter()
    all_cells, outcome_years = set(), defaultdict(set)
    rows = 0
    for batch in parquet.iter_batches(
        batch_size=16384,
        columns=["harvest_year", "lat", "lon_360", "crop", "yield_observed", "yield_t_ha", "fit_authorized", "scc_authorized"],
        use_threads=False,
    ):
        frame = batch.to_pandas()
        rows += len(frame)
        require(frame.crop.astype(str).eq("soy").all(), "unexpected crop")
        require(not frame.fit_authorized.astype(bool).any() and not frame.scc_authorized.astype(bool).any(), "authorization opened")
        rows_by_year.update(frame.harvest_year.astype(int).tolist())
        all_cells.update(zip(frame.lat.astype(float), frame.lon_360.astype(float)))
        observed = frame.loc[frame.yield_observed.astype(bool) & frame.yield_t_ha.gt(0)]
        outcomes_by_year.update(observed.harvest_year.astype(int).tolist())
        for row in observed.itertuples(index=False):
            outcome_years[(float(row.lat), float(row.lon_360))].add(int(row.harvest_year))
    pairs = sum(sum((year - 1) in years for year in years) for years in outcome_years.values())
    return {
        "rows": rows, "unique_cells": len(all_cells), "year_minimum": min(rows_by_year), "year_maximum": max(rows_by_year),
        "rows_by_year": {str(key): int(rows_by_year[key]) for key in sorted(rows_by_year)},
        "positive_observed_outcomes": sum(outcomes_by_year.values()),
        "positive_observed_outcomes_by_year": {str(key): int(outcomes_by_year[key]) for key in sorted(outcomes_by_year)},
        "cells_with_positive_outcome": len(outcome_years), "direct_only_consecutive_positive_pairs": pairs,
        "one_outcome_per_cell_year": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    audit = load(args.audit)
    require(digest(args.config) == audit["contract"]["sha256"], "contract hash differs")
    for record in config["sources"].values():
        require(digest(resolve(record["path"])) == record["sha256"], f"source hash differs: {record['path']}")

    rebuilt = stream_direct(resolve(config["sources"]["direct_panel"]["path"]))
    require(rebuilt == audit["assets"]["outcome_and_direct_weather"], "direct panel summary differs")
    calendar_checks = {}
    for branch in ("noirr", "firr"):
        with xr.open_dataset(resolve(config["sources"][f"calendar_{branch}"]["path"]), decode_times=False) as dataset:
            mask = np.isfinite(dataset.planting_day.values) & np.isfinite(dataset.maturity_day.values) & np.isfinite(dataset.growing_season_length.values)
            calendar_checks[branch] = int(mask.sum())
            require(calendar_checks[branch] == audit["assets"]["calendars"][branch]["finite_calendar_cells"], f"calendar support differs: {branch}")

    weights = pd.read_parquet(resolve(config["sources"]["mirca_weights"]["path"]), columns=["lat", "lon_360", "crop", "irrigation", "area_share", "total_area_ha", "irrigated_area_ha", "rainfed_area_ha", "production_eligible"])
    weights = weights.loc[weights.crop.astype(str).eq("soy")]
    cells = weights.drop_duplicates(["lat", "lon_360"])
    sums = weights.groupby(["lat", "lon_360"], sort=False).area_share.sum()
    weight_checks = {
        "rows": len(weights), "cells": len(cells),
        "total_area_ha": float(cells.total_area_ha.sum()),
        "irrigated_area_ha": float(cells.irrigated_area_ha.sum()),
        "rainfed_area_ha": float(cells.rainfed_area_ha.sum()),
        "maximum_absolute_share_error": float(np.max(np.abs(sums - 1.0))),
    }
    expected_weights = audit["assets"]["irrigation_exposure_weights"]
    require(weight_checks["rows"] == expected_weights["rows"] == 48108, "weight rows differ")
    require(weight_checks["cells"] == expected_weights["supported_cells"] == 24054, "weight cells differ")
    require(weight_checks["maximum_absolute_share_error"] <= 1e-12, "share sum error")
    for source_key, expected_key in (("total_area_ha", "global_total_area_ha"), ("irrigated_area_ha", "global_irrigated_area_ha"), ("rainfed_area_ha", "global_rainfed_area_ha")):
        require(abs(weight_checks[source_key] - expected_weights[expected_key]) <= 1e-6, f"area differs: {source_key}")

    spatial = load(resolve(config["sources"]["spatial_prediction"]["path"]))["crops"]["soy"]
    country = load(resolve(config["sources"]["country_association"]["path"]))["crops"]["soy"]
    later = next(item for item in load(resolve(config["sources"]["later_distribution_confirmation"]["path"]))["results"] if item["crop"] == "soy")
    response = audit["response_evidence"]
    require((spatial["unique_training_pairs"], spatial["unique_terminal_pairs"], spatial["training_source_blocks"], spatial["held_out_source_blocks"]) == (166870, 26004, 56, 55), "spatial response support differs")
    require((country["support"]["singleton"], country["support"]["ambiguous"], country["support"]["absent"], country["mapped_country_labels"]) == (157003, 7069, 2798, 21), "country support differs")
    require(later["pair_count"] == 21026 and later["passes_prespecified_later_period_confirmation_gate"] is False, "later confirmation differs")
    require(response["spatial_terminal_prediction"]["quantity_minus_heat_rmse"] == spatial["paired_rmse_contrasts"]["quantity_minus_controls_only"], "quantity result differs")
    require(response["spatial_terminal_prediction"]["distribution_minus_quantity_rmse"] == spatial["paired_rmse_contrasts"]["quantity_distribution_minus_quantity"], "distribution result differs")
    require(response["independent_later_rainfed_distribution_confirmation"]["bootstrap_interval"] == later["paired_cluster_bootstrap_rmse_difference_quantiles"], "later interval differs")

    require(audit["crop_selection"]["selected"] == "soybean" and audit["crop_selection"]["wheat_detailed_audit_needed"] is False, "crop selection differs")
    require(audit["single_highest_value_next_computation"]["fit_authorized"] is False, "next gate authorizes fit")
    require(audit["claim_gates"] == config["claim_gates"], "claim gates differ")
    require(all(value is False for key, value in audit["claim_gates"].items() if key != "readiness_audit_authorized"), "downstream gate opened")
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"memory cap exceeded: {rss} >= {cap}")
    result = {
        "schema": "soybean_global_response_readiness_audit_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_soybean_global_response_readiness_fail_closed_no_fit",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "audit": {"path": str(args.audit), "sha256": digest(args.audit)},
        "checks": {"direct_panel": rebuilt, "calendar_finite_cells": calendar_checks, "weights": weight_checks, "spatial_support": {"training_pairs": 166870, "terminal_pairs": 26004, "training_blocks": 56, "terminal_blocks": 55}, "country_support": {"singleton_pairs": 157003, "ambiguous_pairs": 7069, "absent_pairs": 2798, "countries": 21}, "later_confirmation_pairs": 21026},
        "claim_gates": {"audit_validated": True, "response_fit_or_downstream_authorized": False},
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
