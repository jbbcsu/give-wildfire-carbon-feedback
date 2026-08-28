#!/usr/bin/env python3
"""Fail-closed preflight for allocating FishMIP grid support to maritime areas.

This validates geometry/allocation accounting only. Sovereign EEZ fractions
can be keyed to GIVE countries, but joint/disputed waters and high seas remain
explicitly ineligible for country welfare aggregation. The validator does not
infer fleet incidence, trade, welfare, damages, or an SCC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCHEMA = "fishmip_grid_eez_allocation_preflight_v1"
CELL_KEYS = ["grid_lat_index", "grid_lon_index"]
ENTITY_TYPES = {"sovereign_eez", "joint_or_disputed", "high_seas"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    support: pd.DataFrame,
    allocation: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    source_version: str,
    source_license: str,
    tolerance: float = 1e-10,
) -> dict[str, object]:
    support_required = set(CELL_KEYS + ["grid_lat", "grid_lon", "cell_area_weight"])
    allocation_required = set(
        CELL_KEYS
        + [
            "grid_lat",
            "grid_lon",
            "allocation_entity",
            "entity_type",
            "iso3",
            "area_fraction",
            "source_version",
            "source_license",
            "country_aggregation_eligible",
        ]
    )
    crosswalk_required = {"iso3", "fund_region"}
    require(support_required <= set(support.columns), "FishMIP support columns changed")
    require(allocation_required <= set(allocation.columns), "maritime-allocation columns changed")
    require(crosswalk_required <= set(crosswalk.columns), "GIVE country crosswalk columns changed")
    require(len(support) > 0 and len(allocation) > 0, "allocation inputs are empty")
    require(not support[CELL_KEYS].duplicated().any(), "FishMIP support duplicates a grid cell")
    require(
        not allocation[CELL_KEYS + ["allocation_entity"]].duplicated().any(),
        "maritime allocation duplicates a cell/entity row",
    )
    for frame, name in [(support, "support"), (allocation, "allocation")]:
        for column in ["grid_lat", "grid_lon"]:
            values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
            require(np.isfinite(values).all(), f"{name} has invalid {column}")
    support_area = pd.to_numeric(support.cell_area_weight, errors="coerce").to_numpy(dtype=float)
    require(np.isfinite(support_area).all() and (support_area > 0).all(), "support area weights are invalid")
    fractions = pd.to_numeric(allocation.area_fraction, errors="coerce").to_numpy(dtype=float)
    require(np.isfinite(fractions).all() and (fractions > 0).all(), "allocation fractions must be positive finite")
    require((fractions <= 1 + tolerance).all(), "allocation fraction exceeds one")
    require(set(allocation.entity_type) <= ENTITY_TYPES, "unknown maritime entity type")
    require(set(allocation.source_version) == {source_version}, "maritime source version is not fixed")
    require(set(allocation.source_license) == {source_license}, "maritime source license is not fixed")

    support_keys = set(map(tuple, support[CELL_KEYS].itertuples(index=False, name=None)))
    allocation_keys = set(map(tuple, allocation[CELL_KEYS].itertuples(index=False, name=None)))
    require(allocation_keys == support_keys, "allocation does not exactly cover FishMIP support cells")
    coordinate_check = allocation.merge(
        support[CELL_KEYS + ["grid_lat", "grid_lon"]],
        on=CELL_KEYS,
        how="left",
        validate="many_to_one",
        suffixes=("", "_support"),
    )
    require(
        np.allclose(coordinate_check.grid_lat, coordinate_check.grid_lat_support, atol=tolerance, rtol=0)
        and np.allclose(coordinate_check.grid_lon, coordinate_check.grid_lon_support, atol=tolerance, rtol=0),
        "allocation grid coordinates differ from FishMIP support",
    )
    sums = allocation.assign(area_fraction=fractions).groupby(CELL_KEYS).area_fraction.sum()
    require(np.allclose(sums.to_numpy(), 1.0, atol=tolerance, rtol=0), "cell allocation fractions do not sum to one")

    normalized_crosswalk = crosswalk.copy()
    normalized_crosswalk["iso3"] = normalized_crosswalk.iso3.astype(str).str.upper().str.strip()
    require(normalized_crosswalk.iso3.str.fullmatch(r"[A-Z]{3}").all(), "crosswalk ISO3 key is invalid")
    require(not normalized_crosswalk.iso3.duplicated().any(), "crosswalk duplicates an ISO3 key")
    known_iso3 = set(normalized_crosswalk.iso3)
    country_rows = allocation.entity_type.eq("sovereign_eez")
    iso3 = allocation.iso3.fillna("").astype(str).str.upper().str.strip()
    eligible = allocation.country_aggregation_eligible
    require(eligible.map(type).eq(bool).all(), "country eligibility must use booleans")
    require(eligible.eq(country_rows).all(), "only sovereign EEZ rows may be country-aggregation eligible")
    require(iso3.loc[country_rows].isin(known_iso3).all(), "sovereign EEZ row lacks a mapped GIVE ISO3")
    require(iso3.loc[~country_rows].eq("").all(), "non-sovereign maritime row must not carry an ISO3")

    joined = allocation.assign(area_fraction=fractions).merge(
        support[CELL_KEYS + ["cell_area_weight"]], on=CELL_KEYS, how="left", validate="many_to_one"
    )
    joined["weighted_area"] = joined.area_fraction * joined.cell_area_weight
    weighted = joined.groupby("entity_type").weighted_area.sum().to_dict()
    total = float(joined.weighted_area.sum())
    require(total > 0, "allocated support area is empty")
    weighted_shares = {name: float(weighted.get(name, 0.0) / total) for name in sorted(ENTITY_TYPES)}
    require(abs(sum(weighted_shares.values()) - 1.0) <= tolerance, "entity-type weighted shares do not conserve")
    mapped_iso3 = sorted(set(iso3.loc[country_rows]))
    return {
        "schema": SCHEMA,
        "status": "passed_geometry_accounting_only",
        "source_version": source_version,
        "source_license": source_license,
        "fishmip_support_cells": len(support),
        "allocation_rows": len(allocation),
        "mapped_sovereign_iso3_count": len(mapped_iso3),
        "mapped_sovereign_iso3": mapped_iso3,
        "weighted_area_share_by_entity_type": weighted_shares,
        "allocation_fraction_tolerance": tolerance,
        "complete_support_coverage": True,
        "cell_fraction_conservation": True,
        "joint_or_disputed_country_aggregation_eligible": False,
        "high_seas_country_aggregation_eligible": False,
        "fleet_incidence_identified": False,
        "trade_or_market_incidence_identified": False,
        "welfare_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--support", type=Path, required=True)
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--source-license", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    support = pd.read_csv(args.support)
    allocation = pd.read_csv(args.allocation, keep_default_na=False)
    crosswalk = pd.read_csv(args.crosswalk)
    result = validate(
        support,
        allocation,
        crosswalk,
        source_version=args.source_version,
        source_license=args.source_license,
    )
    result["inputs"] = {
        "support_sha256": sha256_file(args.support),
        "allocation_sha256": sha256_file(args.allocation),
        "crosswalk_sha256": sha256_file(args.crosswalk),
        "implementation_sha256": sha256_file(Path(__file__)),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"validated {result['fishmip_support_cells']} FishMIP support cells")


if __name__ == "__main__":
    main()
