#!/usr/bin/env python3
"""Run the frozen total-rainfall versus distribution/extremes predictive test."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
NUMERICAL_BASE = PROJECT / "us_county_validation/scripts/evaluate_nass_sorghum_cotton_pdsi_predictive.py"
LEVELS = {
    "tmean": "tmean_c", "precip": "precip_mm",
    "stage1_amount": "stage1_precip_mm", "stage2_amount": "stage2_precip_mm", "stage3_amount": "stage3_precip_mm",
    "stage1_share": "stage1_precip_share", "stage2_share": "stage2_precip_share",
    "wet_days": "wet_days_ge_1mm", "cdd": "cdd_max_days", "rx5day": "rx5day_mm",
}
MODELS = {
    "temperature_trend_only": ["delta_tmean", "delta_tmean_squared"],
    "total_quantity": ["delta_tmean", "delta_tmean_squared", "delta_precip", "delta_precip_squared"],
    "stage_amounts": ["delta_tmean", "delta_tmean_squared", "delta_stage1_amount", "delta_stage2_amount", "delta_stage3_amount"],
    "quantity_plus_stage_shares": ["delta_tmean", "delta_tmean_squared", "delta_precip", "delta_precip_squared", "delta_stage1_share", "delta_stage2_share"],
    "quantity_plus_extremes": ["delta_tmean", "delta_tmean_squared", "delta_precip", "delta_precip_squared", "delta_wet_days", "delta_cdd", "delta_rx5day"],
}
COMPARISONS = {
    "total_quantity_vs_temperature": ("temperature_trend_only", "total_quantity"),
    "stage_amounts_vs_total_quantity": ("total_quantity", "stage_amounts"),
    "stage_shares_vs_total_quantity": ("total_quantity", "quantity_plus_stage_shares"),
    "extremes_vs_total_quantity": ("total_quantity", "quantity_plus_extremes"),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT)
    return result


def load_numerical_base():
    spec = importlib.util.spec_from_file_location("predictive_numerics", NUMERICAL_BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load validated predictive numerics")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_differences(panel: pd.DataFrame) -> pd.DataFrame:
    required = {"crop", "practice", "county_geoid", "state_alpha", "harvest_year", "yield_value", *LEVELS.values()}
    if missing := required - set(panel.columns):
        raise ValueError(f"direct-weather panel lacks {sorted(missing)}")
    if panel.pdsi_spei_scpdsi_coincluded.any():
        raise ValueError("direct-weather input co-includes a drought-index family")
    rows = []
    for (_, _), frame in panel.groupby(["crop", "practice"], observed=True):
        frame = frame.sort_values(["county_geoid", "harvest_year"]).copy()
        frame["log_yield"] = np.log(frame.yield_value.astype(float))
        grouped = frame.groupby("county_geoid", observed=True, sort=False)
        frame["previous_year"] = grouped.harvest_year.shift(1)
        frame["previous_log_yield"] = grouped.log_yield.shift(1)
        for name, column in LEVELS.items():
            frame[f"previous_{name}"] = grouped[column].shift(1)
        frame = frame.loc[frame.harvest_year.sub(frame.previous_year).eq(1)].copy()
        frame["delta_log_yield"] = frame.log_yield - frame.previous_log_yield
        for name, column in LEVELS.items():
            frame[f"delta_{name}"] = frame[column] - frame[f"previous_{name}"]
        frame["delta_tmean_squared"] = np.square(frame.tmean_c) - np.square(frame.previous_tmean)
        frame["delta_precip_squared"] = np.square(frame.precip_mm) - np.square(frame.previous_precip)
        rows.append(frame[[
            "crop", "practice", "county_geoid", "state_alpha", "previous_year", "harvest_year", "delta_log_yield",
            *sorted({column for columns in MODELS.values() for column in columns}),
        ]])
    result = pd.concat(rows, ignore_index=True)
    keys = ["crop", "practice", "county_geoid", "harvest_year"]
    numeric = ["delta_log_yield", *sorted({column for columns in MODELS.values() for column in columns})]
    if result.empty or result.duplicated(keys).any() or not np.isfinite(result[numeric]).all().all():
        raise ValueError("direct-weather differences fail finite/unique gates")
    return result.sort_values(keys).reset_index(drop=True)


def evaluate(differences: pd.DataFrame, numerical) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    results, summaries = [], []
    for (crop, practice), frame in differences.groupby(["crop", "practice"], observed=True, sort=True):
        frame = frame.reset_index(drop=True)
        development = frame.harvest_year.le(2007).to_numpy(bool)
        terminal = frame.harvest_year.ge(2008).to_numpy(bool)
        counts = frame.loc[development].state_alpha.astype(str).value_counts().sort_index()
        states = list(map(str, counts.loc[counts.ge(40)].index))
        if len(states) < 5:
            raise ValueError(f"{crop}/{practice} has fewer than five eligible state folds")
        splits = []
        for state in states:
            state_mask = frame.state_alpha.astype(str).eq(state).to_numpy(bool)
            splits.append(("development_leave_state_out", state, development & ~state_mask, development & state_mask))
        development_counties = set(frame.loc[development, "county_geoid"].astype(str))
        terminal_same = terminal & frame.county_geoid.astype(str).isin(development_counties).to_numpy(bool)
        if terminal_same.sum() < 50:
            raise ValueError(f"{crop}/{practice} has fewer than 50 terminal rows")
        splits.append(("terminal_same_counties", "2008_2018", development, terminal_same))
        stratum_rows = []
        for split, split_id, train_before, test in splits:
            train, purged = numerical.purge(frame, train_before, test)
            for model, columns in MODELS.items():
                row = {
                    "crop": str(crop), "practice": str(practice), "split": split, "split_id": split_id,
                    "model": model, "train_rows_before_endpoint_purge": int(train_before.sum()),
                    "train_rows_purged_shared_level_endpoint": purged, "level_endpoints_disjoint": True,
                    **numerical.fit_predict(frame, columns, train, test),
                }
                results.append(row); stratum_rows.append(row)
        summary = {"crop": str(crop), "practice": str(practice), "eligible_development_states": states}
        for name, (comparator, candidate) in COMPARISONS.items():
            summary[name] = numerical.comparison(stratum_rows, comparator, candidate)
        summaries.append(summary)
    return results, summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--join", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    join_path, protocol_path, out_path = map(project_path, [args.join, args.protocol, args.out])
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite {out_path}")
    numerical = load_numerical_base()
    differences = build_differences(pd.read_parquet(join_path))
    results, summaries = evaluate(differences, numerical)
    support = {}
    for (crop, practice), frame in differences.groupby(["crop", "practice"], observed=True):
        support[f"{crop}:{practice}"] = {
            "difference_rows": len(frame), "counties": int(frame.county_geoid.nunique()),
            "states": int(frame.state_alpha.nunique()), "year_min": int(frame.harvest_year.min()),
            "year_max": int(frame.harvest_year.max()), "terminal_rows": int(frame.harvest_year.ge(2008).sum()),
        }
    payload = {
        "schema": "us_sorghum_cotton_direct_weather_predictive_v1",
        "status": "completed_frozen_quantity_distribution_extremes_predictive_diagnostic",
        "estimand": "out_of_sample_prediction_of_consecutive_year_log_yield_change",
        "moisture_family": "direct_precipitation_with_temperature_controls_no_drought_index_coinclusion",
        "inputs": {
            "joined_panel": {"path": args.join, "sha256": digest(join_path)},
            "protocol": {"path": args.protocol, "sha256": digest(protocol_path)},
            "numerical_base": {"path": str(NUMERICAL_BASE.relative_to(PROJECT)), "sha256": digest(NUMERICAL_BASE)},
            "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        },
        "first_difference_support": support, "model_families": MODELS,
        "results": results, "summaries": summaries,
        "coefficients_emitted": False, "row_predictions_emitted": False,
        "predictive_diagnostic_authorized": True, "causal_claim_authorized": False,
        "irrigation_treatment_claim_authorized": False, "national_representativeness_claim_authorized": False,
        "future_climate_claim_authorized": False, "global_transfer_authorized": False,
        "damage_claim_authorized": False, "scc_claim_authorized": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"out": args.out, "support": support, "summaries": summaries}, indent=2))


if __name__ == "__main__":
    main()
