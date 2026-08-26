#!/usr/bin/env python3
"""Run the isolated national all-practice nClimGrid feature route.

The existing national builders remain the single implementation of the
weather calculations.  This launcher fixes the all-practice inputs and output
trees, adds launcher/core-script hash lineage, and prevents an all-practice run
from writing into the regional direct-practice paths.  It does not fit a
response or calculate damages or SCC.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from build_us_national_county_nclimgrid_weights import (
    DEFAULT_COUNTIES,
    DEFAULT_REFERENCE,
    _partition_paths as weight_partition_paths,
)
from build_us_national_all_practice_nclimgrid_features import (
    CALCULATION_MODULE as FEATURE_CALCULATION_MODULE,
    validate_year_partition_checkpoint,
)
from build_us_national_nclimgrid_features import (
    _default_partition_paths as feature_partition_paths,
)
from us_national_nclimgrid_common import (
    DEFAULT_BOUND_CALENDAR,
    DEFAULT_BOUND_CALENDAR_RECEIPT,
    DEFAULT_COMPETING_PROTOCOL,
    DEFAULT_HTTP_INVENTORY,
    DEFAULT_RAW_WEATHER_DIR,
    DEFAULT_REVIEWED_PRODUCT,
    OUTCOME_KEYS,
    PAIR_KEYS,
    PROJECT_ROOT,
    atomic_write_json,
    canonical_sha256,
    load_contract,
    prepare_support,
    read_table,
    sha256_file,
)


ROUTE_ID = "us_national_all_practice_nclimgrid_features_v1"
CONTRACT = PROJECT_ROOT / "us_county_validation/us_national_all_practice_nclimgrid_features_v1.toml"
PANEL = PROJECT_ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet"
GEOGRAPHY = PROJECT_ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019_geography_gate.csv"
PANEL_PREP_RECEIPT = PROJECT_ROOT / "outputs/us_county/nass_national_all_practice_1981_2019/panel_prepare_audit.json"
GEOGRAPHY_RECEIPT = PROJECT_ROOT / "outputs/us_county/nass_national_all_practice_1981_2019/geography_audit.json"
CORN_PREP_RECEIPT = PROJECT_ROOT / "outputs/us_county/nass_national_all_practice_1981_2019/corn_prepare_audit.json"
SOY_PREP_RECEIPT = PROJECT_ROOT / "outputs/us_county/nass_national_all_practice_1981_2019/soybeans_prepare_audit.json"
NASS_RAW_MANIFEST = PROJECT_ROOT / "data/raw/us_county/nass_api/national_all_practice_1981_2019/MANIFEST.jsonl"
WEIGHT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_polygon_weights_national_all_practice_v1"
FEATURE_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_features_national_all_practice_v1"
ROUTE_OUTPUT_DIR = PROJECT_ROOT / "outputs/us_county/national_all_practice_nclimgrid_features_v1"
TRACKED_SMOKE_RECEIPT = PROJECT_ROOT / "data/provenance/us_national_all_practice_nclimgrid_smoke_20260826.json"
WEIGHT_BUILDER = Path(__file__).with_name("build_us_national_county_nclimgrid_weights.py")
FEATURE_BUILDER = Path(__file__).with_name(
    "build_us_national_all_practice_nclimgrid_features.py"
)
DIRECT_WEIGHT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_polygon_weights_national_v1"
DIRECT_FEATURE_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_features_national_v1"


def relative_path(path: Path) -> str:
    """Return a project-relative path and reject paths outside the project."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"route artifact lies outside the precipitation project: {path}") from error


def file_record(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"route artifact is not a regular file: {path}")
    return {
        "path": relative_path(path),
        "sha256": sha256_file(path),
        "size_bytes": int(path.stat().st_size),
    }


def load_route_support() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if WEIGHT_DIR == DIRECT_WEIGHT_DIR or FEATURE_DIR == DIRECT_FEATURE_DIR:
        raise RuntimeError("all-practice output route aliases a direct-practice output tree")
    contract = load_contract(CONTRACT)
    if contract["contract_id"] != ROUTE_ID:
        raise ValueError("all-practice launcher received the wrong contract identity")
    support, seasons, audit = prepare_support(
        read_table(PANEL), read_table(GEOGRAPHY), read_table(DEFAULT_BOUND_CALENDAR), contract
    )
    if set(support.irrigation_practice.astype(str)) != {"all_practices"}:
        raise ValueError("all-practice route contains another practice label")
    if support.duplicated(PAIR_KEYS).any() or len(support) != len(
        support.drop_duplicates(PAIR_KEYS)
    ):
        raise ValueError("all-practice route does not preserve one row per crop-county-year key")
    return contract, support, seasons, audit


