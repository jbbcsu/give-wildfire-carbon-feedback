#!/usr/bin/env python3
"""Audit the shortest published Blue-SCC nutrition/SCC path to GIVE.

The audit reads a separate pinned checkout and emits aggregate coverage and
reconciliation facts only. It never copies country coefficients, fills a
missing country, computes annual damages, or authorizes an SCC transfer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "blue_scc_nutrition_give_transfer_config_v1"
CONFIG_ROLE = "published_nutrition_and_country_scc_asset_readiness_audit_only"
GIVE_FIELDS = ["country_id", "country_name", "give_region_id", "mapping_version"]
NUTRITION_NUMERIC_FIELDS = [
    "beta_nutrient_percChange_perDegreeC",
    "beta_nutrient_percChange_perDegreeC_se",
    "TAME_nutrients_MortalityEffect",
    "TAME_nutrients_MortalityEffect_se",
    "Nutritional_D",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def unique_iso3(rows: list[dict[str, str]], key: str) -> set[str]:
    countries: set[str] = set()
    for row in rows:
        country = row[key].strip()
        if re.fullmatch(r"[A-Z]{3}", country) is None or country in countries:
            raise ValueError(f"invalid or duplicate country key in {key}")
        countries.add(country)
    return countries


def coverage_summary(
    source_countries: set[str],
    give_rows: list[dict[str, str]],
    expected_regions: set[str],
) -> dict[str, Any]:
    give_countries = unique_iso3(give_rows, "country_id")
    totals: Counter[str] = Counter()
    covered: Counter[str] = Counter()
    for row in give_rows:
        region = row["give_region_id"].strip()
        if region not in expected_regions:
            raise ValueError("GIVE row contains an undeclared region")
        totals[region] += 1
        if row["country_id"].strip() in source_countries:
            covered[region] += 1
    if set(totals) != expected_regions:
        raise ValueError("GIVE crosswalk does not cover every declared region")
    by_region = {
        region: {
            "give_countries": totals[region],
            "source_covered_countries": covered[region],
            "uncovered_countries": totals[region] - covered[region],
            "complete": totals[region] == covered[region],
        }
        for region in sorted(expected_regions)
    }
    overlap = len(source_countries & give_countries)
    return {
        "source_countries": len(source_countries),
        "give_countries": len(give_countries),
        "overlap_countries": overlap,
        "source_only_countries": len(source_countries - give_countries),
        "give_only_countries": len(give_countries - source_countries),
        "give_country_count_coverage_fraction": overlap / len(give_countries),
        "complete_regions": sum(item["complete"] for item in by_region.values()),
        "incomplete_regions": sum(not item["complete"] for item in by_region.values()),
        "region_coverage": by_region,
    }


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ValueError(f"{path.name} is missing registered method tokens: {missing}")


def check_registered(actual: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        if key in {"market_sum_usd_per_tco2", "nonmarket_sum_usd_per_tco2", "nutritional_d_na_rows", "rows"}:
            continue
        if actual.get(key) != value:
            raise ValueError(f"registered {label} result changed: {key}")


def audit(source_root: Path, config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("nutrition transfer config identity changed")
    source = config["source"]
    if git_output(source_root, "rev-parse", "HEAD") != source["repository_commit"]:
        raise ValueError("Blue-SCC repository commit changed")
    tree_paths = git_output(source_root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    license_files = [
        path for path in tree_paths
        if "/" not in path and path.lower().startswith(("license", "copying"))
    ]
    if license_files:
        raise ValueError("root license state changed; review before reuse")

    source_paths: dict[str, Path] = {}
    for name in ("nutrition", "country_scc", "input_builder", "country_export", "scc_utility", "scc_steps"):
        path = source_root / source[f"{name}_path"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing regular source file: {name}")
        if sha256(path) != source[f"{name}_sha256"]:
            raise ValueError(f"source file hash changed: {name}")
        source_paths[name] = path

    require_tokens(source_paths["input_builder"], [
        "pd.merge(fisheries, fisheries_health_coef, on=['iso3'], how='outer').fillna(0)",
        "fisheries_health_coef[col] /= 100",
    ])
    require_tokens(source_paths["country_export"], [
        "country_level=True).query('t==2020')",
        "Data/SCC/out/country_level_scc.csv",
    ])
    require_tokens(source_paths["scc_utility"], [
        "--mod_emission_pulse=ocean_damage",
        "the pulse is one million tons",
        "if country_level:",
    ])
    require_tokens(source_paths["scc_steps"], ["Navigate to your RICE50x folder", "cd work/RICE50x"])

    give_config_path = ROOT / config["give"]["crosswalk_config"]
    give_config = tomllib.loads(give_config_path.read_text(encoding="utf-8"))
    give_path = ROOT / give_config["derived_crosswalk"]
    if sha256(give_path) != give_config["derived_sha256"]:
        raise ValueError("frozen GIVE crosswalk hash changed")
    give_fields, give_rows = read_csv(give_path)
    if give_fields != GIVE_FIELDS or len(give_rows) != config["give"]["expected_country_rows"]:
        raise ValueError("frozen GIVE crosswalk schema or size changed")
    expected_regions = set(map(str, give_config["expected_regions"]))

    nutrition_fields, nutrition_rows = read_csv(source_paths["nutrition"])
    required_nutrition = {"countrycode", *NUTRITION_NUMERIC_FIELDS}
    if not required_nutrition.issubset(nutrition_fields):
        raise ValueError("nutrition coefficient schema changed")
    nutrition_countries = unique_iso3(nutrition_rows, "countrycode")
    complete_rows = [
        row for row in nutrition_rows
        if all(finite(row[name]) for name in NUTRITION_NUMERIC_FIELDS)
    ]
    complete_countries = {row["countrycode"].strip() for row in complete_rows}
    nutritional_d_na_rows = sum(row["Nutritional_D"].strip().upper() == "NA" for row in nutrition_rows)
    nutrition_all_coverage = coverage_summary(nutrition_countries, give_rows, expected_regions)
    nutrition_complete_coverage = coverage_summary(complete_countries, give_rows, expected_regions)
    check_registered(nutrition_all_coverage, config["expected"]["nutrition_all_rows"], "nutrition coverage")
    check_registered(
        nutrition_complete_coverage,
        config["expected"]["nutrition_complete_numeric"],
        "complete-numeric nutrition coverage",
    )
    if nutritional_d_na_rows != config["expected"]["nutrition_complete_numeric"]["nutritional_d_na_rows"]:
        raise ValueError("registered Nutritional_D missingness changed")

    scc_fields, scc_rows = read_csv(source_paths["country_scc"])
    if scc_fields != ["iso3", "scc", "oc_capital", "valuation"]:
        raise ValueError("country SCC schema changed")
    fisheries_rows = [row for row in scc_rows if row["oc_capital"] == "Fisheries"]
    if len(fisheries_rows) != config["expected"]["country_scc"]["rows"]:
        raise ValueError("published fisheries country SCC row count changed")
    valuations = {"Market value", "Non-market use value"}
    if {row["valuation"] for row in fisheries_rows} != valuations:
        raise ValueError("published fisheries country SCC valuation set changed")
    by_valuation: dict[str, dict[str, Any]] = {}
    country_sets: list[set[str]] = []
    for valuation in sorted(valuations):
        rows = [row for row in fisheries_rows if row["valuation"] == valuation]
        countries = unique_iso3(rows, "iso3")
        values = [float(row["scc"]) for row in rows]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("published fisheries country SCC contains a nonfinite value")
        by_valuation[valuation] = {
            "rows": len(rows),
            "countries": len(countries),
            "sum_usd_per_tco2": sum(values),
        }
        country_sets.append(countries)
    if country_sets[0] != country_sets[1]:
        raise ValueError("published fisheries country SCC valuation supports differ")
    country_scc_coverage = coverage_summary(country_sets[0], give_rows, expected_regions)
    check_registered(country_scc_coverage, config["expected"]["country_scc"], "country SCC coverage")

    tolerance = float(config["expected"]["figure4"]["comparison_tolerance"])
    sum_key = {
        "Market value": "market_sum_usd_per_tco2",
        "Non-market use value": "nonmarket_sum_usd_per_tco2",
    }
    figure_key = {
        "Market value": "market_usd_per_tco2",
        "Non-market use value": "nonmarket_usd_per_tco2",
    }
    reconciliation: dict[str, Any] = {}
    for valuation in sorted(valuations):
        country_sum = by_valuation[valuation]["sum_usd_per_tco2"]
        expected_sum = float(config["expected"]["country_scc"][sum_key[valuation]])
        if abs(country_sum - expected_sum) > tolerance:
            raise ValueError("registered country SCC sum changed")
        figure_value = float(config["expected"]["figure4"][figure_key[valuation]])
        reconciliation[valuation] = {
            "country_sum_usd_per_tco2": country_sum,
            "figure4_usd_per_tco2": figure_value,
            "difference_usd_per_tco2": country_sum - figure_value,
            "relative_difference": country_sum / figure_value - 1,
            "matches_within_tolerance": abs(country_sum - figure_value) <= tolerance,
        }

    gdx_paths = sorted(path for path in tree_paths if path.lower().endswith(".gdx"))
    if gdx_paths != list(config["expected"]["repository_tree"]["gdx_paths"]):
        raise ValueError("published repository GDX inventory changed")

    gates = dict(config["claim_gates"])
    if any(gates.values()):
        raise ValueError("nutrition transfer config improperly opens a claim gate")

    return {
        "schema": "blue_scc_nutrition_give_transfer_audit_v1",
        "role": config["role"],
        "status": "blocked_incomplete_nutrition_coverage_nonreconciled_country_scc_and_missing_annual_run_inputs",
        "source": {
            "repository_url": source["repository_url"],
            "repository_commit": source["repository_commit"],
            "repository_license_status": source["repository_license_status"],
            "verified_file_sha256": {
                name: source[f"{name}_sha256"] for name in source_paths
            },
        },
        "give_crosswalk": {
            "mapping_version": give_config["mapping_version"],
            "path": str(give_path.relative_to(ROOT)),
            "sha256": give_config["derived_sha256"],
        },
        "nutrition_input": {
            "all_rows_coverage": nutrition_all_coverage,
            "complete_numeric_coverage": nutrition_complete_coverage,
            "nutritional_d_na_rows": nutritional_d_na_rows,
            "missing_values_are_zero_filled_by_published_input_builder": True,
        },
        "published_2020_country_scc": {
            "coverage": country_scc_coverage,
            "valuation_summaries": by_valuation,
            "figure4_reconciliation": reconciliation,
            "country_values_or_membership_embedded": False,
        },
        "annual_path": {
            "released_gdx_paths": gdx_paths,
            "baseline_and_pulse_result_gdx_released": False,
            "rice50x_model_present_in_repository": any(path.startswith("RICE50x/") for path in tree_paths),
            "published_code_uses_one_million_ton_pulse": True,
            "published_country_export_selects_year_2020": True,
        },
        "interpretation": {
            "country_scc_support_does_not_cure_nutrition_input_missingness": True,
            "missing_countries_or_coefficients_may_not_be_treated_as_zero": True,
            "country_scc_sum_reconciles_to_figure4": all(
                item["matches_within_tolerance"] for item in reconciliation.values()
            ),
            "give_mortality_overlap_remains_unresolved": True,
            "external_source_files_copied": False,
        },
        "claim_gates": gates,
        "config": {
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256(config_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/blue_scc_nutrition_give_transfer_v1.toml",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/provenance/blue_scc_nutrition_give_transfer_audit_20261013.json",
    )
    args = parser.parse_args()
    result = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(
        "Blue-SCC nutrition/GIVE transfer remains blocked: "
        f"{result['nutrition_input']['complete_numeric_coverage']['overlap_countries']}/"
        f"{result['nutrition_input']['complete_numeric_coverage']['give_countries']} "
        "GIVE countries have complete numeric nutrition inputs"
    )


if __name__ == "__main__":
    main()
