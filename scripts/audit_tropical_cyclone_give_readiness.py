"""Audit the published tropical-cyclone SCC artifacts and GIVE claim gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


SCHEMA = "tropical_cyclone_give_readiness_v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_files(root: Path, files: dict[str, str]) -> None:
    for relative, expected in files.items():
        path = root / relative
        require(path.is_file(), f"missing pinned file: {relative}")
        require(sha256(path) == expected, f"hash changed: {relative}")


def validate_contract(contract: dict[str, object]) -> dict[str, object]:
    require(contract.get("schema") == SCHEMA, "contract schema changed")
    selection = contract.get("selection", {})
    require(selection.get("give_status") == "not_explicitly_represented", "GIVE coverage claim changed")
    benchmark = contract.get("published_benchmark", {})
    require(benchmark.get("paired_tc_global_uncertainty_released_in_source_csv") is False, "unsupported paired uncertainty claimed")
    require("not_the_median_of_paired_tc_scc_draws" in benchmark.get("interpretation", ""), "difference-of-medians warning missing")
    overlap = contract.get("overlap_boundary", {})
    require(overlap.get("direct_ciam_storm_surge_overlap") is False, "CIAM boundary changed")
    require(overlap.get("broad_sectoral_overlap_risk") == "high", "macro overlap risk understated")
    require(overlap.get("additive_to_explicit_give_sector_modules") is False, "sectoral additivity gate opened")
    require(overlap.get("additive_to_aggregate_macro_damage_function") is False, "macro additivity gate opened")
    gate = contract.get("current_gate", {})
    require(gate.get("numeric_give_addition_authorized") is False, "numeric GIVE gate opened")
    interface = contract.get("give_target_interface", {})
    require(len(interface.get("required_fields", [])) == 12, "target fields incomplete")
    require(len(interface.get("required_validation", [])) == 8, "validation gates incomplete")
    return {"contract_valid": True, "numeric_give_addition_authorized": False}


def audit_code(root: Path, contract: dict[str, object]) -> dict[str, object]:
    release = contract["code_release"]
    verify_files(root, release["pinned_files"])
    aggregate = (root / "tc_cost/aggregate/scc.py").read_text(encoding="utf-8")
    bootstrap = (root / "tc_cost/bootstrap/scc.py").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for token in (
        'ds_scc[f"scc{s}_tc"] = ds_scc[f"scc{s}"] - ds_scc[f"scc{s}_temp"]',
        'quantile(q=q, dim=qdims)',
        'scc_wld',
    ):
        require(token in aggregate, f"paired SCC implementation token missing: {token}")
    for token in ("load_gmt_pulse", "per gigaton of carbon", "compute_scc"):
        require(token in bootstrap, f"pulse implementation token missing: {token}")
    require("100 TC realizations and 1200 bootstraps" in readme, "documented ensemble size changed")
    return {
        "pinned_hashes_valid": True,
        "paired_tc_difference_is_computed_before_quantiles_in_code": True,
        "documented_tc_realizations": 100,
        "documented_bootstraps": 1200,
    }


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def audit_source_data(root: Path, contract: dict[str, object]) -> dict[str, object]:
    release = contract["source_data_release"]
    verify_files(root, release["pinned_files"])
    table = rows(root / "tabs3.csv")
    require(len(table) == 82, "damage-function row count changed")
    by_country: dict[str, set[str]] = {}
    for row in table:
        by_country.setdefault(row["ISO"], set()).add(row["coeff"])
        for key in ("mean", "17", "83"):
            require(math.isfinite(float(row[key])), f"nonfinite coefficient: {row['ISO']} {key}")
    require(len(by_country) == 41, "country coverage changed")
    require(all(value == {"const", "gmt"} for value in by_country.values()), "coefficient coverage changed")
    gmt = [row for row in table if row["coeff"] == "gmt"]
    mean_negative = sum(float(row["mean"]) < 0 for row in gmt)
    upper_negative = sum(float(row["83"]) < 0 for row in gmt)
    require(mean_negative == 38 and upper_negative == 36, "published GMT coefficient summary changed")

    fig4 = rows(root / "fig4a.csv")
    selected = [
        row for row in fig4
        if row["SSP"] == "SSP2" and row["rcp"] == "rcp60"
        and math.isclose(float(row["rho"]), 0.02)
        and math.isclose(float(row["eta"]), 1.5)
    ]
    require(len(selected) == 1, "main benchmark row missing or duplicated")
    row = selected[0]
    with_tc = float(row["scc_wld50"])
    temp_only = float(row["scc_wld_temp50"])
    difference = with_tc - temp_only
    benchmark = contract["published_benchmark"]
    require(math.isclose(with_tc, benchmark["median_scc_with_temperature_and_tc"]), "with-TC median changed")
    require(math.isclose(temp_only, benchmark["median_scc_temperature_only"]), "temperature-only median changed")
    require(math.isclose(difference, benchmark["difference_of_published_medians"]), "published median difference changed")
    require(math.isclose(with_tc / temp_only - 1, benchmark["relative_increase_from_published_medians"]), "relative increase changed")
    headers = {name: set(rows(root / name)[0]) for name in release["pinned_files"] if name.endswith(".csv")}
    require(not any("scc_wld_tc50" in values for values in headers.values()), "paired global TC quantile unexpectedly released")
    return {
        "pinned_hashes_valid": True,
        "damage_function_country_count": len(by_country),
        "damage_function_row_count": len(table),
        "gmt_mean_negative_country_count": mean_negative,
        "gmt_upper_66_bound_negative_country_count": upper_negative,
        "published_main_with_tc_median": with_tc,
        "published_main_temperature_only_median": temp_only,
        "difference_of_published_medians": difference,
        "relative_increase_from_published_medians": with_tc / temp_only - 1,
        "paired_global_tc_quantile_found": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--source-data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    result = {
        "schema": "tropical_cyclone_give_readiness_receipt_v1",
        **validate_contract(contract),
        "contract_sha256": sha256(args.contract),
        "code_audit": audit_code(args.code_root, contract),
        "source_data_audit": audit_source_data(args.source_data_root, contract),
        "conclusion": "global_published_executable_tc_benchmark_exists_but_additive_give_gate_is_blocked_by_macro_sector_overlap",
    }
    result["implementation_sha256"] = sha256(Path(__file__).resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("tropical-cyclone benchmark verified; additive GIVE gate remains blocked")


if __name__ == "__main__":
    main()