def fixed_common_arguments() -> list[str]:
    return [
        "--panel", str(PANEL),
        "--geography", str(GEOGRAPHY),
        "--calendar", str(DEFAULT_BOUND_CALENDAR),
        "--calendar-validation", str(DEFAULT_BOUND_CALENDAR_RECEIPT),
        "--calendar-protocol", str(DEFAULT_COMPETING_PROTOCOL),
        "--contract", str(CONTRACT),
        "--counties", str(DEFAULT_COUNTIES),
        "--reference-climate", str(DEFAULT_REFERENCE),
        "--inventory", str(DEFAULT_HTTP_INVENTORY),
        "--reviewed-product", str(DEFAULT_REVIEWED_PRODUCT),
        "--raw-weather-dir", str(DEFAULT_RAW_WEATHER_DIR),
    ]


def run_command(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def run_weights(
    geoids: list[str] | None, *, force: bool
) -> tuple[dict[str, Any], list[str], Path]:
    _, support, _, audit = load_route_support()
    eligible = sorted(support.county_geoid.astype(str).unique().tolist())
    requested = eligible if geoids is None else sorted(dict.fromkeys(map(str, geoids)))
    if not requested:
        raise ValueError("weight route requires at least one eligible county")
    if unknown := sorted(set(requested) - set(eligible)):
        raise ValueError(f"requested all-practice counties are outside eligible support: {unknown}")
    if requested == eligible:
        manifest_path = ROUTE_OUTPUT_DIR / "weights/complete_registered_scope_manifest.json"
    else:
        tag = canonical_sha256(requested)[:12]
        manifest_path = ROUTE_OUTPUT_DIR / f"weights/subset_{tag}_manifest.json"
    command = [sys.executable, str(WEIGHT_BUILDER), *fixed_common_arguments()]
    command.extend(["--out-dir", str(WEIGHT_DIR), "--manifest-out", str(manifest_path)])
    for geoid in requested:
        command.extend(["--county-geoid", geoid])
    if force:
        command.append("--force")
    run_command(command)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("registered_sample") != audit:
        raise ValueError("all-practice weight manifest changed its registered sample")
    if manifest.get("requested_counties") != requested:
        raise ValueError("all-practice weight manifest changed its requested counties")
    builder_sha = sha256_file(WEIGHT_BUILDER)
    for geoid in requested:
        output, receipt_path = weight_partition_paths(WEIGHT_DIR, geoid)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        identity = receipt.get("input_identity", {})
        if identity.get("builder_sha256") != builder_sha:
            raise ValueError(f"weight receipt lacks current builder lineage for {geoid}")
        if identity.get("contract_sha256") != sha256_file(CONTRACT):
            raise ValueError(f"weight receipt lacks all-practice contract lineage for {geoid}")
        if receipt.get("output_sha256") != sha256_file(output):
            raise ValueError(f"weight receipt/output hash differs for {geoid}")
    return manifest, requested, manifest_path


def _year_seasons(
    support: pd.DataFrame, seasons: pd.DataFrame, year: int, geoids: list[str] | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    year_support = support.loc[support.harvest_year.eq(year)].copy()
    if geoids is not None:
        year_support = year_support.loc[year_support.county_geoid.isin(geoids)].copy()
    if year_support.empty:
        raise ValueError("requested all-practice year/county scope has no outcome support")
    if year_support.duplicated(PAIR_KEYS).any() or set(year_support.irrigation_practice) != {
        "all_practices"
    }:
        raise ValueError("requested all-practice feature scope changed its one-row key invariant")
    calendar = seasons.loc[seasons.harvest_year.eq(year)].copy()
    required = year_support[["state", "outcome_crop", "harvest_year"]].drop_duplicates()
    calendar = required.merge(
        calendar.rename(columns={"calendar_crop": "outcome_crop"}),
        on=["state", "outcome_crop", "harvest_year"],
        how="left",
        validate="many_to_one",
    ).rename(columns={"outcome_crop": "calendar_crop"})
    if calendar.season_start.isna().any():
        raise ValueError("requested all-practice feature scope lacks a fixed calendar")
    return year_support, calendar


def run_feature(
    year: int, geoids: list[str] | None, *, force: bool
) -> tuple[pd.DataFrame, dict[str, Any], Path, Path]:
    contract, support, seasons, audit = load_route_support()
    if not int(contract["sample"]["year_min"]) <= year <= int(contract["sample"]["year_max"]):
        raise ValueError("all-practice feature year lies outside the registered contract")
    bounded = geoids is not None
    selected_geoids = None if geoids is None else sorted(dict.fromkeys(map(str, geoids)))
    year_support, year_seasons = _year_seasons(support, seasons, year, selected_geoids)
    command = [
        sys.executable, str(FEATURE_BUILDER), "--year", str(year),
        *fixed_common_arguments(), "--weight-dir", str(WEIGHT_DIR),
        "--out-dir", str(FEATURE_DIR),
    ]
    if bounded:
        command.append("--bounded-smoke")
        for geoid in selected_geoids or []:
            command.extend(["--county-geoid", geoid])
    if force:
        command.append("--force")
    run_command(command)
    output, receipt_path = feature_partition_paths(FEATURE_DIR, year, selected_geoids)
    frame, receipt = validate_year_partition_checkpoint(
        output,
        receipt_path,
        year_support,
        expected_national_sample=audit,
        expected_seasons=year_seasons,
    )
    identity = receipt.get("input_identity", {})
    if identity.get("builder_sha256") != sha256_file(FEATURE_BUILDER):
        raise ValueError("feature receipt lacks current builder lineage")
    if identity.get("calculation_module_sha256") != sha256_file(FEATURE_CALCULATION_MODULE):
        raise ValueError("feature receipt lacks current calculation-module lineage")
    if identity.get("contract_sha256") != sha256_file(CONTRACT):
        raise ValueError("feature receipt lacks all-practice contract lineage")
    if frame.duplicated(PAIR_KEYS).any() or len(frame) != len(frame.drop_duplicates(PAIR_KEYS)):
        raise ValueError("all-practice feature output does not preserve one row per key")
    if set(frame.irrigation_practice.astype(str)) != {"all_practices"}:
        raise ValueError("all-practice feature output contains another practice label")
    return frame, receipt, output, receipt_path


def validate_tracked_smoke_receipt(receipt: dict[str, Any]) -> None:
    """Reject misleading gates, absolute paths, or inconsistent smoke counts."""
    if receipt.get("schema") != "us_national_all_practice_nclimgrid_bounded_smoke_receipt_v1":
        raise ValueError("tracked all-practice smoke receipt schema changed")
    if receipt.get("route_id") != ROUTE_ID:
        raise ValueError("tracked all-practice smoke receipt route changed")
    for gate in [
        "raw_observations_embedded", "coefficients_emitted", "row_predictions_emitted",
        "relationship_estimated", "causal_effect_estimated", "damage_estimated",
        "scc_authorized",
    ]:
        if receipt.get(gate) is not False:
            raise ValueError(f"tracked all-practice smoke receipt unexpectedly sets {gate}")

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if "weather_exposure_shared_across_practices" in value:
                raise ValueError("all-practice receipt falsely claims cross-practice exposure sharing")
            if "path" in value:
                path = Path(str(value["path"]))
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("tracked all-practice smoke receipt contains a nonlocal path")
                if set(value) != {"path", "sha256", "size_bytes"}:
                    raise ValueError("tracked all-practice file record fields changed")
                if len(str(value["sha256"])) != 64 or int(value["size_bytes"]) <= 0:
                    raise ValueError("tracked all-practice file record hash/size is invalid")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith("/Users/"):
            raise ValueError("tracked all-practice smoke receipt contains an absolute user path")

    visit(receipt)
    support = receipt.get("registered_support", {})
    if int(support.get("eligible_practice_rows", -1)) != int(
        support.get("eligible_crop_county_years", -2)
    ):
        raise ValueError("registered all-practice support is not one row per key")
    smoke = receipt.get("bounded_smoke", {})
    if smoke.get("irrigation_practice") != "all_practices":
        raise ValueError("bounded smoke practice label changed")
    if smoke.get("weather_exposure_application") != (
        "one_county_crop_year_exposure_joined_to_one_all_practices_outcome"
    ):
        raise ValueError("bounded smoke exposure-application metadata changed")
    if int(smoke.get("outcome_rows", -1)) != int(smoke.get("crop_county_years", -2)):
        raise ValueError("bounded smoke does not preserve one all-practice row per key")
    counts = receipt.get("acquisition_and_preparation_counts", {})
    if int(counts.get("raw_api_records_including_non_fips_aggregates", -1)) != int(
        counts.get("excluded_non_fips_aggregate_records", -2)
    ) + int(counts.get("reported_fips_county_records", -3)):
        raise ValueError("tracked acquisition counts do not reconcile")
    if int(counts.get("prepared_positive_yield_panel_rows", -1)) != int(
        receipt.get("prepared_panel_rows_before_geography_calendar_gate", -2)
    ):
        raise ValueError("tracked preparation row counts do not reconcile")


def write_tracked_smoke_receipt(
    *,
    geoid: str,
    year: int,
    manifest: dict[str, Any],
    frame: pd.DataFrame,
    feature_receipt: dict[str, Any],
    feature_output: Path,
    feature_receipt_path: Path,
    weight_manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    _, support, _, support_audit = load_route_support()
    weight_output, weight_receipt_path = weight_partition_paths(WEIGHT_DIR, geoid)
    weight_receipt = json.loads(weight_receipt_path.read_text(encoding="utf-8"))
    panel_frame = read_table(PANEL)
    panel_rows = int(len(panel_frame))
    geography_rows = int(len(read_table(GEOGRAPHY)))
    corn_prep = json.loads(CORN_PREP_RECEIPT.read_text(encoding="utf-8"))
    soy_prep = json.loads(SOY_PREP_RECEIPT.read_text(encoding="utf-8"))
    panel_prep = json.loads(PANEL_PREP_RECEIPT.read_text(encoding="utf-8"))
    api_response_objects = sum(
        1 for line in NASS_RAW_MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    if api_response_objects != 78:
        raise ValueError("national all-practice API manifest no longer has 78 annual objects")
    for crop_receipt in [corn_prep, soy_prep]:
        if len(crop_receipt["raw_records_by_year"]) != 39:
            raise ValueError("national all-practice preparation receipt lacks 39 annual responses")
    raw_records = int(sum(corn_prep["raw_records_by_year"].values())) + int(
        sum(soy_prep["raw_records_by_year"].values())
    )
    excluded_non_fips = int(sum(corn_prep["excluded_non_fips_records_by_year"].values())) + int(
        sum(soy_prep["excluded_non_fips_records_by_year"].values())
    )
    receipt = {
        "schema": "us_national_all_practice_nclimgrid_bounded_smoke_receipt_v1",
        "route_id": ROUTE_ID,
        "status": "bounded_one_county_one_year_weather_features_validated_not_fitted",
        "registered_support": {
            key: value for key, value in support_audit.items() if key != "states"
        } | {"state_count": len(support_audit["states"])},
        "prepared_panel_rows_before_geography_calendar_gate": panel_rows,
        "prepared_panel_unique_counties": int(panel_frame.county_geoid.nunique()),
        "geography_gate_rows": geography_rows,
        "acquisition_and_preparation_counts": {
            "api_response_objects": api_response_objects,
            "raw_api_records_including_non_fips_aggregates": raw_records,
            "excluded_non_fips_aggregate_records": excluded_non_fips,
            "reported_fips_county_records": int(corn_prep["reported_county_records"])
            + int(soy_prep["reported_county_records"]),
            "corn_reported_fips_county_records": int(corn_prep["reported_county_records"]),
            "soy_reported_fips_county_records": int(soy_prep["reported_county_records"]),
            "suppressed_or_nonnumeric_fips_county_records": int(
                corn_prep["suppressed_or_nonnumeric_county_records"]
            ) + int(soy_prep["suppressed_or_nonnumeric_county_records"]),
            "zero_yield_rows_excluded_from_log_yield_panel": int(sum(
                panel_prep["excluded_zero_yield_rows_by_crop"].values()
            )),
            "prepared_positive_yield_panel_rows": panel_rows,
            "rows_removed_by_geography_calendar_gate": panel_rows
            - int(support_audit["eligible_practice_rows"]),
        },
        "inputs": {
            "nass_api_manifest": file_record(NASS_RAW_MANIFEST),
            "corn_preparation_receipt": file_record(CORN_PREP_RECEIPT),
            "soy_preparation_receipt": file_record(SOY_PREP_RECEIPT),
            "contract": file_record(CONTRACT),
            "prepared_panel": file_record(PANEL),
            "geography_gate": file_record(GEOGRAPHY),
            "fixed_calendar": file_record(DEFAULT_BOUND_CALENDAR),
            "panel_preparation_receipt": file_record(PANEL_PREP_RECEIPT),
            "geography_receipt": file_record(GEOGRAPHY_RECEIPT),
        },
        "script_lineage": {
            "route_launcher": file_record(Path(__file__)),
            "weight_builder": file_record(WEIGHT_BUILDER),
            "feature_builder": file_record(FEATURE_BUILDER),
            "feature_calculation_module": file_record(FEATURE_CALCULATION_MODULE),
        },
        "bounded_smoke": {
            "county_geoid": geoid,
            "harvest_year": year,
            "outcome_rows": int(len(frame)),
            "crop_county_years": int(frame.drop_duplicates(PAIR_KEYS).shape[0]),
            "irrigation_practice": "all_practices",
            "weather_exposure_application": (
                "one_county_crop_year_exposure_joined_to_one_all_practices_outcome"
            ),
            "weight_rows": int(weight_receipt["weight_rows"]),
            "weather_month_objects": int(len(feature_receipt["input_identity"]["weather_months"])),
            "weight_manifest": file_record(weight_manifest_path),
            "weight_output": file_record(weight_output),
            "weight_receipt": file_record(weight_receipt_path),
            "feature_output": file_record(feature_output),
            "feature_receipt": file_record(feature_receipt_path),
            "output_key_sha256": str(feature_receipt["output_key_sha256"]),
            "weight_input_fingerprint_sha256": str(weight_receipt["input_fingerprint_sha256"]),
            "feature_input_fingerprint_sha256": str(feature_receipt["input_fingerprint_sha256"]),
            "manifest_requested_counties": int(manifest["requested_county_count"]),
        },
        "raw_observations_embedded": False,
        "coefficients_emitted": False,
        "row_predictions_emitted": False,
        "relationship_estimated": False,
        "causal_effect_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    validate_tracked_smoke_receipt(receipt)
    atomic_write_json(output_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    weights = subparsers.add_parser("weights")
    weights.add_argument("--county-geoid", action="append")
    weights.add_argument("--all-counties", action="store_true")
    weights.add_argument("--force", action="store_true")
    feature = subparsers.add_parser("feature")
    feature.add_argument("--year", type=int, required=True)
    feature.add_argument("--county-geoid", action="append")
    feature.add_argument("--complete-year", action="store_true")
    feature.add_argument("--force", action="store_true")
    smoke = subparsers.add_parser("smoke")
    smoke.add_argument("--year", type=int, required=True)
    smoke.add_argument("--county-geoid", required=True)
    smoke.add_argument("--force", action="store_true")
    smoke.add_argument("--tracked-receipt", default=str(TRACKED_SMOKE_RECEIPT))
    args = parser.parse_args()

    if args.command == "weights":
        if bool(args.county_geoid) == bool(args.all_counties):
            raise ValueError("choose either explicit --county-geoid values or --all-counties")
        _, requested, _ = run_weights(
            None if args.all_counties else args.county_geoid, force=args.force
        )
        print(f"validated {len(requested)} isolated all-practice weight partitions; no response fit")
        return
    if args.command == "feature":
        if bool(args.county_geoid) == bool(args.complete_year):
            raise ValueError("choose either bounded --county-geoid values or --complete-year")
        frame, _, _, _ = run_feature(
            args.year, None if args.complete_year else args.county_geoid, force=args.force
        )
        print(f"validated {len(frame)} isolated all-practice feature rows; no response fit")
        return
    manifest, _, weight_manifest_path = run_weights([args.county_geoid], force=args.force)
    frame, feature_receipt, output, receipt_path = run_feature(
        args.year, [args.county_geoid], force=args.force
    )
    tracked_path = Path(args.tracked_receipt)
    write_tracked_smoke_receipt(
        geoid=args.county_geoid,
        year=args.year,
        manifest=manifest,
        frame=frame,
        feature_receipt=feature_receipt,
        feature_output=output,
        feature_receipt_path=receipt_path,
        weight_manifest_path=weight_manifest_path,
        output_path=tracked_path,
    )
    print(
        f"validated isolated all-practice smoke for {args.county_geoid}/{args.year}; "
        f"tracked receipt {relative_path(tracked_path)}; no response, damage, or SCC"
    )


if __name__ == "__main__":
    main()
