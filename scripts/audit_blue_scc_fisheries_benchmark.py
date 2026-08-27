#!/usr/bin/env python3
"""Audit the published Blue-SCC fisheries pathway without importing its data.

The script reads a separately cloned source repository, verifies the frozen
commit and exact file identities, checks a small set of transparent method
tokens, and emits aggregate-only facts from the published coefficient table
and Figure 4 source data. It never copies country coefficients or authorizes
their use in GIVE.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    if not letters:
        raise ValueError(f"invalid spreadsheet cell reference: {reference}")
    value = 0
    for letter in letters.group(0):
        value = value * 26 + ord(letter) - 64
    return value - 1


def xlsx_sheet_rows(path: Path, sheet_name: str) -> list[list[object]]:
    """Read simple scalar XLSX cells using only the standard library."""
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
        }
        target = None
        for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
            if sheet.attrib.get("name") == sheet_name:
                target = targets[sheet.attrib[f"{{{REL_NS}}}id"]]
                break
        if target is None:
            raise ValueError(f"missing worksheet: {sheet_name}")
        target_path = PurePosixPath(target.lstrip("/"))
        if not target_path.parts or target_path.parts[0] != "xl":
            target_path = PurePosixPath("xl") / target_path
        normalized = str(PurePosixPath(*[part for part in target_path.parts if part != "."]))

        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(f"{{{MAIN_NS}}}si"):
                shared.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))

        root = ET.fromstring(archive.read(normalized))
        rows: list[list[object]] = []
        for row in root.findall(f".//{{{MAIN_NS}}}row"):
            values: dict[int, object] = {}
            for cell in row.findall(f"{{{MAIN_NS}}}c"):
                index = column_index(cell.attrib["r"])
                kind = cell.attrib.get("t")
                if kind == "inlineStr":
                    value: object = "".join(
                        node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t")
                    )
                else:
                    node = cell.find(f"{{{MAIN_NS}}}v")
                    if node is None or node.text is None:
                        value = ""
                    elif kind == "s":
                        value = shared[int(node.text)]
                    else:
                        number = float(node.text)
                        value = int(number) if number.is_integer() else number
                values[index] = value
            width = max(values, default=-1) + 1
            rows.append([values.get(index, "") for index in range(width)])
        return rows


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ValueError(f"{path.name} is missing expected method tokens: {missing}")


def coefficient_summary(path: Path) -> dict[str, object]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        records = list(csv.DictReader(handle))
    expected = {"country_iso3", "GDP_FractionChange_perC"}
    if not records or not expected.issubset(records[0]):
        raise ValueError("country coefficient table schema changed")
    values: list[float] = []
    countries: set[str] = set()
    for record in records:
        country = record["country_iso3"].strip()
        if not re.fullmatch(r"[A-Z]{3}", country) or country in countries:
            raise ValueError("country coefficient keys are invalid or duplicated")
        countries.add(country)
        value = float(record["GDP_FractionChange_perC"])
        if not math.isfinite(value):
            raise ValueError("country coefficient is nonfinite")
        values.append(value)
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "rows": len(records),
        "nonmissing_coefficients": len(values),
        "negative_coefficients": sum(value < 0 for value in values),
        "positive_coefficients": sum(value > 0 for value in values),
        "zero_coefficients": sum(value == 0 for value in values),
        "minimum_coefficient": min(values),
        "maximum_coefficient": max(values),
        "median_coefficient": median,
    }


def figure_summary(path: Path, sheet_name: str, year: int) -> dict[str, float]:
    rows = xlsx_sheet_rows(path, sheet_name)
    if not rows:
        raise ValueError("Figure 4 source sheet is empty")
    header = [str(value) for value in rows[0]]
    required = ["t", "scc", "oc_capital", "valuation"]
    if any(name not in header for name in required):
        raise ValueError("Figure 4 source sheet schema changed")
    indexes = {name: header.index(name) for name in required}
    selected: dict[tuple[str, str], float] = {}
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        try:
            row_year = int(padded[indexes["t"]])
        except (TypeError, ValueError):
            raise ValueError("Figure 4 source sheet has an invalid year") from None
        if row_year != year:
            continue
        key = (str(padded[indexes["oc_capital"]]), str(padded[indexes["valuation"]]))
        if key in selected:
            raise ValueError(f"duplicate Figure 4 component for {year}: {key}")
        try:
            value = float(padded[indexes["scc"]])
        except (TypeError, ValueError):
            raise ValueError(f"Figure 4 component has a nonnumeric SCC value: {key}") from None
        if not math.isfinite(value):
            raise ValueError(f"Figure 4 component has a nonfinite SCC value: {key}")
        selected[key] = value
    required_keys = {
        ("Total", "Total"),
        ("Fisheries", "Market value"),
        ("Fisheries", "Non-market use value"),
    }
    missing = required_keys - selected.keys()
    if missing:
        raise ValueError(f"Figure 4 source sheet is missing required components: {sorted(missing)}")
    total = selected[("Total", "Total")]
    market = selected[("Fisheries", "Market value")]
    nonmarket = selected[("Fisheries", "Non-market use value")]
    if total == 0:
        raise ValueError("Figure 4 total blue SCC is zero; component share is undefined")
    fisheries_total = market + nonmarket
    return {
        "total_blue_scc_usd_per_tco2": total,
        "fisheries_market_scc_usd_per_tco2": market,
        "fisheries_nonmarket_use_scc_usd_per_tco2": nonmarket,
        "fisheries_total_scc_usd_per_tco2": fisheries_total,
        "fisheries_share_of_total_blue_scc": fisheries_total / total,
    }


def audit(source_root: Path, config_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("contract_id") != "blue_scc_fisheries_literature_benchmark_v1":
        raise ValueError("wrong literature-benchmark contract")
    if git_head(source_root) != config["source"]["repository_commit"]:
        raise ValueError("Blue-SCC repository commit changed")
    license_files = [
        path.name for path in source_root.iterdir()
        if path.is_file() and path.name.lower().startswith(("license", "copying"))
    ]
    if license_files:
        raise ValueError("audited repository now has a root license file; review before reuse")

    files: dict[str, Path] = {}
    for name in [
        "market_projection_script", "market_damage_script", "nutrition_script",
        "country_market_coefficients", "figure4_source_data",
    ]:
        path = source_root / config["files"][name]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing regular source file: {name}")
        expected_hash = config["files"][f"{name}_sha256"]
        if sha256_file(path) != expected_hash:
            raise ValueError(f"source file hash changed: {name}")
        files[name] = path

    require_tokens(files["market_projection_script"], config["method_tokens"]["market_projection"])
    require_tokens(files["market_damage_script"], config["method_tokens"]["market_damage"])
    require_tokens(files["nutrition_script"], config["method_tokens"]["nutrition"])

    coefficients = coefficient_summary(files["country_market_coefficients"])
    if coefficients["rows"] != config["expected"]["country_coefficient_rows"]:
        raise ValueError("country coefficient row count changed")
    figure = figure_summary(
        files["figure4_source_data"],
        config["expected"]["figure_sheet"],
        int(config["expected"]["figure_year"]),
    )
    tolerance = float(config["expected"]["comparison_tolerance"])
    for key in [
        "total_blue_scc_usd_per_tco2", "fisheries_market_scc_usd_per_tco2",
        "fisheries_nonmarket_use_scc_usd_per_tco2",
    ]:
        if abs(figure[key] - float(config["expected"][key])) > tolerance:
            raise ValueError(f"published Figure 4 benchmark changed: {key}")

    return {
        "schema": "blue_scc_fisheries_literature_benchmark_audit_v1",
        "status": "passed_published_method_and_source_data_audit_only",
        "contract_id": config["contract_id"],
        "source": config["source"],
        "verified_file_sha256": {
            name: config["files"][f"{name}_sha256"] for name in files
        },
        "country_market_coefficient_summary": coefficients,
        "published_figure4_baseline_summary": figure,
        "method_readout": {
            "market_pathway": "Free_et_al_country_profit_paths_full_adaptation_relative_to_RCP2.6_then_regional_output_multipliers_and_country_temperature_slopes",
            "nutrition_pathway": "Cheung_et_al_nutrient_availability_slopes_combined_with_selected_relative_risks_GBD_baseline_dependence_5pct_no_substitution_and_income_scaled_VSL",
            "market_measure_is_not_consumer_plus_producer_surplus": True,
            "fishmip_total_catch_is_not_the_published_market_input": True,
        },
        "scientific_gates": config["scientific_gates"],
        "raw_country_coefficients_embedded": False,
        "external_repository_files_copied": False,
        "machine_specific_paths_embedded": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/blue_scc_fisheries_literature_benchmark_v1.toml"),
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    payload = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["published_figure4_baseline_summary"], sort_keys=True))


if __name__ == "__main__":
    main()
