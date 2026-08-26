#!/usr/bin/env python3
"""Plan and, only after explicit gate changes, run the all-practice U.S. SPEI route.

The manifest contains only nClimGrid cells referenced by the isolated national
all-practice county-polygon weights.  There is deliberately no run-all command.
No outcome value is read, and this module does not fit a response relationship.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(CORE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPT_DIR))

import build_spei_grid_chunk as spei_core  # noqa: E402
from build_county_nclimgrid_feature_smoke import validate_polygon_weights  # noqa: E402
from build_us_national_county_nclimgrid_weights import (  # noqa: E402
    SCHEMA as WEIGHT_SCHEMA,
    _partition_paths as weight_partition_paths,
)
from us_national_nclimgrid_common import (  # noqa: E402
    OUTCOME_KEYS,
    PAIR_KEYS,
    STATE_FIPS_TO_ALPHA,
    canonical_sha256,
    sha256_file,
    sha256_records,
    strict_bool,
)
from validate_spei_competitor_contract import (  # noqa: E402
    FALSE_GATES as SPEI_FALSE_GATES,
    load_contract as load_spei_contract,
    validate_contract as validate_spei_contract,
)


ROUTE_CONTRACT = PROJECT_ROOT / "us_county_validation/us_national_all_practice_spei_v1.toml"
CORE_RUNNER = PROJECT_ROOT / "scripts/build_spei_grid_chunk.py"
ALL_PRACTICE_WEIGHT_CONTRACT = (
    PROJECT_ROOT / "us_county_validation/us_national_all_practice_nclimgrid_features_v1.toml"
)
ROUTE_ID = "us_national_all_practice_spei_v1"
MANIFEST_SCHEMA = "us_all_practice_spei_execution_manifest_v1"
CELL_SCHEMA = "us_all_practice_spei_cell_inventory_v1"
SUPPORT_SCHEMA = "us_all_practice_spei_support_calendar_v1"
AGGREGATE_SCHEMA = "us_all_practice_spei_crop_calendar_partition_v1"
CHUNK_RECEIPT_SCHEMA = "us_all_practice_spei_chunk_execution_receipt_v1"
MAX_CELLS = 64
SCALES = (1, 3, 6)
STAGE_FRACTIONS = (0.0, 0.3, 0.7, 1.0)
ROUTE_FALSE_GATES = (
    "cell_execution_authorized",
    "full_scope_execution_authorized",
    "crop_calendar_aggregation_execution_authorized",
    "response_estimation_authorized",
    "coefficient_export_authorized",
    "causal_claim_authorized",
    "damage_claim_authorized",
    "future_projection_authorized",
    "scc_claim_authorized",
)
EXPECTED_TOP = {
    "schema_version",
    "contract_id",
    "analysis_role",
    "manifest_generation_authorized",
    *ROUTE_FALSE_GATES,
    "source",
    "weights",
    "execution",
    "aggregation",
    "resources",
    "paths",
    "scientific_boundary",
}
SUPPORT_COLUMNS = [
    "county_geoid",
    "state",
    "county_name",
    "outcome_crop",
    "harvest_year",
    "irrigation_practice",
    "outcome_source_id",
    "response_estimation_authorized",
    "scc_authorized",
]
CALENDAR_COLUMNS = [
    "state",
    "calendar_crop",
    "harvest_year",
    "season_start",
    "season_end",
    "calendar_source_id",
    "calendar_vintage",
    "calendar_role",
    "boundary_rule",
    "stage_definition",
    "feature_construction_eligible",
    "response_estimation_authorized",
    "scc_authorized",
]
WEIGHT_COLUMNS = [
    "county_geoid",
    "grid_lat_index",
    "grid_lon_index",
    "grid_lat",
    "grid_lon",
    "spatial_weight",
    "coverage_fraction",
    "weather_valid_coverage_fraction",
    "weather_valid_area_relative_to_declared_land",
]


@dataclass(frozen=True)
class RouteInputs:
    contract: dict[str, Any]
    paths: dict[str, Path]


def project_path(value: object, label: str) -> Path:
    path = Path(str(value))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a project-relative path")
    resolved = (PROJECT_ROOT / path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"{label} escapes the project") from error
    return resolved


def require_regular(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symbolic file: {path}")


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"artifact lies outside the project: {path}") from error


def json_object(path: Path, label: str) -> dict[str, Any]:
    require_regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {label}: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def file_record(path: Path) -> dict[str, Any]:
    require_regular(path, "file record input")
    return {
        "path": relative(path),
        "size_bytes": int(path.stat().st_size),
        "sha512": spei_core.sha512_file(path),
    }


def code_identities() -> dict[str, str]:
    paths = (
        Path(__file__).resolve(),
        CORE_RUNNER,
        PROJECT_ROOT / "scripts/spei_construction_primitives.py",
        PROJECT_ROOT / "scripts/spei_distribution.py",
        PROJECT_ROOT / "scripts/spei_monthly_engine.py",
        PROJECT_ROOT / "scripts/validate_spei_competitor_contract.py",
        PROJECT_ROOT / "us_county_validation/scripts/build_us_national_county_nclimgrid_weights.py",
        PROJECT_ROOT / "us_county_validation/scripts/us_national_nclimgrid_common.py",
        ROUTE_CONTRACT,
        ALL_PRACTICE_WEIGHT_CONTRACT,
        PROJECT_ROOT / "config/spei_competitor_v1.toml",
    )
    return {relative(path): spei_core.sha512_file(path) for path in paths}


def load_route_contract(path: Path = ROUTE_CONTRACT) -> RouteInputs:
    if path.resolve() != ROUTE_CONTRACT.resolve():
        raise ValueError("the all-practice SPEI route requires its canonical contract")
    require_regular(path, "route contract")
    try:
        contract = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("cannot read the all-practice SPEI route contract") from error
    if set(contract) != EXPECTED_TOP:
        raise ValueError("all-practice SPEI contract top-level fields changed")
    if contract["schema_version"] != 1 or contract["contract_id"] != ROUTE_ID:
        raise ValueError("all-practice SPEI contract identity changed")
    if contract["analysis_role"] != "manifest_and_aggregation_scaffold_only":
        raise ValueError("all-practice SPEI role changed")
    if contract["manifest_generation_authorized"] is not True:
        raise ValueError("all-practice SPEI manifest generation is not authorized")
    for gate in ROUTE_FALSE_GATES:
        if contract[gate] is not False:
            raise ValueError(f"all-practice SPEI contract unexpectedly opens {gate}")

    source = contract["source"]
    if (
        source["source"] != "nclimgrid"
        or source["source_id"] != "nclimgrid_daily_v1_0_0_20220829"
        or source["algorithm_version"] != spei_core.ALGORITHM_VERSION
        or source["checkpoint_version"] != spei_core.CHECKPOINT_VERSION
        or list(source["accumulation_scales_months"]) != list(SCALES)
        or source["actual_source_sha512_revalidation_required"] is not True
    ):
        raise ValueError("all-practice SPEI source lock changed")
    if list(source["numerical_environment_fields"]) != list(
        spei_core.numerical_environment_identity()
    ):
        raise ValueError("all-practice SPEI numerical-environment fields changed")

    weights = contract["weights"]
    if (
        weights["required_practice"] != "all_practices"
        or int(weights["expected_counties"]) != 2628
        or int(weights["expected_crop_county_years"]) != 136539
        or weights["complete_registered_scope_required"] is not True
        or weights["extra_grid_cells_forbidden"] is not True
        or int(weights["outcome_values_read"]) != 0
    ):
        raise ValueError("all-practice SPEI weight lock changed")
    execution = contract["execution"]
    if (
        execution["manifest_schema"] != MANIFEST_SCHEMA
        or execution["cell_inventory_schema"] != CELL_SCHEMA
        or int(execution["maximum_cells_per_chunk"]) != MAX_CELLS
        or execution["chunk_layout"]
        != "one latitude row and one contiguous referenced-longitude run"
        or execution["one_chunk_per_invocation_required"] is not True
        or execution["automatic_run_all_command_available"] is not False
        or execution["computed_cell_set_must_equal_referenced_cell_set"] is not True
    ):
        raise ValueError("all-practice SPEI execution lock changed")
    aggregation = contract["aggregation"]
    if (
        int(aggregation["analysis_year_min"]) != 1982
        or int(aggregation["analysis_year_max"]) != 2019
        or list(aggregation["scales"]) != list(SCALES)
        or list(aggregation["stage_fractions"]) != list(STAGE_FRACTIONS)
        or int(aggregation["outcome_values_read"]) != 0
        or aggregation["response_columns_forbidden"] is not True
    ):
        raise ValueError("all-practice SPEI aggregation lock changed")

    raw_paths = dict(contract["paths"])
    paths = {name: project_path(value, f"paths.{name}") for name, value in raw_paths.items()}
    output_names = [
        "plan_root",
        "cell_output_root",
        "execution_receipt_root",
        "aggregate_partition_root",
        "aggregate_receipt_root",
        "direct_weather_feature_root",
        "pdsi_output_root",
    ]
    if len({paths[name] for name in output_names}) != len(output_names):
        raise ValueError("all-practice SPEI output paths alias another route")
    if "national_all_practice_spei_v1" not in paths["cell_output_root"].as_posix():
        raise ValueError("all-practice SPEI cell outputs lost their isolated namespace")
    if "spei_features_national_all_practice_v1" not in paths[
        "aggregate_partition_root"
    ].as_posix():
        raise ValueError("all-practice SPEI aggregates lost their isolated namespace")
    for name, value in paths.items():
        if value.exists() and value.is_symlink():
            raise ValueError(f"all-practice SPEI path may not be a symlink: {name}")
    return RouteInputs(contract=contract, paths=paths)


def _normalize_support_keys(frame: pd.DataFrame, contract: Mapping[str, Any]) -> pd.DataFrame:
    if set(frame.columns) != set(SUPPORT_COLUMNS):
        raise ValueError("key-only NASS projection columns changed")
    value = frame.copy()
    value["county_geoid"] = value.county_geoid.astype("string").str.strip()
    value["state"] = value.state.astype("string").str.strip().str.upper()
    value["county_name"] = value.county_name.astype("string").str.strip()
    value["outcome_crop"] = value.outcome_crop.astype("string").str.strip()
    value["irrigation_practice"] = value.irrigation_practice.astype("string").str.strip()
    value["harvest_year"] = pd.to_numeric(value.harvest_year, errors="raise").astype("int64")
    if value.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("key-only NASS projection contains malformed GEOIDs")
    expected_state = value.county_geoid.str[:2].map(STATE_FIPS_TO_ALPHA)
    if expected_state.isna().any() or not expected_state.eq(value.state).all():
        raise ValueError("key-only NASS GEOID/state values do not reconcile")
    if value.duplicated(OUTCOME_KEYS).any():
        raise ValueError("key-only NASS projection duplicates outcome keys")
    if set(value.outcome_source_id.astype(str)) != {
        str(contract["sample"]["outcome_source_id"])
    }:
        raise ValueError("key-only NASS projection source changed")
    if strict_bool(value.response_estimation_authorized, "NASS response gate").any():
        raise ValueError("key-only NASS projection opens response estimation")
    if strict_bool(value.scc_authorized, "NASS SCC gate").any():
        raise ValueError("key-only NASS projection opens SCC use")
    return value


def support_calendar_without_outcomes(
    route: RouteInputs,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    weights = route.contract["weights"]
    weight_contract_path = project_path(weights["route_contract"], "weights.route_contract")
    require_regular(weight_contract_path, "all-practice weight contract")
    weight_contract = tomllib.loads(weight_contract_path.read_text(encoding="utf-8"))
    if weight_contract.get("contract_id") != "us_national_all_practice_nclimgrid_features_v1":
        raise ValueError("all-practice weather contract identity changed")
    panel_path = project_path(weights["panel"], "weights.panel")
    geography_path = project_path(weights["geography"], "weights.geography")
    calendar_path = project_path(weights["calendar"], "weights.calendar")
    require_regular(panel_path, "key-only all-practice panel")
    require_regular(geography_path, "all-practice geography gate")
    require_regular(calendar_path, "fixed crop calendar")

    panel = pd.read_parquet(panel_path, columns=SUPPORT_COLUMNS)
    panel = _normalize_support_keys(panel, weight_contract)
    sample = weight_contract["sample"]
    crops = set(map(str, sample["crops"]))
    practices = {"all_practices"}
    year_min, year_max = int(sample["year_min"]), int(sample["year_max"])
    scope = panel.loc[
        panel.outcome_crop.isin(crops)
        & panel.irrigation_practice.isin(practices)
        & panel.harvest_year.between(year_min, year_max)
    ].copy()
    if set(scope.outcome_crop) != crops or set(scope.irrigation_practice) != practices:
        raise ValueError("key-only all-practice scope changed")
    if scope.duplicated(PAIR_KEYS).any():
        raise ValueError("key-only all-practice scope is not one row per crop/county/year")

    geography = pd.read_csv(
        geography_path,
        dtype={"county_geoid": "string"},
        usecols=[
            "county_geoid",
            "state",
            "feature_construction_eligible",
            "response_estimation_authorized",
            "scc_authorized",
        ],
    )
    geography["county_geoid"] = geography.county_geoid.astype("string").str.strip()
    geography["state"] = geography.state.astype("string").str.strip().str.upper()
    if geography.duplicated("county_geoid").any():
        raise ValueError("all-practice geography gate duplicates GEOIDs")
    if strict_bool(geography.response_estimation_authorized, "geography response gate").any():
        raise ValueError("all-practice geography gate opens response estimation")
    if strict_bool(geography.scc_authorized, "geography SCC gate").any():
        raise ValueError("all-practice geography gate opens SCC use")
    geography["feature_construction_eligible"] = strict_bool(
        geography.feature_construction_eligible, "geography feature gate"
    )
    eligible = geography.loc[
        geography.feature_construction_eligible, ["county_geoid", "state"]
    ].rename(columns={"state": "geography_state"})
    selected = scope.merge(eligible, on="county_geoid", how="inner", validate="many_to_one")
    if selected.empty or not selected.state.eq(selected.geography_state).all():
        raise ValueError("key-only all-practice support and geography do not reconcile")
    selected = selected.drop(columns="geography_state")

    calendar = pd.read_csv(calendar_path, usecols=CALENDAR_COLUMNS)
    calendar["state"] = calendar.state.astype("string").str.strip().str.upper()
    calendar["calendar_crop"] = calendar.calendar_crop.astype("string").str.strip()
    calendar["harvest_year"] = pd.to_numeric(calendar.harvest_year, errors="raise").astype(int)
    calendar = calendar.loc[
        calendar.calendar_crop.isin(crops)
        & calendar.harvest_year.between(year_min, year_max)
        & calendar.calendar_role.astype("string").eq(str(weight_contract["calendar"]["role"]))
    ].copy()
    calendar["season_start"] = pd.to_datetime(calendar.season_start, errors="raise").dt.normalize()
    calendar["season_end"] = pd.to_datetime(calendar.season_end, errors="raise").dt.normalize()
    if calendar.duplicated(["state", "calendar_crop", "harvest_year"]).any():
        raise ValueError("fixed calendar duplicates state/crop/year keys")
    if (calendar.season_end < calendar.season_start).any():
        raise ValueError("fixed calendar has a negative season")
    if not strict_bool(calendar.feature_construction_eligible, "calendar feature gate").all():
        raise ValueError("fixed calendar contains an ineligible row")
    if strict_bool(calendar.response_estimation_authorized, "calendar response gate").any():
        raise ValueError("fixed calendar opens response estimation")
    if strict_bool(calendar.scc_authorized, "calendar SCC gate").any():
        raise ValueError("fixed calendar opens SCC use")
    for column, expected in {
        "calendar_source_id": weight_contract["calendar"]["source_id"],
        "calendar_vintage": weight_contract["calendar"]["vintage"],
        "calendar_role": weight_contract["calendar"]["role"],
        "boundary_rule": weight_contract["calendar"]["boundary_rule"],
        "stage_definition": weight_contract["calendar"]["stage_definition"],
    }.items():
        if set(calendar[column].astype(str)) != {str(expected)}:
            raise ValueError(f"fixed calendar {column} changed")

    support = selected.merge(
        calendar,
        left_on=["state", "outcome_crop", "harvest_year"],
        right_on=["state", "calendar_crop", "harvest_year"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_calendar"),
    )
    if support.season_start.isna().any() or len(support) != len(selected):
        raise ValueError("key-only all-practice support lacks a fixed calendar")
    pairs = selected.drop_duplicates(PAIR_KEYS)
    counts = {
        "eligible_counties": int(selected.county_geoid.nunique()),
        "eligible_crop_county_years": int(len(pairs)),
        "eligible_practice_rows": int(len(selected)),
        "corn_crop_county_years": int(pairs.outcome_crop.eq("corn_grain").sum()),
        "soy_crop_county_years": int(pairs.outcome_crop.eq("soybeans").sum()),
        "states": sorted(selected.state.unique().tolist()),
        "year_min": int(selected.harvest_year.min()),
        "year_max": int(selected.harvest_year.max()),
        "outcome_key_sha256": sha256_records(selected, OUTCOME_KEYS),
        "pair_key_sha256": sha256_records(pairs, PAIR_KEYS),
        "relationship_estimated": False,
        "scc_authorized": False,
    }
    expected_counts = {
        "eligible_counties": int(weights["expected_counties"]),
        "eligible_crop_county_years": int(weights["expected_crop_county_years"]),
        "eligible_practice_rows": int(weight_contract["sample"]["expected_practice_rows"]),
        "corn_crop_county_years": int(weight_contract["sample"]["expected_corn_crop_county_years"]),
        "soy_crop_county_years": int(weight_contract["sample"]["expected_soy_crop_county_years"]),
    }
    if {key: counts[key] for key in expected_counts} != expected_counts:
        raise ValueError("key-only all-practice registered counts changed")
    keep = [
        "county_geoid",
        "state",
        "county_name",
        "outcome_crop",
        "harvest_year",
        "irrigation_practice",
        "season_start",
        "season_end",
        "calendar_source_id",
        "calendar_vintage",
        "calendar_role",
        "boundary_rule",
        "stage_definition",
    ]
    result = support.loc[support.harvest_year.between(1982, 2019), keep].copy()
    result.insert(0, "schema", SUPPORT_SCHEMA)
    result["outcome_values_read"] = 0
    result["response_estimation_authorized"] = False
    result["scc_authorized"] = False
    return result.sort_values(["harvest_year", "county_geoid", "outcome_crop"]), counts


def validate_source_identity(route: RouteInputs, *, recompute: bool) -> tuple[Any, dict[str, Any]]:
    source_contract_path = project_path(
        route.contract["source"]["source_contract"], "source.source_contract"
    )
    contract = load_spei_contract(source_contract_path)
    validate_spei_contract(contract, require_local_inputs=True)
    inventory = spei_core.load_source_inventory("nclimgrid", contract)
    expected = str(route.contract["source"]["source_file_set_sha512"])
    if inventory.declared_file_set_sha512 != expected:
        raise ValueError("nClimGrid declared file-set identity changed")
    validation = spei_core.verify_source_files(inventory) if recompute else {
        "objects": len(inventory.records),
        "bytes": int(sum(record.size_bytes for record in inventory.records)),
        "all_sha512_recomputed": False,
        "all_sha512_equal_declared": True,
        "actual_file_set_sha512": inventory.declared_file_set_sha512,
    }
    return inventory, validation
