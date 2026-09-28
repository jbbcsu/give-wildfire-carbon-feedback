#!/usr/bin/env python3
"""Audit geographic heterogeneity in frozen PDSI and direct-weather scores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def state_records(payload: dict, family: str) -> list[dict]:
    rows = []
    for summary in payload["summaries"]:
        for comparison, content in summary.items():
            if comparison in {"crop", "practice", "eligible_development_states"}:
                continue
            for key, values in content["folds"].items():
                split, split_id = key.split(":", 1)
                if split != "development_leave_state_out":
                    continue
                improvement = float(values["rmse_improvement"])
                floor = float(values["required_floor"])
                rows.append({
                    "family": family, "crop": summary["crop"], "practice": summary["practice"],
                    "comparison": comparison, "state": split_id, "rmse_improvement": improvement,
                    "required_floor": floor,
                    "classification": "material_improvement" if improvement >= floor else ("worse" if improvement < 0 else "positive_below_threshold"),
                })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct", type=Path, required=True)
    parser.add_argument("--pdsi", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    direct, pdsi = json.loads(args.direct.read_text()), json.loads(args.pdsi.read_text())
    rows = state_records(direct, "direct_weather") + state_records(pdsi, "pdsi")
    counts = {}
    for row in rows:
        key = ":".join([row["family"], row["crop"], row["practice"], row["comparison"]])
        counts.setdefault(key, {"material_improvement": 0, "positive_below_threshold": 0, "worse": 0})[row["classification"]] += 1
    common_states = sorted(
        set(item["state"] for item in rows if item["crop"] == "cotton_upland")
        & set(item["state"] for item in rows if item["crop"] == "sorghum_grain")
    )
    cross_crop = []
    analogous = [
        ("direct_weather", "total_quantity_vs_temperature"),
        ("direct_weather", "stage_shares_vs_total_quantity"),
        ("direct_weather", "extremes_vs_total_quantity"),
        ("pdsi", "season_linear_vs_trend"),
        ("pdsi", "stage_linear_vs_season_linear"),
    ]
    for family, comparison in analogous:
        for state in common_states:
            selected = [row for row in rows if row["family"] == family and row["comparison"] == comparison and row["practice"] == "non_irrigated" and row["state"] == state]
            by_crop = {row["crop"]: row for row in selected}
            if set(by_crop) != {"cotton_upland", "sorghum_grain"}:
                raise ValueError("common-state cross-crop record is incomplete")
            cross_crop.append({
                "family": family, "comparison": comparison, "state": state,
                "cotton_classification": by_crop["cotton_upland"]["classification"],
                "sorghum_classification": by_crop["sorghum_grain"]["classification"],
                "both_material_improvement": all(by_crop[crop]["classification"] == "material_improvement" for crop in by_crop),
                "opposite_improvement_sign": by_crop["cotton_upland"]["rmse_improvement"] * by_crop["sorghum_grain"]["rmse_improvement"] < 0,
            })
    result = {
        "status": "descriptive_geographic_predictive_heterogeneity_audit",
        "inputs": {"direct_sha256": digest(args.direct), "pdsi_sha256": digest(args.pdsi)},
        "state_fold_records": rows, "classification_counts": counts,
        "common_crop_states": common_states, "nonirrigated_cross_crop_common_state_records": cross_crop,
        "common_state_both_material_count": sum(item["both_material_improvement"] for item in cross_crop),
        "common_state_opposite_sign_count": sum(item["opposite_improvement_sign"] for item in cross_crop),
        "welfare_winner_loser_interpretation_authorized": False,
        "causal_damage_or_scc_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "records": len(rows), "common_states": common_states,
        "common_state_both_material_count": result["common_state_both_material_count"],
        "common_state_opposite_sign_count": result["common_state_opposite_sign_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
