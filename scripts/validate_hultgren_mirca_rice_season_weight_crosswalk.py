#!/usr/bin/env python3
"""Independent aggregate validator for the Hultgren/MIRCA rice crosswalk."""
from __future__ import annotations

import argparse
import json
import math
import resource
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from audit_hultgren_mirca_rice_season_weight_crosswalk import (
    CONFIG_DEFAULT,
    CELL_COLUMNS,
    ROOT,
    digest,
    load_config,
    recover_unrepaired,
    resolve,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(left: float, right: float, label: str) -> None:
    require(math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-7), f"{label} differs")


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def validate(receipt_path: Path, config_path: Path = CONFIG_DEFAULT) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "hultgren_mirca_rice_season_weight_crosswalk_audit/v1", "schema differs")
    require(receipt.get("config_sha256") == config_hash, "config hash differs")
    require(receipt.get("status") == "exact_ri1_candidate_crosswalk_incomplete_and_hultgren_ri2_basis_unavailable", "status differs")
    table_path = resolve(receipt["output"]["path"])
    require(digest(table_path) == receipt["output"]["sha256"], "output hash differs")
    table = pd.read_parquet(table_path)
    require(len(table) == receipt["output"]["rows"] == 10104, "output row count differs")
    require(not table.duplicated(["latitude", "longitude"]).any(), "duplicate output cells")
    forbidden = ("yield", "response", "coefficient", "damage", "scc")
    emitted_numeric = [column.lower() for column in table.columns]
    require(not any(any(word in column for word in forbidden) and not column.endswith("authorized") for column in emitted_numeric), "forbidden effect field emitted")
    require(table["production_eligible"].eq(False).all(), "production flag opened")
    require(table["response_fit_authorized"].eq(False).all(), "response flag opened")
    require(table["damage_or_scc_authorized"].eq(False).all(), "damage/SCC flag opened")

    correction = json.loads(resolve(config["hultgren_india_correction_path"]).read_text(encoding="utf-8"))
    source_cells: pd.DataFrame | None = None
    source_rows = 0
    for record in correction["outputs"]:
        path = resolve(record["output"]["path"])
        frame = pd.read_parquet(path, columns=["calendar_branch", "harvest_year", *CELL_COLUMNS])
        source_rows += len(frame)
        cells = frame[CELL_COLUMNS].drop_duplicates().sort_values(CELL_COLUMNS[:2]).reset_index(drop=True)
        if source_cells is None:
            source_cells = cells
        else:
            require(source_cells.equals(cells), "preserved branch/chunk cell support differs")
    require(source_rows == 545616 and source_cells is not None, "preserved Hultgren rows differ")
    actual_cells = table[CELL_COLUMNS].sort_values(CELL_COLUMNS[:2]).reset_index(drop=True)
    require(source_cells.equals(actual_cells), "audit table is not the exact preserved Hultgren cell set")

    candidate = pd.read_parquet(resolve(config["mirca_candidate_path"]))
    for system in ("rainfed", "irrigated"):
        candidate[f"unrepaired_{system}_area_ha"] = recover_unrepaired(
            candidate[f"{system}_area_ha"].to_numpy(),
            candidate[f"{system}_repair_scale"].to_numpy(),
        )
    ri1 = candidate[candidate["crop"].eq("ri1")]
    expected_join = source_cells.merge(
        ri1[[
            "lat", "lon", "rainfed_area_ha", "irrigated_area_ha",
            "unrepaired_rainfed_area_ha", "unrepaired_irrigated_area_ha",
        ]],
        left_on=["latitude", "longitude"], right_on=["lat", "lon"],
        how="left", validate="one_to_one", indicator=True,
    )
    any_match = expected_join["_merge"].eq("both")
    require(int(any_match.sum()) == 10089, "exact Rice1 row match count differs")
    summaries = {row["weight_system"]: row for row in receipt["ri1_branch_summaries"]}
    for system in ("rainfed", "irrigated"):
        repaired = f"{system}_area_ha"
        original = f"unrepaired_{system}_area_ha"
        positive = expected_join[repaired].fillna(0).gt(0)
        summary = summaries[system]
        require(int(positive.sum()) == summary["exact_cells_with_positive_corresponding_weight"], f"{system} positive cells differ")
        require(len(expected_join) - int(positive.sum()) == summary["cells_without_positive_corresponding_weight"], f"{system} missing cells differ")
        close(float(positive.mean()), summary["positive_weight_cell_fraction"], f"{system} cell fraction")
        matched_repaired = float(expected_join.loc[positive, repaired].sum())
        matched_original = float(expected_join.loc[positive, original].sum())
        close(matched_repaired, summary["repaired_rice1_area_on_hultgren_support_ha"], f"{system} repaired support area")
        close(matched_original, summary["unrepaired_rice1_area_on_hultgren_support_ha"], f"{system} original support area")
        close(matched_repaired / float(ri1[repaired].sum()), summary["repaired_area_fraction_on_hultgren_support"], f"{system} repaired fraction")
    rainfed = expected_join["rainfed_area_ha"].fillna(0).gt(0)
    irrigated = expected_join["irrigated_area_ha"].fillna(0).gt(0)
    expected_joint = {
        "both_corresponding_weights_positive": int((rainfed & irrigated).sum()),
        "rainfed_only_positive": int((rainfed & ~irrigated).sum()),
        "irrigated_only_positive": int((~rainfed & irrigated).sum()),
        "neither_rice1_weight_positive": int((~rainfed & ~irrigated).sum()),
    }
    require(receipt["ri1_joint_support"] == expected_joint, "joint support differs")
    ri2 = candidate[candidate["crop"].eq("ri2")]
    require(len(ri2) == receipt["ri2_inventory"]["mirca_ri2_weight_rows"] == 8836, "Rice2 inventory differs")
    require(receipt["ri2_inventory"]["preserved_hultgren_ri2_weather_branches"] == 0, "Rice2 Hultgren availability differs")
    gates = receipt["claim_gates"]
    require(gates["exact_ri1_candidate_sensitivity_crosswalk_available"] is True, "candidate gate differs")
    for gate in (
        "complete_ri1_branch_weight_coverage", "preserved_hultgren_ri2_basis_available",
        "unrepaired_mirca_source_reconciliation_passed", "production_season_weight_crosswalk_authorized",
        "response_fit_authorized", "published_response_evaluated",
        "damage_calculation_authorized", "scc_use_authorized",
    ):
        require(gates[gate] is False, f"claim gate opened: {gate}")
    maximum_rss = peak_rss_bytes()
    require(maximum_rss <= int(config["resources"]["worker_memory_bytes_maximum"]), "validator memory cap exceeded")
    return {
        "status": "validated",
        "receipt": str(receipt_path),
        "independent_exact_cell_source_join_matches": True,
        "independent_original_area_reconstruction_matches": True,
        "ri1_rainfed_positive_weight_cells": int(rainfed.sum()),
        "ri1_irrigated_positive_weight_cells": int(irrigated.sum()),
        "preserved_hultgren_ri2_weather_branches": 0,
        "production_season_weight_crosswalk_authorized": False,
        "all_response_damage_scc_gates_closed": True,
        "maximum_rss_bytes": maximum_rss,
        "memory_cap_bytes": int(config["resources"]["worker_memory_bytes_maximum"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.receipt, args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
