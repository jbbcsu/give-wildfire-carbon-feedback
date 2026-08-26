#!/usr/bin/env python3
"""Create an explicitly labeled complete-yield-support sensitivity panel.

The GDHY grid support changes across source years. This utility retains only
crop/irrigation/grid cells with an observed, positive yield in every year of a
declared contiguous period. It is a sample-composition sensitivity, not the
primary estimand: conditioning on complete source support may itself select a
nonrepresentative subset and therefore must never be presented as a repair or
an imputation of missing yields.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


CELL_KEYS = ["crop", "irrigation", "lat", "lon_360"]
ROW_KEYS = [*CELL_KEYS, "harvest_year"]


def filter_complete_support(
    panel: pd.DataFrame,
    year_start: int,
    year_end: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if year_start > year_end:
        raise ValueError("year_start must not exceed year_end")
    required = set(ROW_KEYS + ["yield_observed", "yield_t_ha"])
    if missing := required - set(panel.columns):
        raise ValueError(f"Panel lacks required fields {sorted(missing)}")
    if panel.duplicated(ROW_KEYS).any():
        raise ValueError("Panel contains duplicate crop/irrigation/grid/year keys")

    frame = panel.copy()
    if frame[CELL_KEYS].isna().any().any():
        raise ValueError("Cell keys must not contain missing values")
    for name in ("crop", "irrigation"):
        normalized = frame[name].astype(str).str.strip()
        if normalized.eq("").any():
            raise ValueError(f"{name} must not contain blank values")
        frame[name] = normalized
    coordinates = frame[["lat", "lon_360"]].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(coordinates.to_numpy(dtype=float)).all():
        raise ValueError("lat and lon_360 must be finite numeric coordinates")
    if not coordinates["lat"].between(-90, 90).all():
        raise ValueError("lat must lie in [-90, 90]")
    if not ((coordinates["lon_360"] >= 0) & (coordinates["lon_360"] < 360)).all():
        raise ValueError("lon_360 must lie in [0, 360)")
    frame[["lat", "lon_360"]] = coordinates
    years_numeric = pd.to_numeric(frame["harvest_year"], errors="coerce")
    if (
        not np.isfinite(years_numeric.to_numpy(dtype=float)).all()
        or not np.equal(years_numeric, np.floor(years_numeric)).all()
    ):
        raise ValueError("harvest_year must contain finite integers")
    frame["harvest_year"] = years_numeric.astype(int)
    if frame.duplicated(ROW_KEYS).any():
        raise ValueError("Panel contains duplicate normalized crop/irrigation/grid/year keys")
    expected_years = list(range(year_start, year_end + 1))
    observed_years = sorted(frame["harvest_year"].unique().tolist())
    if observed_years != expected_years:
        raise ValueError(
            f"Panel years must equal the complete declared period: {observed_years} != {expected_years}"
        )
    if not pd.api.types.is_bool_dtype(frame["yield_observed"]):
        normalized = frame["yield_observed"].astype(str).str.strip().str.lower()
        if not normalized.isin({"true", "false", "1", "0"}).all():
            raise ValueError("yield_observed must contain only Boolean values")
        frame["yield_observed"] = normalized.isin({"true", "1"})
    else:
        frame["yield_observed"] = frame["yield_observed"].astype(bool)
    yields = pd.to_numeric(frame["yield_t_ha"], errors="coerce")
    observed = frame["yield_observed"]
    observed_yields = yields.loc[observed].to_numpy(dtype=float)
    if not np.isfinite(observed_yields).all() or (observed_yields <= 0).any():
        raise ValueError("Observed yields must be finite and positive")
    frame["yield_t_ha"] = yields

    rows_per_cell = frame.groupby(CELL_KEYS, observed=True).size()
    if not rows_per_cell.eq(len(expected_years)).all():
        raise ValueError("Every source cell must contain one row for every declared year")
    observed_per_cell = frame.groupby(CELL_KEYS, observed=True)["yield_observed"].sum()
    complete_index = observed_per_cell.loc[observed_per_cell.eq(len(expected_years))].index
    marked = frame.set_index(CELL_KEYS).index.isin(complete_index)
    output = frame.loc[marked].copy().sort_values(ROW_KEYS).reset_index(drop=True)
    if output.empty:
        raise ValueError("No complete-support cells remain")
    if not output["yield_observed"].all():
        raise AssertionError("Complete-support output contains an unobserved yield")
    if len(output) != len(complete_index) * len(expected_years):
        raise AssertionError("Complete-support output row count does not reconcile")

    output["yield_support_sensitivity"] = "complete_positive_yield_all_declared_years"
    output["yield_support_conditioning_is_primary"] = False
    output["missing_yield_imputed"] = False
    if "scc_authorized" in output and not output["scc_authorized"].isin([False]).all():
        raise ValueError("Complete-support sensitivity cannot authorize SCC use")

    observed_by_year = (
        frame.groupby("harvest_year", observed=True)["yield_observed"].sum().astype(int).to_dict()
    )
    support_matrix = frame.pivot(
        index=CELL_KEYS, columns="harvest_year", values="yield_observed"
    )
    if support_matrix.isna().any().any():
        raise AssertionError("Source-support matrix does not contain every declared year")
    source_pairs_by_transition: dict[str, int] = {}
    complete_pairs_by_transition: dict[str, int] = {}
    for start, end in zip(expected_years[:-1], expected_years[1:]):
        label = f"{start}-{end}"
        source_pairs_by_transition[label] = int(
            (support_matrix[start] & support_matrix[end]).sum()
        )
        complete_pairs_by_transition[label] = int(len(complete_index))
    source_observed_levels = int(observed.sum())
    output_observed_levels = int(len(output))
    source_consecutive_pairs = sum(source_pairs_by_transition.values())
    complete_consecutive_pairs = sum(complete_pairs_by_transition.values())
    audit: dict[str, object] = {
        "schema_version": 1,
        "status": "complete_yield_support_sample_composition_sensitivity_only",
        "year_start": year_start,
        "year_end": year_end,
        "expected_years": expected_years,
        "source_rows": int(len(frame)),
        "source_cells": int(len(observed_per_cell)),
        "source_observed_yields_by_year": {str(key): value for key, value in observed_by_year.items()},
        "source_observed_yield_levels": source_observed_levels,
        "source_consecutive_observed_pairs_by_transition": source_pairs_by_transition,
        "complete_support_cells": int(len(complete_index)),
        "output_rows": int(len(output)),
        "output_observed_yield_levels": output_observed_levels,
        "complete_support_consecutive_pairs_by_transition": complete_pairs_by_transition,
        "observed_level_retained_fraction": output_observed_levels / source_observed_levels,
        "consecutive_pair_retained_fraction": (
            None
            if source_consecutive_pairs == 0
            else complete_consecutive_pairs / source_consecutive_pairs
        ),
        "excluded_incomplete_support_cells": int(len(observed_per_cell) - len(complete_index)),
        "missing_yield_imputed": False,
        "selection_warning": (
            "Conditioning on complete GDHY source support can select a nonrepresentative "
            "subset; use only as a robustness comparison with the unbalanced primary panel."
        ),
        "causal_interpretation_authorized": False,
        "scc_authorized": False,
    }
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--expected-year-start", required=True, type=int)
    parser.add_argument("--expected-year-end", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--audit-out", required=True, type=Path)
    args = parser.parse_args()

    source = pd.read_parquet(args.panel)
    output, audit = filter_complete_support(
        source, args.expected_year_start, args.expected_year_end
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
