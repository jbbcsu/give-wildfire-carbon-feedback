#!/usr/bin/env python3
"""Independently validate the soybean no-fit design/heterogeneity preflight."""
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

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["lat", "lon_360", "harvest_year"]


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def positive_levels(path: Path, features: list[str], minimum: int, maximum: int) -> pd.DataFrame:
    columns = KEYS + ["yield_observed", "yield_t_ha"] + features
    pieces: list[pd.DataFrame] = []
    for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=columns, use_threads=False):
        year = batch.column(batch.schema.get_field_index("harvest_year")).to_numpy(zero_copy_only=False)
        observed = batch.column(batch.schema.get_field_index("yield_observed")).to_numpy(zero_copy_only=False).astype(bool)
        outcome = batch.column(batch.schema.get_field_index("yield_t_ha")).to_numpy(zero_copy_only=False)
        mask = (year >= minimum) & (year <= maximum) & observed & (outcome > 0)
        if np.any(mask):
            pieces.append(batch.select(KEYS + features).filter(pa.array(mask)).to_pandas())
    out = pd.concat(pieces, ignore_index=True)
    require(not out.duplicated(KEYS).any(), "duplicate positive levels")
    return out


def differences(levels: pd.DataFrame, features: list[str], minimum: int, maximum: int) -> pd.DataFrame:
    frame = levels.sort_values(KEYS[:2] + ["harvest_year"]).reset_index(drop=True)
    group = frame.groupby(KEYS[:2], sort=False, observed=True)
    keep = frame.harvest_year.sub(group.harvest_year.shift()).eq(1) & frame.harvest_year.between(minimum, maximum)
    delta = group[features].diff().loc[keep]
    delta.columns = [f"d_{column}" for column in features]
    return pd.concat([frame.loc[keep, KEYS].reset_index(drop=True), delta.reset_index(drop=True)], axis=1)


def blocks(frame: pd.DataFrame) -> np.ndarray:
    lat = np.minimum(np.floor((frame.lat.to_numpy(float) + 90.0) / 10.0).astype(int), 17)
    lon = np.floor(np.mod(frame.lon_360.to_numpy(float), 360.0) / 10.0).astype(int)
    return np.asarray([f"b{a:02d}_{b:02d}" for a, b in zip(lat, lon)], dtype=object)


def support(frame: pd.DataFrame) -> dict:
    singleton = frame.country_count.eq(1) & frame.country_label.notna()
    country_counts = frame.loc[singleton].groupby("country_label").size()
    block_counts = frame.groupby("block10").size()
    return {
        "pairs": len(frame), "years": frame.harvest_year.nunique(),
        "year_minimum": int(frame.harvest_year.min()), "year_maximum": int(frame.harvest_year.max()),
        "cells": frame[["lat", "lon_360"]].drop_duplicates().shape[0],
        "singleton_pairs": int(singleton.sum()), "ambiguous_pairs": int(frame.country_count.fillna(0).gt(1).sum()),
        "absent_pairs": int((~singleton & ~frame.country_count.fillna(0).gt(1)).sum()),
        "countries": int(country_counts.size), "blocks": int(block_counts.size),
        "effective_countries": float(country_counts.sum() ** 2 / np.square(country_counts).sum()),
        "effective_blocks": float(block_counts.sum() ** 2 / np.square(block_counts).sum()),
    }


def independent_design(frame: pd.DataFrame, columns: list[str]) -> dict:
    singleton = frame.country_count.eq(1) & frame.country_label.notna()
    work = frame.loc[singleton, ["country_label", "harvest_year"] + columns].copy()
    x = work[columns].astype(float)
    centered = x - work.assign(**{column: x[column] for column in columns}).groupby(["country_label", "harvest_year"], observed=True)[columns].transform("mean")
    matrix = centered.to_numpy(float)
    scale = np.sqrt(np.mean(matrix * matrix, axis=0))
    standardized = matrix / scale
    gram = standardized.T @ standardized
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    singular = np.sqrt(eigenvalues[::-1])
    tolerance = 1e-10 * singular[0]
    rank = int((singular > tolerance).sum())
    condition = float(singular[0] / singular[-1])
    with np.errstate(all="ignore"):
        inverse = (eigenvectors / eigenvalues) @ eigenvectors.T
        projected = standardized @ inverse
    require(np.isfinite(inverse).all() and np.isfinite(projected).all(), "nonfinite independent leverage calculation")
    leverage = np.sum(projected * standardized, axis=1)
    top_n = int(math.ceil(0.01 * len(leverage)))
    return {
        "pairs": len(work), "rank": rank, "condition": condition,
        "maximum_leverage": float(leverage.max()), "p99_leverage": float(np.quantile(leverage, 0.99)),
        "top_one_percent_share": float(np.partition(leverage, len(leverage) - top_n)[-top_n:].sum() / leverage.sum()),
        "leverage_sum": float(leverage.sum()),
    }


