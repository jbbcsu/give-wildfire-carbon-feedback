#!/usr/bin/env python3
"""Shared fail-closed gates for national U.S. nClimGrid feature construction.

This module supports two deliberately separate outcome routes: the regional
direct-practice panel and the national all-practice panel.  It checks each
route's exact practice set, calendar, geography, and registered counts.  It
does not read weather, fit a response, calculate damages, or authorize SCC use.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

import acquire_nclimgrid_daily_bulk as bulk
import inventory_nclimgrid_daily_http as http_inventory
from build_county_polygon_nclimgrid_weights import STATE_FIPS_TO_ALPHA


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "us_county_validation/us_national_nclimgrid_features_v1.toml"
DEFAULT_HTTP_INVENTORY = PROJECT_ROOT / "data/provenance/nclimgrid_daily_1981_2019_http_inventory.csv"
DEFAULT_REVIEWED_PRODUCT = PROJECT_ROOT / "data/provenance/nclimgrid_daily_198101.toml"
DEFAULT_RAW_WEATHER_DIR = PROJECT_ROOT / "data/raw/us_county/nclimgrid_daily"
DEFAULT_BOUND_CALENDAR = PROJECT_ROOT / "data/interim/us_county/nass_usual_date_calendars_1981_2022.csv"
DEFAULT_BOUND_CALENDAR_RECEIPT = (
    PROJECT_ROOT / "outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json"
)
DEFAULT_COMPETING_PROTOCOL = PROJECT_ROOT / "us_county_validation/us_competing_moisture_predictive_v1.toml"

PAIR_KEYS = ["county_geoid", "outcome_crop", "harvest_year"]
OUTCOME_KEYS = PAIR_KEYS + ["irrigation_practice"]
EXPECTED_CONTRACT_TOP = {
    "schema_version", "contract_id", "analysis_role",
    "feature_construction_authorized", "response_estimation_authorized",
    "causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized",
    "sample", "weather", "calendar", "partitioning", "scientific_boundary",
}


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype={"county_geoid": "string"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def sha256_records(frame: pd.DataFrame, columns: list[str]) -> str:
    ordered = frame.loc[:, columns].sort_values(columns).reset_index(drop=True)
    payload = ordered.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_acquired_months(
    keys: list[tuple[int, int]],
    *,
    inventory_path: Path = DEFAULT_HTTP_INVENTORY,
    reviewed_product_path: Path = DEFAULT_REVIEWED_PRODUCT,
    raw_weather_dir: Path = DEFAULT_RAW_WEATHER_DIR,
    revalidate_netcdf: bool = True,
) -> tuple[list[Path], list[dict[str, Any]]]:
    """Verify requested local months against the reviewed inventory/manifest.

    This intentionally validates only the months used by one derived partition;
    a concurrently growing acquisition manifest therefore cannot invalidate an
    already completed year.  Each needed object must already be a validated
    immutable checkpoint; an unmanifested file or ``.part`` fails closed.
    """
    if not keys or len(set(keys)) != len(keys) or keys != sorted(keys):
        raise ValueError("requested weather months must be unique and chronological")
    rows = http_inventory.load_inventory(inventory_path, require_complete=True)
    inventory_sha512 = bulk.smoke.sha512_file(inventory_path)
    if inventory_sha512 != bulk.REVIEWED_INVENTORY_SHA512:
        raise RuntimeError("nClimGrid HTTP inventory differs from its reviewed SHA-512")
    product = bulk.load_reviewed_product_record(reviewed_product_path)
    manifest_path = raw_weather_dir / bulk.MANIFEST_NAME
    records = bulk.load_acquisition_manifest(
        manifest_path,
        rows=rows,
        inventory_name=inventory_path.name,
        inventory_sha512=inventory_sha512,
        product=product,
    )
    paths: list[Path] = []
    identities: list[dict[str, Any]] = []
    for key in keys:
        row = rows.get(key)
        record = records.get(key)
        if row is None:
            raise RuntimeError(f"requested month {key} lies outside the reviewed inventory")
        if record is None:
            raise RuntimeError(f"requested month {key} is not in the validated acquisition manifest")
        path = raw_weather_dir / row.name
        part = raw_weather_dir / (row.name + ".part")
        if part.exists():
            raise RuntimeError(f"requested month has an unresolved partial object: {part.name}")
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"validated nClimGrid object is absent: {path}")
        if path.stat().st_size != int(record["size_bytes"]):
            raise RuntimeError(f"validated nClimGrid size changed: {path.name}")
        digest = bulk.smoke.sha512_file(path)
        if digest != str(record["local_sha512"]):
            raise RuntimeError(f"validated nClimGrid SHA-512 changed: {path.name}")
        if revalidate_netcdf:
            _, details = bulk.validate_local_payload(
                path, row, expected_sha512=str(record["local_sha512"])
            )
            if details != record["netcdf_validation"]:
                raise RuntimeError(f"validated nClimGrid schema receipt changed: {path.name}")
        paths.append(path)
        identities.append(
            {
                "year": int(key[0]),
                "month": int(key[1]),
                "name": row.name,
                "canonical_url": row.canonical_url,
                "content_length": int(row.content_length),
                "etag": row.etag,
                "last_modified": row.last_modified,
                "local_sha512": str(record["local_sha512"]),
                "inventory_sha512": inventory_sha512,
                "reviewed_product_record_sha512": str(product["sha512"]),
                "product_version": str(record["product_version"]),
                "license": record["license"],
                "relationship_estimated": False,
                "scc_authorized": False,
            }
        )
    return paths, identities


def validate_bound_calendar_receipt(
    calendar_path: Path,
    receipt_path: Path = DEFAULT_BOUND_CALENDAR_RECEIPT,
    protocol_path: Path = DEFAULT_COMPETING_PROTOCOL,
) -> dict[str, Any]:
    """Recompute the exact shared calendar receipt used by the U.S. diagnostic."""
    from build_us_competing_moisture_inputs import validate_source_receipt

    receipt = validate_source_receipt(
        receipt_path, calendar_path, "calendar", protocol_path
    )
    if receipt.get("family") != "calendar":
        raise ValueError("bound calendar receipt has the wrong source family")
    if receipt.get("upstream_raw_daily_monthly_or_calendar_pdf_recomputed") is not False:
        raise ValueError("calendar receipt overstates upstream PDF recomputation")
    return receipt


def strict_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing booleans")
        return series.astype(bool)
    text = series.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return text.eq("true")


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    try:
        contract = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read national weather contract {path}") from error
    if set(contract) != EXPECTED_CONTRACT_TOP:
        raise ValueError("national weather contract top-level fields changed")
    contract_id = str(contract.get("contract_id"))
    allowed_contracts = {
        "us_national_nclimgrid_features_v1": {"irrigated", "non_irrigated"},
        "us_national_all_practice_nclimgrid_features_v1": {"all_practices"},
    }
    if contract["schema_version"] != 1 or contract_id not in allowed_contracts:
        raise ValueError("national weather contract identity changed")
    if contract["analysis_role"] != "historical_us_county_weather_feature_construction_only":
        raise ValueError("national weather analysis role changed")
    if contract["feature_construction_authorized"] is not True:
        raise ValueError("national weather feature construction is not authorized")
    for gate in [
        "response_estimation_authorized", "causal_claim_authorized",
        "damage_claim_authorized", "scc_claim_authorized",
    ]:
        if contract[gate] is not False:
            raise ValueError(f"national weather contract unexpectedly authorizes {gate}")
    sample = contract["sample"]
    if set(map(str, sample["crops"])) != {"corn_grain", "soybeans"}:
        raise ValueError("national weather contract crop scope changed")
    if set(map(str, sample["irrigation_practices"])) != allowed_contracts[contract_id]:
        raise ValueError("national weather practice scope changed")
    if int(sample["year_min"]) != 1981 or int(sample["year_max"]) != 2019:
        raise ValueError("national weather year scope changed")
    weather = contract["weather"]
    if float(weather["wet_day_threshold_mm"]) != 1.0:
        raise ValueError("national weather wet-day threshold changed")
    if weather["spatial_weight_role"] != "county_polygon_primary_proxy":
        raise ValueError("national weather spatial route changed")
    if weather["crop_pixel_exposure"] is not False:
        raise ValueError("county-polygon primary route cannot claim crop-pixel exposure")
    if float(weather["minimum_weather_valid_area_relative_to_declared_land"]) != 0.95:
        raise ValueError("national weather-valid land-coverage gate changed")
    if float(weather["minimum_geometric_grid_coverage"]) != 0.999:
        raise ValueError("national geometric grid-coverage gate changed")
    if float(weather["maximum_declared_area_relative_error"]) != 0.03:
        raise ValueError("national declared-area reconciliation gate changed")
    if weather["reference_validity_mask"] != (
        "finite prcp/tavg/tmin/tmax on every day of the validated January 1981 grid object"
    ):
        raise ValueError("national reference weather-validity mask changed")
    if int(weather["reference_valid_grid_cells"]) != 469758:
        raise ValueError("national reference weather-valid grid-cell count changed")
    return contract


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    if missing := columns - set(frame.columns):
        raise ValueError(f"{label} lacks columns {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{label} is empty")


def prepare_support(
    panel: pd.DataFrame,
    geography: pd.DataFrame,
    calendar: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    enforce_registered_counts: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return eligible long outcomes and exact fixed calendar rows.

    The upstream NASS inventory is deliberately feature-ineligible before the
    independent geography gate.  Eligibility here is the conjunction of exact
    paired outcomes, named crop/calendar support, and the geography screen; it
    does not authorize fitting.
    """
    sample = contract["sample"]
    weather = contract["weather"]
    calendar_contract = contract["calendar"]
    crops = set(map(str, sample["crops"]))
    practices = set(map(str, sample["irrigation_practices"]))
    year_min, year_max = int(sample["year_min"]), int(sample["year_max"])

    _require_columns(
        panel,
        {
            *OUTCOME_KEYS, "state", "county_name", "yield_bu_acre",
            "outcome_source_id", "response_estimation_authorized", "scc_authorized",
        },
        "NASS outcome panel",
    )
    outcomes = panel.copy()
    outcomes["county_geoid"] = outcomes.county_geoid.astype("string").str.strip()
    outcomes["state"] = outcomes.state.astype("string").str.strip().str.upper()
    outcomes["county_name"] = outcomes.county_name.astype("string").str.strip()
    outcomes["outcome_crop"] = outcomes.outcome_crop.astype("string").str.strip()
    outcomes["irrigation_practice"] = outcomes.irrigation_practice.astype("string").str.strip()
    outcomes["harvest_year"] = pd.to_numeric(outcomes.harvest_year, errors="raise").astype("int64")
    outcomes["yield_bu_acre"] = pd.to_numeric(outcomes.yield_bu_acre, errors="raise")
    if outcomes.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("NASS outcome panel contains malformed GEOIDs")
    if outcomes.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("NASS outcome panel contains malformed states")
    outcome_fips_state = outcomes.county_geoid.str[:2].map(STATE_FIPS_TO_ALPHA)
    if outcome_fips_state.isna().any() or not outcome_fips_state.eq(outcomes.state).all():
        raise ValueError("NASS outcome county GEOID does not reconcile to its postal state")
    if not np.isfinite(outcomes.yield_bu_acre).all() or (outcomes.yield_bu_acre <= 0).any():
        raise ValueError("NASS outcome panel contains nonpositive/nonfinite yields")
    if strict_bool(outcomes.response_estimation_authorized, "NASS response gate").any():
        raise ValueError("NASS outcome panel unexpectedly authorizes a response fit")
    if strict_bool(outcomes.scc_authorized, "NASS SCC gate").any():
        raise ValueError("NASS outcome panel unexpectedly authorizes SCC use")
    if set(outcomes.outcome_source_id.astype(str)) != {str(sample["outcome_source_id"])}:
        raise ValueError("NASS outcome source differs from the national contract")
    if outcomes.duplicated(OUTCOME_KEYS).any():
        raise ValueError("NASS outcome panel duplicates outcome keys")
    route_scope = outcomes.loc[
        outcomes.outcome_crop.isin(crops)
        & outcomes.harvest_year.between(year_min, year_max)
    ]
    observed_practices = set(route_scope.irrigation_practice.astype(str))
    if observed_practices != practices:
        raise ValueError(
            "NASS outcome panel practice scope differs from the selected national contract: "
            f"{sorted(observed_practices)} != {sorted(practices)}"
        )

    _require_columns(
        geography,
        {
            "county_geoid", "state", "feature_construction_eligible",
            "response_estimation_authorized", "scc_authorized",
        },
        "geography gate",
    )
    geo = geography.copy()
    geo["county_geoid"] = geo.county_geoid.astype("string").str.strip()
    geo["state"] = geo.state.astype("string").str.strip().str.upper()
    if geo.county_geoid.str.fullmatch(r"\d{5}").ne(True).any() or geo.duplicated("county_geoid").any():
        raise ValueError("geography gate contains malformed or duplicate GEOIDs")
    geography_fips_state = geo.county_geoid.str[:2].map(STATE_FIPS_TO_ALPHA)
    if geography_fips_state.isna().any() or not geography_fips_state.eq(geo.state).all():
        raise ValueError("geography county GEOID does not reconcile to its postal state")
    geo["feature_construction_eligible"] = strict_bool(
        geo.feature_construction_eligible, "geography feature gate"
    )
    if strict_bool(geo.response_estimation_authorized, "geography response gate").any():
        raise ValueError("geography gate unexpectedly authorizes a response fit")
    if strict_bool(geo.scc_authorized, "geography SCC gate").any():
        raise ValueError("geography gate unexpectedly authorizes SCC use")
    eligible_geo = geo.loc[geo.feature_construction_eligible, ["county_geoid", "state"]]

    selected = outcomes.loc[
        outcomes.outcome_crop.isin(crops)
        & outcomes.irrigation_practice.isin(practices)
        & outcomes.harvest_year.between(year_min, year_max)
    ].merge(
        eligible_geo.rename(columns={"state": "geography_state"}),
        on="county_geoid", how="inner", validate="many_to_one",
    )
    if selected.empty or not selected.state.eq(selected.geography_state).all():
        raise ValueError("eligible NASS and geography states do not reconcile")
    selected = selected.drop(columns="geography_state")
    if set(selected.outcome_crop) != crops or set(selected.irrigation_practice) != practices:
        raise ValueError("eligible support does not populate each crop/practice")
    practice_sets = selected.groupby(PAIR_KEYS, observed=True).irrigation_practice.agg(set)
    if not practice_sets.map(lambda value: value == practices).all():
        if practices == {"irrigated", "non_irrigated"}:
            raise ValueError("eligible support does not preserve exact irrigation-practice pairs")
        raise ValueError("eligible support does not preserve one all_practices row per key")
    if practices == {"all_practices"} and selected.duplicated(PAIR_KEYS).any():
        raise ValueError("eligible support does not preserve one all_practices row per key")
    for column in ["state", "county_name", "outcome_source_id"]:
        if selected.groupby(PAIR_KEYS, observed=True)[column].nunique(dropna=False).ne(1).any():
            raise ValueError(f"eligible outcomes disagree on {column}")

    _require_columns(
        calendar,
        {
            "state", "calendar_crop", "harvest_year", "season_start", "season_end",
            "calendar_source_id", "calendar_vintage", "calendar_role", "boundary_rule",
            "stage_definition", "feature_construction_eligible",
            "response_estimation_authorized", "scc_authorized",
        },
        "crop calendar",
    )
    seasons = calendar.copy()
    seasons["state"] = seasons.state.astype("string").str.strip().str.upper()
    seasons["calendar_crop"] = seasons.calendar_crop.astype("string").str.strip()
    seasons["harvest_year"] = pd.to_numeric(seasons.harvest_year, errors="raise").astype("int64")
    seasons = seasons.loc[
        seasons.calendar_crop.isin(crops)
        & seasons.harvest_year.between(year_min, year_max)
        & seasons.calendar_role.astype("string").eq(str(calendar_contract["role"]))
    ].copy()
    seasons["season_start"] = pd.to_datetime(seasons.season_start, errors="raise").dt.normalize()
    seasons["season_end"] = pd.to_datetime(seasons.season_end, errors="raise").dt.normalize()
    if seasons.duplicated(["state", "calendar_crop", "harvest_year"]).any():
        raise ValueError("fixed crop calendar duplicates state/crop/year keys")
    if (seasons.season_end < seasons.season_start).any() or seasons.season_end.dt.year.ne(
        seasons.harvest_year
    ).any():
        raise ValueError("fixed crop calendar has invalid crop-year dates")
    duration = seasons.season_end.sub(seasons.season_start).dt.days.add(1)
    if not duration.between(30, 500).all():
        raise ValueError("fixed crop calendar duration lies outside 30..500 days")
    for flag in ["feature_construction_eligible", "response_estimation_authorized", "scc_authorized"]:
        seasons[flag] = strict_bool(seasons[flag], f"calendar {flag}")
    if not seasons.feature_construction_eligible.all():
        raise ValueError("selected fixed calendar contains ineligible rows")
    if seasons.response_estimation_authorized.any() or seasons.scc_authorized.any():
        raise ValueError("selected fixed calendar unexpectedly authorizes fitting or SCC")
    exact = {
        "calendar_source_id": str(calendar_contract["source_id"]),
        "calendar_vintage": str(calendar_contract["vintage"]),
        "boundary_rule": str(calendar_contract["boundary_rule"]),
        "stage_definition": str(calendar_contract["stage_definition"]),
    }
    for column, expected in exact.items():
        if set(seasons[column].astype(str)) != {expected}:
            raise ValueError(f"fixed calendar {column} differs from the national contract")

    required_calendar = selected[["state", "outcome_crop", "harvest_year"]].drop_duplicates()
    available_calendar = seasons.rename(columns={"calendar_crop": "outcome_crop"})
    joined_calendar = required_calendar.merge(
        available_calendar,
        on=["state", "outcome_crop", "harvest_year"], how="left", validate="many_to_one",
    )
    if joined_calendar.season_start.isna().any() or len(joined_calendar) != len(required_calendar):
        raise ValueError("eligible outcome support lacks an exact fixed calendar")
    seasons = joined_calendar.rename(columns={"outcome_crop": "calendar_crop"})

    pairs = selected.drop_duplicates(PAIR_KEYS)
    counts = {
        "eligible_counties": int(selected.county_geoid.nunique()),
        "eligible_crop_county_years": int(len(pairs)),
        "eligible_practice_rows": int(len(selected)),
        "corn_crop_county_years": int(pairs.outcome_crop.eq("corn_grain").sum()),
        "soy_crop_county_years": int(pairs.outcome_crop.eq("soybeans").sum()),
    }
    if enforce_registered_counts:
        expected_counts = {
            "eligible_counties": int(sample["expected_counties"]),
            "eligible_crop_county_years": int(sample["expected_crop_county_years"]),
            "eligible_practice_rows": int(sample["expected_practice_rows"]),
            "corn_crop_county_years": int(sample["expected_corn_crop_county_years"]),
            "soy_crop_county_years": int(sample["expected_soy_crop_county_years"]),
        }
        if counts != expected_counts:
            raise ValueError(f"eligible national sample counts changed: {counts} != {expected_counts}")
    counts.update(
        {
            "states": sorted(selected.state.unique().tolist()),
            "year_min": int(selected.harvest_year.min()),
            "year_max": int(selected.harvest_year.max()),
            "outcome_key_sha256": sha256_records(selected, OUTCOME_KEYS),
            "pair_key_sha256": sha256_records(pairs, PAIR_KEYS),
            "relationship_estimated": False,
            "scc_authorized": False,
        }
    )
    return (
        selected.sort_values(OUTCOME_KEYS).reset_index(drop=True),
        seasons.sort_values(["state", "calendar_crop", "harvest_year"]).reset_index(drop=True),
        counts,
    )


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def atomic_write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        frame.to_parquet(temporary, index=False)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
