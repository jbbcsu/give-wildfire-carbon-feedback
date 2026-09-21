#!/usr/bin/env python3
"""Export the audited five-ESM weather contrasts without annual panel ledgers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from render_five_esm_maize_area_weather_report import render


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_public(result: dict, audit: dict, primary_resource: dict,
                 audit_resource: dict, result_sha: str, audit_sha: str) -> dict:
    # Reuse the report's interpretation and 120-manifest completeness gates.
    render(result, audit, result_sha, audit_sha)
    for label, receipt in (("primary", primary_resource), ("audit", audit_resource)):
        if receipt.get("status") != "completed" or receipt.get("returncode") != 0:
            raise ValueError(f"{label} resource receipt did not pass")
        if receipt.get("max_mib") != 512 or receipt.get("min_free_gib") != 130:
            raise ValueError(f"{label} resource contract changed")
    return {
        "status": "public_five_esm_fixed_area_weather_only_not_forced_response_yield_damage_or_scc",
        "primary_result_sha256": result_sha,
        "independent_audit_sha256": audit_sha,
        "crop": result["crop"],
        "irrigation": result["irrigation"],
        "weight_year": result["weight_year"],
        "weights_sha256": result["weights_sha256"],
        "years": result["years"],
        "esms": result["esms"],
        "scenarios": result["scenarios"],
        "original_positive_area_cells": result["original_positive_area_cells"],
        "original_positive_area_ha": result["original_positive_area_ha"],
        "matched_calendar_cells": result["matched_calendar_cells"],
        "matched_area_ha": result["matched_area_ha"],
        "matched_area_fraction": result["matched_area_fraction"],
        "scenario_minus_ssp126": result["scenario_minus_ssp126"],
        "audit": {
            key: audit[key] for key in (
                "annual_numeric_checks", "contrast_numeric_checks",
                "fixed_source_tile_checks", "bound_annual_source_manifests",
                "no_yield_damage_scc_estimated",
            )
        },
        "resources": {
            "primary_sampled_peak_group_rss_bytes": primary_resource["sampled_peak_group_rss_bytes"],
            "audit_sampled_peak_group_rss_bytes": audit_resource["sampled_peak_group_rss_bytes"],
            "primary_sampled_peak_new_disk_bytes": primary_resource["sampled_peak_new_disk_bytes"],
            "audit_sampled_peak_new_disk_bytes": audit_resource["sampled_peak_new_disk_bytes"],
        },
        "models_are_not_probability_draws": True,
        "annual_panels_in_public_receipt": False,
        "yield_damage_scc_estimated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--primary-resource", type=Path, required=True)
    parser.add_argument("--audit-resource", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("fresh output required")
    result_sha, audit_sha = sha(args.result), sha(args.audit)
    public = build_public(
        json.loads(args.result.read_text()), json.loads(args.audit.read_text()),
        json.loads(args.primary_resource.read_text()),
        json.loads(args.audit_resource.read_text()), result_sha, audit_sha,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(public, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(args.out)


if __name__ == "__main__":
    main()
