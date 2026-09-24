#!/usr/bin/env python3
"""Export all adaptation/tail regional paths for paired GIVE replacement."""

from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

PULSE = 0.000025


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
    p.add_argument("--fund-receipt", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    require(not a.output.exists() and not a.receipt.exists(), "fresh outputs required")
    receipt = json.loads(a.fund_receipt.read_text())
    require(receipt["schema"] == "epa_fair_hultgren_quantity_fund_paths/v1", "receipt differs")
    source = Path(receipt["output"]["path"])
    require(digest(source) == receipt["output"]["sha256"], "source hash differs")
    columns = ["climate_model", "year", "adaptation", "tail_rule", "fund_region", "marginal_damage_difference_billion_usd2005"]
    frame = pd.read_parquet(source, filters=[("pulse_size_gtc", "==", PULSE)], columns=columns)
    models = sorted(frame.climate_model.unique())
    adaptations = ["fixed", "trend", "upper"]
    tails = ["uncapped", "published_analogue_p01_p99"]
    regions = receipt["support"]["fund_regions"]
    for col, levels in [("climate_model", models), ("adaptation", adaptations), ("tail_rule", tails), ("fund_region", regions)]:
        frame[col] = pd.Categorical(frame[col], categories=levels, ordered=True)
    frame = frame.sort_values(["climate_model", "adaptation", "tail_rule", "year", "fund_region"]).reset_index(drop=True)
    require(len(frame) == 26 * 3 * 2 * 281 * 16, "support differs")
    counts = frame.groupby(["climate_model", "adaptation", "tail_rule"], observed=True).size()
    require(len(counts) == 156 and counts.eq(281 * 16).all(), "path support differs")
    require(frame.loc[frame.year.eq(2020), "marginal_damage_difference_billion_usd2005"].eq(0).all(), "pre-pulse identity differs")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(a.output, index=False)
    result = {
        "schema": "quantity_replacement_adaptation_tail_ensemble_input/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "registered_156_path_regional_increments_for_paired_replacement",
        "specification": {"pulse_size_gtc": PULSE, "elasticity_id": "hultgren_pair_010_004", "yield_to_supply_mapping": "horizontal_output"},
        "source": {"path": str(source), "sha256": digest(source), "receipt": str(a.fund_receipt), "receipt_sha256": digest(a.fund_receipt)},
        "support": {"climate_models": models, "adaptations": adaptations, "tail_rules": tails, "years": [2020, 2300], "regions": regions, "paths": 156, "rows": len(frame)},
        "output": {"path": str(a.output), "bytes": a.output.stat().st_size, "sha256": digest(a.output)},
        "claim_gate": "engineering_input_only_until_paired_give_validation",
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "support": result["support"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
