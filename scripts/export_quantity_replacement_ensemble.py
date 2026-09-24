#!/usr/bin/env python3
"""Export the registered 26-model central regional paths for paired GIVE runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PULSE = 0.000025
ADAPTATION = "fixed"
TAIL = "uncapped"


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
    parser.add_argument("--fund-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    receipt = json.loads(args.fund_receipt.read_text(encoding="utf-8"))
    require(receipt["schema"] == "epa_fair_hultgren_quantity_fund_paths/v1", "receipt differs")
    source = Path(receipt["output"]["path"])
    require(digest(source) == receipt["output"]["sha256"], "source hash differs")
    regions = receipt["support"]["fund_regions"]
    frame = pd.read_parquet(
        source,
        filters=[
            ("pulse_size_gtc", "==", PULSE),
            ("adaptation", "==", ADAPTATION),
            ("tail_rule", "==", TAIL),
        ],
        columns=["climate_model", "year", "fund_region", "marginal_damage_difference_billion_usd2005"],
    )
    models = sorted(frame.climate_model.unique())
    require(len(models) == receipt["support"]["models"] == 26, "model support differs")
    frame["climate_model"] = pd.Categorical(frame.climate_model, categories=models, ordered=True)
    frame["fund_region"] = pd.Categorical(frame.fund_region, categories=regions, ordered=True)
    frame = frame.sort_values(["climate_model", "year", "fund_region"]).reset_index(drop=True)
    require(len(frame) == 26 * 281 * 16, "ensemble support differs")
    for model, group in frame.groupby("climate_model", observed=True, sort=True):
        require(list(group.year.unique()) == list(range(2020, 2301)), f"year support differs for {model}")
        require(all(list(year_group.fund_region.astype(str)) == regions for _, year_group in group.groupby("year", observed=True, sort=True)), f"region order differs for {model}")
        require((group.loc[group.year.eq(2020), "marginal_damage_difference_billion_usd2005"] == 0.0).all(), f"pre-pulse identity differs for {model}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    result = {
        "schema": "quantity_replacement_ensemble_input/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "registered_26_model_central_regional_increments_for_paired_replacement",
        "specification": {"pulse_size_gtc": PULSE, "adaptation": ADAPTATION, "tail_rule": TAIL, "elasticity_id": "hultgren_pair_010_004", "yield_to_supply_mapping": "horizontal_output"},
        "source": {"path": str(source), "sha256": digest(source), "receipt": str(args.fund_receipt), "receipt_sha256": digest(args.fund_receipt)},
        "support": {"climate_models": models, "years": [2020, 2300], "regions": regions, "rows": len(frame)},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gate": "engineering_input_only_until_paired_give_validation",
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
