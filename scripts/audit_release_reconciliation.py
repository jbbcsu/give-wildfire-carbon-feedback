#!/usr/bin/env python3
"""Fail-closed reconciliation of the EPA globalAQ release and article values."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "epa_globalaq_release_reconciliation_config_v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def mean_components(rows: list[dict[str, str]], rate: str) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    by_model: dict[str, dict[str, float]] = {}
    means: dict[str, float] = {}
    for pollutant in ("Ozone", "PM"):
        selected = {
            row["Model"]: float(row["mean_npd"])
            for row in rows
            if row["discount.rate"] == rate and row["Pollutant"] == pollutant
        }
        if set(selected) != {"CESM2", "GISS"} or not all(math.isfinite(value) for value in selected.values()):
            raise ValueError(f"unexpected {pollutant} model support")
        by_model[pollutant] = selected
        means[pollutant] = sum(selected.values()) / len(selected)
    return means, by_model


def mean_net(rows: list[dict[str, str]], rate: str) -> tuple[float, dict[str, float]]:
    selected = {
        row["Model"]: float(row["mean_npd"])
        for row in rows
        if row["discount.rate"] == rate
    }
    if set(selected) != {"CESM2", "GISS"} or not all(math.isfinite(value) for value in selected.values()):
        raise ValueError("unexpected net model support")
    return sum(selected.values()) / len(selected), selected


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ValueError(f"source tokens changed in {path.name}: {missing}")


def close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def audit(repo: Path, config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("release reconciliation config schema changed")
    source = config["source"]
    if git_output(repo, "rev-parse", "HEAD") != source["commit"]:
        raise ValueError("vendor checkout commit changed")
    if git_output(repo, "remote", "get-url", "origin") != source["repository_url"] + ".git":
        raise ValueError("vendor origin changed")
    tree_paths = git_output(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    if len(tree_paths) != source["tree_entry_count"]:
        raise ValueError("official repository tree size changed")

    for relative, expected_hash in config["verified_files"].items():
        path = repo / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing regular source file: {relative}")
        if sha256_file(path) != expected_hash:
            raise ValueError(f"source hash changed: {relative}")
    for relative, tokens in config["required_source_tokens"].items():
        require_tokens(repo / relative, tokens)

    rate = config["article"]["discount_schedule"]
    rff_components, rff_models = mean_components(
        read_csv(repo / "output/npd/npd_global_rff_means.csv"), rate
    )
    rff_net, rff_net_models = mean_net(
        read_csv(repo / "output/npd/npd_global_rff_net_means.csv"), rate
    )
    mean_components_result, mean_models = mean_components(
        read_csv(repo / "output/npd/npd_global_means.csv"), rate
    )
    expected = config["expected_checked_in_summaries"]
    tolerance = float(expected["tolerance"])
    for pollutant, value in expected["rff_component_means"].items():
        if not close(rff_components[pollutant], value, tolerance):
            raise ValueError(f"registered RFF {pollutant} mean changed")
    if not close(rff_net, expected["rff_net_mean"], tolerance):
        raise ValueError("registered RFF net mean changed")
    for pollutant, value in expected["mean_path_component_means"].items():
        if not close(mean_components_result[pollutant], value, tolerance):
            raise ValueError(f"registered mean-path {pollutant} mean changed")

    article = config["article"]["reported_usd_per_tco2"]
    component_sum = sum(rff_components.values())
    checked_in_parquet = [path for path in tree_paths if path.endswith(".parquet")]
    dependency_manifests = [
        path for path in tree_paths
        if Path(path).name.lower() in {
            "renv.lock", "description", "environment.yml", "environment.yaml",
            "requirements.txt", "sessioninfo.txt",
        }
    ]
    gates = config["claim_gates"]
    if any(gates.values()):
        raise ValueError("claim gate unexpectedly open")

    return {
        "schema": "epa_globalaq_release_reconciliation_audit_v1",
        "role": config["role"],
        "status": "blocked_no_post_submission_release_and_article_generating_streams_absent",
        "source": {
            "repository_url": source["repository_url"],
            "commit": source["commit"],
            "commit_date": source["commit_date"],
            "code_license": source["code_license"],
            "repository_data_license": source["repository_data_license"],
            "tree_entry_count": len(tree_paths),
            "verified_file_sha256": config["verified_files"],
        },
        "official_api_observation": config["official_api_observation"],
        "checked_in_2pct_ramsey": {
            "rff_component_means_usd_per_tco2": rff_components,
            "rff_component_model_values": rff_models,
            "rff_component_sum_usd_per_tco2": component_sum,
            "rff_net_mean_usd_per_tco2": rff_net,
            "rff_net_model_values": rff_net_models,
            "rff_net_minus_component_sum_usd_per_tco2": rff_net - component_sum,
            "mean_path_component_means_usd_per_tco2": mean_components_result,
            "mean_path_component_model_values": mean_models,
        },
        "article_comparison": {
            "reported_usd_per_tco2": article,
            "article_minus_checked_in_rff": {
                "Ozone": article["Ozone"] - rff_components["Ozone"],
                "PM": article["PM"] - rff_components["PM"],
                "Net": article["Net"] - rff_net,
            },
            "rff_components_reproduce_article": all(
                close(rff_components[key], article[key], tolerance) for key in ("Ozone", "PM")
            ),
            "mean_path_components_reproduce_article": all(
                close(mean_components_result[key], article[key], tolerance) for key in ("Ozone", "PM")
            ),
            "checked_in_net_equals_checked_in_component_sum": close(rff_net, component_sum, tolerance),
            "article_net_equals_article_component_sum": close(
                article["Net"], article["Ozone"] + article["PM"], tolerance
            ),
        },
        "artifact_inventory": {
            "checked_in_parquet_paths": checked_in_parquet,
            "dependency_manifest_paths": dependency_manifests,
            "missing_required_artifacts": config["missing_required_artifacts"],
            "ignored_upstream_patterns": [
                "input/RFF/pop_income/*",
                "input/RFF/temperature/**",
                "input/RFF/rft_inputs/*",
                "output/rft/*",
                "output/npd/npd_country*",
                "output/npd/npd_full_streams*",
            ],
        },
        "interpretation": {
            "official_head_still_equals_submission_commit_at_observation_date": True,
            "official_release_or_tag_identifies_article_version": False,
            "checked_in_summary_variants_do_not_reproduce_article_components": True,
            "checked_in_component_and_net_summaries_are_not_same_run_additive": True,
            "currency_price_year_conflict_requires_author_clarification": True,
            "article_values_remain_external_benchmarks_only": True,
            "wildfire_files_or_estimates_used": False,
            "new_estimate_or_imputation_performed": False,
        },
        "required_author_delivery": [
            "article_generating_commit_or_versioned_archive",
            "artifact_manifest_with_sha256_license_and_derivation",
            "exact_R_environment_lock_and_session_info",
            "complete_RFF_population_income_temperature_and_mortality_inputs",
            "matched_2030_CO2_baseline_and_perturbed_pulse_metadata",
            "complete_10000_trial_country_year_pollutant_damage_streams_or_equivalent_reproducible_chunks",
            "same_run_component_and_net_summaries_reconciling_to_article_values",
            "explicit_currency_price_year_reconciling_2024_inputs_with_2020_NPV_header",
            "machine_readable_nonwildfire_PM25_emissions_and_species_boundary",
        ],
        "claim_gates": gates,
        "config": {
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256_file(config_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "vendor/globalAQ_rft")
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config/epa_globalaq_release_reconciliation_v1.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "data/provenance/epa_globalaq_release_reconciliation_20261013.json",
    )
    args = parser.parse_args()
    result = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("EPA globalAQ article reproduction remains blocked: final matched streams are not released")


if __name__ == "__main__":
    main()
