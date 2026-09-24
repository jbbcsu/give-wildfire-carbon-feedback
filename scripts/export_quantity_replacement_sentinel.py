#!/usr/bin/env python3
"""Export one pinned regional path for the paired GIVE replacement sentinel."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

MODEL = "ACCESS-CM2"
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
            ("climate_model", "==", MODEL),
            ("pulse_size_gtc", "==", PULSE),
            ("adaptation", "==", ADAPTATION),
            ("tail_rule", "==", TAIL),
        ],
    )
    frame = frame[["year", "fund_region", "marginal_damage_difference_billion_usd2005"]]
    frame["fund_region"] = pd.Categorical(frame.fund_region, categories=regions, ordered=True)
    frame = frame.sort_values(["year", "fund_region"]).reset_index(drop=True)
    require(len(frame) == 281 * 16, "sentinel support differs")
    require(list(frame.year.unique()) == list(range(2020, 2301)), "sentinel years differ")
    require(all(list(group.fund_region.astype(str)) == regions for _, group in frame.groupby("year", observed=True, sort=True)), "sentinel region order differs")
    require((frame.loc[frame.year.eq(2020), "marginal_damage_difference_billion_usd2005"] == 0.0).all(), "pre-pulse identity differs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    result = {
        "schema": "quantity_replacement_sentinel/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pinned_central_market_regional_increment_for_paired_replacement_test",
        "specification": {"climate_model": MODEL, "pulse_size_gtc": PULSE, "adaptation": ADAPTATION, "tail_rule": TAIL, "elasticity_id": "hultgren_pair_010_004", "yield_to_supply_mapping": "horizontal_output"},
        "source": {"path": str(source), "sha256": digest(source), "receipt": str(args.fund_receipt), "receipt_sha256": digest(args.fund_receipt)},
        "support": {"years": [2020, 2300], "regions": regions, "rows": len(frame)},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gate": "engineering_input_only_not_replacement_scc",
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
