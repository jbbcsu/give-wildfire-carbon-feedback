#!/usr/bin/env python3
"""Build currency-aligned FUND-region marginal damage-difference paths."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_epa_fair_hultgren_quantity_damage_paths import (
    ADAPTATION, PULSES, VALUE, YEAR_CHUNK, adaptation_factors, country_market_damage,
    model_frame, response_coefficients,
)
ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validated_price_registry(path: Path) -> tuple[dict, float]:
    with path.open("rb") as stream:
        registry = tomllib.load(stream)
    require(registry["schema_version"] == 1 and registry["status"] == "registered_GDP_wide_approximation_not_applied", "price registry identity differs")
    require(registry["input_units"] == "constant_2014_2016_USD" and registry["output_units"] == "USD2005", "price units differ")
    require(registry["price_concept_equivalence_claimed"] is False, "price-concept limitation removed")
    expected = {"y2005": 87.504, "y2014": 103.654, "y2015": 104.691, "y2016": 105.740}
    indices = registry["annual_indices"]
    require(all(type(indices.get(key)) is float and indices[key] == value for key, value in expected.items()), "price indices differ")
    reference = ROOT / registry["source_file"]
    require(reference.is_file() and reference.stat().st_size == 165719 and digest(reference) == registry["source_sha256"], "price reference identity differs")
    scalar = indices["y2005"] / np.mean([indices["y2014"], indices["y2015"], indices["y2016"]])
    require(type(registry["central_scalar"]) is float and math.isclose(scalar, registry["central_scalar"], rel_tol=0, abs_tol=1e-15), "price scalar differs")
    return registry, float(scalar)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--damage-paths", type=Path, required=True)
    parser.add_argument("--damage-receipt", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--epa-slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--fund-mapping", type=Path, required=True)
    parser.add_argument("--fund-order", type=Path, required=True)
    parser.add_argument("--price-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    receipt = json.loads(args.damage_receipt.read_text(encoding="utf-8"))
    require(receipt["schema"] == "epa_fair_hultgren_quantity_damage_paths/v1", "damage receipt differs")
    require(receipt["output"]["sha256"] == digest(args.damage_paths), "damage path hash differs")
    require(receipt["sources"]["panel"]["sha256"] == digest(args.panel), "panel hash differs")
    require(receipt["sources"]["epa_slopes"]["sha256"] == digest(args.epa_slopes), "slope hash differs")
    require(receipt["sources"]["fair"]["sha256"] == digest(args.fair), "FAIR hash differs")

    with args.fund_mapping.open(newline="", encoding="utf-8-sig") as stream:
        mapping = {row["ISO3"]: row["fundregion"] for row in csv.DictReader(stream)}
    with args.fund_order.open(newline="", encoding="utf-8") as stream:
        regions = [row["fund_region"] for row in csv.DictReader(stream)]
    require(len(regions) == 16 and len(set(regions)) == 16, "FUND order differs")
    require(set(mapping.values()) <= set(regions), "unknown FUND mapping label")
    region_index = {region: index for index, region in enumerate(regions)}

    registry, scalar = validated_price_registry(args.price_registry)
    require(0 < scalar < 1, "price conversion scalar invalid")

    global_paths = pd.read_parquet(args.damage_paths).set_index(
        ["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]
    )["damage_change_usd_source_price_basis"]
    require(global_paths.index.is_unique, "global path keys differ")
    panel = pd.read_parquet(args.panel)
    slopes = pd.read_csv(args.epa_slopes)
    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301, dtype=np.int32)
    fair_paths = {
        pulse: fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.isin(years)].sort_values("year").difference_k.to_numpy(dtype=np.float64)
        for pulse in PULSES
    }
    tail = receipt["tail_rules"]["published_analogue_p01_p99"]
    lower = float(tail["lower_log_yield_per_gtc"])
    upper = float(tail["upper_log_yield_per_gtc"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    rows_written = 0
    maximum_global_error = 0.0
    represented_countries: set[str] = set()
    represented_regions: set[str] = set()
    try:
        for model in sorted(slopes.source.unique()):
            frame = model_frame(panel, slopes, model)
            first, second = response_coefficients(frame)
            values = frame[VALUE].to_numpy(dtype=np.float64)
            iso = frame.iso3.to_numpy()
            starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
            country_value = np.add.reduceat(values, starts)
            countries = iso[starts]
            missing = sorted(set(countries) - set(mapping))
            require(not missing, f"unmapped represented countries for {model}: {missing}")
            country_regions = np.asarray([region_index[mapping[country]] for country in countries], dtype=np.int16)
            represented_countries.update(str(country) for country in countries)
            represented_regions.update(mapping[str(country)] for country in countries)
            for pulse, delta_temperature in fair_paths.items():
                for start in range(0, len(years), YEAR_CHUNK):
                    stop = min(start + YEAR_CHUNK, len(years))
                    chunk_years = years[start:stop]
                    temperature = delta_temperature[start:stop]
                    raw = first[:, None] * temperature[None, :] + second[:, None] * np.square(temperature[None, :])
                    tail_inputs = {
                        "uncapped": raw,
                        "published_analogue_p01_p99": np.zeros_like(raw) if pulse == 0.0 else np.clip(raw / pulse, lower, upper) * pulse,
                    }
                    batch_records = []
                    for tail_rule, response in tail_inputs.items():
                        for scenario in ADAPTATION:
                            factors = adaptation_factors(chunk_years, scenario)
                            adapted = np.where(response < 0.0, response * factors[None, :], response)
                            np.exp(adapted, out=adapted)
                            adapted *= values[:, None]
                            country_output = np.add.reduceat(adapted, starts, axis=0)
                            ratios = country_output / country_value[:, None]
                            country_damage = country_market_damage(country_value, ratios)
                            regional = np.zeros((len(regions), len(chunk_years)), dtype=np.float64)
                            np.add.at(regional, country_regions, country_damage)
                            for column, year in enumerate(chunk_years):
                                key = (model, int(year), pulse, scenario, tail_rule)
                                global_value = float(global_paths.loc[key])
                                reconstructed = float(regional[:, column].sum())
                                maximum_global_error = max(maximum_global_error, abs(global_value - reconstructed))
                                for region_position, region in enumerate(regions):
                                    source_value = float(regional[region_position, column])
                                    batch_records.append({
                                        "climate_model": model,
                                        "year": int(year),
                                        "pulse_size_gtc": pulse,
                                        "adaptation": scenario,
                                        "tail_rule": tail_rule,
                                        "fund_region": region,
                                        "marginal_damage_difference_usd_source_price_basis": source_value,
                                        "marginal_damage_difference_billion_usd2005": source_value * scalar / 1e9,
                                    })
                    table = pa.Table.from_pandas(pd.DataFrame(batch_records), preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(args.output, table.schema, compression="zstd")
                    writer.write_table(table)
                    rows_written += len(batch_records)
    finally:
        if writer is not None:
            writer.close()
    require(rows_written == len(global_paths) * len(regions), "regional row count differs")
    require(maximum_global_error <= 2e-3, f"regional/global damage reconciliation differs: {maximum_global_error}")
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds 64 MiB owned-output budget")

    result = {
        "schema": "epa_fair_hultgren_quantity_fund_paths/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "currency_aligned_fund_region_marginal_damage_differences_not_paired_replacement_or_scc",
        "definition": "annual pulse-minus-baseline maize quantity-channel damage differences by GIVE FUND region",
        "sources": {
            "damage_paths": {"path": str(args.damage_paths), "sha256": digest(args.damage_paths), "receipt": str(args.damage_receipt), "receipt_sha256": digest(args.damage_receipt)},
            "panel": {"path": str(args.panel), "sha256": digest(args.panel)},
            "epa_slopes": {"path": str(args.epa_slopes), "sha256": digest(args.epa_slopes)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair)},
            "fund_mapping": {"path": str(args.fund_mapping), "sha256": digest(args.fund_mapping)},
            "fund_order": {"path": str(args.fund_order), "sha256": digest(args.fund_order)},
            "price_registry": {"path": str(args.price_registry), "sha256": digest(args.price_registry), "reference_path": registry["source_file"], "reference_sha256": registry["source_sha256"]},
        },
        "currency": {
            "input": registry["input_units"],
            "output": registry["output_units"],
            "central_scalar": scalar,
            "formula": registry["central_formula"],
            "approximation_disclosure": registry["approximation_disclosure"],
        },
        "support": {
            "rows": rows_written,
            "models": int(global_paths.index.get_level_values("climate_model").nunique()),
            "countries": len(represented_countries),
            "fund_regions": regions,
            "represented_fund_regions": sorted(represented_regions),
            "unmapped_represented_countries": [],
        },
        "validation": {
            "regional_sums_reconciled_to_every_global_path": True,
            "maximum_absolute_global_reconciliation_error_source_usd": maximum_global_error,
            "zero_and_pre_2021_identity_inherited_and_recomputed": True,
        },
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": [
            "These are marginal damage differences, not standalone baseline and pulse agriculture damage levels.",
            "The GDP-wide price conversion is a registered approximation to the agricultural price concept.",
            "A complete paired replacement needs a defensible baseline agriculture damage path; assigning a zero baseline would change GIVE consumption and discounting and is not authorized.",
            "No discounting, emissions normalization, paired GIVE execution, or SCC is performed here.",
        ],
        "claim_gates": {"currency_aligned_marginal_damage_difference": True, "paired_agriculture_levels": False, "agriculture_replacement": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "currency": result["currency"], "validation": result["validation"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
