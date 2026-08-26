#!/usr/bin/env python3
"""Assemble only complete validated year partitions into the U.S. direct table.

The output is the locked direct-weather source for a later predictive
diagnostic.  Assembly does not fit that diagnostic or authorize causal,
damage, or SCC interpretation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from build_us_competing_moisture_inputs import (
    load_protocol as load_competing_protocol,
    require_bound_calendar,
    validate_calendar_source,
    validate_direct,
)
from build_us_national_county_nclimgrid_weights import (
    DEFAULT_CALENDAR,
    DEFAULT_GEOGRAPHY,
    DEFAULT_PANEL,
    _partition_paths as weight_partition_paths,
)
from build_us_national_nclimgrid_features import (
    DEFAULT_OUT_DIR as DEFAULT_PARTITION_DIR,
    DEFAULT_WEIGHT_DIR,
    SCHEMA as YEAR_SCHEMA,
    required_month_keys,
    validate_year_partition_checkpoint,
    validate_year_output,
)
from us_national_nclimgrid_common import (
    DEFAULT_BOUND_CALENDAR_RECEIPT,
    DEFAULT_COMPETING_PROTOCOL,
    DEFAULT_CONTRACT,
    DEFAULT_HTTP_INVENTORY,
    DEFAULT_RAW_WEATHER_DIR,
    DEFAULT_REVIEWED_PRODUCT,
    OUTCOME_KEYS,
    PROJECT_ROOT,
    atomic_write_json,
    atomic_write_parquet,
    canonical_sha256,
    load_contract,
    prepare_support,
    read_table,
    sha256_file,
    sha256_records,
    validate_acquired_months,
    validate_bound_calendar_receipt,
)


SCHEMA = "us_national_nclimgrid_feature_assembly_v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
DEFAULT_RECEIPT = PROJECT_ROOT / "outputs/us_county/national_nclimgrid_features_v1/assembly_validation.json"


def _year_paths(partition_dir: Path, year: int) -> tuple[Path, Path]:
    directory = partition_dir / f"harvest_year={year}"
    return directory / "features.parquet", directory / "receipt.json"


def load_complete_year_partition(
    partition_dir: Path,
    year: int,
    support: pd.DataFrame,
    *,
    contract_path: Path,
    panel_path: Path,
    geography_path: Path,
    calendar_path: Path,
    calendar_validation_path: Path,
    calendar_protocol_path: Path,
    weight_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    output, receipt_path = _year_paths(partition_dir, year)
    if not output.is_file() or not receipt_path.is_file():
        raise ValueError(f"harvest year {year} lacks a complete feature partition")
    calendar_raw = read_table(calendar_path)
    calendar_selected = calendar_raw.loc[
        calendar_raw.calendar_role.astype("string").eq("fixed_primary")
        & pd.to_numeric(calendar_raw.harvest_year, errors="raise").eq(year)
    ].copy()
    required_calendar = support[["state", "outcome_crop", "harvest_year"]].drop_duplicates()
    expected_seasons = required_calendar.merge(
        calendar_selected.rename(columns={"calendar_crop": "outcome_crop"}),
        on=["state", "outcome_crop", "harvest_year"], how="left", validate="many_to_one",
    ).rename(columns={"outcome_crop": "calendar_crop"})
    if expected_seasons.season_start.isna().any():
        raise ValueError(f"harvest year {year} lacks a bound calendar row")
    frame, receipt = validate_year_partition_checkpoint(
        output, receipt_path, support, expected_seasons=expected_seasons
    )
    if receipt.get("schema") != YEAR_SCHEMA or int(receipt.get("harvest_year", -1)) != year:
        raise ValueError(f"harvest year {year} receipt identity changed")
    if receipt.get("bounded_smoke") is not False or receipt.get("complete_year_support") is not True:
        raise ValueError(f"harvest year {year} is only a bounded smoke")
    identity = receipt.get("input_identity")
    if not isinstance(identity, dict) or canonical_sha256(identity) != receipt.get("input_fingerprint_sha256"):
        raise ValueError(f"harvest year {year} input fingerprint does not reconcile")
    expected_top = {
        "schema": YEAR_SCHEMA,
        "harvest_year": year,
        "bounded_smoke_geoids": None,
        "contract_sha256": sha256_file(contract_path),
        "panel_sha256": sha256_file(panel_path),
        "geography_sha256": sha256_file(geography_path),
        "calendar_sha256": sha256_file(calendar_path),
        "calendar_validation_sha256": sha256_file(calendar_validation_path),
        "calendar_protocol_sha256": sha256_file(calendar_protocol_path),
        "calendar_receipt_status": validate_bound_calendar_receipt(
            calendar_path, calendar_validation_path, calendar_protocol_path
        )["status"],
        "builder_sha256": sha256_file(Path(__file__).with_name(
            "build_us_national_nclimgrid_features.py"
        )),
        "support_outcome_key_sha256": sha256_records(support, OUTCOME_KEYS),
    }
    for key, expected in expected_top.items():
        if identity.get(key) != expected:
            raise ValueError(f"harvest year {year} input identity differs on {key}")
    month_records = identity.get("weather_months")
    weight_records = identity.get("weight_partitions")
    if not isinstance(month_records, list) or not isinstance(weight_records, list):
        raise ValueError(f"harvest year {year} receipt lacks weather/weight lineage")
    month_keys = [(int(record["year"]), int(record["month"])) for record in month_records]
    if month_keys != required_month_keys(
        expected_seasons
    ):
        raise ValueError(f"harvest year {year} receipt weather-month scope changed")
    expected_geoids = sorted(support.county_geoid.astype(str).unique().tolist())
    observed_geoids = sorted(str(record["county_geoid"]) for record in weight_records)
    if observed_geoids != expected_geoids or len(observed_geoids) != len(set(observed_geoids)):
        raise ValueError(f"harvest year {year} receipt weight-county scope changed")
    for record in weight_records:
        geoid = str(record["county_geoid"])
        weight_output, weight_receipt = weight_partition_paths(weight_dir, geoid)
        if not weight_output.is_file() or not weight_receipt.is_file():
            raise ValueError(f"harvest year {year} weight partition disappeared for {geoid}")
        if sha256_file(weight_output) != str(record["output_sha256"]):
            raise ValueError(f"harvest year {year} weight output hash changed for {geoid}")
        current_weight_receipt = json.loads(weight_receipt.read_text(encoding="utf-8"))
        if current_weight_receipt.get("input_fingerprint_sha256") != record["input_fingerprint_sha256"]:
            raise ValueError(f"harvest year {year} weight receipt changed for {geoid}")
    if sha256_file(output) != receipt.get("output_sha256"):
        raise ValueError(f"harvest year {year} feature output hash changed")
    validate_year_output(frame, support)
    if sha256_records(frame, OUTCOME_KEYS) != receipt.get("output_key_sha256"):
        raise ValueError(f"harvest year {year} feature keys differ from its receipt")
    return frame, receipt


def assemble(
    *,
    panel_path: Path,
    geography_path: Path,
    calendar_path: Path,
    calendar_validation_path: Path,
    contract_path: Path,
    calendar_protocol_path: Path,
    partition_dir: Path,
    weight_dir: Path,
    revalidate_raw: bool,
    inventory_path: Path,
    reviewed_product_path: Path,
    raw_weather_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    contract = load_contract(contract_path)
    calendar_receipt = validate_bound_calendar_receipt(
        calendar_path, calendar_validation_path, calendar_protocol_path
    )
    support, seasons, sample_audit = prepare_support(
        read_table(panel_path), read_table(geography_path), read_table(calendar_path), contract
    )
    frames: list[pd.DataFrame] = []
    partition_receipts: list[dict[str, Any]] = []
    raw_months: set[tuple[int, int]] = set()
    receipt_raw_identity: dict[tuple[int, int], dict[str, Any]] = {}
    years = sorted(support.harvest_year.unique().tolist())
    expected_years = list(range(int(contract["sample"]["year_min"]), int(contract["sample"]["year_max"]) + 1))
    if years != expected_years:
        raise ValueError("national outcome support does not populate every registered year")
    for year in years:
        year_support = support.loc[support.harvest_year.eq(year)].copy()
        frame, receipt = load_complete_year_partition(
            partition_dir, int(year), year_support,
            contract_path=contract_path, panel_path=panel_path,
            geography_path=geography_path, calendar_path=calendar_path,
            calendar_validation_path=calendar_validation_path,
            calendar_protocol_path=calendar_protocol_path, weight_dir=weight_dir,
        )
        frames.append(frame)
        partition_receipts.append(
            {
                "harvest_year": int(year),
                "output_sha256": str(receipt["output_sha256"]),
                "input_fingerprint_sha256": str(receipt["input_fingerprint_sha256"]),
            }
        )
        for record in receipt["input_identity"]["weather_months"]:
            key = (int(record["year"]), int(record["month"]))
            existing = receipt_raw_identity.get(key)
            if existing is not None and existing != record:
                raise ValueError(f"year receipts disagree on raw weather identity {key}")
            receipt_raw_identity[key] = record
            raw_months.add(key)
    raw_validation: dict[str, Any]
    if revalidate_raw:
        _, raw_records = validate_acquired_months(
            sorted(raw_months), inventory_path=inventory_path,
            reviewed_product_path=reviewed_product_path, raw_weather_dir=raw_weather_dir,
        )
        current_raw_identity = {
            (int(record["year"]), int(record["month"])): record
            for record in raw_records
        }
        if current_raw_identity != receipt_raw_identity:
            raise ValueError("current raw weather identities differ from year receipts")
        raw_validation = {
            "performed": True,
            "objects": len(raw_records),
            "object_identity_sha256": canonical_sha256(raw_records),
        }
    else:
        raw_validation = {
            "performed": False,
            "limitation": "year receipts checked, but raw monthly payloads were not rehashed in assembly",
        }
    combined = pd.concat(frames, ignore_index=True).sort_values(OUTCOME_KEYS).reset_index(drop=True)
    if combined.duplicated(OUTCOME_KEYS).any() or len(combined) != len(support):
        raise ValueError("assembled output does not have one row per exact outcome key")
    competing_protocol = load_competing_protocol(calendar_protocol_path)
    validated_calendar = validate_calendar_source(read_table(calendar_path), competing_protocol)
    validated_direct = validate_direct(combined, competing_protocol)
    require_bound_calendar(validated_direct, validated_calendar, "assembled direct-weather input")
    if set(map(tuple, validated_direct[OUTCOME_KEYS].itertuples(index=False, name=None))) != set(
        map(tuple, support[OUTCOME_KEYS].itertuples(index=False, name=None))
    ):
        raise ValueError("competing-moisture direct schema changes the national outcome support")
    audit = {
        "schema": SCHEMA,
        "status": "complete_national_direct_weather_table_validated_not_fitted",
        "registered_sample": sample_audit,
        "assembled_rows": int(len(combined)),
        "assembled_counties": int(combined.county_geoid.nunique()),
        "assembled_years": years,
        "partition_receipts": partition_receipts,
        "calendar_receipt_status": calendar_receipt["status"],
        "calendar_receipt_sha256": sha256_file(calendar_validation_path),
        "competing_moisture_schema_rows": int(len(validated_direct)),
        "raw_payload_revalidation": raw_validation,
        "coefficients_emitted": False,
        "row_predictions_emitted": False,
        "relationship_estimated": False,
        "causal_effect_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    return combined, audit


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--geography", default=str(DEFAULT_GEOGRAPHY))
    parser.add_argument("--calendar", default=str(DEFAULT_CALENDAR))
    parser.add_argument("--calendar-validation", default=str(DEFAULT_BOUND_CALENDAR_RECEIPT))
    parser.add_argument("--calendar-protocol", default=str(DEFAULT_COMPETING_PROTOCOL))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--partition-dir", default=str(DEFAULT_PARTITION_DIR))
    parser.add_argument("--weight-dir", default=str(DEFAULT_WEIGHT_DIR))
    parser.add_argument("--inventory", default=str(DEFAULT_HTTP_INVENTORY))
    parser.add_argument("--reviewed-product", default=str(DEFAULT_REVIEWED_PRODUCT))
    parser.add_argument("--raw-weather-dir", default=str(DEFAULT_RAW_WEATHER_DIR))
    parser.add_argument(
        "--skip-raw-revalidation", action="store_true",
        help="development-only: trust year receipts instead of rehashing all raw months",
    )


def assemble_from_args(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    return assemble(
        panel_path=Path(args.panel), geography_path=Path(args.geography),
        calendar_path=Path(args.calendar), calendar_validation_path=Path(args.calendar_validation),
        contract_path=Path(args.contract), calendar_protocol_path=Path(args.calendar_protocol),
        partition_dir=Path(args.partition_dir), weight_dir=Path(args.weight_dir),
        revalidate_raw=not args.skip_raw_revalidation,
        inventory_path=Path(args.inventory), reviewed_product_path=Path(args.reviewed_product),
        raw_weather_dir=Path(args.raw_weather_dir),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--receipt-out", default=str(DEFAULT_RECEIPT))
    args = parser.parse_args()
    combined, audit = assemble_from_args(args)
    output = Path(args.out)
    atomic_write_parquet(output, combined)
    audit["output"] = {
        "path": str(output), "sha256": sha256_file(output),
        "outcome_key_sha256": sha256_records(combined, OUTCOME_KEYS),
    }
    atomic_write_json(Path(args.receipt_out), audit)
    print(
        f"assembled {len(combined)} validated direct-weather rows; "
        "no fit, causal effect, damage, or SCC"
    )


if __name__ == "__main__":
    main()
