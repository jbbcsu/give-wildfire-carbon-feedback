#!/usr/bin/env python3
"""Audit whether a separate Rice2 Hultgren weather basis is source-feasible."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import resource
import sys
import tomllib
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

CONFIG_DEFAULT = ROOT / "config/hultgren_rice2_weather_basis_feasibility_v1.toml"
CONTRACT_ID = "hultgren_rice2_weather_basis_feasibility_v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def recorded_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def recover_unrepaired(repaired: np.ndarray, scale: np.ndarray) -> np.ndarray:
    repaired = np.asarray(repaired, dtype=np.float64)
    scale = np.asarray(scale, dtype=np.float64)
    require(repaired.shape == scale.shape, "area and repair scale shapes differ")
    require(np.isfinite(repaired).all() and np.isfinite(scale).all(), "nonfinite area or scale")
    require((repaired >= 0).all() and (scale >= 0).all(), "negative area or scale")
    require(not np.any((scale == 0) & (repaired != 0)), "positive repaired area has zero scale")
    return np.divide(repaired, scale, out=np.zeros_like(repaired), where=scale > 0)


def phase_partition_counts(month_count: int) -> tuple[int, int, int]:
    """Return source slice lengths for a complete 3--12 month rice season."""
    require(3 <= month_count <= 12, "source-observed rice season must contain 3 through 12 months")
    return min(2, month_count), min(3, max(0, month_count - 2)), max(0, month_count - 5)


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config.get("schema_version") == 1, "config schema changed")
    require(config.get("contract_id") == CONTRACT_ID, "contract id changed")
    sources = config["sources"]
    hashed = (
        "hultgren_panel", "set_crop_variables", "collapse_clim", "response_validation",
        "author_support", "weather_method_validation", "historical_preflight_validation",
        "calendar_manifest", "calendar_crosswalk", "mirca_metadata", "mirca_candidate",
        "mirca_calendar_rainfed", "mirca_calendar_irrigated", "weather_module", "weather_builder",
    )
    for key in hashed:
        source = resolve(sources[f"{key}_path"])
        require(source.is_file(), f"source missing: {key}")
        require(digest(source) == sources[f"{key}_sha256"], f"source hash differs: {key}")
    branches = {row["branch"]: row for row in config["calendar_branches"]}
    require(set(branches) == {"ri1_noirr", "ri1_firr", "ri2_noirr", "ri2_firr"}, "calendar registry changed")
    for branch, record in branches.items():
        path_value = resolve(record["path"])
        require(path_value.is_file(), f"calendar missing: {branch}")
        require(digest(path_value) == record["sha256"], f"calendar hash differs: {branch}")
    policy = config["support_policy"]
    for key in (
        "copy_ri1_calendar_authorized", "fill_missing_ri2_calendar_authorized",
        "nearest_neighbor_calendar_authorized",
    ):
        require(policy[key] is False, f"forbidden support rule opened: {key}")
    auth = config["authorization"]
    require(auth["source_inventory_audit_authorized"] is True, "inventory audit not authorized")
    require(auth["calendar_feasibility_audit_authorized"] is True, "calendar audit not authorized")
    for key in (
        "weather_basis_build_authorized", "published_response_evaluation_authorized",
        "response_fit_authorized", "damage_calculation_authorized", "scc_use_authorized",
    ):
        require(auth[key] is False, f"claim gate opened: {key}")
    return config, hashlib.sha256(raw).hexdigest()


COMPLETE_COLUMNS = [
    "ln_yield", "ln_gdppc", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop",
    "gdd", "kdd", "tmin", "prcp_poly_1_bin1", "prcp_poly_1_bin2",
    "prcp_poly_1_bin3", "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


def panel_audit(path: Path, chunk_rows: int) -> dict[str, Any]:
    columns = [
        "season", "season_length", "iso", "uid", "adm0_year", "adm1_fact",
        "median_plant_month", "median_harvest_month", *COMPLETE_COLUMNS,
    ]
    pieces: list[pd.DataFrame] = []
    with pd.read_stata(path, columns=columns, convert_categoricals=False, iterator=True) as reader:
        variable_labels = reader.variable_labels()
        while True:
            try:
                part = reader.read(chunk_rows)
            except StopIteration:
                break
            if part.empty:
                break
            pieces.append(part)
    frame = pd.concat(pieces, ignore_index=True)
    source_seasons = {str(k): int(v) for k, v in frame.season.value_counts().sort_index().items()}
    complete = frame.dropna(subset=COMPLETE_COLUMNS).copy()
    removal_rounds: list[int] = []
    while True:
        keep = np.logical_and.reduce([
            complete.groupby(column)[column].transform("size").gt(1).to_numpy()
            for column in ("uid", "adm0_year", "adm1_fact")
        ])
        removed = int((~keep).sum())
        removal_rounds.append(removed)
        if removed == 0:
            break
        complete = complete.loc[keep].copy()
    estimation_seasons = {str(k): int(v) for k, v in complete.season.value_counts().sort_index().items()}
    second = complete.loc[complete.season.eq("second")]
    second_lengths = {str(int(k)): int(v) for k, v in second.season_length.value_counts().sort_index().items()}
    second_countries = {str(k): int(v) for k, v in second.iso.value_counts().sort_index().items()}
    short = complete.loc[complete.season_length.lt(6)]
    short_lengths = {
        str(int(k)): int(v) for k, v in short.season_length.value_counts().sort_index().items()
    }
    phase3_columns = ["prcp_poly_1_bin3", "prcp_poly_2_bin3"]
    phase3_nonzero = int(np.count_nonzero(short[phase3_columns].to_numpy(dtype=np.float64)))
    require(len(frame) == 178_157, "source panel row count differs")
    require(len(complete) == 166_174, "published estimation sample count differs")
    require(estimation_seasons.get("second") == 1_189, "second-season estimation rows differ")
    require(second_lengths == {"4": 708, "5": 481}, "second-season calendar lengths differ")
    require(set(short_lengths) <= {"3", "4", "5"}, "sub-three-month estimation season observed")
    require(phase3_nonzero == 0, "short source seasons no longer have zero third-phase terms")
    return {
        "source_rows": len(frame),
        "source_season_rows": source_seasons,
        "complete_case_rows_before_singleton_removal": int(frame.dropna(subset=COMPLETE_COLUMNS).shape[0]),
        "singleton_removal_rounds": removal_rounds,
        "published_estimation_rows": len(complete),
        "published_estimation_season_rows": estimation_seasons,
        "second_season_countries": second_countries,
        "second_season_length_rows": second_lengths,
        "short_season_length_rows": short_lengths,
        "short_three_to_five_month_estimation_rows": int(short.shape[0]),
        "short_season_phase3_nonzero_values": phase3_nonzero,
        "season_variable_label": variable_labels.get("season", ""),
        "interpretation": (
            "The pooled published rice estimation sample explicitly includes second seasons; "
            "all second-season rows are 4--5 months, and absent phase 3 is encoded as exact zero."
        ),
    }


def load_calendar(path: Path, branch: str) -> dict[str, Any]:
    with xr.open_dataset(path, engine="h5netcdf", decode_timedelta=False, cache=False) as dataset:
        require(dict(dataset.sizes) == {"lon": 720, "lat": 360}, f"grid changed: {branch}")
        require(dataset.attrs.get("title") == "GGCMI crop calendar for Phase 3", f"title changed: {branch}")
        require(dataset.attrs.get("version") == "1.01", f"version changed: {branch}")
        required = {"planting_day", "maturity_day", "growing_season_length", "data_source_used", "fraction_of_harvested_area"}
        require(required <= set(dataset.data_vars), f"calendar variables missing: {branch}")
        latitude = np.asarray(dataset.lat.values, dtype=np.float64)
        longitude = np.asarray(dataset.lon.values, dtype=np.float64)
        planting = np.asarray(dataset.planting_day.values, dtype=np.float64)
        maturity = np.asarray(dataset.maturity_day.values, dtype=np.float64)
        fraction = np.asarray(dataset.fraction_of_harvested_area.values, dtype=np.float64)
        data_source = np.asarray(dataset.data_source_used.values, dtype=np.float64)
        attrs = {name: dict(dataset[name].attrs) for name in required}
    require(np.array_equal(latitude, 89.75 - 0.5 * np.arange(360)), f"latitude grid changed: {branch}")
    require(np.array_equal(longitude, -179.75 + 0.5 * np.arange(720)), f"longitude grid changed: {branch}")
    finite = np.isfinite(planting) & np.isfinite(maturity)
    plant_month = np.full(planting.shape, -1, dtype=np.int8)
    harvest_month = np.full(maturity.shape, -1, dtype=np.int8)
    for value in np.unique(planting[finite]):
        plant_month[planting == value] = source_month_from_day(float(value))
    for value in np.unique(maturity[finite]):
        harvest_month[maturity == value] = source_month_from_day(float(value))
    month_count = np.full(planting.shape, -1, dtype=np.int8)
    for row, column in zip(*np.where(finite), strict=True):
        month_count[row, column] = len(season_months(int(plant_month[row, column]), int(harvest_month[row, column])))
    positive_fraction = np.nan_to_num(fraction, nan=0.0) > 0
    return {
        "branch": branch,
        "latitude": latitude, "longitude": longitude,
        "planting": planting, "maturity": maturity, "fraction": fraction,
        "data_source": data_source, "finite": finite,
        "plant_month": plant_month, "harvest_month": harvest_month,
        "month_count": month_count, "positive_fraction": positive_fraction,
        "summary": {
            "path": recorded_path(path),
            "finite_calendar_cells": int(finite.sum()),
            "positive_publisher_fraction_cells": int(positive_fraction.sum()),
            "finite_positive_fraction_cells": int((finite & positive_fraction).sum()),
            "whole_month_season_distribution_on_finite_cells": {
                str(k): int(v) for k, v in sorted(Counter(month_count[finite].tolist()).items())
            },
            "data_source_index_distribution_on_finite_cells": {
                str(int(k)): int(v) for k, v in sorted(Counter(data_source[finite].astype(int).tolist()).items())
            },
            "metadata": attrs,
        },
    }


def calendar_and_weight_audit(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    calendars = {
        row["branch"]: load_calendar(resolve(row["path"]), row["branch"])
        for row in config["calendar_branches"]
    }
    comparisons: dict[str, Any] = {}
    for regime in ("noirr", "firr"):
        first, second = calendars[f"ri1_{regime}"], calendars[f"ri2_{regime}"]
        common = first["finite"] & second["finite"]
        same_months = common & (first["plant_month"] == second["plant_month"]) & (first["harvest_month"] == second["harvest_month"])
        comparisons[regime] = {
            "common_finite_cells": int(common.sum()),
            "same_whole_month_calendar_cells": int(same_months.sum()),
            "different_whole_month_calendar_cells": int((common & ~same_months).sum()),
            "ri2_finite_only_cells": int((second["finite"] & ~first["finite"]).sum()),
            "ri1_finite_only_cells": int((first["finite"] & ~second["finite"]).sum()),
        }
    ri2_branch_arrays_identical = all(
        np.array_equal(calendars["ri2_noirr"][name], calendars["ri2_firr"][name], equal_nan=True)
        for name in ("planting", "maturity", "fraction", "data_source")
    )

    sources = config["sources"]
    candidate = pd.read_parquet(resolve(sources["mirca_candidate_path"]))
    require(len(candidate) == 30_903, "MIRCA candidate row count differs")
    require(candidate["production_eligible"].eq(False).all(), "MIRCA production gate opened")
    require(candidate["scc_authorized"].eq(False).all(), "MIRCA SCC gate opened")
    ri2 = candidate.loc[candidate.crop.eq("ri2")].copy()
    require(len(ri2) == 8_836, "MIRCA Rice2 row count differs")
    for system in ("rainfed", "irrigated"):
        ri2[f"unrepaired_{system}_area_ha"] = recover_unrepaired(
            ri2[f"{system}_area_ha"].to_numpy(), ri2[f"{system}_repair_scale"].to_numpy()
        )
    strict_support: dict[str, Any] = {}
    for regime, system in (("noirr", "rainfed"), ("firr", "irrigated")):
        calendar = calendars[f"ri2_{regime}"]
        first = calendars[f"ri1_{regime}"]
        grid = pd.DataFrame({
            "lat": np.repeat(calendar["latitude"], len(calendar["longitude"])),
            "lon": np.tile(calendar["longitude"], len(calendar["latitude"])),
            "finite": calendar["finite"].ravel(),
            "positive_fraction": calendar["positive_fraction"].ravel(),
            "month_count": calendar["month_count"].ravel(),
            "ri2_plant_month": calendar["plant_month"].ravel(),
            "ri2_harvest_month": calendar["harvest_month"].ravel(),
            "ri1_plant_month": first["plant_month"].ravel(),
            "ri1_harvest_month": first["harvest_month"].ravel(),
        })
        area = f"unrepaired_{system}_area_ha"
        positive = ri2.loc[ri2[area].gt(0), ["lat", "lon", area]].copy()
        joined = positive.merge(grid, on=["lat", "lon"], how="left", validate="one_to_one")
        direct = joined["finite"].fillna(False) & joined["positive_fraction"].fillna(False)
        distinct = direct & (
            (joined["ri2_plant_month"] != joined["ri1_plant_month"])
            | (joined["ri2_harvest_month"] != joined["ri1_harvest_month"])
        )
        old_domain = direct & joined["month_count"].between(6, 12)
        direct_area = float(joined.loc[direct, area].sum())
        total_area = float(ri2[area].sum())
        strict_support[system] = {
            "positive_unrepaired_mirca_rice2_cells": len(positive),
            "unrepaired_global_rice2_area_ha": total_area,
            "direct_no_fill_cells": int(direct.sum()),
            "direct_no_fill_area_ha": direct_area,
            "direct_no_fill_area_fraction": direct_area / total_area,
            "direct_no_fill_month_distribution": {
                str(int(k)): int(v) for k, v in joined.loc[direct, "month_count"].value_counts().sort_index().items()
            },
            "direct_no_fill_cells_distinct_from_ri1": int(distinct.sum()),
            "current_six_to_twelve_month_cells": int(old_domain.sum()),
            "current_six_to_twelve_month_area_ha": float(joined.loc[old_domain, area].sum()),
            "current_six_to_twelve_area_fraction_of_direct_support": (
                float(joined.loc[old_domain, area].sum()) / direct_area
            ),
        }
    result = {
        "branches": {name: value["summary"] for name, value in calendars.items()},
        "ri1_ri2_comparisons": comparisons,
        "ri2_noirr_firr_calendar_arrays_identical": ri2_branch_arrays_identical,
        "strict_direct_ri2_calendar_and_mirca_support": strict_support,
        "calendar_interpretation": (
            "All finite GGCMI Rice2 cells declare data-source index 4 (RICEATLAS). "
            "The separate rainfed and irrigated Rice2 files contain identical calendar arrays, "
            "but the Rice2 calendar is not a copy of Rice1."
        ),
    }
    return result, calendars


def mirca_calendar_inventory(config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for system in ("rainfed", "irrigated"):
        path = resolve(config["sources"][f"mirca_calendar_{system}_path"])
        frame = pd.read_csv(
            path, encoding="latin1",
            usecols=["Country", "unit_code", "Crop", "Subcrop", "Type", "Growing_area", "Planting_Month", "Maturity_Month"],
        )
        rice2 = frame.loc[frame.Crop.eq("Rice2")]
        positive = rice2.loc[rice2.Growing_area.gt(0)]
        require(len(rice2) == 4_849, f"MIRCA Rice2 calendar row count differs: {system}")
        require(not positive[["unit_code", "Planting_Month", "Maturity_Month"]].isna().any().any(), f"positive MIRCA Rice2 calendar incomplete: {system}")
        result[system] = {
            "path": recorded_path(path),
            "rice2_rows": len(rice2),
            "positive_growing_area_rows": len(positive),
            "reported_growing_area_ha": float(positive.Growing_area.sum()),
            "countries_with_positive_growing_area": int(positive.Country.nunique()),
            "unique_positive_plant_harvest_month_pairs": int(positive[["Planting_Month", "Maturity_Month"]].drop_duplicates().shape[0]),
            "positive_rows_with_complete_unit_and_calendar": int(len(positive)),
            "direct_grid_join_available_from_csv_alone": False,
        }
    return result


def implementation_and_weather_inventory(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    sources = config["sources"]
    builder = resolve(sources["weather_builder_path"]).read_text(encoding="utf-8")
    weather_module = resolve(sources["weather_module_path"]).read_text(encoding="utf-8")
    do_files = sorted(resolve(sources["hultgren_code_directory"]).glob("*.do"))
    explicit_ri2_tokens = sum(len(re.findall(r"(?i)\b(?:ri2|rice2)\b", path.read_text(encoding="utf-8", errors="replace"))) for path in do_files)
    implementation = {
        "current_builder_calendar_choices_are_ri1_only": 'choices=("ri1_noirr", "ri1_firr")' in builder,
        "current_builder_filters_to_six_through_twelve_months": "(month_count >= 6) & (month_count <= 12)" in builder,
        "current_scalar_weather_method_rejects_under_six_months": "if not 6 <= len(precipitation) <= 12" in weather_module,
        "preserved_hultgren_do_file_count": len(do_files),
        "explicit_ri2_or_rice2_tokens_in_preserved_do_files": explicit_ri2_tokens,
        "mechanical_phase_slices_already_allow_empty_phase3": "(slice(0, 2), slice(2, 5), slice(5, None))" in builder,
        "required_correction": (
            "Permit explicitly declared ri2_noirr/ri2_firr and source-observed 3--12 month seasons; "
            "retain missing later phase months as structural zeros, not imputed weather."
        ),
    }
    require(all(implementation[key] for key in (
        "current_builder_calendar_choices_are_ri1_only",
        "current_builder_filters_to_six_through_twelve_months",
        "current_scalar_weather_method_rejects_under_six_months",
        "mechanical_phase_slices_already_allow_empty_phase3",
    )), "current implementation signature changed")
    require(explicit_ri2_tokens == 0, "preserved Hultgren code now contains explicit Rice2 logic")

    raw_weather = ROOT / "data/raw/isimip3a_gswp3_w5e5_v1_3"
    files = sorted(raw_weather.glob("gswp3-w5e5_obsclim_*_global_daily_*.nc"))
    expected = {(variable, period) for variable in ("pr", "tasmin", "tasmax") for period in ("1981_1990", "1991_2000", "2001_2010", "2011_2019")}
    observed: set[tuple[str, str]] = set()
    inventory = []
    for path in files:
        match = re.fullmatch(r"gswp3-w5e5_obsclim_(pr|tasmin|tasmax)_global_daily_(\d{4}_\d{4})\.nc", path.name)
        if match:
            observed.add((match.group(1), match.group(2)))
            inventory.append({"path": recorded_path(path), "bytes": path.stat().st_size})
    require(observed == expected, "local historical daily weather inventory differs")
    preflight = json.loads(resolve(sources["historical_preflight_validation_path"]).read_text(encoding="utf-8"))
    require(preflight.get("status") == "validated_unweighted_ri1_branch_preflight_not_response_damage_or_scc", "prior preflight status differs")
    weather_inventory = {
        "local_daily_file_count": len(inventory),
        "variables": ["pr", "tasmin", "tasmax"],
        "complete_calendar_year_blocks": ["1981-1990", "1991-2000", "2001-2010", "2011-2019"],
        "files": inventory,
        "previously_validated_ri1_periods": ["1981-1990", "1991-2000", "2001-2010"],
        "weather_product_role": "alternative GSWP3-W5E5 transport; not exact Hultgren GMFD reproduction",
    }
    return implementation, weather_inventory


def run(config_path: Path) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    panel = panel_audit(resolve(config["sources"]["hultgren_panel_path"]), int(config["resources"]["panel_chunk_rows"]))
    calendar, _ = calendar_and_weight_audit(config)
    mirca_calendars = mirca_calendar_inventory(config)
    implementation, weather = implementation_and_weather_inventory(config)
    maximum_rss = peak_rss_bytes()
    cap = int(config["resources"]["worker_memory_bytes_maximum"])
    require(maximum_rss < cap, "audit exceeded 512 MiB memory cap")
    feasible_after_bounded_fix = bool(
        panel["published_estimation_season_rows"]["second"] > 0
        and panel["short_season_phase3_nonzero_values"] == 0
        and all(calendar["branches"][f"ri2_{regime}"]["finite_positive_fraction_cells"] > 0 for regime in ("noirr", "firr"))
        and all(calendar["strict_direct_ri2_calendar_and_mirca_support"][system]["direct_no_fill_cells"] > 0 for system in ("rainfed", "irrigated"))
    )
    require(feasible_after_bounded_fix, "Rice2 source-feasibility evidence failed")
    return {
        "schema": "hultgren_rice2_weather_basis_feasibility/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "rice2_source_inputs_available_current_builder_blocked_by_short_season_and_branch_guards",
        "contract_id": CONTRACT_ID,
        "config": {"path": recorded_path(config_path), "sha256": config_hash},
        "hultgren_panel": panel,
        "ggcmi_calendars": calendar,
        "mirca_administrative_calendar_inventory": mirca_calendars,
        "historical_weather_inventory": weather,
        "implementation_audit": implementation,
        "decision": {
            "separate_rice2_calendar_available": True,
            "rice2_calendar_distinct_from_rice1": True,
            "published_panel_contains_second_season_observations": True,
            "source_short_season_zero_phase_semantics_observed": True,
            "rice2_weather_basis_feasible_without_copying_ri1_or_filling_missing_calendars_after_bounded_code_fix": feasible_after_bounded_fix,
            "current_builder_can_execute_source_faithful_rice2": False,
            "exact_hultgren_gmfd_sage_historical_reproduction_available": False,
        },
        "claim_gates": {
            "source_inventory_and_calendar_feasibility_validated": True,
            "rice2_weather_basis_built": False,
            "rice2_weather_basis_independently_validated": False,
            "mirca_candidate_promoted_to_production_weights": False,
            "published_response_evaluated": False,
            "response_fit_authorized": False,
            "damage_calculated": False,
            "scc_calculated": False,
        },
        "single_safest_next_gate": (
            "Patch only the rice weather primitive and builder guards to accept explicitly declared "
            "ri2_noirr/ri2_firr and 3--12 month seasons, encode absent later phase months as exact zeros, "
            "then run and independently reaggregate a one-harvest-year pilot on the strict finite, positive-"
            "publisher-fraction Rice2 support. Do not attach production weights or evaluate the response."
        ),
        "resources": {"maximum_rss_bytes": maximum_rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": recorded_path(Path(__file__)), "sha256": digest(Path(__file__))},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "fresh output required")
    result = run(args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "claim_gates": result["claim_gates"],
        "resources": result["resources"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
