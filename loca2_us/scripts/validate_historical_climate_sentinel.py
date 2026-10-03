#!/usr/bin/env python3
"""Independently validate the saved LOCA2 historical climate sentinel."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


QUANTILES = np.array([0.1, 0.25, 0.5, 0.75, 0.9])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    root = Path(__file__).resolve().parents[2]
    receipt_path = args.receipt if args.receipt.is_absolute() else root / args.receipt
    receipt = json.loads(receipt_path.read_text())
    require(receipt["status"] == "pass", "sentinel receipt failed")
    config_path = root / receipt["config"]["path"]
    require(digest(config_path) == receipt["config"]["sha256"], "sentinel config changed")
    config = tomllib.loads(config_path.read_text())
    model_path = root / receipt["output"]["path"]
    require(digest(model_path) == receipt["output"]["sha256"], "modeled feature output changed")
    modeled = pd.read_parquet(model_path).sort_values("harvest_year").reset_index(drop=True)
    require(modeled.harvest_year.tolist() == receipt["support"]["years"], "modeled years differ")

    features = sorted(receipt["comparisons"])
    observed_rows = []
    columns = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice", *features]
    for year in receipt["support"]["years"]:
        path = root / config["inputs"]["nclimgrid_feature_pattern"].format(year=year)
        frame = pd.read_parquet(path, columns=columns)
        selected = frame.loc[
            frame.county_geoid.astype(str).str.zfill(5).eq(receipt["support"]["county_geoid"])
            & frame.outcome_crop.eq(receipt["support"]["crop"])
        ]
        require(len(selected) >= 1, f"observed sentinel missing in {year}")
        for feature in features:
            require(selected[feature].nunique(dropna=False) == 1, f"observed practices differ on {feature}/{year}")
        observed_rows.append({"harvest_year": year, **{feature: float(selected.iloc[0][feature]) for feature in features}})
    observed = pd.DataFrame(observed_rows)

    checks = 0
    maximum_absolute_difference = 0.0
    for frame, label in ((modeled, "modeled"), (observed, "observed")):
        require(np.allclose(frame[["stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm"]].sum(axis=1), frame.precip_mm, rtol=0, atol=1e-8), f"{label} stage rainfall does not reconcile")
        require(np.allclose(frame[["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]].sum(axis=1), 1.0, rtol=0, atol=1e-10), f"{label} shares do not sum to one")
        checks += 2 * len(frame)

    for feature in features:
        model_values = modeled[feature].to_numpy(dtype=float)
        observed_values = observed[feature].to_numpy(dtype=float)
        mq = np.quantile(model_values, QUANTILES)
        oq = np.quantile(observed_values, QUANTILES)
        recomputed = {
            "model_mean": float(model_values.mean()),
            "observed_mean": float(observed_values.mean()),
            "climatology_bias_model_minus_observed": float(model_values.mean() - observed_values.mean()),
            "model_standard_deviation": float(model_values.std(ddof=1)),
            "observed_standard_deviation": float(observed_values.std(ddof=1)),
            "standard_deviation_ratio": float(model_values.std(ddof=1) / observed_values.std(ddof=1)),
            "quantile_rmse": float(np.sqrt(np.mean(np.square(mq - oq)))),
        }
        for key, value in recomputed.items():
            saved = receipt["comparisons"][feature][key]
            difference = abs(value - saved)
            maximum_absolute_difference = max(maximum_absolute_difference, difference)
            require(np.isclose(value, saved, rtol=0, atol=1e-12), f"saved comparison differs: {feature}/{key}")
            checks += 1
        for key, values in (("model_quantiles", mq), ("observed_quantiles", oq), ("quantile_differences_model_minus_observed", mq - oq)):
            saved = np.asarray(receipt["comparisons"][feature][key], dtype=float)
            maximum_absolute_difference = max(maximum_absolute_difference, float(np.max(np.abs(values - saved))))
            require(np.allclose(values, saved, rtol=0, atol=1e-12), f"saved quantiles differ: {feature}/{key}")
            checks += len(values)

    result = {
        "schema": "loca2_us_historical_climate_sentinel_validation/v1",
        "status": "pass",
        "checks": checks,
        "maximum_absolute_saved_precision_difference": maximum_absolute_difference,
        "support": receipt["support"],
        "source_receipt": {"path": str(receipt_path.relative_to(root)), "sha256": digest(receipt_path)},
        "claim_gates": receipt["claim_gates"],
    }
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "checks": checks, "maximum_difference": maximum_absolute_difference}, indent=2))


if __name__ == "__main__":
    main()
