#!/usr/bin/env python3
"""Independently reconstruct and validate the wheat/PDSI predictive diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
PANEL_BUILDER = PROJECT / "us_county_validation/scripts/estimate_wheat_practice_pdsi_sensitivity.py"
MODEL_COLUMNS = {
    "trend_only": (),
    "pdsi_linear": ("delta_pdsi",),
    "pdsi_quadratic": ("delta_pdsi", "delta_pdsi_squared"),
}
METRIC_FIELDS = ("rmse", "mae", "r2_oos", "correlation")
COUNT_FIELDS = (
    "train_rows_before_endpoint_purge",
    "train_rows_purged_shared_level_endpoint",
    "training_rows",
    "test_rows",
    "candidate_predictor_count_including_year_terms",
    "retained_scaled_predictor_count",
    "design_rank_including_intercept",
    "dropped_svd_directions",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def load_panel_builder():
    spec = importlib.util.spec_from_file_location("wheat_pdsi_panel_builder", PANEL_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load weighted wheat panel builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reconstruct_differences(level: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for practice in ("irrigated", "non_irrigated"):
        outcome = f"log_yield_{practice}"
        table = level[["county_geoid", "state", "harvest_year", "pdsi", outcome]].copy()
        table.sort_values(["county_geoid", "harvest_year"], inplace=True)
        grouped = table.groupby("county_geoid", observed=True, sort=False)
        previous_year = grouped["harvest_year"].shift()
        previous_outcome = grouped[outcome].shift()
        previous_pdsi = grouped["pdsi"].shift()
        keep = table.harvest_year.eq(previous_year.add(1))
        piece = pd.DataFrame({
            "county_geoid": table.loc[keep, "county_geoid"].astype(str),
            "state": table.loc[keep, "state"].astype(str),
            "irrigation_practice": practice,
            "difference_previous_harvest_year": previous_year.loc[keep].astype(int),
            "harvest_year": table.loc[keep, "harvest_year"].astype(int),
            "delta_log_yield": (
                table.loc[keep, outcome] - previous_outcome.loc[keep]
            ).astype(float),
            "delta_pdsi": (
                table.loc[keep, "pdsi"] - previous_pdsi.loc[keep]
            ).astype(float),
            "delta_pdsi_squared": (
                table.loc[keep, "pdsi"].pow(2) - previous_pdsi.loc[keep].pow(2)
            ).astype(float),
        })
        pieces.append(piece)
    differences = pd.concat(pieces, ignore_index=True)
    differences.sort_values(
        ["county_geoid", "irrigation_practice", "harvest_year"], inplace=True,
    )
    differences.reset_index(drop=True, inplace=True)
    if differences.empty or not np.isfinite(
        differences[["delta_log_yield", "delta_pdsi", "delta_pdsi_squared"]]
    ).all().all():
        raise ValueError("independent first-difference reconstruction failed")
    return differences


def support_table(differences: pd.DataFrame) -> dict[str, dict[str, int]]:
    return {
        str(practice): {
            "difference_rows": int(len(part)),
            "counties": int(part.county_geoid.nunique()),
            "states": int(part.state.nunique()),
            "difference_year_min": int(part.harvest_year.min()),
            "difference_year_max": int(part.harvest_year.max()),
            "terminal_rows": int(part.harvest_year.ge(2001).sum()),
        }
        for practice, part in differences.groupby(
            "irrigation_practice", observed=True, sort=True
        )
    }


def purged_training_mask(
    frame: pd.DataFrame, candidate: np.ndarray, test: np.ndarray,
) -> tuple[np.ndarray, int]:
    test_endpoints: set[tuple[str, str, int]] = set()
    for row in frame.loc[test].itertuples(index=False):
        test_endpoints.update({
            (str(row.county_geoid), str(row.irrigation_practice), int(row.harvest_year)),
            (
                str(row.county_geoid), str(row.irrigation_practice),
                int(row.difference_previous_harvest_year),
            ),
        })
    keep = candidate.copy()
    for position in np.flatnonzero(candidate):
        row = frame.iloc[int(position)]
        identifiers = (
            (str(row.county_geoid), str(row.irrigation_practice), int(row.harvest_year)),
            (
                str(row.county_geoid), str(row.irrigation_practice),
                int(row.difference_previous_harvest_year),
            ),
        )
        if any(identifier in test_endpoints for identifier in identifiers):
            keep[position] = False
    return keep, int(candidate.sum() - keep.sum())


def independently_fit(
    frame: pd.DataFrame, columns: tuple[str, ...], train: np.ndarray, test: np.ndarray,
) -> dict[str, Any]:
    year = frame.harvest_year.to_numpy(dtype=float)
    centered_year = (
        year - float(year[train].mean())
    ) / float(year[train].std(ddof=0))
    predictors = [frame[name].to_numpy(dtype=float) for name in columns]
    predictors.extend((centered_year, np.square(centered_year)))
    raw = np.column_stack(predictors)
    means = raw[train].mean(axis=0)
    scales = raw[train].std(axis=0, ddof=0)
    floor = np.maximum(1e-10, 1e-8 * np.max(np.abs(raw[train]), axis=0))
    retained = np.isfinite(scales) & (scales > floor)
    standardized = (raw[:, retained] - means[retained]) / scales[retained]
    design = np.column_stack((np.ones(len(frame)), standardized))
    y_train = frame.loc[train, "delta_log_yield"].to_numpy(dtype=float)
    beta, _, rank, singular = np.linalg.lstsq(
        design[train], y_train, rcond=1e-10,
    )
    prediction = np.einsum("ij,j->i", design[test], beta, optimize=True)
    observed = frame.loc[test, "delta_log_yield"].to_numpy(dtype=float)
    residual = observed - prediction
    denominator = float(np.sum(np.square(observed - float(y_train.mean()))))
    correlation = None
    if len(observed) > 1 and np.std(observed) > 0 and np.std(prediction) > 0:
        correlation = float(np.corrcoef(observed, prediction)[0, 1])
    active_rank = int(np.sum(singular > singular[0] * 1e-10))
    if int(rank) != active_rank:
        raise ValueError("independent least-squares rank does not match SVD threshold")
    return {
        "rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "mae": float(np.mean(np.abs(residual))),
        "r2_oos": None if denominator <= 0 else float(
            1 - np.sum(np.square(residual)) / denominator
        ),
        "correlation": correlation,
        "candidate_predictor_count_including_year_terms": int(raw.shape[1]),
        "retained_scaled_predictor_count": int(retained.sum()),
        "design_rank_including_intercept": active_rank,
        "dropped_svd_directions": int(len(singular) - active_rank),
        "training_rows": int(train.sum()),
        "test_rows": int(test.sum()),
    }


def reconstruct_results(differences: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for practice, part in differences.groupby(
        "irrigation_practice", observed=True, sort=True
    ):
        frame = part.reset_index(drop=True)
        development = frame.harvest_year.lt(2001).to_numpy(dtype=bool)
        terminal = ~development
        counts = frame.loc[development, "state"].astype(str).value_counts()
        eligible = sorted(map(str, counts.loc[counts.ge(50)].index))
        split_masks: list[tuple[str, str, np.ndarray, np.ndarray]] = []
        for state in eligible:
            held_out = frame.state.astype(str).eq(state).to_numpy(dtype=bool)
            split_masks.append((
                "development_leave_state_out", state,
                development & ~held_out, development & held_out,
            ))
        development_counties = set(frame.loc[development, "county_geoid"].astype(str))
        terminal_same = terminal & frame.county_geoid.astype(str).isin(
            development_counties
        ).to_numpy(dtype=bool)
        split_masks.append((
            "terminal_same_counties", "2001_2007", development, terminal_same,
        ))
        for split, split_id, candidate, test in split_masks:
            train, purged = purged_training_mask(frame, candidate, test)
            for model, columns in MODEL_COLUMNS.items():
                rows.append({
                    "irrigation_practice": str(practice),
                    "split": split,
                    "split_id": split_id,
                    "model": model,
                    "train_rows_before_endpoint_purge": int(candidate.sum()),
                    "train_rows_purged_shared_level_endpoint": purged,
                    "level_endpoints_disjoint": True,
                    **independently_fit(frame, columns, train, test),
                })
    return rows


def compare_results(
    reported: list[dict[str, Any]], reconstructed: list[dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    key_fields = ("irrigation_practice", "split", "split_id", "model")
    report_index = {tuple(row[field] for field in key_fields): row for row in reported}
    check_index = {tuple(row[field] for field in key_fields): row for row in reconstructed}
    if report_index.keys() != check_index.keys() or len(report_index) != len(reported):
        raise ValueError("predictive result keys differ or are duplicated")
    maximum = 0.0
    checks = []
    for key in sorted(report_index):
        source = report_index[key]
        check = check_index[key]
        for field in COUNT_FIELDS:
            if int(source[field]) != int(check[field]):
                raise ValueError(f"count mismatch for {key}/{field}")
        if source.get("level_endpoints_disjoint") is not True:
            raise ValueError(f"endpoint-disjoint flag is closed for {key}")
        differences = {}
        for field in METRIC_FIELDS:
            if source[field] is None or check[field] is None:
                if source[field] != check[field]:
                    raise ValueError(f"null metric mismatch for {key}/{field}")
                difference = 0.0
            else:
                difference = abs(float(source[field]) - float(check[field]))
            differences[field] = difference
            maximum = max(maximum, difference)
        checks.append({
            "irrigation_practice": key[0], "split": key[1],
            "split_id": key[2], "model": key[3],
            "maximum_absolute_metric_difference": max(differences.values()),
        })
    return maximum, checks


def validate_summaries(result: dict[str, Any]) -> None:
    indexed = {
        (row["irrigation_practice"], row["split"], row["split_id"], row["model"]): row
        for row in result["results"]
    }
    for summary in result["summaries"]:
        practice = summary["irrigation_practice"]
        passes = []
        for state in summary["eligible_development_states"]:
            baseline = float(indexed[(
                practice, "development_leave_state_out", state, "trend_only",
            )]["rmse"])
            linear = float(indexed[(
                practice, "development_leave_state_out", state, "pdsi_linear",
            )]["rmse"])
            improvement = baseline - linear
            floor = max(0.0001, 0.01 * baseline)
            if abs(improvement - float(summary["development_state_improvements"][state])) > 1e-12:
                raise ValueError("reported development improvement is inconsistent")
            if abs(floor - float(summary["development_state_required_floors"][state])) > 1e-12:
                raise ValueError("reported development floor is inconsistent")
            passes.append(improvement >= floor)
        terminal_baseline = float(indexed[(
            practice, "terminal_same_counties", "2001_2007", "trend_only",
        )]["rmse"])
        terminal_linear = float(indexed[(
            practice, "terminal_same_counties", "2001_2007", "pdsi_linear",
        )]["rmse"])
        terminal_improvement = terminal_baseline - terminal_linear
        gate = bool(all(passes) and terminal_improvement > 0)
        if gate != bool(summary["pdsi_linear_predictive_gate_passed"]):
            raise ValueError("reported predictive gate is inconsistent")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--resource", required=True)
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    result_path = project_path(arguments.result)
    resource_path = project_path(arguments.resource)
    out_path = project_path(arguments.out)
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite {out_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("schema") != "us_wheat_practice_pdsi_predictive_v1":
        raise ValueError("wrong predictive result schema")
    if result.get("moisture_family") != "pdsi_only_not_stacked_with_direct_rainfall":
        raise ValueError("PDSI-only family boundary is absent")
    if result.get("predictive_diagnostic_authorized") is not True:
        raise ValueError("predictive diagnostic flag is unexpectedly closed")
    for gate in (
        "causal_claim_authorized", "irrigation_treatment_claim_authorized",
        "national_representativeness_claim_authorized",
        "future_drought_claim_authorized", "global_transfer_authorized",
        "damage_claim_authorized", "scc_claim_authorized",
    ):
        if result.get(gate) is not False:
            raise ValueError(f"result unexpectedly opens {gate}")
    serialized_models = json.dumps(result.get("model_families", {})).lower()
    for forbidden in ("rainfall", "wet-day", "intensity", "dry-spell"):
        if forbidden in serialized_models:
            raise ValueError(f"forbidden stacked feature found: {forbidden}")
    for record in result["inputs"].values():
        path = project_path(record["path"])
        if sha256(path) != record["sha256"]:
            raise ValueError(f"frozen input identity changed: {record['path']}")
    resource = json.loads(resource_path.read_text(encoding="utf-8"))
    if (
        resource.get("status") != "command_completed"
        or int(resource.get("returncode", -1)) != 0
        or int(resource.get("peak_rss_bytes", 2**63)) > 512 * 1024 * 1024
    ):
        raise ValueError("production resource receipt failed")

    builder = load_panel_builder()
    join_path = project_path(result["inputs"]["joined_panel"]["path"])
    calendar_path = project_path(result["inputs"]["calendar_definitions"]["path"])
    weights = builder.wheat_state_weights(calendar_path)
    level, panel_audit = builder.prepare_panel(join_path, weights)
    if panel_audit != result["level_panel"]:
        raise ValueError("level-panel audit differs")
    differences = reconstruct_differences(level)
    support = support_table(differences)
    if support != result["first_difference_support"]:
        raise ValueError("first-difference support differs")
    reconstructed = reconstruct_results(differences)
    maximum, checks = compare_results(result["results"], reconstructed)
    if maximum > 1e-10:
        raise ValueError(f"saved-precision metric tolerance failed: {maximum}")
    validate_summaries(result)

    output = {
        "schema": "us_wheat_practice_pdsi_predictive_independent_validation_v1",
        "status": "passed",
        "result": {"path": arguments.result, "sha256": sha256(result_path)},
        "production_resource": {
            "path": arguments.resource,
            "sha256": sha256(resource_path),
            "peak_rss_bytes": int(resource["peak_rss_bytes"]),
        },
        "first_difference_support": support,
        "independent_result_checks": checks,
        "maximum_absolute_metric_difference": maximum,
        "checked_result_rows": len(checks),
        "primary_gates": {
            summary["irrigation_practice"]: bool(
                summary["pdsi_linear_predictive_gate_passed"]
            )
            for summary in result["summaries"]
        },
        "stronger_claim_gates_all_closed": True,
        "claim_boundary": (
            "historical regional predictive diagnostic for a separate PDSI family; "
            "not causal, an irrigation treatment effect, national, future-facing, "
            "global, damage, or SCC evidence"
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "checked_result_rows": output["checked_result_rows"],
        "maximum_absolute_metric_difference": maximum,
        "primary_gates": output["primary_gates"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
