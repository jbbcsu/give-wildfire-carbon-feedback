#!/usr/bin/env python3
"""Outcome-blind soybean first-difference design and heterogeneity preflight."""
from __future__ import annotations

import argparse
import ctypes
import gc
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["lat", "lon_360", "harvest_year"]
WORKER_PEAK_RSS: list[int] = []


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


def debug_rss(label: str) -> None:
    if os.environ.get("SOY_PREFLIGHT_DEBUG_RSS") == "1":
        print(f"RSS {label}: {peak_rss_bytes()}", file=sys.stderr)


def release_memory() -> None:
    gc.collect()
    pa.default_memory_pool().release_unused()
    if sys.platform == "darwin":
        library = ctypes.CDLL(None)
        function = library.malloc_zone_pressure_relief
        function.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        function.restype = ctypes.c_size_t
        function(None, 0)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stream_positive_levels(path: Path, features: list[str], config: dict[str, Any], family: str) -> pd.DataFrame:
    sample = config["sample"]
    basis = config["basis_contract"]
    if family == "heat":
        metadata = ["diagnostic_fit_authorized", "family_stacking_authorized", "causal_interpretation_authorized", "production_fit_authorized", "scc_authorized"]
    else:
        metadata = [
            "irrigation", "exposure_allocation", "weight_source_id", "weight_vintage",
            "response_basis_contract_id", "basis_allocation_order", "fit_authorized", "scc_authorized",
        ]
        if family == "direct":
            metadata.append("nonlinear_post_allocation_transform_authorized")
        if family == "scpdsi":
            metadata.append("direct_weather_terms_included")
    columns = KEYS + ["crop", "yield_observed", "yield_t_ha"] + features + metadata
    parquet = pq.ParquetFile(path)
    require(set(columns) <= set(parquet.schema_arrow.names), f"{family} source schema is incomplete")
    pieces: list[pd.DataFrame] = []
    seen_rows = 0
    positive_rows = 0
    constants: dict[str, set[Any]] = {column: set() for column in metadata}
    for batch in parquet.iter_batches(batch_size=8192, columns=columns, use_threads=False):
        year_index = batch.schema.get_field_index("harvest_year")
        years = batch.column(year_index).to_numpy(zero_copy_only=False)
        year_mask = (years >= int(sample["level_year_minimum"])) & (years <= int(sample["level_year_maximum"]))
        if not np.any(year_mask):
            continue
        train_batch = batch.filter(pa.array(year_mask))
        seen_rows += train_batch.num_rows
        crop_values = pc.unique(train_batch.column(train_batch.schema.get_field_index("crop"))).to_pylist()
        require(crop_values == [sample["crop"]], f"{family} contains an unexpected crop")
        for column in metadata:
            constants[column].update(pc.unique(train_batch.column(train_batch.schema.get_field_index(column))).to_pylist())
        observed = train_batch.column(train_batch.schema.get_field_index("yield_observed")).to_numpy(zero_copy_only=False).astype(bool)
        outcome = train_batch.column(train_batch.schema.get_field_index("yield_t_ha")).to_numpy(zero_copy_only=False)
        mask = observed & (outcome > 0)
        numeric = train_batch.select(KEYS + features).filter(pa.array(mask)).to_pandas()
        positive = numeric.copy()
        positive_rows += len(positive)
        pieces.append(positive)
    require(seen_rows > 0 and positive_rows > 0, f"{family} has no training support")
    if family == "heat":
        expected = {column: config["heat_contract"][column] for column in metadata}
    else:
        expected = {
            "irrigation": basis["irrigation"],
            "exposure_allocation": basis["exposure_allocation"],
            "weight_source_id": basis["weight_source_id"],
            "weight_vintage": basis["weight_vintage"],
            "basis_allocation_order": basis["basis_allocation_order"],
            "response_basis_contract_id": basis[f"{family}_response_basis_contract_id"],
            "fit_authorized": False,
            "scc_authorized": False,
        }
        if family == "direct":
            expected["nonlinear_post_allocation_transform_authorized"] = basis["nonlinear_post_allocation_transform_authorized"]
        if family == "scpdsi":
            expected["direct_weather_terms_included"] = basis["scpdsi_direct_weather_terms_included"]
    for column, value in expected.items():
        require(constants[column] == {value}, f"{family} basis contract differs for {column}: {constants[column]}")
    levels = pd.concat(pieces, ignore_index=True)
    del pieces
    gc.collect()
    pa.default_memory_pool().release_unused()
    require(not levels.duplicated(KEYS).any(), f"{family} has duplicate positive cell-years")
    return levels


