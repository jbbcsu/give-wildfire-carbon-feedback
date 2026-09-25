#!/usr/bin/env python3
"""Validate the preliminary quantity-channel SCC release bundle and boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path, schema: str, status: str | None = None) -> dict:
    value = json.loads(path.read_text())
    require(value.get("schema") == schema, f"schema differs: {path}")
    if status is not None:
        require(value.get("status") == status, f"status differs: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    require(not output.exists(), "fresh output required")

    paths = {
        "paired_structural": root / "data/provenance/quantity_full_structural_paired_ensemble_20260924.json",
        "coefficient_grid": root / "data/provenance/quantity_coefficient_delta_uncertainty_grid_20260925.json",
        "coefficient_by_model": root / "data/provenance/quantity_coefficient_delta_by_model_20260925.json",
        "coefficient_market_grid": root / "data/provenance/quantity_coefficient_delta_market_grid_20260925.json",
        "coefficient_market_job": root / "data/provenance/quantity_coefficient_delta_market_grid_job_20260925.json",
        "country_decomposition": root / "data/provenance/quantity_scc_country_decomposition_20260925.json",
        "country_decomposition_job": root / "data/provenance/quantity_scc_country_decomposition_job_20260925.json",
        "country_decomposition_report": root / "QUANTITY_SCC_COUNTRY_DECOMPOSITION_RESULTS_20260925.md",
        "country_decomposition_figure": root / "manuscript/figures/quantity_scc_country_decomposition_20260925.svg",
        "country_decomposition_figure_validation": root / "data/provenance/quantity_scc_country_decomposition_figure_20260925.json",
        "period_decomposition": root / "data/provenance/quantity_scc_period_decomposition_20260925.json",
        "period_decomposition_job": root / "data/provenance/quantity_scc_period_decomposition_job_20260925.json",
        "period_decomposition_report": root / "QUANTITY_SCC_PERIOD_DECOMPOSITION_RESULTS_20260925.md",
        "period_discount_grid": root / "data/provenance/quantity_scc_period_discount_grid_20260925.json",
        "manuscript_validation": root / "data/provenance/manuscript_scc_claim_validation_20260925.json",
        "manuscript_reference_registry": root / "data/provenance/manuscript_reference_registry_20260925.json",
        "manuscript_reference_validation": root / "data/provenance/manuscript_reference_validation_20260925.json",
        "manuscript_link_validation": root / "data/provenance/manuscript_link_validation_20260925.json",
        "figure_validation": root / "data/provenance/quantity_coefficient_interval_figure_20260925.json",
        "manuscript": root / "manuscript/MAIN_MANUSCRIPT.md",
        "methods_si": root / "manuscript/METHODS_SUPPORTING_INFORMATION.md",
        "figure": root / "manuscript/figures/quantity_coefficient_intervals_20260925.svg",
        "table3": root / "manuscript/tables/TABLE_3_SCC_RESULTS.md",
        "table3_validation": root / "data/provenance/manuscript_scc_table_20260925.json",
        "targeted_test_job": root / "data/provenance/preliminary_scc_targeted_tests_job_20260925.json",
    }
    for path in paths.values():
        require(path.is_file(), f"release file missing: {path}")

    paired = load(paths["paired_structural"], "quantity_full_structural_paired_ensemble/v1",
                  "paired_full_registered_market_adaptation_tail_design_pass")
    grid = load(paths["coefficient_grid"], "quantity_coefficient_delta_uncertainty_grid/v1",
                "published_coefficient_covariance_delta_grid_complete")
    by_model = load(paths["coefficient_by_model"], "quantity_coefficient_delta_by_model/v1",
                    "coefficient_only_delta_by_climate_model_complete")
    market_grid = load(paths["coefficient_market_grid"], "quantity_coefficient_delta_market_grid/v1",
                       "fixed_uncapped_two_percent_market_grid_complete")
    market_job = json.loads(paths["coefficient_market_job"].read_text())
    country = load(
        paths["country_decomposition"],
        "quantity_scc_country_decomposition/v1",
        "central_fixed_uncapped_two_percent_country_decomposition_complete",
    )
    country_job = json.loads(paths["country_decomposition_job"].read_text())
    country_figure = load(
        paths["country_decomposition_figure_validation"],
        "quantity_scc_country_decomposition_figure/v1",
        "pass",
    )
    period = load(
        paths["period_decomposition"],
        "quantity_scc_period_decomposition/v1",
        "central_fixed_uncapped_two_percent_period_decomposition_complete",
    )
    period_job = json.loads(paths["period_decomposition_job"].read_text())
    period_grid = load(
        paths["period_discount_grid"],
        "quantity_scc_period_discount_grid/v1",
        "four_schedule_period_decomposition_complete",
    )
    manuscript_validation = load(paths["manuscript_validation"], "manuscript_scc_claim_validation/v1", "pass")
    reference_validation = load(
        paths["manuscript_reference_validation"], "manuscript_reference_validation/v1", "pass"
    )
    link_validation = load(paths["manuscript_link_validation"], "manuscript_link_validation/v1", "pass")
    figure_validation = load(paths["figure_validation"], "quantity_coefficient_interval_figure/v1", "pass")
    table3_validation = load(paths["table3_validation"], "manuscript_scc_table/v1", "pass")
    targeted_test_job = json.loads(paths["targeted_test_job"].read_text())

    require(paired["support"]["paired_paths"] == 936, "paired path count differs")
    require(paired["support"]["result_rows"] == 3744, "paired SCC count differs")
    require(paired["validation"]["all_3744_external_values_reconstructed_exactly"], "paired reconstruction failed")
    require(paired["validation"]["all_paired_errors_below_bounds"], "paired numerical bounds failed")
    require(paired["validation"]["baseline_agriculture_and_cpc_exact_every_run"], "baseline preservation failed")
    require(paired["claim_gates"]["paired_registered_structural_design"], "paired claim gate closed")
    require(not paired["claim_gates"]["full_precipitation_agriculture_scc"], "full-SCC gate unexpectedly open")

    require(len(grid["results"]) == 4, "discount grid differs")
    require(by_model["validation"] == {
        "all_rows": 104,
        "all_values_finite": True,
        "maximum_central_value_error_usd2020_per_tco2": by_model["validation"]["maximum_central_value_error_usd2020_per_tco2"],
        "maximum_shared_mean_se_error_usd2020_per_tco2": 0.0,
    }, "by-model validation fields differ")
    require(by_model["validation"]["maximum_central_value_error_usd2020_per_tco2"] <= 2e-14,
            "by-model central reconstruction failed")
    require(all(not value for key, value in grid["claim_gates"].items()
                if key != "published_coefficient_covariance_delta_method"),
            "coefficient claim boundary unexpectedly open")
    require(grid["claim_gates"]["published_coefficient_covariance_delta_method"],
            "coefficient delta gate closed")
    require(len(market_grid["results"]) == 6, "coefficient market grid differs")
    require(all(row["normal_approximation_95_interval_usd2020_per_tco2"][1] < 0
                for row in market_grid["results"]), "market coefficient interval crosses zero")
    require(market_grid["validation"]["maximum_directional_derivative_relative_error"] <= 5e-4,
            "market derivative validation failed")
    require(market_job["status"] == "completed" and market_job["returncode"] == 0,
            "market coefficient job failed")
    require(country["summary"]["countries"] == 106, "country decomposition support differs")
    require(country["summary"]["negative_country_count"] == 61, "negative country count differs")
    require(country["summary"]["positive_country_count"] == 45, "positive country count differs")
    require(country["summary"]["country_components_changing_sign_across_models"] == 106,
            "country sign-change count differs")
    require(abs(country["summary"]["usa_china_share_of_gross_absolute_components"] - 0.7491735302529217)
            <= 1e-14, "country concentration share differs")
    require(abs(country["summary"]["leave_out_usa_and_china_global_mean_usd2020_per_tco2"]
                - (-0.00024980407854519656)) <= 1e-14,
            "country leave-out diagnostic differs")
    require(abs(country["summary"]["global_equal_model_mean_usd2020_per_tco2"]
                - next(row for row in grid["results"] if row["discount_rate_label"] == "2.0%")["central_mean_usd2020_per_tco2"])
            <= 2e-14, "country/global SCC mean differs")
    require(country["validation"]["maximum_model_reconstruction_error_usd2020_per_tco2"] <= 2e-14,
            "country model reconstruction failed")
    require(country_job["status"] == "completed" and country_job["returncode"] == 0,
            "country decomposition job failed")
    require(country_job["sampled_peak_group_rss_bytes"] <= 768 * 1024 * 1024,
            "country decomposition exceeded memory contract")
    require(digest(paths["country_decomposition_figure"]) == country_figure["output"]["sha256"],
            "country figure changed after validation")
    require(digest(paths["country_decomposition"]) ==
            country_figure["sources"]["decomposition_receipt"]["sha256"],
            "country figure source changed after validation")
    require(len(period["summary"]["periods"]) == 4, "period decomposition support differs")
    require(abs(sum(row["share_of_signed_total"] for row in period["summary"]["periods"]) - 1.0)
            <= 1e-14, "period shares do not sum to one")
    require(abs(sum(row["discounted_contribution_usd2020_per_tco2"]
                    for row in period["summary"]["periods"])
                - period["summary"]["global_equal_model_mean_usd2020_per_tco2"]) <= 2e-14,
            "period contributions do not reconstruct global mean")
    require(period["validation"]["maximum_model_reconstruction_error_usd2020_per_tco2"] <= 2e-14,
            "period model reconstruction failed")
    require(period_job["status"] == "completed" and period_job["returncode"] == 0,
            "period decomposition job failed")
    require(period_job["sampled_peak_group_rss_bytes"] <= 768 * 1024 * 1024,
            "period decomposition exceeded memory contract")
    require(len(period_grid["results"]) == 4, "period discount grid differs")
    require(period_grid["validation"]["model_schedule_totals"] == 104,
            "period model-schedule support differs")
    require(period_grid["validation"]["maximum_model_reconstruction_error_usd2020_per_tco2"] <= 2e-14,
            "period discount-grid reconstruction failed")
    through_2100 = [sum(row["share_of_signed_total"] for row in result["periods"][:2])
                    for result in period_grid["results"]]
    require(all(left < right for left, right in zip(through_2100, through_2100[1:])),
            "through-2100 shares not ordered by discount schedule")
    manuscript_text = " ".join(paths["manuscript"].read_text().split())
    for fragment in (
        "Sixty-one of 106 country components are negative",
        "United States (-$0.00353)",
        "Mexico (+$0.00031)",
        "not country causal effects",
        "every country component does",
        "remaining global mean to -$0.00025 per tCO2",
        "44.1% accrues in 2020--2050",
        "quantity channel is therefore small per year",
        "60.2%, 71.4%, 80.6%, and 87.2%",
    ):
        require(fragment in manuscript_text, f"country claim fragment missing: {fragment}")

    manuscript_source = manuscript_validation["sources"]["manuscript"]
    require(digest(paths["manuscript"]) == manuscript_source["sha256"], "manuscript changed after validation")
    require(digest(paths["manuscript"]) == reference_validation["sources"]["manuscript"]["sha256"],
            "manuscript changed after reference validation")
    require(digest(paths["manuscript_reference_registry"]) ==
            reference_validation["sources"]["registry"]["sha256"],
            "reference registry changed after validation")
    require(reference_validation["checks"]["registered_dois"] == 6,
            "manuscript reference support differs")
    require(reference_validation["checks"]["wildfire_agriculture_doi_nonconflation"],
            "wildfire and agriculture citations conflated")
    require(link_validation["checks"]["local_links_resolved"] == 22,
            "manuscript local-link support differs")
    require(link_validation["checks"]["missing_local_links"] == 0,
            "manuscript local links missing")
    require(digest(paths["manuscript"]) ==
            link_validation["sources"]["manuscript/MAIN_MANUSCRIPT.md"]["sha256"],
            "manuscript changed after link validation")
    require(digest(paths["methods_si"]) ==
            link_validation["sources"]["manuscript/METHODS_SUPPORTING_INFORMATION.md"]["sha256"],
            "Methods SI changed after link validation")
    require(digest(paths["figure"]) == figure_validation["output"]["sha256"], "figure changed after validation")
    require(digest(paths["coefficient_by_model"]) == figure_validation["sources"]["input"]["sha256"],
            "figure source changed after validation")
    require(digest(paths["table3"]) == table3_validation["output"]["sha256"],
            "Table 3 changed after validation")
    require(targeted_test_job["status"] == "completed" and targeted_test_job["returncode"] == 0,
            "targeted quantity/welfare tests failed")
    require(targeted_test_job["sampled_peak_group_rss_bytes"] <= 512 * 1024 * 1024,
            "targeted tests exceeded memory contract")

    tracked_raw = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    ).stdout.decode().split("\0")
    tracked_raw = [path for path in tracked_raw if path]
    prohibited_path = re.compile(r"(^|/)data/(raw|interim|processed|outputs)/|(^|/)(\.env|nass\.env|credentials[^/]*)$")
    prohibited_tracked = [path for path in tracked_raw if prohibited_path.search(path)]
    require(not prohibited_tracked, f"restricted paths tracked: {prohibited_tracked}")
    wildfire_named = [path for path in tracked_raw if "wildfire" in path.lower()]
    require(not wildfire_named, f"wildfire artifacts tracked in isolated project: {wildfire_named}")

    secret_pattern = re.compile(
        rb"(?i)(NASS_API_KEY|AWS_SECRET_ACCESS_KEY|OPENAI_API_KEY)\s*=\s*([^\s<>{}\"'`]+)"
    )
    secret_hits = []
    for relative in tracked_raw:
        path = root / relative
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            continue
        data = path.read_bytes()
        for match in secret_pattern.finditer(data):
            value = match.group(2)
            if value.startswith(b"...") or value.startswith(b"secret-never-print"):
                continue
            secret_hits.append(relative)
            break
    require(not secret_hits, f"credential-like assignments in tracked files: {secret_hits}")

    result = {
        "schema": "preliminary_scc_release_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "release_scope": "paired annual-global-maize rainfall-quantity SCC benchmark; not total precipitation-agriculture SCC",
        "checks": {
            "paired_paths": 936,
            "paired_scc_values": 3744,
            "coefficient_discount_schedules": 4,
            "coefficient_model_schedule_rows": 104,
            "coefficient_market_specifications": 6,
            "country_accounting_components": 106,
            "country_decomposition_models": 26,
            "country_decomposition_memory_budget_mib": 768,
            "country_decomposition_figure_hash_bound": True,
            "period_accounting_bins": 4,
            "period_decomposition_memory_budget_mib": 768,
            "period_discount_schedules": 4,
            "manuscript_hash_bound": True,
            "manuscript_doi_references_validated": 6,
            "wildfire_agriculture_doi_nonconflation": True,
            "manuscript_local_links_resolved": 22,
            "figure_hash_bound": True,
            "table3_hash_bound": True,
            "tracked_files_scanned": len(tracked_raw),
            "restricted_tracked_paths": 0,
            "credential_like_tracked_assignments": 0,
            "wildfire_named_tracked_paths": 0,
            "targeted_quantity_welfare_unit_tests": 11,
        },
        "claim_gates": {
            "paired_quantity_channel_scc": True,
            "full_precipitation_agriculture_scc": False,
            "probabilistic_total_uncertainty": False,
            "causal_drought_or_timing_scc": False,
        },
        "sources": {name: {"path": str(path.relative_to(root)), "sha256": digest(path)}
                    for name, path in paths.items()},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(root)),
                           "sha256": digest(Path(__file__).resolve())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "checks": result["checks"], "claim_gates": result["claim_gates"]}, indent=2))


if __name__ == "__main__":
    main()
