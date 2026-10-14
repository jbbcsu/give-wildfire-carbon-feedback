#!/usr/bin/env python3
"""Fail-closed utilities for the FrEDI v4.1.1 electricity heat sentinel."""

from __future__ import annotations

import csv
import hashlib
import json
import resource
import sys
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 50


class ElectricityContractError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(262144), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return value / divisor


def _rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def _number(value: str, label: str) -> Decimal:
    try:
        result = Decimal(value)
    except Exception as exc:
        raise ElectricityContractError(f"non-numeric {label}: {value!r}") from exc
    if not result.is_finite():
        raise ElectricityContractError(f"non-finite {label}: {value!r}")
    return result


def validate_contract(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if config["scope"]["authorized_released_sector"] != "ElecTD":
        raise ElectricityContractError("only released ElecTD is authorized")
    if config["scope"]["audited_but_excluded_sector"] != "ElecSD":
        raise ElectricityContractError("bundled ElecSD must remain explicitly excluded")
    gates = {row["endpoint"]: row for row in config["endpoint_gates"]}
    if set(gates) != {
        "generation_and_capacity",
        "building_heating_and_cooling_demand",
        "transmission_and_distribution",
        "transmission_only",
        "distribution_only",
    }:
        raise ElectricityContractError("electricity endpoint gates differ from frozen contract")
    if gates["transmission_and_distribution"]["authorized_for_output"] is not True:
        raise ElectricityContractError("combined T&D gate is not authorized")
    for endpoint in (
        "generation_and_capacity",
        "building_heating_and_cooling_demand",
        "transmission_only",
        "distribution_only",
    ):
        if gates[endpoint]["authorized_for_output"] is not False:
            raise ElectricityContractError(f"forbidden endpoint was opened: {endpoint}")
    if config["claim_status"] != {
        "td_deterministic_interface_sentinel": "open",
        "generation_capacity": "closed_bundled_with_excluded_demand",
        "building_heating_cooling_demand": "prohibited",
        "transmission_distribution_split": "closed",
        "matched_GIVE_pulse": "closed",
        "global_extrapolation": "prohibited",
        "SCC": "closed",
    }:
        raise ElectricityContractError("claim gates differ from frozen contract")
    sentinel = config["sentinel"]
    if Decimal(str(sentinel["driver_conus_degC_rel1995"])) != Decimal("1.5"):
        raise ElectricityContractError("sentinel is frozen to 1.5 C")
    if sentinel["economic_year"] != 2020:
        raise ElectricityContractError("sentinel is frozen to 2020")

    manifest_path = root / config["source_manifest"]
    manifest = read_json(manifest_path)
    for item in manifest["files"]:
        relative = item.get("raw_path")
        if relative is None:
            if item.get("vendored") is not False:
                raise ElectricityContractError(f"non-vendored file lacks explicit flag: {item['path']}")
            continue
        path = root / relative
        if not path.is_file():
            raise ElectricityContractError(f"missing pinned source: {relative}")
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise ElectricityContractError(f"pinned source mismatch: {relative}")

    alignment_path = root / config["alignment_audit"]
    alignment = read_json(alignment_path)
    tolerance = Decimal(str(alignment.get("absolute_tolerance")))
    if alignment.get("status") != "PASS" or tolerance > Decimal("1e-6"):
        raise ElectricityContractError("v4.1.1 electricity alignment audit is not admissible")
    if any(
        Decimal(str(row["max_abs_difference"])) > tolerance
        or row.get("unmatched_rows", 0) != 0
        for row in alignment.get("comparisons", [])
    ):
        raise ElectricityContractError("v4.1.1 electricity source alignment failed")
    return manifest, alignment


def _audit_scaled(
    path: Path,
    sector: str,
    config: dict[str, Any],
    retain: bool,
) -> tuple[dict[tuple[str, str, str, int], Decimal], set[str]]:
    expected = config["expected_source_support"][sector]
    models = set(config["sentinel"]["models"])
    variants = set(expected["variants"])
    bins: Counter[str] = Counter()
    state_names: dict[str, str] = {}
    values: dict[tuple[str, str, str, int], Decimal] = {}
    row_count = 0
    for row in _rows(path):
        row_count += 1
        if row["sector"] != sector:
            raise ElectricityContractError(f"unexpected sector in {path.name}")
        if row["impactType"] != "NA" or row["impactYear"] != "NA":
            raise ElectricityContractError(f"unexpected released component metadata in {path.name}")
        if row["model"] not in models or row["variant"] not in variants:
            raise ElectricityContractError(f"unexpected model/variant in {path.name}")
        try:
            temperature_bin = int(row["modelUnitValue"])
        except ValueError as exc:
            raise ElectricityContractError(f"invalid temperature bin in {path.name}") from exc
        if temperature_bin not in range(1, 7):
            raise ElectricityContractError(f"temperature bin outside 1..6 in {path.name}")
        bins[str(temperature_bin)] += 1
        postal = row["postal"]
        if len(postal) != 2:
            raise ElectricityContractError(f"invalid postal code in {path.name}")
        if state_names.setdefault(postal, row["state"]) != row["state"]:
            raise ElectricityContractError(f"inconsistent state label in {path.name}")
        number = _number(row["value"], f"{sector} scaled response")
        if temperature_bin in (1, 2):
            key = (postal, row["model"], row["variant"], temperature_bin)
            if key in values:
                raise ElectricityContractError(f"duplicate interpolation key in {path.name}: {key}")
            if retain:
                values[key] = number
    if row_count != expected["rows"]:
        raise ElectricityContractError(f"unexpected row count in {path.name}: {row_count}")
    if dict(sorted(bins.items())) != expected["rows_by_bin"]:
        raise ElectricityContractError(f"unexpected bin support in {path.name}")
    states = set(state_names)
    if len(states) != config["scope"]["expected_postal_count"]:
        raise ElectricityContractError(f"unexpected state/DC support in {path.name}")
    expected_keys = len(states) * len(models) * len(variants) * 2
    observed_keys = sum(1 for row in _rows(path) if int(row["modelUnitValue"]) in (1, 2))
    if observed_keys != expected_keys:
        raise ElectricityContractError(f"incomplete 1/2 C support in {path.name}")
    if retain and len(values) != expected_keys:
        raise ElectricityContractError(f"retained interpolation support is incomplete in {path.name}")
    return values, states


def _audit_scalar(
    path: Path,
    scalar_name: str,
    config: dict[str, Any],
    target_year: int,
) -> tuple[dict[str, Decimal], set[str]]:
    expected = config["expected_source_support"]
    target: dict[str, Decimal] = {}
    years_by_state: dict[str, set[int]] = {}
    row_count = 0
    for row in _rows(path):
        row_count += 1
        if row["scalarName"] != scalar_name:
            raise ElectricityContractError(f"unexpected scalar name in {path.name}")
        year = int(row["year"])
        years_by_state.setdefault(row["postal"], set()).add(year)
        number = _number(row["value"], f"{scalar_name} value")
        if year == target_year:
            if row["postal"] in target:
                raise ElectricityContractError(f"duplicate target scalar in {path.name}")
            target[row["postal"]] = number
    required_years = set(range(2006, 2091)) | {2100, 2200, 2300}
    if row_count != expected["scalar_rows"]:
        raise ElectricityContractError(f"unexpected scalar rows in {path.name}: {row_count}")
    if len(years_by_state) != config["scope"]["expected_postal_count"]:
        raise ElectricityContractError(f"unexpected scalar state/DC support in {path.name}")
    if any(years != required_years for years in years_by_state.values()):
        raise ElectricityContractError(f"unexpected year support in {path.name}")
    if set(target) != set(years_by_state):
        raise ElectricityContractError(f"missing target-year scalar in {path.name}")
    return target, set(years_by_state)


def interpolate(v1: Decimal, v2: Decimal, x: Decimal) -> Decimal:
    if not Decimal("1") <= x <= Decimal("2"):
        raise ElectricityContractError("sentinel interpolation is restricted to [1,2] C")
    return v1 + (x - Decimal("1")) * (v2 - v1)


OUTPUT_FIELDS = [
    "scope",
    "model_type",
    "driver_conus_degC_rel1995",
    "economic_year",
    "gcm",
    "variant",
    "released_sector",
    "endpoint_resolution",
    "annual_impact_2015usd_per_year",
]


def compute_sentinel(root: Path, config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    validate_contract(root, config)
    raw = root / "data/raw/fredi_data/inst/extdata/fredi"
    _, sd_states = _audit_scaled(raw / "gcm/ElecSD_scaledimpacts.csv", "ElecSD", config, False)
    td_values, td_states = _audit_scaled(raw / "gcm/ElecTD_scaledimpacts.csv", "ElecTD", config, True)
    year = config["sentinel"]["economic_year"]
    _, sd_scalar_states = _audit_scalar(
        raw / "scalars/Scalar_damageAdj_elecSD_refCosts.csv",
        "elecSD_refCosts",
        config,
        year,
    )
    td_growth, td_scalar_states = _audit_scalar(
        raw / "scalars/Scalar_damageAdj_elecTD_growthFactor.csv",
        "elecTD_growthFactor",
        config,
        year,
    )
    if not (sd_states == td_states == sd_scalar_states == td_scalar_states):
        raise ElectricityContractError("ElecSD/ElecTD source supports do not align")

    temp = Decimal(str(config["sentinel"]["driver_conus_degC_rel1995"]))
    quantizer = Decimal("0.000001")
    output: list[dict[str, str]] = []
    for variant in config["sentinel"]["variants"]:
        for model in config["sentinel"]["models"]:
            total = Decimal("0")
            for postal in sorted(td_states):
                scaled = interpolate(
                    td_values[(postal, model, variant, 1)],
                    td_values[(postal, model, variant, 2)],
                    temp,
                )
                total += scaled * td_growth[postal]
            output.append({
                "scope": "CONUS_48_plus_DC",
                "model_type": "GCM",
                "driver_conus_degC_rel1995": str(temp),
                "economic_year": str(year),
                "gcm": model,
                "variant": variant,
                "released_sector": "ElecTD",
                "endpoint_resolution": "combined_transmission_distribution",
                "annual_impact_2015usd_per_year": format(total.quantize(quantizer), "f"),
            })
    diagnostics = {
        "state_dc_count": len(td_states),
        "gcm_count": len(config["sentinel"]["models"]),
        "variant_count": len(config["sentinel"]["variants"]),
        "output_row_count": len(output),
        "computed_sectors": ["ElecTD"],
        "audited_excluded_sectors": ["ElecSD"],
    }
    return output, diagnostics


def write_output(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