def consecutive_differences(levels: pd.DataFrame, features: list[str], config: dict[str, Any]) -> pd.DataFrame:
    sample = config["sample"]
    ordered = levels.sort_values(["lat", "lon_360", "harvest_year"]).reset_index(drop=True)
    grouped = ordered.groupby(["lat", "lon_360"], sort=False, observed=True)
    prior_year = grouped.harvest_year.shift(1)
    consecutive = ordered.harvest_year.sub(prior_year).eq(1)
    differences = grouped[features].diff()
    out = ordered.loc[consecutive, KEYS].copy()
    out = out.loc[out.harvest_year.between(int(sample["pair_year_minimum"]), int(sample["pair_year_maximum"]))]
    differences = differences.loc[out.index]
    differences.columns = [f"d_{column}" for column in features]
    out = pd.concat([out.reset_index(drop=True), differences.reset_index(drop=True)], axis=1)
    require(not out.duplicated(KEYS).any(), "duplicate first-difference pairs")
    return out


def block_labels(frame: pd.DataFrame) -> pd.Series:
    lat_bin = np.floor((frame.lat.to_numpy(dtype=float) + 90.0) / 10.0).astype(int)
    lat_bin = np.minimum(lat_bin, 17)
    lon = np.mod(frame.lon_360.to_numpy(dtype=float), 360.0)
    lon_bin = np.floor(lon / 10.0).astype(int)
    return pd.Series([f"b{a:02d}_{b:02d}" for a, b in zip(lat_bin, lon_bin)], index=frame.index, dtype="string")


def attach_geography(frame: pd.DataFrame, country: pd.DataFrame) -> pd.DataFrame:
    out = frame.merge(country, on=["lat", "lon_360"], how="left", validate="many_to_one")
    out["block10"] = block_labels(out)
    singleton = out.country_count.eq(1) & out.country_label.notna() & out.country_label.astype(str).str.len().gt(0)
    out["singleton_country"] = singleton
    out["country_label"] = out["country_label"].astype("category")
    out["block10"] = out["block10"].astype("category")
    return out


def support_summary(frame: pd.DataFrame) -> dict[str, Any]:
    singleton = frame.loc[frame.singleton_country]
    counts = singleton.groupby("country_label", observed=True).size()
    block_counts = frame.groupby("block10", observed=True).size()
    return {
        "pairs": int(len(frame)),
        "pair_end_year_minimum": int(frame.harvest_year.min()),
        "pair_end_year_maximum": int(frame.harvest_year.max()),
        "pair_end_years": int(frame.harvest_year.nunique()),
        "pairs_by_end_year": {str(int(key)): int(value) for key, value in frame.groupby("harvest_year").size().items()},
        "cells": int(frame[["lat", "lon_360"]].drop_duplicates().shape[0]),
        "countries_singleton": int(singleton.country_label.nunique()),
        "singleton_country_pairs": int(len(singleton)),
        "ambiguous_country_pairs": int(frame.country_count.fillna(0).gt(1).sum()),
        "absent_country_pairs": int((~frame.singleton_country & ~frame.country_count.fillna(0).gt(1)).sum()),
        "blocks10": int(frame.block10.nunique()),
        "effective_country_clusters_inverse_herfindahl": float(counts.sum() ** 2 / np.square(counts).sum()) if len(counts) else 0.0,
        "effective_block10_clusters_inverse_herfindahl": float(block_counts.sum() ** 2 / np.square(block_counts).sum()),
        "largest_singleton_country_pair_share": float(counts.max() / counts.sum()) if len(counts) else None,
        "largest_block10_pair_share": float(block_counts.max() / block_counts.sum()),
    }


