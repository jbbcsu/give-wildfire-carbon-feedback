#!/usr/bin/env python3
"""Audit META Amazon mechanics and write a non-SCC readiness receipt."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def legacy_release(total: float, duration: float) -> tuple[int, float]:
    installment = total / duration
    cumulative = 0.0
    years = 0
    while cumulative < total - 0.01:
        cumulative += installment
        years += 1
        if years > 1000:
            raise RuntimeError("release audit failed to terminate")
    return years, cumulative


def stock_conserving_release(total: float, duration: float) -> list[float]:
    installment = total / duration
    remaining = total
    out = []
    while remaining > 1e-12:
        payment = min(installment, remaining)
        out.append(payment)
        remaining -= payment
    return out


def main() -> int:
    cfg = json.loads((ROOT / "config/amazon_dieback_feedback_contract_v1.json").read_text())
    meta = cfg["meta_2021"]
    hashes = {
        key: digest(ROOT / meta[key]) == meta[key.replace("_path", "_sha256")]
        for key in ("source_path", "co2_connection_path", "parameter_path", "benchmark_path", "license_path")
    }
    with (ROOT / meta["parameter_path"]).open(encoding="utf-8-sig", newline="") as handle:
        params = list(csv.DictReader(handle))
    with (ROOT / meta["benchmark_path"]).open(encoding="utf-8-sig", newline="") as handle:
        benchmark = list(csv.DictReader(handle))
    first_release = next(row for row in benchmark if float(row["CO2_AMAZ (GtCO2)"]) > 0)
    total = meta["central_parameters"]["maximum_release_GtCO2"]
    noninteger_duration = 50.5
    legacy_years, legacy_total = legacy_release(total, noninteger_duration)
    corrected = stock_conserving_release(total, noninteger_duration)
    example_temp = 2.0
    b = meta["central_parameters"]["annual_hazard_coefficient_per_degC"]
    annual_hazard = 1.0 - math.exp(-b * max(0.0, example_temp - 1.0))
    receipt = {
        "schema": "amazon_dieback_feedback_readiness_receipt/v1",
        "status": cfg["status"],
        "give_integration_authorized": cfg["scope"]["give_integration_authorized"],
        "scc_adjustment_authorized": cfg["scope"]["scc_adjustment_authorized"],
        "vendored_hashes_match": hashes,
        "parameter_calibrations": len(params),
        "benchmark_first_release_year": int(first_release["Year"]),
        "benchmark_first_release_GtCO2": float(first_release["CO2_AMAZ (GtCO2)"]),
        "annual_hazard_at_2C": annual_hazard,
        "continuous_duration_source_issue": {
            "example_duration_years": noninteger_duration,
            "legacy_installments": legacy_years,
            "legacy_total_GtCO2": legacy_total,
            "legacy_overshoot_GtCO2": legacy_total - total,
            "corrected_installments": len(corrected),
            "corrected_total_GtCO2": sum(corrected),
            "stock_conserving_gate_passed": abs(legacy_total - total) < 1e-9
        },
        "combined_epa_uplift_used": False,
        "climate_or_scc_result_created": False
    }
    out = ROOT / "provenance/amazon_feedback_readiness_receipt_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

