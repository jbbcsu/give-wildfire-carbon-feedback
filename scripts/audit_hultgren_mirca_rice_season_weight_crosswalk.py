#!/usr/bin/env python3
"""Audit exact-cell Hultgren rice/MIRCA season-weight compatibility."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DEFAULT = ROOT / "config" / "hultgren_mirca_rice_season_weight_crosswalk_audit_v1.toml"
CONTRACT_ID = "hultgren_mirca_rice_season_weight_crosswalk_audit_v1"
MEMORY_CAP = 512 * 1024 * 1024
CELL_COLUMNS = [
    "native_lat_index", "native_lon_index", "latitude", "longitude",
    "plant_month", "harvest_month", "season_months",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def recorded_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def recover_unrepaired(repaired: np.ndarray, scale: np.ndarray) -> np.ndarray:
    repaired = np.asarray(repaired, dtype=float)
    scale = np.asarray(scale, dtype=float)
    require(repaired.shape == scale.shape, "area and scale shapes differ")
    require(np.isfinite(repaired).all() and np.isfinite(scale).all(), "nonfinite area or scale")
    require((repaired >= 0).all() and (scale >= 0).all(), "negative area or scale")
    require(not np.any((scale == 0) & (repaired != 0)), "positive repaired area has zero scale")
    return np.divide(repaired, scale, out=np.zeros_like(repaired), where=scale > 0)


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config.get("schema_version") == 1, "config schema changed")
    require(config.get("contract_id") == CONTRACT_ID, "contract id changed")
    expected = {
        ("ri1_noirr", "ri1", "rainfed"),
        ("ri1_firr", "ri1", "irrigated"),
    }
    actual = {
        (row["hultgren_branch"], row["mirca_crop"], row["weight_system"])
        for row in config.get("branch_mapping", [])
    }
    require(actual == expected, "branch mapping changed")
    unavailable = {
        (row["hultgren_branch"], row["mirca_crop"], row["weight_system"])
        for row in config.get("unavailable_branch", [])
    }
    require(
        unavailable == {("ri2_noirr", "ri2", "rainfed"), ("ri2_firr", "ri2", "irrigated")},
        "unavailable ri2 registry changed",
    )
    for prefix in (
        "hultgren_response_validation", "hultgren_preflight_validation",
        "hultgren_india_correction", "hultgren_india_validation",
        "mirca_reconciliation_receipt", "mirca_reconciliation_validation", "mirca_candidate",
    ):
        source = resolve(config[f"{prefix}_path"])
        require(digest(source) == config[f"{prefix}_sha256"], f"{prefix} hash differs")
    crosswalk = config["crosswalk"]
    for key in (
        "nearest_neighbor_authorized", "opposite_irrigation_weight_authorized",
        "rice3_transfer_authorized", "unmatched_cell_fill_authorized",
        "country_average_fill_authorized", "renormalization_over_matched_cells_authorized",
    ):
        require(crosswalk.get(key) is False, f"forbidden crosswalk rule opened: {key}")
    authorization = config["authorization"]
    require(authorization.get("source_crosswalk_audit_authorized") is True, "audit authorization missing")
    require(authorization.get("candidate_sensitivity_table_authorized") is True, "table authorization missing")
    for key, value in authorization.items():
        if key not in {"source_crosswalk_audit_authorized", "candidate_sensitivity_table_authorized"}:
            require(value is False, f"claim gate opened: {key}")
    return config, hashlib.sha256(raw).hexdigest()


def load_hultgren_cells(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    receipt = json.loads(resolve(config["hultgren_india_correction_path"]).read_text(encoding="utf-8"))
    require(receipt.get("status") == "india_reporting_year_exception_applied_to_verified_cells", "India correction status differs")
    by_branch: dict[str, list[dict[str, Any]]] = {"ri1_noirr": [], "ri1_firr": []}
    for row in receipt.get("outputs", []):
        branch = row.get("calendar_branch")
        if branch in by_branch:
            by_branch[branch].append(row["output"])
    branch_cells: dict[str, pd.DataFrame] = {}
    branch_audit: dict[str, Any] = {}
    for branch, outputs in by_branch.items():
        require(len(outputs) == 3, f"expected three preserved chunks for {branch}")
        reference: pd.DataFrame | None = None
        total_rows = 0
        years: set[int] = set()
        sources: list[dict[str, Any]] = []
        for record in outputs:
            path = resolve(record["path"])
            require(digest(path) == record["sha256"], f"preserved Hultgren chunk hash differs: {path}")
            frame = pd.read_parquet(path, columns=["calendar_branch", "harvest_year", *CELL_COLUMNS])
            require(frame["calendar_branch"].eq(branch).all(), f"branch column differs for {branch}")
            require(len(frame) == int(record["rows"]), f"chunk row count differs for {branch}")
            total_rows += len(frame)
            years.update(int(value) for value in frame["harvest_year"].unique())
            cells = frame[CELL_COLUMNS].drop_duplicates().sort_values(CELL_COLUMNS[:2]).reset_index(drop=True)
            require(len(cells) == 10104, f"cell count differs for {branch}")
            if reference is None:
                reference = cells
            else:
                require(reference.equals(cells), f"cell/calendar support changes across chunks for {branch}")
            sources.append({"path": record["path"], "rows": len(frame), "sha256": record["sha256"]})
        require(reference is not None and total_rows == 272808, f"preserved rows differ for {branch}")
        branch_cells[branch] = reference
        branch_audit[branch] = {
            "cell_year_rows": total_rows,
            "unique_cells": len(reference),
            "harvest_year_count": len(years),
            "harvest_years": sorted(years),
            "sources": sources,
        }
    require(branch_cells["ri1_noirr"].equals(branch_cells["ri1_firr"]), "ri1 branch calendars differ")
    return branch_cells["ri1_noirr"], branch_audit


def branch_summary(
    joined: pd.DataFrame,
    mirca_crop: pd.DataFrame,
    branch: str,
    system: str,
    repaired_column: str,
    original_column: str,
) -> dict[str, Any]:
    positive = joined[repaired_column].fillna(0).gt(0)
    any_row = joined["mirca_ri1_row_available"]
    global_repaired = float(mirca_crop[repaired_column].sum())
    global_original = float(mirca_crop[original_column].sum())
    matched_repaired = float(joined.loc[positive, repaired_column].sum())
    matched_original = float(joined.loc[positive, original_column].sum())
    cells = len(joined)
    positive_cells = int(positive.sum())
    years = 27
    return {
        "hultgren_branch": branch,
        "mirca_crop": "ri1",
        "weight_system": system,
        "hultgren_cells": cells,
        "hultgren_cell_years": cells * years,
        "exact_cells_with_any_mirca_ri1_row": int(any_row.sum()),
        "exact_cells_with_positive_corresponding_weight": positive_cells,
        "cells_without_positive_corresponding_weight": cells - positive_cells,
        "positive_weight_cell_fraction": positive_cells / cells,
        "matched_cell_years_with_positive_corresponding_weight": positive_cells * years,
        "unmatched_cell_years_without_positive_corresponding_weight": (cells - positive_cells) * years,
        "global_repaired_rice1_area_ha": global_repaired,
        "global_unrepaired_rice1_area_ha": global_original,
        "repaired_rice1_area_on_hultgren_support_ha": matched_repaired,
        "unrepaired_rice1_area_on_hultgren_support_ha": matched_original,
        "repaired_area_fraction_on_hultgren_support": matched_repaired / global_repaired,
        "unrepaired_area_fraction_on_hultgren_support": matched_original / global_original,
        "complete_positive_corresponding_weight_coverage": positive_cells == cells,
    }


def run(config_path: Path, table_path: Path) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    cells, hultgren_audit = load_hultgren_cells(config)
    candidate = pd.read_parquet(resolve(config["mirca_candidate_path"]))
    require(len(candidate) == 30903, "MIRCA candidate row count differs")
    require(candidate["production_eligible"].eq(False).all(), "candidate production gate opened")
    require(candidate["scc_authorized"].eq(False).all(), "candidate SCC gate opened")
    require(candidate["proportional_reconciliation_sensitivity"].eq(True).all(), "candidate sensitivity flag differs")
    require(set(candidate["crop"]) == {"ri1", "ri2"}, "MIRCA crop registry differs")
    require(not candidate.duplicated(["crop", "lat", "lon"]).any(), "duplicate MIRCA crop cells")
    for system in ("rainfed", "irrigated"):
        repaired = f"{system}_area_ha"
        scale = f"{system}_repair_scale"
        candidate[f"unrepaired_{system}_area_ha"] = recover_unrepaired(
            candidate[repaired].to_numpy(), candidate[scale].to_numpy()
        )

    ri1 = candidate.loc[candidate["crop"].eq("ri1")].copy()
    selected = [
        "lat", "lon", "rainfed_area_ha", "irrigated_area_ha",
        "unrepaired_rainfed_area_ha", "unrepaired_irrigated_area_ha",
        "rainfed_repair_scale", "irrigated_repair_scale",
    ]
    joined = cells.merge(
        ri1[selected], left_on=["latitude", "longitude"], right_on=["lat", "lon"],
        how="left", validate="one_to_one", indicator=True,
    )
    joined["mirca_ri1_row_available"] = joined["_merge"].eq("both")
    joined.drop(columns=["_merge", "lat", "lon"], inplace=True)
    area_columns = [column for column in joined if "area_ha" in column]
    joined[area_columns] = joined[area_columns].fillna(0.0)
    scale_columns = ["rainfed_repair_scale", "irrigated_repair_scale"]
    joined[scale_columns] = joined[scale_columns].fillna(0.0)
    joined["ri1_rainfed_weight_available"] = joined["rainfed_area_ha"].gt(0)
    joined["ri1_irrigated_weight_available"] = joined["irrigated_area_ha"].gt(0)
    joined["proportional_reconciliation_sensitivity"] = True
    joined["production_eligible"] = False
    joined["response_fit_authorized"] = False
    joined["damage_or_scc_authorized"] = False

    summaries = []
    for mapping in config["branch_mapping"]:
        system = mapping["weight_system"]
        summaries.append(branch_summary(
            joined, ri1, mapping["hultgren_branch"], system,
            mapping["repaired_area_column"], f"unrepaired_{system}_area_ha",
        ))
    rainfed = joined["ri1_rainfed_weight_available"]
    irrigated = joined["ri1_irrigated_weight_available"]
    joint = {
        "both_corresponding_weights_positive": int((rainfed & irrigated).sum()),
        "rainfed_only_positive": int((rainfed & ~irrigated).sum()),
        "irrigated_only_positive": int((~rainfed & irrigated).sum()),
        "neither_rice1_weight_positive": int((~rainfed & ~irrigated).sum()),
    }
    ri2 = candidate.loc[candidate["crop"].eq("ri2")]
    ri2_inventory = {
        "mirca_ri2_weight_rows": len(ri2),
        "positive_rainfed_weight_cells": int(ri2["rainfed_area_ha"].gt(0).sum()),
        "positive_irrigated_weight_cells": int(ri2["irrigated_area_ha"].gt(0).sum()),
        "repaired_rainfed_area_ha": float(ri2["rainfed_area_ha"].sum()),
        "repaired_irrigated_area_ha": float(ri2["irrigated_area_ha"].sum()),
        "preserved_hultgren_ri2_weather_branches": 0,
        "crosswalk_executable_without_substitution": False,
    }
    table_path.parent.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(table_path, index=False, compression="zstd")
    maximum_rss = peak_rss_bytes()
    require(maximum_rss <= int(config["resources"]["worker_memory_bytes_maximum"]), "memory cap exceeded")
    production_pass = bool(
        all(row["complete_positive_corresponding_weight_coverage"] for row in summaries)
        and ri2_inventory["preserved_hultgren_ri2_weather_branches"] == 2
        and False  # unrepaired Rice1--Rice3 source reconciliation remains failed
    )
    result = {
        "schema": "hultgren_mirca_rice_season_weight_crosswalk_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "exact_ri1_candidate_crosswalk_incomplete_and_hultgren_ri2_basis_unavailable",
        "contract_id": CONTRACT_ID,
        "config_sha256": config_hash,
        "mapping_rule": "Rice1_to_preserved_ri1_branches_by_exact_half_degree_cell; Rice2_unavailable_without_preserved_ri2_basis",
        "hultgren_support": hultgren_audit,
        "ri1_branch_summaries": summaries,
        "ri1_joint_support": joint,
        "ri2_inventory": ri2_inventory,
        "output": {
            "path": recorded_path(table_path),
            "rows": len(joined),
            "bytes": table_path.stat().st_size,
            "sha256": digest(table_path),
        },
        "sources": {
            key: {"path": config[f"{key}_path"], "sha256": config[f"{key}_sha256"]}
            for key in (
                "hultgren_response_validation", "hultgren_preflight_validation",
                "hultgren_india_correction", "hultgren_india_validation",
                "mirca_reconciliation_receipt", "mirca_reconciliation_validation", "mirca_candidate",
            )
        },
        "claim_gates": {
            "exact_ri1_candidate_sensitivity_crosswalk_available": True,
            "no_imputation_or_substitution_used": True,
            "complete_ri1_branch_weight_coverage": False,
            "preserved_hultgren_ri2_basis_available": False,
            "unrepaired_mirca_source_reconciliation_passed": False,
            "production_season_weight_crosswalk_authorized": production_pass,
            "response_fit_authorized": False,
            "published_response_evaluated": False,
            "damage_calculation_authorized": False,
            "scc_use_authorized": False,
        },
        "resources": {
            "maximum_rss_bytes": maximum_rss,
            "memory_cap_bytes": int(config["resources"]["worker_memory_bytes_maximum"]),
        },
        "warning": (
            "The table is an exact-cell source audit and proportional-reconciliation sensitivity. "
            "It is not a production weight crosswalk, response evaluation, damage estimate, or SCC input."
        ),
    }
    require(production_pass is False, "production gate unexpectedly passed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--table-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.config, args.table_out)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "hultgren_support"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
