#!/usr/bin/env python3
"""Audit the partial national county-weight checkpoint without resuming it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCHEMA = "us_national_weight_checkpoint_distribution_v1"
RECEIPT_SCHEMA = "us_national_county_nclimgrid_weight_partition_v1"
THRESHOLDS = (0.96, 0.97, 0.99, 1.0)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def audit(receipts_root: Path, geography_path: Path, checkpoint_path: Path) -> dict[str, object]:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    require(
        checkpoint.get("schema") == "us_national_all_practice_nclimgrid_weight_checkpoint_v1",
        "checkpoint schema changed",
    )
    require(
        checkpoint.get("status") == "failed_closed_on_registered_weather_valid_area_gate",
        "checkpoint no longer records the registered fail-closed state",
    )
    expected = int(checkpoint["completed_county_receipts"])
    registered = int(checkpoint["registered_counties"])
    threshold = float(
        checkpoint["failure"]["registered_minimum_weather_valid_area_relative_to_declared_land"]
    )
    require(threshold == 0.95, "registered land-coverage threshold changed")
    require(checkpoint.get("threshold_relaxed") is False, "checkpoint relaxed the threshold")

    geography = pd.read_csv(geography_path, dtype={"county_geoid": str})
    required_geography = {
        "county_geoid", "state", "crop_county_years", "feature_construction_eligible",
    }
    require(required_geography <= set(geography.columns), "geography gate columns changed")
    require(not geography.county_geoid.duplicated().any(), "geography gate duplicates a county")
    geography["county_geoid"] = geography.county_geoid.str.zfill(5)
    geography = geography.set_index("county_geoid")

    receipt_paths = sorted(receipts_root.glob("county_geoid=*/receipt.json"))
    require(len(receipt_paths) == expected, "completed receipt count differs from checkpoint")
    rows: list[dict[str, object]] = []
    identities: list[dict[str, str]] = []
    seen: set[str] = set()
    contract_sha = str(checkpoint["contract"]["sha256"])
    for receipt_path in receipt_paths:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        require(receipt.get("schema") == RECEIPT_SCHEMA, "county receipt schema changed")
        geoid = str(receipt.get("county_geoid", "")).zfill(5)
        require(geoid not in seen and geoid in geography.index, "county receipt identity is invalid")
        seen.add(geoid)
        require(receipt_path.parent.name == f"county_geoid={geoid}", "receipt directory key changed")
        weights_path = receipt_path.with_name("weights.parquet")
        require(weights_path.is_file(), f"county weights are missing for {geoid}")
        output_sha = sha256_file(weights_path)
        require(output_sha == receipt.get("output_sha256"), f"county weight hash changed for {geoid}")
        identity = receipt.get("input_identity", {})
        require(identity.get("contract_sha256") == contract_sha, "county contract identity changed")
        require(
            float(identity.get("minimum_weather_valid_area_relative_to_declared_land")) == threshold,
            "county receipt uses a different land-coverage threshold",
        )
        require(receipt.get("analysis_role") == "historical_county_validation_weight_input_only", "county analysis role changed")
        require(receipt.get("crop_pixel_exposure") is False, "county receipt claims crop-pixel exposure")
        for gate in ["relationship_estimated", "response_estimation_authorized", "scc_authorized"]:
            require(receipt.get(gate) is False, f"county receipt unexpectedly opens {gate}")
        ratio = float(receipt["weather_valid_area_relative_to_declared_land"])
        geometric = float(receipt["coverage_fraction"])
        require(np.isfinite(ratio) and ratio >= threshold, f"completed county fails threshold: {geoid}")
        require(np.isfinite(geometric) and geometric >= 0.999, f"completed county fails geometry: {geoid}")
        require(int(receipt["weight_rows"]) == int(receipt["positive_weather_cells"]) > 0, "county weight-row count changed")
        require(
            int(receipt["support_crop_county_years"]) == int(geography.loc[geoid, "crop_county_years"]),
            "county outcome support count changed",
        )
        require(bool(geography.loc[geoid, "feature_construction_eligible"]), "receipt county is geography-ineligible")
        rows.append({
            "county_geoid": geoid,
            "state": str(geography.loc[geoid, "state"]),
            "weather_valid_area_relative_to_declared_land": ratio,
            "weather_masked_intersection_area_m2": float(receipt["weather_masked_intersection_area_m2"]),
            "weight_rows": int(receipt["weight_rows"]),
            "support_crop_county_years": int(receipt["support_crop_county_years"]),
        })
        identities.append({
            "county_geoid": geoid,
            "input_fingerprint_sha256": str(receipt["input_fingerprint_sha256"]),
            "output_sha256": output_sha,
            "receipt_sha256": sha256_file(receipt_path),
        })

    frame = pd.DataFrame(rows).sort_values("county_geoid").reset_index(drop=True)
    ratios = frame.weather_valid_area_relative_to_declared_land.to_numpy(dtype=float)
    minimum_index = int(np.argmin(ratios))
    state_counts = frame.groupby("state").size().sort_index()
    require(len(frame) == expected and len(seen) == expected, "completed receipt keys are incomplete")
    require(frame.county_geoid.is_monotonic_increasing, "completed receipt summary is not ordered")

    return {
        "schema": SCHEMA,
        "status": "validated_partial_checkpoint_distribution_only",
        "completed_county_receipts": expected,
        "registered_counties": registered,
        "completed_fraction_of_registered_counties": expected / registered,
        "registered_minimum_weather_valid_area_relative_to_declared_land": threshold,
        "minimum_completed_ratio": float(ratios[minimum_index]),
        "minimum_completed_ratio_county_geoid": str(frame.iloc[minimum_index].county_geoid),
        "ratio_quantiles": {
            key: float(np.quantile(ratios, quantile))
            for key, quantile in [("p01", 0.01), ("p05", 0.05), ("p50", 0.5), ("p95", 0.95), ("p99", 0.99)]
        },
        "completed_count_below_ratio_threshold": {
            str(value): int(np.sum(ratios < value)) for value in THRESHOLDS
        },
        "completed_count_with_positive_masked_area": int(
            np.sum(frame.weather_masked_intersection_area_m2.to_numpy(dtype=float) > 0)
        ),
        "states_with_completed_receipts": int(len(state_counts)),
        "completed_receipts_by_state": {state: int(count) for state, count in state_counts.items()},
        "minimum_completed_geoid": str(frame.county_geoid.min()),
        "maximum_completed_geoid": str(frame.county_geoid.max()),
        "total_weight_rows": int(frame.weight_rows.sum()),
        "total_supported_crop_county_years": int(frame.support_crop_county_years.sum()),
        "receipt_set_sha256": canonical_sha256(sorted(identities, key=lambda row: row["county_geoid"])),
        "checkpoint": {"path": display_path(checkpoint_path), "sha256": sha256_file(checkpoint_path)},
        "geography_gate": {"path": display_path(geography_path), "sha256": sha256_file(geography_path)},
        "implementation": {
            "path": display_path(Path(__file__)),
            "sha256": sha256_file(Path(__file__)),
        },
        "partial_scope_warning": (
            "The completed receipts are a fail-closed partial checkpoint shaped by FIPS-ordered "
            "execution plus earlier bounded smokes; they are not a nationally representative sample "
            "or an authorized national feature panel."
        ),
        "threshold_relaxed": False,
        "failed_county_excluded": False,
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts-root", type=Path, required=True)
    parser.add_argument("--geography", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.receipts_root.resolve(), args.geography.resolve(), args.checkpoint.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(
        f"validated {result['completed_county_receipts']} completed county receipts; "
        f"minimum land-relative ratio={result['minimum_completed_ratio']:.9f}"
    )


if __name__ == "__main__":
    main()
