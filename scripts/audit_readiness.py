#!/usr/bin/env python3
"""Audit GIVE natural methane and the published MAGICC wetland benchmark."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delta_wetland_emissions(temp_delta_k: float, slope: float) -> float:
    """Mechanical anomaly only; not an authorized absolute-emissions model."""
    return slope * temp_delta_k


def normal_probability_below_zero(mean: float, sd: float) -> float:
    return 0.5 * (1.0 + math.erf((0.0 - mean) / (sd * math.sqrt(2.0))))


def main() -> int:
    cfg = json.loads((ROOT / "config/wetland_methane_feedback_contract_v1.json").read_text())
    give = cfg["give_audit"]
    path = ROOT / give["natural_emissions_path"]
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    future = [float(r["CH4"]) for r in rows if 2015 <= int(r["year"]) <= 2300]
    bench = cfg["magicc_2026_benchmark"]
    mean = bench["mean_slope_MtCH4_per_year_per_K"]
    sd = bench["slope_sd_MtCH4_per_year_per_K"]
    receipt = {
        "schema": "wetland_methane_feedback_readiness_receipt/v1",
        "status": cfg["status"],
        "give_integration_authorized": cfg["scope"]["give_integration_authorized"],
        "scc_adjustment_authorized": cfg["scope"]["scc_adjustment_authorized"],
        "give_natural_emissions_hash_matches": digest(path) == give["natural_emissions_sha256"],
        "natural_ch4_2015_2300_years": len(future),
        "natural_ch4_2015_2300_constant": len(set(future)) == 1,
        "natural_ch4_2015_2300_Mt_per_year": future[0],
        "mechanical_mean_delta_for_one_K_Mt_per_year": delta_wetland_emissions(1.0, mean),
        "untruncated_normal_probability_negative_slope": normal_probability_below_zero(mean, sd),
        "biogenic_oxidation_gate_passed": cfg["claim_gates"]["biogenic_methane_oxidation_routing_validated"],
        "climate_damage_or_scc_result_created": False
    }
    out = ROOT / "provenance/wetland_methane_readiness_receipt_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

