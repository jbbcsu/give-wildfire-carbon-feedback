#!/usr/bin/env python3
"""Reweight the validated annual quantity-channel path across GIVE discount schedules."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_quantity_coefficient_delta_uncertainty import PULSE, digest, require
from decompose_quantity_scc_by_period import PERIODS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annual-receipt", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    annual_receipt = json.loads(args.annual_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
    require(annual_receipt["schema"] == "quantity_scc_period_decomposition/v1", "annual receipt differs")
    annual_path = Path(annual_receipt["output"]["path"])
    require(digest(annual_path) == annual_receipt["output"]["sha256"], "annual table hash differs")
    require(digest(args.cpc) == diagnostic["sources"]["give_cpc"]["sha256"], "CPC hash differs")
    diagnostic_path = Path(diagnostic["output"]["path"])
    require(digest(diagnostic_path) == diagnostic["output"]["sha256"], "diagnostic hash differs")

    annual = pd.read_csv(annual_path)
    require(len(annual) == 7306, "annual model-year support differs")
    years = np.arange(2020, 2301)
    cpc = pd.read_csv(args.cpc).set_index("year").loc[years, "net_cpc_2005usd_per_person"].to_numpy(float)
    expected = pd.read_csv(diagnostic_path)
    expected = expected.loc[
        expected.pulse_size_gtc.eq(PULSE)
        & expected.adaptation.eq("fixed")
        & expected.tail_rule.eq("uncapped")
        & expected.elasticity_id.eq("hultgren_pair_010_004")
        & expected.yield_to_supply_mapping.eq("horizontal_output")
    ].set_index(["discount_rate_label", "climate_model"])
    require(len(expected) == 104, "expected model-schedule support differs")

    results = []
    maximum_error = 0.0
    for schedule in diagnostic["discounting"]["rates"]:
        label = schedule["label"]
        discount = np.power(cpc[0] / cpc, float(schedule["eta"])) / np.power(
            1.0 + float(schedule["prtp"]), years - 2020
        )
        work = annual.copy()
        work["discounted"] = (
            work.undiscounted_scc_equivalent_usd2020_per_tco2_year.to_numpy(float)
            * work.year.map(dict(zip(years, discount, strict=True))).to_numpy(float)
        )
        model_totals = work.groupby("climate_model").discounted.sum()
        expected_totals = expected.loc[label].partial_scc_diagnostic_usd2020_per_tco2
        require(set(model_totals.index) == set(expected_totals.index), f"model labels differ: {label}")
        error = float((model_totals.reindex(expected_totals.index) - expected_totals).abs().max())
        maximum_error = max(maximum_error, error)
        mean_annual = work.groupby("year").discounted.mean()
        total = float(mean_annual.sum())
        periods = []
        for start, end in PERIODS:
            contribution = float(mean_annual.loc[start:end].sum())
            periods.append(
                {
                    "years": [start, end],
                    "discounted_contribution_usd2020_per_tco2": contribution,
                    "share_of_signed_total": contribution / total,
                }
            )
        results.append(
            {
                "discount_rate_label": label,
                "prtp": float(schedule["prtp"]),
                "eta": float(schedule["eta"]),
                "equal_model_mean_usd2020_per_tco2": total,
                "periods": periods,
            }
        )
    require(maximum_error <= 2e-14, f"discount-grid model reconstruction differs: {maximum_error}")
    require(all(math.isclose(sum(row["share_of_signed_total"] for row in result["periods"]), 1.0, abs_tol=1e-14)
                for result in results), "period shares differ from one")
    output = {
        "schema": "quantity_scc_period_discount_grid/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "four_schedule_period_decomposition_complete",
        "estimand": "time-period contributions to the equal-26-model fixed-adaptation uncapped annual-maize rainfall-quantity SCC under four GIVE Ramsey schedules",
        "results": results,
        "validation": {
            "model_schedule_totals": 104,
            "maximum_model_reconstruction_error_usd2020_per_tco2": maximum_error,
        },
        "sources": {
            "annual_receipt": {"path": str(args.annual_receipt), "sha256": digest(args.annual_receipt)},
            "annual_table": {"path": str(annual_path), "sha256": digest(annual_path)},
            "cpc": {"path": str(args.cpc), "sha256": digest(args.cpc)},
            "diagnostic_receipt": {"path": str(args.diagnostic_receipt), "sha256": digest(args.diagnostic_receipt)},
        },
        "claim_gates": {
            "registered_discount_schedule_temporal_accounting": True,
            "probabilistic_discount_uncertainty": False,
            "full_precipitation_agriculture_scc": False,
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "results": results, "validation": output["validation"]}, indent=2))


if __name__ == "__main__":
    main()
