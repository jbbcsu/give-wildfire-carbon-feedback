#!/usr/bin/env python3
"""Register the paired 26-model adaptation-by-tail GIVE replacement."""

from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["input_receipt", "expected_receipt", "result", "job_receipt", "julia_script", "component", "output"]:
        p.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    a = p.parse_args(); require(not a.output.exists(), "fresh output required")
    inp = json.loads(a.input_receipt.read_text()); exp_receipt = json.loads(a.expected_receipt.read_text()); job = json.loads(a.job_receipt.read_text())
    require(inp["schema"] == "quantity_replacement_adaptation_tail_ensemble_input/v1", "input receipt differs")
    require(exp_receipt["schema"] == "epa_fair_hultgren_quantity_partial_scc_diagnostic/v1", "diagnostic receipt differs")
    require(job["status"] == "completed" and job["returncode"] == 0, "GIVE job failed")
    source = Path(inp["output"]["path"]); require(digest(source) == inp["output"]["sha256"], "input hash differs")
    frame = pd.read_csv(a.result)
    keys = ["climate_model", "adaptation", "tail_rule", "discount_rate_label"]
    require(len(frame) == 26 * 3 * 2 * 4 == 624 and not frame.duplicated(keys).any(), "result support differs")
    require(frame.baseline_agriculture_error_usd.eq(0).all() and frame.baseline_cpc_error.eq(0).all(), "baseline identity differs")
    require(frame.regional_increment_error_billion_usd2005.max() <= 1e-12, "regional increment differs")
    require(frame.aggregated_increment_error_usd.max() <= 0.05, "aggregation cancellation exceeds gate")
    require((frame.absolute_error <= frame.numerical_error_bound_usd2005_per_tco2 + 1e-15).all(), "paired error exceeds propagated bound")
    exp_path = Path(exp_receipt["output"]["path"]); require(digest(exp_path) == exp_receipt["output"]["sha256"], "diagnostic hash differs")
    expected = pd.read_csv(exp_path)
    expected = expected.loc[expected.pulse_size_gtc.eq(inp["specification"]["pulse_size_gtc"]) & expected.elasticity_id.eq(inp["specification"]["elasticity_id"]) & expected.yield_to_supply_mapping.eq(inp["specification"]["yield_to_supply_mapping"]), keys + ["partial_scc_diagnostic_usd2005_per_tco2", "partial_scc_diagnostic_usd2020_per_tco2"]]
    merged = frame.merge(expected, on=keys, how="outer", validate="one_to_one", indicator=True)
    require(len(merged) == 624 and merged._merge.eq("both").all(), "diagnostic keys differ")
    require(merged.expected_usd2005_per_tco2.eq(merged.partial_scc_diagnostic_usd2005_per_tco2).all() and merged.expected_usd2020_per_tco2.eq(merged.partial_scc_diagnostic_usd2020_per_tco2).all(), "diagnostic copies differ")
    summaries = {}
    for (rate, adaptation, tail), group in frame.groupby(["discount_rate_label", "adaptation", "tail_rule"], sort=True):
        v = group.expected_usd2020_per_tco2
        summaries.setdefault(rate, {}).setdefault(adaptation, {})[tail] = {"models": len(v), "mean_usd2020_per_tco2": float(v.mean()), "median_usd2020_per_tco2": float(v.median()), "minimum_usd2020_per_tco2": float(v.min()), "maximum_usd2020_per_tco2": float(v.max()), "negative_models": int((v < 0).sum())}
    result = {
        "schema": "quantity_anchored_replacement_adaptation_tail_ensemble/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "paired_156_path_adaptation_tail_replacement_pass",
        "specification": inp["specification"], "support": {"climate_models": 26, "adaptations": inp["support"]["adaptations"], "tail_rules": inp["support"]["tail_rules"], "discount_schedules": 4, "paths": 156, "result_rows": 624}, "summary": summaries,
        "validation": {"baseline_agriculture_maximum_absolute_error_usd": float(frame.baseline_agriculture_error_usd.max()), "baseline_cpc_maximum_absolute_error": float(frame.baseline_cpc_error.max()), "regional_increment_maximum_absolute_error_billion_usd2005": float(frame.regional_increment_error_billion_usd2005.max()), "aggregated_increment_maximum_absolute_error_usd": float(frame.aggregated_increment_error_usd.max()), "paired_vs_external_maximum_absolute_error_usd2005_per_tco2": float(frame.absolute_error.max()), "all_errors_below_propagated_bounds": True, "all_624_external_rows_reconstructed_exactly": True},
        "sources": {"regional_input": {"path": str(source), "sha256": digest(source), "receipt": str(a.input_receipt), "receipt_sha256": digest(a.input_receipt)}, "external_diagnostic": {"path": str(exp_path), "sha256": digest(exp_path), "receipt": str(a.expected_receipt), "receipt_sha256": digest(a.expected_receipt)}, "julia_result": {"path": str(a.result), "bytes": a.result.stat().st_size, "sha256": digest(a.result)}, "julia_job": {"path": str(a.job_receipt), "sha256": digest(a.job_receipt), **job}, "julia_script": {"path": str(a.julia_script), "sha256": digest(a.julia_script)}, "replacement_component": {"path": str(a.component), "sha256": digest(a.component)}},
        "claim_gates": {"paired_adaptation_tail_quantity_channel_scc": True, "market_structure_paired_execution": False, "probabilistic_or_empirical_uncertainty": False, "full_precipitation_agriculture_scc": False},
        "limitations": ["Only the central elasticity and horizontal-output supply mapping are paired here.", "The design excludes timing, drought, temperature, other crops, irrigation adaptation, trade, storage, and adaptation costs.", "Adaptation labels are registered scenarios, not estimated probabilities."],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "support": result["support"], "validation": result["validation"]}, indent=2))


if __name__ == "__main__": main()
