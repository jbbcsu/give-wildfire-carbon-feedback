#!/usr/bin/env python3
"""Expand the annual quantity bridge across registered market sensitivities."""

from __future__ import annotations

import argparse
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
    ADAPTATION,
    PULSES,
    VALUE,
    YEAR_CHUNK,
    adaptation_factors,
    model_frame,
    response_coefficients,
)

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = ("horizontal_output", "fixed_input_cost")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def damage_from_ratio(
    baseline_value: np.ndarray,
    supply_ratio: np.ndarray,
    supply_elasticity: float,
    demand_elasticity: float,
) -> np.ndarray:
    shift = np.log(supply_ratio)
    change_log_price = -shift / (supply_elasticity + demand_elasticity)
    z = (1.0 - demand_elasticity) * change_log_price
    exprel = np.ones_like(z)
    nonzero = z != 0.0
    exprel[nonzero] = np.expm1(z[nonzero]) / z[nonzero]
    return -baseline_value[:, None] * shift / (1.0 + supply_elasticity) * exprel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--central-paths", type=Path, required=True)
    parser.add_argument("--central-receipt", type=Path, required=True)
    parser.add_argument("--fund-receipt", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "config/welfare_scenario_registry.toml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    central_receipt = json.loads(args.central_receipt.read_text(encoding="utf-8"))
    fund_receipt = json.loads(args.fund_receipt.read_text(encoding="utf-8"))
    registry = tomllib.loads(args.registry.read_text(encoding="utf-8"))
    require(central_receipt["schema"] == "epa_fair_hultgren_quantity_damage_paths/v1", "central receipt differs")
    require(fund_receipt["schema"] == "epa_fair_hultgren_quantity_fund_paths/v1", "FUND receipt differs")
    for path, key in ((args.panel, "panel"), (args.slopes, "epa_slopes"), (args.fair, "fair")):
        require(digest(path) == central_receipt["sources"][key]["sha256"], f"{key} hash differs")
    require(digest(args.central_paths) == central_receipt["output"]["sha256"], "central paths hash differs")
    require(registry["gates"]["deflator_to_USD2005_resolved"], "currency gate unresolved")

    elasticities = []
    for row in registry["elasticity_pairs"]:
        supply = float(row["supply"])
        demand = -float(row["demand_signed"])
        require(supply > 0 and demand > 0, "elasticity sign differs")
        elasticities.append((str(row["id"]), supply, demand, bool(row["central"])))
    require(len(elasticities) == 3 and sum(item[3] for item in elasticities) == 1, "elasticity registry differs")
    central_spec = next(item for item in elasticities if item[3])
    require(central_spec[1:3] == (0.10, 0.04), "central elasticity differs")

    tail = central_receipt["tail_rules"]["published_analogue_p01_p99"]
    lower = float(tail["lower_log_yield_per_gtc"])
    upper = float(tail["upper_log_yield_per_gtc"])
    currency_scalar = float(fund_receipt["currency"]["central_scalar"])
    require(math.isfinite(currency_scalar) and currency_scalar > 0, "currency scalar invalid")

    panel = pd.read_parquet(args.panel)
    slopes = pd.read_csv(args.slopes)
    fair = pd.read_csv(args.fair)
    central = pd.read_parquet(args.central_paths)
    years = np.arange(2020, 2301, dtype=np.int32)
    fair_paths = {
        pulse: fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.isin(years)]
        .sort_values("year").difference_k.to_numpy(dtype=np.float64)
        for pulse in PULSES
    }
    require(all(len(path) == len(years) for path in fair_paths.values()), "FAIR horizon differs")

    keys = ["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]
    expected = len(central) * len(elasticities) * len(MAPPINGS)
    small, next_small = 0.000025, 0.00005
    convergence_state = {
        (elasticity_id, mapping): {"maximum_absolute": 0.0, "scale": 1e-30}
        for elasticity_id, *_ in elasticities for mapping in MAPPINGS
    }
    summary_values: dict[tuple[str, str, str, str], list[float]] = {}
    zero_identity = True
    pre_identity = True
    central_error = 0.0
    central_seen = 0
    row_count = 0
    records: list[dict[str, object]] = []
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    require(not partial.exists(), "stale partial output exists")
    writer: pq.ParquetWriter | None = None

    def flush() -> None:
        nonlocal writer, records
        if not records:
            return
        table = pa.Table.from_pandas(pd.DataFrame.from_records(records), preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(partial, table.schema, compression="zstd")
        writer.write_table(table)
        records = []

    try:
        for model in sorted(slopes.source.unique()):
            frame = model_frame(panel, slopes, model)
            first, second = response_coefficients(frame)
            values = frame[VALUE].to_numpy(dtype=np.float64)
            iso = frame.iso3.to_numpy()
            starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
            country_value = np.add.reduceat(values, starts)
            require(np.all(country_value > 0), f"nonpositive country value: {model}")
            prior = central.loc[central.climate_model.eq(model)]
            prior_lookup = {
                (int(row.year), float(row.pulse_size_gtc), str(row.adaptation), str(row.tail_rule)):
                float(row.damage_change_usd_source_price_basis)
                for row in prior.itertuples(index=False)
            }
            require(len(prior_lookup) == len(prior), f"prior central duplicate: {model}")
            for start in range(0, len(years), YEAR_CHUNK):
                stop = min(start + YEAR_CHUNK, len(years))
                chunk_years = years[start:stop]
                small_cache: dict[tuple[str, str, str, str], np.ndarray] = {}
                for pulse, delta_temperature in fair_paths.items():
                    chunk_temperature = delta_temperature[start:stop]
                    raw = first[:, None] * chunk_temperature[None, :] + second[:, None] * np.square(chunk_temperature[None, :])
                    tail_inputs = {
                        "uncapped": raw,
                        "published_analogue_p01_p99": np.zeros_like(raw)
                        if pulse == 0.0 else np.clip(raw / pulse, lower, upper) * pulse,
                    }
                    for tail_rule, response in tail_inputs.items():
                        for adaptation in ADAPTATION:
                            factor = adaptation_factors(chunk_years, adaptation)
                            adapted = np.where(response < 0.0, response * factor[None, :], response)
                            for elasticity_id, supply, demand, is_central in elasticities:
                                for mapping in MAPPINGS:
                                    exponent = 1.0 if mapping == "horizontal_output" else 1.0 + supply
                                    weighted_output = np.exp(exponent * adapted) * values[:, None]
                                    country_output = np.add.reduceat(weighted_output, starts, axis=0)
                                    ratios = country_output / country_value[:, None]
                                    require(np.isfinite(ratios).all() and np.all(ratios > 0), "invalid supply ratio")
                                    damages = damage_from_ratio(country_value, ratios, supply, demand).sum(axis=0)
                                    cache_key = (adaptation, tail_rule, elasticity_id, mapping)
                                    if pulse == small:
                                        small_cache[cache_key] = damages / small
                                    elif pulse == next_small:
                                        normalized = damages / next_small
                                        prior_normalized = small_cache[cache_key]
                                        state = convergence_state[(elasticity_id, mapping)]
                                        state["maximum_absolute"] = max(state["maximum_absolute"], float(np.max(np.abs(prior_normalized - normalized))))
                                        state["scale"] = max(state["scale"], float(np.max(np.abs(prior_normalized))), float(np.max(np.abs(normalized))))
                                    for index, year in enumerate(chunk_years):
                                        source_damage = float(damages[index])
                                        zero_identity = zero_identity and (pulse != 0.0 or source_damage == 0.0)
                                        pre_identity = pre_identity and (year > 2020 or source_damage == 0.0)
                                        if is_central and mapping == "horizontal_output":
                                            prior_key = (int(year), float(pulse), adaptation, tail_rule)
                                            central_error = max(central_error, abs(prior_lookup.pop(prior_key) - source_damage))
                                            central_seen += 1
                                        if pulse == small and year > 2020:
                                            summary_values.setdefault(cache_key, []).append(source_damage)
                                        records.append({
                                            "climate_model": model,
                                            "year": int(year),
                                            "pulse_size_gtc": pulse,
                                            "adaptation": adaptation,
                                            "tail_rule": tail_rule,
                                            "elasticity_id": elasticity_id,
                                            "supply_elasticity": supply,
                                            "demand_elasticity_magnitude": demand,
                                            "central_elasticity": is_central,
                                            "yield_to_supply_mapping": mapping,
                                            "damage_change_usd_source_price_basis": source_damage,
                                            "damage_change_billion_usd2005": source_damage * currency_scalar / 1e9,
                                            "minimum_country_supply_ratio": float(ratios[:, index].min()),
                                            "maximum_country_supply_ratio": float(ratios[:, index].max()),
                                        })
                                        row_count += 1
                                    if len(records) >= 25_000:
                                        flush()
                require(len(small_cache) == len(elasticities) * len(MAPPINGS) * len(ADAPTATION) * 2, "convergence cache differs")
            require(not prior_lookup, f"prior central rows unvisited: {model}")
        flush()
    except BaseException:
        if writer is not None:
            writer.close()
        partial.unlink(missing_ok=True)
        raise
    require(writer is not None, "no output rows")
    writer.close()
    require(row_count == expected, "output row count differs")
    require(central_seen == len(central) and central_error <= 1e-5, "central path reproduction failed")
    require(zero_identity, "zero-pulse identity failed")
    require(pre_identity, "pre-2021 identity failed")

    convergence = []
    for (elasticity_id, mapping), state in sorted(convergence_state.items()):
        convergence.append({
            "elasticity_id": elasticity_id,
            "yield_to_supply_mapping": mapping,
            "maximum_relative_normalized_damage_disagreement": state["maximum_absolute"] / state["scale"],
        })
    maximum_convergence = max(item["maximum_relative_normalized_damage_disagreement"] for item in convergence)
    require(maximum_convergence <= 2e-4, "market sensitivity shrinking-pulse convergence failed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    partial.replace(args.output)
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds owned-output limit")
    summaries = []
    for (adaptation, tail_rule, elasticity_id, mapping), values_for_summary in sorted(summary_values.items()):
        array = np.asarray(values_for_summary, dtype=np.float64)
        summaries.append({
            "adaptation": adaptation,
            "tail_rule": tail_rule,
            "elasticity_id": elasticity_id,
            "yield_to_supply_mapping": mapping,
            "mean": float(array.mean()),
            "median": float(np.median(array)),
            "min": float(array.min()),
            "max": float(array.max()),
        })
    receipt = {
        "schema": "epa_fair_hultgren_quantity_market_sensitivities/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "registered_national_market_sensitivities_not_paired_replacement_or_scc",
        "definition": "annual global maize precipitation-quantity marginal damage differences under registered national-market elasticities and supply mappings",
        "market": {
            "geography": "separate fully anticipated national maize markets",
            "elasticities": [{"id": i, "supply": s, "demand_magnitude": d, "central": c} for i, s, d, c in elasticities],
            "yield_to_supply_mappings": list(MAPPINGS),
        },
        "currency": fund_receipt["currency"],
        "sources": {
            "panel": {"path": str(args.panel), "sha256": digest(args.panel)},
            "slopes": {"path": str(args.slopes), "sha256": digest(args.slopes)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair)},
            "central_paths": {"path": str(args.central_paths), "sha256": digest(args.central_paths), "receipt": str(args.central_receipt), "receipt_sha256": digest(args.central_receipt)},
            "fund_paths_receipt": {"path": str(args.fund_receipt), "sha256": digest(args.fund_receipt)},
            "registry": {"path": str(args.registry), "sha256": digest(args.registry)},
        },
        "support": {"rows": row_count, "models": int(slopes.source.nunique()), "years": [2020, 2300], "pulses_gtc": list(PULSES), "adaptation_cases": list(ADAPTATION), "tail_rules": ["uncapped", "published_analogue_p01_p99"]},
        "validation": {
            "central_path_maximum_absolute_reproduction_error_source_usd": central_error,
            "zero_pulse_identity": True,
            "pre_2021_identity": True,
            "convergence_relative_tolerance": 2e-4,
            "maximum_relative_normalized_damage_disagreement": maximum_convergence,
            "convergence_by_market_specification": convergence,
        },
        "smallest_pulse_summaries_source_usd": summaries,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gates": {"market_sensitivity": True, "paired_agriculture_levels": False, "agriculture_replacement": False, "scc": False},
        "limitations": [
            "These are marginal differences, not paired baseline and pulse agriculture damage levels.",
            "The calculation remains the annual rainfall-quantity maize channel only.",
            "No trade, storage, other crops, adaptation costs, or future maize-value growth is represented.",
            "The GDP-wide currency rebase is an approximation to the source agricultural price concept.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "support": receipt["support"], "validation": receipt["validation"], "output": receipt["output"]}, indent=2))


if __name__ == "__main__":
    main()
