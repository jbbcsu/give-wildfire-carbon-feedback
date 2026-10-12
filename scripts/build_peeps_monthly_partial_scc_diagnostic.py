#!/usr/bin/env python3
"""Discount one-ESM monthly-pattern damages on the standard GIVE baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_epa_fair_hultgren_quantity_damage_paths import CONVERGENCE_RELATIVE_TOLERANCE
from build_epa_fair_hultgren_quantity_fund_paths import validated_price_registry

PRICE_2005_TO_2020 = 113.648 / 87.504
MOLECULAR_C_TO_CO2 = 12.0 / 44.0
DISCOUNT_RATES = (
    ("1.5%", math.exp(9.149606e-05) - 1.0, 1.016010),
    ("2.0%", math.exp(0.001972641) - 1.0, 1.244458999),
    ("2.5%", math.exp(0.004618784) - 1.0, 1.421158088),
    ("3.0%", math.exp(0.007702711) - 1.0, 1.567899391),
)


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
    parser.add_argument("--damage-paths", type=Path, required=True)
    parser.add_argument("--damage-receipt", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--cpc-job-receipt", type=Path, required=True)
    parser.add_argument("--price-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    damage_receipt = json.loads(args.damage_receipt.read_text())
    job_receipt = json.loads(args.cpc_job_receipt.read_text())
    require(damage_receipt["schema"] == "peeps_fair_hultgren_monthly_damage_paths/v1", "damage receipt differs")
    require(damage_receipt["output"]["sha256"] == digest(args.damage_paths), "damage path hash differs")
    require(damage_receipt["claim_gates"]["central_structural_damage_path"], "damage path gate closed")
    require(job_receipt["status"] == "completed" and job_receipt["returncode"] == 0, "GIVE CPC export job failed")
    registry, price_scalar = validated_price_registry(args.price_registry)

    cpc = pd.read_csv(args.cpc)
    require(list(cpc.year) == list(range(2020, 2301)), "GIVE CPC years differ")
    require(cpc.rff_sample_id.nunique() == 1 and int(cpc.rff_sample_id.iloc[0]) == 6546, "RFF sample differs")
    expected_cpc = cpc.net_consumption_billion_2005usd.to_numpy() * 1e3 / cpc.global_population_million.to_numpy()
    cpc_error = float(np.max(np.abs(expected_cpc - cpc.net_cpc_2005usd_per_person.to_numpy())))
    expected_net = cpc.global_gdp_billion_2005usd.to_numpy() - cpc.total_damage_2005usd.to_numpy() / 1e9
    net_error = float(np.max(np.abs(expected_net - cpc.net_consumption_billion_2005usd.to_numpy())))
    require(cpc_error <= 1e-9 and net_error <= 1e-8 and (cpc.net_cpc_2005usd_per_person > 0).all(), "GIVE CPC identity failed")
    base_cpc = float(cpc.loc[cpc.year.eq(2020), "net_cpc_2005usd_per_person"].iloc[0])
    discount = {
        label: np.asarray([(base_cpc / float(row.net_cpc_2005usd_per_person)) ** eta / (1.0 + prtp) ** (int(row.year) - 2020) for row in cpc.itertuples(index=False)])
        for label, prtp, eta in DISCOUNT_RATES
    }
    require(all(values[0] == 1.0 for values in discount.values()), "discount identity differs")

    paths = pd.read_parquet(args.damage_paths)
    require(len(paths) == damage_receipt["support"]["rows"], "damage row count differs")
    require(paths.climate_model.nunique() == 1 and set(paths.tail_rule) == {"uncapped"}, "damage design differs")
    records = []
    for (pulse, adaptation), frame in paths.loc[paths.pulse_size_gtc.gt(0)].groupby(["pulse_size_gtc", "adaptation"]):
        frame = frame.sort_values("year")
        require(frame.year.tolist() == list(range(2020, 2301)), "annual path coverage differs")
        annual = frame.damage_change_usd_source_price_basis.to_numpy(dtype=np.float64) * price_scalar / 1e9
        normalized = annual * MOLECULAR_C_TO_CO2 / float(pulse)
        for label, prtp, eta in DISCOUNT_RATES:
            scc_2005 = float(np.sum(discount[label] * normalized))
            records.append({
                "climate_model": str(frame.climate_model.iloc[0]),
                "pulse_size_gtc": float(pulse),
                "adaptation": str(adaptation),
                "tail_rule": "uncapped",
                "discount_rate_label": label,
                "prtp": prtp,
                "eta": eta,
                "partial_scc_diagnostic_usd2005_per_tco2": scc_2005,
                "partial_scc_diagnostic_usd2020_per_tco2": scc_2005 * PRICE_2005_TO_2020,
                "annual_year_count": len(frame),
            })
    output = pd.DataFrame(records).sort_values(["adaptation", "pulse_size_gtc", "discount_rate_label"]).reset_index(drop=True)
    require(len(output) == 3 * 3 * 4 and not output.duplicated(["pulse_size_gtc", "adaptation", "discount_rate_label"]).any(), "SCC output support differs")
    keys = ["adaptation", "discount_rate_label"]
    small = output.loc[output.pulse_size_gtc.eq(0.000025), keys + ["partial_scc_diagnostic_usd2005_per_tco2"]]
    next_small = output.loc[output.pulse_size_gtc.eq(0.00005), keys + ["partial_scc_diagnostic_usd2005_per_tco2"]]
    joined = small.merge(next_small, on=keys, suffixes=("_small", "_next"), validate="one_to_one")
    a = joined.partial_scc_diagnostic_usd2005_per_tco2_small.to_numpy()
    b = joined.partial_scc_diagnostic_usd2005_per_tco2_next.to_numpy()
    convergence = float(np.max(np.abs(a - b)) / max(np.max(np.abs(a)), np.max(np.abs(b)), 1e-30))
    require(convergence <= CONVERGENCE_RELATIVE_TOLERANCE, "SCC shrinking-pulse convergence failed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    central = output.loc[output.pulse_size_gtc.eq(0.000025) & output.discount_rate_label.eq("2.0%")]
    central_values = {str(row.adaptation): float(row.partial_scc_diagnostic_usd2020_per_tco2) for row in central.itertuples(index=False)}
    result = {
        "schema": "peeps_monthly_partial_scc_diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "one_esm_monthly_pattern_standard_give_baseline_discount_diagnostic_not_paired_replacement_scc",
        "definition": "one-ESM monthly precipitation-pattern maize marginal damage differences discounted with the deterministic standard GIVE baseline consumption path",
        "discounting": {"emission_year": 2020, "last_year": 2300, "rff_sample_id": 6546, "formula": "(CPC_2020/CPC_t)^eta / (1+prtp)^(t-2020)", "rates": [{"label": label, "prtp": prtp, "eta": eta} for label, prtp, eta in DISCOUNT_RATES], "molecular_conversion_C_to_CO2": MOLECULAR_C_TO_CO2, "pricelevel_2005_to_2020": PRICE_2005_TO_2020},
        "currency": {"source_to_usd2005_scalar": price_scalar, "approximation_disclosure": registry["approximation_disclosure"]},
        "sources": {"damage_paths": {"path": str(args.damage_paths), "sha256": digest(args.damage_paths), "receipt": str(args.damage_receipt), "receipt_sha256": digest(args.damage_receipt)}, "give_cpc": {"path": str(args.cpc), "sha256": digest(args.cpc), "job_receipt": str(args.cpc_job_receipt), "job_receipt_sha256": digest(args.cpc_job_receipt)}, "price_registry": {"path": str(args.price_registry), "sha256": digest(args.price_registry)}},
        "support": {"output_rows": len(output), "annual_years_per_path": 281, "climate_models": 1, "adaptation_cases": 3, "positive_pulses": 3, "discount_schedules": 4},
        "validation": {"maximum_cpc_identity_error": cpc_error, "maximum_net_consumption_identity_error_billion_usd2005": net_error, "maximum_relative_small_pulse_scc_disagreement": convergence, "pulse_convergence_tolerance": CONVERGENCE_RELATIVE_TOLERANCE},
        "central_2pct_smallest_pulse_usd2020_per_tco2": central_values,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gates": {"standard_give_baseline_discount_diagnostic": True, "paired_agriculture_levels": False, "agriculture_replacement": False, "give_replacement_scc": False},
        "limitations": ["This is a one-ESM monthly-pattern diagnostic, not a probabilistic precipitation SCC.", "Discount factors come from standard deterministic GIVE retaining MooreAg; no paired agriculture replacement is installed.", "The GDP-wide price conversion approximates the agricultural price concept.", "Only maize and monthly mean precipitation are included; daily drought/extremes and other crops remain omitted.", "The common physical support excludes 1.0% of response value without renormalization, as documented upstream."],
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "central_2pct": central_values, "validation": result["validation"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
