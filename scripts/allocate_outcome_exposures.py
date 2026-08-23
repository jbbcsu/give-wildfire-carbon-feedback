#!/usr/bin/env python3
"""Collapse irrigation-specific climate exposures to one observed-yield row.

GDHY supplies one gridded crop/season yield outcome, not separate rainfed and
irrigated yields.  This utility therefore refuses to emit duplicated outcome
rows.  It combines explicitly named irrigation-calendar exposures using an
independent, fixed baseline crop-area-share table and records a machine-
readable audit.  It estimates no response and authorizes no SCC input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop"]
PANEL_REQUIRED = set(KEYS + ["irrigation", "yield_observed", "yield_t_ha"])
WEIGHT_KEYS = ["lat", "lon_360", "crop", "irrigation"]
WEIGHT_REQUIRED = set(
    WEIGHT_KEYS
    + ["area_share", "weight_source_id", "weight_vintage", "source_role"]
)
REQUIRED_SOURCE_ROLE = "independent_fixed_baseline_crop_area_share"


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table format for {path}; use CSV or Parquet")


def write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        frame.to_csv(path, index=False)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        frame.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported output format for {path}; use CSV or Parquet")


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    if missing := required - set(frame.columns):
        raise ValueError(f"{label} missing required fields {sorted(missing)}")


def constant_text(frame: pd.DataFrame, column: str) -> str:
    values = frame[column].dropna().astype(str).str.strip().unique()
    if len(values) != 1 or not values[0]:
        raise ValueError(f"Weights must contain exactly one nonblank {column}")
    return values[0]


def validate_outcomes(panel: pd.DataFrame) -> None:
    if panel.duplicated(KEYS + ["irrigation"]).any():
        raise ValueError("Exposure panel has duplicate crop-grid-year-irrigation rows")
    if not panel["yield_observed"].isin([True, False]).all():
        raise ValueError("yield_observed must be Boolean")
    if not panel["yield_observed"].eq(panel["yield_t_ha"].notna()).all():
        raise ValueError("yield_observed does not match yield_t_ha missingness")
    if (panel.loc[panel["yield_observed"], "yield_t_ha"] <= 0).any():
        raise ValueError("Observed yields must be positive")
    for key, group in panel.groupby(KEYS, sort=False, dropna=False):
        if group["yield_observed"].nunique(dropna=False) != 1:
            raise ValueError(f"Outcome missingness differs across exposures for {key}")
        observed = bool(group["yield_observed"].iloc[0])
        if observed and not np.allclose(
            group["yield_t_ha"].to_numpy(dtype=float),
            float(group["yield_t_ha"].iloc[0]),
            rtol=0.0,
            atol=1e-12,
        ):
            raise ValueError(f"Yield values differ across exposures for {key}")


def validate_weights(weights: pd.DataFrame, expected: list[str]) -> tuple[str, str]:
    if "harvest_year" in weights.columns or "year" in weights.columns:
        raise ValueError("Area-share weights must be fixed baseline data, not year varying")
    if weights.duplicated(WEIGHT_KEYS).any():
        raise ValueError("Area-share table has duplicate crop-grid-irrigation rows")
    if set(weights["irrigation"].dropna().astype(str).unique()) != set(expected):
        raise ValueError("Area-share table irrigation labels differ from the declared set")
    shares = pd.to_numeric(weights["area_share"], errors="coerce")
    if not np.isfinite(shares).all() or ((shares < 0) | (shares > 1)).any():
        raise ValueError("area_share must be finite and between zero and one")
    weights["area_share"] = shares
    source_id = constant_text(weights, "weight_source_id")
    vintage = constant_text(weights, "weight_vintage")
    if set(weights["source_role"].dropna().astype(str).str.strip().unique()) != {REQUIRED_SOURCE_ROLE}:
        raise ValueError(f"source_role must be {REQUIRED_SOURCE_ROLE}")
    grouped = weights.groupby(["lat", "lon_360", "crop"], dropna=False)
    bad_labels = grouped["irrigation"].agg(lambda x: set(x.astype(str)) != set(expected))
    if bad_labels.any():
        raise ValueError("Every crop-grid weight group must contain every declared irrigation label")
    totals = grouped["area_share"].sum()
    if not np.allclose(totals.to_numpy(dtype=float), 1.0, rtol=0.0, atol=1e-10):
        raise ValueError("Area shares must sum to one within every crop-grid group")
    return source_id, vintage


def allocate(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
    features: list[str],
    expected: list[str],
) -> tuple[pd.DataFrame, dict[str, object]]:
    require_columns(panel, PANEL_REQUIRED | set(features), "Exposure panel")
    require_columns(weights, WEIGHT_REQUIRED, "Area-share table")
    if not features or len(features) != len(set(features)):
        raise ValueError("Declare at least one unique feature")
    if len(expected) < 2 or len(expected) != len(set(expected)):
        raise ValueError("Declare at least two unique irrigation labels")
    validate_outcomes(panel)
    source_id, vintage = validate_weights(weights, expected)
    if set(panel["irrigation"].dropna().astype(str).unique()) != set(expected):
        raise ValueError("Exposure-panel irrigation labels differ from the declared set")
    numeric = panel[features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("All declared exposure features must be finite numeric values")
    panel = panel.copy()
    panel[features] = numeric
    merged = panel.merge(
        weights[WEIGHT_KEYS + ["area_share"]],
        on=WEIGHT_KEYS,
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise ValueError("One or more exposure rows lack an independent area-share weight")
    merged = merged.drop(columns="_merge")
    counts = merged.groupby(KEYS, dropna=False)["irrigation"].agg(set)
    if not counts.map(lambda x: x == set(expected)).all():
        raise ValueError("Every observed-outcome key must contain every declared irrigation exposure")

    weighted = merged[features].multiply(merged["area_share"], axis=0)
    weighted[KEYS] = merged[KEYS]
    output = weighted.groupby(KEYS, sort=True, as_index=False)[features].sum()
    outcomes = (
        merged.groupby(KEYS, sort=True, as_index=False)
        .agg(yield_observed=("yield_observed", "first"), yield_t_ha=("yield_t_ha", "first"))
    )
    output = outcomes.merge(output, on=KEYS, validate="one_to_one")
    output["irrigation"] = "area_weighted"
    output["exposure_allocation"] = "one_outcome_independent_fixed_area_weighted"
    output["weight_source_id"] = source_id
    output["weight_vintage"] = vintage
    output["scc_authorized"] = False
    if output.duplicated(KEYS).any() or len(output) != panel.groupby(KEYS, dropna=False).ngroups:
        raise AssertionError("Allocation did not produce exactly one row per observed-outcome key")
    audit: dict[str, object] = {
        "schema_version": 1,
        "purpose": "Prevent duplicated aggregate yield outcomes across irrigation exposures.",
        "boundary": "Data-contract output only; no response coefficient or SCC use is authorized.",
        "input_rows": int(len(panel)),
        "output_rows": int(len(output)),
        "outcome_keys": int(panel.groupby(KEYS, dropna=False).ngroups),
        "observed_outcomes": int(output["yield_observed"].sum()),
        "irrigation_labels": expected,
        "features": features,
        "weight_source_id": source_id,
        "weight_vintage": vintage,
        "weight_source_role": REQUIRED_SOURCE_ROLE,
        "weights_fixed_across_years": True,
        "one_row_per_outcome": True,
        "scc_authorized": False,
    }
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--feature", action="append", required=True)
    parser.add_argument("--expected-irrigation", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    panel = read_table(Path(args.panel))
    weights = read_table(Path(args.weights))
    output, audit = allocate(panel, weights, args.feature, args.expected_irrigation)
    write_table(output, Path(args.out))
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