def close(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    require(digest(args.config) == audit["contract"]["sha256"], "audit/config binding differs")
    for record in config["sources"].values():
        require(digest(resolve(record["path"])) == record["sha256"], f"source hash differs: {record['path']}")

    heat = list(config["heat_controls"]["columns"])
    quantity = list(config["families"]["quantity"]["moisture_columns"])
    years = config["sample"]
    direct_levels = positive_levels(resolve(config["sources"]["direct_panel"]["path"]), quantity, int(years["level_year_minimum"]), int(years["level_year_maximum"]))
    heat_levels = positive_levels(resolve(config["sources"]["heat_panel"]["path"]), heat, int(years["level_year_minimum"]), int(years["level_year_maximum"]))
    direct = differences(direct_levels, quantity, int(years["pair_year_minimum"]), int(years["pair_year_maximum"]))
    heat_pairs = differences(heat_levels, heat, int(years["pair_year_minimum"]), int(years["pair_year_maximum"]))
    primary = direct.merge(heat_pairs, on=KEYS, validate="one_to_one")
    country = pd.read_parquet(resolve(config["sources"]["country_proxy"]["path"]), columns=["lat", "lon_360", "country_label", "country_count"])
    primary = primary.merge(country, on=["lat", "lon_360"], how="left", validate="many_to_one")
    primary["block10"] = blocks(primary)
    rebuilt_support = support(primary)
    expected_support = audit["pair_construction"]["direct_heat_pairs"]
    comparisons = {
        "pairs": expected_support["pairs"], "years": expected_support["pair_end_years"],
        "year_minimum": expected_support["pair_end_year_minimum"], "year_maximum": expected_support["pair_end_year_maximum"],
        "cells": expected_support["cells"], "singleton_pairs": expected_support["singleton_country_pairs"],
        "ambiguous_pairs": expected_support["ambiguous_country_pairs"], "absent_pairs": expected_support["absent_country_pairs"],
        "countries": expected_support["countries_singleton"], "blocks": expected_support["blocks10"],
    }
    for key, expected in comparisons.items():
        require(rebuilt_support[key] == expected, f"primary support differs: {key}")
    require(close(rebuilt_support["effective_countries"], expected_support["effective_country_clusters_inverse_herfindahl"]), "effective country clusters differ")
    require(close(rebuilt_support["effective_blocks"], expected_support["effective_block10_clusters_inverse_herfindahl"]), "effective block clusters differ")

    columns = [f"d_{column}" for column in heat + quantity]
    rebuilt_design = independent_design(primary, columns)
    expected_design = audit["families"]["quantity"]["control_alternatives"]["country_year"]
    require(rebuilt_design["pairs"] == expected_design["finite_pairs"], "quantity design pairs differ")
    require(rebuilt_design["rank"] == expected_design["rank"], "quantity design rank differs")
    require(close(rebuilt_design["condition"], expected_design["scaled_condition_number"]), "quantity condition differs")
    require(close(rebuilt_design["maximum_leverage"], expected_design["leverage"]["maximum"]), "quantity maximum leverage differs")
    require(close(rebuilt_design["p99_leverage"], expected_design["leverage"]["p99"]), "quantity p99 leverage differs")
    require(close(rebuilt_design["top_one_percent_share"], expected_design["leverage"]["top_one_percent_share"]), "quantity top leverage share differs")
    require(close(rebuilt_design["leverage_sum"], expected_design["rank"]), "quantity leverage trace differs")

    scpdsi_levels = positive_levels(resolve(config["sources"]["scpdsi_panel"]["path"]), [], int(years["level_year_minimum"]), int(years["level_year_maximum"]))
    scpdsi_pairs = differences(scpdsi_levels.assign(_one=1.0), ["_one"], int(years["pair_year_minimum"]), int(years["pair_year_maximum"]))
    scpdsi_keys = scpdsi_pairs[KEYS].merge(heat_pairs[KEYS], on=KEYS, validate="one_to_one")
    expected_scpdsi = audit["pair_construction"]["scpdsi_heat_pairs"]
    require(len(scpdsi_levels) == audit["pair_construction"]["scpdsi_positive_levels"], "scPDSI positive levels differ")
    require(len(scpdsi_keys) == expected_scpdsi["pairs"], "scPDSI pair support differs")

    for family, record in audit["families"].items():
        for control, design in record["control_alternatives"].items():
            require(design["full_column_rank"] and design["rank"] == design["columns"], f"rank gate differs: {family}/{control}")
            require(design["scaled_condition_number"] is not None and design["scaled_condition_number"] < 10.0, f"condition gate differs: {family}/{control}")
            require(close(design["leverage"]["sum_equals_rank"], design["rank"]), f"leverage trace differs: {family}/{control}")
    country_gate = audit["country_quantity_qualification"]["resolution_gate"]
    require(country_gate["qualifying_countries"] == ["CHN", "USA"] and country_gate["passes"] is False, "country gate differs")
    require(audit["resolution"]["finest_support_qualified_geographic_resolution"] == "pooled_global", "resolution differs")
    require(audit["outcome_blinding"]["slopes_or_coefficients_computed"] is False, "slope boundary opened")
    require(all(value is False for key, value in audit["claim_gates"].items() if key != "design_preflight_authorized"), "downstream gate opened")

    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"validation memory cap exceeded: {rss}")
    result = {
        "schema": "soybean_continuous_design_heterogeneity_preflight_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_outcome_blind_design_preflight_fail_closed",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "audit": {"path": str(args.audit), "sha256": digest(args.audit)},
        "checks": {
            "direct_positive_levels": len(direct_levels), "heat_positive_levels": len(heat_levels),
            "direct_heat_support": rebuilt_support, "quantity_country_year_design": rebuilt_design,
            "scpdsi_positive_levels": len(scpdsi_levels), "scpdsi_heat_pairs": len(scpdsi_keys),
            "country_resolution_gate_passes": False, "finest_resolution": "pooled_global",
            "response_fit_or_downstream_claim_authorized": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
