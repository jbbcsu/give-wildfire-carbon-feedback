#!/usr/bin/env python3
"""Validate matched core-GIVE FAIR baseline/pulse temperature paths."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


CONFIG_SCHEMA = "give_fair_temperature_path_smoke_config_v1"
CONFIG_ROLE = "matched_core_fair_temperature_path_numerical_gate_not_feature_response_damage_or_scc"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(config_path: Path, paths_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("FAIR temperature-path contract identity changed")
    if config.get("limitations", {}).get("damage_or_scc_authorized") is not False:
        raise ValueError("FAIR temperature-path smoke unexpectedly opens damage/SCC use")
    root = config_path.parent.parent
    core_root = (root / str(config["core_root"])).resolve()
    for receipt in config.get("source_receipts", []):
        source = (core_root / str(receipt["path"])).resolve()
        source.relative_to(core_root)
        if not source.is_file() or sha256(source) != str(receipt["sha256"]):
            raise ValueError(f"core source receipt changed: {receipt['path']}")

    frame = pd.read_csv(paths_path)
    required = {
        "year", "pulse_size_gtc", "baseline_temperature_c",
        "pulse_temperature_c", "difference_k",
    }
    if set(frame.columns) != required or frame.empty:
        raise ValueError("FAIR temperature-path schema changed")
    numeric = frame[list(required)].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("FAIR temperature paths contain nonfinite values")
    years = set(range(int(config["model_start_year"]), int(config["model_end_year"]) + 1))
    scales = [float(value) for value in config["pulse_sizes_gtc"]]
    if set(frame["year"].astype(int)) != years or set(frame["pulse_size_gtc"].astype(float)) != set(scales):
        raise ValueError("FAIR year or pulse-size product changed")
    if frame.duplicated(["year", "pulse_size_gtc"]).any() or len(frame) != len(years) * len(scales):
        raise ValueError("FAIR year/pulse product is incomplete or duplicated")
    baseline_wide = frame.pivot(index="year", columns="pulse_size_gtc", values="baseline_temperature_c")
    if not np.allclose(baseline_wide.to_numpy(), baseline_wide.iloc[:, [0]].to_numpy(), rtol=0, atol=0):
        raise ValueError("FAIR baseline path differs across paired runs")
    if not np.allclose(
        frame["difference_k"],
        frame["pulse_temperature_c"] - frame["baseline_temperature_c"],
        rtol=0,
        atol=1e-15,
    ):
        raise ValueError("FAIR temperature differences do not reconcile")
    zero = frame["pulse_size_gtc"] == 0
    if not np.allclose(frame.loc[zero, "difference_k"], 0, rtol=0, atol=0):
        raise ValueError("zero-pulse FAIR path is not identical")
    pre = frame["year"] <= int(config["pulse_year"])
    if not np.allclose(frame.loc[pre, "difference_k"], 0, rtol=0, atol=0):
        raise ValueError("FAIR paths diverge before the pulse can affect temperature")

    positive = sorted((value for value in scales if value > 0), reverse=True)
    if len(positive) < 3:
        raise ValueError("FAIR convergence gate requires three positive pulse sizes")
    wide = frame.loc[frame["pulse_size_gtc"] > 0].pivot(
        index="year", columns="pulse_size_gtc", values="difference_k"
    )
    normalized = pd.DataFrame({scale: wide[scale] / scale for scale in positive})
    smallest, next_smallest = positive[-1], positive[-2]
    difference = np.abs(normalized[smallest] - normalized[next_smallest])
    scale = np.maximum.reduce([
        np.abs(normalized[smallest].to_numpy()),
        np.abs(normalized[next_smallest].to_numpy()),
        np.full(len(normalized), 1e-15),
    ])
    tolerance = 1e-12 + float(config["convergence_rtol"]) * scale
    if (difference.to_numpy() > tolerance).any():
        raise ValueError("smallest FAIR pulse-size temperature signals do not converge")
    positive_rows = frame.loc[frame["pulse_size_gtc"] > 0]
    first_nonzero = positive_rows.loc[np.abs(positive_rows["difference_k"]) > 0, "year"]
    if first_nonzero.empty:
        raise ValueError("positive FAIR pulses never affect temperature")
    maxima = (
        positive_rows.groupby("pulse_size_gtc")["difference_k"]
        .apply(lambda values: float(np.max(np.abs(values))))
        .sort_index()
        .to_dict()
    )
    return {
        "result": "passed",
        "rows": int(len(frame)),
        "years": [min(years), max(years)],
        "pulse_year": int(config["pulse_year"]),
        "first_nonzero_temperature_year": int(first_nonzero.min()),
        "pulse_sizes_gtc": scales,
        "maximum_absolute_temperature_difference_k": {str(k): v for k, v in maxima.items()},
        "zero_pulse_identity": True,
        "pre_pulse_identity": True,
        "baseline_path_identity_across_scales": True,
        "decreasing_pulse_convergence": True,
        "maximum_smallest_scale_normalized_disagreement": float(difference.max()),
        "paths_sha256": sha256(paths_path),
        "config_sha256": sha256(config_path),
        "fair_feature_path_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--paths", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    audit = validate(args.config.resolve(), args.paths.resolve())
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
