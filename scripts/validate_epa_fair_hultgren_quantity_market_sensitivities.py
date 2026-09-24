#!/usr/bin/env python3
"""Independently stream-audit the registered quantity-market sensitivities."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PULSES = (0.0, 0.000025, 0.00005, 0.0001)
TAILS = ("uncapped", "published_analogue_p01_p99")
ADAPTATIONS = ("fixed", "trend", "upper")
MAPPINGS = ("horizontal_output", "fixed_input_cost")
YEAR_CHUNK = 16


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def expected_rows(models: list[str], elasticities: list[tuple[str, float, float, bool]]):
    years = list(range(2020, 2301))
    for model in models:
        for start in range(0, len(years), YEAR_CHUNK):
            chunk = years[start:start + YEAR_CHUNK]
            for pulse in PULSES:
                for tail in TAILS:
                    for adaptation in ADAPTATIONS:
                        for elasticity_id, supply, demand, central in elasticities:
                            for mapping in MAPPINGS:
                                for year in chunk:
                                    yield model, year, pulse, adaptation, tail, elasticity_id, supply, demand, central, mapping


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--central-paths", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "config/welfare_scenario_registry.toml")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(receipt["schema"] == "epa_fair_hultgren_quantity_market_sensitivities/v1", "receipt schema differs")
    source = Path(receipt["output"]["path"])
    require(source.exists() and digest(source) == receipt["output"]["sha256"], "sensitivity output hash differs")
    require(digest(args.central_paths) == receipt["sources"]["central_paths"]["sha256"], "central path hash differs")
    registry = tomllib.loads(args.registry.read_text(encoding="utf-8"))
    require(digest(args.registry) == receipt["sources"]["registry"]["sha256"], "registry hash differs")
    elasticities = [
        (str(row["id"]), float(row["supply"]), -float(row["demand_signed"]), bool(row["central"]))
        for row in registry["elasticity_pairs"]
    ]

    central_table = pq.read_table(args.central_paths)
    central = central_table.to_pandas()
    models = sorted(central.climate_model.unique())
    central_lookup = {
        (str(row.climate_model), int(row.year), float(row.pulse_size_gtc), str(row.adaptation), str(row.tail_rule)):
        float(row.damage_change_usd_source_price_basis)
        for row in central.itertuples(index=False)
    }
    require(len(central_lookup) == len(central), "central path keys duplicate")

    expected = expected_rows(models, elasticities)
    scalar = float(receipt["currency"]["central_scalar"])
    small_cache: dict[tuple[object, ...], float] = {}
    convergence = {(item[0], mapping): {"absolute": 0.0, "scale": 1e-30} for item in elasticities for mapping in MAPPINGS}
    central_error = 0.0
    currency_error = 0.0
    zero_identity = True
    pre_identity = True
    rows = 0
    columns = [
        "climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule",
        "elasticity_id", "supply_elasticity", "demand_elasticity_magnitude",
        "central_elasticity", "yield_to_supply_mapping",
        "damage_change_usd_source_price_basis", "damage_change_billion_usd2005",
        "minimum_country_supply_ratio", "maximum_country_supply_ratio",
    ]
    for batch in pq.ParquetFile(source).iter_batches(batch_size=65_536, columns=columns):
        frame = batch.to_pandas()
        for row in frame.itertuples(index=False):
            wanted = next(expected, None)
            require(wanted is not None, "more rows than expected")
            observed = (
                str(row.climate_model), int(row.year), float(row.pulse_size_gtc),
                str(row.adaptation), str(row.tail_rule), str(row.elasticity_id),
                float(row.supply_elasticity), float(row.demand_elasticity_magnitude),
                bool(row.central_elasticity), str(row.yield_to_supply_mapping),
            )
            require(observed == wanted, f"ordered key product differs at row {rows}")
            damage = float(row.damage_change_usd_source_price_basis)
            converted = float(row.damage_change_billion_usd2005)
            require(all(math.isfinite(value) for value in (damage, converted, row.minimum_country_supply_ratio, row.maximum_country_supply_ratio)), "nonfinite value")
            require(0 < row.minimum_country_supply_ratio <= row.maximum_country_supply_ratio, "supply-ratio bounds invalid")
            currency_error = max(currency_error, abs(converted - damage * scalar / 1e9))
            zero_identity = zero_identity and (row.pulse_size_gtc != 0.0 or damage == 0.0)
            pre_identity = pre_identity and (row.year > 2020 or damage == 0.0)
            if row.central_elasticity and row.yield_to_supply_mapping == "horizontal_output":
                key = (row.climate_model, int(row.year), float(row.pulse_size_gtc), row.adaptation, row.tail_rule)
                central_error = max(central_error, abs(central_lookup.pop(key) - damage))
            cache_key = (
                row.climate_model, int(row.year), row.adaptation, row.tail_rule,
                row.elasticity_id, row.yield_to_supply_mapping,
            )
            spec = (row.elasticity_id, row.yield_to_supply_mapping)
            if row.pulse_size_gtc == 0.000025:
                small_cache[cache_key] = damage / 0.000025
            elif row.pulse_size_gtc == 0.00005:
                first = small_cache.pop(cache_key)
                second = damage / 0.00005
                convergence[spec]["absolute"] = max(convergence[spec]["absolute"], abs(first - second))
                convergence[spec]["scale"] = max(convergence[spec]["scale"], abs(first), abs(second))
            rows += 1

    require(next(expected, None) is None, "fewer rows than expected")
    require(not central_lookup and not small_cache, "validation caches did not close")
    require(rows == receipt["support"]["rows"], "row count differs")
    require(zero_identity and pre_identity, "identity check failed")
    require(central_error == 0.0 and currency_error == 0.0, "central or currency arithmetic differs")
    convergence_rows = [
        {"elasticity_id": key[0], "yield_to_supply_mapping": key[1],
         "maximum_relative_normalized_damage_disagreement": state["absolute"] / state["scale"]}
        for key, state in sorted(convergence.items())
    ]
    maximum_convergence = max(row["maximum_relative_normalized_damage_disagreement"] for row in convergence_rows)
    require(maximum_convergence <= receipt["validation"]["convergence_relative_tolerance"], "convergence gate failed")

    result = {
        "schema": "epa_fair_hultgren_quantity_market_sensitivities_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "scope": "Independent streaming audit of the full ordered support, identities, currency arithmetic, central reproduction, and shrinking-pulse convergence.",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "streamed_rows": rows,
            "full_ordered_key_product": True,
            "zero_pulse_identity": zero_identity,
            "pre_2021_identity": pre_identity,
            "maximum_absolute_currency_error_billion_usd2005": currency_error,
            "maximum_absolute_central_reproduction_error_source_usd": central_error,
            "maximum_relative_normalized_damage_disagreement": maximum_convergence,
            "convergence_by_market_specification": convergence_rows,
        },
        "interpretation": "Market-sensitivity validation only; paired agriculture levels, replacement accounting, discounting, and SCC remain closed.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    main()
