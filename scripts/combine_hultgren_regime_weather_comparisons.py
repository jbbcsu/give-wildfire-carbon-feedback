#!/usr/bin/env python3
"""Combine validated rainfed/irrigated weather contrasts on unique cell support."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALL_SUPPORT = [
    "gdd", "kdd",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
    "season_total_mm", "monthly_square_sum_mm2",
]
DISTRIBUTION = ["monthly_concentration", "phase1_share", "phase2_share", "phase3_share"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def combine_rows(rainfed: dict, irrigated: dict) -> dict:
    rf_area = float(rainfed["area_ha"])
    ir_area = float(irrigated["area_ha"])
    total_area = rf_area + ir_area
    require(total_area > 0, "zero combined area")
    result = {
        "harvest_year": int(rainfed["harvest_year"]),
        "rainfed_area_ha": rf_area,
        "irrigated_area_ha": ir_area,
        "combined_area_ha": total_area,
        "fixed_irrigated_area_share": ir_area / total_area,
    }
    for label in ("reference", "comparison"):
        result[f"{label}_zero_precipitation_area_fraction"] = (
            rf_area * rainfed[f"{label}_zero_precipitation_area_fraction"]
            + ir_area * irrigated[f"{label}_zero_precipitation_area_fraction"]
        ) / total_area
    for metric in ALL_SUPPORT:
        for label in ("reference", "comparison"):
            result[f"{label}_{metric}"] = (
                rf_area * rainfed[f"{label}_{metric}"] + ir_area * irrigated[f"{label}_{metric}"]
            ) / total_area
        result[f"delta_{metric}"] = result[f"comparison_{metric}"] - result[f"reference_{metric}"]
    rf_distribution_area = rf_area * rainfed["distribution_common_positive_area_fraction"]
    ir_distribution_area = ir_area * irrigated["distribution_common_positive_area_fraction"]
    distribution_area = rf_distribution_area + ir_distribution_area
    require(distribution_area > 0, "zero combined distribution support")
    result["distribution_common_positive_area_fraction"] = distribution_area / total_area
    for metric in DISTRIBUTION:
        for label in ("reference", "comparison"):
            result[f"{label}_{metric}"] = (
                rf_distribution_area * rainfed[f"{label}_{metric}"]
                + ir_distribution_area * irrigated[f"{label}_{metric}"]
            ) / distribution_area
        result[f"delta_{metric}"] = result[f"comparison_{metric}"] - result[f"reference_{metric}"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rainfed", type=Path, required=True)
    parser.add_argument("--irrigated", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    sources = [json.loads(path.read_text(encoding="utf-8")) for path in (args.rainfed, args.irrigated)]
    for source in sources:
        require(source["status"] == "weather_basis_comparison_not_yield_damage_or_scc", "source comparison failed")
        require(source["direction"] == "comparison_minus_reference", "comparison direction differs")
    require(sources[0]["reference"]["label"] == sources[1]["reference"]["label"], "reference labels differ")
    require(sources[0]["comparison"]["label"] == sources[1]["comparison"]["label"], "comparison labels differ")
    rf_annual = {int(row["harvest_year"]): row for row in sources[0]["annual_area_weighted"]}
    ir_annual = {int(row["harvest_year"]): row for row in sources[1]["annual_area_weighted"]}
    require(rf_annual.keys() == ir_annual.keys(), "annual support differs")
    annual = [combine_rows(rf_annual[year], ir_annual[year]) for year in sorted(rf_annual)]

    # Convert pooled records to the same field names used by annual rows. Area is
    # constant across years under fixed MIRCA support, so the first annual area is exact.
    pooled_inputs = []
    for source, annual_lookup in zip(sources, (rf_annual, ir_annual)):
        pooled = dict(source["pooled_area_year_weighted"])
        first = annual_lookup[min(annual_lookup)]
        pooled["harvest_year"] = min(annual_lookup)
        pooled["area_ha"] = first["area_ha"]
        for label in ("reference", "comparison"):
            pooled[f"{label}_zero_precipitation_area_fraction"] = pooled.pop(
                f"{label}_zero_precipitation_area_year_fraction"
            )
        pooled["distribution_common_positive_area_fraction"] = pooled.pop(
            "distribution_common_positive_area_year_fraction"
        )
        pooled_inputs.append(pooled)
    pooled = combine_rows(*pooled_inputs)
    pooled.pop("harvest_year")
    pooled["years"] = len(annual)
    pooled["rainfed_cell_years"] = int(sources[0]["pooled_area_year_weighted"]["cell_years"])
    pooled["irrigated_cell_years"] = int(sources[1]["pooled_area_year_weighted"]["cell_years"])

    result = {
        "schema": "hultgren_combined_regime_weather_scenario_comparison/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "fixed_area_combined_weather_comparison_not_yield_damage_or_scc",
        "reference_label": sources[0]["reference"]["label"],
        "comparison_label": sources[0]["comparison"]["label"],
        "direction": "comparison_minus_reference",
        "sources": {
            "rainfed": {"path": str(args.rainfed), "sha256": digest(args.rainfed)},
            "irrigated": {"path": str(args.irrigated), "sha256": digest(args.irrigated)},
        },
        "annual_fixed_area_weighted": annual,
        "pooled_fixed_area_year_weighted": pooled,
        "interpretation": "rainfed and irrigated comparisons combined with fixed eligible MIRCA hectares on globally unique cell/regime support; no endogenous irrigation or adaptation",
        "claim_gates": {"physical_weather_contrast": True, "yield_damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "pooled": pooled}, indent=2))


if __name__ == "__main__":
    main()
