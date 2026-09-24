#!/usr/bin/env python3
"""Discount quantity-channel marginal damages on the standard GIVE baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
GIVE_ROOT = ROOT.parent / "paper-2022-scc-give-zenodo"
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
    parser.add_argument("--market-receipt", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--julia-script", type=Path, required=True)
    parser.add_argument("--julia-job-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    market_receipt = json.loads(args.market_receipt.read_text(encoding="utf-8"))
    require(market_receipt["schema"] == "epa_fair_hultgren_quantity_market_sensitivities/v1", "market receipt differs")
    market_path = Path(market_receipt["output"]["path"])
    require(digest(market_path) == market_receipt["output"]["sha256"], "market output hash differs")
    julia_job = json.loads(args.julia_job_receipt.read_text(encoding="utf-8"))
    require(julia_job["status"] == "completed" and julia_job["returncode"] == 0, "GIVE export job failed")

    cpc = pd.read_csv(args.cpc)
    require(list(cpc.year) == list(range(2020, 2301)), "GIVE CPC years differ")
    require(cpc.rff_sample_id.nunique() == 1 and int(cpc.rff_sample_id.iloc[0]) == 6546, "RFF sample differs")
    expected_cpc = cpc.net_consumption_billion_2005usd.to_numpy() * 1e3 / cpc.global_population_million.to_numpy()
    cpc_error = float(np.max(np.abs(expected_cpc - cpc.net_cpc_2005usd_per_person.to_numpy())))
    expected_net = cpc.global_gdp_billion_2005usd.to_numpy() - cpc.total_damage_2005usd.to_numpy() / 1e9
    net_error = float(np.max(np.abs(expected_net - cpc.net_consumption_billion_2005usd.to_numpy())))
    require(cpc_error <= 1e-9 and net_error <= 1e-8, "exported GIVE consumption identity differs")
    require((cpc.net_cpc_2005usd_per_person > 0).all(), "nonpositive CPC")

    base_cpc = float(cpc.loc[cpc.year.eq(2020), "net_cpc_2005usd_per_person"].iloc[0])
    discount = {}
    for label, prtp, eta in DISCOUNT_RATES:
        discount[label] = {
            int(row.year): (base_cpc / float(row.net_cpc_2005usd_per_person)) ** eta
            / (1.0 + prtp) ** (int(row.year) - 2020)
            for row in cpc.itertuples(index=False)
        }
        require(discount[label][2020] == 1.0, f"discount identity differs: {label}")

    group_columns = [
        "climate_model", "pulse_size_gtc", "adaptation", "tail_rule",
        "elasticity_id", "yield_to_supply_mapping",
    ]
    sums: dict[tuple[object, ...], np.ndarray] = defaultdict(lambda: np.zeros(len(DISCOUNT_RATES), dtype=np.float64))
    counts: dict[tuple[object, ...], int] = defaultdict(int)
    columns = group_columns + ["year", "damage_change_billion_usd2005"]
    source_rows = 0
    positive_rows = 0
    for batch in pq.ParquetFile(market_path).iter_batches(batch_size=65_536, columns=columns):
        frame = batch.to_pandas()
        source_rows += len(frame)
        frame = frame.loc[frame.pulse_size_gtc.gt(0.0)]
        positive_rows += len(frame)
        for row in frame.itertuples(index=False):
            key = tuple(getattr(row, column) for column in group_columns)
            pulse = float(row.pulse_size_gtc)
            damage = float(row.damage_change_billion_usd2005) * MOLECULAR_C_TO_CO2 / pulse
            for index, (label, _, _) in enumerate(DISCOUNT_RATES):
                sums[key][index] += discount[label][int(row.year)] * damage
            counts[key] += 1
    require(source_rows == market_receipt["support"]["rows"], "source row count differs")
    require(set(counts.values()) == {281}, "annual SCC path coverage differs")

    records = []
    for key in sorted(sums):
        for index, (label, prtp, eta) in enumerate(DISCOUNT_RATES):
            scc_2005 = float(sums[key][index])
            record = dict(zip(group_columns, key, strict=True))
            records.append({
                **record,
                "discount_rate_label": label,
                "prtp": prtp,
                "eta": eta,
                "partial_scc_diagnostic_usd2005_per_tco2": scc_2005,
                "partial_scc_diagnostic_usd2020_per_tco2": scc_2005 * PRICE_2005_TO_2020,
                "annual_year_count": counts[key],
            })
    output = pd.DataFrame(records).sort_values(group_columns + ["discount_rate_label"]).reset_index(drop=True)
    require(len(output) == 26 * 3 * 3 * 2 * 3 * 2 * 4, "diagnostic row count differs")
    require(not output.duplicated(group_columns + ["discount_rate_label"]).any(), "diagnostic key duplicates")

    convergence_keys = [column for column in group_columns if column != "pulse_size_gtc"] + ["discount_rate_label"]
    small = output.loc[output.pulse_size_gtc.eq(0.000025), convergence_keys + ["partial_scc_diagnostic_usd2005_per_tco2"]]
    next_small = output.loc[output.pulse_size_gtc.eq(0.00005), convergence_keys + ["partial_scc_diagnostic_usd2005_per_tco2"]]
    joined = small.merge(next_small, on=convergence_keys, suffixes=("_small", "_next"), validate="one_to_one")
    x = joined.partial_scc_diagnostic_usd2005_per_tco2_small.to_numpy()
    y = joined.partial_scc_diagnostic_usd2005_per_tco2_next.to_numpy()
    convergence_absolute = float(np.max(np.abs(x - y)))
    convergence_scale = max(float(np.max(np.abs(x))), float(np.max(np.abs(y))), 1e-30)
    convergence_relative = convergence_absolute / convergence_scale
    require(convergence_relative <= 2e-4, "partial SCC pulse convergence failed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    summaries = (
        output.loc[output.pulse_size_gtc.eq(0.000025)]
        .groupby(["adaptation", "tail_rule", "elasticity_id", "yield_to_supply_mapping", "discount_rate_label"])
        .partial_scc_diagnostic_usd2020_per_tco2.agg(["mean", "median", "min", "max"])
        .reset_index().to_dict("records")
    )
    source_files = {
        "give_scc_source": GIVE_ROOT / "packages/MimiGIVE/src/scc.jl",
        "give_net_consumption_source": GIVE_ROOT / "packages/MimiGIVE/src/components/netconsumption.jl",
        "give_main_model_source": GIVE_ROOT / "packages/MimiGIVE/src/main_model.jl",
        "give_discount_rate_source": GIVE_ROOT / "src/discount_rates.jl",
        "give_manifest": GIVE_ROOT / "Manifest.toml",
    }
    result = {
        "schema": "epa_fair_hultgren_quantity_partial_scc_diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "standard_give_baseline_discount_diagnostic_not_paired_replacement_scc",
        "definition": "annual maize precipitation-quantity marginal damage differences discounted with the deterministic standard GIVE baseline consumption path and normalized to dollars per tonne CO2",
        "discounting": {
            "emission_year": 2020,
            "last_year": 2300,
            "rff_sample_id": 6546,
            "formula": "(CPC_2020/CPC_t)^eta / (1+prtp)^(t-2020)",
            "rates": [{"label": label, "prtp": prtp, "eta": eta} for label, prtp, eta in DISCOUNT_RATES],
            "molecular_conversion_C_to_CO2": MOLECULAR_C_TO_CO2,
            "pricelevel_2005_to_2020": PRICE_2005_TO_2020,
        },
        "sources": {
            "market_paths": {"path": str(market_path), "sha256": digest(market_path), "receipt": str(args.market_receipt), "receipt_sha256": digest(args.market_receipt)},
            "give_cpc": {"path": str(args.cpc), "sha256": digest(args.cpc), "export_script": str(args.julia_script), "export_script_sha256": digest(args.julia_script), "job_receipt": str(args.julia_job_receipt), "job_receipt_sha256": digest(args.julia_job_receipt)},
            **{name: {"path": str(path), "sha256": digest(path)} for name, path in source_files.items()},
        },
        "support": {"source_rows": source_rows, "positive_pulse_rows": positive_rows, "output_rows": len(output), "annual_years_per_path": 281, "climate_models": 26},
        "validation": {"maximum_cpc_identity_error": cpc_error, "maximum_net_consumption_identity_error_billion_usd2005": net_error, "maximum_relative_small_pulse_scc_disagreement": convergence_relative, "pulse_convergence_tolerance": 2e-4},
        "smallest_pulse_usd2020_summaries": summaries,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gates": {"standard_give_baseline_discount_diagnostic": True, "paired_agriculture_levels": False, "agriculture_replacement": False, "give_replacement_scc": False},
        "limitations": [
            "Discount factors come from the standard deterministic GIVE baseline, which retains MooreAg; the precipitation module is not installed as its replacement.",
            "The diagnostic excludes feedback of alternative agriculture baseline damage levels on consumption and discount factors.",
            "Only the maize annual-rainfall-quantity channel is included; timing, drought, temperature, other crops, adaptation costs, trade, and storage remain excluded.",
            "This deterministic diagnostic does not include GIVE socioeconomic, climate, damage, or discounting uncertainty draws.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "validation": result["validation"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
