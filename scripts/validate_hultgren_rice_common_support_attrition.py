#!/usr/bin/env python3
"""Independently validate the compact rice common-support attrition audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

KEYS = ["lat", "lon_360"]
FEATURES = ["yield_t_ha", "tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def smd(retained: pd.Series, excluded: pd.Series) -> float:
    pooled = np.sqrt((retained.var(ddof=1) + excluded.var(ddof=1)) / 2.0)
    return float((retained.mean() - excluded.mean()) / pooled) if pooled > 0 else 0.0


def equal(left: Any, right: Any, path: str = "root") -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        require(set(left) == set(right), f"keys differ at {path}")
        for key in left:
            equal(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list) and isinstance(right, list):
        require(len(left) == len(right), f"length differs at {path}")
        for index, (a, b) in enumerate(zip(left, right)):
            equal(a, b, f"{path}[{index}]")
    elif isinstance(left, (float, int)) and isinstance(right, (float, int)) and not isinstance(left, bool) and not isinstance(right, bool):
        require(math.isclose(float(left), float(right), rel_tol=1e-7, abs_tol=1e-7), f"number differs at {path}")
    else:
        require(left == right, f"value differs at {path}")


def summarize(part: pd.DataFrame) -> dict[str, object]:
    crop = str(part.crop.iloc[0])
    retained = part.loc[part.weight_available]
    excluded = part.loc[~part.weight_available]
    features = [
        {
            "feature": feature,
            "retained_mean": float(retained[feature].mean()),
            "excluded_mean": float(excluded[feature].mean()),
            "retained_minus_excluded_standardized_mean_difference": smd(retained[feature], excluded[feature]),
        }
        for feature in FEATURES
    ]
    annual = [
        {
            "harvest_year": int(year),
            "positive_observed_cell_years": len(group),
            "retained_cell_years": int(group.weight_available.sum()),
            "retention_fraction": float(group.weight_available.mean()),
        }
        for year, group in part.groupby("harvest_year", sort=True)
    ]
    cells = part.drop_duplicates(KEYS)
    latitude = (
        cells.groupby(["latitude_band", "weight_available"], observed=True)
        .size().rename("cells").reset_index().sort_values(["latitude_band", "weight_available"]).to_dict("records")
    )
    country = (
        cells.groupby(["country_label_audit", "weight_available"], observed=True)
        .size().rename("cells").reset_index()
    )
    country["crop"] = crop
    excluded_country = country.loc[~country.weight_available].sort_values(["cells", "country_label_audit"], ascending=[False, True]).head(15)
    cell_retention = float(cells.weight_available.mean())
    minimum_annual = min(row["retention_fraction"] for row in annual)
    max_abs = max(abs(row["retained_minus_excluded_standardized_mean_difference"]) for row in features)
    return {
        "crop": crop,
        "positive_observed_cells": len(cells),
        "retained_cells": int(cells.weight_available.sum()),
        "excluded_cells": int((~cells.weight_available).sum()),
        "cell_retention_fraction": cell_retention,
        "positive_observed_cell_years": len(part),
        "retained_cell_years": len(retained),
        "excluded_cell_years": len(excluded),
        "cell_year_retention_fraction": float(len(retained) / len(part)),
        "minimum_annual_retention_fraction": minimum_annual,
        "maximum_absolute_standardized_mean_difference": max_abs,
        "feature_contrasts": features,
        "annual_retention": annual,
        "latitude_band_cell_counts": latitude,
        "top_excluded_country_proxy_groups": excluded_country.to_dict("records"),
        "low_attrition_gate": bool(cell_retention >= .95 and minimum_annual >= .90 and max_abs <= .25),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(digest(args.output) == receipt["output"]["sha256"], "output hash differs")
    frame = pd.read_parquet(args.output)
    require(len(frame) == receipt["output"]["rows"], "row count differs")
    require(not frame.duplicated(["crop", "harvest_year", *KEYS]).any(), "duplicate crop-cell-year")
    recomputed = [summarize(frame.loc[frame.crop.eq(crop)].copy()) for crop in ("ri1", "ri2")]
    equal(recomputed, receipt["crop_summaries"], "crop_summaries")
    all_pass = all(row["low_attrition_gate"] for row in recomputed)
    require(all_pass == receipt["all_crops_low_attrition_gate"] is False, "aggregate gate differs")
    require(receipt["claim_gates"]["imputation_used"] is False, "imputation gate differs")
    require(receipt["claim_gates"]["response_damage_or_scc_authorized"] is False, "SCC gate differs")
    result = {
        "status": "validated_full_compact_attrition_recomputation",
        "receipt_sha256": digest(args.receipt),
        "output_sha256": digest(args.output),
        "rows": len(frame),
        "all_crop_summaries_match": True,
        "numeric_comparison_tolerance": 1e-7,
        "all_crops_low_attrition_gate": all_pass,
        "imputation_used": False,
        "response_damage_or_scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