def group_codes(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    if len(columns) == 1:
        codes, _ = pd.factorize(frame[columns[0]], sort=True)
    else:
        first, _ = pd.factorize(frame[columns[0]], sort=True)
        second, _ = pd.factorize(frame[columns[1]], sort=True)
        require(np.all(first >= 0) and np.all(second >= 0), f"missing residualization group in {columns}")
        combined = first.astype(np.int64) * (int(second.max()) + 1) + second.astype(np.int64)
        codes, _ = pd.factorize(combined, sort=True)
    require(np.all(codes >= 0), f"missing residualization group in {columns}")
    return codes.astype(np.int64, copy=False)


def residualize(matrix: np.ndarray, codes: np.ndarray) -> np.ndarray:
    groups = int(codes.max()) + 1
    totals = np.zeros((groups, matrix.shape[1]), dtype=np.float64)
    np.add.at(totals, codes, matrix)
    counts = np.bincount(codes, minlength=groups).astype(np.float64)
    matrix -= totals[codes] / counts[codes, None]
    return matrix


def design_diagnostics(frame: pd.DataFrame, columns: list[str], group_columns: list[str], config: dict[str, Any]) -> dict[str, Any]:
    finite = np.isfinite(frame[columns].to_numpy(dtype=np.float64)).all(axis=1)
    needed = list(dict.fromkeys(KEYS + ["country_label", "country_count", "singleton_country", "block10"] + columns))
    work = frame.loc[finite, needed].reset_index(drop=True)
    x = work[columns].to_numpy(dtype=np.float64, copy=True)
    codes = group_codes(work, group_columns)
    residual = residualize(x, codes)
    scale = np.sqrt(np.mean(np.square(residual), axis=0))
    positive_scale = scale > np.finfo(float).eps
    standardized = np.zeros_like(residual)
    standardized[:, positive_scale] = residual[:, positive_scale] / scale[positive_scale]
    gram = standardized.T @ standardized
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    singular = np.sqrt(eigenvalues[::-1])
    relative_tolerance = float(config["numerics"]["rank_relative_tolerance"])
    absolute_tolerance = relative_tolerance * singular[0] if len(singular) else 0.0
    rank = int(np.sum(singular > absolute_tolerance))
    full_rank = rank == len(columns)
    condition = float(singular[0] / singular[-1]) if full_rank and singular[-1] > 0 else None
    maximum_eigenvalue = float(eigenvalues[-1]) if len(eigenvalues) else 0.0
    threshold_squared = absolute_tolerance**2
    keep = eigenvalues > threshold_squared if maximum_eigenvalue > np.finfo(float).eps else np.zeros_like(eigenvalues, dtype=bool)
    if np.any(keep):
        vectors = eigenvectors[:, keep]
        with np.errstate(all="ignore"):
            gram_inverse = (vectors / eigenvalues[keep]) @ vectors.T
            projected = standardized @ gram_inverse
        require(np.isfinite(gram_inverse).all() and np.isfinite(projected).all(), "nonfinite leverage calculation")
        leverage = np.sum(projected * standardized, axis=1)
    else:
        leverage = np.zeros(len(work), dtype=float)
    top_n = max(1, int(math.ceil(float(config["numerics"]["leverage_top_fraction"]) * len(leverage))))
    leverage_sum = float(leverage.sum())
    top_share = float(np.partition(leverage, len(leverage) - top_n)[-top_n:].sum() / leverage_sum) if leverage_sum else None
    effective_rows = float(leverage_sum**2 / np.square(leverage).sum()) if np.square(leverage).sum() else 0.0
    return {
        "support": support_summary(work),
        "residualization_groups": int(np.unique(codes).size),
        "design_columns": columns,
        "columns": int(len(columns)),
        "finite_pairs": int(len(work)),
        "dropped_nonfinite_pairs": int(len(frame) - len(work)),
        "rank": rank,
        "full_column_rank": full_rank,
        "scaled_condition_number": condition,
        "singular_values_scaled": [float(value) for value in singular],
        "residualized_column_rms": {column: float(value) for column, value in zip(columns, scale)},
        "leverage": {
            "maximum": float(leverage.max()) if len(leverage) else None,
            "p99": float(np.quantile(leverage, 0.99)) if len(leverage) else None,
            "top_one_percent_share": top_share,
            "effective_rows_inverse_herfindahl": effective_rows,
            "sum_equals_rank": leverage_sum,
        },
    }


def external_design_diagnostics(config_path: Path, family: str, control: str) -> dict[str, Any]:
    """Run one design diagnostic in a fresh interpreter to release numeric workspaces."""
    worker = ROOT / "scripts/audit_soybean_continuous_design_worker.py"
    completed = subprocess.run(
        [sys.executable, str(worker), "--config", str(config_path), "--family", family, "--control", control],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    require(completed.returncode == 0, f"design worker failed for {family}/{control}: {completed.stderr[-2000:]}")
    payload = json.loads(completed.stdout)
    WORKER_PEAK_RSS.append(int(payload["peak_rss_bytes"]))
    return payload["result"]


def external_country_qualification(config_path: Path) -> dict[str, Any]:
    worker = ROOT / "scripts/audit_soybean_country_qualification_worker.py"
    completed = subprocess.run(
        [sys.executable, str(worker), "--config", str(config_path)],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    require(completed.returncode == 0, f"country qualification worker failed: {completed.stderr[-2000:]}")
    payload = json.loads(completed.stdout)
    WORKER_PEAK_RSS.append(int(payload["peak_rss_bytes"]))
    return payload


def variation_record(values: np.ndarray, global_low: float, global_high: float) -> dict[str, Any]:
    values = values[np.isfinite(values)]
    quantiles = np.quantile(values, [0.01, 0.05, 0.5, 0.95, 0.99])
    return {
        "pairs": int(len(values)),
        "standard_deviation": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "p01": float(quantiles[0]), "p05": float(quantiles[1]), "p50": float(quantiles[2]),
        "p95": float(quantiles[3]), "p99": float(quantiles[4]),
        "two_sided_p05_p95": bool(quantiles[1] < 0 < quantiles[3]),
        "fraction_inside_global_p05_p95": float(np.mean((values >= global_low) & (values <= global_high))),
    }


def geography_variation(frame: pd.DataFrame, key: str, moisture: str, global_low: float, global_high: float) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for label, subset in frame.groupby(key, sort=True, observed=True):
        record = variation_record(subset[moisture].to_numpy(dtype=float), global_low, global_high)
        record.update({
            "pair_end_years": int(subset.harvest_year.nunique()),
            "cells": int(subset[["lat", "lon_360"]].drop_duplicates().shape[0]),
            "occupied_10degree_blocks": int(subset.block10.nunique()),
        })
        records[str(label)] = record
    return records


def control_groups(name: str) -> list[str]:
    return {
        "global_year": ["harvest_year"],
        "country_year": ["country_label", "harvest_year"],
        "block10_year": ["block10", "harvest_year"],
    }[name]


def qualify_countries(frame: pd.DataFrame, columns: list[str], global_low: float, global_high: float, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    thresholds = config["country_qualification"]
    singleton = frame.loc[frame.singleton_country].copy()
    details: dict[str, Any] = {}
    for country, subset in singleton.groupby("country_label", sort=True, observed=True):
        variation = variation_record(subset["d_log1p_precip_mm"].to_numpy(dtype=float), global_low, global_high)
        variation.update({
            "pair_end_years": int(subset.harvest_year.nunique()),
            "cells": int(subset[["lat", "lon_360"]].drop_duplicates().shape[0]),
            "occupied_10degree_blocks": int(subset.block10.nunique()),
        })
        design = design_diagnostics(subset, columns, ["harvest_year"], config)
        checks = {
            "minimum_pairs": len(subset) >= int(thresholds["minimum_pairs"]),
            "minimum_pair_end_years": variation["pair_end_years"] >= int(thresholds["minimum_pair_end_years"]),
            "minimum_cells": variation["cells"] >= int(thresholds["minimum_cells"]),
            "minimum_occupied_10degree_blocks": variation["occupied_10degree_blocks"] >= int(thresholds["minimum_occupied_10degree_blocks"]),
            "two_sided_primary_quantity": variation["two_sided_p05_p95"],
            "minimum_global_overlap": variation["fraction_inside_global_p05_p95"] >= float(thresholds["minimum_fraction_primary_quantity_values_inside_global_p05_p95"]),
            "full_column_rank": design["full_column_rank"],
            "maximum_scaled_condition_number": design["scaled_condition_number"] is not None and design["scaled_condition_number"] <= float(thresholds["maximum_scaled_condition_number"]),
            "maximum_leverage": design["leverage"]["maximum"] is not None and design["leverage"]["maximum"] <= float(thresholds["maximum_maximum_leverage"]),
            "maximum_top_one_percent_leverage_share": design["leverage"]["top_one_percent_share"] is not None and design["leverage"]["top_one_percent_share"] <= float(thresholds["maximum_top_one_percent_leverage_share"]),
        }
        details[str(country)] = {"variation": variation, "design": design, "checks": checks, "qualifies": all(checks.values())}
        release_memory()
    qualified = {country: value for country, value in details.items() if value["qualifies"]}
    qualifying_pairs = sum(value["variation"]["pairs"] for value in qualified.values())
    singleton_pairs = len(singleton)
    largest_share = max((value["variation"]["pairs"] for value in qualified.values()), default=0) / qualifying_pairs if qualifying_pairs else None
    gate_thresholds = config["country_resolution_gate"]
    gate_checks = {
        "minimum_qualifying_countries": len(qualified) >= int(gate_thresholds["minimum_qualifying_countries"]),
        "minimum_singleton_pair_coverage_fraction": singleton_pairs > 0 and qualifying_pairs / singleton_pairs >= float(gate_thresholds["minimum_singleton_pair_coverage_fraction"]),
        "maximum_largest_qualifying_country_pair_share": largest_share is not None and largest_share <= float(gate_thresholds["maximum_largest_qualifying_country_pair_share"]),
    }
    gate = {
        "qualifying_countries": sorted(qualified),
        "qualifying_country_count": len(qualified),
        "singleton_country_pairs": singleton_pairs,
        "qualifying_country_pairs": int(qualifying_pairs),
        "qualifying_pair_coverage_fraction": float(qualifying_pairs / singleton_pairs) if singleton_pairs else 0.0,
        "largest_qualifying_country_pair_share": float(largest_share) if largest_share is not None else None,
        "checks": gate_checks,
        "passes": all(gate_checks.values()),
    }
    return details, gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh audit output required")
    raw = args.config.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config["contract_id"] == "soybean_continuous_design_heterogeneity_preflight_v1", "contract id changed")
    require(config["claim_gates"]["design_preflight_authorized"] is True, "design preflight not authorized")
    require(all(value is False for key, value in config["claim_gates"].items() if key != "design_preflight_authorized"), "downstream claim gate opened")
    for record in config["sources"].values():
        path = resolve(record["path"])
        require(path.is_file(), f"missing source: {path}")
        require(digest(path) == record["sha256"], f"source hash differs: {path}")
    for receipt_key, panel_key, family in (
        ("direct_receipt", "direct_panel", "direct"), ("heat_receipt", "heat_panel", "heat"), ("scpdsi_receipt", "scpdsi_panel", "scpdsi")
    ):
        receipt = load_json(resolve(config["sources"][receipt_key]["path"]))
        require(receipt["status"] == "validated_continuous_candidate_1982_2016", f"{family} receipt status changed")
        require(receipt["output"]["sha256"] == config["sources"][panel_key]["sha256"], f"{family} panel receipt mismatch")
        require(receipt["fit_performed"] is False and receipt["causal_interpretation_authorized"] is False, f"{family} response boundary opened")

    heat_columns = list(config["heat_controls"]["columns"])
    direct_columns = sorted({column for family in ("quantity", "distribution") for column in config["families"][family]["moisture_columns"]})
    scpdsi_columns = sorted({column for family in ("scpdsi_season", "scpdsi_stages") for column in config["families"][family]["moisture_columns"]})
    direct_levels = stream_positive_levels(resolve(config["sources"]["direct_panel"]["path"]), direct_columns, config, "direct")
    direct_positive_levels = len(direct_levels)
    direct_pairs = consecutive_differences(direct_levels, direct_columns, config)
    debug_rss("direct pairs")
    del direct_levels
    gc.collect(); pa.default_memory_pool().release_unused()
    heat_levels = stream_positive_levels(resolve(config["sources"]["heat_panel"]["path"]), heat_columns, config, "heat")
    heat_positive_levels = len(heat_levels)
    heat_pairs = consecutive_differences(heat_levels, heat_columns, config)
    debug_rss("heat pairs")
    del heat_levels
    gc.collect(); pa.default_memory_pool().release_unused()
    direct_heat = direct_pairs.merge(heat_pairs, on=KEYS, how="inner", validate="one_to_one")
    debug_rss("direct heat merge")
    require(len(direct_heat) == len(direct_pairs) == len(heat_pairs), "direct and heat pair support differs")
    del direct_pairs
    gc.collect(); pa.default_memory_pool().release_unused()
    country_columns = ["lat", "lon_360", "country_label", "country_count", "mapspam_5m_cell_count"]
    country = pd.read_parquet(resolve(config["sources"]["country_proxy"]["path"]), columns=country_columns)
    require(not country.duplicated(["lat", "lon_360"]).any(), "country proxy contains duplicate cells")
    direct_heat = attach_geography(direct_heat, country)

    weights = pd.read_parquet(
        resolve(config["sources"]["mirca_weights"]["path"]),
        columns=["lat", "lon_360", "crop", "irrigation", "area_share", "weight_vintage", "production_eligible"],
        filters=[[('crop', '==', config["sample"]["crop"])]],
    )
    weights = weights.loc[weights.crop.astype(str).eq(config["sample"]["crop"])]
    share_error = weights.groupby(["lat", "lon_360"], observed=True).area_share.sum().sub(1.0).abs().max()
    require(set(weights.irrigation.astype(str)) == {"firr", "noirr"}, "MIRCA regimes changed")
    require(set(weights.weight_vintage.astype(str)) == {config["basis_contract"]["weight_vintage"]}, "MIRCA vintage changed")
    require(bool(weights.production_eligible.astype(bool).all()) and float(share_error) <= 1e-12, "MIRCA weight eligibility changed")
    mirca_rows = len(weights)
    mirca_cells = weights[["lat", "lon_360"]].drop_duplicates().shape[0]
    del weights
    release_memory()

    country_payload = external_country_qualification(args.config)
    global_low, global_high = float(country_payload["global_low"]), float(country_payload["global_high"])
    global_variation = country_payload["global_variation"]
    country_variation = country_payload["country_variation"]
    block_variation = country_payload["block_variation"]
    country_details, country_gate = country_payload["country_details"], country_payload["country_gate"]
    debug_rss("country qualification")
    release_memory()

    family_results: dict[str, Any] = {}
    for family in ("distribution", "quantity"):
        family_config = config["families"][family]
        columns = [f"d_{column}" for column in heat_columns + list(family_config["moisture_columns"])]
        alternatives: dict[str, Any] = {}
        for control in config["control_alternatives"]:
            alternatives[control] = external_design_diagnostics(args.config, family, control)
            debug_rss(f"family {family} control {control}")
            release_memory()
        family_results[family] = {
            "role": family_config["role"],
            "mutually_exclusive_family": "scpdsi" if family.startswith("scpdsi") else "direct",
            "control_alternatives": alternatives,
        }
        debug_rss(f"family {family}")
    reference = family_results["quantity"]["control_alternatives"]["country_year"]
    pooled_support_passes = (
        reference["full_column_rank"] and reference["scaled_condition_number"] is not None
        and reference["scaled_condition_number"] <= float(config["country_qualification"]["maximum_scaled_condition_number"])
        and reference["support"]["pair_end_years"] >= int(config["country_qualification"]["minimum_pair_end_years"])
        and reference["support"]["blocks10"] >= int(config["country_qualification"]["minimum_occupied_10degree_blocks"])
    )
    finest = "country_proxy" if country_gate["passes"] else (config["country_resolution_gate"]["fallback_resolution"] if pooled_support_passes else "none")

    direct_support = support_summary(direct_heat)
    del direct_heat
    release_memory()

    scpdsi_levels = stream_positive_levels(resolve(config["sources"]["scpdsi_panel"]["path"]), scpdsi_columns, config, "scpdsi")
    scpdsi_positive_levels = len(scpdsi_levels)
    scpdsi_pairs = consecutive_differences(scpdsi_levels, scpdsi_columns, config)
    debug_rss("scpdsi pairs")
    del scpdsi_levels
    release_memory()
    scpdsi_heat = scpdsi_pairs.merge(heat_pairs, on=KEYS, how="inner", validate="one_to_one")
    debug_rss("scpdsi heat merge")
    del scpdsi_pairs, heat_pairs
    release_memory()
    scpdsi_heat = attach_geography(scpdsi_heat, country)
    for family in ("scpdsi_stages", "scpdsi_season"):
        family_config = config["families"][family]
        columns = [f"d_{column}" for column in heat_columns + list(family_config["moisture_columns"])]
        alternatives = {}
        for control in config["control_alternatives"]:
            alternatives[control] = external_design_diagnostics(args.config, family, control)
            debug_rss(f"family {family} control {control}")
            release_memory()
        family_results[family] = {
            "role": family_config["role"],
            "mutually_exclusive_family": "scpdsi",
            "control_alternatives": alternatives,
        }
    scpdsi_support = support_summary(scpdsi_heat)

    result = {
        "schema": "soybean_continuous_design_heterogeneity_preflight/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_outcome_blind_design_preflight_fail_closed_no_response_fit",
        "contract": {"path": str(args.config), "sha256": hashlib.sha256(raw).hexdigest()},
        "outcome_blinding": {
            "outcome_used_only_as_positive_support_mask": True,
            "outcome_magnitudes_retained_after_masking": False,
            "slopes_or_coefficients_computed": False,
            "production_response_fit_performed": False,
        },
        "basis": {
            "weight_vintage": config["basis_contract"]["weight_vintage"],
            "allocation_order": config["basis_contract"]["basis_allocation_order"],
            "soy_mirca_rows": int(mirca_rows),
            "soy_mirca_cells": int(mirca_cells),
            "maximum_absolute_area_share_sum_error": float(share_error),
        },
        "pair_construction": {
            "level_years": [int(config["sample"]["level_year_minimum"]), int(config["sample"]["level_year_maximum"])],
            "pair_end_years": [int(config["sample"]["pair_year_minimum"]), int(config["sample"]["pair_year_maximum"])],
            "direct_positive_levels": int(direct_positive_levels),
            "heat_positive_levels": int(heat_positive_levels),
            "scpdsi_positive_levels": int(scpdsi_positive_levels),
            "direct_heat_pairs": direct_support,
            "scpdsi_heat_pairs": scpdsi_support,
        },
        "families": family_results,
        "primary_quantity_variation": {
            "global": global_variation,
            "country_proxy": country_variation,
            "block10": block_variation,
        },
        "country_quantity_qualification": {
            "thresholds": config["country_qualification"],
            "countries": country_details,
            "resolution_gate": country_gate,
        },
        "resolution": {
            "pooled_country_year_design_support_passes": bool(pooled_support_passes),
            "country_proxy_resolution_passes": country_gate["passes"],
            "block10_response_strata_authorized": False,
            "finest_support_qualified_geographic_resolution": finest,
            "interpretation": "design support only; neither response heterogeneity nor economic winners/losers is estimated",
        },
        "family_boundary": {
            "direct_quantity_primary": True,
            "direct_distribution_separate": True,
            "scpdsi_separate_mutually_exclusive": True,
            "simultaneous_direct_and_scpdsi_stacking": False,
        },
        "claim_gates": config["claim_gates"],
    }
    parent_rss = peak_rss_bytes()
    worker_rss = max(WORKER_PEAK_RSS, default=0)
    rss = max(parent_rss, worker_rss)
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"memory cap exceeded: {rss} >= {cap}")
    result["resources"] = {"peak_rss_bytes": rss, "parent_peak_rss_bytes": parent_rss, "maximum_worker_peak_rss_bytes": worker_rss, "isolated_design_workers": len(WORKER_PEAK_RSS), "memory_cap_bytes": cap, "memory_gate_passed": True}
    worker_path = ROOT / "scripts/audit_soybean_continuous_design_worker.py"
    country_worker_path = ROOT / "scripts/audit_soybean_country_qualification_worker.py"
    result["implementation"] = {
        "audit": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
        "design_worker": {"path": str(worker_path.relative_to(ROOT)), "sha256": digest(worker_path)},
        "country_worker": {"path": str(country_worker_path.relative_to(ROOT)), "sha256": digest(country_worker_path)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "pair_construction": result["pair_construction"],
        "family_designs": {family: {control: {key: value for key, value in metrics.items() if key in {"finite_pairs", "rank", "full_column_rank", "scaled_condition_number", "leverage"}} for control, metrics in record["control_alternatives"].items()} for family, record in family_results.items()},
        "country_resolution_gate": country_gate, "resolution": result["resolution"], "resources": result["resources"],
    }, indent=2))


if __name__ == "__main__":
    main()
