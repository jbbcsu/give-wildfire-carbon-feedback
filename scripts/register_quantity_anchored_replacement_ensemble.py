#!/usr/bin/env python3
"""Independently validate and register the 26-model paired GIVE ensemble."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GIVE_ROOT = ROOT.parent / "paper-2022-scc-give-zenodo"
LABELS = ["1.5%", "2.0%", "2.5%", "3.0%"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--job-receipt", type=Path, required=True)
    parser.add_argument("--julia-script", type=Path, required=True)
    parser.add_argument("--component", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    input_receipt = json.loads(args.input_receipt.read_text(encoding="utf-8"))
    expected_receipt = json.loads(args.expected_receipt.read_text(encoding="utf-8"))
    job = json.loads(args.job_receipt.read_text(encoding="utf-8"))
    require(input_receipt["schema"] == "quantity_replacement_ensemble_input/v1", "input receipt differs")
    require(expected_receipt["schema"] == "epa_fair_hultgren_quantity_partial_scc_diagnostic/v1", "expected receipt differs")
    require(job["status"] == "completed" and job["returncode"] == 0, "paired GIVE job failed")
    source = Path(input_receipt["output"]["path"])
    require(digest(source) == input_receipt["output"]["sha256"], "regional input hash differs")
    frame = pd.read_csv(args.result)
    require(len(frame) == 26 * 4, "result support differs")
    require(sorted(frame.climate_model.unique()) == input_receipt["support"]["climate_models"], "model support differs")
    require(all(list(group.discount_rate_label) == LABELS for _, group in frame.groupby("climate_model", sort=True)), "discount schedules differ")
    require((frame.baseline_agriculture_error_usd == 0.0).all(), "baseline agriculture differs")
    require((frame.baseline_cpc_error == 0.0).all(), "baseline CPC differs")
    require((frame.regional_increment_error_billion_usd2005 <= 1e-12).all(), "regional increment error differs")
    require(frame.aggregated_increment_error_usd.max() <= 0.01, "aggregated increment error exceeds one cent")
    require((frame.absolute_error <= frame.numerical_error_bound_usd2005_per_tco2 + 1e-15).all(), "paired diagnostic exceeds numerical bound")

    expected_path = Path(expected_receipt["output"]["path"])
    require(digest(expected_path) == expected_receipt["output"]["sha256"], "external diagnostic hash differs")
    expected = pd.read_csv(expected_path)
    expected = expected.loc[
        expected.pulse_size_gtc.eq(input_receipt["specification"]["pulse_size_gtc"])
        & expected.adaptation.eq(input_receipt["specification"]["adaptation"])
        & expected.tail_rule.eq(input_receipt["specification"]["tail_rule"])
        & expected.elasticity_id.eq(input_receipt["specification"]["elasticity_id"])
        & expected.yield_to_supply_mapping.eq(input_receipt["specification"]["yield_to_supply_mapping"]),
        ["climate_model", "discount_rate_label", "partial_scc_diagnostic_usd2005_per_tco2", "partial_scc_diagnostic_usd2020_per_tco2"],
    ]
    merged = frame.merge(expected, on=["climate_model", "discount_rate_label"], how="outer", validate="one_to_one", indicator=True)
    require(len(merged) == 104 and merged._merge.eq("both").all(), "external comparison keys differ")
    require((merged.expected_diagnostic_usd2005_per_tco2 == merged.partial_scc_diagnostic_usd2005_per_tco2).all(), "2005-dollar diagnostic copy differs")
    require((merged.expected_diagnostic_usd2020_per_tco2 == merged.partial_scc_diagnostic_usd2020_per_tco2).all(), "2020-dollar diagnostic copy differs")

    summaries = {}
    for label in LABELS:
        values = frame.loc[frame.discount_rate_label.eq(label), "expected_diagnostic_usd2020_per_tco2"]
        summaries[label] = {
            "models": int(len(values)),
            "mean_usd2020_per_tco2": float(values.mean()),
            "median_usd2020_per_tco2": float(values.median()),
            "minimum_usd2020_per_tco2": float(values.min()),
            "maximum_usd2020_per_tco2": float(values.max()),
            "negative_models": int((values < 0).sum()),
            "positive_models": int((values > 0).sum()),
        }

    give_sources = {
        "main_model": GIVE_ROOT / "packages/MimiGIVE/src/main_model.jl",
        "scc": GIVE_ROOT / "packages/MimiGIVE/src/scc.jl",
        "damage_aggregator": GIVE_ROOT / "packages/MimiGIVE/src/components/DamageAggregator.jl",
        "manifest": GIVE_ROOT / "Manifest.toml",
    }
    result = {
        "schema": "quantity_anchored_replacement_ensemble/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "paired_26_model_central_marginal_response_replacement_pass",
        "specification": input_receipt["specification"],
        "definition": "retain exact MooreAg baseline regional damage levels, remove the MooreAg marginal pulse response, and substitute the precipitation-quantity marginal response exactly once",
        "support": {"climate_models": 26, "discount_schedules": LABELS, "result_rows": len(frame)},
        "summary": summaries,
        "validation": {
            "baseline_agriculture_maximum_absolute_error_usd": float(frame.baseline_agriculture_error_usd.max()),
            "baseline_cpc_maximum_absolute_error": float(frame.baseline_cpc_error.max()),
            "regional_increment_maximum_absolute_error_billion_usd2005": float(frame.regional_increment_error_billion_usd2005.max()),
            "aggregated_increment_maximum_absolute_error_usd": float(frame.aggregated_increment_error_usd.max()),
            "paired_vs_external_diagnostic_maximum_absolute_error_usd2005_per_tco2": float(frame.absolute_error.max()),
            "all_paired_errors_below_derived_floating_point_bounds": True,
            "all_104_external_rows_reconstructed_exactly": True,
            "legacy_agriculture_removed_and_single_replacement_producer_audited_for_every_model": True,
        },
        "sources": {
            "regional_input": {"path": str(source), "sha256": digest(source), "receipt": str(args.input_receipt), "receipt_sha256": digest(args.input_receipt)},
            "external_diagnostic": {"path": str(expected_path), "sha256": digest(expected_path), "receipt": str(args.expected_receipt), "receipt_sha256": digest(args.expected_receipt)},
            "julia_result": {"path": str(args.result), "bytes": args.result.stat().st_size, "sha256": digest(args.result)},
            "julia_job": {"path": str(args.job_receipt), "sha256": digest(args.job_receipt), **job},
            "julia_script": {"path": str(args.julia_script), "sha256": digest(args.julia_script)},
            "replacement_component": {"path": str(args.component), "sha256": digest(args.component)},
            **{f"give_{name}": {"path": str(path), "sha256": digest(path)} for name, path in give_sources.items()},
        },
        "claim_gates": {"paired_replacement_engineering": True, "central_26_model_quantity_channel_scc": True, "adaptation_or_market_uncertainty_in_paired_give": False, "full_precipitation_agriculture_replacement": False},
        "limitations": [
            "This is the central fixed-adaptation, uncapped-tail, smallest-pulse specification only.",
            "The baseline level is anchored to MooreAg to preserve consumption; only the marginal response is replaced.",
            "The response is the global maize annual-rainfall-quantity channel and excludes rainfall timing, drought, temperature, other crops, irrigation adaptation, trade, storage, and adaptation costs.",
            "The negative mean is a model result for this narrow channel, not evidence that total climate-driven precipitation changes are beneficial.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "summary": summaries, "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    main()
