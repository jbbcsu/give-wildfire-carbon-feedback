#!/usr/bin/env python3
"""Validate the compact MIRCA rice proportional-reconciliation candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(receipt["status"] == "validated_candidate_sensitivity_not_production_eligible", "status differs")
    require(digest(args.output) == receipt["output"]["sha256"], "candidate hash differs")
    frame = pd.read_parquet(args.output)
    require(len(frame) == receipt["output"]["rows"], "row count differs")
    require(not frame.duplicated(["crop", "lat", "lon_360"]).any(), "duplicate crop-cell rows")
    require(set(frame.crop) == {"ri1", "ri2"}, "unexpected crop")
    numeric = frame[["irrigated_area_ha", "rainfed_area_ha", "total_area_ha", "irrigated_share"]]
    require(np.isfinite(numeric.to_numpy()).all(), "nonfinite candidate values")
    require((numeric.to_numpy() >= 0).all(), "negative candidate values")
    total_error = float(np.max(np.abs(frame.total_area_ha - frame.irrigated_area_ha - frame.rainfed_area_ha)))
    share_error = float(np.max(np.abs(frame.irrigated_share - frame.irrigated_area_ha / frame.total_area_ha)))
    require(total_error <= 1e-9 and share_error <= 1e-12, "candidate area/share algebra differs")
    require(frame.proportional_reconciliation_sensitivity.eq(True).all(), "sensitivity flag differs")
    require(frame.production_eligible.eq(False).all(), "production gate opened")
    require(frame.scc_authorized.eq(False).all(), "SCC gate opened")

    by_crop = frame.groupby("crop", observed=True)[["irrigated_area_ha", "rainfed_area_ha"]].sum()
    maximum_season_total_error = 0.0
    for system, column in (("ir", "irrigated_area_ha"), ("rf", "rainfed_area_ha")):
        audit = next(row for row in receipt["system_audits"] if row["system"] == system)
        require(audit["annual_positive_seasonal_zero_cells"] == 0, "unsupported annual cells present")
        require(audit["seasonal_positive_annual_zero_cells"] == 0, "unsupported seasonal cells present")
        require(audit["postrepair_maximum_absolute_cell_error_ha"] <= 1e-9, "repair does not reconcile")
        for season, crop in ((1, "ri1"), (2, "ri2")):
            expected = next(row["repaired_area_ha"] for row in audit["season_areas"] if row["season"] == season)
            maximum_season_total_error = max(maximum_season_total_error, abs(float(by_crop.loc[crop, column]) - expected))
    require(maximum_season_total_error <= 1e-7, "candidate season totals differ from receipt")

    validation = {
        "status": "validated_compact_candidate_and_closed_claim_gates",
        "receipt_sha256": digest(args.receipt),
        "output_sha256": digest(args.output),
        "rows": len(frame),
        "maximum_area_identity_error_ha": total_error,
        "maximum_share_identity_error": share_error,
        "maximum_season_total_error_ha": maximum_season_total_error,
        "support_complete": True,
        "postrepair_reconciliation_exact": True,
        "production_weights_authorized": False,
        "response_damage_or_scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
