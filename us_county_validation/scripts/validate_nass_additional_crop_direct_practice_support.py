#!/usr/bin/env python3
"""Structural validation of additional-crop and rice count-only NASS screens."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
YEARS = tuple(range(1981, 2020))
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")
CROPS = {
    "sorghum_grain": ("SORGHUM", "ALL CLASSES", "GRAIN", "BU / ACRE"),
    "cotton_upland": (
        "COTTON", "UPLAND", "ALL UTILIZATION PRACTICES", "LB / ACRE",
    ),
    "rice": ("RICE", "ALL CLASSES", "ALL UTILIZATION PRACTICES", "CWT / ACRE"),
    "barley": ("BARLEY", "ALL CLASSES", "ALL UTILIZATION PRACTICES", "BU / ACRE"),
    "oats": ("OATS", "ALL CLASSES", "ALL UTILIZATION PRACTICES", "BU / ACRE"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    resolved = (ROOT / path).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved


def contains_credential(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(name).lower() in {"key", "api_key", "nass_api_key", "quickstats_api_key"}
            or contains_credential(item)
            for name, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_credential(item) for item in value)
    return False


def expected_parameters(crop: str, practice: str, year: int | None) -> dict[str, str]:
    commodity, crop_class, utilization, unit = CROPS[crop]
    query = {
        "source_desc": "SURVEY", "sector_desc": "CROPS",
        "commodity_desc": commodity, "class_desc": crop_class,
        "util_practice_desc": utilization, "unit_desc": unit,
        "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL", "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL", "prodn_practice_desc": practice,
        "format": "JSON",
    }
    if year is not None:
        query["year"] = str(year)
    return query


def reconstruct_summary(crop: str, records: dict[tuple[str, int | None], int]) -> dict[str, Any]:
    all_year = {practice: records[(practice, None)] for practice in PRACTICES}
    stage_one = all(500 <= all_year[practice] < 50_000 for practice in PRACTICES)
    if not stage_one:
        return {
            "crop": crop, "stage_one_all_year_counts": all_year,
            "stage_one_passed": False, "annual_counts_queried": False,
            "count_feasible": False,
            "blocking_reasons": [
                "one or both all-years practice counts are below 500 or at/above the API cap"
            ],
        }
    upper = {
        str(year): min(records[(practice, year)] for practice in PRACTICES)
        for year in YEARS
    }
    positive = [year for year in YEARS if upper[str(year)] > 0]
    at_25 = [year for year in YEARS if upper[str(year)] >= 25]
    usdm_at_25 = [year for year in range(2001, 2020) if upper[str(year)] >= 25]
    conditions = {
        "paired_count_upper_bound_at_least_500": sum(upper.values()) >= 500,
        "at_least_10_positive_years": len(positive) >= 10,
        "at_least_5_years_with_upper_bound_25": len(at_25) >= 5,
        "at_least_5_usdm_era_years_with_upper_bound_25": len(usdm_at_25) >= 5,
    }
    return {
        "crop": crop, "stage_one_all_year_counts": all_year,
        "stage_one_passed": True, "annual_counts_queried": True,
        "annual_paired_count_upper_bounds": upper,
        "paired_count_upper_bound_1981_2019": sum(upper.values()),
        "positive_year_count": len(positive),
        "positive_year_range": [min(positive), max(positive)] if positive else None,
        "years_with_upper_bound_at_least_25": at_25,
        "usdm_era_years_with_upper_bound_at_least_25": usdm_at_25,
        "gate_conditions": conditions, "count_feasible": all(conditions.values()),
        "blocking_reasons": [name for name, passed in conditions.items() if not passed],
    }


def check_resource(path: Path) -> int:
    resource = json.loads(path.read_text(encoding="utf-8"))
    if (
        resource.get("status") != "command_completed"
        or int(resource.get("returncode", -1)) != 0
        or int(resource.get("peak_rss_bytes", 2**63)) > 512 * 1024 * 1024
    ):
        raise ValueError(f"resource receipt failed: {path}")
    return int(resource["peak_rss_bytes"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--resource", required=True)
    parser.add_argument("--rice-diagnostic", required=True)
    parser.add_argument("--rice-resource", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    source_path = project_path(args.input)
    resource_path = project_path(args.resource)
    rice_path = project_path(args.rice_diagnostic)
    rice_resource_path = project_path(args.rice_resource)
    out_path = project_path(args.out)
    if out_path.exists() or not out_path.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored interim validation output required")

    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("schema") != "nass_additional_crop_direct_practice_count_support_v1":
        raise ValueError("wrong additional-crop count schema")
    if source.get("status") != "completed_count_only_no_values_downloaded":
        raise ValueError("additional-crop count run did not complete")
    for record in (source["protocol"], source["implementation"], source["downloader"]):
        if sha256(project_path(record["path"])) != record["sha256"]:
            raise ValueError(f"source identity changed: {record['path']}")
    if contains_credential(source):
        raise ValueError("additional-crop result contains a credential field")
    for flag in (
        "api_data_endpoint_called", "yield_values_downloaded",
        "paired_counties_observed", "weather_joined", "response_estimated",
        "causal_claim_authorized", "irrigation_treatment_claim_authorized",
        "national_representativeness_claim_authorized", "damage_claim_authorized",
        "scc_claim_authorized",
    ):
        if source.get(flag) is not False:
            raise ValueError(f"unexpected open claim/data flag: {flag}")

    rows_by_crop: dict[str, dict[tuple[str, int | None], int]] = {
        crop: {} for crop in CROPS
    }
    for row in source["queries"]:
        crop = str(row["crop"])
        practice = str(row["practice"])
        year = None if row["year"] is None else int(row["year"])
        key = (practice, year)
        if crop not in CROPS or practice not in PRACTICES or key in rows_by_crop[crop]:
            raise ValueError("additional-crop query key is invalid or duplicated")
        if row["query_parameters_excluding_key"] != expected_parameters(crop, practice, year):
            raise ValueError("additional-crop key-free query parameters differ")
        count = row["count"]
        if type(count) is not int or count < 0:
            raise ValueError("additional-crop count is invalid")
        rows_by_crop[crop][key] = count
    rebuilt = []
    for crop, records in rows_by_crop.items():
        if not all((practice, None) in records for practice in PRACTICES):
            raise ValueError(f"{crop}: all-years counts are incomplete")
        stage_one = all(500 <= records[(practice, None)] < 50_000 for practice in PRACTICES)
        expected_keys = {(practice, None) for practice in PRACTICES}
        if stage_one:
            expected_keys |= {(practice, year) for practice in PRACTICES for year in YEARS}
        if set(records) != expected_keys:
            raise ValueError(f"{crop}: staged count matrix differs")
        rebuilt.append(reconstruct_summary(crop, records))
    if rebuilt != source["crop_summaries"] or len(source["queries"]) != 322:
        raise ValueError("additional-crop summaries do not reconstruct")
    feasible = [row["crop"] for row in rebuilt if row["count_feasible"]]
    blocked = [row["crop"] for row in rebuilt if not row["count_feasible"]]
    if feasible != source["count_feasible_crops"] or blocked != source["count_blocked_crops"]:
        raise ValueError("feasible/blocked crop lists do not reconstruct")

    rice = json.loads(rice_path.read_text(encoding="utf-8"))
    if rice.get("schema") != "nass_rice_direct_practice_zero_count_diagnostic_v1":
        raise ValueError("wrong rice diagnostic schema")
    for record in (rice["protocol"], rice["implementation"]):
        if sha256(project_path(record["path"])) != record["sha256"]:
            raise ValueError(f"rice source identity changed: {record['path']}")
    if contains_credential(rice) or rice.get("api_data_endpoint_called") is not False:
        raise ValueError("rice diagnostic credential/data boundary failed")
    rice_counts = {}
    common = {
        "source_desc": "SURVEY", "sector_desc": "CROPS",
        "commodity_desc": "RICE", "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY", "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR", "format": "JSON",
    }
    for row in rice["queries"]:
        practice = str(row["practice"])
        expected = dict(common)
        if practice != "UNFILTERED":
            expected["prodn_practice_desc"] = practice
        if practice in rice_counts or row["query_parameters_excluding_key"] != expected:
            raise ValueError("rice diagnostic query differs or duplicates")
        rice_counts[practice] = int(row["count"])
    if set(rice_counts) != {"UNFILTERED", *PRACTICES}:
        raise ValueError("rice diagnostic query matrix is incomplete")
    expected_conclusion = (
        "county_rice_yield_exists_but_no_direct_practice_labels"
        if rice_counts["UNFILTERED"] > 0
        and rice_counts["IRRIGATED"] == rice_counts["NON-IRRIGATED"] == 0
        else "primary_exact_series_descriptor_requires_separate_audit"
        if rice_counts["IRRIGATED"] > 0 or rice_counts["NON-IRRIGATED"] > 0
        else "broad_count_inconclusive_or_county_survey_rice_yield_absent"
    )
    if rice.get("conclusion") != expected_conclusion:
        raise ValueError("rice diagnostic conclusion does not reconstruct")

    production_rss = check_resource(resource_path)
    rice_rss = check_resource(rice_resource_path)
    output = {
        "schema": "nass_additional_crop_direct_practice_count_validation_v1",
        "status": "passed",
        "source": {"path": args.input, "sha256": sha256(source_path)},
        "rice_diagnostic": {"path": args.rice_diagnostic, "sha256": sha256(rice_path)},
        "validated_query_count": len(source["queries"]) + len(rice["queries"]),
        "count_feasible_crops": feasible,
        "count_blocked_crops": blocked,
        "rice_broad_counts": rice_counts,
        "rice_conclusion": expected_conclusion,
        "production_peak_rss_bytes": production_rss,
        "rice_diagnostic_peak_rss_bytes": rice_rss,
        "credential_fields_found": False,
        "yield_values_downloaded": False,
        "response_estimated": False,
        "damage_or_scc_estimated": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "passed", "validated_query_count": output["validated_query_count"],
        "count_feasible_crops": feasible, "count_blocked_crops": blocked,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
