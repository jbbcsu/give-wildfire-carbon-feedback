#!/usr/bin/env python3
"""Validate the machine-readable transcription of Hultgren Table S13."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = tomllib.loads(config_path.read_text())
    require(config["source_doi"] == "10.1038/s41586-025-09085-w", "source DOI changed")
    receipt = ROOT / config["source_pdf_receipt"]
    source = json.loads(receipt.read_text())
    require(source["sha256"] == config["source_pdf_sha256"], "source PDF hash changed")
    text = ROOT / config["text_extract"]
    require(digest(text) == config["text_extract_sha256"], "text extraction hash changed")
    require(config["project_scc_authorized"] is False, "project SCC gate changed")

    rows = config["rows"]
    require(len(rows) == 16, "Table S13 row count changed")
    require(Counter(row["emissions"] for row in rows) == {"RCP8.5": 8, "RCP4.5": 8}, "scenario count changed")
    unique = set()
    ratios = []
    for row in rows:
        key = tuple(row[field] for field in (
            "emissions", "supply_elasticity", "demand_elasticity", "market",
            "max_expenditure", "co2_fertilization",
        ))
        require(key not in unique, f"duplicate scenario row: {key}")
        unique.add(key)
        varietal = float(row["varietal_switching"])
        flexible = float(row["flexible_production_trade"])
        require(math.isfinite(varietal) and math.isfinite(flexible) and 0 < flexible < varietal, "invalid SCC values")
        ratios.append(flexible / varietal)
    require(max(abs(ratio - 0.45) for ratio in ratios) < 0.0015, "reported 55 percent flexibility adjustment changed")

    by_scenario = {}
    for scenario in ("RCP8.5", "RCP4.5"):
        selected = [row for row in rows if row["emissions"] == scenario]
        by_scenario[scenario] = {
            "varietal_switching_range_2023_usd_per_tco2": [
                min(float(row["varietal_switching"]) for row in selected),
                max(float(row["varietal_switching"]) for row in selected),
            ],
            "flexible_production_trade_range_2023_usd_per_tco2": [
                min(float(row["flexible_production_trade"]) for row in selected),
                max(float(row["flexible_production_trade"]) for row in selected),
            ],
        }

    output = {
        "schema": "hultgren_partial_scc_table_s13_validation_v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": digest(config_path)},
        "source_pdf_receipt": {"path": config["source_pdf_receipt"], "sha256": digest(receipt)},
        "source_pdf_sha256": config["source_pdf_sha256"],
        "rows": len(rows),
        "reported_flexible_to_varietal_ratio_range": [min(ratios), max(ratios)],
        "scenario_ranges": by_scenario,
        "claim_gates": {
            "published_table_transcription_validated": True,
            "project_damage_estimate_validated": False,
            "project_scc_estimate_validated": False,
            "give_integration_authorized": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output["scenario_ranges"], sort_keys=True))


if __name__ == "__main__":
    main()
