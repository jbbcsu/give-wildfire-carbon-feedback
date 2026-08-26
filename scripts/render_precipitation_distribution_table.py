#!/usr/bin/env python3
"""Render coefficient-free Markdown from validated distribution summaries.

This utility does not fit a model or revalidate source observations.  It only
accepts validator-produced summary JSON whose scientific boundary fields and
hashes match the supplied, current diagnostic specification and lock files.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from evaluate_precipitation_distribution_diagnostic import (
    DIAGNOSTIC_CONTRACT_ID,
    SPEC_DEFAULT,
    assert_coefficients_suppressed,
    load_contract,
    locked_input,
    sha256_path,
)
from validate_precipitation_distribution_diagnostic import (
    HOLDOUTS,
    SUMMARY_STATUS,
)


PROJECT = Path(__file__).resolve().parents[1]
LOCK_GLOB = "precipitation_distribution_diagnostic*.lock.toml"
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
BOUNDARY_FLAGS = {
    "source_basis_fit_authorized": False,
    "coefficients_suppressed": True,
    "causal_interpretation_authorized": False,
    "production_model_selection_authorized": False,
    "scc_use_authorized": False,
}
EXTENSION_PREFIX = "quantity_plus_"
REQUIRED_WARNING = (
    "Rankings and incremental RMSE are descriptive held-out predictive comparisons. "
    "They are not causal effect estimates, model-selection authority, damages, or SCC inputs."
)


def _hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def discover_locks(paths: list[Path] | None) -> list[Path]:
    """Return explicit locks or the deterministic project lock inventory."""
    locks = paths or sorted((PROJECT / "config").glob(LOCK_GLOB))
    if not locks:
        raise ValueError("No diagnostic lock files were supplied or discovered")
    resolved = [path.resolve() for path in locks]
    if len(resolved) != len(set(resolved)):
        raise ValueError("Duplicate diagnostic lock paths are not allowed")
    return resolved


def index_locks(lock_paths: list[Path]) -> dict[str, Path]:
    """Index locks by exact file hash and reject ambiguous duplicate content."""
    indexed: dict[str, Path] = {}
    for path in lock_paths:
        if not path.is_file():
            raise ValueError(f"Diagnostic lock does not exist: {path}")
        digest = sha256_path(path)
        if digest in indexed:
            raise ValueError(
                f"Two diagnostic locks have identical content: {indexed[digest]} and {path}"
            )
        indexed[digest] = path
    return indexed


def _validate_boundary(summary: dict[str, Any], path: Path) -> None:
    if summary.get("status") != SUMMARY_STATUS:
        raise ValueError(f"Unrecognized validation status in {path}")
    if summary.get("diagnostic_contract_id") != DIAGNOSTIC_CONTRACT_ID:
        raise ValueError(f"Diagnostic contract mismatch in {path}")
    for name, expected in BOUNDARY_FLAGS.items():
        value = summary.get(name)
        if type(value) is not bool or value is not expected:
            raise ValueError(f"Scientific boundary requires {name}={expected} in {path}")
    if summary.get("warning") != REQUIRED_WARNING:
        raise ValueError(f"Scientific interpretation warning mismatch in {path}")
    assert_coefficients_suppressed(summary)


def validate_summary(
    path: Path,
    spec_path: Path,
    lock_index: dict[str, Path],
) -> list[dict[str, Any]]:
    """Validate one summary and return its coefficient-free report rows."""
    if not path.name.endswith("_summary.json"):
        raise ValueError(f"Summary input must end in _summary.json: {path}")
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read summary JSON {path}: {error}") from error
    if not isinstance(summary, dict):
        raise ValueError(f"Summary root must be an object: {path}")
    _validate_boundary(summary, path)

    spec_hash = _hash(summary.get("spec_sha256"), "spec_sha256")
    if not spec_path.is_file() or sha256_path(spec_path) != spec_hash:
        raise ValueError(f"Summary specification hash does not match {spec_path}: {path}")
    lock_hash = _hash(summary.get("lock_sha256"), "lock_sha256")
    lock_path = lock_index.get(lock_hash)
    if lock_path is None:
        raise ValueError(f"No supplied diagnostic lock matches lock_sha256 in {path}")
    spec, lock, models, loaded_spec_hash, loaded_lock_hash = load_contract(spec_path, lock_path)
    if loaded_spec_hash != spec_hash or loaded_lock_hash != lock_hash:
        raise ValueError(f"Loaded diagnostic contract hashes do not match {path}")

    crop = summary.get("crop")
    if not isinstance(crop, str) or not crop:
        raise ValueError(f"Summary crop is absent in {path}")
    source = locked_input(lock, crop)
    panel_hash = _hash(summary.get("source_panel_sha256"), "source_panel_sha256")
    if source.get("panel_sha256") != panel_hash:
        raise ValueError(f"Summary source-panel hash does not match its lock in {path}")
    if summary.get("models") != list(models):
        raise ValueError(f"Summary model registry does not match its contract in {path}")

    comparisons = summary.get("comparisons")
    if not isinstance(comparisons, list):
        raise ValueError(f"Summary comparisons must be a list in {path}")
    by_holdout: dict[str, dict[str, Any]] = {}
    for comparison in comparisons:
        if not isinstance(comparison, dict):
            raise ValueError(f"Every comparison must be an object in {path}")
        holdout = comparison.get("holdout")
        if holdout in by_holdout:
            raise ValueError(f"Duplicate holdout {holdout!r} in {path}")
        if holdout not in HOLDOUTS:
            raise ValueError(f"Unrecognized holdout {holdout!r} in {path}")
        by_holdout[str(holdout)] = comparison
    if set(by_holdout) != set(HOLDOUTS):
        raise ValueError(f"Summary does not contain the complete holdout product in {path}")

    model_order = {name: index for index, name in enumerate(models)}
    extension_models = [name for name in models if name.startswith(EXTENSION_PREFIX)]
    if not extension_models:
        raise ValueError(f"Diagnostic contract has no distribution extensions in {path}")

    rows: list[dict[str, Any]] = []
    for holdout in HOLDOUTS:
        comparison = by_holdout[holdout]
        temperature_rmse = _finite_nonnegative(
            comparison.get("temperature_control_rmse"),
            f"{holdout}.temperature_control_rmse",
        )
        seasonal_rmse = _finite_nonnegative(
            comparison.get("seasonal_quantity_rmse"),
            f"{holdout}.seasonal_quantity_rmse",
        )
        ranked = comparison.get("ranked_models")
        if not isinstance(ranked, list):
            raise ValueError(f"ranked_models must be a list for {holdout} in {path}")
        indexed: dict[str, dict[str, Any]] = {}
        for entry in ranked:
            if not isinstance(entry, dict):
                raise ValueError(f"Every ranked model must be an object in {path}")
            model = entry.get("model")
            if model in indexed:
                raise ValueError(f"Duplicate ranked model {model!r} for {holdout} in {path}")
            if model not in models:
                raise ValueError(f"Unrecognized ranked model {model!r} for {holdout} in {path}")
            indexed[str(model)] = entry
        if set(indexed) != set(models):
            raise ValueError(f"Ranked model product is incomplete for {holdout} in {path}")

        temperature_ranked = _finite_nonnegative(
            indexed["temperature_control"].get("rmse"),
            f"{holdout}.temperature_control.rmse",
        )
        seasonal_ranked = _finite_nonnegative(
            indexed["seasonal_quantity"].get("rmse"),
            f"{holdout}.seasonal_quantity.rmse",
        )
        if not math.isclose(temperature_rmse, temperature_ranked, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"Temperature-control RMSE does not reconcile for {holdout} in {path}")
        if not math.isclose(seasonal_rmse, seasonal_ranked, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"Seasonal-quantity RMSE does not reconcile for {holdout} in {path}")

        extension_values: list[tuple[float, int, str, float]] = []
        for model in extension_models:
            entry = indexed[model]
            rmse = _finite_nonnegative(entry.get("rmse"), f"{holdout}.{model}.rmse")
            improvement = _finite(
                entry.get("rmse_improvement_vs_seasonal_quantity"),
                f"{holdout}.{model}.rmse_improvement_vs_seasonal_quantity",
            )
            expected_improvement = seasonal_rmse - rmse
            if not math.isclose(improvement, expected_improvement, rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(
                    f"Incremental RMSE does not reconcile for {model}/{holdout} in {path}"
                )
            extension_values.append((rmse, model_order[model], model, improvement))
        best_rmse, _order, best_model, improvement = min(extension_values)
        rows.append(
            {
                "crop": crop,
                "holdout": holdout,
                "temperature_rmse": temperature_rmse,
                "seasonal_quantity_rmse": seasonal_rmse,
                "extension": best_model,
                "extension_rmse": best_rmse,
                "improvement_vs_seasonal": improvement,
            }
        )
    return rows


def render_markdown(rows: list[dict[str, Any]]) -> str:
    """Render deterministic Markdown without fitted parameters."""
    header = (
        "| Crop | Holdout | Temperature RMSE | Seasonal quantity RMSE | "
        "Lowest-RMSE distribution extension | Extension RMSE | "
        "Improvement vs seasonal |\n"
        "|---|---|---:|---:|---|---:|---:|\n"
    )
    body = "".join(
        "| {crop} | {holdout} | {temperature_rmse:.6f} | "
        "{seasonal_quantity_rmse:.6f} | {extension} | {extension_rmse:.6f} | "
        "{improvement_vs_seasonal:+.6f} |\n".format(**row)
        for row in rows
    )
    note = (
        "\n*Coefficient-free held-out predictive diagnostics only. Positive improvement "
        "means lower RMSE than seasonal quantity; negative values report worse performance. "
        "The table does not establish causality, select a production model, estimate damages, "
        "or authorize SCC use.*\n"
    )
    return header + body + note


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summaries", nargs="+", type=Path)
    parser.add_argument("--spec", type=Path, default=SPEC_DEFAULT)
    parser.add_argument(
        "--lock",
        action="append",
        type=Path,
        help="Allowed diagnostic lock; repeat as needed (default: discover project locks)",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    spec_path = args.spec.resolve()
    lock_index = index_locks(discover_locks(args.lock))
    inputs = sorted((path.resolve() for path in args.summaries), key=lambda path: str(path))
    if len(inputs) != len(set(inputs)):
        raise ValueError("Duplicate summary paths are not allowed")
    rows: list[dict[str, Any]] = []
    for path in inputs:
        rows.extend(validate_summary(path, spec_path, lock_index))
    rendered = render_markdown(rows)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
