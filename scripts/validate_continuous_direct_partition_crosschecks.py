#!/usr/bin/env python3
"""Compare a new direct-weather partition with independent legacy overlaps.

Legacy middle-period artifacts are used only as validation references. They
are never copied or spliced into the isolated continuous-panel namespace.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_continuous_global_panel_partitions import (
    FALSE_GATES,
    _resolve,
    generate_tasks,
    load_config,
    validate_task,
)
from scpdsi_partition_provenance import sha256_file


KEY = ["harvest_year", "lat", "lon", "crop", "irrigation"]
STAGE_METRICS = [
    "tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm",
    "rx5day_mm", "stage_days",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--absolute-tolerance", type=float, default=1e-10)
    args = parser.parse_args()
    if not np.isfinite(args.absolute_tolerance) or args.absolute_tolerance < 0:
        raise ValueError("Absolute tolerance must be finite and nonnegative")

    config_path = Path(args.config)
    config = load_config(config_path)
    new_path = Path(args.new)
    matching_tasks = [
        task
        for task in generate_tasks(config_path, config)
        if Path(task.output).resolve() == new_path.resolve()
    ]
    if len(matching_tasks) != 1 or matching_tasks[0].family not in {
        "direct_season", "direct_stage"
    }:
        raise ValueError("New cross-check target is not a registered direct-weather task")
    task = matching_tasks[0]
    source_valid, source_detail = validate_task(
        task, config_path, config
    )
    if not source_valid:
        raise ValueError(
            f"New cross-check partition lacks a valid source-bound receipt: {source_detail}"
        )
    new = pd.read_parquet(new_path)
    if new.empty:
        raise ValueError("Cross-check requires a nonempty new partition")
    if set(new["crop"].astype(str)) != {new_crop := str(new["crop"].iloc[0])}:
        raise ValueError("New partition contains multiple crops")
    if set(new["irrigation"].astype(str)) != {
        new_irrigation := str(new["irrigation"].iloc[0])
    }:
        raise ValueError("New partition contains multiple irrigation regimes")
    if sorted(new["harvest_year"].astype(int).unique()) != list(
        range(config["construction_year_start"], config["construction_year_end"] + 1)
    ):
        raise ValueError("New partition does not cover the exact construction years")
    duplicate_key = KEY if task.family == "direct_season" else KEY + ["stage_id"]
    if new.duplicated(duplicate_key).any():
        raise ValueError("New partition has duplicate crop-year grid keys")

    comparisons: list[dict[str, object]] = []
    new_latitudes = set(float(value) for value in new["lat"].unique())
    for item in config["existing_middle_crosschecks"]:
        if (item["crop"], item["irrigation"]) != (new_crop, new_irrigation):
            continue
        legacy_field = (
            "season_panel" if task.family == "direct_season" else "stage_panel"
        )
        legacy_path = _resolve(config_path, item[legacy_field])
        legacy = pd.read_parquet(legacy_path)
        legacy = legacy[
            legacy["harvest_year"].between(item["year_start"], item["year_end"])
            & legacy["lat"].astype(float).isin(new_latitudes)
        ]
        current = new[
            new["harvest_year"].between(item["year_start"], item["year_end"])
        ]
        if task.family == "direct_season":
            if list(current.columns) != list(legacy.columns):
                raise ValueError(
                    f"Column contract differs from legacy cross-check {legacy_path}"
                )
        else:
            stage_columns = [
                f"stage{stage}_{metric}"
                for metric in STAGE_METRICS
                for stage in range(1, int(config["expected_stages"]) + 1)
            ]
            missing_legacy = set(KEY + stage_columns) - set(legacy.columns)
            if missing_legacy:
                raise ValueError(
                    f"Legacy stage cross-check lacks {sorted(missing_legacy)}: {legacy_path}"
                )
            current = current.pivot(
                index=KEY, columns="stage_id", values=STAGE_METRICS
            )
            current.columns = [
                f"stage{int(stage)}_{metric}" for metric, stage in current.columns
            ]
            current = current.reset_index()[KEY + stage_columns]
            legacy = legacy[KEY + stage_columns]
        current = current.sort_values(KEY).reset_index(drop=True)
        legacy = legacy.sort_values(KEY).reset_index(drop=True)
        if len(current) != len(legacy) or not current[KEY].equals(legacy[KEY]):
            raise ValueError(f"Key coverage differs from legacy cross-check {legacy_path}")
        maximum = 0.0
        for column in current.columns:
            if pd.api.types.is_bool_dtype(current[column]):
                if not np.array_equal(
                    current[column].to_numpy(), legacy[column].to_numpy()
                ):
                    raise ValueError(f"Boolean values differ for {column} in {legacy_path}")
            elif pd.api.types.is_numeric_dtype(current[column]):
                left = current[column].to_numpy()
                right = legacy[column].to_numpy()
                if not np.allclose(
                    left,
                    right,
                    rtol=0,
                    atol=args.absolute_tolerance,
                    equal_nan=True,
                ):
                    raise ValueError(
                        f"Numeric values differ for {column} in {legacy_path}"
                    )
                finite = np.isfinite(left) & np.isfinite(right)
                if finite.any():
                    maximum = max(
                        maximum, float(np.max(np.abs(left[finite] - right[finite])))
                    )
            elif not current[column].equals(legacy[column]):
                raise ValueError(f"Values differ for {column} in {legacy_path}")
        comparisons.append(
            {
                "years": [item["year_start"], item["year_end"]],
                "legacy_path": str(legacy_path.resolve()),
                "legacy_sha256": sha256_file(legacy_path),
                "rows": len(current),
                "key_match": True,
                "maximum_absolute_difference": maximum,
            }
        )
    if not comparisons:
        raise ValueError("No registered legacy overlap applies to this partition")

    result = {
        "schema_version": 1,
        "status": "passed_exact_or_numerically_identical",
        "config_file": str(config_path.resolve()),
        "config_sha256": sha256_file(config_path),
        "new_path": str(new_path.resolve()),
        "new_sha256": sha256_file(new_path),
        "family": task.family,
        "new_partition_rows": len(new),
        "absolute_tolerance": args.absolute_tolerance,
        "source_bound_partition_receipt_validated": True,
        "comparisons": comparisons,
        "role": "crosscheck_only_no_legacy_artifact_spliced",
        "causal_or_damage_inference_supported": False,
        **{gate: False for gate in FALSE_GATES},
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
