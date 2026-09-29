#!/usr/bin/env python3
"""Audit whether Blue-SCC market multipliers can be removed reproducibly.

This is a design and provenance audit. It never derives country coefficients,
fills coverage gaps, treats profit as total welfare, or calculates an SCC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "blue_scc_market_welfare_decomposition_config_v1"
CONFIG_ROLE = "source_pinned_multiplier_separability_and_welfare_semantics_audit_only"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_tokens(text: str, tokens: list[str], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ValueError(f"{label} method tokens changed or are absent: {missing}")


def inspect_design(
    projection: str,
    damage: str,
    crosscutting: str,
    main: str,
    tracked_paths: set[str],
    upstream_paths: list[str],
    lock_paths: list[str],
) -> dict[str, object]:
    require_tokens(
        projection,
        [
            "summarise(profits_usd = mean(profits_usd, na.rm = TRUE))",
            "profit_diff_from_rcp_26 = profits_usd - profits_usd_baseline",
            'WDI(country = "all", indicator = "NY.GDP.MKTP.PP.KD", start = 2012, end = 2021)',
            "multiplier_value = c(1+2.59+0.62",
            "1+2.67+0.62",
            "1+3.12+0.76",
            "1+2.05+0.56",
            "1+3.52+1.22",
            "1+3.27 +0.73",
            "multiplier_value=ifelse(is.na(multiplier_value),4.55,multiplier_value)",
            "profits_usd * multiplier_value/ (1.14*GDP_ppp)",
            "profits_usd_baseline * multiplier_value / (1.14*GDP_ppp)",
            "profit_ppDiff_from_rcp_26 = profits_usd_percGDP - profits_usd_percGDP_baseline",
        ],
        "market projection",
    )
    require_tokens(
        damage,
        [
            'filter(scenario == "Full Adaptation"',
            "I(profit_ppDiff_from_rcp_26/100) ~ 0 + I(tdif_from_rcp26)",
            "write.csv(fish_tcoeff,file=\"Data/output_modules_input_rice50x/input_rice50x/fish_tcoeff.csv\")",
        ],
        "market damage regression",
    )
    require_tokens(
        projection,
        [
            'countrycode(fisheries_df_temp_gdp$country_iso3,origin="iso3c",destination="continent")',
            'countrycode(fisheries_df_temp_gdp$country_iso3,origin="iso3c",destination="region")',
        ],
        "country multiplier assignment",
    )
    require_tokens(
        crosscutting,
        [
            'read.csv("External_Data/other/scenarios/SSP245_magicc_202303021423.csv")',
            'read.csv("External_Data/other/scenarios/SSP585_magicc_202303221353.csv")',
            'read.csv("External_Data/other/scenarios/SSP126_magicc_202308040902.csv")',
            'read.csv("External_Data/other/scenarios/SSP460_magicc_202402051249.csv")',
        ],
        "temperature inputs",
    )
    require_tokens(main, ["'WDI', 'countrycode'"], "runtime package loading")

    upstream_presence = {path: path in tracked_paths for path in upstream_paths}
    lock_presence = {path: path in tracked_paths for path in lock_paths}
    return {
        "formula_findings": {
            "raw_profit_contrast_computed_before_multiplier": True,
            "published_regression_outcome_is_profit_gdp_difference_times_country_multiplier": True,
            "country_multiplier_constant_within_country_in_released_code": True,
            "multiplier_free_slope_equals_published_slope_divided_by_exact_country_multiplier": True,
            "regional_total_multipliers": {
                "Africa": 4.21,
                "Asia": 4.29,
                "Europe": 4.88,
                "Latin America & Caribbean": 3.61,
                "North America": 5.74,
                "Oceania": 5.0,
                "unmatched_default": 4.55,
            },
        },
        "tracked_upstream_inputs": upstream_presence,
        "tracked_required_upstream_files": sum(upstream_presence.values()),
        "required_upstream_files": len(upstream_presence),
        "dependency_locks": lock_presence,
        "tracked_dependency_locks": sum(lock_presence.values()),
        "dependency_lock_candidates": len(lock_presence),
        "reproducibility_findings": {
            "per_country_multiplier_assignment_persisted": False,
            "countrycode_package_version_pinned": False,
            "live_wdi_gdp_query_snapshot_pinned": False,
            "raw_profit_series_tracked": upstream_presence.get(upstream_paths[0], False),
            "derived_regression_panel_tracked": upstream_presence.get(upstream_paths[1], False),
            "exact_multiplier_free_coefficients_reproducible": False,
        },
        "welfare_findings": {
            "released_input_named_profit_not_revenue": True,
            "indirect_and_induced_multiplier_algebraically_separable": True,
            "consumer_surplus_present": False,
            "profit_established_as_producer_surplus": False,
            "consumer_plus_producer_surplus_available": False,
        },
    }


def git_lines(source_root: Path, *arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


def audit(source_root: Path, config_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("decomposition config identity changed")
    if git_lines(source_root, "rev-parse", "HEAD") != [config["source"]["repository_commit"]]:
        raise ValueError("Blue-SCC repository commit changed")
    license_files = [
        path.name
        for path in source_root.iterdir()
        if path.is_file() and path.name.lower().startswith(("license", "copying"))
    ]
    if license_files:
        raise ValueError("root license state changed; review before reuse")

    texts: dict[str, str] = {}
    verified: dict[str, str] = {}
    for name in ("market_projection_script", "market_damage_script", "crosscutting_script", "main_script"):
        path = source_root / config["files"][name]
        observed = sha256(path)
        if observed != config["files"][f"{name}_sha256"]:
            raise ValueError(f"source file hash changed: {name}")
        texts[name] = path.read_text(encoding="utf-8")
        verified[name] = observed

    tracked = set(git_lines(source_root, "ls-tree", "-r", "--name-only", "HEAD"))
    findings = inspect_design(
        texts["market_projection_script"],
        texts["market_damage_script"],
        texts["crosscutting_script"],
        texts["main_script"],
        tracked,
        list(map(str, config["required_upstream"]["paths"])),
        list(map(str, config["dependency_lock"]["paths"])),
    )
    for key in (
        "tracked_required_upstream_files", "required_upstream_files",
        "tracked_dependency_locks", "dependency_lock_candidates",
    ):
        if findings[key] != int(config["expected"][key]):
            raise ValueError(f"registered reproducibility result changed: {key}")

    transfer_path = ROOT / config["local_inputs"]["transfer_receipt"]
    if sha256(transfer_path) != config["local_inputs"]["transfer_receipt_sha256"]:
        raise ValueError("country-transfer receipt changed")
    transfer = json.loads(transfer_path.read_text(encoding="utf-8"))
    if transfer["coverage"]["complete_regions"] != int(config["expected"]["complete_give_regions"]):
        raise ValueError("country-transfer completeness result changed")
    if transfer["claim_gates"]["country_coefficient_transfer_authorized"] is not False:
        raise ValueError("country-transfer receipt improperly opens transfer gate")

    gates = dict(config["claim_gates"])
    if any(gates.values()):
        raise ValueError("decomposition config improperly opens a scientific gate")
    return {
        "schema": "blue_scc_market_welfare_decomposition_audit_v1",
        "role": config["role"],
        "status": "multiplier_algebraically_separable_but_exact_decomposition_not_reproducible",
        "source": config["source"],
        "verified_file_sha256": verified,
        **findings,
        "country_coverage_context": {
            "complete_give_regions": transfer["coverage"]["complete_regions"],
            "incomplete_give_regions": transfer["coverage"]["incomplete_regions"],
            "six_complete_regions_do_not_cure_welfare_semantics": True,
        },
        "interpretation": {
            "no_country_coefficient_derived": True,
            "no_missing_country_filled_or_zeroed": True,
            "no_incomplete_region_renormalized": True,
            "external_source_files_copied": False,
        },
        "claim_gates": gates,
        "provenance": {
            "config_path": str(config_path.relative_to(ROOT)),
            "config_sha256": sha256(config_path),
            "country_transfer_receipt_path": str(transfer_path.relative_to(ROOT)),
            "country_transfer_receipt_sha256": sha256(transfer_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config/blue_scc_market_welfare_decomposition_v1.toml",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "data/provenance/blue_scc_market_welfare_decomposition_audit_20260928.json",
    )
    args = parser.parse_args()
    result = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(result["status"])


if __name__ == "__main__":
    main()
