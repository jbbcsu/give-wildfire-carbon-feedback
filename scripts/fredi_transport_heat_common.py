#!/usr/bin/env python3
"""Bounded, fail-closed FrEDI road/rail heat-interface utilities."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import resource
import sys
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 40

REQUIRED_COMPONENT_GATES = {
    "road_repair",
    "road_user",
    "rail_replacement",
    "rail_delay",
}
EXPECTED_AGGREGATES = {"Roads", "Rail"}


class ContractError(RuntimeError):
    """Raised when a pinned-source or scientific-scope contract fails."""


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def peak_rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return value / divisor


def validate_contract(project_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    allowed = set(config["scope"]["allowed_released_aggregates"])
    if allowed != EXPECTED_AGGREGATES:
        raise ContractError(f"released aggregates must be exactly {sorted(EXPECTED_AGGREGATES)}")
    gates = config.get("component_gates", [])
    endpoints = {row.get("endpoint") for row in gates}
    if endpoints != REQUIRED_COMPONENT_GATES or any(
        row.get("available_in_public_v4_1_1_runtime") is not False for row in gates
    ):
        raise ContractError("all four component endpoints must remain explicit and unavailable")
    if config["claim_status"] != {
        "deterministic_interface_smoke_test": "open",
        "component_resolved_transport": "closed",
        "matched_GIVE_pulse": "closed",
        "global_extrapolation": "prohibited",
        "SCC": "closed",
    }:
        raise ContractError("claim gates differ from the frozen fail-closed contract")
    if config["scope"]["model_type"] != "GCM":
        raise ContractError("only GCM temperature surfaces are authorized")
    if Decimal(str(config["smoke_test"]["driver_conus_degC_rel1995"])) != Decimal("1.5"):
        raise ContractError("this audit is frozen to the 1.5 C interpolation sentinel")
    if config["smoke_test"]["economic_year"] != 2020:
        raise ContractError("this audit is frozen to the 2020 scalar sentinel")

    manifest_path = project_root / config["source_manifest"]
    manifest = read_json(manifest_path)
    alignment_path = project_root / config["alignment_audit"]
    alignment = read_json(alignment_path)
    if alignment.get("status") != "PASS":
        raise ContractError("embedded-v4.1.1 transport alignment audit did not pass")
    tolerance = Decimal(str(alignment.get("tolerance")))
    if tolerance > Decimal("1e-12") or any(
        Decimal(str(row["max_abs_difference"])) > tolerance
        for row in alignment.get("comparisons", [])
    ):
        raise ContractError("embedded-v4.1.1 transport alignment exceeds tolerance")
    for entry in manifest["files"]:
        raw_path = entry.get("raw_path")
        if raw_path is None:
            if entry.get("vendored") is not False:
                raise ContractError(f"non-vendored entry lacks explicit vendored=false: {entry['path']}")
            continue
        path = project_root / raw_path
        if not path.is_file():
            raise ContractError(f"missing pinned source: {raw_path}")
        if path.stat().st_size != entry["bytes"]:
            raise ContractError(f"byte-size mismatch: {raw_path}")
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise ContractError(f"SHA-256 mismatch: {raw_path}")
    return manifest


def _csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _finite_decimal(value: str, label: str) -> Decimal:
    try:
        number = Decimal(value)
    except Exception as exc:
        raise ContractError(f"non-numeric {label}: {value!r}") from exc
    if not number.is_finite():
        raise ContractError(f"non-finite {label}: {value!r}")
    return number


def _load_scaled(
    path: Path,
    aggregate: str,
    config: dict[str, Any],
) -> tuple[dict[tuple[str, str, str, int], Decimal], set[str], dict[str, str]]:
    expected = config["expected_source_support"]
    models = set(config["smoke_test"]["models"])
    variants = set(config["smoke_test"]["variants"])
    values: dict[tuple[str, str, str, int], Decimal] = {}
    states: set[str] = set()
    state_names: dict[str, str] = {}
    bins: Counter[str] = Counter()
    rows = 0
    for row in _csv_rows(path):
        rows += 1
        if row["sector"] != aggregate:
            raise ContractError(f"unexpected sector in {path.name}: {row['sector']}")
        if row["impactYear"] != expected["impact_year_literal"]:
            raise ContractError(f"component-like impactYear appeared in {path.name}")
        if row["impactType"] != expected["impact_type_literal"]:
            raise ContractError(f"component-like impactType appeared in {path.name}")
        if row["model"] not in models or row["variant"] not in variants:
            raise ContractError(f"unexpected model/variant in {path.name}")
        try:
            model_bin = int(row["modelUnitValue"])
        except ValueError as exc:
            raise ContractError(f"non-integer temperature bin in {path.name}") from exc
        if model_bin not in range(1, 7):
            raise ContractError(f"temperature bin outside 1..6 in {path.name}")
        bins[str(model_bin)] += 1
        postal = row["postal"]
        if not postal or len(postal) != 2:
            raise ContractError(f"invalid postal code in {path.name}")
        states.add(postal)
        old_name = state_names.setdefault(postal, row["state"])
        if old_name != row["state"]:
            raise ContractError(f"inconsistent state name for {postal}")
        number = _finite_decimal(row["value"], f"{aggregate} scaled value")
        if model_bin in (1, 2):
            key = (postal, row["model"], row["variant"], model_bin)
            if key in values:
                raise ContractError(f"duplicate interpolation key: {key}")
            values[key] = number
    if rows != expected["scaled_rows_per_aggregate"]:
        raise ContractError(f"unexpected {aggregate} row count: {rows}")
    if dict(sorted(bins.items())) != expected["scaled_rows_by_bin"]:
        raise ContractError(f"unexpected {aggregate} temperature-bin support: {dict(bins)}")
    if len(states) != config["scope"]["expected_postal_count"]:
        raise ContractError(f"unexpected {aggregate} state/DC count: {len(states)}")
    expected_keys = len(states) * len(models) * len(variants) * 2
    if len(values) != expected_keys:
        raise ContractError(f"incomplete 1/2 C support in {aggregate}")
    return values, states, state_names


def _load_miles(
    path: Path,
    scalar_name: str,
    config: dict[str, Any],
) -> tuple[dict[str, Decimal], set[str]]:
    expected = config["expected_source_support"]
    by_state: dict[str, dict[int, Decimal]] = {}
    rows = 0
    for row in _csv_rows(path):
        rows += 1
        if row["scalarName"] != scalar_name:
            raise ContractError(f"unexpected scalar name in {path.name}")
        year = int(row["year"])
        if year not in expected["physical_miles_years"]:
            raise ContractError(f"unexpected miles year in {path.name}: {year}")
        by_state.setdefault(row["postal"], {})[year] = _finite_decimal(
            row["value"], f"{scalar_name} value"
        )
    if rows != expected["physical_miles_rows_per_aggregate"]:
        raise ContractError(f"unexpected rows in {path.name}: {rows}")
    if len(by_state) != config["scope"]["expected_postal_count"]:
        raise ContractError(f"unexpected state/DC count in {path.name}")
    output: dict[str, Decimal] = {}
    years = set(expected["physical_miles_years"])
    for postal, observations in by_state.items():
        if set(observations) != years:
            raise ContractError(f"missing miles endpoint for {postal}")
        if len(set(observations.values())) != 1:
            raise ContractError(f"miles endpoints are not constant for {postal}")
        output[postal] = observations[min(years)]
    return output, set(by_state)


def _load_road_adjustment(
    path: Path,
    variant: str,
    year: int,
    config: dict[str, Any],
) -> tuple[dict[str, Decimal], set[str]]:
    expected = config["expected_source_support"]
    target: dict[str, Decimal] = {}
    state_years: dict[str, set[int]] = {}
    rows = 0
    scalar_name = f"road_miles_and_pop_{variant}"
    for row in _csv_rows(path):
        rows += 1
        if row["scalarName"] != scalar_name:
            raise ContractError(f"unexpected scalar name in {path.name}")
        row_year = int(row["year"])
        if not expected["road_adjustment_year_min"] <= row_year <= expected["road_adjustment_year_max"]:
            raise ContractError(f"road adjustment year outside frozen support in {path.name}")
        state_years.setdefault(row["postal"], set()).add(row_year)
        number = _finite_decimal(row["value"], f"{scalar_name} value")
        if row_year == year:
            if row["postal"] in target:
                raise ContractError(f"duplicate {year} road adjustment for {row['postal']}")
            target[row["postal"]] = number
    if rows != expected["road_adjustment_rows_per_variant"]:
        raise ContractError(f"unexpected rows in {path.name}: {rows}")
    required_years = set(range(expected["road_adjustment_year_min"], expected["road_adjustment_year_max"] + 1))
    if len(state_years) != config["scope"]["expected_postal_count"]:
        raise ContractError(f"unexpected state/DC count in {path.name}")
    if any(years != required_years for years in state_years.values()):
        raise ContractError(f"nonannual road adjustment support in {path.name}")
    if set(target) != set(state_years):
        raise ContractError(f"missing {year} road adjustment in {path.name}")
    return target, set(state_years)


def _load_rail_growth(path: Path, year: int, config: dict[str, Any]) -> Decimal:
    observed_years: list[int] = []
    target: Decimal | None = None
    for row in _csv_rows(path):
        if row["scalarName"] != "rail_growth_factor" or row["state"] != "National Total":
            raise ContractError(f"unexpected rail growth metadata in {path.name}")
        row_year = int(row["year"])
        observed_years.append(row_year)
        number = _finite_decimal(row["value"], "rail growth factor")
        if row_year == year:
            target = number
    if observed_years != config["expected_source_support"]["rail_growth_years"]:
        raise ContractError("rail-growth years differ from frozen support")
    if target is None:
        raise ContractError(f"rail growth factor lacks target year {year}")
    return target


def linear_interpolate(v1: Decimal, v2: Decimal, x: Decimal) -> Decimal:
    if not Decimal("1") <= x <= Decimal("2"):
        raise ContractError("smoke interpolation is restricted to [1,2] C")
    return v1 + (x - Decimal("1")) * (v2 - v1)


def compute_smoke(project_root: Path, config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    validate_contract(project_root, config)
    raw = project_root / "data/raw/fredi_data/inst/extdata/fredi"
    temp = Decimal(str(config["smoke_test"]["driver_conus_degC_rel1995"]))
    year = config["smoke_test"]["economic_year"]
    models = config["smoke_test"]["models"]
    variants = config["smoke_test"]["variants"]

    scaled: dict[str, dict[tuple[str, str, str, int], Decimal]] = {}
    state_sets: list[set[str]] = []
    for aggregate in sorted(EXPECTED_AGGREGATES):
        values, states, _ = _load_scaled(raw / "gcm" / f"{aggregate}_scaledimpacts.csv", aggregate, config)
        scaled[aggregate] = values
        state_sets.append(states)
    road_miles, road_states = _load_miles(
        raw / "scalars/Scalar_physScalar_road_miles.csv", "road_miles", config
    )
    rail_miles, rail_states = _load_miles(
        raw / "scalars/Scalar_physScalar_rail_miles.csv", "rail_miles", config
    )
    state_sets.extend([road_states, rail_states])
    canonical_states = state_sets[0]
    if any(states != canonical_states for states in state_sets[1:]):
        raise ContractError("Roads/Rail response and miles state supports do not align")

    road_adjustments: dict[str, dict[str, Decimal]] = {}
    for variant in variants:
        values, states = _load_road_adjustment(
            raw / "scalars" / f"Scalar_damageAdj_road_miles_and_pop_{variant}.csv",
            variant,
            year,
            config,
        )
        if states != canonical_states:
            raise ContractError(f"road adjustment state support differs for {variant}")
        road_adjustments[variant] = values
    rail_growth = _load_rail_growth(
        raw / "scalars/Scalar_damageAdj_rail_growth_factor.csv", year, config
    )

    output: list[dict[str, str]] = []
    quantizer = Decimal("0.000001")
    for aggregate in sorted(EXPECTED_AGGREGATES):
        for variant in variants:
            for model in models:
                total = Decimal("0")
                for postal in sorted(canonical_states):
                    value = linear_interpolate(
                        scaled[aggregate][(postal, model, variant, 1)],
                        scaled[aggregate][(postal, model, variant, 2)],
                        temp,
                    )
                    if aggregate == "Roads":
                        scalar = road_miles[postal] * road_adjustments[variant][postal]
                    else:
                        scalar = rail_miles[postal] * rail_growth
                    total += value * scalar
                output.append(
                    {
                        "scope": "CONUS_48_plus_DC",
                        "model_type": "GCM",
                        "driver_conus_degC_rel1995": str(temp),
                        "economic_year": str(year),
                        "gcm": model,
                        "variant": variant,
                        "released_aggregate": aggregate,
                        "annual_impact_2015usd_per_year": format(total.quantize(quantizer), "f"),
                        "component_resolution": "combined_public_surface",
                    }
                )
    diagnostics = {
        "state_dc_count": len(canonical_states),
        "gcm_count": len(models),
        "variant_count": len(variants),
        "released_aggregate_count": len(EXPECTED_AGGREGATES),
        "output_row_count": len(output),
    }
    return output, diagnostics


OUTPUT_FIELDS = [
    "scope",
    "model_type",
    "driver_conus_degC_rel1995",
    "economic_year",
    "gcm",
    "variant",
    "released_aggregate",
    "annual_impact_2015usd_per_year",
    "component_resolution",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
