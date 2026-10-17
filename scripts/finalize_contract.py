#!/usr/bin/env python3
"""Create a deterministic receipt without creating an SCC result."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    cfg = json.loads((ROOT / "config/freshwater_angling_contract_v1.json").read_text())
    table = ROOT / cfg["reported_benchmark"]["path"]
    with table.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    means = {f"{r['endpoint']}|{r['rcp']}": float(r["cumulative_change_million_2015usd"])
             for r in rows if r["gcm"] == "five_gcm_average"}
    receipt = {
        "schema": "freshwater_angling_readiness_receipt/v1",
        "status": cfg["status"],
        "give_addition_authorized": cfg["scope"]["give_addition_authorized"],
        "reported_benchmark_label": cfg["reported_benchmark"]["label"],
        "reported_five_gcm_average_million_2015usd": means,
        "reported_table_sha256": digest(table),
        "failed_gates": sorted(k for k, value in cfg["claim_gates"].items() if value is False),
        "scc_output_created": False
    }
    out = ROOT / "provenance/freshwater_angling_readiness_receipt_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
