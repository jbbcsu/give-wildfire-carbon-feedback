#!/usr/bin/env python3
"""Test FishMIP temporal diagnostics against two literal FishStat status sets."""

from __future__ import annotations
import argparse, csv, hashlib, json, math, tomllib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

TEMPORAL_SHA = "24552000bf4292cc6f8f9d1c85c46cea49a904cf9c47a30b716121389e25e00f"
YEARS = np.arange(1950, 2015)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(value: bool, message: str) -> None:
    if not value: raise ValueError(message)


def metrics(observed: np.ndarray, modeled: np.ndarray) -> dict[str, float]:
    residual = modeled - observed
    return {"level_pearson": float(np.corrcoef(observed, modeled)[0, 1]), "level_rmse": float(np.sqrt(np.mean(residual**2))), "first_difference_pearson": float(np.corrcoef(np.diff(observed), np.diff(modeled))[0, 1]), "first_difference_rmse": float(np.sqrt(np.mean((np.diff(modeled) - np.diff(observed))**2)))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract", type=Path, required=True); p.add_argument("--ledger-receipt", type=Path, required=True); p.add_argument("--temporal", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); require(not a.output.exists(), "fresh output required")
    contract = tomllib.loads(a.contract.read_text()); ledger = json.loads(a.ledger_receipt.read_text()); require(digest(a.temporal) == TEMPORAL_SHA, "temporal diagnostic hash differs")
    require(contract["schema"] == "fao_fishstat_capture_headless_export_contract_v1" and ledger["schema"] == "fao_fishstat_marine_status_ledger/v1", "source schema differs")
    ledger_path = Path(ledger["output"]["path"]); require(digest(ledger_path) == ledger["output"]["sha256"], "ledger hash differs")
    present = set(ledger["support"]["statuses_present"]); quality = set(contract["export"]["observed_or_quality_status_codes"]) & present
    require(quality == {"A", "E", "I", "X"}, "present quality-status set differs")
    totals = {"contract_observed_or_quality": {int(y): 0.0 for y in YEARS}, "A_only": {int(y): 0.0 for y in YEARS}}
    with ledger_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            year = int(row["year"]); status = row["status_code"]; value = float(row["tonnes_live_weight"])
            if year not in totals["A_only"]: continue
            if status in quality: totals["contract_observed_or_quality"][year] += value
            if status == "A": totals["A_only"][year] += value
    normalized = {}
    references = {}
    for family, values in totals.items():
        array = np.asarray([values[int(y)] for y in YEARS]); require((array > 0).all(), "nonpositive observed series")
        reference = float(array[(YEARS >= 2005)].mean()); references[family] = reference; normalized[family] = array / reference
    temporal = json.loads(a.temporal.read_text()); annual = temporal["annual"]; require([r["year"] for r in annual] == YEARS.tolist(), "temporal years differ")
    results = []
    for path in temporal["paths"]:
        path_id = path["path_id"]; modeled = np.asarray([r[f"{path_id}_normalized"] for r in annual])
        for start in [1950, 1980]:
            mask = YEARS >= start
            base = metrics(normalized["contract_observed_or_quality"][mask], modeled[mask]); alternate = metrics(normalized["A_only"][mask], modeled[mask])
            results.append({"path_id": path_id, "start_year": start, "end_year": 2014, "contract_observed_or_quality": base, "A_only": alternate, "A_only_minus_quality": {key: alternate[key] - base[key] for key in base}})
    result = {"schema": "fishmip_fao_status_sensitivity/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "literal_status_family_temporal_sensitivity_complete", "status_families": {"contract_observed_or_quality": sorted(quality), "A_only": ["A"]}, "reference_2005_2014_tonnes": references, "support": {"years": [1950, 2014], "paths": len(temporal["paths"]), "periods": [[1950, 2014], [1980, 2014]], "comparisons": len(results)}, "comparisons": results, "sources": {"contract": {"path": str(a.contract), "sha256": digest(a.contract)}, "status_ledger": {"path": str(ledger_path), "sha256": digest(ledger_path), "receipt": str(a.ledger_receipt), "receipt_sha256": digest(a.ledger_receipt)}, "temporal_diagnostic": {"path": str(a.temporal), "sha256": digest(a.temporal)}}, "claim_gates": {"observation_status_sensitivity": True, "preferred_calibration_status_family": False, "model_selection": False, "climate_attribution": False, "welfare_damage_or_scc": False}, "limitations": ["A-only is a literal robustness subset, not a claim that other contract quality codes are invalid.", "The global temporal comparison cannot separate ecology from reporting, effort, management, markets, or technology.", "No model is selected or weighted from these post-existing-evidence comparisons."], "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())}}
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "references": references, "comparisons": len(results)}, indent=2))


if __name__ == "__main__": main()
