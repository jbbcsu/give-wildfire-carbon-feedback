#!/usr/bin/env python3
"""Validate the descriptive sorghum/cotton geographic heterogeneity audit."""
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


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--direct", type=Path, required=True)
    parser.add_argument("--pdsi", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    require(audit["inputs"] == {"direct_sha256": digest(args.direct), "pdsi_sha256": digest(args.pdsi)}, "input hashes differ")
    rows = audit["state_fold_records"]
    require(len(rows) == 168, "state-fold record count differs")
    for row in rows:
        improvement, floor = float(row["rmse_improvement"]), float(row["required_floor"])
        expected = "material_improvement" if improvement >= floor else ("worse" if improvement < 0 else "positive_below_threshold")
        require(row["classification"] == expected, "classification differs")
    require(audit["common_crop_states"] == ["NM", "OK", "TX"], "common states differ")
    cross = audit["nonirrigated_cross_crop_common_state_records"]
    require(len(cross) == 15, "cross-crop record count differs")
    both, opposite = 0, 0
    for item in cross:
        expected_both = item["cotton_classification"] == item["sorghum_classification"] == "material_improvement"
        require(item["both_material_improvement"] == expected_both, "both-material flag differs")
        both += expected_both
        cotton = next(row for row in rows if row["family"] == item["family"] and row["comparison"] == item["comparison"] and row["practice"] == "non_irrigated" and row["crop"] == "cotton_upland" and row["state"] == item["state"])
        sorghum = next(row for row in rows if row["family"] == item["family"] and row["comparison"] == item["comparison"] and row["practice"] == "non_irrigated" and row["crop"] == "sorghum_grain" and row["state"] == item["state"])
        expected_opposite = float(cotton["rmse_improvement"]) * float(sorghum["rmse_improvement"]) < 0
        require(item["opposite_improvement_sign"] == expected_opposite, "opposite-sign flag differs")
        opposite += expected_opposite
    require((both, opposite) == (audit["common_state_both_material_count"], audit["common_state_opposite_sign_count"]), "cross-crop totals differ")
    require(not audit["welfare_winner_loser_interpretation_authorized"] and not audit["causal_damage_or_scc_authorized"], "claim gate opened")
    result = {
        "status": "validated_descriptive_geographic_heterogeneity_audit",
        "audit_sha256": digest(args.audit), "state_fold_records": len(rows),
        "cross_crop_common_state_records": len(cross), "both_material_count": both,
        "opposite_improvement_sign_count": opposite,
        "welfare_winner_loser_interpretation_authorized": False,
        "causal_damage_or_scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
