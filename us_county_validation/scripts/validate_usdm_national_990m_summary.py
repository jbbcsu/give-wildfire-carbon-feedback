#!/usr/bin/env python3
"""Independently validate the final national 990 m USDM summary artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERMS = [f"d{level}_weeks" for level in range(5)]
MODEL_KEYS = {
    (crop, irrigation)
    for crop in ("corn_grain", "soybeans")
    for irrigation in ("dryland", "irrigated")
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def validate_result(payload: dict, family: str) -> dict[tuple[str, str, str], float]:
    rows = payload["coefficients"]
    require(len(rows) == 20, f"{family} must have 20 coefficients")
    values: dict[tuple[str, str, str], float] = {}
    for row in rows:
        require(row["family"] == family, f"coefficient family differs in {family}")
        key = (str(row["outcome_crop"]), str(row["irrigation_class"]), str(row["term"]))
        require(key[:2] in MODEL_KEYS and key[2] in TERMS, f"unexpected coefficient key {key}")
        require(key not in values, f"duplicate coefficient key {key}")
        value = float(row["exact_percent_change_per_equivalent_week"])
        require(math.isfinite(value), f"nonfinite coefficient {key}")
        values[key] = value
    require(len(values) == 20, f"{family} coefficient support differs")
    path = resolve(payload["path"])
    require(path.is_file() and sha256(path) == payload["sha256"], f"{family} result identity differs")
    return values


def expected_movement(left: dict, right: dict) -> tuple[float, tuple[tuple[str, str, str], float]]:
    changes = {key: abs(left[key] - right[key]) for key in sorted(left)}
    return sum(changes.values()) / len(changes), max(changes.items(), key=lambda item: item[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--merged-validation", type=Path, required=True)
    parser.add_argument("--component-validation", type=Path, action="append", required=True)
    parser.add_argument("--resource-receipt", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text())
    merged = json.loads(args.merged_validation.read_text())
    require(summary["schema"] == "usdm_agricultural_area_spatial_basis_comparison_v1", "summary schema differs")
    for gate in ("causal_claim_authorized", "damage_claim_authorized", "global_transfer_authorized", "scc_claim_authorized"):
        require(summary.get(gate) is False, f"summary opens {gate}")
    require(set(summary["bases"]) == {"county", "cultivated", "broad"}, "basis set differs")
    require(summary.get("rejected_3_96km_diagnostic", {}).get("status") == "rejected_by_frozen_native_resolution_sentinel_gate", "rejected diagnostic boundary differs")

    require(merged.get("passed") is True, "merged validator did not pass")
    require(merged["state_count"] == 48, "state count differs")
    require(merged["counties"] == 2909, "county count differs")
    require(merged["rows"] == 2909 * 2 * 13, "merged row count differs")
    require(merged["maximum_grid_peak_rss_bytes"] <= args.memory_cap_bytes, "grid memory cap failed")
    require(merged["maximum_exposure_peak_rss_bytes"] <= args.memory_cap_bytes, "exposure memory cap failed")
    require(len(merged["partitions"]) == 48, "partition receipt count differs")
    require(len({row["state_fips"] for row in merged["partitions"]}) == 48, "partition state IDs differ")

    require(len(args.component_validation) == 6, "expected six component validation receipts")
    component_receipts = []
    for path in args.component_validation:
        payload = json.loads(path.read_text())
        require(payload.get("status") == "passed", f"component validator did not pass: {path}")
        component_receipts.append({"path": str(path), "sha256": sha256(path), "schema": payload["schema"]})
    require(len({row["path"] for row in component_receipts}) == 6, "component validation paths repeat")

    require(len(args.resource_receipt) == 6, "expected six component resource receipts")
    resource_receipts = []
    for path in args.resource_receipt:
        payload = json.loads(path.read_text())
        require(payload.get("status") == "command_completed", f"component command did not complete: {path}")
        require(payload.get("returncode") == 0, f"component command failed: {path}")
        require(payload["peak_rss_bytes"] <= args.memory_cap_bytes, f"component memory cap failed: {path}")
        resource_receipts.append({
            "path": str(path), "sha256": sha256(path),
            "peak_rss_bytes": payload["peak_rss_bytes"], "wall_seconds": payload["wall_seconds"],
        })
    require(len({row["path"] for row in resource_receipts}) == 6, "resource receipt paths repeat")

    coefficient_sets: dict[tuple[str, str], dict] = {}
    expected_basis_text = {
        "county": "county",
        "cultivated": "990m",
        "broad": "990m",
    }
    for basis, basis_payload in summary["bases"].items():
        exposure = basis_payload["exposure"]
        exposure_path = resolve(exposure["path"])
        require(exposure_path.is_file() and sha256(exposure_path) == exposure["sha256"], f"{basis} exposure identity differs")
        require(expected_basis_text[basis] in exposure["source_area_basis"].lower(), f"{basis} source label differs")
        require(exposure["counties"] > 0 and exposure["unique_county_years"] > 0, f"{basis} support is empty")
        for family in ("drought_only", "drought_plus_weather"):
            coefficient_sets[basis, family] = validate_result(basis_payload[family], family)
        if basis != "county":
            robustness = basis_payload["state_robustness"]
            require(len(robustness["coefficients"]) == 20, f"{basis} robustness support differs")
            robustness_path = resolve(robustness["path"])
            require(robustness_path.is_file() and sha256(robustness_path) == robustness["sha256"], f"{basis} robustness identity differs")

    pair_map = {
        "county_vs_cultivated": ("county", "cultivated"),
        "county_vs_broad": ("county", "broad"),
        "cultivated_vs_broad": ("cultivated", "broad"),
    }
    maximum_movement_error = 0.0
    for family in ("drought_only", "drought_plus_weather"):
        reported_family = summary["coefficient_movements_within_final_comparison"][family]
        for pair, (left, right) in pair_map.items():
            reported = reported_family[pair]
            mean_value, (maximum_key, maximum_value) = expected_movement(
                coefficient_sets[left, family], coefficient_sets[right, family]
            )
            errors = [
                abs(mean_value - reported["mean_absolute_movement_percentage_point_per_equivalent_week"]),
                abs(maximum_value - reported["maximum_absolute_movement"]["absolute_movement_percentage_point_per_equivalent_week"]),
            ]
            maximum_movement_error = max(maximum_movement_error, *errors)
            require(errors[0] <= 1e-12 and errors[1] <= 1e-12, f"movement arithmetic differs for {family}/{pair}")
            require(reported["coefficient_count"] == 20, f"movement count differs for {family}/{pair}")
            reported_key = tuple(reported["maximum_absolute_movement"][field] for field in ("outcome_crop", "irrigation_class", "term"))
            require(reported_key == maximum_key, f"maximum movement key differs for {family}/{pair}")

    receipt = {
        "schema": "usdm_national_990m_summary_independent_validation_v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "summary": {"path": str(args.summary), "sha256": sha256(args.summary)},
        "merged_validation": {"path": str(args.merged_validation), "sha256": sha256(args.merged_validation)},
        "state_count": merged["state_count"],
        "counties": merged["counties"],
        "merged_rows": merged["rows"],
        "maximum_grid_peak_rss_bytes": merged["maximum_grid_peak_rss_bytes"],
        "maximum_exposure_peak_rss_bytes": merged["maximum_exposure_peak_rss_bytes"],
        "maximum_component_peak_rss_bytes": max(row["peak_rss_bytes"] for row in resource_receipts),
        "component_validations": component_receipts,
        "component_resources": resource_receipts,
        "maximum_movement_recalculation_error": maximum_movement_error,
        "claim_boundary": "historical U.S. exposure and association validation only; not causal, future, damage, global-transfer, or SCC evidence",
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "global_transfer_authorized": False,
        "scc_claim_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: receipt[key] for key in ("status", "state_count", "counties", "merged_rows", "maximum_movement_recalculation_error")}, indent=2))


if __name__ == "__main__":
    main()
