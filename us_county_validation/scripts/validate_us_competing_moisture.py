#!/usr/bin/env python3
"""Recompute and validate a U.S. competing-moisture diagnostic result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from build_us_competing_moisture_inputs import (
    DEFAULT_PROTOCOL,
    KEYS,
    build_inputs,
    load_protocol,
    read_table,
    sha256,
)
from evaluate_us_competing_moisture import evaluate, load_validated_inputs


def walk_keys(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, child
            yield from walk_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_keys(child, f"{prefix}[{index}]")


def validate_candidate(
    input_dir: Path,
    input_audit: Path,
    direct_weather: Path,
    direct_validation: Path,
    pdsi_join: Path,
    pdsi_validation: Path,
    calendar: Path,
    calendar_validation: Path,
    candidate_path: Path,
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    expected = evaluate(
        input_dir,
        input_audit,
        direct_weather,
        direct_validation,
        pdsi_join,
        pdsi_validation,
        calendar,
        calendar_validation,
        protocol_path,
    )
    if candidate != expected:
        raise ValueError("candidate result differs from full deterministic recomputation")
    protocol = load_protocol(protocol_path)
    rebuilt_all = build_inputs(
        read_table(direct_weather), read_table(pdsi_join), read_table(calendar), protocol
    )
    rebuilt = rebuilt_all[:3]
    rebuilt_audit = rebuilt_all[3]
    stored = load_validated_inputs(
        input_dir,
        input_audit,
        protocol,
        protocol_path,
        direct_weather,
        direct_validation,
        pdsi_join,
        pdsi_validation,
        calendar,
        calendar_validation,
    )[:3]
    for label, rebuilt_frame, stored_frame in zip(
        ["common", "direct_weather", "pdsi"], rebuilt, stored, strict=True
    ):
        pd.testing.assert_frame_equal(
            rebuilt_frame.sort_values(KEYS).reset_index(drop=True),
            stored_frame.sort_values(KEYS).reset_index(drop=True),
            check_dtype=True,
            check_exact=True,
            obj=f"rebuilt {label} diagnostic input",
        )
    stored_audit = json.loads(input_audit.read_text(encoding="utf-8"))
    stored_semantic_audit = {
        key: value for key, value in stored_audit.items() if key not in {"inputs", "outputs"}
    }
    if stored_semantic_audit != rebuilt_audit:
        raise ValueError("input audit semantic fields differ from raw-source rebuild")
    if candidate.get("status") != "aggregate_noncausal_predictive_diagnostic_complete":
        raise ValueError("candidate status changed")
    if candidate.get("coefficients_in_output") is not False:
        raise ValueError("candidate exposes coefficients")
    if candidate.get("row_predictions_in_output") is not False:
        raise ValueError("candidate exposes row predictions")
    if candidate.get("causal_effect_estimated") is not False:
        raise ValueError("candidate claims a causal effect")
    if candidate.get("damage_calculated") is not False or candidate.get("scc_calculated") is not False:
        raise ValueError("candidate claims damages or SCC")
    for path, value in walk_keys(candidate):
        leaf = path.rsplit(".", 1)[-1].lower()
        if ("coefficient" in leaf and leaf != "coefficients_in_output") or (
            "prediction" in leaf and leaf != "row_predictions_in_output"
        ):
            raise ValueError(f"candidate contains forbidden row/coefficient field {path}")
        if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
            raise ValueError(f"candidate contains a nonfinite value at {path}")
    return {
        "status": "validated_exact_recomputation_aggregate_predictive_diagnostic",
        "protocol_id": candidate["protocol_id"],
        "candidate": {"path": str(candidate_path), "sha256": sha256(candidate_path)},
        "input_audit": {"path": str(input_audit), "sha256": sha256(input_audit)},
        "protocol": {"path": str(protocol_path), "sha256": sha256(protocol_path)},
        "raw_sources": {
            "direct_weather": {"path": str(direct_weather), "sha256": sha256(direct_weather)},
            "pdsi_join": {"path": str(pdsi_join), "sha256": sha256(pdsi_join)},
            "calendar": {"path": str(calendar), "sha256": sha256(calendar)},
        },
        "source_validation_receipts": {
            "direct_weather": {
                "path": str(direct_validation), "sha256": sha256(direct_validation)
            },
            "pdsi": {"path": str(pdsi_validation), "sha256": sha256(pdsi_validation)},
            "calendar": {
                "path": str(calendar_validation), "sha256": sha256(calendar_validation)
            },
        },
        "raw_source_tables_rebuilt_into_diagnostic_inputs": True,
        "upstream_daily_weather_monthly_pdsi_or_calendar_pdf_recomputed": False,
        "first_difference_level_endpoint_purge_recomputed": True,
        "distribution_material_promotion_floor_recomputed": True,
        "metric_rows_recomputed": len(candidate["metrics"]),
        "coefficients_in_output": False,
        "row_predictions_in_output": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--input-audit", required=True)
    parser.add_argument("--direct-weather", required=True)
    parser.add_argument("--direct-validation", required=True)
    parser.add_argument("--pdsi-join", required=True)
    parser.add_argument("--pdsi-validation", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--calendar-validation", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = validate_candidate(
        Path(args.input_dir),
        Path(args.input_audit),
        Path(args.direct_weather),
        Path(args.direct_validation),
        Path(args.pdsi_join),
        Path(args.pdsi_validation),
        Path(args.calendar),
        Path(args.calendar_validation),
        Path(args.candidate),
        Path(args.protocol),
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"validated {receipt['metric_rows_recomputed']} aggregate metrics by exact recomputation; "
        "no causal/damage/SCC claim"
    )


if __name__ == "__main__":
    main()
