#!/usr/bin/env python3
"""Build isolated all-practice U.S. nClimGrid feature partitions.

The reviewed direct-practice calculation module supplies the cell-first
weather algorithms.  This adapter enforces exactly one ``all_practices``
outcome per crop-county-year and emits route-specific metadata and receipts;
it never labels a singleton outcome as weather shared across practices.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

import build_us_national_nclimgrid_features as direct_core
from build_us_national_county_nclimgrid_weights import (
    DEFAULT_COUNTIES,
    DEFAULT_REFERENCE,
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


SCHEMA = "us_national_all_practice_nclimgrid_feature_year_partition_v1"
ROUTE_ID = "us_national_all_practice_nclimgrid_features_v1"
EXPOSURE_APPLICATION = (
    "one_county_crop_year_exposure_joined_to_one_all_practices_outcome"
)
CALCULATION_MODULE = Path(direct_core.__file__).resolve()
DEFAULT_PANEL = PROJECT_ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet"
DEFAULT_GEOGRAPHY = PROJECT_ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019_geography_gate.csv"
DEFAULT_CONTRACT = PROJECT_ROOT / "us_county_validation/us_national_all_practice_nclimgrid_features_v1.toml"
DEFAULT_WEIGHT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_polygon_weights_national_all_practice_v1"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_features_national_all_practice_v1"


def require_all_practice_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("contract_id") != ROUTE_ID:
        raise ValueError("all-practice feature builder received another contract identity")
    if set(map(str, contract["sample"]["irrigation_practices"])) != {"all_practices"}:
        raise ValueError("all-practice feature builder received another practice scope")


def build_all_practice_year_panel(
    support: pd.DataFrame,
    seasons: pd.DataFrame,
    weights: pd.DataFrame,
    cells: pd.DataFrame,
    dates: pd.DatetimeIndex,
    climate: dict[str, Any],
    contract: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the reviewed calculations and replace paired-practice metadata."""
    require_all_practice_contract(contract)
    if set(support.irrigation_practice.astype(str)) != {"all_practices"}:
        raise ValueError("all-practice year support contains another practice")
    if support.duplicated(PAIR_KEYS).any():
        raise ValueError("all-practice year support duplicates crop-county-year keys")
    frame, audit = direct_core.build_year_panel(
        support, seasons, weights, cells, dates, climate, contract
    )
    if "weather_exposure_shared_across_practices" not in frame or not frame[
        "weather_exposure_shared_across_practices"
    ].astype(bool).all():
        raise ValueError("calculation module no longer emits its reviewed exposure marker")
    frame = frame.drop(columns="weather_exposure_shared_across_practices")
    frame["weather_exposure_application"] = EXPOSURE_APPLICATION
    audit = dict(audit)
    if audit.pop("weather_exposure_shared_across_practices", None) is not True:
        raise ValueError("calculation-module audit no longer emits its reviewed exposure marker")
    audit["single_all_practices_outcome_per_crop_county_year"] = True
    audit["weather_exposure_application"] = EXPOSURE_APPLICATION
    return frame.sort_values(OUTCOME_KEYS).reset_index(drop=True), audit


def validate_all_practice_year_output(frame: pd.DataFrame, support: pd.DataFrame) -> None:
    if set(support.irrigation_practice.astype(str)) != {"all_practices"}:
        raise ValueError("all-practice output validator received another practice scope")
    if frame.empty or frame.duplicated(PAIR_KEYS).any():
        raise ValueError("all-practice year output is empty or duplicates crop-county-year keys")
    if set(frame.irrigation_practice.astype(str)) != {"all_practices"}:
        raise ValueError("all-practice year output contains another practice")
    if "weather_exposure_shared_across_practices" in frame:
        raise ValueError("single all-practice output incorrectly claims shared practices")
    if "weather_exposure_application" not in frame or set(
        frame.weather_exposure_application.astype(str)
    ) != {EXPOSURE_APPLICATION}:
        raise ValueError("all-practice year output lacks exact exposure-application metadata")
    direct_projection = frame.drop(columns="weather_exposure_application").assign(
        weather_exposure_shared_across_practices=True
    )
    direct_core.validate_year_output(direct_projection, support)


