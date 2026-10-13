#!/usr/bin/env python3
"""Audit whether released Blue-SCC market files support a GIVE transfer.

Only aggregate coverage, support, formula, and reconciliation facts are
emitted. Country coefficients and country SCC values are never copied.
"""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from pathlib import Path
from typing import Any

from audit_blue_scc_fisheries_benchmark import figure_summary, sha256_file
from audit_blue_scc_nutrition_give_transfer import (
    coverage_summary,
    git_output,
    read_csv,
    require_tokens,
    unique_iso3,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "blue_scc_market_component_transfer_config_v1"
CONFIG_ROLE = "published_market_component_reproduction_and_transfer_audit_only"
GIVE_FIELDS = ["country_id", "country_name", "give_region_id", "mapping_version"]


def compact_coverage(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        key: summary[key]
        for key in (
            "source_countries", "give_countries", "overlap_countries",
            "source_only_countries", "give_only_countries",
            "give_country_count_coverage_fraction", "complete_regions", "incomplete_regions",
        )
    } | {
        "complete_region_ids": sorted(
            region for region, item in summary["region_coverage"].items() if item["complete"]
        )
    }


def check_expected(actual: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        if key == "sum_usd_per_tco2":
            continue
        if actual.get(key) != value:
            raise ValueError(f"registered {label} result changed: {key}")


def audit(source_root: Path, config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("market component transfer config identity changed")
    source = config["source"]
    if git_output(source_root, "rev-parse", "HEAD") != source["repository_commit"]:
        raise ValueError("Blue-SCC repository commit changed")
    tree_paths = git_output(source_root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    root_licenses = [
        path for path in tree_paths
        if "/" not in path and path.lower().startswith(("license", "copying"))
    ]
    if root_licenses:
        raise ValueError("root license state changed; review before reuse")

    source_paths: dict[str, Path] = {}
    for name in (
        "market_coefficients", "country_scc", "figure4", "market_projection",
        "market_damage", "input_builder", "country_export", "scc_utility",
    ):
        path = source_root / source[f"{name}_path"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing regular source file: {name}")
        if sha256_file(path) != source[f"{name}_sha256"]:
            raise ValueError(f"source file hash changed: {name}")
        source_paths[name] = path

    require_tokens(source_paths["market_projection"], [
        "profits_usd * multiplier_value",
        "profit_ppDiff_from_rcp_26",
        "Full Adaptation",
    ])
    require_tokens(source_paths["market_damage"], [
        "profit_ppDiff_from_rcp_26/100",
        "0 + I(tdif_from_rcp26)",
    ])
    require_tokens(source_paths["input_builder"], [
        "fish_tcoeff.csv",
        "GDP_FractionChange_perC",
        "pd.merge(fisheries, fisheries_health_coef, on=['iso3'], how='outer').fillna(0)",
    ])
    require_tokens(source_paths["country_export"], [
        "country_level=True).query('t==2020')",
        "Data/SCC/out/country_level_scc.csv",
    ])
    require_tokens(source_paths["scc_utility"], [
        "agg_level = ['t', 'n']",
        "agg_level = ['t']",
        "world_popu = df.groupby(agg_level).popu.sum()",
        "--mod_emission_pulse=ocean_damage",
        "pulse is one million tons",
    ])

    give_config_path = ROOT / config["give"]["crosswalk_config"]
    give_config = tomllib.loads(give_config_path.read_text(encoding="utf-8"))
    give_path = ROOT / give_config["derived_crosswalk"]
    if sha256_file(give_path) != give_config["derived_sha256"]:
        raise ValueError("frozen GIVE crosswalk hash changed")
    give_fields, give_rows = read_csv(give_path)
    if give_fields != GIVE_FIELDS or len(give_rows) != config["give"]["expected_country_rows"]:
        raise ValueError("frozen GIVE crosswalk schema or size changed")
    expected_regions = set(map(str, give_config["expected_regions"]))
    if len(expected_regions) != config["give"]["expected_region_count"]:
        raise ValueError("frozen GIVE region count changed")

    coefficient_fields, coefficient_rows = read_csv(source_paths["market_coefficients"])
    required_coefficient_fields = {"country_iso3", "GDP_FractionChange_perC", "GDP_FractionChange_perC_se"}
    if not required_coefficient_fields.issubset(coefficient_fields):
        raise ValueError("market coefficient schema changed")
    coefficient_countries = unique_iso3(coefficient_rows, "country_iso3")
    for row in coefficient_rows:
        if not all(math.isfinite(float(row[name])) for name in required_coefficient_fields - {"country_iso3"}):
            raise ValueError("market coefficient contains a nonfinite value")
    coefficient_coverage = compact_coverage(
        coverage_summary(coefficient_countries, give_rows, expected_regions)
    )
    check_expected(coefficient_coverage, config["expected"]["market_coefficients"], "coefficient coverage")

    scc_fields, scc_rows = read_csv(source_paths["country_scc"])
    if scc_fields != ["iso3", "scc", "oc_capital", "valuation"]:
        raise ValueError("country SCC schema changed")
    market_rows = [
        row for row in scc_rows
        if row["oc_capital"] == "Fisheries" and row["valuation"] == "Market value"
    ]
    country_scc_countries = unique_iso3(market_rows, "iso3")
    market_values = [float(row["scc"]) for row in market_rows]
    if not all(math.isfinite(value) for value in market_values):
        raise ValueError("country market SCC contains a nonfinite value")
    country_scc_coverage = compact_coverage(
        coverage_summary(country_scc_countries, give_rows, expected_regions)
    )
    check_expected(country_scc_coverage, config["expected"]["country_scc"], "country SCC coverage")
    country_scc_sum = sum(market_values)
    tolerance = float(config["expected"]["figure4"]["comparison_tolerance"])
    if abs(country_scc_sum - float(config["expected"]["country_scc"]["sum_usd_per_tco2"])) > tolerance:
        raise ValueError("registered country market SCC sum changed")

    support_relationship = {
        "intersection_countries": len(coefficient_countries & country_scc_countries),
        "coefficient_only_countries": len(coefficient_countries - country_scc_countries),
        "country_scc_only_countries": len(country_scc_countries - coefficient_countries),
    }
    if support_relationship != dict(config["expected"]["support_relationship"]):
        raise ValueError("registered coefficient/country-SCC support relationship changed")

    figure = figure_summary(
        source_paths["figure4"],
        config["expected"]["figure4"]["sheet"],
        int(config["expected"]["figure4"]["year"]),
    )
    figure_market = figure["fisheries_market_scc_usd_per_tco2"]
    if abs(figure_market - float(config["expected"]["figure4"]["market_usd_per_tco2"])) > tolerance:
        raise ValueError("published Figure 4 market component changed")

    gdx_paths = sorted(path for path in tree_paths if path.lower().endswith(".gdx"))
    if gdx_paths != list(config["expected"]["repository_tree"]["gdx_paths"]):
        raise ValueError("published repository GDX inventory changed")
    gates = dict(config["claim_gates"])
    if any(gates.values()):
        raise ValueError("market transfer config improperly opens a claim gate")

    return {
        "schema": "blue_scc_market_component_transfer_audit_v1",
        "role": config["role"],
        "status": "blocked_country_file_is_not_additive_global_decomposition_and_transfer_inputs_are_incomplete",
        "source": {
            "repository_url": source["repository_url"],
            "repository_commit": source["repository_commit"],
            "repository_license_status": source["repository_license_status"],
            "verified_file_sha256": {
                name: source[f"{name}_sha256"] for name in source_paths
            },
        },
        "market_temperature_coefficients": {
            "coverage": coefficient_coverage,
            "welfare_semantics": "Free_et_al_profit_GDP_temperature_slope_after_regional_output_multiplier",
            "country_values_or_membership_embedded": False,
        },
        "published_2020_country_market_scc": {
            "coverage": country_scc_coverage,
            "sum_usd_per_tco2": country_scc_sum,
            "country_values_or_membership_embedded": False,
        },
        "support_relationship": support_relationship,
        "global_figure4_market_component": {
            "year": int(config["expected"]["figure4"]["year"]),
            "usd_per_tco2": figure_market,
            "country_file_sum_difference_usd_per_tco2": country_scc_sum - figure_market,
            "country_file_sum_relative_difference": country_scc_sum / figure_market - 1,
            "reproduced_directly_from_figure_source_workbook": True,
            "reproduced_by_summing_country_file": abs(country_scc_sum - figure_market) <= tolerance,
        },
        "formula_findings": {
            "global_and_country_files_use_different_aggregation_levels": True,
            "country_export_uses_country_level_discounting_and_selects_2020": True,
            "country_file_is_not_an_additive_decomposition_of_global_market_scc": True,
            "market_coefficient_includes_regional_output_multiplier": True,
            "consumer_plus_producer_surplus_measure": False,
        },
        "annual_path": {
            "released_gdx_paths": gdx_paths,
            "baseline_and_pulse_result_gdx_released": False,
            "rice50x_model_present_in_repository": any(path.startswith("RICE50x/") for path in tree_paths),
            "published_code_uses_one_million_ton_pulse": True,
            "annual_regional_market_damages_reproducible": False,
        },
        "interpretation": {
            "figure4_value_is_published_benchmark_only": True,
            "partial_complete_regions_do_not_authorize_transfer": True,
            "missing_countries_may_not_be_filled_or_zeroed": True,
            "external_source_files_copied": False,
            "market_only_path_avoids_nutrition_mortality_overlap": True,
            "market_multiplier_and_other_market_damage_overlap_remains_unresolved": True,
        },
        "required_source_artifacts": [
            "explicit_code_and_data_reuse_license",
            "same_run_additive_country_decomposition_summing_to_figure4_market_component",
            "annual_country_baseline_and_pulse_fisheries_market_damage_flows",
            "rice50x_model_commit_dependency_lock_and_baseline_pulse_result_gdx",
            "exact_143_to_155_country_mapping_and_missingness_semantics",
            "exact_country_multiplier_assignment_and_upstream_profit_panel",
            "multiplier_free_direct_surplus_outputs_or_valid_consumer_plus_producer_surplus",
            "give_market_overlap_accounting_boundary",
        ],
        "claim_gates": gates,
        "config": {
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256_file(config_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config/blue_scc_market_component_transfer_v1.toml",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "data/provenance/blue_scc_market_component_transfer_audit_20261013.json",
    )
    args = parser.parse_args()
    result = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(
        "Blue-SCC market transfer blocked: Figure 4 market component is reproducible "
        "only as a published global workbook value, not an additive country transfer"
    )


if __name__ == "__main__":
    main()
