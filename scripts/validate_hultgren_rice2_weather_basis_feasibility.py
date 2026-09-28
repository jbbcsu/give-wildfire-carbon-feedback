#!/usr/bin/env python3
"""Independently validate the bounded Hultgren Rice2 feasibility audit."""
from __future__ import annotations

import argparse
import gc
import json
import math
import resource
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import season_months, source_month_from_day
from audit_hultgren_rice2_weather_basis_feasibility import CONFIG_DEFAULT, digest, load_config, resolve


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(left: float, right: float, message: str) -> None:
    require(math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-6), message)


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


COMPLETE_COLUMNS = [
    "ln_yield", "ln_gdppc", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop",
    "gdd", "kdd", "tmin", "prcp_poly_1_bin1", "prcp_poly_1_bin2",
    "prcp_poly_1_bin3", "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


def validate_panel(path: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    columns = ["season", "season_length", "iso", "uid", "adm0_year", "adm1_fact", *COMPLETE_COLUMNS]
    pieces: list[pd.DataFrame] = []
    source_rows = 0
    with pd.read_stata(path, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                part = reader.read(25_000)
            except StopIteration:
                break
            if part.empty:
                break
            source_rows += len(part)
            selected = part.dropna(subset=COMPLETE_COLUMNS)
            if not selected.empty:
                pieces.append(selected.copy())
    require(source_rows == receipt["source_rows"] == 178_157, "source panel rows differ")
    sample = pd.concat(pieces, ignore_index=True)
    del pieces
    initial = len(sample)
    while True:
        keep = np.logical_and.reduce([
            sample.groupby(column)[column].transform("size").gt(1).to_numpy()
            for column in ("uid", "adm0_year", "adm1_fact")
        ])
        if keep.all():
            break
        sample = sample.loc[keep].copy()
    by_season = {str(k): int(v) for k, v in sample.season.value_counts().sort_index().items()}
    require(initial == receipt["complete_case_rows_before_singleton_removal"] == 166_354, "complete-case rows differ")
    require(len(sample) == receipt["published_estimation_rows"] == 166_174, "estimation rows differ")
    require(by_season == receipt["published_estimation_season_rows"], "estimation season counts differ")
    second = sample.loc[sample.season.eq("second")]
    lengths = {str(int(k)): int(v) for k, v in second.season_length.value_counts().sort_index().items()}
    require(lengths == receipt["second_season_length_rows"] == {"4": 708, "5": 481}, "second-season lengths differ")
    short = sample.loc[sample.season_length.lt(6), ["prcp_poly_1_bin3", "prcp_poly_2_bin3"]]
    short_lengths = {
        str(int(k)): int(v)
        for k, v in sample.loc[sample.season_length.lt(6), "season_length"].value_counts().sort_index().items()
    }
    require(short_lengths == receipt["short_season_length_rows"], "short-season lengths differ")
    require(set(short_lengths) <= {"3", "4", "5"}, "sub-three-month estimation season observed")
    nonzero = int(np.count_nonzero(short.to_numpy(dtype=np.float64)))
    require(nonzero == receipt["short_season_phase3_nonzero_values"] == 0, "short-season phase 3 differs")
    return {"source_rows": source_rows, "estimation_rows": len(sample), "second_season_rows": len(second), "short_phase3_nonzero_values": nonzero}


def calendar_frame(path: Path) -> tuple[pd.DataFrame, dict[str, int], dict[str, int]]:
    with xr.open_dataset(path, engine="h5netcdf", decode_timedelta=False, cache=False) as dataset:
        lat = np.asarray(dataset.lat.values, dtype=np.float64)
        lon = np.asarray(dataset.lon.values, dtype=np.float64)
        planting = np.asarray(dataset.planting_day.values, dtype=np.float64)
        maturity = np.asarray(dataset.maturity_day.values, dtype=np.float64)
        fraction = np.asarray(dataset.fraction_of_harvested_area.values, dtype=np.float64)
        source = np.asarray(dataset.data_source_used.values, dtype=np.float64)
    finite = np.isfinite(planting) & np.isfinite(maturity)
    plant_month = np.full(planting.shape, -1, dtype=np.int8)
    harvest_month = np.full(maturity.shape, -1, dtype=np.int8)
    month_count = np.full(planting.shape, -1, dtype=np.int8)
    for row, column in zip(*np.where(finite), strict=True):
        plant_month[row, column] = source_month_from_day(float(planting[row, column]))
        harvest_month[row, column] = source_month_from_day(float(maturity[row, column]))
        month_count[row, column] = len(season_months(int(plant_month[row, column]), int(harvest_month[row, column])))
    positive_fraction = np.nan_to_num(fraction, nan=0.0) > 0
    frame = pd.DataFrame({
        "lat": np.repeat(lat, len(lon)), "lon": np.tile(lon, len(lat)),
        "finite": finite.ravel(), "positive_fraction": positive_fraction.ravel(),
        "plant_month": plant_month.ravel(), "harvest_month": harvest_month.ravel(),
        "month_count": month_count.ravel(),
    })
    months = {str(k): int(v) for k, v in sorted(Counter(month_count[finite].tolist()).items())}
    sources = {str(int(k)): int(v) for k, v in sorted(Counter(source[finite].astype(int).tolist()).items())}
    return frame, months, sources


def validate_calendars(config: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    frames: dict[str, pd.DataFrame] = {}
    for record in config["calendar_branches"]:
        branch = record["branch"]
        frame, months, sources = calendar_frame(resolve(record["path"]))
        frames[branch] = frame
        summary = receipt["branches"][branch]
        require(int(frame.finite.sum()) == summary["finite_calendar_cells"], f"finite calendars differ: {branch}")
        require(int(frame.positive_fraction.sum()) == summary["positive_publisher_fraction_cells"], f"positive fractions differ: {branch}")
        require(months == summary["whole_month_season_distribution_on_finite_cells"], f"month distribution differs: {branch}")
        require(sources == summary["data_source_index_distribution_on_finite_cells"], f"data-source distribution differs: {branch}")
    for regime in ("noirr", "firr"):
        first, second = frames[f"ri1_{regime}"], frames[f"ri2_{regime}"]
        common = first.finite & second.finite
        same = common & first.plant_month.eq(second.plant_month) & first.harvest_month.eq(second.harvest_month)
        comparison = receipt["ri1_ri2_comparisons"][regime]
        require(int(common.sum()) == comparison["common_finite_cells"], f"common calendar count differs: {regime}")
        require(int(same.sum()) == comparison["same_whole_month_calendar_cells"], f"same calendar count differs: {regime}")

    candidate = pd.read_parquet(resolve(config["sources"]["mirca_candidate_path"]))
    ri2 = candidate.loc[candidate.crop.eq("ri2")].copy()
    checks: dict[str, Any] = {}
    for regime, system in (("noirr", "rainfed"), ("firr", "irrigated")):
        repaired = ri2[f"{system}_area_ha"].to_numpy(dtype=np.float64)
        scale = ri2[f"{system}_repair_scale"].to_numpy(dtype=np.float64)
        original = np.divide(repaired, scale, out=np.zeros_like(repaired), where=scale > 0)
        ri2[f"original_{system}"] = original
        positive = ri2.loc[ri2[f"original_{system}"].gt(0), ["lat", "lon", f"original_{system}"]]
        joined = positive.merge(frames[f"ri2_{regime}"], on=["lat", "lon"], how="left", validate="one_to_one")
        direct = joined.finite.fillna(False) & joined.positive_fraction.fillna(False)
        direct_area = float(joined.loc[direct, f"original_{system}"].sum())
        expected = receipt["strict_direct_ri2_calendar_and_mirca_support"][system]
        require(len(positive) == expected["positive_unrepaired_mirca_rice2_cells"], f"positive Rice2 cells differ: {system}")
        require(int(direct.sum()) == expected["direct_no_fill_cells"], f"direct support cells differ: {system}")
        close(direct_area, expected["direct_no_fill_area_ha"], f"direct support area differs: {system}")
        old = direct & joined.month_count.between(6, 12)
        require(int(old.sum()) == expected["current_six_to_twelve_month_cells"], f"old-domain cells differ: {system}")
        checks[system] = {"direct_cells": int(direct.sum()), "direct_area_ha": direct_area, "six_to_twelve_month_cells": int(old.sum())}
    return checks


def validate(receipt_path: Path, config_path: Path) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "hultgren_rice2_weather_basis_feasibility/v1", "receipt schema differs")
    require(receipt.get("config", {}).get("sha256") == config_hash, "config hash differs")
    require(receipt.get("status") == "rice2_source_inputs_available_current_builder_blocked_by_short_season_and_branch_guards", "status differs")
    implementation = resolve(receipt["implementation"]["path"])
    require(digest(implementation) == receipt["implementation"]["sha256"], "audit implementation hash differs")
    panel = validate_panel(resolve(config["sources"]["hultgren_panel_path"]), receipt["hultgren_panel"])
    gc.collect()
    support = validate_calendars(config, receipt["ggcmi_calendars"])
    decisions = receipt["decision"]
    for key in (
        "separate_rice2_calendar_available", "rice2_calendar_distinct_from_rice1",
        "published_panel_contains_second_season_observations",
        "source_short_season_zero_phase_semantics_observed",
        "rice2_weather_basis_feasible_without_copying_ri1_or_filling_missing_calendars_after_bounded_code_fix",
    ):
        require(decisions[key] is True, f"decision gate closed unexpectedly: {key}")
    require(decisions["current_builder_can_execute_source_faithful_rice2"] is False, "current builder gate opened")
    require(decisions["exact_hultgren_gmfd_sage_historical_reproduction_available"] is False, "exact reproduction gate opened")
    claim_gates = receipt["claim_gates"]
    require(claim_gates["source_inventory_and_calendar_feasibility_validated"] is True, "feasibility gate differs")
    for key in (
        "rice2_weather_basis_built", "rice2_weather_basis_independently_validated",
        "mirca_candidate_promoted_to_production_weights", "published_response_evaluated",
        "response_fit_authorized", "damage_calculated", "scc_calculated",
    ):
        require(claim_gates[key] is False, f"claim gate opened: {key}")
    maximum_rss = peak_rss_bytes()
    cap = int(config["resources"]["worker_memory_bytes_maximum"])
    require(maximum_rss < cap, "validator exceeded 512 MiB memory cap")
    return {
        "schema": "hultgren_rice2_weather_basis_feasibility_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated",
        "receipt": {"path": str(receipt_path), "sha256": digest(receipt_path)},
        "checks": {"panel": panel, "strict_direct_support": support},
        "claim_gates": {
            "source_inventory_and_calendar_feasibility_validated": True,
            "rice2_weather_basis_built": False,
            "published_response_evaluated": False,
            "damage_or_scc_calculated": False,
        },
        "resources": {"maximum_rss_bytes": maximum_rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__))},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "fresh output required")
    result = validate(args.receipt, args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
