#!/usr/bin/env python3
"""Credential-safe count-only NASS screen for additional direct-practice crops."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / "us_county_validation/scripts/download_nass_quickstats_api.py"
PROTOCOL = ROOT / "US_ADDITIONAL_CROP_DIRECT_PRACTICE_COUNT_PROTOCOL_20260925.md"
YEARS = tuple(range(1981, 2020))
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")
CROPS = {
    "sorghum_grain": {
        "commodity_desc": "SORGHUM", "class_desc": "ALL CLASSES",
        "util_practice_desc": "GRAIN", "unit_desc": "BU / ACRE",
    },
    "cotton_upland": {
        "commodity_desc": "COTTON", "class_desc": "UPLAND",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "unit_desc": "LB / ACRE",
    },
    "rice": {
        "commodity_desc": "RICE", "class_desc": "ALL CLASSES",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "unit_desc": "CWT / ACRE",
    },
    "barley": {
        "commodity_desc": "BARLEY", "class_desc": "ALL CLASSES",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "unit_desc": "BU / ACRE",
    },
    "oats": {
        "commodity_desc": "OATS", "class_desc": "ALL CLASSES",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "unit_desc": "BU / ACRE",
    },
}
STAGE_ONE_MINIMUM = 500
PAIR_UPPER_BOUND_MINIMUM = 500
MINIMUM_POSITIVE_YEARS = 10
MINIMUM_YEARS_AT_25 = 5
MINIMUM_USDM_ERA_YEARS_AT_25 = 5
REQUEST_THROTTLE_SECONDS = 1.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_downloader():
    spec = importlib.util.spec_from_file_location("nass_additional_crop_counts", DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load credential-safe NASS downloader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parameters(crop: str, practice: str, year: int | None = None) -> dict[str, str]:
    if crop not in CROPS or practice not in PRACTICES:
        raise ValueError("unsupported crop/practice count query")
    if year is not None and year not in YEARS:
        raise ValueError("year is outside the frozen screen")
    result = {
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        **CROPS[crop],
        "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "prodn_practice_desc": practice,
        "format": "JSON",
    }
    if year is not None:
        result["year"] = str(year)
    return result


def bounded_count(base: Any, query: dict[str, str], key: str, label: str) -> int:
    delays = (0, 5, 15, 30)
    last_error: RuntimeError | None = None
    for delay in delays:
        if delay:
            time.sleep(delay)
        try:
            count = base.count_records(query, key)
            time.sleep(REQUEST_THROTTLE_SECONDS)
            return count
        except RuntimeError as error:
            last_error = error
    raise RuntimeError(
        f"NASS count request failed after bounded retries for {label}"
    ) from last_error


def cache_identifier(crop: str, practice: str, year: int | None) -> str:
    suffix = "all_years" if year is None else str(year)
    return f"{crop}|{practice}|{suffix}"


def read_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    if not path.is_file() or not path.resolve().is_relative_to(ROOT / "data/interim"):
        raise ValueError("count checkpoint must be an ignored interim file")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_sha256") != sha256(PROTOCOL):
        raise ValueError("count checkpoint protocol identity differs")
    records = payload.get("records")
    if not isinstance(records, dict):
        raise ValueError("count checkpoint records are invalid")
    return records


def write_cache(path: Path, records: dict[str, dict[str, Any]]) -> None:
    path = path.resolve()
    if not path.is_relative_to(ROOT / "data/interim") or path.suffix != ".json":
        raise ValueError("count checkpoint must be an ignored interim JSON file")
    payload = {
        "schema": "nass_additional_crop_count_checkpoint_v1",
        "protocol_sha256": sha256(PROTOCOL),
        "records": records,
        "credential_stored": False,
        "yield_values_stored": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def summarize_crop(
    crop: str, stage_one: dict[str, int], annual_rows: list[dict[str, Any]], api_cap: int,
) -> dict[str, Any]:
    stage_one_pass = all(
        STAGE_ONE_MINIMUM <= int(stage_one[practice]) < api_cap
        for practice in PRACTICES
    )
    if not stage_one_pass:
        return {
            "crop": crop,
            "stage_one_all_year_counts": stage_one,
            "stage_one_passed": False,
            "annual_counts_queried": False,
            "count_feasible": False,
            "blocking_reasons": [
                "one or both all-years practice counts are below 500 or at/above the API cap"
            ],
        }
    expected = {(practice, year) for practice in PRACTICES for year in YEARS}
    observed = {(str(row["practice"]), int(row["year"])) for row in annual_rows}
    if observed != expected or len(annual_rows) != len(expected):
        raise ValueError(f"{crop}: annual count matrix is incomplete or duplicated")
    by_key = {
        (str(row["practice"]), int(row["year"])): int(row["count"])
        for row in annual_rows
    }
    upper = {
        str(year): min(by_key[(practice, year)] for practice in PRACTICES)
        for year in YEARS
    }
    positive_years = [year for year in YEARS if upper[str(year)] > 0]
    years_at_25 = [year for year in YEARS if upper[str(year)] >= 25]
    usdm_years_at_25 = [year for year in range(2001, 2020) if upper[str(year)] >= 25]
    total_upper = sum(upper.values())
    conditions = {
        "paired_count_upper_bound_at_least_500": total_upper >= PAIR_UPPER_BOUND_MINIMUM,
        "at_least_10_positive_years": len(positive_years) >= MINIMUM_POSITIVE_YEARS,
        "at_least_5_years_with_upper_bound_25": len(years_at_25) >= MINIMUM_YEARS_AT_25,
        "at_least_5_usdm_era_years_with_upper_bound_25": (
            len(usdm_years_at_25) >= MINIMUM_USDM_ERA_YEARS_AT_25
        ),
    }
    return {
        "crop": crop,
        "stage_one_all_year_counts": stage_one,
        "stage_one_passed": True,
        "annual_counts_queried": True,
        "annual_paired_count_upper_bounds": upper,
        "paired_count_upper_bound_1981_2019": total_upper,
        "positive_year_count": len(positive_years),
        "positive_year_range": (
            [min(positive_years), max(positive_years)] if positive_years else None
        ),
        "years_with_upper_bound_at_least_25": years_at_25,
        "usdm_era_years_with_upper_bound_at_least_25": usdm_years_at_25,
        "gate_conditions": conditions,
        "count_feasible": all(conditions.values()),
        "blocking_reasons": [name for name, passed in conditions.items() if not passed],
    }


def contains_credential_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(name).lower() in {"key", "api_key", "nass_api_key", "quickstats_api_key"}
            or contains_credential_field(item)
            for name, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_credential_field(item) for item in value)
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--secrets-file", type=Path, default=ROOT / ".secrets/nass.env")
    parser.add_argument(
        "--checkpoint", type=Path,
        default=ROOT / "data/interim/us_county/nass_additional_crop_direct_practice_count_checkpoint_20260925.json",
    )
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim") or out.suffix != ".json":
        raise ValueError("fresh ignored interim JSON output required")
    base = load_downloader()
    key = base.read_key(args.secrets_file)
    cached = read_cache(args.checkpoint)

    def get_count(crop: str, practice: str, year: int | None) -> tuple[int, dict[str, str]]:
        query = parameters(crop, practice, year)
        identifier = cache_identifier(crop, practice, year)
        if identifier in cached:
            record = cached[identifier]
            if record.get("query_parameters_excluding_key") != query:
                raise ValueError(f"cached query identity differs for {identifier}")
            count = record.get("count")
            if type(count) is not int or count < 0:
                raise ValueError(f"cached count is invalid for {identifier}")
            return count, query
        count = bounded_count(base, query, key, identifier)
        cached[identifier] = {
            "count": count, "query_parameters_excluding_key": query,
        }
        write_cache(args.checkpoint, cached)
        return count, query

    queries: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for crop in CROPS:
        stage_one: dict[str, int] = {}
        for practice in PRACTICES:
            count, query = get_count(crop, practice, None)
            stage_one[practice] = count
            queries.append({
                "stage": "all_years", "crop": crop, "practice": practice,
                "year": None, "count": count,
                "query_parameters_excluding_key": query,
            })
        annual_rows: list[dict[str, Any]] = []
        if all(STAGE_ONE_MINIMUM <= stage_one[p] < base.MAX_API_RECORDS for p in PRACTICES):
            for year in YEARS:
                for practice in PRACTICES:
                    count, query = get_count(crop, practice, year)
                    row = {
                        "stage": "annual_1981_2019", "crop": crop,
                        "practice": practice, "year": year, "count": count,
                        "query_parameters_excluding_key": query,
                    }
                    annual_rows.append(row)
                    queries.append(row)
        summaries.append(summarize_crop(
            crop, stage_one, annual_rows, base.MAX_API_RECORDS,
        ))

    result = {
        "schema": "nass_additional_crop_direct_practice_count_support_v1",
        "status": "completed_count_only_no_values_downloaded",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "official_count_endpoint": base.COUNT_ENDPOINT,
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256(PROTOCOL),
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "downloader": {
            "path": str(DOWNLOADER.relative_to(ROOT)), "sha256": sha256(DOWNLOADER),
        },
        "year_window": [min(YEARS), max(YEARS)],
        "thresholds": {
            "stage_one_minimum_each_practice": STAGE_ONE_MINIMUM,
            "api_record_cap_exclusive": base.MAX_API_RECORDS,
            "paired_count_upper_bound_minimum": PAIR_UPPER_BOUND_MINIMUM,
            "minimum_positive_years": MINIMUM_POSITIVE_YEARS,
            "minimum_years_with_upper_bound_25": MINIMUM_YEARS_AT_25,
            "minimum_usdm_era_years_with_upper_bound_25": MINIMUM_USDM_ERA_YEARS_AT_25,
        },
        "queries": queries,
        "query_count": len(queries),
        "crop_summaries": summaries,
        "count_feasible_crops": [row["crop"] for row in summaries if row["count_feasible"]],
        "count_blocked_crops": [row["crop"] for row in summaries if not row["count_feasible"]],
        "api_data_endpoint_called": False,
        "yield_values_downloaded": False,
        "paired_counties_observed": False,
        "weather_joined": False,
        "response_estimated": False,
        "causal_claim_authorized": False,
        "irrigation_treatment_claim_authorized": False,
        "national_representativeness_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    if contains_credential_field(result):
        raise ValueError("saved output unexpectedly contains a credential field")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "query_count": result["query_count"],
        "count_feasible_crops": result["count_feasible_crops"],
        "count_blocked_crops": result["count_blocked_crops"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