def validate_year_partition_checkpoint(
    output: Path,
    receipt_path: Path,
    support: pd.DataFrame,
    *,
    expected_identity: Mapping[str, Any] | None = None,
    expected_national_sample: Mapping[str, Any] | None = None,
    expected_seasons: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not output.is_file() or not receipt_path.is_file():
        raise ValueError("all-practice year partition output or receipt is absent")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("all-practice year partition receipt is unreadable") from error
    identity = receipt.get("input_identity")
    if receipt.get("schema") != SCHEMA or not isinstance(identity, dict):
        raise ValueError("all-practice year partition receipt schema/input identity changed")
    if canonical_sha256(identity) != receipt.get("input_fingerprint_sha256"):
        raise ValueError("all-practice year partition input fingerprint does not reconcile")
    if expected_identity is not None and identity != dict(expected_identity):
        raise ValueError("all-practice year partition differs from current exact input identity")
    if identity.get("builder_sha256") != sha256_file(Path(__file__)):
        raise ValueError("all-practice year partition builder hash changed")
    if identity.get("calculation_module_sha256") != sha256_file(CALCULATION_MODULE):
        raise ValueError("all-practice year partition calculation-module hash changed")
    if support.empty or support.harvest_year.nunique() != 1:
        raise ValueError("all-practice checkpoint requires one nonempty support year")
    year = int(support.harvest_year.iloc[0])
    if int(receipt.get("harvest_year", -1)) != year or int(identity.get("harvest_year", -1)) != year:
        raise ValueError("all-practice year partition harvest year changed")
    bounded_geoids = identity.get("bounded_smoke_geoids")
    expected_bounded = bounded_geoids is not None
    if receipt.get("bounded_smoke") is not expected_bounded:
        raise ValueError("all-practice partition bounded-smoke flag does not reconcile")
    if receipt.get("complete_year_support") is not (not expected_bounded):
        raise ValueError("all-practice partition complete-support flag does not reconcile")
    if receipt.get("bounded_smoke_geoids") != bounded_geoids:
        raise ValueError("all-practice partition bounded-smoke GEOIDs do not reconcile")
    if expected_national_sample is not None and receipt.get("registered_national_sample") != dict(
        expected_national_sample
    ):
        raise ValueError("all-practice partition registered national sample changed")
    if receipt.get("output_sha256") != sha256_file(output):
        raise ValueError("all-practice partition output hash changed")
    frame = pd.read_parquet(output)
    validate_all_practice_year_output(frame, support)
    if expected_seasons is not None:
        direct_core.validate_output_calendar(frame, expected_seasons)
    if receipt.get("output_key_sha256") != sha256_records(frame, OUTCOME_KEYS):
        raise ValueError("all-practice partition output-key hash changed")
    audit = receipt.get("build_audit")
    if not isinstance(audit, dict):
        raise ValueError("all-practice partition lacks its build audit")
    expected_audit = {
        "harvest_year": year,
        "counties": int(frame.county_geoid.nunique()),
        "crop_county_years": int(frame.drop_duplicates(PAIR_KEYS).shape[0]),
        "practice_rows": int(len(frame)),
        "corn_crop_county_years": int(frame.outcome_crop.eq("corn_grain").sum()),
        "soy_crop_county_years": int(frame.outcome_crop.eq("soybeans").sum()),
    }
    for key, expected in expected_audit.items():
        if audit.get(key) != expected:
            raise ValueError(f"all-practice build audit differs on {key}")
    if audit.get("cell_first_nonlinear_basis") is not True:
        raise ValueError("all-practice build audit lacks cell-first basis confirmation")
    if "weather_exposure_shared_across_practices" in audit:
        raise ValueError("all-practice build audit incorrectly claims shared practices")
    if audit.get("single_all_practices_outcome_per_crop_county_year") is not True:
        raise ValueError("all-practice build audit lacks its one-row key invariant")
    if audit.get("weather_exposure_application") != EXPOSURE_APPLICATION:
        raise ValueError("all-practice build audit exposure metadata changed")
    for key in ["relationship_estimated", "response_estimation_authorized", "scc_authorized"]:
        if audit.get(key) is not False or receipt.get(key) is not False:
            raise ValueError(f"all-practice partition unexpectedly sets {key}")
    if receipt.get("damage_estimated") is not False:
        raise ValueError("all-practice partition unexpectedly claims damage estimation")
    return frame, receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--geography", default=str(DEFAULT_GEOGRAPHY))
    parser.add_argument("--calendar", default=str(DEFAULT_BOUND_CALENDAR))
    parser.add_argument("--calendar-validation", default=str(DEFAULT_BOUND_CALENDAR_RECEIPT))
    parser.add_argument("--calendar-protocol", default=str(DEFAULT_COMPETING_PROTOCOL))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--counties", default=str(DEFAULT_COUNTIES))
    parser.add_argument("--reference-climate", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--weight-dir", default=str(DEFAULT_WEIGHT_DIR))
    parser.add_argument("--inventory", default=str(DEFAULT_HTTP_INVENTORY))
    parser.add_argument("--reviewed-product", default=str(DEFAULT_REVIEWED_PRODUCT))
    parser.add_argument("--raw-weather-dir", default=str(DEFAULT_RAW_WEATHER_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--county-geoid", action="append")
    parser.add_argument("--bounded-smoke", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    paths = {
        "panel": Path(args.panel), "geography": Path(args.geography),
        "calendar": Path(args.calendar), "contract": Path(args.contract),
        "counties": Path(args.counties), "reference_climate": Path(args.reference_climate),
    }
    contract = load_contract(paths["contract"])
    require_all_practice_contract(contract)
    calendar_receipt = validate_bound_calendar_receipt(
        paths["calendar"], Path(args.calendar_validation), Path(args.calendar_protocol)
    )
    if not int(contract["sample"]["year_min"]) <= args.year <= int(
        contract["sample"]["year_max"]
    ):
        raise ValueError("requested harvest year lies outside the all-practice contract")
    support, seasons, national_audit = prepare_support(
        read_table(paths["panel"]), read_table(paths["geography"]),
        read_table(paths["calendar"]), contract,
    )
    year_support = support.loc[support.harvest_year.eq(args.year)].copy()
    year_seasons = seasons.loc[seasons.harvest_year.eq(args.year)].copy()
    bounded_geoids: list[str] | None = None
    if args.county_geoid:
        if not args.bounded_smoke:
            raise ValueError("county subsets require --bounded-smoke")
        bounded_geoids = sorted(dict.fromkeys(args.county_geoid))
        unknown = sorted(set(bounded_geoids) - set(year_support.county_geoid.astype(str)))
        if unknown:
            raise ValueError(f"bounded-smoke counties lack all-practice support: {unknown}")
        year_support = year_support.loc[year_support.county_geoid.isin(bounded_geoids)].copy()
        required_calendar = year_support[["state", "outcome_crop", "harvest_year"]].drop_duplicates()
        year_seasons = required_calendar.merge(
            year_seasons.rename(columns={"calendar_crop": "outcome_crop"}),
            on=["state", "outcome_crop", "harvest_year"], how="left", validate="many_to_one",
        ).rename(columns={"outcome_crop": "calendar_crop"})
    elif args.bounded_smoke:
        raise ValueError("--bounded-smoke requires at least one --county-geoid")
    if year_support.empty or year_support.duplicated(PAIR_KEYS).any():
        raise ValueError("requested all-practice year/subset is empty or duplicates keys")

    reference_paths, reference_records = validate_acquired_months(
        [(1981, 1)], inventory_path=Path(args.inventory),
        reviewed_product_path=Path(args.reviewed_product),
        raw_weather_dir=Path(args.raw_weather_dir),
    )
    if paths["reference_climate"].resolve() != reference_paths[0].resolve():
        raise ValueError("weight reference climate differs from the validated acquisition object")
    weight_lineage_support = support.loc[
        support.county_geoid.isin(year_support.county_geoid.unique())
    ].copy()
    weights, weight_receipts = direct_core.validate_weight_partitions(
        Path(args.weight_dir), weight_lineage_support,
        contract_path=paths["contract"], panel_path=paths["panel"],
        geography_path=paths["geography"], calendar_path=paths["calendar"],
        calendar_validation_path=Path(args.calendar_validation),
        calendar_protocol_path=Path(args.calendar_protocol),
        counties_path=paths["counties"], reference_identity=reference_records[0],
    )
    months = direct_core.required_month_keys(year_seasons)
    climate_paths, climate_records = validate_acquired_months(
        months, inventory_path=Path(args.inventory),
        reviewed_product_path=Path(args.reviewed_product),
        raw_weather_dir=Path(args.raw_weather_dir),
    )
    cells = (
        weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]]
        .drop_duplicates().sort_values(["grid_lat_index", "grid_lon_index"])
        .reset_index(drop=True)
    )
    input_identity = {
        "schema": SCHEMA,
        "harvest_year": args.year,
        "bounded_smoke_geoids": bounded_geoids,
        "contract_sha256": sha256_file(paths["contract"]),
        "panel_sha256": sha256_file(paths["panel"]),
        "geography_sha256": sha256_file(paths["geography"]),
        "calendar_sha256": sha256_file(paths["calendar"]),
        "calendar_validation_sha256": sha256_file(Path(args.calendar_validation)),
        "calendar_protocol_sha256": sha256_file(Path(args.calendar_protocol)),
        "calendar_receipt_status": calendar_receipt["status"],
        "builder_sha256": sha256_file(Path(__file__)),
        "calculation_module_sha256": sha256_file(CALCULATION_MODULE),
        "support_outcome_key_sha256": sha256_records(year_support, OUTCOME_KEYS),
        "weather_months": climate_records,
        "weight_partitions": weight_receipts,
    }
    fingerprint = canonical_sha256(input_identity)
    output, receipt_path = direct_core._default_partition_paths(
        Path(args.out_dir), args.year, bounded_geoids
    )
    if not args.force and output.is_file() and receipt_path.is_file():
        try:
            existing, _ = validate_year_partition_checkpoint(
                output, receipt_path, year_support, expected_identity=input_identity,
                expected_national_sample=national_audit, expected_seasons=year_seasons,
            )
            print(
                f"resumed validated {args.year} all-practice partition with {len(existing)} rows; "
                "no response estimated"
            )
            return
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass

    dates, climate = direct_core.load_daily_unique_cells(climate_paths, cells)
    panel, build_audit = build_all_practice_year_panel(
        year_support, year_seasons, weights, cells, dates, climate, contract
    )
    validate_all_practice_year_output(panel, year_support)
    direct_core.validate_output_calendar(panel, year_seasons)
    atomic_write_parquet(output, panel)
    receipt = {
        "schema": SCHEMA,
        "harvest_year": args.year,
        "bounded_smoke": bounded_geoids is not None,
        "bounded_smoke_geoids": bounded_geoids,
        "complete_year_support": bounded_geoids is None,
        "input_fingerprint_sha256": fingerprint,
        "input_identity": input_identity,
        "output_path": str(output),
        "output_sha256": sha256_file(output),
        "output_key_sha256": sha256_records(panel, OUTCOME_KEYS),
        "build_audit": build_audit,
        "registered_national_sample": national_audit,
        "county_proxy_interpretation": (
            "fixed 2019 legal county polygon area average, not crop-pixel or average-farm weather"
        ),
        "stage_interpretation": "equal-duration engineering proxy, not observed phenology",
        "outcome_interpretation": "one all-production-practices yield; not direct rainfed yield",
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    atomic_write_json(receipt_path, receipt)
    print(
        f"wrote {len(panel)} all-practice rows for harvest year {args.year}; "
        f"bounded_smoke={bounded_geoids is not None}; no response estimated"
    )


if __name__ == "__main__":
    main()
