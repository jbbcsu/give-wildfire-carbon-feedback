#!/usr/bin/env python3
"""Register and audit the paired anchored-replacement GIVE sentinel."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GIVE_ROOT = ROOT.parent / "paper-2022-scc-give-zenodo"


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
    parser.add_argument("--sentinel-receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--job-receipt", type=Path, required=True)
    parser.add_argument("--julia-script", type=Path, required=True)
    parser.add_argument("--component", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    sentinel = json.loads(args.sentinel_receipt.read_text(encoding="utf-8"))
    expected = json.loads(args.expected_receipt.read_text(encoding="utf-8"))
    job = json.loads(args.job_receipt.read_text(encoding="utf-8"))
    require(sentinel["schema"] == "quantity_replacement_sentinel/v1", "sentinel receipt differs")
    require(expected["schema"] == "epa_fair_hultgren_quantity_partial_scc_diagnostic/v1", "expected receipt differs")
    require(job["status"] == "completed" and job["returncode"] == 0, "paired GIVE job failed")
    source = Path(sentinel["output"]["path"])
    require(digest(source) == sentinel["output"]["sha256"], "regional increment hash differs")
    frame = pd.read_csv(args.result)
    require(list(frame.discount_rate_label) == ["1.5%", "2.0%", "2.5%", "3.0%"], "discount schedule differs")
    require((frame.baseline_agriculture_error_usd == 0.0).all(), "baseline agriculture differs")
    require((frame.baseline_cpc_error == 0.0).all(), "baseline CPC differs")
    require((frame.absolute_error <= frame.numerical_error_bound_usd2005_per_tco2 + 1e-15).all(), "paired diagnostic exceeds numerical bound")
    require(frame.aggregated_increment_error_usd.max() <= 0.01, "aggregated increment error exceeds one cent")

    give_sources = {
        "main_model": GIVE_ROOT / "packages/MimiGIVE/src/main_model.jl",
        "scc": GIVE_ROOT / "packages/MimiGIVE/src/scc.jl",
        "damage_aggregator": GIVE_ROOT / "packages/MimiGIVE/src/components/DamageAggregator.jl",
        "manifest": GIVE_ROOT / "Manifest.toml",
    }
    result = {
        "schema": "quantity_anchored_replacement_sentinel/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "paired_marginal_response_replacement_sentinel_pass",
        "specification": sentinel["specification"],
        "definition": "retain the exact MooreAg baseline regional damage level, remove the MooreAg marginal pulse response, and substitute the external precipitation-quantity marginal response",
        "validation": {
            "baseline_agriculture_maximum_absolute_error_usd": float(frame.baseline_agriculture_error_usd.max()),
            "baseline_cpc_maximum_absolute_error": float(frame.baseline_cpc_error.max()),
            "regional_increment_maximum_absolute_error_billion_usd2005": float(frame.regional_increment_error_billion_usd2005.max()),
            "aggregated_increment_maximum_absolute_error_usd": float(frame.aggregated_increment_error_usd.max()),
            "paired_vs_external_diagnostic_maximum_absolute_error_usd2005_per_tco2": float(frame.absolute_error.max()),
            "all_paired_errors_below_derived_floating_point_bounds": True,
            "legacy_agriculture_component_removed_and_single_replacement_producer_audited_in_julia": True,
        },
        "sources": {
            "regional_increment": {"path": str(source), "sha256": digest(source), "receipt": str(args.sentinel_receipt), "receipt_sha256": digest(args.sentinel_receipt)},
            "external_diagnostic": {"path": expected["output"]["path"], "sha256": expected["output"]["sha256"], "receipt": str(args.expected_receipt), "receipt_sha256": digest(args.expected_receipt)},
            "julia_job": {"path": str(args.job_receipt), "sha256": digest(args.job_receipt), **job},
            "julia_script": {"path": str(args.julia_script), "sha256": digest(args.julia_script)},
            "replacement_component": {"path": str(args.component), "sha256": digest(args.component)},
            **{f"give_{name}": {"path": str(path), "sha256": digest(path)} for name, path in give_sources.items()},
        },
        "output": {"path": str(args.result), "bytes": args.result.stat().st_size, "sha256": digest(args.result)},
        "claim_gates": {"paired_replacement_engineering": True, "single_model_sentinel": True, "ensemble_replacement_scc": False, "full_agriculture_replacement": False},
        "limitations": [
            "This is one climate-model, one-pulse, central-market sentinel rather than the full ensemble.",
            "The baseline level is anchored to MooreAg to preserve consumption; only the marginal response is replaced.",
            "The replacement response remains the maize annual-rainfall-quantity channel only.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
